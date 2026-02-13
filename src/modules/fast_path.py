import os
import re
import threading
from typing import List, Dict, Any, Optional

class PrefixTrie:
    """Simulacija Rust PrefixTrie-a u Pythonu."""
    def __init__(self):
        self.root = {"docs": [], "children": {}}

    def insert(self, key: str, document: Dict[str, Any]):
        node = self.root
        for char in key.lower():
            if char not in node["children"]:
                node["children"][char] = {"docs": [], "children": {}}
            node = node["children"][char]
        # Spremi dokument u čvor (možemo limitirati broj da ne raste previše)
        if len(node["docs"]) < 10:
            node["docs"].append(document)

    def search(self, prefix: str) -> List[Dict[str, Any]]:
        node = self.root
        for char in prefix.lower():
            if char not in node["children"]:
                return []
            node = node["children"][char]
        
        return self._collect_recursive(node, limit=10)

    def _collect_recursive(self, node: Dict[str, Any], limit: int) -> List[Dict[str, Any]]:
        results = list(node["docs"])
        for char in node["children"]:
            if len(results) >= limit:
                break
            results.extend(self._collect_recursive(node["children"][char], limit - len(results)))
        return results[:limit]

class FastPath:
    """
    Simulacija Rust Kronos strukture za brzu pretragu.
    Sada koristi pravi Rust modul (kronos_core) ako je dostupan.
    """
    def __init__(self, librarian=None):
        self.librarian = librarian
        self.is_warmed_up = False
        self._lock = threading.Lock() # Thread safety for Rust FFI
        
        # Baseline structures
        self.exact_index: Dict[str, Dict[str, Any]] = {}
        self.prefix_trie = PrefixTrie()

        # Rust Engine (Phase 9 - Real Rust)
        self.rust_engine = None
        try:
            from src.modules.kronos_core import FastPath as RustFastPath
            self.rust_engine = RustFastPath()
            # print("--- FastPath: Rust engine ucitan! ---")
        except ImportError:
            # print("INFO: FastPath: Rust engine nije pronadjen, koristim Python fallback.")
            pass

    def warmup(self):
        """Puni memorijski indeks najvažnijim entitetima radi brzine."""
        if not self.librarian:
            return
            
        print("--- FastPath: Zagrijavam memorijski indeks... ---")
        # 1. Dohvati sve entitete (odluke, naslove, emailove)
        # Ovdje simuliramo punjenje iz SQLite-a
        stats = self.librarian.get_stats()
        if stats.get('entities'):
            # Koristimo direktan upit za brzinu
            import sqlite3
            conn = sqlite3.connect(self.librarian.meta_path)
            cursor = conn.cursor()
            cursor.execute("SELECT type, content, file_path, project FROM entities LIMIT 1000")
            rows = cursor.fetchall()
            conn.close()

            for etype, content, path, project in rows:
                if content is None:
                    continue
                
                doc = {
                    "content": content,
                    "metadata": {"source": path, "project": project, "type": etype},
                    "score": 1.0
                }

                # Index za literal match (emailovi, kratki stringovi)
                content_lower = content.lower().strip()
                if len(content) < 100:
                    self.exact_index[content_lower] = doc
                    if self.rust_engine:
                        with self._lock:
                            self.rust_engine.insert(content_lower, content)
                
                # Index za prefix i ključne riječi (pomaže da 'T034' nadje cijelu rečenicu)
                words = content.split()
                for word in words: 
                    word_clean = word.lower().strip().strip(".,!?\"'()")
                    if len(word_clean) > 2:
                        self.prefix_trie.insert(word_clean, doc)
                        # Također dodajemo važne riječi u Rust engine kao ključeve
                        if self.rust_engine and (len(word_clean) > 3 or any(c.isdigit() for c in word_clean)):
                            with self._lock:
                                self.rust_engine.insert(word_clean, content)
                
                if "@" in content: # Specijalno za emailove
                    self.prefix_trie.insert(content_lower, doc)
                    if self.rust_engine:
                        with self._lock:
                            self.rust_engine.insert(content_lower, content)

            # 2. DODATNO: Indexiraj imena projekata kao super-brze ulaze
            from src.modules.librarian import Librarian
            lib = Librarian()
            proj_stats = lib.get_project_stats()
            for p_name in proj_stats.keys():
                if p_name:
                    p_name_lower = p_name.lower()
                    if self.rust_engine:
                        with self._lock:
                            self.rust_engine.insert(p_name_lower, f"Projekt: {p_name}")
                    
                    p_doc = {
                        "content": f"Projekt: {p_name}",
                        "metadata": {"project": p_name, "type": "PROJECT_METADATA"},
                        "score": 1.0
                    }
                    self.exact_index[p_name_lower] = p_doc
                    self.prefix_trie.insert(p_name_lower, p_doc)

        self.is_warmed_up = True
        # with self._lock:
        #     count = self.rust_engine.__len__() if self.rust_engine else len(self.exact_index)
        # print(f"DONE: FastPath zagrijan s {count} literalnih ulaza.")

    def search(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Glavna pretraga brze staze.
        Vraća rezultate samo ako je 'confidence' maksimalan.
        """
        if self.rust_engine:
            with self._lock:
                rust_res = self.rust_engine.search(query)
            
            if rust_res:
                print(f"DEBUG: FastPath Rust Match found for '{query}': {rust_res.get('type')}")
                return {
                    "type": rust_res.get("type", "ExactMatch"),
                    "confidence": rust_res.get("confidence", 1.0),
                    "data": {
                        "entities": [{
                            "content": rust_res.get("content", ""),
                            "metadata": {"source": "rust_fast_path"},
                            "score": rust_res.get("confidence", 1.0)
                        }],
                        "chunks": []
                    }
                }
            return None

        normalized_query = query.lower().strip()

        # 1. L0: Exact Match (0.01ms)
        if normalized_query in self.exact_index:
            res = self.exact_index[normalized_query]
            print(f"DEBUG: FastPath ExactMatch found for '{normalized_query}'")
            return {
                "type": "ExactMatch",
                "confidence": 1.0,
                "data": {"entities": [res], "chunks": []}
            }

        # 2. L1: Email/Literal detection (Regex fast path)
        email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', query)
        if email_match:
            email = email_match.group(0).lower()
            if email in self.exact_index:
                return {
                    "type": "LiteralEmailMatch",
                    "confidence": 1.0,
                    "data": {"entities": [self.exact_index[email]], "chunks": []}
                }

        # 3. L1: Prefix Search (0.1ms)
        if len(normalized_query) >= 3:
            prefix_results = self.prefix_trie.search(normalized_query)
            if prefix_results:
                # Provjeri je li prvi rezultat baš dobar (npr. query je cijeli prefiks prve riječi)
                first = prefix_results[0]
                if first["content"].lower().startswith(normalized_query):
                    print(f"DEBUG: FastPath PrefixMatch found for '{normalized_query}' -> {first['content']}")
                    return {
                        "type": "PrefixMatch",
                        "confidence": 0.9, # Visoko ali ne 1.0 (možda ipak treba semantic)
                        "data": {"entities": prefix_results[:3], "chunks": []}
                    }

        return None
