//! TPC Substrate — Rust Core Engine
//! 
//! Memory-safe, deterministic substrate for:
//! - Vector operations (geometric glyph signatures)
//! - Concurrent philosopher beam execution
//! - Immutable vault storage
//! - Drift ping confirmation chains
//! - State synchronization with Python orchestrator

pub mod memory;
pub mod recursion;
pub mod vault;
pub mod drift;
pub mod beams;
pub mod geometry;
pub mod sync;

use pyo3::prelude::*;

/// Python module initialization
#[pymodule]
fn tpc_substrate(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<memory::RustMemoryEngine>()?;
    m.add_class::<vault::RustVaultStore>()?;
    m.add_class::<drift::RustDriftPing>()?;
    m.add_class::<geometry::RustGlyphEngine>()?;
    Ok(())
}
