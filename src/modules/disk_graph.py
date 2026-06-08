"""
Disk-Based Knowledge Graph za Kronos v0.6.1

SQLite-based graf storage za low-RAM knowledge graph.
Omogućuje cross-project pattern matching i reuse.
"""

import sqlite3
import json
import os
import sys
from typing import List, Dict, Optional, Any
from datetime import datetime

# Path optimization - add current dir to sys.path for rust_graph.pyd
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    import rust_graph
    USE_RUST = True
except ImportError:
    USE_RUST = False


class DiskKnowledgeGraph:
    """
    Disk-based graf sa SQLite backend-om.
    Optimiziran za low RAM usage i velike grafove.
    Sada koristi Rust engine za brze pretrage (ako je dostupan).
    """
    
    def __init__(self, db_path: str = "data/knowledge_graph.db"):
        self.db_path = db_path
        self.use_rust = USE_RUST
        self.rust_engine = None
        
        # Ensure directory exists
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
        
        if self.use_rust:
            try:
                # Resolve absolute path for Rust
                abs_db_path = os.path.abspath(db_path)
                self.rust_engine = rust_graph.RustGraphEngine(abs_db_path)
                print(f"  🦀 Rust Graph Engine aktivan (DB: {db_path})")
            except Exception as e:
                print(f"  ⚠️ Greška pri inicijalizaciji Rust engine-a: {e}")
                self.use_rust = False
        
        self.conn = sqlite3.connect(db_path, timeout=30.0, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        
        # Performance pragmas
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA cache_size=10000")
        
        self._init_schema()

    def _estimate_query_weight(self, node_id: str, depth: int) -> int:
        """
        Procjenjuje 'težinu' upita na temelju fanout-a početnog noda i dubine.
        Vraća broj koji predstavlja procijenjeni broj operacija.
        """
        try:
            res = self.conn.execute("SELECT COUNT(*) FROM graph_edges WHERE from_node = ?", (node_id,)).fetchone()
            fanout = res[0] if res else 0
            # Jednostavna formula: fanout * (2^depth) za procijenu rasta
            return fanout * (2 ** (depth - 1))
        except Exception:
            return 0
    
    def _init_schema(self):
        """Kreira tablice ako ne postoje ili ih migrira."""
        try:
            # Provjera sheme za graph_nodes
            cursor = self.conn.cursor()
            cursor.execute("PRAGMA table_info(graph_nodes)")
            columns = {row['name']: dict(row) for row in cursor.fetchall()}
            
            needs_nodes_migration = False
            if columns:
                # Ako postoji tablica, provjeri ima li 'valid_from' i je li 'node_id' primarni ključ
                if 'valid_from' not in columns:
                    needs_nodes_migration = True
                elif columns.get('node_id', {}).get('pk', 0) == 1:
                    needs_nodes_migration = True
            
            if needs_nodes_migration:
                print("  📦 Migriram graph_nodes tablicu na temporalnu shemu...")
                # SQLite ne podržava drop primarnog ključa pa radimo backup-and-recreate
                self.conn.execute("ALTER TABLE graph_nodes RENAME TO graph_nodes_old")
                self.conn.execute("""
                    CREATE TABLE graph_nodes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        node_id TEXT NOT NULL,
                        node_type TEXT NOT NULL,
                        content TEXT,
                        metadata TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        valid_from TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        valid_to TIMESTAMP
                    )
                """)
                # Kopiraj podatke
                self.conn.execute("""
                    INSERT INTO graph_nodes (node_id, node_type, content, metadata, created_at, valid_from, valid_to)
                    SELECT node_id, node_type, content, metadata, created_at, created_at, NULL
                    FROM graph_nodes_old
                """)
                self.conn.execute("DROP TABLE graph_nodes_old")
                print("  ✅ Migracija graph_nodes završena.")
            else:
                # Kreiraj ako ne postoji
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS graph_nodes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        node_id TEXT NOT NULL,
                        node_type TEXT NOT NULL,
                        content TEXT,
                        metadata TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        valid_from TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        valid_to TIMESTAMP
                    )
                """)

            # Provjera i migracija za graph_edges
            cursor.execute("PRAGMA table_info(graph_edges)")
            edge_columns = {row['name']: dict(row) for row in cursor.fetchall()}
            
            if edge_columns:
                if 'valid_from' not in edge_columns:
                    print("  📦 Dodajem temporalne stupce u graph_edges...")
                    self.conn.execute("ALTER TABLE graph_edges ADD COLUMN valid_from TIMESTAMP")
                    self.conn.execute("ALTER TABLE graph_edges ADD COLUMN valid_to TIMESTAMP")
                    self.conn.execute("UPDATE graph_edges SET valid_from = created_at")
                    print("  ✅ Migracija graph_edges završena.")
            else:
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS graph_edges (
                        edge_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        from_node TEXT NOT NULL,
                        to_node TEXT NOT NULL,
                        relationship_type TEXT NOT NULL,
                        metadata TEXT,
                        weight REAL DEFAULT 1.0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        valid_from TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        valid_to TIMESTAMP
                    )
                """)

            # Indeksi za performance
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_from_node ON graph_edges(from_node)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_to_node ON graph_edges(to_node)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_rel_type ON graph_edges(relationship_type)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_node_type ON graph_nodes(node_type)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_node_id ON graph_nodes(node_id)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_node_valid_to ON graph_nodes(valid_to)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_edge_valid_to ON graph_edges(valid_to)")
            
        except sqlite3.OperationalError as e:
            print(f"  ⚠️ Schema creation/migration error: {e}")
    
    def add_node(self, node_id: str, node_type: str, content: str = None, metadata: dict = None):
        """Dodaj node u graf s temporalnim praćenjem."""
        try:
            # Provjeri postoji li već aktivni čvor s istim node_id
            cursor = self.conn.execute(
                "SELECT content, metadata FROM graph_nodes WHERE node_id = ? AND valid_to IS NULL",
                (node_id,)
            )
            row = cursor.fetchone()
            
            new_metadata_str = json.dumps(metadata or {})
            timestamp = datetime.now().isoformat()
            
            if row:
                existing_content = row['content']
                existing_metadata = row['metadata']
                
                # Ako su podaci identični, preskoči unos
                if existing_content == content and existing_metadata == new_metadata_str:
                    return
                
                # Ako su različiti, soft-deletaj aktivni čvor
                self.conn.execute(
                    "UPDATE graph_nodes SET valid_to = ? WHERE node_id = ? AND valid_to IS NULL",
                    (timestamp, node_id)
                )
            
            # Umetni novu verziju
            self.conn.execute("""
                INSERT INTO graph_nodes (node_id, node_type, content, metadata, valid_from, valid_to)
                VALUES (?, ?, ?, ?, ?, NULL)
            """, (node_id, node_type, content, new_metadata_str, timestamp))
            
        except sqlite3.OperationalError as e:
            print(f"  ⚠️ DB Error adding node: {e}")
    
    def add_edge(self, from_node: str, to_node: str, rel_type: str, metadata: dict = None, weight: float = 1.0):
        """Dodaj vezu između nodova s temporalnim praćenjem."""
        try:
            # Provjeri i osiguraj postojanje aktivnih čvorova
            existing_from = self.get_node(from_node)
            existing_to = self.get_node(to_node)
            
            timestamp = datetime.now().isoformat()
            
            if not existing_from:
                self.add_node(from_node, "unknown", None, {})
            
            if not existing_to:
                self.add_node(to_node, "unknown", None, {})
                
            # Provjeri postoji li već aktivna veza
            cursor = self.conn.execute("""
                SELECT edge_id, metadata, weight FROM graph_edges 
                WHERE from_node = ? AND to_node = ? AND relationship_type = ? AND valid_to IS NULL
            """, (from_node, to_node, rel_type))
            row = cursor.fetchone()
            
            new_metadata_str = json.dumps(metadata or {})
            
            if row:
                existing_metadata = row['metadata']
                existing_weight = row['weight']
                
                # Ako su podaci identični, preskoči
                if existing_metadata == new_metadata_str and existing_weight == weight:
                    return
                    
                # Ako su različiti, soft-deletaj staru vezu
                edge_id = row['edge_id']
                self.conn.execute(
                    "UPDATE graph_edges SET valid_to = ? WHERE edge_id = ?",
                    (timestamp, edge_id)
                )
                
            # Umetni novu verziju
            self.conn.execute("""
                INSERT INTO graph_edges (from_node, to_node, relationship_type, metadata, weight, valid_from, valid_to)
                VALUES (?, ?, ?, ?, ?, ?, NULL)
            """, (from_node, to_node, rel_type, new_metadata_str, weight, timestamp))
            
        except sqlite3.OperationalError as e:
            print(f"  ⚠️ DB Error adding edge: {e}")
    
    def get_node(self, node_id: str) -> Optional[Dict]:
        """Dohvati single aktivni node."""
        cursor = self.conn.execute(
            "SELECT * FROM graph_nodes WHERE node_id = ? AND valid_to IS NULL ORDER BY valid_from DESC LIMIT 1", 
            (node_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_neighbors(self, node_id: str, rel_type: str = None, direction: str = "outgoing") -> List[Dict]:
        """
        Dohvati susjedne aktivne nodove preko aktivnih veza.
        """
        if direction == "outgoing":
            query = """
                SELECT n.*, e.relationship_type, e.weight
                FROM graph_edges e
                JOIN graph_nodes n ON e.to_node = n.node_id
                WHERE e.from_node = ? AND e.valid_to IS NULL AND n.valid_to IS NULL
            """
        elif direction == "incoming":
            query = """
                SELECT n.*, e.relationship_type, e.weight
                FROM graph_edges e
                JOIN graph_nodes n ON e.from_node = n.node_id
                WHERE e.to_node = ? AND e.valid_to IS NULL AND n.valid_to IS NULL
            """
        else:  # both
            query = """
                SELECT n.*, e.relationship_type, e.weight
                FROM graph_edges e
                JOIN graph_nodes n ON (e.to_node = n.node_id OR e.from_node = n.node_id)
                WHERE (e.from_node = ? OR e.to_node = ?) AND e.valid_to IS NULL AND n.valid_to IS NULL
            """
        
        params = [node_id] if direction != "both" else [node_id, node_id]
        
        if rel_type:
            query += " AND e.relationship_type = ?"
            params.append(rel_type)
        
        cursor = self.conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def find_path(self, start_id: str, end_id: str, max_depth: int = 5) -> Optional[List[str]]:
        """
        Breadth-First Search za pronalazak shortest path.
        Disk-based implementacija (ne učitava cijeli graf u RAM).
        """
        if self.use_rust:
            try:
                return self.rust_engine.find_path(start_id, end_id, max_depth)
            except Exception as e:
                print(f"  ⚠️ Rust Path Error: {e}")

        from collections import deque
        
        queue = deque([(start_id, [start_id])])
        visited = {start_id}
        
        while queue:
            current, path = queue.popleft()
            
            if len(path) > max_depth:
                continue
            
            if current == end_id:
                return path
            
            # Dohvati susjedne nodove (samo aktivne)
            neighbors = self.conn.execute(
                "SELECT to_node FROM graph_edges WHERE from_node = ? AND valid_to IS NULL", 
                (current,)
            ).fetchall()
            
            for (neighbor_id,) in neighbors:
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append((neighbor_id, path + [neighbor_id]))
        
        return None  # Path not found
    
    def get_subgraph(self, node_id: str, depth: int = 2) -> Dict:
        """
        Dohvati aktivni subgraf oko određenog noda.
        """
        weight = self._estimate_query_weight(node_id, depth)
        node_ids = []

        if self.use_rust and weight > 15: 
            try:
                node_ids = self.rust_engine.get_related(node_id, depth)
            except Exception as e:
                print(f"  ⚠️ Rust Traversal Error: {e}")
        
        if not node_ids:
            # Python Traversal (BFS)
            visited = {node_id}
            queue = [(node_id, 0)]
            while queue:
                curr_id, d = queue.pop(0)
                if d < depth:
                    neighbors = self.conn.execute(
                        "SELECT to_node FROM graph_edges WHERE from_node = ? AND valid_to IS NULL", 
                        (curr_id,)
                    ).fetchall()
                    for (n_id,) in neighbors:
                        if n_id not in visited:
                            visited.add(n_id)
                            queue.append((n_id, d + 1))
            node_ids = list(visited)

        return self._hydrate_subgraph(node_ids)

    def _hydrate_subgraph(self, node_ids: List[str]) -> Dict:
        """Hydration (Selective Fetch): dohvaća pune podatke za listu ID-ova (samo aktivne)."""
        if not node_ids:
            return {"nodes": {}, "edges": []}
            
        nodes = {}
        edges = []
        
        # Batch fetch nodes (samo aktivni)
        placeholders = ",".join(["?"] * len(node_ids))
        cursor = self.conn.execute(
            f"SELECT * FROM graph_nodes WHERE node_id IN ({placeholders}) AND valid_to IS NULL", 
            node_ids
        )
        for row in cursor.fetchall():
            nodes[row['node_id']] = dict(row)
            
        # Batch fetch edges izmedu tih nodova (samo aktivne)
        cursor = self.conn.execute(
            f"SELECT * FROM graph_edges WHERE from_node IN ({placeholders}) AND valid_to IS NULL", 
            node_ids
        )
        for row in cursor.fetchall():
            edge_dict = dict(row)
            if edge_dict['to_node'] in nodes:
                edges.append(edge_dict)
                
        return {"nodes": nodes, "edges": edges}

    def get_related_nodes(self, node_id: str, depth: int = 2) -> List[str]:
        """Dohvati listu povezanih aktivnih node ID-ova (Traversal)."""
        weight = self._estimate_query_weight(node_id, depth)
        
        if self.use_rust and weight > 15:
            try:
                return self.rust_engine.get_related(node_id, depth)
            except Exception:
                pass 

        # Python fallback BFS (samo aktivni)
        visited = {node_id}
        queue = [(node_id, 0)]
        while queue:
            curr_id, d = queue.pop(0)
            if d < depth:
                neighbors = self.conn.execute(
                    "SELECT to_node FROM graph_edges WHERE from_node = ? AND valid_to IS NULL", 
                    (curr_id,)
                ).fetchall()
                for (n_id,) in neighbors:
                    if n_id not in visited:
                        visited.add(n_id)
                        queue.append((n_id, d + 1))
        return list(visited)
    
    def search_nodes(self, node_type: str = None, content_query: str = None, limit: int = 10) -> List[Dict]:
        """
        Pretraži aktivne nodove po tipu ili sadržaju.
        """
        query = "SELECT * FROM graph_nodes WHERE valid_to IS NULL"
        params = []
        
        if node_type:
            query += " AND node_type = ?"
            params.append(node_type)
        
        if content_query:
            query += " AND content LIKE ?"
            params.append(f"%{content_query}%")
        
        query += f" LIMIT {limit}"
        
        cursor = self.conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_related_by_type(self, node_id: str, rel_type: str) -> List[Dict]:
        """Dohvati sve aktivne nodove povezane s određenim tipom relacije."""
        return self.get_neighbors(node_id, rel_type=rel_type, direction="both")
    
    def get_stats(self) -> Dict:
        """Vrati statistike grafa (aktivne i povijesne)."""
        node_count_active = self.conn.execute("SELECT COUNT(*) as count FROM graph_nodes WHERE valid_to IS NULL").fetchone()['count']
        node_count_total = self.conn.execute("SELECT COUNT(*) as count FROM graph_nodes").fetchone()['count']
        edge_count_active = self.conn.execute("SELECT COUNT(*) as count FROM graph_edges WHERE valid_to IS NULL").fetchone()['count']
        edge_count_total = self.conn.execute("SELECT COUNT(*) as count FROM graph_edges").fetchone()['count']
        
        node_types = self.conn.execute("""
            SELECT node_type, COUNT(*) as count 
            FROM graph_nodes 
            WHERE valid_to IS NULL
            GROUP BY node_type
        """).fetchall()
        
        rel_types = self.conn.execute("""
            SELECT relationship_type, COUNT(*) as count 
            FROM graph_edges 
            WHERE valid_to IS NULL
            GROUP BY relationship_type
        """).fetchall()
        
        return {
            "active_nodes": node_count_active,
            "total_historical_nodes": node_count_total,
            "active_edges": edge_count_active,
            "total_historical_edges": edge_count_total,
            "total_nodes": node_count_active,  # Za backward kompatibilnost
            "total_edges": edge_count_active,  # Za backward kompatibilnost
            "node_types": {row['node_type']: row['count'] for row in node_types},
            "relationship_types": {row['relationship_type']: row['count'] for row in rel_types}
        }
        
    def soft_delete_node(self, node_id: str):
        """Soft-deletaj čvor i sve njegove aktivne veze."""
        try:
            timestamp = datetime.now().isoformat()
            self.conn.execute(
                "UPDATE graph_nodes SET valid_to = ? WHERE node_id = ? AND valid_to IS NULL",
                (timestamp, node_id)
            )
            self.conn.execute("""
                UPDATE graph_edges SET valid_to = ? 
                WHERE (from_node = ? OR to_node = ?) AND valid_to IS NULL
            """, (timestamp, node_id, node_id))
        except sqlite3.OperationalError as e:
            print(f"  ⚠️ DB Error soft-deleting node {node_id}: {e}")

    def soft_delete_edge_by_id(self, edge_id: int):
        """Soft-deletaj vezu po ID-u."""
        try:
            timestamp = datetime.now().isoformat()
            self.conn.execute(
                "UPDATE graph_edges SET valid_to = ? WHERE edge_id = ?",
                (timestamp, edge_id)
            )
        except sqlite3.OperationalError as e:
            print(f"  ⚠️ DB Error soft-deleting edge {edge_id}: {e}")
    
    def clear(self):
        """Obriši sav sadržaj grafa."""
        try:
            self.conn.execute("DELETE FROM graph_edges")
            self.conn.execute("DELETE FROM graph_nodes")
            self.conn.execute("VACUUM")
        except sqlite3.OperationalError as e:
            print(f"  ⚠️ Clear error: {e}")
    
    def close(self):
        """Zatvori konekciju."""
        self.conn.close()
        self.rust_engine = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Utility function za brzo korištenje
def get_graph(db_path: str = "data/knowledge_graph.db") -> DiskKnowledgeGraph:
    """Kreiraj i vrati graph instancu."""
    return DiskKnowledgeGraph(db_path)
