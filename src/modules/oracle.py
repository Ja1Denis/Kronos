from colorama import Fore, Style
import chromadb
import os

class Oracle:
    def __init__(self, db_path="data/store"):
        self.db_path = db_path
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(name="kronos_memory")
        
        # Inicijaliziramo Librarian-a za FTS pretragu
        import os
        from modules.librarian import Librarian
        # Pretpostavljamo da je db_path = root/store, pa je root = dirname(db_path)
        root_path = os.path.dirname(db_path) 
        if not root_path: root_path = "."
        self.librarian = Librarian(root_path)

    def ask(self, query, limit=5, silent=False):
        """
        Postavlja pitanje Kronosu (Hibridna pretraga).
        Kombinira:
        1. Vektorsku pretragu (ChromaDB - ONNX)
        2. Keyword pretragu (SQLite FTS5 - BM25)
        """
        from utils.stemmer import stem_text
        stemmed_query = stem_text(query, mode="aggressive")
        
        if not silent:
            print(f"{Fore.MAGENTA}🔮 Oracle traži odgovor na: '{query}'{Style.RESET_ALL}")
            print(f"{Fore.MAGENTA}   (Stemmed: {stemmed_query}){Style.RESET_ALL}")
        
        # 1. Vektorska pretraga
        vector_results = self.collection.query(
            query_texts=[query],
            n_results=limit
        )
        
        # 2. Keyword pretraga (FTS)
        fts_results = self.librarian.search_fts(stemmed_query, limit=limit)
        
        # 3. Kombinacija rezultata (Deduplikacija)
        final_results = []
        seen_contents = set()
        
        # Dodaj vektorske rezultate
        if vector_results['documents']:
            documents = vector_results['documents'][0]
            metadatas = vector_results['metadatas'][0]
            distances = vector_results['distances'][0]
            
            for doc, meta, dist in zip(documents, metadatas, distances):
                if doc not in seen_contents:
                    final_results.append({
                        "content": doc,
                        "metadata": meta,
                        "score": 1 - dist,
                        "type": "Vector 🧠"
                    })
                    seen_contents.add(doc)
        
        # Dodaj FTS rezultate
        for path, content in fts_results:
            if content not in seen_contents:
                final_results.append({
                    "content": content,
                    "metadata": {"source": path},
                    "score": 0.0, # FTS nema direktno usporediv score s vektorima
                    "type": "Keyword 🗝️"
                })
                seen_contents.add(content)
                
        if not silent:
            if not final_results:
                print(f"{Fore.YELLOW}Nema rezultata.{Style.RESET_ALL}")
                return []
                
            print(f"{Fore.GREEN}Pronađeno {len(final_results)} unikatnih rezultata:{Style.RESET_ALL}")
            
            for i, res in enumerate(final_results[:limit*2]): # Prikazujemo top rezultate
                source = res['metadata'].get('source', 'Unknown')
                source_name = os.path.basename(source)
                score_display = f"{res['score']:.2%}" if res['type'].startswith("Vector") else "N/A"
                
                print(f"\n{Fore.CYAN}📄 [{res['type']}] {source_name}{Style.RESET_ALL} (Score: {score_display})")
                print(f"   {res['content'][:300].replace(chr(10), ' ')}...") # Replace newlines for cleaner output
                print("-" * 50)
            
        return final_results
