import logging
import numpy as np
import time
from typing import Dict, List

logger = logging.getLogger(__name__)

class AdaptivePlasticityEngine:
    """
    Models human auditory learning: gets better at hearing specific voices, accents, contexts.
    """
    
    def __init__(self, caleon_oracle):
        self.oracle = caleon_oracle
        self.learning_rate = 0.05
        self.experience_log = []
        
        # Frequency-specific learning (which frequencies Caleon hears well)
        self.frequency_mastery = {f: 0.5 for f in np.linspace(20, 20000, 50)}
        
        # Context-specific learning (which topics/accents she understands)
        self.context_mastery = {}
    
    def log_experience(self, audio_path: str, transcription: str, corrections: List[Dict]):
        """
        Each listening experience improves future performance.
        """
        experience = {
            "timestamp": time.time(),
            "audio_path": audio_path,
            "final_transcription": transcription,
            "corrections_made": corrections,
            "difficulty_score": len(corrections) / len(transcription.split()) if transcription else 0
        }
        
        self.experience_log.append(experience)
        
        # Learn from corrections
        if corrections:
            self._update_frequency_mastery(corrections)
            self._update_context_mastery(audio_path, corrections)
        
        # Periodically adjust perceptual filter
        if len(self.experience_log) % 10 == 0:
            self._apply_learning_to_filter()
    
    def _update_frequency_mastery(self, corrections: List[Dict]):
        """Learn which frequencies cause mishearing"""
        for correction in corrections:
            # Determine phoneme frequency (simplified)
            freq_range = self._estimate_phoneme_frequency(correction["original"])
            
            # If correction was needed, reduce mastery in that range
            if correction["confidence_before"] < 0.5:
                current_mastery = self.frequency_mastery.get(freq_range, 0.5)
                # Increase mastery slightly (learning)
                new_mastery = min(1.0, current_mastery + self.learning_rate)
                self.frequency_mastery[freq_range] = new_mastery
    
    def _update_context_mastery(self, audio_path: str, corrections: List[Dict]):
        """Learn which contexts (speakers, topics) are difficult"""
        context_key = self._extract_context(audio_path)
        
        if context_key not in self.context_mastery:
            self.context_mastery[context_key] = 0.5
        
        # Adjust mastery based on correction rate
        correction_rate = len(corrections) / 10  # Normalize
        current_mastery = self.context_mastery[context_key]
        
        if correction_rate < 0.2:
            # Easy context: increase mastery
            self.context_mastery[context_key] = min(1.0, current_mastery + self.learning_rate * 2)
        else:
            # Hard context: slower learning
            self.context_mastery[context_key] = min(1.0, current_mastery + self.learning_rate * 0.5)
    
    def _apply_learning_to_filter(self):
        """Adjust perceptual filter based on learned mastery"""
        pf = self.oracle.perceptual_filter
        
        # Improve frequency sensitivity for mastered ranges
        for freq, mastery in self.frequency_mastery.items():
            if mastery > 0.8:
                # Boost sensitivity in learned ranges
                pf.state.frequency_sensitivity[freq] = min(1.0, pf.state.frequency_sensitivity.get(freq, 0.5) * 1.05)
        
        logger.debug("Hearing improved: avg mastery=%.3f", np.mean(list(self.frequency_mastery.values())))
    
    def _estimate_phoneme_frequency(self, word: str) -> float:
        """Map word to its dominant frequency band (simplified)"""
        # Vowels: lower frequencies (~200-2000 Hz)
        # Consonants: higher frequencies (~2000-8000 Hz)
        vowels = "aeiou"
        if any(v in word.lower() for v in vowels):
            return 1000.0
        else:
            return 4000.0
    
    def _extract_context(self, audio_path: str) -> str:
        """Extract context from path (speaker, topic, environment)"""
        # Example: "audio/phil_interview_tech.wav" → "phil_tech"
        parts = audio_path.split('/')[-1].replace('.wav', '').split('_')
        return f"{parts[0]}_{parts[-1]}" if len(parts) >= 2 else "general"
    
    def get_mastery_report(self) -> Dict:
        """Export learning progress"""
        return {
            "frequency_mastery": self.frequency_mastery,
            "context_mastery": self.context_mastery,
            "total_experiences": len(self.experience_log),
            "avg_difficulty": np.mean([e["difficulty_score"] for e in self.experience_log]) if self.experience_log else 0
        }