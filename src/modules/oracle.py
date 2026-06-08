import re
import hashlib
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from colorama import Fore, Style
import chromadb
import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential
from src.utils.metadata_helper import validate_metadata, enrich_metadata
from src.modules.types import QueryType, Pointer, SearchResult
from src.utils.metrics import metrics
from src.utils.logger import logger

# Import Graph (v0.6.1+)
try:
    from src.modules.disk_graph import DiskKnowledgeGraph
    GRAPH_AVAILABLE = True
except ImportError:
    GRAPH_AVAILABLE = False
    logger.warning("Graph module not available - running in legacy mode")

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5))
def resilient_vector_query(collection, query, n_results=5, where=None):
    """Retry vector query do 3 puta s exponential backoff"""
    try:
        return collection.query(query_texts=[query], n_results=n_results, where=where)
    except Exception as e:
        logger.warning(f"Vector query retry due to: {e}")
        metrics.log_failure("vector")
        raise  # Re-raise da retry logic uhvati

class Oracle:
    def __init__(self, db_path="data/store"):
        self.db_path = db_path
        self._lock = threading.Lock() # Global lock for thread safety
        
        # Učitaj varijable iz .agent/.env datoteke
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        workspace_root = os.path.dirname(project_root)
        env_path = os.path.join(workspace_root, '.agent', '.env')
        load_dotenv(env_path)
        
        # Use Gemini for embeddings to avoid local model crashes on Windows
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            try:
                from chromadb.utils import embedding_functions
                self.embedding_function = embedding_functions.GoogleGenerativeAiEmbeddingFunction(
                    api_key=api_key,
                    model_name="models/gemini-embedding-001"
                )
            except Exception as e:
                print(f"⚠️ Warning: Could not init Gemini embeddings: {e}")
                self.embedding_function = None
            
            try:
                from src.utils.llm_client import LLMClient
                self.llm = LLMClient(api_key=api_key)
                logger.info("🤖 LLM Client initialized for Self-RAG")
            except Exception as e:
                logger.warning(f"Could not initialize LLM Client: {e}")
                self.llm = None
        else:
            self.embedding_function = None
            self.llm = None

        # Initialize Knowledge Graph (v0.6.1+)
        self.graph = None
        if GRAPH_AVAILABLE:
            try:
                graph_db_path = os.path.join(os.path.dirname(db_path), 'knowledge_graph.db')
                if os.path.exists(graph_db_path):
                    self.graph = DiskKnowledgeGraph(graph_db_path)
                    logger.info(f"📊 Graph loaded: {self.graph.get_stats()['total_nodes']} nodes")
            except Exception as e:
                logger.warning(f"Could not initialize graph: {e}")

        from src.modules.librarian import Librarian
        self.librarian = Librarian()
        
        # Skill Manager & Approval System (Faza 1)
        from src.modules.skill_manager import SkillManager
        from src.modules.approval import ApprovalManager
        self.skill_manager = SkillManager(self.librarian)
        self.approval_manager = ApprovalManager(self.librarian)
        
        # Ostavljamo ove varijable kao None radi kompatibilnosti
        self.client = None
        self.collection = None
        
        # FastPath (Phase 9 - Rust-inspired simulation)
        try:
            from src.modules.fast_path import FastPath
            self.fast_path = FastPath(self.librarian)
            # Pokrećemo warmup u zasebnom threadu (sada sigurno uz lockove)
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
        Wrapper za upsert u sqlite-vec s validacijom i obogaćivanjem metapodataka.
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
            if not self.embedding_function:
                logger.error("❌ Embedding function not initialized in Oracle!")
                return
                
            try:
                embeddings = self.embedding_function(valid_docs)
            except Exception as e:
                logger.error(f"❌ Failed to generate embeddings in Oracle: {e}")
                return
                
            import sqlite_vec
            import json
            with self._lock:
                conn = self.librarian._get_sqlite_conn()
                cursor = conn.cursor()
                try:
                    for doc, meta, uid, emb in zip(valid_docs, valid_metas, valid_ids, embeddings):
                        project = meta.get("project", "default")
                        # 1. Spasi u vec_metadata
                        cursor.execute('''
                            INSERT OR REPLACE INTO vec_metadata (custom_id, document, metadata_json, project)
                            VALUES (?, ?, ?, ?)
                        ''', (uid, doc, json.dumps(meta), project))
                        
                        rowid = cursor.lastrowid
                        
                        # 2. Spasi u vec_items
                        cursor.execute('''
                            INSERT OR REPLACE INTO vec_items (rowid, embedding)
                            VALUES (?, ?)
                        ''', (rowid, sqlite_vec.serialize_float32(emb)))
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    logger.error(f"❌ Oracle safe_upsert failed: {e}")
                finally:
                    conn.close()

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
             print(f"DEBUG: Oracle: generating hypothesis for '{query}'...")
             vector_query = self.hypothesizer.generate_hypothesis(query)
        import sqlite_vec
        import json
        metrics.log_query()
        
        # Generiranje embeddinga za upit
        try:
            emb = self.embedding_function([vector_query])[0]
            emb_bytes = sqlite_vec.serialize_float32(emb)
        except Exception as e:
            logger.error(f"Failed to generate query embedding: {e}")
            emb_bytes = None
            
        vector_candidates = {
            'ids': [[]],
            'documents': [[]],
            'metadatas': [[]],
            'distances': [[]]
        }
        
        if emb_bytes:
            conn = self.librarian._get_sqlite_conn()
            cursor = conn.cursor()
            try:
                # Ako filtriramo po projektu, tražimo više kandidata kako bismo kompenzirali
                k_val = limit * 8 if project else limit * 4
                if project:
                    cursor.execute('''
                        SELECT m.custom_id, m.document, m.metadata_json, v.distance
                        FROM vec_items v
                        JOIN vec_metadata m ON v.rowid = m.rowid
                        WHERE v.embedding MATCH ? AND k = ? AND m.project = ?
                        ORDER BY v.distance ASC
                    ''', (emb_bytes, k_val, project))
                else:
                    cursor.execute('''
                        SELECT m.custom_id, m.document, m.metadata_json, v.distance
                        FROM vec_items v
                        JOIN vec_metadata m ON v.rowid = m.rowid
                        WHERE v.embedding MATCH ? AND k = ?
                        ORDER BY v.distance ASC
                    ''', (emb_bytes, k_val))
                    
                rows = cursor.fetchall()
                for row in rows:
                    custom_id, document, metadata_json, distance = row
                    try:
                        metadata = json.loads(metadata_json)
                    except:
                        metadata = {}
                    vector_candidates['ids'][0].append(custom_id)
                    vector_candidates['documents'][0].append(document)
                    vector_candidates['metadatas'][0].append(metadata)
                    vector_candidates['distances'][0].append(distance)
            except Exception as e:
                logger.error(f"sqlite-vec query failed: {e}")
            finally:
                conn.close()
        
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

    def get_graph_context(self, query: str, max_results: int = 5) -> Dict:
        """
        Dohvati graph context za upit (v0.6.1+).
        
        Args:
            query: Korisnički upit
            max_results: Maksimalan broj rezultata
            
        Returns:
            Dict s graph informacijama (classes, methods, files, dependencies)
        """
        if not self.graph:
            return {"available": False, "message": "Graph not initialized"}
        
        try:
            context = {
                "available": True,
                "stats": self.graph.get_stats(),
                "results": []
            }
            
            # Search for relevant nodes
            search_terms = query.lower().split()
            
            # Find classes matching query
            classes = self.graph.search_nodes(node_type='class', limit=max_results)
            classes = [c for c in classes if any(term in c.get('content', '').lower() for term in search_terms)]
            
            # Find functions matching query  
            funcs = self.graph.search_nodes(node_type='function', limit=max_results)
            funcs = [f for f in funcs if any(term in f.get('content', '').lower() for term in search_terms)]
            
            # Find files matching query
            files = self.graph.search_nodes(node_type='file', limit=max_results)
            files = [f for f in files if any(term in f.get('content', '').lower() for term in search_terms)]
            
            # Build context
            if classes:
                context["results"].append({
                    "type": "classes",
                    "count": len(classes),
                    "items": [{"name": c.get("content"), "file": c.get("metadata", {}).get("file", "")} for c in classes]
                })
            
            if funcs:
                context["results"].append({
                    "type": "functions", 
                    "count": len(funcs),
                    "items": [{"name": f.get("content")} for f in funcs]
                })
            
            if files:
                context["results"].append({
                    "type": "files",
                    "count": len(files),
                    "items": [{"path": f.get("content")} for f in files]
                })
            
            return context
            
        except Exception as e:
            return {"available": True, "error": str(e)}

    def ask(self, query, project=None, limit=10, silent=False, hyde=True, expand=False, self_rag=None):
        """
        Thread-safe metoda za upit s robusnim error handlingom i Fallback lancem.
        """
        try:
            with self._lock:
                if self_rag is None:
                    self_rag = os.getenv("KRONOS_SELF_RAG", "false").lower() == "true"
                
                self_rag_triggered = False
                self_rag_loops = 1
                self_rag_reason = ""

                # 00. Skill matching check (Faza 1)
                try:
                    threshold = float(os.getenv("KRONOS_SKILL_THRESHOLD", "0.5"))
                    matched_skill = self.skill_manager.match_skill(query, threshold=threshold)
                    if matched_skill:
                        logger.info(f"🎯 Query matched skill: {matched_skill['name']} (score: {matched_skill['score']:.4f})")
                        
                        # Create approval request
                        req_id = self.approval_manager.create_request(matched_skill['name'], query)
                        
                        # Wait for approval (timeout 30 seconds)
                        approved = self.approval_manager.wait_for_approval(req_id, timeout_sec=30)
                        
                        if approved:
                            return {
                                "status": "approved_skill",
                                "message": f"Skill '{matched_skill['name']}' approved for query '{query}'.",
                                "skill": matched_skill,
                                "approval_id": req_id,
                                "entities": [], "chunks": [], "pointers": [],
                                "method": "Smart-Context-Engine"
                            }
                        else:
                            return {
                                "status": "rejected_skill",
                                "message": f"Skill '{matched_skill['name']}' was rejected or timed out.",
                                "skill": matched_skill,
                                "approval_id": req_id,
                                "entities": [], "chunks": [], "pointers": [],
                                "method": "Smart-Context-Engine"
                            }
                except Exception as e:
                    logger.error(f"Error in skill matching pipeline: {e}")

                # 0. Fast Path (L0/L1) - High confidence exact matches
                if self.fast_path:
                    try:
                        fast_res = self.fast_path.search(query)
                        if fast_res and fast_res["confidence"] >= 0.9:
                            if not silent: 
                                # print(f"{Fore.GREEN}⚡ FastPath: {fast_res['type']} detektiran!{Style.RESET_ALL}")
                                pass
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

                # 1. Detektiraj tip upita i temporalne markere
                try:
                    query_type = self.detect_query_type(query)
                    temporal_keywords = [
                        "zadnje", "zadnji", "zadnjih", "nedavno", "latest", "recent", 
                        "novo", "update", "v0.", "v1.", "danas", "today", "promjene", 
                        "izmjene", "radili", "napravili", "status", "log"
                    ]
                    is_temporal = any(k in query.lower() for k in temporal_keywords)
                except Exception:
                    query_type = QueryType.SEMANTIC # Default fallback
                    is_temporal = False
                
                if not silent:
                     temporal_status = " [TEMPORAL BOOST]" if is_temporal else ""
                     # print(f"{Fore.CYAN}--- Tip upita: {query_type.value.upper()}{temporal_status} ---{Style.RESET_ALL}")
                
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
                
                # FTS FALLBACK / RECALL IMPROVEMENT
                # Ako imamo malo kandidata, pokušaj širi FTS (OR mode)
                if len(all_candidates) < 5:
                    try:
                        stemmed_q = query.lower()
                        wider_fts = self.librarian.search_fts(stemmed_q, project=project, limit=limit, mode="or")
                        for c in wider_fts:
                            path, content, start, end = c
                            all_candidates.append({
                                "id": f"fts_or_{path}_{hash(content)}",
                                "content": content,
                                "metadata": {"source": path, "start_line": start, "end_line": end},
                                "score": 0.5,
                                "method": "Keyword-Wide"
                            })
                    except Exception: pass

                # 3.5. Self-RAG Evaluation & Re-query
                if self_rag and self.llm and all_candidates:
                    try:
                        # Limit candidates to top 8 for evaluation to save tokens and time
                        eval_candidates = all_candidates[:8]
                        context_pieces = []
                        for idx, c in enumerate(eval_candidates):
                            source = c.get('metadata', {}).get('source', 'Unknown')
                            content_snippet = c.get('content', '')[:1000]
                            context_pieces.append(f"[{idx+1}] File: {source}\nContent:\n{content_snippet}\n---")
                        
                        context_text = "\n".join(context_pieces)
                        
                        prompt = f"""You are the Kronos Self-RAG Evaluator.
Your job is to determine if the retrieved codebase context is SUFFICIENT to answer the user query.

User Query: "{query}"

Retrieved Context:
{context_text}

Analyze the retrieved context. Is it sufficient to answer the user query? If not, what specific details are missing?
You MUST respond exactly in the following format:
STATUS: [SUFFICIENT or INSUFFICIENT]
REASON: [Brief explanation of why it is or isn't sufficient]
RE-QUERY: [If INSUFFICIENT, provide a single clean search query (keywords or phrases) to find the missing details. If SUFFICIENT, leave empty.]
"""
                        eval_response = self.llm.complete(prompt, model_name="gemini-2.0-flash")
                        
                        status = "SUFFICIENT"
                        re_query = ""
                        reason = ""
                        
                        for line in eval_response.split('\n'):
                            line_stripped = line.strip()
                            if line_stripped.startswith("STATUS:"):
                                status = line_stripped.replace("STATUS:", "").strip()
                            elif line_stripped.startswith("RE-QUERY:"):
                                re_query = line_stripped.replace("RE-QUERY:", "").strip()
                            elif line_stripped.startswith("REASON:"):
                                reason = line_stripped.replace("REASON:", "").strip()
                        
                        if status == "INSUFFICIENT" and re_query:
                            if not silent:
                                print(f"{Fore.CYAN}🤖 Self-RAG: Context evaluated as INSUFFICIENT. Reason: {reason}. Running RE-QUERY: '{re_query}'...{Style.RESET_ALL}")
                            
                            self_rag_triggered = True
                            self_rag_loops = 2
                            self_rag_reason = reason
                            
                            try:
                                retrieved_round2 = self._retrieve_candidates(re_query, project=project, limit=limit, hyde=False)
                                if retrieved_round2:
                                    # Add score boost and label method
                                    for c in retrieved_round2:
                                        c['score'] = c.get('score', 0.5) + 0.1
                                        c['method'] = c.get('method', '') + "-SelfRAG"
                                    all_candidates.extend(retrieved_round2)
                            except Exception as e:
                                print(f"{Fore.YELLOW}⚠️ Self-RAG: Re-query retrieval error: {e}{Style.RESET_ALL}")
                        else:
                            if not silent:
                                print(f"{Fore.GREEN}🤖 Self-RAG: Context evaluated as SUFFICIENT. Reason: {reason}{Style.RESET_ALL}")
                            self_rag_reason = reason
                    except Exception as e:
                        print(f"{Fore.YELLOW}⚠️ Self-RAG evaluation failure: {e}{Style.RESET_ALL}")

                # DEFENSE: Check candidates validity
                if not all_candidates:
                    if not silent: print(f"{Fore.YELLOW}WARNING: No candidates found for query.{Style.RESET_ALL}")
                    return self._empty_response("No relevant information found.")

                # 4. Deduplikacija i RANGIRANJE (Temporal Tuning)
                seen_ids = set()
                unique_candidates = []
                
                def calculate_boosted_score(c):
                    try:
                        base_score = float(c.get('score', 0.0))
                        if is_temporal:
                            # Pokušaj dobiti timestamp iz metapodataka
                            meta = c.get('metadata', {})
                            last_mod = float(meta.get('last_modified', 0))
                            current_time = datetime.now().timestamp()
                            age_seconds = current_time - last_mod
                            
                            # Temporalni boost: progresivno veći za novije stvari
                            # < 48h: 1.0, < 1 tjedan: 0.5, ostalo: 0
                            recency_boost = 1.0 if age_seconds < 172800 else (0.5 if age_seconds < 604800 else 0)
                            
                            # Utility score formula
                            boosted = (base_score * 0.3) + (recency_boost * 0.7)
                            c['utility_score'] = boosted # Store for classification phase
                            return boosted
                        
                        c['utility_score'] = base_score
                        return base_score
                    except Exception:
                        return 0.0

                sorted_cands = sorted(all_candidates, key=calculate_boosted_score, reverse=True)

                for cand in sorted_cands:
                    cid = cand.get('id')
                    if cid and cid not in seen_ids:
                        unique_candidates.append(cand)
                        seen_ids.add(cid)
                
                # 5. Decision Tree / Classification (Project Map Logic)
                final_chunks = []
                final_pointers = []
                final_entities = []
                query_keywords = self.extract_keywords(query)
                
                # Pragovi su sada fleksibilniji, pogotovo za temporalne upite
                chunk_threshold = 0.5 if is_temporal else 0.65
                pointer_threshold = 0.1 # Vrlo nisko da dobijemo "Project Map"
                
                for i, cand in enumerate(unique_candidates):
                    u_score = cand.get('utility_score', 0.0)
                    method = cand.get('method', 'unknown')
                    
                    if method == 'Entity':
                        final_entities.append(cand)
                        continue

                    # Ako je visoki score ili top rezultat kod temporalnog upita -> chunk
                    if u_score >= chunk_threshold or (is_temporal and i < 5):
                        final_chunks.append(cand)
                    # Sve ostalo što ima bilo kakav smisao ide u Pointers (Project Map)
                    elif u_score >= pointer_threshold:
                        p = self._candidate_to_pointer(cand, query_keywords)
                        if p: final_pointers.append(p)

                # 6. Clustering i Finalni odgovor
                final_pointers = self.cluster_pointers(final_pointers)

                if final_chunks or final_pointers or final_entities:
                    if final_chunks and final_pointers:
                        resp = self.build_mixed_response(final_chunks, final_pointers)
                    elif final_chunks:
                        resp = self.build_chunk_response(final_chunks)
                    else:
                        resp = self.build_pointer_response(final_pointers)
                else:
                    # AMBIGUITY HANDLING: Ako nema rezultata, a upit spominje projekt
                    project_markers = ["projekt", "project", "ovom", "this", "ovi"]
                    if any(m in query.lower() for m in project_markers):
                        # Dohvati popis svih projekata iz baze
                        try:
                            import sqlite3
                            conn = self.librarian._get_sqlite_conn()
                            cursor = conn.cursor()
                            cursor.execute("SELECT DISTINCT project FROM knowledge_fts WHERE project IS NOT NULL")
                            projects = [row[0] for row in cursor.fetchall()]
                            conn.close()
                            
                            if projects:
                                return {
                                    "status": "ambiguous",
                                    "message": f"Nisam siguran na koji projekt misliš. U bazi imam: {', '.join(projects)}.",
                                    "projects": projects,
                                    "entities": [], "chunks": [], "pointers": []
                                }
                        except Exception: pass

                    # FALLBACK: Probaj globalno ako je filter bio postavljen
                    if project:
                        return self.ask(query, project=None, limit=limit, silent=silent)
                    
                    resp = self._empty_response("No relevant information found.")

                # Add extra fields for debugging/backward compatibility
                resp["entities"] = final_entities
                resp["query_type"] = query_type.value
                resp["method"] = "Hybrid-Pointer-System"
                resp["self_rag"] = {
                    "triggered": self_rag_triggered,
                    "loops": self_rag_loops,
                    "reason": self_rag_reason
                }
                
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
