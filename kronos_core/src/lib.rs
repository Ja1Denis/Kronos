use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::collections::HashMap;

#[derive(Clone)]
struct TrieNode {
    children: HashMap<char, Box<TrieNode>>,
    contents: Vec<String>,
}

impl TrieNode {
    fn new() -> Self {
        Self {
            children: HashMap::new(),
            contents: Vec::new(),
        }
    }
}

#[derive(Clone)]
struct PrefixTrie {
    root: TrieNode,
}

impl PrefixTrie {
    fn new() -> Self {
        Self {
            root: TrieNode::new(),
        }
    }

    fn insert(&mut self, key: &str, content: &str) {
        let normalized = key.trim().to_lowercase();
        let mut node = &mut self.root;

        for ch in normalized.chars() {
            node = node
                .children
                .entry(ch)
                .or_insert_with(|| Box::new(TrieNode::new()));
        }

        if node.contents.len() < 10 {
            node.contents.push(content.to_string());
        }
    }

    fn search(&self, prefix: &str, limit: usize) -> Vec<String> {
        let normalized = prefix.trim().to_lowercase();
        let mut node = &self.root;

        for ch in normalized.chars() {
            if let Some(next_node) = node.children.get(&ch) {
                node = next_node;
            } else {
                return Vec::new();
            }
        }

        let mut results = Vec::new();
        self.collect_recursive(node, &mut results, limit);
        results
    }

    fn collect_recursive(&self, node: &TrieNode, results: &mut Vec<String>, limit: usize) {
        for content in &node.contents {
            if results.len() >= limit {
                return;
            }
            if !results.contains(content) {
                results.push(content.clone());
            }
        }

        for child in node.children.values() {
            if results.len() >= limit {
                return;
            }
            self.collect_recursive(child, results, limit);
        }
    }
}

#[pyclass]
pub struct FastPath {
    exact_index: HashMap<String, String>, // key -> content
    prefix_trie: PrefixTrie,
}

#[pymethods]
impl FastPath {
    #[new]
    pub fn new() -> Self {
        Self {
            exact_index: HashMap::new(),
            prefix_trie: PrefixTrie::new(),
        }
    }

    pub fn insert(&mut self, key: String, content: String) {
        let normalized = key.trim().to_lowercase();
        self.exact_index.insert(normalized.clone(), content.clone());
        
        // Također indeksiramo riječi za prefiks
        for word in normalized.split_whitespace().take(3) {
            if word.len() > 2 {
                self.prefix_trie.insert(word, &content);
            }
        }
        
        // Specijalno za emailove ili cijele ključeve
        if normalized.contains('@') || normalized.len() < 50 {
            self.prefix_trie.insert(&normalized, &content);
        }
    }

    pub fn search<'py>(&self, py: Python<'py>, query: String) -> PyResult<Option<Bound<'py, PyDict>>> {
        let normalized = query.trim().to_lowercase();

        // 1. Exact Match
        if let Some(content) = self.exact_index.get(&normalized) {
            let res = PyDict::new_bound(py);
            res.set_item("type", "ExactMatch")?;
            res.set_item("confidence", 1.0)?;
            res.set_item("content", content.clone())?;
            return Ok(Some(res));
        }

        // 2. Prefix Match
        if normalized.len() >= 3 {
            let results = self.prefix_trie.search(&normalized, 5);
            if !results.is_empty() {
                let first = &results[0];
                if first.to_lowercase().starts_with(&normalized) {
                    let res = PyDict::new_bound(py);
                    res.set_item("type", "PrefixMatch")?;
                    res.set_item("confidence", 0.9)?;
                    res.set_item("content", first.clone())?;
                    return Ok(Some(res));
                }
            }
        }

        Ok(None)
    }
    
    pub fn clear(&mut self) {
        self.exact_index.clear();
        self.prefix_trie = PrefixTrie::new();
    }
    
    pub fn __len__(&self) -> usize {
        self.exact_index.len()
    }
}

#[pymodule]
fn kronos_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<FastPath>()?;
    Ok(())
}
