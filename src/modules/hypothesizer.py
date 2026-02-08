import json
import os
import hashlib
from src.utils.llm_client import LLMClient

# Putanja do cache datoteke (apsolutna)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE_DIR = os.path.join(ROOT_DIR, "data", "cache")
CACHE_FILE = os.path.join(CACHE_DIR, "hyde_cache.json")

import threading

class Hypothesizer:
    def __init__(self, llm_client: LLMClient = None):
        self.llm = llm_client or LLMClient()
        self.cache = {}
        self.lock = threading.Lock()
        self._load_cache()
        
    def _load_cache(self):
        """Učitava cache iz JSON datoteke."""
        with self.lock:
            if not os.path.exists(CACHE_DIR):
                os.makedirs(CACHE_DIR, exist_ok=True)
                
            if os.path.exists(CACHE_FILE):
                try:
                    with open(CACHE_FILE, "r", encoding="utf-8") as f:
                        self.cache = json.load(f)
                except Exception as e:
                    print(f"Warning: Ne mogu učitati HyDE cache: {e}")
                    self.cache = {}

    def _save_cache(self):
        """Sprema cache u JSON datoteku."""
        with self.lock:
            try:
                with open(CACHE_FILE, "w", encoding="utf-8") as f:
                    json.dump(self.cache, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"Warning: Ne mogu spremiti HyDE cache: {e}")

    def generate_hypothesis(self, query: str) -> str:
        """
        Generira hipotetski odgovor na upit koristeći LLM (uz caching).
        """
        # 1. Check Cache
        query_hash = hashlib.md5(query.strip().lower().encode()).hexdigest()
        
        with self.lock:
            if query_hash in self.cache:
                return self.cache[query_hash]

        # 2. LLM Call
        prompt = (
            f"Molim te napiši kratak, hipotetski odlomak teksta koji odgovara na pitanje: '{query}'. "
            "Piši kao da je to isječak iz tehničke dokumentacije projekta Kronos. "
            "Koristi stručnu terminologiju (embedding, chroma, sqlite). "
            "Ne piši uvod niti zaključak, samo srž sadržaja."
        )
        
        hypothesis = self.llm.complete(prompt)
        
        # 3. Save to Cache (samo ako je validan odgovor)
        if not hypothesis.startswith("MOCK") and not hypothesis.startswith("ERROR") and not hypothesis.startswith("BLOCKED"):
            with self.lock:
                self.cache[query_hash] = hypothesis.strip()
            self._save_cache()
            
        # Ako je mock ili greška, vrati originalni upit kao fallback
        if hypothesis.startswith("MOCK") or hypothesis.startswith("ERROR"):
            print(f"[HyDE Warning] LLM nije dostupan: {hypothesis}")
            return query 
            
        return hypothesis.strip()

    def expand_query(self, query: str, num_variations: int = 3) -> list[str]:
        """
        Generira varijacije upita za poboljšanje pretrage (Query Expansion).
        """
        # 1. Check Cache
        cache_key = f"EXPAND_{query.strip().lower()}"
        query_hash = hashlib.md5(cache_key.encode()).hexdigest()
        
        with self.lock:
            if query_hash in self.cache:
                try:
                    cached_data = json.loads(self.cache[query_hash])
                    if isinstance(cached_data, list):
                        return cached_data
                except:
                    pass 
        
        # 2. LLM Call
        prompt = (
            f"Tvoj zadatak je generirati {num_variations} alternativnih verzija korisničkog upita za semantičku pretragu. "
            f"Cilj je pokriti sinonime i različite načine postavljanja istog pitanja u kontekstu 'Kronos' AI projekta. "
            f"Originalni upit: '{query}'\n"
            "Format: Samo pitanja, svako u novom redu. Bez brojeva, bez uvoda."
        )
        
        response = self.llm.complete(prompt)
        
        # Parse output
        variations = []
        if response and not response.startswith("ERROR") and not response.startswith("MOCK"):
            for line in response.split('\n'):
                line = line.strip()
                # Ukloni brojeve ako ih je LLM dodao (1. Pitanje)
                import re
                line = re.sub(r'^\d+\.\s*', '', line)
                line = line.lstrip("- ")
                if line and line != query:
                    variations.append(line)
                    
        # Osiguraj da imamo bar original
        if query not in variations:
            variations.insert(0, query)
            
        # Limit
        final_variations = variations[:num_variations+1]
        
        # 3. Save to Cache
        if not response.startswith("MOCK") and not response.startswith("ERROR"):
            with self.lock:
                self.cache[query_hash] = json.dumps(final_variations)
            self._save_cache()
            
        return final_variations

if __name__ == "__main__":
    hypo = Hypothesizer()
    print("Testiram Hypothesizer (HyDE & Expansion)...")
    
    q = "Kako radi Kronos ingestion?"
    # Test HyDE
    # h = hypo.generate_hypothesis(q)
    # print(f"Hipoteza: {h[:50]}...")
    
    # Test Expansion
    print(f"\nOriginalni upit: {q}")
    vars = hypo.expand_query(q)
    print("Varijacije:")
    for v in vars:
        print(f"- {v}")
