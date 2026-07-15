"""
CP 3.0 sidecar adapter.

CP 3.0 is an acoustic feature enhancer for Gate 1. It is not the primary STT
engine. Faster-Whisper owns primary STT/input gateway behavior.
"""

from pathlib import Path
from typing import Dict
import sys

import numpy as np


CP3_PATH = Path(__file__).resolve().parents[3] / "cochlear_processor_3.0"
if str(CP3_PATH) not in sys.path:
    sys.path.insert(0, str(CP3_PATH))


class CP3SidecarAdapter:
    """
    Sidecar wrapper for Cochlear Processor 3.0.

    Provides acoustic feature enhancement only. It does not transcribe audio and
    does not replace the Faster-Whisper Gate 1 input gateway.
    """

    def __init__(self, vector_dim: int = 512):
        self.vector_dim = vector_dim
        self.processor = None
        self._init_processor()

    def _init_processor(self):
        try:
            # from cochlear_processor_v3 import CochlearProcessor
            # self.processor = CochlearProcessor()
            pass
        except ImportError as e:
            print(f"[CP3SidecarAdapter] Processor not available: {e}")
            self.processor = None

    def enhance_audio(self, audio_path: str) -> np.ndarray:
        """Return optional CP 3.0 acoustic features for an audio file."""
        if self.processor:
            # return self.processor.process_audio(audio_path)
            pass
        return self._fallback_vector(audio_path)

    def process_audio(self, audio_path: str) -> np.ndarray:
        """Deprecated alias. Use enhance_audio()."""
        return self.enhance_audio(audio_path)

    def process_text(self, text: str) -> np.ndarray:
        """Deprecated: CP 3.0 is not the active text/STT gateway."""
        return self._fallback_vector(text)

    def _fallback_vector(self, seed: str) -> np.ndarray:
        np.random.seed(hash(seed) % 2**32)
        vector = np.random.randn(self.vector_dim)
        return vector / (np.linalg.norm(vector) + 1e-10)

    def get_stats(self) -> Dict:
        return {
            "processor_available": self.processor is not None,
            "vector_dim": self.vector_dim,
            "role": "sidecar_acoustic_feature_enhancer",
            "primary_stt": False,
            "status": "sidecar_active" if self.processor else "sidecar_stub_mode",
        }


_cp3_sidecar_adapter = None


def get_cp3_sidecar_adapter(vector_dim: int = 512) -> CP3SidecarAdapter:
    global _cp3_sidecar_adapter
    if _cp3_sidecar_adapter is None:
        _cp3_sidecar_adapter = CP3SidecarAdapter(vector_dim)
    return _cp3_sidecar_adapter


CochlearAdapter = CP3SidecarAdapter


def get_cochlear_adapter(vector_dim: int = 512) -> CP3SidecarAdapter:
    """Deprecated compatibility alias. Use get_cp3_sidecar_adapter()."""
    return get_cp3_sidecar_adapter(vector_dim)
