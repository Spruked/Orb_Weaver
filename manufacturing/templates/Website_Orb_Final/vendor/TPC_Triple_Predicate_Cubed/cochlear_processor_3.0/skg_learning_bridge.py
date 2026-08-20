import time
import numpy as np
from typing import Dict, List
from skg_perceptual_filter import SpeakerKnowledgeGraph, SKGPerceptualFilter

class SKGLearningBridge:
    """
    Connects Cochlear Processor corrections back to SKG for permanent learning.
    """
    
    def __init__(self, skg: SpeakerKnowledgeGraph, processor: SKGPerceptualFilter):
        self.skg = skg
        self.processor = processor
        self.learning_batch = []
    
    def process_correction(self, correction: Dict):
        """
        A single correction becomes permanent knowledge.
        correction: {
            "original": "aye",
            "corrected": "AI",
            "phoneme": "ai",
            "context": "podcast_tech",
            "speaker": "phil_dandy",
            "confidence_delta": 0.35
        }
        """
        
        # 1. Update phoneme mastery
        self._update_phoneme_mastery(correction)
        
        # 2. Update speaker acoustic profile
        self._update_speaker_profile(correction)
        
        # 3. Store in correction memory
        self._log_correction(correction)
        
        # 4. Batch save to SKG (don't write every single correction)
        self.learning_batch.append(correction)
        
        if len(self.learning_batch) >= 10:
            self._commit_learning()
    
    def _update_phoneme_mastery(self, correction: Dict):
        """Increase mastery for correctly inferred phoneme"""
        phoneme_id = correction["phoneme"]
        if phoneme_id not in self.skg.data["phoneme_mastery"]:
            self.skg.data["phoneme_mastery"][phoneme_id] = {
                "phoneme": phoneme_id,
                "frequency_range": self._estimate_phoneme_freq(phoneme_id),
                "mastery_score": 0.5,
                "mishearing_history": [],
                "corrective_patterns": []
            }
        
        phoneme = self.skg.data["phoneme_mastery"][phoneme_id]
        
        # Increase mastery (moving average)
        learning_rate = self.skg.data["caleon_hearing_profile"]["learning_rate"]
        phoneme["mastery_score"] = (phoneme["mastery_score"] * (1 - learning_rate)) + (0.95 * learning_rate)
        
        # Log mishearing for pattern analysis
        phoneme["mishearing_history"].append({
            "timestamp": time.time(),
            "misheard_as": correction["original"],
            "context": correction["context"],
            "confidence_before": 0.55  # Simulated
        })
        
        # Store corrective pattern
        corrective_pattern = self._derive_corrective_pattern(correction)
        if corrective_pattern not in phoneme["corrective_patterns"]:
            phoneme["corrective_patterns"].append(corrective_pattern)
        
        print(f"📈 Phoneme '{phoneme_id}' mastery: {phoneme['mastery_score']:.3f}")
    
    def _update_speaker_profile(self, correction: Dict):
        """Learn speaker-specific acoustic quirks"""
        speaker_id = correction["speaker"]
        if speaker_id not in self.skg.data["speaker_acoustic_profiles"]:
            self.skg.data["speaker_acoustic_profiles"][speaker_id] = {
                "speaker_id": speaker_id,
                "dominant_frequency": 2000.0,
                "formant_signature": {},
                "mastery_score": 0.5,
                "common_mishearings": {}
            }
        
        profile = self.skg.data["speaker_acoustic_profiles"][speaker_id]
        
        # Increase speaker mastery
        profile["mastery_score"] = min(1.0, profile["mastery_score"] + 0.02)
        
        # Log mishearing pattern
        mishearing_type = f"{correction['phoneme']}_as_{correction['original']}"
        profile["common_mishearings"][mishearing_type] = (
            profile["common_mishearings"].get(mishearing_type, 0) + 1
        )
        
        print(f"📈 Speaker '{speaker_id}' mastery: {profile['mastery_score']:.3f}")
    
    def _derive_corrective_pattern(self, correction: Dict) -> str:
        """Translate correction into actionable voice adjustment"""
        
        # Example mapping
        if correction["phoneme"] == "ai":
            return "increase_formant_f2"
        elif correction["phoneme"] == "th":
            return "enhance_high_freq"
        elif correction.get("confidence_delta", 0) > 0.3:
            return "reduce_speaking_rate"
        
        return "general_clarity_boost"
    
    def _estimate_phoneme_freq(self, phoneme: str) -> float:
        """Estimate frequency range for a phoneme"""
        freq_map = {
            "ai": 1800.0,
            "th": 4000.0,
            "s": 6000.0,
            "m": 250.0,
            "sh": 3000.0
        }
        return freq_map.get(phoneme, 2000.0)
    
    def _log_correction(self, correction: Dict):
        """Add correction to memory (keep last 100)"""
        self.skg.data["correction_memory"]["last_100_corrections"].append({
            "timestamp": time.time(),
            **correction
        })
        
        # Keep only last 100
        corrections = self.skg.data["correction_memory"]["last_100_corrections"]
        if len(corrections) > 100:
            self.skg.data["correction_memory"]["last_100_corrections"] = corrections[-100:]
    
    def _commit_learning(self):
        """Batch-write learning to SKG"""
        
        print(f"💾 Committing {len(self.learning_batch)} corrections to SKG...")
        
        # Update SKG on disk
        self.skg._save_skg()
        
        # Clear batch
        self.learning_batch = []
        
        # Also update processor's in-memory state
        self.processor.phoneme_mastery = self.skg.data["phoneme_mastery"]
        self.processor.speaker_profiles = self.skg.data["speaker_acoustic_profiles"]
    
    def get_mastery_report(self) -> Dict:
        """Export learning progress"""
        phoneme_scores = {k: v["mastery_score"] for k, v in self.skg.data["phoneme_mastery"].items()}
        speaker_scores = {k: v["mastery_score"] for k, v in self.skg.data["speaker_acoustic_profiles"].items()}
        
        return {
            "phoneme_mastery": phoneme_scores,
            "speaker_mastery": speaker_scores,
            "total_corrections": len(self.skg.data["correction_memory"]["last_100_corrections"]),
            "avg_phoneme_mastery": np.mean(list(phoneme_scores.values())) if phoneme_scores else 0.5,
            "avg_speaker_mastery": np.mean(list(speaker_scores.values())) if speaker_scores else 0.5
        }
