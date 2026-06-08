use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use rusqlite::{params, Connection, Result};
use std::collections::HashMap;

#[pyclass]
pub struct RustGraphEngine {
    conn: Connection,
}

#[pymethods]
impl RustGraphEngine {
    #[new]
    pub fn new(db_path: String) -> PyResult<Self> {
        let conn = Connection::open(&db_path)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("DB Open Error: {}", e)))?;
        
        Ok(RustGraphEngine { conn })
    }

    /// BFS traversal using Recursive CTE. Returns unique node IDs.
    pub fn get_related(&self, node_id: String, depth: usize) -> PyResult<Vec<String>> {
        let mut stmt = self.conn.prepare(
            "WITH RECURSIVE bfs AS (
                SELECT to_node, 1 as current_depth
                FROM graph_edges
                WHERE from_node = ?1 AND valid_to IS NULL
                UNION
                SELECT e.to_node, bfs.current_depth + 1
                FROM graph_edges e
                INNER JOIN bfs ON e.from_node = bfs.to_node
                WHERE bfs.current_depth < ?2 AND e.valid_to IS NULL
            )
            SELECT DISTINCT to_node FROM bfs"
        ).map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Prepare Error: {}", e)))?;

        let rows = stmt.query_map(params![node_id, depth], |row| {
            row.get::<_, String>(0)
        }).map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Query Error: {}", e)))?;

        let mut results = Vec::new();
        // Add start node to results as it's part of the context
        results.push(node_id);
        
        for row in rows {
            if let Ok(id) = row {
                results.push(id);
            }
        }

        Ok(results)
    }

    /// Get direct neighbors (outgoing).
    pub fn get_neighbors(&self, node_id: String) -> PyResult<Vec<String>> {
        let mut stmt = self.conn.prepare("SELECT to_node FROM graph_edges WHERE from_node = ?1 AND valid_to IS NULL")
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Prepare Error: {}", e)))?;

        let rows = stmt.query_map(params![node_id], |row| row.get::<_, String>(0))
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Query Error: {}", e)))?;

        let mut results = Vec::new();
        for row in rows {
            if let Ok(id) = row {
                results.push(id);
            }
        }
        Ok(results)
    }

    /// Full Subgraph extraction (Nodes + Edges) for context.
    pub fn get_subgraph(&self, py: Python, node_id: String, depth: usize) -> PyResult<PyObject> {
        // 1. Get all related node IDs first via CTE
        let mut stmt = self.conn.prepare(
            "WITH RECURSIVE bfs AS (
                SELECT ?1 as node_id, 0 as d
                UNION
                SELECT e.to_node, bfs.d + 1
                FROM graph_edges e
                INNER JOIN bfs ON e.from_node = bfs.node_id
                WHERE bfs.d < ?2 AND e.valid_to IS NULL
            )
            SELECT node_id FROM bfs"
        ).map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Prepare Error: {}", e)))?;

        let id_rows = stmt.query_map(params![node_id, depth], |row| row.get::<_, String>(0))
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Query Error: {}", e)))?;

        let mut ids = Vec::new();
        for id in id_rows {
            if let Ok(id_str) = id {
                ids.push(id_str);
            }
        }

        if ids.is_empty() {
             let dict = PyDict::new(py);
             dict.set_item("nodes", PyDict::new(py))?;
             dict.set_item("edges", PyList::empty(py))?;
             return Ok(dict.to_object(py));
        }

        // 2. Fetch node details for all discovered IDs (samo aktivne)
        let placeholders = vec!["?"; ids.len()].join(",");
        let node_query = format!("SELECT * FROM graph_nodes WHERE node_id IN ({}) AND valid_to IS NULL", placeholders);
        let mut node_stmt = self.conn.prepare(&node_query).unwrap();
        
        let node_rows = node_stmt.query_map(rusqlite::params_from_iter(ids.iter()), |row| {
            let mut map = HashMap::new();
            // Pomaknuti indeksi zbog novog auto-increment id na indeksu 0
            map.insert("node_id", row.get::<_, String>(1)?);
            map.insert("node_type", row.get::<_, String>(2)?);
            map.insert("content", row.get::<_, Option<String>>(3)?.unwrap_or_default());
            map.insert("metadata", row.get::<_, String>(4)?);
            map.insert("created_at", row.get::<_, String>(5)?);
            Ok(map)
        }).unwrap();

        let nodes_dict = PyDict::new(py);
        for node in node_rows {
            if let Ok(n) = node {
                let id = n["node_id"].clone();
                let n_dict = PyDict::new(py);
                for (k, v) in n {
                    n_dict.set_item(k, v)?;
                }
                nodes_dict.set_item(id, n_dict)?;
            }
        }

        // 3. Fetch all edges between these nodes (samo aktivne)
        let edge_query = format!("SELECT * FROM graph_edges WHERE from_node IN ({}) AND valid_to IS NULL", placeholders);
        let mut edge_stmt = self.conn.prepare(&edge_query).unwrap();
        let edge_rows = edge_stmt.query_map(rusqlite::params_from_iter(ids.iter()), |row| {
            let mut map = HashMap::new();
            map.insert("edge_id", row.get::<_, i64>(0)?.to_string());
            map.insert("from_node", row.get::<_, String>(1)?);
            map.insert("to_node", row.get::<_, String>(2)?);
            map.insert("relationship_type", row.get::<_, String>(3)?);
            map.insert("metadata", row.get::<_, String>(4)?);
            map.insert("weight", row.get::<_, f64>(5)?.to_string());
            Ok(map)
        }).unwrap();

        let edges_list = PyList::empty(py);
        for edge in edge_rows {
            if let Ok(e) = edge {
                let e_dict = PyDict::new(py);
                for (k, v) in e {
                    e_dict.set_item(k, v)?;
                }
                edges_list.append(e_dict)?;
            }
        }

        let result = PyDict::new(py);
        result.set_item("nodes", nodes_dict)?;
        result.set_item("edges", edges_list)?;

        Ok(result.to_object(py))
    }

    /// Find shortest path using BFS.
    pub fn find_path(&self, start_id: String, end_id: String, max_depth: usize) -> PyResult<Option<Vec<String>>> {
        let query = "
            WITH RECURSIVE path_finder(node_id, path, depth) AS (
                SELECT ?1, ?1, 0
                UNION ALL
                SELECT e.to_node, pf.path || ',' || e.to_node, pf.depth + 1
                FROM graph_edges e
                JOIN path_finder pf ON e.from_node = pf.node_id
                WHERE pf.depth < ?3 AND pf.path NOT LIKE '%' || e.to_node || '%' AND e.valid_to IS NULL
            )
            SELECT path FROM path_finder WHERE node_id = ?2 ORDER BY depth ASC LIMIT 1
        ";

        let mut stmt = self.conn.prepare(query).map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Prepare Error: {}", e)))?;
        let mut rows = stmt.query(params![start_id, end_id, max_depth]).map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Query Error: {}", e)))?;

        if let Some(row) = rows.next().map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Row Error: {}", e)))? {
            let path_str: String = row.get(0).map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Get Error: {}", e)))?;
            let path: Vec<String> = path_str.split(',').map(|s| s.to_string()).collect();
            Ok(Some(path))
        } else {
            Ok(None)
        }
    }
}

