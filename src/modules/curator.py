import json
import random
from src.modules.librarian import Librarian
from src.modules.oracle import Oracle
from src.utils.llm_client import LLMClient
from colorama import Fore, Style

class Curator:
    def __init__(self):
        self.librarian = Librarian()
        # Oracle koristimo za pristup ChromaDB kolekciji
        self.oracle = Oracle() 
        self.llm = LLMClient()
        
    def discover_topics(self, sample_size=50):
        """
        Analizira uzorak nasumičnih chunkova i identificira glavne teme.
        """
        # 1. Get random sample
        sample_chunks = self.librarian.get_random_chunks(limit=sample_size)
        
        if not sample_chunks:
            print("Nema dovoljno podataka za analizu.")
            return []
            
        # 2. Ask LLM
        prompt = (
            "Analiziraj sljedeće isječke teksta iz tehničke dokumentacije i identificiraj 5-7 glavnih tema ili kategorija. "
            "Vrati SAMO JSON listu stringova (npr. [\"Baza Podataka\", \"API Interface\"]). "
            "Teme moraju biti na hrvatskom jeziku.\n\n"
            "Isječci:\n" + "\n---\n".join([c[:200] for c in sample_chunks])
        )
        
        response = self.llm.complete(prompt)
        
        # 3. Parse result
        try:
            # Clean possible markdown code blocks
            clean_response = response.replace("```json", "").replace("```", "").strip()
            # Ponekad LLM vrati tekst prije/poslije JSON-a, probaj naći [ ... ]
            start = clean_response.find('[')
            end = clean_response.rfind(']')
            if start != -1 and end != -1:
                clean_response = clean_response[start:end+1]
                
            topics = json.loads(clean_response)
            return topics
        except Exception as e:
            print(f"Error parsing topics: {e} \nResponse was: {response}")
            return []
            
    def auto_tag(self, topics, chunks_per_topic=20):
        """
        Automatski tagira chunkove u vektorskoj bazi s identificiranim temama.
        """
        results = {}
        processed_ids = set()
        
        for topic in topics:
            print(f"Tagiram temu: {Fore.CYAN}{topic}{Style.RESET_ALL}...")
            
            # Find relevant chunks for this topic using Oracle's vector search
            # Koristimo sirovi query na kolekciji
            search_res = self.oracle.collection.query(
                query_texts=[topic],
                n_results=chunks_per_topic
            )
            
            if not search_res['ids']:
                continue
                
            ids = search_res['ids'][0]
            metadatas = search_res['metadatas'][0]
            
            updated_count = 0
            
            for i, chunk_id in enumerate(ids):
                # if chunk_id in processed_ids: continue # Možemo dozvoliti multi-tagging
                
                meta = metadatas[i]
                
                # Update metadata
                if 'topics' in meta:
                    current_topics = meta['topics'].split(',')
                    if topic not in current_topics:
                        meta['topics'] += f",{topic}"
                else:
                    meta['topics'] = topic
                    
                # Store update (Chroma update requires IDs)
                self.oracle.collection.update(
                    ids=[chunk_id],
                    metadatas=[meta]
                )
                updated_count += 1
                processed_ids.add(chunk_id)
                
            results[topic] = updated_count
            
        return results

    def run_clustering_pipeline(self):
        """Izvodi cijeli proces: Sampling -> Topic Discovery -> Auto-Tagging."""
        print(f"{Fore.MAGENTA}🔎 Curator analizira bazu znanja...{Style.RESET_ALL}")
        
        topics = self.discover_topics(sample_size=40)
        if not topics:
            print("Nisu pronađene teme.")
            return
            
        print(f"Identificirane teme:")
        for t in topics:
             print(f" - {t}")
             
        print("-" * 30)
        stats = self.auto_tag(topics)
        
        print(f"\n{Fore.GREEN}✅ Gotovo! Rezultati tagiranja:{Style.RESET_ALL}")
        for theme, count in stats.items():
            print(f" - {theme}: {count} chunkova")

if __name__ == "__main__":
    curator = Curator()
    curator.run_clustering_pipeline()
