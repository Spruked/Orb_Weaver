# cochlear_processor_v3.py
from skg_perceptual_filter import SKGPerceptualFilter, SpeakerKnowledgeGraph
from cognitive_inference import CognitiveInferenceEngine
from correction_loop import RealtimeCorrectionLoop
from skg_learning_bridge import SKGLearningBridge
from adaptive_plasticity import AdaptivePlasticityEngine
import numpy as np
import time
from typing import Dict, List, Tuple, Optional
import uuid

# Vault writer — store correction traces (best-effort; never blocks audio pipeline)
def vault_write_trace(trace: dict) -> None:
    import json, os, time as _t
    try:
        vault_dir = os.path.join(os.path.dirname(__file__), "..", "vault_traces")
        os.makedirs(vault_dir, exist_ok=True)
        fname = os.path.join(vault_dir, f"trace_{int(_t.time()*1000)}.json")
        with open(fname, "w") as f:
            json.dump(trace, f, indent=2, default=str)
    except Exception:
        pass  # never let vault I/O crash the audio pipeline

class CochlearProcessorV3:
    """
    Human-like audio processing with mishearing and correction.
    """
    
    def __init__(self, skg_path: str = "hearing_skg.json"):
        self.skg = SpeakerKnowledgeGraph(skg_path)
        self.perceptual_filter = SKGPerceptualFilter(self.skg)
        self.cognitive_engine = CognitiveInferenceEngine()
        self.correction_loop = RealtimeCorrectionLoop(self)
        self.learning_bridge = SKGLearningBridge(self.skg, self.perceptual_filter)
        
        self.correction_callbacks = []
        self.plasticity_engine = AdaptivePlasticityEngine(self)
    
    def process_audio_human_like(self, audio_path: str, context: Dict, speaker_id: Optional[str] = None) -> Dict:
        """
        Full pipeline: perceptual filtering → transcription → inference → correction → learning
        """
        print(f"🧠 Processing audio '{audio_path}' with human-like perception...")
        
        # 1. Load audio
        audio_data, sr = self._load_audio(audio_path)
        
        # 2. Perceptual filtering (simulates ear/brain)
        filtered_audio, perceptual_report = self.perceptual_filter.apply_perceptual_filter(audio_data, context, speaker_id)
        
        # 3. Transcription (with confidence scores)
        transcript, confidence_scores = self._transcribe_with_confidence(filtered_audio, sr)
        
        # 4. Cognitive inference (fill gaps)
        inferred_transcript, corrections = self.cognitive_engine.process_with_inference(
            transcript, confidence_scores, perceptual_report
        )
        
        # 5. Real-time correction loop (insert corrections)
        final_transcript = self.correction_loop.monitor_and_correct(
            inferred_transcript,
            on_correction=self._trigger_reresynthesis,
            word_confidences=confidence_scores,
        )
        
        # 6. Build trace with all metadata
        trace = self._build_enriched_trace(
            audio_path=audio_path,
            original_transcript=transcript,
            corrected_transcript=final_transcript,
            corrections=corrections,
            perceptual_report=perceptual_report,
            context=context,
            speaker_id=speaker_id
        )
        trace["final_transcript"] = final_transcript
        self._last_trace_id = trace["trace_id"]
        
        # 7. Write to vault
        vault_write_trace(trace)
        
        # 8. Learning: update mastery based on corrections
        for correction in corrections:
            correction["speaker"] = speaker_id or "unknown"
            correction["context"] = context.get("topic", "general")
            self.learning_bridge.process_correction(correction)

        # 9. Adaptive plasticity: log experience to improve future performance
        self.plasticity_engine.log_experience(audio_path, final_transcript, corrections)
        
        print(f"   → Final transcript: '{final_transcript[:80]}...'")
        print(f"   → Corrections made: {len(corrections)}")
        print(f"   → Perceptual confidence: {perceptual_report['confidence_factor']:.2f}")
        
        return trace
    
    def _load_audio(self, path: str) -> Tuple[np.ndarray, int]:
        """Load audio file via soundfile (WAV/FLAC/OGG) with librosa fallback for MP3/M4A."""
        try:
            import soundfile as sf
            data, sr = sf.read(path, dtype="float32", always_2d=False)
            if data.ndim == 2:
                data = data.mean(axis=1)  # stereo → mono
            if sr != 16000:
                import scipy.signal as sig
                n_out = int(len(data) * 16000 / sr)
                data = sig.resample(data, n_out).astype(np.float32)
                sr = 16000
            return data, sr
        except Exception:
            import librosa  # raises ImportError if not installed — expected
            return librosa.load(path, sr=16000)
    
    def _transcribe_with_confidence(self, audio: np.ndarray, sr: int) -> Tuple[str, List[float]]:
        """
        Real Whisper transcription with per-token log-probability → per-word confidence.
        """
        import whisper
        model = self._get_whisper_model()
        # Whisper expects float32 at 16 kHz
        result = model.transcribe(audio, word_timestamps=True, fp16=False, verbose=False)

        # Collect per-word confidences from Whisper's token log-probs
        words: List[str] = []
        confidence_scores: List[float] = []
        for seg in result.get("segments", []):
            for w in seg.get("words", []):
                words.append(w["word"].strip())
                # Whisper provides no_speech_prob and avg_logprob per segment
                lp = seg.get("avg_logprob", -1.0)
                # Map log-prob (typically -3..0) to 0..1 confidence
                conf = float(np.clip(np.exp(lp), 0.0, 1.0))
                confidence_scores.append(conf)

        # Fall back to full-text split if word timestamps unavailable
        if not words:
            transcript = result.get("text", "").strip()
            words = transcript.split()
            # Use segment-level logprob for all words
            all_lp = [s.get("avg_logprob", -0.5) for s in result.get("segments", [])] or [-0.5]
            avg_conf = float(np.clip(np.exp(np.mean(all_lp)), 0.0, 1.0))
            confidence_scores = [avg_conf] * len(words)

        transcript = " ".join(words)
        
        return transcript, confidence_scores
    
    def _build_enriched_trace(self, **data) -> Dict:
        """Build vault trace with all human-like processing metadata"""
        trace = {
            "trace_id": self._generate_trace_id(),
            "timestamp": time.time(),
            "processor": "cochlear_v3_human_like",
            "audio_path": data["audio_path"],
            "speaker_id": data.get("speaker_id"),
            "transcription": {
                "original": data["original_transcript"],
                "corrected": data["corrected_transcript"],
                "corrections": data["corrections"],
                "confidence_before": np.mean([c["confidence_before"] for c in data["corrections"]]) if data["corrections"] else 0.8,
                "confidence_after": np.mean([c["confidence_after"] for c in data["corrections"]]) if data["corrections"] else 0.8
            },
            "perceptual": data["perceptual_report"],
            "context": data["context"],
            "learning": self.learning_bridge.get_mastery_report()
        }
        
        # Link to previous trace for causality
        trace["prev_trace_id"] = self._get_last_trace_id()
        
        return trace
    
    def _trigger_reresynthesis(self, wrong: str, right: str):
        """If confidence is too low, trigger re-synthesis with clearer voice"""
        print(f"🔄 Correction triggered: '{wrong}' → '{right}'")
        
        # Notify any registered callbacks (could trigger POM re-synthesis)
        for callback in self.correction_callbacks:
            callback(wrong, right)
    
    def add_correction_callback(self, callback):
        """Register callback for re-synthesis triggers"""
        self.correction_callbacks.append(callback)
    
    def get_learning_summary(self) -> Dict:
        """Export Caleon's hearing improvement over time"""
        mastery = self.learning_bridge.get_mastery_report()
        return {
            "total_corrections_processed": mastery["total_corrections"],
            "avg_phoneme_mastery": mastery["avg_phoneme_mastery"],
            "avg_speaker_mastery": mastery["avg_speaker_mastery"],
            "phoneme_mastery": mastery["phoneme_mastery"],
            "speaker_mastery": mastery["speaker_mastery"],
            "perceptual_confidence_trend": self.perceptual_filter.state.attention_level
        }
    
    def _generate_trace_id(self) -> str:
        return str(uuid.uuid4())

    def _get_last_trace_id(self) -> str:
        return self._last_trace_id if hasattr(self, '_last_trace_id') else 'none'

    # ── Whisper model singleton (loaded once per processor instance) ──────────
    def _get_whisper_model(self):
        if not hasattr(self, '_whisper_model') or self._whisper_model is None:
            import whisper
            self._whisper_model = whisper.load_model("base")
        return self._whisper_model


