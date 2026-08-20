import json
import numpy as np
from typing import Dict, List, Optional, Tuple
from perceptual_filter import HumanPerceptualFilter

class SpeakerKnowledgeGraph:
    """
    Manages the hearing knowledge graph for persistent learning.
    """
    
    def __init__(self, skg_path: str = "hearing_skg.json"):
        self.skg_path = skg_path
        self.data = self._load_skg()
    
    def _load_skg(self) -> Dict:
        """Load SKG from JSON file"""
        try:
            with open(self.skg_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            # Return default structure if file doesn't exist
            return {
                "caleon_hearing_profile": {
                    "instance_id": "caleon_cochlear_primary",
                    "attention_baseline": 0.75,
                    "frequency_sensitivity_baseline": {},
                    "learning_rate": 0.08
                },
                "phoneme_mastery": {},
                "speaker_acoustic_profiles": {},
                "contextual_attention_weights": {},
                "correction_memory": {"last_100_corrections": []}
            }
    
    def _save_skg(self):
        """Save SKG to JSON file"""
        with open(self.skg_path, 'w') as f:
            json.dump(self.data, f, indent=2)

class SKGPerceptualFilter(HumanPerceptualFilter):
    """
    Human filter + SKG acceleration = learned hearing.
    """
    
    def __init__(self, skg: SpeakerKnowledgeGraph, sample_rate=16000):
        super().__init__(sample_rate)
        self.skg = skg
        
        # Load hearing profile from SKG
        self.hearing_profile = self.skg.data["caleon_hearing_profile"]
        self.phoneme_mastery = self.skg.data.get("phoneme_mastery", {})
        self.speaker_profiles = self.skg.data.get("speaker_acoustic_profiles", {})
        
        # Initialize attention based on SKG baseline
        self.state.attention_level = self.hearing_profile["attention_baseline"]
    
    def apply_perceptual_filter(self, audio_chunk: np.ndarray, context: Dict, speaker_id: Optional[str] = None) -> Tuple[np.ndarray, Dict]:
        """
        Enhanced filter that uses SKG to pre-tune for known speakers/contexts.
        """
        # 1. Pre-load speaker-specific adjustments from SKG
        if speaker_id and speaker_id in self.speaker_profiles:
            self._apply_speaker_acoustic_profile(speaker_id)
        
        # 2. Boost attention for important contexts
        self._apply_contextual_attention_weights(context)
        
        # 3. Run base perceptual filter
        filtered_audio, perceptual_report = super().apply_perceptual_filter(audio_chunk)
        
        # 4. Phoneme-specific enhancement for low-mastery phonemes
        filtered_audio = self._enhance_difficult_phonemes(filtered_audio, context)
        
        # 5. Generate SKG-enhanced report
        perceptual_report["skg_enhancements"] = {
            "speaker_profile_applied": speaker_id,
            "attention_boost": self.state.attention_level - self.hearing_profile["attention_baseline"],
            "phoneme_enhancements_applied": self._get_active_enhancements()
        }
        
        return filtered_audio, perceptual_report
    
    def _apply_speaker_acoustic_profile(self, speaker_id: str):
        """Tune filter for a specific speaker's voice"""
        profile = self.speaker_profiles[speaker_id]
        
        # Increase attention for speakers she knows well
        if profile["mastery_score"] > 0.85:
            self.state.attention_level = min(1.0, self.state.attention_level + 0.1)
        
        # Adjust frequency sensitivity to speaker's dominant range
        dominant_freq = profile["dominant_frequency"]
        for f in self.state.frequency_sensitivity:
            if abs(f - dominant_freq) < 500:  # Within 500Hz
                self.state.frequency_sensitivity[f] *= 1.2  # Boost
    
    def _apply_contextual_attention_weights(self, context: Dict):
        """Increase attention if context contains important keywords"""
        text_context = context.get("text", "")
        for weight_rule in self.skg.data.get("contextual_attention_weights", {}).values():
            if any(trigger in text_context for trigger in weight_rule["triggers"]):
                self.state.attention_level = min(1.0, self.state.attention_level * weight_rule["weight"])
    
    def _enhance_difficult_phonemes(self, audio: np.ndarray, context: Dict) -> np.ndarray:
        """Boost frequency bands for phonemes Caleon historically mishears"""
        # FFT
        fft = np.fft.rfft(audio)
        freqs = np.fft.rfftfreq(len(audio), 1/self.sample_rate)
        
        # Find phonemes likely in this context
        likely_phonemes = self._predict_phonemes_from_context(context)
        
        for phoneme_id in likely_phonemes:
            phoneme = self.phoneme_mastery.get(phoneme_id)
            if phoneme and phoneme["mastery_score"] < 0.7:
                # Boost this phoneme's frequency range
                target_freq = phoneme["frequency_range"]
                boost_factor = 1.5 - (phoneme["mastery_score"] * 0.5)  # More boost for lower mastery
                
                for i, freq in enumerate(freqs):
                    if abs(freq - target_freq) < 300:  # ±300Hz
                        fft[i] *= boost_factor
        
        return np.fft.irfft(fft)
    
    def _predict_phonemes_from_context(self, context: Dict) -> List[str]:
        """Predict which phonemes are likely in this context"""
        # Simplified: use keyword-triggered phoneme prediction
        phoneme_triggers = {
            "AI": ["ai", "ey"],
            "machine": ["m", "sh", "n"],
            "learning": ["l", "r", "ng"],
            "the": ["th", "ee"],
            "that": ["th", "ae"]
        }
        
        text = context.get("text", "")
        likely_phonemes = set()
        
        for keyword, phonemes in phoneme_triggers.items():
            if keyword.lower() in text.lower():
                likely_phonemes.update(phonemes)
        
        return list(likely_phonemes)
    
    def _get_active_enhancements(self) -> List[str]:
        """Return list of SKG-driven enhancements applied"""
        enhancements = []
        if self.state.attention_level > 0.85:
            enhancements.append("high_attention_mode")
        if any(s > 1.1 for s in self.state.frequency_sensitivity.values()):
            enhancements.append("speaker_frequency_boost")
        return enhancements