"""
Disk-Based Knowledge Graph za Kronos v0.6.1

SQLite-based graf storage za low-RAM knowledge graph.
Omogućuje cross-project pattern matching i reuse.
"""

import sqlite3
import json
import os
from typing import List, Dict, Optional, Any
from datetime import datetime


class DiskKnowledgeGraph:
    """
    Disk-based graf sa SQLite backend-om.
    Optimiziran za low RAM usage i velike grafove.
    """
    
    def __init__(self, db_path: str = "data/knowledge_graph.db"):
        self.db_path = db_path
        
        # Ensure directory exists
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
        
        self.conn = sqlite3.connect(db_path, timeout=30.0, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        
        # Performance pragmas
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA cache_size=10000")
        
        self._init_schema()
    
    def _init_schema(self):
        """Kreira tablice ako ne postoje."""
        try:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS graph_nodes (
                    node_id TEXT PRIMARY KEY,
                    node_type TEXT NOT NULL,
                    content TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS graph_edges (
                    edge_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_node TEXT NOT NULL,
                    to_node TEXT NOT NULL,
                    relationship_type TEXT NOT NULL,
                    metadata TEXT,
                    weight REAL DEFAULT 1.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(from_node) REFERENCES graph_nodes(node_id),
                    FOREIGN KEY(to_node) REFERENCES graph_nodes(node_id)
                )
            """)
            
            # Indeksi za performance
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_from_node ON graph_edges(from_node)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_to_node ON graph_edges(to_node)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_rel_type ON graph_edges(relationship_type)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_node_type ON graph_nodes(node_type)")
        except sqlite3.OperationalError as e:
            print(f"  ⚠️ Schema creation error: {e}")
    
    def add_node(self, node_id: str, node_type: str, content: str = None, metadata: dict = None):
        """Dodaj node u graf."""
        try:
            self.conn.execute("""
                INSERT OR REPLACE INTO graph_nodes (node_id, node_type, content, metadata)
                VALUES (?, ?, ?, ?)
            """, (node_id, node_type, content, json.dumps(metadata or {})))
        except sqlite3.OperationalError as e:
            print(f"  ⚠️ DB Error adding node: {e}")
    
    def add_edge(self, from_node: str, to_node: str, rel_type: str, metadata: dict = None, weight: float = 1.0):
        """Dodaj vezu između nodova."""
        try:
            # Only add nodes if they don't exist
            existing_from = self.get_node(from_node)
            existing_to = self.get_node(to_node)
            
            if not existing_from:
                self.conn.execute("""
                    INSERT INTO graph_nodes (node_id, node_type, content, metadata)
                    VALUES (?, ?, ?, ?)
                """, (from_node, "unknown", None, "{}"))
            
            if not existing_to:
                self.conn.execute("""
                    INSERT INTO graph_nodes (node_id, node_type, content, metadata)
                    VALUES (?, ?, ?, ?)
                """, (to_node, "unknown", None, "{}"))
            
            self.conn.execute("""
                INSERT INTO graph_edges (from_node, to_node, relationship_type, metadata, weight)
                VALUES (?, ?, ?, ?, ?)
            """, (from_node, to_node, rel_type, json.dumps(metadata or {}), weight))
        except sqlite3.OperationalError as e:
            print(f"  ⚠️ DB Error adding edge: {e}")
    
    def get_node(self, node_id: str) -> Optional[Dict]:
        """Dohvati single node."""
        cursor = self.conn.execute(
            "SELECT * FROM graph_nodes WHERE node_id = ?", 
            (node_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_neighbors(self, node_id: str, rel_type: str = None, direction: str = "outgoing") -> List[Dict]:
        """
        Dohvati susjedne nodove.
        
        Args:
            node_id: ID početnog noda
            rel_type: Filter po tipu relacije (opciono)
            direction: 'outgoing', 'incoming', ili 'both'
        """
        if direction == "outgoing":
            query = """
                SELECT n.*, e.relationship_type, e.weight
                FROM graph_edges e
                JOIN graph_nodes n ON e.to_node = n.node_id
                WHERE e.from_node = ?
            """
        elif direction == "incoming":
            query = """
                SELECT n.*, e.relationship_type, e.weight
                FROM graph_edges e
                JOIN graph_nodes n ON e.from_node = n.node_id
                WHERE e.to_node = ?
            """
        else:  # both
            query = """
                SELECT n.*, e.relationship_type, e.weight
                FROM graph_edges e
                JOIN graph_nodes n ON (e.to_node = n.node_id OR e.from_node = n.node_id)
                WHERE (e.from_node = ? OR e.to_node = ?)
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
        from collections import deque
        
        queue = deque([(start_id, [start_id])])
        visited = {start_id}
        
        while queue:
            current, path = queue.popleft()
            
            if len(path) > max_depth:
                continue
            
            if current == end_id:
                return path
            
            # Dohvati susjedne nodove (samo IDs za manju RAM usage)
            neighbors = self.get_neighbors(current, direction="outgoing")
            
            for neighbor in neighbors:
                neighbor_id = neighbor['node_id']
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append((neighbor_id, path + [neighbor_id]))
        
        return None  # Path not found
    
    def get_subgraph(self, node_id: str, depth: int = 2) -> Dict:
        """
        Dohvati subgraf oko određenog noda (za context).
        Iterativno učitava nodove s diska po potrebi.
        """
        nodes = {}
        edges = []
        to_explore = [(node_id, 0)]
        visited = set()
        
        while to_explore:
            current_id, current_depth = to_explore.pop(0)
            
            if current_id in visited or current_depth > depth:
                continue
            
            visited.add(current_id)
            
            # Dohvati node details
            node_data = self.conn.execute(
                "SELECT * FROM graph_nodes WHERE node_id = ?", 
                (current_id,)
            ).fetchone()
            
            if node_data:
                nodes[current_id] = dict(node_data)
            
            # Dohvati edges
            outgoing_edges = self.conn.execute("""
                SELECT * FROM graph_edges WHERE from_node = ?
            """, (current_id,)).fetchall()
            
            for edge in outgoing_edges:
                edge_dict = dict(edge)
                edges.append(edge_dict)
                
                # Dodaj destinacijski node za sljedeću iteraciju
                if current_depth + 1 <= depth:
                    to_explore.append((edge_dict['to_node'], current_depth + 1))
        
        return {"nodes": nodes, "edges": edges}
    
    def search_nodes(self, node_type: str = None, content_query: str = None, limit: int = 10) -> List[Dict]:
        """
        Pretraži nodove po tipu ili sadržaju.
        """
        query = "SELECT * FROM graph_nodes WHERE 1=1"
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
        """Dohvati sve nodove povezane s određenim tipom relacije."""
        return self.get_neighbors(node_id, rel_type=rel_type, direction="both")
    
    def get_stats(self) -> Dict:
        """Vrati statistike grafa."""
        node_count = self.conn.execute("SELECT COUNT(*) as count FROM graph_nodes").fetchone()['count']
        edge_count = self.conn.execute("SELECT COUNT(*) as count FROM graph_edges").fetchone()['count']
        
        # Broj po tipovima
        node_types = self.conn.execute("""
            SELECT node_type, COUNT(*) as count 
            FROM graph_nodes 
            GROUP BY node_type
        """).fetchall()
        
        rel_types = self.conn.execute("""
            SELECT relationship_type, COUNT(*) as count 
            FROM graph_edges 
            GROUP BY relationship_type
        """).fetchall()
        
        return {
            "total_nodes": node_count,
            "total_edges": edge_count,
            "node_types": {row['node_type']: row['count'] for row in node_types},
            "relationship_types": {row['relationship_type']: row['count'] for row in rel_types}
        }
    
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
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Utility function za brzo korištenje
def get_graph(db_path: str = "data/knowledge_graph.db") -> DiskKnowledgeGraph:
    """Kreiraj i vrati graph instancu."""
    return DiskKnowledgeGraph(db_path)
