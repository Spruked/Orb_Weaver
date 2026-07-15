"""
Gate 1 input gateway.

Faster-Whisper is the primary STT/input gateway.
Qwen STT is optional.
CP 3.0 is a sidecar acoustic feature enhancer, not the primary STT engine.
"""

from dataclasses import dataclass
import importlib.util
from pathlib import Path
from typing import Any, Dict, Optional, Union
import hashlib

import numpy as np


@dataclass
class Gate1Stimulus:
    """Normalized Gate 1 output for the TPC cognitive pipeline."""

    modality: str
    text: str
    signal: np.ndarray
    sample_rate: int = 24000
    metadata: Optional[Dict[str, Any]] = None
    confidence: float = 1.0

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class FasterWhisperInputGateway:
    """
    Gate 1 input gateway.

    Audio input is transcribed by Faster-Whisper when available, with optional
    Qwen STT reserved as a secondary path. CP 3.0 may add acoustic sidecar
    features, but does not own STT authority.
    """

    def __init__(self, vector_dim: int = 512):
        self.vector_dim = vector_dim
        self.cp3_sidecar = self._load_cp3_sidecar_adapter(vector_dim)
        self.faster_whisper_model = self._load_faster_whisper()

    def _load_cp3_sidecar_adapter(self, vector_dim: int):
        adapter_path = Path(__file__).resolve().parents[3] / "engines" / "cochlear_processor_3.0" / "adapter.py"
        spec = importlib.util.spec_from_file_location("cp3_sidecar_adapter", adapter_path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.get_cp3_sidecar_adapter(vector_dim)

    def _load_faster_whisper(self):
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            return None

        try:
            return WhisperModel("base", device="cpu", compute_type="int8")
        except Exception:
            return None

    def process(self, input_data: Union[str, np.ndarray], input_type: str = "text") -> Gate1Stimulus:
        if input_type == "audio":
            return self.process_audio(input_data)
        return self.process_text(str(input_data))

    def process_audio(self, audio_path: Union[str, Path]) -> Gate1Stimulus:
        text = self._transcribe_audio(audio_path)
        signal = self._text_to_vector(text)
        sidecar_features = self.cp3_sidecar.enhance_audio(str(audio_path)) if self.cp3_sidecar else None
        signal = self._blend_sidecar(signal, sidecar_features)

        return Gate1Stimulus(
            modality="audio",
            text=text,
            signal=signal,
            metadata={
                "primary_gateway": "faster_whisper",
                "optional_stt": "qwen",
                "sidecar": "cp3",
                "audio_path": str(audio_path),
            },
        )

    def process_text(self, text: str) -> Gate1Stimulus:
        signal = self._text_to_vector(text)
        return Gate1Stimulus(
            modality="text",
            text=text,
            signal=signal,
            sample_rate=0,
            metadata={
                "primary_gateway": "text_input",
                "sidecar": "cp3_available",
            },
        )

    def _transcribe_audio(self, audio_path: Union[str, Path]) -> str:
        if self.faster_whisper_model is None:
            return str(audio_path)

        segments, _ = self.faster_whisper_model.transcribe(str(audio_path))
        transcript = " ".join(segment.text.strip() for segment in segments).strip()
        return transcript or str(audio_path)

    def _text_to_vector(self, text: str) -> np.ndarray:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        repeated = (digest * ((self.vector_dim // len(digest)) + 1))[:self.vector_dim]
        vector = np.frombuffer(repeated, dtype=np.uint8).astype(float) / 255.0
        return vector / (np.linalg.norm(vector) + 1e-10)

    def _blend_sidecar(self, signal: np.ndarray, sidecar_features: Optional[np.ndarray]) -> np.ndarray:
        if sidecar_features is None:
            return signal
        features = np.asarray(sidecar_features, dtype=float).flatten()
        if features.size < self.vector_dim:
            features = np.pad(features, (0, self.vector_dim - features.size))
        features = features[:self.vector_dim]
        features = features / (np.linalg.norm(features) + 1e-10)
        blended = (signal * 0.85) + (features * 0.15)
        return blended / (np.linalg.norm(blended) + 1e-10)


_input_gateway_instance = None


def get_input_gateway(vector_dim: int = 512) -> FasterWhisperInputGateway:
    global _input_gateway_instance
    if _input_gateway_instance is None:
        _input_gateway_instance = FasterWhisperInputGateway(vector_dim)
    return _input_gateway_instance
