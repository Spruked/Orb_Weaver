use ndarray::Array1;
use pyo3::prelude::*;
use rayon::prelude::*;

/// Rust-native philosopher beam execution
/// Parallel beam runner with cross-influence via confidence metrics only
#[pyclass]
pub struct RustBeamRunner {
    vector_dim: usize,
}

#[pymethods]
impl RustBeamRunner {
    #[new]
    fn new(vector_dim: usize) -> Self {
        Self { vector_dim }
    }

    /// Run all four beams in parallel
    /// Returns: Vec<(beam_name, confidence, output_vector)>
    fn run_parallel(&self, input: Vec<f64>, 
                    beam_weights: Vec<f64>) -> PyResult<String> {
        let input_arr = Array1::from(input);

        // Define beam operations
        let beams: Vec<Box<dyn Fn(&Array1<f64>) -> (f64, Vec<f64>) + Send + Sync>> = vec![
            Box::new(|v| hume_beam(v)),
            Box::new(|v| kant_beam(v)),
            Box::new(|v| locke_beam(v)),
            Box::new(|v| spinoza_beam(v)),
        ];

        let beam_names = vec!["Hume", "Kant", "Locke", "Spinoza"];

        // Execute in parallel
        let results: Vec<(String, f64, Vec<f64>)> = beams.par_iter()
            .enumerate()
            .map(|(i, beam_fn)| {
                let (conf, output) = beam_fn(&input_arr);
                (beam_names[i].to_string(), conf, output)
            })
            .collect();

        let json_results: Vec<serde_json::Value> = results.into_iter()
            .map(|(name, conf, output)| {
                serde_json::json!({
                    "name": name,
                    "confidence": conf,
                    "output": output,
                })
            })
            .collect();

        Ok(serde_json::to_string(&json_results).unwrap_or_default())
    }
}

// Individual beam logic — pure deterministic functions

fn hume_beam(input: &Array1<f64>) -> (f64, Vec<f64>) {
    // Empirical skepticism: deflate overconfident claims
    let magnitude = input.mapv(|x| x * x).sum().sqrt();
    let has_impression = (magnitude / 10.0).min(1.0);
    let confidence = has_impression * 0.7;

    let output = input * (0.5 + 0.5 * confidence) + 
        Array1::from(vec![0.05; input.len()]);

    (confidence, output.to_vec())
}

fn kant_beam(input: &Array1<f64>) -> (f64, Vec<f64>) {
    // Categorical: universalizability via self-similarity
    let normalized = input / (input.mapv(|x| x * x).sum().sqrt() + 1e-10);
    let self_sim = normalized.dot(&normalized);
    let confidence = (self_sim * 0.9).min(0.95);

    let output = normalized * confidence * (input.len() as f64).sqrt();

    (confidence, output.to_vec())
}

fn locke_beam(input: &Array1<f64>) -> (f64, Vec<f64>) {
    // Rights: preserve individual dimension sovereignty
    let harm_proxy = input.iter().filter(|&&x| x < 0.0).map(|&x| x.abs()).sum::<f64>();
    let total = input.iter().map(|&x| x.abs()).sum::<f64>();
    let preservation = if total > 0.0 { 1.0 - harm_proxy / total } else { 0.5 };
    let confidence = preservation * 0.9;

    let mut output = input.to_vec();
    output.iter_mut().for_each(|x| {
        if *x == 0.0 { *x = 0.01; }
    });

    (confidence, output)
}

fn spinoza_beam(input: &Array1<f64>) -> (f64, Vec<f64>) {
    // Geometric determinism: necessity via low entropy
    let normalized = input.mapv(|x| x.abs()) / (input.mapv(|x| x.abs()).sum() + 1e-10);
    let entropy = -normalized.iter()
        .map(|&x| if x > 0.0 { x * x.log2() } else { 0.0 })
        .sum::<f64>();
    let max_entropy = (input.len() as f64).log2();
    let necessity = if max_entropy > 0.0 { 1.0 - entropy / max_entropy } else { 1.0 };
    let confidence = necessity * 0.95;

    // SVD-like projection (simplified)
    let output = input / (input.mapv(|x| x * x).sum().sqrt() + 1e-10) * 
        confidence * (input.len() as f64).sqrt();

    (confidence, output.to_vec())
}
