use std::collections::HashMap;
use std::time::{Duration, Instant};
use parking_lot::RwLock;
use pyo3::prelude::*;
use serde::{Deserialize, Serialize};

/// Rust-native drift ping confirmation chain
/// Memory-safe, zero-allocation hot path
#[pyclass]
pub struct RustDriftPing {
    threshold_ms: u64,
    integrity_threshold: f64,
    confirmations: Arc<RwLock<u64>>,
    drifts: Arc<RwLock<u64>>,
    gate_registry: Arc<RwLock<HashMap<String, GateStats>>>,
}

#[derive(Clone, Serialize, Deserialize)]
struct GateStats {
    gate_type: String,
    ping_count: u64,
    drifts_detected: u64,
}

#[pymethods]
impl RustDriftPing {
    #[new]
    fn new(threshold_ms: u64, integrity_threshold: f64) -> Self {
        Self {
            threshold_ms,
            integrity_threshold,
            confirmations: Arc::new(RwLock::new(0)),
            drifts: Arc::new(RwLock::new(0)),
            gate_registry: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    /// Register a gate (called once at init)
    fn register_gate(&self, gate_id: String, gate_type: String) {
        let mut registry = self.gate_registry.write();
        registry.insert(gate_id, GateStats {
            gate_type,
            ping_count: 0,
            drifts_detected: 0,
        });
    }

    /// Confirm a ping — hot path, minimal allocation
    fn confirm(&self, gate_id: String, signal_integrity: f64, latency_ms: u64) -> PyResult<bool> {
        let mut registry = self.gate_registry.write();

        if let Some(stats) = registry.get_mut(&gate_id) {
            stats.ping_count += 1;

            // Check latency
            if latency_ms > self.threshold_ms {
                stats.drifts_detected += 1;
                let mut drifts = self.drifts.write();
                *drifts += 1;
                return Ok(false); // Drift detected
            }

            // Check integrity
            if signal_integrity < self.integrity_threshold {
                stats.drifts_detected += 1;
                let mut drifts = self.drifts.write();
                *drifts += 1;
                return Ok(false); // Integrity failure
            }

            // Confirmed
            let mut confirmations = self.confirmations.write();
            *confirmations += 1;
            Ok(true)
        } else {
            Err(pyo3::exceptions::PyKeyError::new_err("Gate not registered"))
        }
    }

    /// Get drift report
    fn get_report(&self) -> PyResult<String> {
        let confirmations = *self.confirmations.read();
        let drifts = *self.drifts.read();
        let total = confirmations + drifts;

        let drift_rate = if total > 0 {
            drifts as f64 / total as f64
        } else {
            0.0
        };

        let report = serde_json::json!({
            "total_pings": total,
            "confirmed": confirmations,
            "drift_detected": drifts,
            "drift_rate": drift_rate,
            "status": if drift_rate == 0.0 { "ZERO_DRIFT" } else { "DRIFT_DETECTED" },
            "threshold_ms": self.threshold_ms,
            "integrity_threshold": self.integrity_threshold,
        });

        Ok(report.to_string())
    }

    fn get_gate_stats(&self) -> PyResult<String> {
        let registry = self.gate_registry.read();
        let stats: HashMap<String, GateStats> = registry.clone();
        Ok(serde_json::to_string(&stats).unwrap_or_default())
    }
}
