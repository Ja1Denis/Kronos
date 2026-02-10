from colorama import Fore, Style
import chromadb
import os
import threading
from concurrent.futures import ThreadPoolExecutor

class Oracle:
    def __init__(self, db_path="data/store"):
        self.db_path = db_path
        self._lock = threading.Lock() # Global lock for thread safety
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(name="kronos_memory")
        
        from src.modules.librarian import Librarian
        self.librarian = Librarian()
        
        # Opcionalno za HyDE/Context
        self.hypothesizer = None
        self.contextualizer = None
        
        try:
            from src.modules.hyde import Hypothesizer
            from src.modules.contextualizer import Contextualizer
            self.hypothesizer = Hypothesizer()
            self.contextualizer = Contextualizer()
        except ImportError:
            pass

    def _retrieve_candidates(self, query, project=None, limit=10, hyde=False, silent=False):
        """Privatna metoda za fetch, poziva se unutar ask locka"""
        vector_query = query
        if hyde and self.hypothesizer:
             vector_query = self.hypothesizer.generate_hypothetical_answer(query)
        
        where_filter = None
        if project:
             where_filter = {"project": project}
             
        vector_candidates = self.collection.query(
            query_texts=[vector_query],
            n_results=limit * 4,
            where=where_filter
        )
        
        # Stemmed query za FTS
        try:
            from src.utils.crostem_utils import stem_text
            stemmed_query = stem_text(query)
        except ImportError:
            # Fallback if utils not available in path
            stemmed_query = query.lower()
            
        fts_candidates = self.librarian.search_fts(stemmed_query, project=project, limit=limit * 4)

        candidates = []
        # Vector
        for i in range(len(vector_candidates['ids'][0])):
            candidates.append({
                "id": vector_candidates['ids'][0][i],
                "content": vector_candidates['documents'][0][i],
                "metadata": vector_candidates['metadatas'][0][i],
                "score": 1.0 - vector_candidates['distances'][0][i],
                "method": "Vector"
            })
            
        # FTS
        for c in fts_candidates:
             content, path, score = c
             candidates.append({
                 "id": f"fts_{path}_{hash(content)}",
                 "content": content,
                 "metadata": {"source": path},
                 "score": 0.8,
                 "method": "Keyword"
             })
             
        return candidates

    def ask(self, query, project=None, limit=10, silent=False, hyde=True, expand=False):
        """Thread-safe metoda za upit"""
        with self._lock:
            # 1. Query Expansion
            queries = [query]
            if expand and self.hypothesizer:
                if not silent: print(f"{Fore.MAGENTA}✨ Proširujem upit (Query Expansion)...{Style.RESET_ALL}")
                queries = self.hypothesizer.expand_query(query)
            elif not silent:
                 project_info = f" na projektu [bold cyan]{project}[/]" if project else ""
                 print(f"{Fore.MAGENTA}🔮 Kronos razmatra{project_info}: '{query}'{Style.RESET_ALL}")

            # 2. Retrieval Loop
            merged_chunks = {}
            for q in queries:
                candidates = self._retrieve_candidates(q, project, limit, hyde, silent=True)
                for c in candidates:
                    content = c["content"]
                    source = c['metadata'].get('source', '').lower()
                    
                    boost = 0.0
                    if any(x in source for x in ["current_status", "status", "todo", "development_log", "log.md"]):
                        boost += 0.5
                    elif any(x in source for x in ["tasks.md", "vision.md", "README"]):
                        boost += 0.2
                    elif "archive" in source or "old" in source:
                        boost -= 0.3
                    
                    current_score = c["score"] + boost
                    
                    if content in merged_chunks:
                        merged_chunks[content]["score"] += current_score
                    else:
                        c["score"] = current_score
                        merged_chunks[content] = c

            all_chunks = list(merged_chunks.values())
            all_chunks.sort(key=lambda x: x["score"], reverse=True)
            
            final_chunks = all_chunks[:limit]
            if self.contextualizer:
                for chunk in final_chunks:
                    source = chunk['metadata'].get('source')
                    if source:
                        chunk['expanded_content'] = self.contextualizer.expand_context(chunk['content'], source)
                    else:
                        chunk['expanded_content'] = chunk['content']

            # 3. Entities
            stopwords = {'sto', 'što', 'je', 'to', 'u', 'na', 'za', 'da', 'i', 'a', 'ili', 'kako', 'koji', 'koja', 'koje', 'mi', 'ti', 'projektu', 'projekt'}
            keywords = [w for w in query.lower().split() if w not in stopwords and len(w) > 2]
            
            final_entities = []
            seen_ids = set()
            for kw in keywords:
                ents = self.librarian.search_entities(kw, project=project, limit=limit)
                for e in ents:
                    if e['id'] not in seen_ids:
                        final_entities.append(e)
                        seen_ids.add(e['id'])

            return {
                "entities": [
                    {
                        "id": ent['id'],
                        "content": ent['content'],
                        "metadata": ent.get('metadata', {}),
                        "type": ent.get('type', "UNKNOWN").upper()
                    } for ent in final_entities
                ],
                "chunks": [
                    {
                        "content": c.get("expanded_content", c["content"]),
                        "original_content": c["content"],
                        "metadata": c["metadata"],
                        "score": c["score"],
                        "method": c.get("method", "Unknown")
                    } for c in final_chunks
                ]
            }
