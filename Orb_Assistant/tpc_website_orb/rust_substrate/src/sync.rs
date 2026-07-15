use pyo3::prelude::*;
use tokio::sync::{mpsc, broadcast};
use std::sync::Arc;
use parking_lot::Mutex;

/// State synchronization between Rust substrate and Python orchestrator
/// Uses channels for zero-copy message passing
#[pyclass]
pub struct RustSyncBridge {
    tx: Arc<Mutex<mpsc::Sender<SyncMessage>>>,
    rx: Arc<Mutex<mpsc::Receiver<SyncMessage>>>,
}

#[derive(Clone)]
struct SyncMessage {
    channel: String,
    payload: Vec<u8>,
}

#[pymethods]
impl RustSyncBridge {
    #[new]
    fn new() -> Self {
        let (tx, rx) = mpsc::channel(1000);
        Self {
            tx: Arc::new(Mutex::new(tx)),
            rx: Arc::new(Mutex::new(rx)),
        }
    }

    /// Send message to Rust substrate
    fn send(&self, channel: String, payload: Vec<u8>) -> PyResult<bool> {
        let tx = self.tx.lock();
        match tx.try_send(SyncMessage { channel, payload }) {
            Ok(_) => Ok(true),
            Err(_) => Ok(false),
        }
    }

    /// Receive message (non-blocking)
    fn try_recv(&self) -> PyResult<Option<(String, Vec<u8>)>> {
        let mut rx = self.rx.lock();
        match rx.try_recv() {
            Ok(msg) => Ok(Some((msg.channel, msg.payload))),
            Err(_) => Ok(None),
        }
    }
}
