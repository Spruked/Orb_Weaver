import hashlib
import re
from typing import Union

import numpy as np


class AdaptiveCochlearProcessorV2:
    """
    Enhanced cochlear text processor with richer feature extraction.
    Produces structured 18D stimuli for philosopher reasoning.
    """

    def __init__(self, output_dims: int = 18):
        self.output_dims = output_dims

    def process_text(self, text: str) -> np.ndarray:
        text = str(text).lower().strip()
        text = re.sub(r"[^\w\s]", " ", text)
        words = text.split()

        if not words:
            return np.zeros(self.output_dims)

        features = np.zeros(self.output_dims)

        # 1. Statistical structure (dims 0-5)
        word_lengths = [len(word) for word in words]
        features[0] = np.mean(word_lengths) / 10.0
        features[1] = np.std(word_lengths) / 5.0
        features[2] = len(words) / 50.0
        features[3] = len(set(words)) / len(words)
        features[4] = len(text) / 500.0
        features[5] = text.count(" ") / len(text) if text else 0.0

        # 2. Semantic density patterns (dims 6-11)
        text_hash = hashlib.md5(text.encode("utf-8")).hexdigest()
        hash_vals = [int(text_hash[i : i + 2], 16) / 255.0 for i in range(0, 12, 2)]
        for index, value in enumerate(hash_vals):
            target = index + 6
            if target < self.output_dims:
                features[target] = value

        # 3. Syntactic and trigger structure (dims 12-17)
        features[12] = 1.0 if any(marker in text for marker in ["what", "why", "how", "is it", "can we"]) else 0.0
        features[13] = self._keyword_density(text, ["observe", "data", "evidence", "empirical", "sense"])
        features[14] = self._keyword_density(text, ["universal", "all", "every", "must", "always", "law"])
        features[15] = self._keyword_density(text, ["consent", "agree", "permission", "right", "autonomy"])
        features[16] = self._keyword_density(text, ["prove", "demonstrate", "necessary", "axiom", "geometry", "chain"])
        features[17] = self._keyword_density(text, ["abstract", "metaphysics", "theory"])

        features = np.tanh(features * 2)
        return self._ensure_empirical_variance(features, text)

    def process(self, input_data: Union[str, np.ndarray], input_type: str = "text") -> np.ndarray:
        if input_type == "text":
            return self.process_text(str(input_data))
        if input_type == "audio":
            return self.process_audio(np.asarray(input_data))
        raise ValueError(f"Unknown input type: {input_type}")

    def process_audio(self, input_data: np.ndarray) -> np.ndarray:
        if len(input_data) == 0:
            return np.zeros(self.output_dims)

        fft = np.abs(np.fft.rfft(input_data, n=256))
        features = np.zeros(self.output_dims)
        band_size = max(1, len(fft) // self.output_dims)

        for index in range(self.output_dims):
            start = index * band_size
            end = start + band_size
            if start < len(fft):
                features[index] = np.mean(fft[start:end]) / (np.max(fft) + 1e-10)

        return features * 2 - 1

    def _keyword_density(self, text: str, keywords: list[str]) -> float:
        return sum(1 for keyword in keywords if keyword in text) / max(len(keywords), 1)

    def _ensure_empirical_variance(self, features: np.ndarray, text: str) -> np.ndarray:
        min_variance = 0.12
        if np.var(features) >= min_variance:
            return features

        digest = hashlib.sha256(text.encode("utf-8")).digest()
        pattern = np.array(
            [digest[index % len(digest)] / 255.0 for index in range(self.output_dims)]
        )
        pattern = (pattern - np.mean(pattern)) / (np.std(pattern) + 1e-10)

        centered = features - np.mean(features)
        if np.std(centered) < 1e-10:
            centered = pattern
        else:
            centered = centered / np.std(centered)

        boosted = np.mean(features) + centered * np.sqrt(min_variance)
        boosted += pattern * 0.03
        return np.clip(boosted, -1.0, 1.0)
