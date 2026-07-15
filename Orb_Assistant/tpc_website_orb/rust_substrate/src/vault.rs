use ndarray::Array1;
use parking_lot::RwLock;
use std::collections::HashMap;
use pyo3::prelude::*;
use serde::{Deserialize, Serialize};

/// Rust-native vault storage
/// Immutable append-only with geometric retrieval
#[pyclass]
pub struct RustVaultStore {
    a_priori: Arc<RwLock<HashMap<String, VaultEntry>>>,
    a_posteriori: Arc<RwLock<HashMap<String, VaultEntry>>>,
    max_entries: usize,
}

#[derive(Clone, Serialize, Deserialize)]
struct VaultEntry {
    id: String,
    signature: Vec<f64>,
    content: String,
    certainty: f64,
    retrieval_count: u64,
    timestamp: f64,
}

#[pymethods]
impl RustVaultStore {
    #[new]
    fn new(max_entries: usize) -> Self {
        Self {
            a_priori: Arc::new(RwLock::new(HashMap::new())),
            a_posteriori: Arc::new(RwLock::new(HashMap::new())),
            max_entries,
        }
    }

    /// Store a posteriori entry
    fn store_aposteriori(&self, id: String, signature: Vec<f64>, 
                         content: String, certainty: f64) -> PyResult<String> {
        let entry = VaultEntry {
            id: id.clone(),
            signature,
            content,
            certainty,
            retrieval_count: 0,
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap_or_default()
                .as_secs_f64(),
        };

        let mut store = self.a_posteriori.write();

        // Prune if over max
        if store.len() >= self.max_entries {
            self._prune_oldest(&mut store);
        }

        store.insert(id.clone(), entry);
        Ok(id)
    }

    /// Geometric retrieval by cosine similarity
    fn retrieve(&self, query: Vec<f64>, top_k: usize, 
                threshold: f64) -> PyResult<String> {
        let query_arr = Array1::from(query);
        let query_norm = query_arr.mapv(|x| x * x).sum().sqrt();

        let store = self.a_posteriori.read();

        let mut scored: Vec<(String, f64, String)> = store.values()
            .filter_map(|entry| {
                let entry_arr = Array1::from(entry.signature.clone());
                let dot = query_arr.dot(&entry_arr);
                let entry_norm = entry_arr.mapv(|x| x * x).sum().sqrt();
                let similarity = dot / (query_norm * entry_norm + 1e-10);
                let distance = 1.0 - similarity;

                if distance <= threshold {
                    let confidence = similarity * entry.certainty * 
                        (1.0 + 0.1 * entry.retrieval_count as f64);
                    Some((entry.id.clone(), confidence, entry.content.clone()))
                } else {
                    None
                }
            })
            .collect();

        // Sort by confidence
        scored.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
        scored.truncate(top_k);

        let results: Vec<serde_json::Value> = scored.into_iter()
            .map(|(id, conf, content)| {
                serde_json::json!({
                    "id": id,
                    "confidence": conf,
                    "content": content,
                })
            })
            .collect();

        Ok(serde_json::to_string(&results).unwrap_or_default())
    }

    fn _prune_oldest(&self, store: &mut HashMap<String, VaultEntry>) {
        let mut entries: Vec<_> = store.values().cloned().collect();
        entries.sort_by(|a, b| {
            let a_score = (a.retrieval_count, a.timestamp);
            let b_score = (b.retrieval_count, b.timestamp);
            a_score.cmp(&b_score)
        });

        let remove_count = (entries.len() / 10).max(1);
        for entry in entries.into_iter().take(remove_count) {
            store.remove(&entry.id);
        }
    }

    fn get_stats(&self) -> PyResult<String> {
        let a_priori = self.a_priori.read();
        let a_posteriori = self.a_posteriori.read();

        let stats = serde_json::json!({
            "a_priori_entries": a_priori.len(),
            "a_posteriori_entries": a_posteriori.len(),
            "max_entries": self.max_entries,
        });

        Ok(stats.to_string())
    }
}
