from colorama import Fore, Style
import chromadb
import os
from concurrent.futures import ThreadPoolExecutor

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
        
        # Vector Search - Main (Chunks + Entities mixed)
        where_filter = {"project": project} if project else None
        
        vector_candidates = self.collection.query(
            query_texts=[vector_query],
            n_results=limit * 2,
            where=where_filter
        )
        
        entity_where = {"type": "entity"}
        if project:
             # Explicit AND for ChromaDB
             entity_where = {"$and": [{"type": "entity"}, {"project": project}]}
             
        entity_candidates = self.collection.query(
            query_texts=[vector_query],
            n_results=limit,
            where=entity_where
        )
        
        # FTS
        fts_candidates = self.librarian.search_fts(stemmed_query, project=project, limit=limit * 2)
        
        candidates = []
        
        # Helper za dodavanje
        def add_candidates(source_res, is_entity_boost=False):
            if source_res and source_res['documents']:
                for doc, meta, dist in zip(source_res['documents'][0], source_res['metadatas'][0], source_res['distances'][0]):
                     # Boost score za entitete
                     score = (1 - dist)
                     if is_entity_boost: 
                         score += 0.2 # Artificial boost for focused entities
                     
                     candidates.append({
                         "content": doc,
                         "metadata": meta,
                         "score": score,
                         "method": "Vector (Entity)" if is_entity_boost else "Vector"
                     })

        add_candidates(vector_candidates)
        add_candidates(entity_candidates, is_entity_boost=True)

                 
        for path, content in fts_candidates:
             candidates.append({
                 "content": content,
                 "metadata": {"source": path},
                 "score": 0.8, # Povećan Base FTS score (prije 0.5)
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

        # 2. Retrieval Loop (Paralelno)
        merged_chunks = {}
        
        def fetch_candidates(q):
            return self._retrieve_candidates(q, project, limit, hyde, silent=True)

        with ThreadPoolExecutor(max_workers=len(queries)) as executor:
            results = list(executor.map(fetch_candidates, queries))

        # 3. Merge results & Rank
        for candidates in results:
            for c in candidates:
                content = c["content"]
                
                # --- [BOOSTING LOGIC] ---
                # Dajemo prednost "živim" dokumentima naspram statične dokumentacije
                source = c['metadata'].get('source', '').lower()
                boost = 0.0
                
                # Visoki prioritet: Trenutno stanje i logovi
                if any(x in source for x in ["current_status", "status", "todo", "development_log", "log.md"]):
                    boost += 0.5
                # Srednji prioritet: Planovi i zadaci
                elif any(x in source for x in ["tasks.md", "vision.md", "README"]):
                    boost += 0.2
                # Penalizacija: Stare arhive ili backupi (ako ih ima u bazi)
                elif "archive" in source or "old" in source:
                    boost -= 0.3
                
                # Primijeni boost na score
                current_score = c["score"] + boost
                
                if content in merged_chunks:
                    # RRF-ish fusion s kumulativnim score-om
                    merged_chunks[content]["score"] += current_score
                    if c["method"] not in merged_chunks[content]["method"]:
                         merged_chunks[content]["method"] += f", {c['method']}"
                else:
                    c["score"] = current_score # spremi boostani score
                    merged_chunks[content] = c

        all_chunks = list(merged_chunks.values())
        
        # Rerank prema finalnom (boostanom) score-u
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

        # 4. Entity Search (Keyword + Semantic)
        # Prvo dohvati keyword kandidate
        stopwords = {'sto', 'što', 'je', 'to', 'u', 'na', 'za', 'da', 'i', 'a', 'ili', 'kako', 'koji', 'koja', 'koje', 'mi', 'ti', 'projektu', 'projekt'}
        keywords = [w for w in query.lower().split() if w not in stopwords and len(w) > 2]
        
        keyword_entities = []
        seen_ids = set()
        for kw in keywords:
            ents = self.librarian.search_entities(kw, project=project, limit=limit)
            for e in ents:
                if e['id'] not in seen_ids:
                    keyword_entities.append(e)
                    seen_ids.add(e['id'])
        
        # Ako nema rezultata s pojedinačnim riječima, probaj cijeli upit
        if not keyword_entities:
            keyword_entities = self.librarian.search_entities(query, project=project, limit=limit)
            for e in keyword_entities: seen_ids.add(e['id'])

        # Sada procesiraj final_chunks i izdvoji semantic entities
        semantic_entities = []
        regular_chunks = []

        for c in final_chunks:
            meta = c['metadata']
            if meta.get('type') == 'entity':
                # Ovo je entitet iz ChromaDB-a
                eid = meta.get('entity_id')
                # Ako već imamo ovaj entitet iz keyword searcha, preskoči duplikat, 
                # ali možda semantic search ima bolji score? Zadržimo to.
                if eid not in seen_ids:
                    ent = {
                        "id": eid,
                        "content": c['content'],
                        "metadata": meta,
                        "type": meta.get('entity_type', 'UNKNOWN').upper(),
                        "created_at": meta.get('created_at', '')
                    }
                    semantic_entities.append(ent)
                    seen_ids.add(eid)
            else:
                regular_chunks.append(c)

        # Spoji sve entitete (prioritet: Semantic > Keyword jer su rerankirani)
        # Zapravo, keyword entities nisu rerankirani.
        # Idemo: Semantic Entities + Keyword Entities
        final_entities = semantic_entities + [e for e in keyword_entities if e['id'] not in seen_ids] 

        return {
            "entities": [
                {
                    "id": ent['id'],
                    "content": ent['content'],
                    "metadata": ent.get('metadata', {"source": ent.get('file_path'), "project": ent.get('project')}),
                    "type": ent['type'].upper() if 'type' in ent else "UNKNOWN",
                    "created_at": ent['created_at']
                } for ent in final_entities
            ],
            "chunks": [
                {
                    "content": c.get("expanded_content", c["content"]),
                    "original_content": c["content"],
                    "metadata": c["metadata"],
                    "score": c["score"],
                    "method": c["method"]
                } for c in regular_chunks
            ]
        }
