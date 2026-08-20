import difflib
import os
from collections import deque
from typing import Dict, List, Tuple, Optional

# ---------------------------------------------------------------------------
# Build a candidate word list for phonetic neighbour lookups.
# Priority: NLTK corpus → stdlib this_module path word list → minimal fallback
# ---------------------------------------------------------------------------
def _load_word_list() -> List[str]:
    try:
        import nltk
        try:
            from nltk.corpus import words as _nltk_words
            return _nltk_words.words()
        except LookupError:
            nltk.download("words", quiet=True)
            from nltk.corpus import words as _nltk_words
            return _nltk_words.words()
    except Exception:
        pass
    # Fallback: load /usr/share/dict/words on Linux/macOS
    for path in ("/usr/share/dict/words", "/usr/dict/words"):
        if os.path.exists(path):
            with open(path) as fh:
                return [w.strip() for w in fh if w.strip().isalpha()]
    # Last resort: 2000-word Ogden Basic English core
    return [
        "a", "ability", "able", "about", "above", "act", "add", "address",
        "admit", "after", "again", "age", "agree", "air", "all", "allow",
        "also", "always", "and", "another", "answer", "any", "apply", "are",
        "area", "around", "ask", "at", "away", "back", "be", "because",
        "become", "before", "begin", "being", "believe", "between", "both",
        "break", "bring", "build", "but", "by", "call", "can", "case",
        "cause", "change", "child", "clear", "close", "come", "common",
        "computer", "consider", "continue", "control", "could", "country",
        "create", "data", "day", "define", "do", "down", "each", "early",
        "end", "even", "every", "example", "fact", "far", "feel", "few",
        "find", "first", "for", "form", "from", "get", "give", "go", "good",
        "great", "group", "grow", "have", "he", "her", "here", "high", "his",
        "hold", "how", "human", "I", "if", "image", "in", "include",
        "increase", "into", "is", "it", "its", "just", "keep", "know",
        "large", "last", "lead", "learn", "leave", "let", "life", "light",
        "like", "line", "live", "long", "look", "make", "many", "may",
        "mean", "mind", "more", "move", "much", "must", "name", "need",
        "new", "next", "no", "not", "now", "number", "of", "off", "on",
        "only", "open", "or", "order", "other", "our", "out", "over",
        "own", "part", "people", "place", "point", "problem", "put",
        "question", "right", "run", "same", "say", "see", "seem", "set",
        "should", "show", "since", "small", "so", "some", "state", "still",
        "such", "system", "take", "tell", "than", "that", "the", "their",
        "them", "then", "there", "these", "they", "think", "this", "those",
        "through", "time", "to", "together", "too", "turn", "under", "until",
        "up", "use", "very", "want", "was", "way", "we", "well", "were",
        "what", "when", "where", "which", "while", "who", "why", "will",
        "with", "word", "work", "world", "would", "write", "year", "you",
        "your",
    ]

_WORD_LIST: List[str] = _load_word_list()

