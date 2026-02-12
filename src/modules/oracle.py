import re
import hashlib
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from colorama import Fore, Style
import chromadb
import os
from typing import List, Dict, Any, Optional
from src.utils.metadata_helper import validate_metadata, enrich_metadata
from src.modules.types import QueryType, Pointer, SearchResult

class Oracle:
    def __init__(self, db_path="data/store"):
        self.db_path = db_path
        self._lock = threading.Lock() # Global lock for thread safety
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(name="kronos_memory")
        
        from src.modules.librarian import Librarian
        self.librarian = Librarian()
        
        # FastPath (Phase 9 - Rust-inspired simulation)
        try:
            from src.modules.fast_path import FastPath
            self.fast_path = FastPath(self.librarian)
            # Pokrećemo warmup u zasebnom threadu da ne blokira start
            threading.Thread(target=self.fast_path.warmup, daemon=True).start()
        except ImportError:
            self.fast_path = None

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

    def safe_upsert(self, documents, metadatas, ids):
        """
        Wrapper oko collection.upsert s validacijom i obogaćivanjem metapodataka.
        """
        valid_docs = []
        valid_metas = []
        valid_ids = []
        
        for i, (doc, meta, uid) in enumerate(zip(documents, metadatas, ids)):
            if not validate_metadata(meta):
                print(f"{Fore.RED}❌ Metadata Validation Failed for {uid}. Skipping.{Style.RESET_ALL}")
                continue
            
            # Enrich metadata using helper
            enriched_meta = enrich_metadata(doc, meta)
                
            valid_docs.append(doc)
            valid_metas.append(enriched_meta)
            valid_ids.append(uid)
            
        if valid_docs:
            with self._lock:
                self.collection.upsert(
                    documents=valid_docs,
                    metadatas=valid_metas,
                    ids=valid_ids
                )

    def detect_query_type(self, query: str) -> QueryType:
        """
        Heuristička detekcija tipa upita.
        Priority: Aggregation > Semantic > Lookup
        """
        query_lower = query.lower().strip()
        
        # 1. Aggregation (Highest priority because "How many" contains "How")
        aggregation_markers = [
            "list", "popis", "prikaži sve", "daj sve", "listaj", "pokaži sve",
            "broj ", "koliko ", "how many", "zbroji", "sum", "total",
            "summary", "sažetak", "svi ", "sve ", "all ", "everything"
        ]
        
        if any(marker in query_lower for marker in aggregation_markers):
            return QueryType.AGGREGATION

        # 2. Semantic
        semantic_markers = [
            "explain", "objasni", "kako ", "how ", "why", "zašto", "čemu",
            "overview", "pregled", "arhitektura", "architecture", "design", "dizajn",
            "concept", "koncept", "značenje", "meaning", "princip"
        ]
        
        if any(marker in query_lower for marker in semantic_markers):
            return QueryType.SEMANTIC
            
        return QueryType.LOOKUP

    def extract_section_title(self, content: str) -> str:
        """
        Pronalazi najvjerojatniji naslov sekcije iz sadržaja chunka.
        """
        if not content or not isinstance(content, str):
            return "Untitled Section"
            
        lines = content.split('\n')
        # 1. Traži markdown headere (#, ##, ###)
        for line in lines:
            line = line.strip()
            if line.startswith('#'):
                # Ukloni sve # i razmake na početku
                title = line.lstrip('#').strip()
                if title: return title
                
        # 2. Fallback: Prva ne-prazna linija (ograničena na 60 znakova)
        for line in lines:
            line = line.strip()
            if line:
                if len(line) > 60:
                    return line[:57] + "..."
                return line
                
        return "Untitled Section"

    def build_pointer_response(self, pointers: List[Pointer]) -> Dict[str, Any]:
        """Formatira odgovor koji sadrži samo pointere."""
        from src.modules.context_budgeter import ContextItem
        total_tokens = sum(ContextItem.estimate_tokens(p.to_context()) for p in pointers)
        
        return {
            "type": "pointer_response",
            "pointers": [p.to_dict() for p in pointers],
            "total_found": len(pointers),
            "estimated_tokens": total_tokens,
            "message": f"Found {len(pointers)} relevant locations. Use fetch_exact to read content.",
            "status": "success"
        }

    def build_mixed_response(self, chunks: List[Dict], pointers: List[Pointer]) -> Dict[str, Any]:
        """Formatira mješoviti odgovor s chunkovima i pointerima."""
        from src.modules.context_budgeter import ContextItem
        chunk_tokens = sum(ContextItem.estimate_tokens(c.get("content", "")) for c in chunks)
        pointer_tokens = sum(ContextItem.estimate_tokens(p.to_context()) for p in pointers)
        
        return {
            "type": "mixed_response",
            "chunks": chunks,
            "pointers": [p.to_dict() for p in pointers],
            "total_found": len(chunks) + len(pointers),
            "estimated_tokens": chunk_tokens + pointer_tokens,
            "message": f"Found {len(chunks)} full chunks and {len(pointers)} additional pointers for more context.",
            "status": "success"
        }

    def build_chunk_response(self, chunks: List[Dict]) -> Dict[str, Any]:
        """Formatira odgovor koji sadrži samo pune chunkove."""
        from src.modules.context_budgeter import ContextItem
        total_tokens = sum(ContextItem.estimate_tokens(c.get("content", "")) for c in chunks)
        
        return {
            "type": "chunk_response",
            "chunks": chunks,
            "pointers": [],
            "estimated_tokens": total_tokens,
            "message": f"Found {len(chunks)} highly relevant chunks.",
            "status": "success"
        }

    def cluster_pointers(self, pointers: List[Pointer], limit: int = 5) -> List[Pointer]:
        """
        Grupira pointere po direktoriju i vraća najrelevantnije iz svake grupe.
        Pomaže u sprječavanju "eksplozije" konteksta s previše sličnih pointera.
        """
        if not pointers:
            return []
            
        clusters = {}
        for p in pointers:
            directory = os.path.dirname(p.file_path)
            if directory not in clusters:
                clusters[directory] = []
            clusters[directory].append(p)
            
        final_pointers = []
        # Iz svakog clustera uzmi najbolji pointer
        for directory in clusters:
            best_p = sorted(clusters[directory], key=lambda x: x.confidence, reverse=True)[0]
            final_pointers.append(best_p)
            
        # Sortiraj po confidence i limitiraj
        final_pointers.sort(key=lambda x: x.confidence, reverse=True)
        return final_pointers[:limit]

    def extract_keywords(self, query: str, limit: int = 5) -> List[str]:
        """
        Ekstrakcija ključnih riječi iz upita (za Pointere).
        """
        stopwords = {
            "what", "where", "how", "why", "when", "who", "which", "is", "are", "the", "a", "an",
            "this", "that", "those", "these", "to", "for", "with", "from", "at", "by", "on", "in",
            "što", "gdje", "kako", "zašto", "kada", "tko", "koji", "je", "su", "taj", "ova", "ovo",
            "u", "na", "sa", "iz", "kod", "do", "za", "o", "li", "bi", "da", "ne", "pa", "te", "ni"
        }
        
        # Clean query
        clean_query = re.sub(r'[^\w\s]', ' ', query.lower())
        words = clean_query.split()
        
        # Filter stopwords and short words
        keywords = [w for w in words if w not in stopwords and len(w) > 2]
        
        # Return unique top words
        seen = set()
        unique_keywords = []
        for k in keywords:
            if k not in seen:
                unique_keywords.append(k)
                seen.add(k)
                if len(unique_keywords) >= limit:
                    break
        
        return unique_keywords

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
        
        # Stemmed query za FTS (Hybrid AND mode by default)
        try:
            from src.utils.stemmer import stem_text
            stemmed_query = stem_text(query)
        except ImportError:
            stemmed_query = query.lower()
            
        fts_candidates = self.librarian.search_fts(stemmed_query, project=project, limit=limit * 4, mode="and")

        candidates = []
        # Vector
        if vector_candidates and vector_candidates['ids']:
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
             path, content, start_line, end_line = c 
             candidates.append({
                 "id": f"fts_{path}_{hash(content)}",
                 "content": content,
                 "metadata": {
                     "source": path,
                     "start_line": start_line,
                     "end_line": end_line
                 },
                 "score": 0.7,
                 "method": "Keyword"
             })
             
        return candidates

    def ask(self, query, project=None, limit=10, silent=False, hyde=True, expand=False):
        """
        Thread-safe metoda za upit s robusnim error handlingom i Fallback lancem.
        """
        try:
            with self._lock:
                # 0. Fast Path (L0/L1) - High confidence exact matches
                if self.fast_path:
                    try:
                        fast_res = self.fast_path.search(query)
                        if fast_res and fast_res["confidence"] >= 0.9:
                            if not silent: 
                                print(f"{Fore.GREEN}⚡ FastPath: {fast_res['type']} detektiran!{Style.RESET_ALL}")
                            return {
                                "entities": [{
                                    "id": "fp_" + str(hash(e.get('content', ''))),
                                    "content": e.get('content', ''),
                                    "metadata": e.get('metadata', {}),
                                    "type": e.get('metadata', {}).get("type", "UNKNOWN").upper()
                                } for e in fast_res.get("data", {}).get("entities", [])],
                                "chunks": [],
                                "pointers": [],
                                "method": fast_res.get("type", "FastPath")
                            }
                    except Exception as e:
                        print(f"{Fore.YELLOW}⚠️ FastPath error: {e}{Style.RESET_ALL}")

                # 1. Detektiraj tip upita
                try:
                    query_type = self.detect_query_type(query)
                except Exception:
                    query_type = QueryType.SEMANTIC # Default fallback
                
                if not silent:
                     print(f"{Fore.CYAN}🔎 Tip upita: {query_type.value.upper()}{Style.RESET_ALL}")

                # 2. Query Expansion (Samo za Semantic)
                queries = [query]
                if expand and self.hypothesizer and query_type == QueryType.SEMANTIC:
                    try:
                        queries = self.hypothesizer.expand_query(query)
                    except Exception:
                        queries = [query]

                # 3. Retrieval Loop
                all_candidates = []
                for q in queries:
                    try:
                        use_hyde = hyde or (query_type == QueryType.SEMANTIC)
                        retrieved = self._retrieve_candidates(q, project=project, limit=limit, hyde=use_hyde)
                        if retrieved:
                            all_candidates.extend(retrieved)
                    except Exception as e:
                        print(f"{Fore.YELLOW}⚠️ Retrieval error for query '{q}': {e}{Style.RESET_ALL}")
                
                # DEFENSE: Check candidates validity
                if not all_candidates:
                    if not silent: print(f"{Fore.YELLOW}⚠️ No candidates found for query.{Style.RESET_ALL}")
                    return self._empty_response("No relevant information found.")

                # 4. Deduplikacija i rangiranje
                seen_ids = set()
                unique_candidates = []
                
                # Sort safely by score
                def safe_score(c):
                    try:
                        score = c.get('score', 0.0)
                        return float(score) if isinstance(score, (int, float, str)) else 0.0
                    except Exception:
                        return 0.0

                for cand in sorted(all_candidates, key=safe_score, reverse=True):
                    cid = cand.get('id')
                    if cid and cid not in seen_ids:
                        unique_candidates.append(cand)
                        seen_ids.add(cid)
                
                
                # 5. Decision Tree / Classification
                final_chunks = []
                final_pointers = []
                final_entities = []
                query_keywords = self.extract_keywords(query)
                
                if query_type == QueryType.AGGREGATION:
                    if len(unique_candidates) > 5:
                        for cand in unique_candidates:
                            if cand.get('method') in ['Vector', 'Keyword']:
                                 p = self._candidate_to_pointer(cand, query_keywords)
                                 if p: final_pointers.append(p)
                            else:
                                 final_entities.append(cand)
                    else:
                        for cand in unique_candidates:
                            if cand.get('method') in ['Vector', 'Keyword']:
                                 final_chunks.append(cand)
                            else:
                                 final_entities.append(cand)
                                 
                elif query_type == QueryType.LOOKUP:
                    for cand in unique_candidates:
                        score = safe_score(cand)
                        if score > 0.75:
                            final_chunks.append(cand)
                        elif score > 0.4:
                            p = self._candidate_to_pointer(cand, query_keywords)
                            if p: final_pointers.append(p)
                
                else: # SEMANTIC
                    for i, cand in enumerate(unique_candidates):
                        score = safe_score(cand)
                        if i < 3 and score > 0.6:
                            final_chunks.append(cand)
                        else:
                            p = self._candidate_to_pointer(cand, query_keywords)
                            if p: final_pointers.append(p)


                # 6. Clustering
                final_pointers = self.cluster_pointers(final_pointers)

                # 7. Response Construction with specialized builders
                if final_chunks and final_pointers:
                    resp = self.build_mixed_response(final_chunks, final_pointers)
                elif final_chunks:
                    resp = self.build_chunk_response(final_chunks)
                elif final_pointers:
                    resp = self.build_pointer_response(final_pointers)
                else:
                    resp = self._empty_response("No relevant information found.")

                # Add extra fields for debugging/backward compatibility
                resp["entities"] = final_entities
                resp["query_type"] = query_type.value
                resp["method"] = "Hybrid-Pointer-System"
                
                return resp
        except Exception as e:
            print(f"{Fore.RED}❌ Oracle.ask() critical failure: {e}{Style.RESET_ALL}")
            import traceback
            traceback.print_exc()
            return self._error_response(str(e))

    def _empty_response(self, message):
        return {
            "entities": [],
            "chunks": [],
            "pointers": [],
            "message": message,
            "status": "empty"
        }

    def _error_response(self, error_msg):
        return {
            "entities": [],
            "chunks": [],
            "pointers": [],
            "error": error_msg,
            "status": "error"
        }

    def _candidate_to_pointer(self, candidate: dict, keywords: List[str]) -> Optional[Pointer]:
        """Helper za pretvorbu kandidata u Pointer objekt s provjerama sigurnosti."""
        try:
            if not candidate or not isinstance(candidate, dict):
                return None
                
            meta = candidate.get("metadata")
            if not meta or not isinstance(meta, dict):
                return None
            
            source = meta.get("source")
            if not source or not isinstance(source, str):
                return None
            
            # Security: Path safety
            from src.utils.metadata_helper import is_safe_path
            if not is_safe_path(source):
                print(f"{Fore.RED}⚠️ Skipping unsafe path in candidate: {source}{Style.RESET_ALL}")
                return None
                
            start = meta.get("start_line", 1)
            end = meta.get("end_line", 1)
            
            # Ensure line range is valid at least logically
            if not isinstance(start, int) or not isinstance(end, int) or end < start:
                start, end = 1, 1
            
            content = candidate.get("content", "")
            section = self.extract_section_title(content)
            
            return Pointer(
                file_path=source,
                section=section,
                line_range=(start, end),
                keywords=keywords,
                confidence=float(candidate.get("score", 0.0)),
                last_modified=str(meta.get("last_modified", 0)),
                content_hash=meta.get("content_hash", ""),
                indexed_at=meta.get("indexed_at", "")
            )
        except Exception as e:
            print(f"{Fore.YELLOW}⚠️ Failed to create pointer: {e}{Style.RESET_ALL}")
            return None
