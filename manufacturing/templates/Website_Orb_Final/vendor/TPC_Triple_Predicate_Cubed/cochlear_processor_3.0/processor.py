from __future__ import annotations

import sys
from pathlib import Path
from typing import Union

import numpy as np

_REPO_DIR = Path(__file__).resolve().parent
if str(_REPO_DIR) not in sys.path:
    sys.path.insert(0, str(_REPO_DIR))

from cochlear_processor_v3 import (  # noqa: E402
    CochlearProcessorV3,
    FastCochlearProcessor,
    HumanHearingProfile,
)
from processor_v2 import AdaptiveCochlearProcessorV2  # noqa: E402
from skg_perceptual_filter import SKGPerceptualFilter, SpeakerKnowledgeGraph  # noqa: E402


class AdaptiveCochlearProcessor(AdaptiveCochlearProcessorV2):
    """
    TPC-compatible entry point for the cloned cochlear processor repo.
    It keeps the existing 18D stimulus contract while routing audio through
    the repo's SKG perceptual filter.
    """

    def __init__(
        self,
        output_dims: int = 18,
        sample_rate: int = 16000,
        skg_path: str | Path | None = None,
        random_seed: int = 0,
    ):
        super().__init__(output_dims=output_dims)
        self.sample_rate = sample_rate
        self.random_seed = random_seed
        self.skg_path = Path(skg_path) if skg_path else _REPO_DIR / "hearing_skg.json"
        self.skg = SpeakerKnowledgeGraph(str(self.skg_path))
        self.perceptual_filter = SKGPerceptualFilter(self.skg, sample_rate=sample_rate)

    def process_audio(
        self,
        audio_signal: Union[str, Path, np.ndarray],
        sample_rate: int | None = None,
    ) -> np.ndarray:
        if isinstance(audio_signal, (str, Path)):
            engine = CochlearProcessorV3(skg_path=str(self.skg_path))
            audio, rate = engine._load_audio(str(audio_signal))
        else:
            audio = np.asarray(audio_signal, dtype=float)
            rate = sample_rate or self.sample_rate

        audio = np.ravel(audio)
        if audio.size == 0:
            return np.zeros(self.output_dims)

        rng_state = np.random.get_state()
        np.random.seed(self.random_seed)
        try:
            filtered_audio, _ = self.perceptual_filter.apply_perceptual_filter(
                audio.copy(),
                {"text": "", "topic": "tpc"},
            )
        finally:
            np.random.set_state(rng_state)

        return self._band_features(filtered_audio, rate)

    def process(
        self,
        input_data: Union[str, Path, np.ndarray],
        input_type: str = "text",
    ) -> np.ndarray:
        if input_type == "text":
            return self.process_text(str(input_data))
        if input_type == "audio":
            return self.process_audio(input_data)
        raise ValueError(f"Unknown input type: {input_type}")

    def _band_features(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        fft = np.abs(np.fft.rfft(audio, n=256))
        freqs = np.fft.rfftfreq(256, 1 / sample_rate)
        features = np.zeros(self.output_dims)
        nyquist = max(sample_rate // 2, 20)
        band_edges = np.logspace(1, np.log10(nyquist), self.output_dims + 1)

        for i in range(self.output_dims):
            mask = (freqs >= band_edges[i]) & (freqs < band_edges[i + 1])
            if np.any(mask):
                features[i] = np.mean(fft[mask])

        max_value = np.max(features)
        if max_value > 0:
            features = features / max_value

        return features