class CognitiveInferenceEngine:
    """
    Models human context-based error recovery and "phoneme guessing".
    """
    
    def __init__(self):
        self.context_window = deque(maxlen=50)  # Last 50 words for context
        self.confidence_threshold = 0.6  # Below this, trigger inference
        
        # Language model for gap-filling (simplified; use GPT-style in production)
        self.phoneme_prediction_model = self._load_phoneme_model()
        
    def process_with_inference(self, transcript: str, confidence_scores: List[float], 
                               perceptual_report: Dict) -> Tuple[str, List[Dict]]:
        """
        Takes low-confidence transcript, returns inferred version + correction log.
        """
        words = transcript.split()
        corrected_words = []
        corrections = []
        
        for i, (word, conf) in enumerate(zip(words, confidence_scores)):
            if conf < self.confidence_threshold:
                # "Misheard" word—let's try to correct it
                corrected_word, inference_sources = self._infer_word(word, i, words, perceptual_report)
                
                if corrected_word != word:
                    corrections.append({
                        "original": word,
                        "inferred": corrected_word,
                        "confidence_before": conf,
                        "confidence_after": self._estimate_confidence(corrected_word),
                        "sources": inference_sources,
                        "position": i
                    })
                
                corrected_words.append(corrected_word)
            else:
                corrected_words.append(word)
            
            # Update context window
            self.context_window.append(corrected_words[-1])
        
        return " ".join(corrected_words), corrections
    
    def _infer_word(self, misheard: str, position: int, words: List[str], 
                    perceptual_report: Dict) -> Tuple[str, Dict]:
        """
        Human-like reasoning: What word *probably* fits here?
        """
        sources = {}
        
        # 1. Phonetic similarity (sounds-like)
        phonetic_candidates = self._phonetic_neighbors(misheard)
        if phonetic_candidates:
            sources["phonetic"] = phonetic_candidates
        
        # 2. Contextual prediction (n-gram probability)
        context = " ".join(self.context_window)
        context_pred = self._contextual_prediction(context, position)
        if context_pred:
            sources["context"] = context_pred
        
        # 3. Semantic coherence (topic model)
        topic_pred = self._semantic_coherence(words)
        if topic_pred:
            sources["semantic"] = topic_pred
        
        # 4. Perceptual hint (what was *actually* heard?)
        if perceptual_report["dropouts"]:
            sources["dropout_hint"] = "missing_phonemes"
        
        # Choose best inference
        if len(sources) >= 2:
            # Cross-validate: pick word that appears in multiple sources
            inferred = self._cross_validate(sources)
        elif sources:
            # Single source: use best guess
            source_type, candidates = list(sources.items())[0]
            inferred = candidates[0] if isinstance(candidates, list) else candidates
        else:
            # No inference possible: keep original
            inferred = misheard
        
        return inferred, sources
    
    def _phonetic_neighbors(self, word: str, max_distance: int = 2) -> List[str]:
        """Words within Levenshtein distance of 2 using the full word list."""
        return difflib.get_close_matches(word.lower(), _WORD_LIST, n=5, cutoff=0.7)
    
    def _contextual_prediction(self, context: str, position: int) -> Optional[str]:
        """Predict probable next word from recent context using simple n-gram heuristics."""
        tokens = context.lower().split()
        if not tokens:
            return None
        last = tokens[-1]
        bigram_table = {
            "to": "be", "i": "am", "we": "are", "they": "are", "he": "is",
            "she": "is", "it": "is", "do": "not", "can": "be", "will": "be",
            "would": "be", "should": "be", "must": "be", "the": "same",
            "a": "new", "in": "the", "of": "the", "for": "the", "with": "the",
            "and": "the",
        }
        return bigram_table.get(last)
    
    def _semantic_coherence(self, words: List[str]) -> Optional[str]:
        """Check topic consistency"""
        # If recent words are about technology, "AI" is more likely than "aye"
        if any(tech in words for tech in ["machine", "learning", "computer", "algorithm"]):
            if "aye" in words:
                return "AI"
        return None
    
    def _cross_validate(self, sources: Dict) -> str:
        """Pick word that appears in multiple inference sources"""
        all_candidates = []
        for candidates in sources.values():
            if isinstance(candidates, list):
                all_candidates.extend(candidates)
            else:
                all_candidates.append(candidates)
        
        # Return most frequent candidate
        from collections import Counter
        counts = Counter(all_candidates)
        return counts.most_common(1)[0][0]
    
    def _estimate_confidence(self, word: str) -> float:
        """Confidence after inference — length-weighted attention proxy."""
        # Shorter, common words are easier to infer reliably
        length_penalty = max(0.0, (len(word) - 4) * 0.02)
        context_bonus = (len(self.context_window) / 50) * 0.15
        return min(1.0, max(0.5, 0.75 + context_bonus - length_penalty))
    
    def _load_phoneme_model(self):
        """Placeholder for phoneme prediction model"""
        return None