"""
Phonatory Output Bridge
Connects TPC reasoning output to TTS engines.
Kokoro primary, Qwen backup.
Integrates with the TPC Website ORB assistant.
"""

import numpy as np
from typing import Dict, List, Optional, Any
import time

from Orb_Assistant.tpc_website_orb.engines.kokoro_engine.adapter import get_kokoro_adapter
from Orb_Assistant.tpc_website_orb.engines.qwen_engine.adapter import get_qwen_adapter


class PhonatoryOutputBridge:
    """
    Bridges TPC output to phonatory (speech) synthesis.
    Routes to Kokoro (primary) or Qwen (backup).
    """

    def __init__(self):
        self.kokoro = get_kokoro_adapter()
        self.qwen = get_qwen_adapter()
        self.primary_engine = "kokoro"
        self.backup_engine = "qwen"
        self.output_history: List[Dict] = []

    def speak(self, text: str, voice: str = None,
              engine: str = "auto") -> Dict:
        """
        Convert TPC output text to speech.

        Args:
            text: Text to synthesize
            voice: Voice ID (auto-selected if None)
            engine: "kokoro", "qwen", or "auto"

        Returns:
            Dict with audio_path, engine_used, duration_estimate
        """
        start_time = time.time()

        # Select engine
        if engine == "auto":
            engine = self._select_engine()

        # Select voice
        if voice is None:
            voice = self._select_voice(engine)

        # Synthesize
        audio_path = None
        error = None

        try:
            if engine == "kokoro":
                audio_path = self.kokoro.synthesize(text, voice=voice)
            elif engine == "qwen":
                audio_path = self.qwen.synthesize(text, voice_id=voice)
        except Exception as e:
            error = str(e)
            # Try backup
            if engine == "kokoro":
                engine = "qwen"
                try:
                    audio_path = self.qwen.synthesize(text, voice_id=voice)
                except Exception as e2:
                    error += f" | Backup failed: {e2}"

        result = {
            'audio_path': audio_path,
            'engine_used': engine,
            'voice': voice,
            'text_length': len(text),
            'processing_time_ms': (time.time() - start_time) * 1000,
            'error': error,
            'timestamp': time.time()
        }

        self.output_history.append(result)
        return result

    def _select_engine(self) -> str:
        """Select best available engine."""
        kokoro_stats = self.kokoro.get_stats()
        if kokoro_stats.get('pipeline_available'):
            return "kokoro"
        return "qwen"

    def _select_voice(self, engine: str) -> str:
        """Select default voice for engine."""
        if engine == "kokoro":
            voices = self.kokoro.list_voices()
            return voices[0] if voices else "af_bella"
        return "default"

    def get_stats(self) -> Dict:
        return {
            'total_outputs': len(self.output_history),
            'kokoro_available': self.kokoro.get_stats()['pipeline_available'],
            'qwen_available': self.qwen.get_stats()['model_available'],
            'primary_engine': self.primary_engine,
            'avg_processing_time_ms': np.mean([o['processing_time_ms'] 
                for o in self.output_history]) if self.output_history else 0
        }


# Singleton
_phonatory_bridge = None

def get_phonatory_bridge() -> PhonatoryOutputBridge:
    global _phonatory_bridge
    if _phonatory_bridge is None:
        _phonatory_bridge = PhonatoryOutputBridge()
    return _phonatory_bridge