#[pymodule]
fn rust_graph(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<RustGraphEngine>()?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;

    fn setup_test_db(path: &str) -> Connection {
        let _ = fs::remove_file(path);
        let conn = Connection::open(path).unwrap();
        conn.execute("CREATE TABLE graph_nodes (id INTEGER PRIMARY KEY AUTOINCREMENT, node_id TEXT, node_type TEXT, content TEXT, metadata TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, valid_from TIMESTAMP DEFAULT CURRENT_TIMESTAMP, valid_to TIMESTAMP)", []).unwrap();
        conn.execute("CREATE TABLE graph_edges (edge_id INTEGER PRIMARY KEY, from_node TEXT, to_node TEXT, relationship_type TEXT, metadata TEXT, weight REAL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, valid_from TIMESTAMP DEFAULT CURRENT_TIMESTAMP, valid_to TIMESTAMP)", []).unwrap();
        
        conn.execute("INSERT INTO graph_nodes (node_id, node_type) VALUES ('A', 'file'), ('B', 'file'), ('C', 'file')", []).unwrap();
        conn.execute("INSERT INTO graph_edges (from_node, to_node, relationship_type) VALUES ('A', 'B', 'calls'), ('B', 'C', 'calls')", []).unwrap();
        conn
    }

    #[test]
    fn test_related() {
        let db = "test_graph.db";
        let conn = setup_test_db(db);
        let engine = RustGraphEngine { conn };
        let related = engine.get_related("A".to_string(), 2).unwrap();
        assert!(related.contains(&"A".to_string()));
        assert!(related.contains(&"B".to_string()));
        assert!(related.contains(&"C".to_string()));
        let _ = fs::remove_file(db);
    }
}
