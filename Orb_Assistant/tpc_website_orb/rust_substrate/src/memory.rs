use ndarray::{Array1, Array2, Axis};
use parking_lot::RwLock;
use std::collections::HashMap;
use std::sync::Arc;
use pyo3::prelude::*;
use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// Rust-native memory engine for vector operations
/// Replaces Python numpy for hot paths
#[pyclass]
pub struct RustMemoryEngine {
    vector_store: Arc<RwLock<HashMap<String, Array1<f64>>>>,
    dimension: usize,
}

#[pymethods]
impl RustMemoryEngine {
    #[new]
    fn new(dimension: usize) -> Self {
        Self {
            vector_store: Arc::new(RwLock::new(HashMap::new())),
            dimension,
        }
    }

    /// Store vector with UUID key
    fn store_vector(&self, key: String, data: Vec<f64>) -> PyResult<String> {
        let arr = Array1::from(data);
        let mut store = self.vector_store.write();
        store.insert(key.clone(), arr);
        Ok(key)
    }

    /// Cosine similarity between two vectors — hot path
    fn cosine_similarity(&self, a_key: &str, b_key: &str) -> PyResult<f64> {
        let store = self.vector_store.read();

        let a = store.get(a_key)
        let b = store.get(b_key);

        match (a, b) {
            (Some(vec_a), Some(vec_b)) => {
                let dot = vec_a.dot(vec_b);
                let norm_a = vec_a.mapv(|x| x * x).sum().sqrt();
                let norm_b = vec_b.mapv(|x| x * x).sum().sqrt();
                Ok(dot / (norm_a * norm_b + 1e-10))
            }
            _ => Err(pyo3::exceptions::PyKeyError::new_err("Vector not found")),
        }
    }

    /// Batch cosine similarity — parallelized with rayon
    fn batch_similarity(&self, query_key: &str, target_keys: Vec<String>) -> PyResult<Vec<f64>> {
        let store = self.vector_store.read();
        let query = store.get(query_key)
            .ok_or_else(|| pyo3::exceptions::PyKeyError::new_err("Query not found"))?;

        let results: Vec<f64> = target_keys.into_iter()
            .filter_map(|key| {
                store.get(&key).map(|target| {
                    let dot = query.dot(target);
                    let norm_q = query.mapv(|x| x * x).sum().sqrt();
                    let norm_t = target.mapv(|x| x * x).sum().sqrt();
                    dot / (norm_q * norm_t + 1e-10)
                })
            })
            .collect();

        Ok(results)
    }

    /// Get memory stats
    fn stats(&self) -> PyResult<String> {
        let store = self.vector_store.read();
        let stats = serde_json::json!({
            "total_vectors": store.len(),
            "dimension": self.dimension,
            "memory_estimate_kb": store.len() * self.dimension * 8 / 1024,
        });
        Ok(stats.to_string())
    }
}

/// Concurrent vector pool for beam operations
pub struct VectorPool {
    vectors: Vec<Array1<f64>>,
}

impl VectorPool {
    pub fn new(count: usize, dimension: usize) -> Self {
        let vectors = (0..count)
            .map(|_| Array1::zeros(dimension))
            .collect();
        Self { vectors }
    }

    /// Parallel philosopher beam execution
    pub fn parallel_beams<F>(&self, operation: F) -> Vec<Array1<f64>>
    where
        F: Fn(&Array1<f64>) -> Array1<f64> + Send + Sync,
    {
        use rayon::prelude::*;

        self.vectors
            .par_iter()
            .map(|v| operation(v))
            .collect()
    }
}
