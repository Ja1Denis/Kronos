import json
import os
import hashlib
from src.utils.llm_client import LLMClient

# Putanja do cache datoteke (apsolutna)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE_DIR = os.path.join(ROOT_DIR, "data", "cache")
CACHE_FILE = os.path.join(CACHE_DIR, "hyde_cache.json")

class Hypothesizer:
    def __init__(self, llm_client: LLMClient = None):
        self.llm = llm_client or LLMClient()
        self.cache = {}
        self._load_cache()
        
    def _load_cache(self):
        """Učitava cache iz JSON datoteke."""
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
        if query_hash in self.cache:
            # print(f"[DEBUG] HyDE Cache Hit!") # Otkomentiraj za debug
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
            self.cache[query_hash] = hypothesis.strip()
            self._save_cache()
            
        # Ako je mock ili greška, vrati originalni upit kao fallback
        if hypothesis.startswith("MOCK") or hypothesis.startswith("ERROR"):
            print(f"[HyDE Warning] LLM nije dostupan: {hypothesis}")
            return query 
            
        return hypothesis.strip()

if __name__ == "__main__":
    hypo = Hypothesizer()
    print("Testiram Hypothesizer (HyDE)...")
    q = "Kako radi Kronos ingestion?"
    h = hypo.generate_hypothesis(q)
    print(f"Originalni upit: {q}")
    print("-" * 20)
    print(f"Generirana hipoteza:\n{h}")
    print("-" * 20)
