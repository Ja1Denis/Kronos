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

    def ask(self, query, project=None, limit=5, silent=False):
        """
        Postavlja pitanje Kronosu koristeći 3-stage pipeline:
        1. Retrieval (Vector + Keyword)
        2. Merging & Deduplication
        3. Reranking (Scoring)
        """
        from src.utils.stemmer import stem_text
        stemmed_query = stem_text(query, mode="aggressive")
        
        if not silent:
            project_info = f" na projektu [bold cyan]{project}[/]" if project else ""
            print(f"{Fore.MAGENTA}🔮 Kronos razmatra{project_info}: '{query}'{Style.RESET_ALL}")

        # STAGE 0: Entity Search (Prioritet)
        entities = self.librarian.search_entities(query, project=project, limit=limit)

        # STAGE 1: Broad Retrieval
        # a) Vector
        where_filter = {"project": project} if project else None
        vector_candidates = self.collection.query(
            query_texts=[query],
            n_results=limit * 2, # Uzmi više kandidata za reranking
            where=where_filter
        )
        
        # b) Keyword
        fts_candidates = self.librarian.search_fts(stemmed_query, project=project, limit=limit * 2)

        # STAGE 2: Merging & Deduplication
        all_chunks = []
        seen_contents = set()

        # Dodaj vektorske kandidate
        if vector_candidates['documents']:
            for doc, meta, dist in zip(vector_candidates['documents'][0], vector_candidates['metadatas'][0], vector_candidates['distances'][0]):
                if doc not in seen_contents:
                    score = 1 - dist
                    all_chunks.append({
                        "content": doc,
                        "metadata": meta,
                        "v_score": score,
                        "k_score": 0,
                        "method": "Vector"
                    })
                    seen_contents.add(doc)

        # Dodaj i poveži FTS kandidate
        for path, content in fts_candidates:
            if content in seen_contents:
                # Već imamo iz vektora, povečaj mu k_score
                for chunk in all_chunks:
                    if chunk["content"] == content:
                        chunk["k_score"] = 1.0 # Jednostavan boosting
                        chunk["method"] = "Hybrid 🧩"
                        break
            else:
                all_chunks.append({
                    "content": content,
                    "metadata": {"source": path},
                    "v_score": 0,
                    "k_score": 1.0,
                    "method": "Keyword"
                })
                seen_contents.add(content)

        # STAGE 3: Simple Reranking (Scoring)
        # Finalni score = vector_score + keyword_boost
        for chunk in all_chunks:
            chunk["final_score"] = chunk["v_score"] + (chunk["k_score"] * 0.3)

        # Sortiraj po finalnom scoru
        all_chunks.sort(key=lambda x: x["final_score"], reverse=True)

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
                    "content": c["content"],
                    "metadata": c["metadata"],
                    "score": c["final_score"],
                    "method": c["method"]
                } for c in all_chunks[:limit]
            ]
        }
