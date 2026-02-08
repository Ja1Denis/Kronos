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
        from src.modules.librarian import Librarian
        # Pretpostavljamo da je db_path = root/store, pa je root = dirname(db_path)
        root_path = os.path.dirname(db_path) 
        if not root_path: root_path = "."
        self.librarian = Librarian(root_path)
        
        # Lazy load za HyDE (opcionalno)
        try:
            from src.modules.hypothesizer import Hypothesizer
            self.hypothesizer = Hypothesizer()
        except Exception as e:
            print(f"Warning: Ne mogu učitati Hypothesizer: {e}")
            self.hypothesizer = None
            
        # Lazy load za Contextualizer
        try:
            from src.modules.contextualizer import Contextualizer
            self.contextualizer = Contextualizer()
        except Exception as e:
            print(f"Warning: Ne mogu učitati Contextualizer: {e}")
            self.contextualizer = None

    def _retrieve_candidates(self, query, project, limit, hyde, silent):
        """Helper metoda koja vraća sirove kandidate (Vector + FTS)."""
        from src.utils.stemmer import stem_text
        stemmed_query = stem_text(query, mode="aggressive")

        # HyDE
        vector_query = query
        if hyde and self.hypothesizer:
            if not silent: print(f"{Fore.CYAN}💭 HyDE: Generiram hipotezu za '{query}'...{Style.RESET_ALL}")
            vector_query = self.hypothesizer.generate_hypothesis(query)
            # if not silent: print(f"{Fore.DIM}Hipoteza: {vector_query[:100]}...{Style.RESET_ALL}")
        
        # Vector
        where_filter = {"project": project} if project else None
        vector_candidates = self.collection.query(
            query_texts=[vector_query],
            n_results=limit * 2,
            where=where_filter
        )
        
        # FTS
        fts_candidates = self.librarian.search_fts(stemmed_query, project=project, limit=limit * 2)
        
        candidates = []
        if vector_candidates['documents']:
            for doc, meta, dist in zip(vector_candidates['documents'][0], vector_candidates['metadatas'][0], vector_candidates['distances'][0]):
                 candidates.append({
                     "content": doc,
                     "metadata": meta,
                     "score": (1 - dist),
                     "method": "Vector"
                 })
                 
        for path, content in fts_candidates:
             candidates.append({
                 "content": content,
                 "metadata": {"source": path},
                 "score": 0.5, # Base FTS score
                 "method": "Keyword"
             })
             
        return candidates

    def ask(self, query, project=None, limit=5, silent=False, hyde=False, expand=False):
        """
        Postavlja pitanje Kronosu koristeći napredni pipeline:
        1. Query Expansion (opcionalno)
        2. Multi-Retrieval (HyDE, Vector, FTS)
        3. RRF Fusion & Deduplication
        4. Contextual Expansion
        """
        
        # 1. Query Expansion
        queries = [query]
        if expand and self.hypothesizer:
            if not silent: print(f"{Fore.MAGENTA}✨ Proširujem upit (Query Expansion)...{Style.RESET_ALL}")
            variations = self.hypothesizer.expand_query(query)
            queries = variations # ovo uključuje i original
            if not silent:
                for v in queries[1:]: print(f"  - {v}")
        elif not silent:
             project_info = f" na projektu [bold cyan]{project}[/]" if project else ""
             print(f"{Fore.MAGENTA}🔮 Kronos razmatra{project_info}: '{query}'{Style.RESET_ALL}")

        # 2. Retrieval Loop (Merge & Rank)
        merged_chunks = {}
        
        for q in queries:
            # Silent za sub-upite da ne spamamo konzolu, osim ako je expansion uključen pa želimo vidjeti progress?
            sub_silent = True 
            candidates = self._retrieve_candidates(q, project, limit, hyde, sub_silent)
            
            for c in candidates:
                content = c["content"]
                if content in merged_chunks:
                    # Boost postojećeg (RRF-ish)
                    merged_chunks[content]["score"] += c["score"]
                    if c["method"] not in merged_chunks[content]["method"]:
                         merged_chunks[content]["method"] += f", {c['method']}"
                else:
                    merged_chunks[content] = c

        all_chunks = list(merged_chunks.values())
        
        # Rerank
        all_chunks.sort(key=lambda x: x["score"], reverse=True)
        
        # Contextual Expansion za top rezultate
        final_chunks = all_chunks[:limit]
        if self.contextualizer:
            for chunk in final_chunks:
                source = chunk['metadata'].get('source')
                if source:
                    chunk['expanded_content'] = self.contextualizer.expand_context(chunk['content'], source, context_window=300)
                else:
                    chunk['expanded_content'] = chunk['content']

        # Entity Search (samo jednom, na originalni upit)
        entities = self.librarian.search_entities(query, project=project, limit=limit)

        return {
            "entities": [
                {
                    "id": ent['id'],
                    "content": ent['content'],
                    "metadata": {"source": ent['file_path'], "project": ent['project']},
                    "type": ent['type'].upper(),
                    "created_at": ent['created_at']
                } for ent in entities
            ],
            "chunks": [
                {
                    "content": c.get("expanded_content", c["content"]),
                    "original_content": c["content"],
                    "metadata": c["metadata"],
                    "score": c["score"],
                    "method": c["method"]
                } for c in final_chunks
            ]
        }