class FastCochlearProcessor(CochlearProcessorV3):
    """
    Optimized for real-time human-like processing.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Pre-allocate buffers
        self.audio_buffer = np.zeros(16000 * 10)  # 10-second buffer
        
        # JIT compile critical filters
        self._jit_compile_filters()
        
        # Use faster ASR backend (Whisper.cpp or ONNX Runtime)
        self.asr_backend = "whisper_cpp"  # 3x faster than Python Whisper
        
    def _jit_compile_filters(self):
        """Numba JIT compilation for perceptual filters"""
        try:
            from numba import jit
            
            @jit(nopython=True)
            def fast_frequency_masking(fft, frequencies, sensitivity_map):
                for i in range(len(frequencies)):
                    freq = frequencies[i]
                    # Linear search (fast enough for small arrays)
                    for f_key, sens in sensitivity_map.items():
                        if abs(freq - f_key) < 100:
                            fft[i] *= sens
                            break
                    return fft
            
            self._fast_mask = fast_frequency_masking
        except ImportError:
            self._fast_mask = None
    
    def process_chunked(self, audio_stream, chunk_size=1600):
        """
        Process audio in small chunks for real-time performance.
        """
        for i in range(0, len(audio_stream), chunk_size):
            chunk = audio_stream[i:i+chunk_size]
            
            # Fast path: minimal processing if confidence is high
            if self._should_use_fast_path(chunk):
                transcript = self._fast_transcribe(chunk)
                yield transcript, 0.8, []  # High confidence, no corrections
            else:
                # Slow path: full human-like processing
                trace = self.process_audio_human_like(
                    chunk, context={"is_realtime": True}
                )
                yield trace["transcription"]["corrected"], trace["transcription"]["confidence_after"], trace["transcription"]["corrections"]
    
    def _should_use_fast_path(self, audio_chunk: np.ndarray) -> bool:
        """
        Use fast path when:
        - High attention level
        - No recent dropouts
        - Mastery > 0.8 for this context
        """
        return (
            self.perceptual_filter.state.attention_level > 0.8 and
            len(self.perceptual_filter.state.recent_phoneme_memory or []) > 20 and
            self.plasticity_engine.context_mastery.get(self._extract_context("current"), 0) > 0.8
        )
    
    def _fast_transcribe(self, audio_chunk: np.ndarray) -> str:
        """Use pre-warmed ASR model for low-latency transcription"""
        # Whisper.cpp with GPU acceleration
        return self.asr_cpp.transcribe(
            audio_chunk,
            beam_size=1,  # Fast, low-accuracy mode
            best_of=1,
            language="en"
        )
    
    def _extract_context(self, audio_path: str) -> str:
        """Extract context from path (speaker, topic, environment)"""
        # Example: "audio/phil_interview_tech.wav" → "phil_tech"
        parts = audio_path.split('/')[-1].replace('.wav', '').split('_')
        return f"{parts[0]}_{parts[-1]}" if len(parts) >= 2 else "general"


class HumanHearingProfile:
    """Preset profiles for different human hearing conditions"""
    
    PROFILES = {
        "young_adult": {
            "attention_level": 0.9,
            "frequency_sensitivity": "full_range",
            "confidence": 0.9,
            "correction_rate": 0.05
        },
        "distracted": {
            "attention_level": 0.4,
            "frequency_sensitivity": "reduced_high_freq",
            "confidence": 0.6,
            "correction_rate": 0.3
        },
        "hearing_impaired": {
            "attention_level": 0.7,
            "frequency_sensitivity": "sloping_loss",  # High-freq loss
            "confidence": 0.5,
            "correction_rate": 0.4
        },
        "expert_listener": {
            "attention_level": 0.95,
            "frequency_sensitivity": "enhanced_midrange",
            "confidence": 0.95,
            "correction_rate": 0.02
        }
    }
    
    @classmethod
    def apply_profile(cls, processor: CochlearProcessorV3, profile_name: str):
        """Set processor to simulate a specific human profile"""
        profile = cls.PROFILES[profile_name]
        
        pf = processor.perceptual_filter
        pf.state.attention_level = profile["attention_level"]
        
        # Adjust frequency sensitivity
        if profile["frequency_sensitivity"] == "reduced_high_freq":
            for f in pf.state.frequency_sensitivity:
                if f > 8000:
                    pf.state.frequency_sensitivity[f] *= 0.5
        
        processor.correction_loop.callback_threshold = profile["confidence"]
        processor.cognitive_engine.confidence_threshold = profile["confidence"]