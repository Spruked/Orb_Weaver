"""
orb/vault/a_priori/qa_cognitive.py
Cognitive state for QA storage.
"""

from __future__ import annotations
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from ..shared.types import QACorrespondence, IntentType


@dataclass
class QACognitiveState:
    """
    QA correspondence storage with intent indexing.
    """

    qa_pairs: Dict[str, QACorrespondence] = field(default_factory=dict)
    intent_index: Dict[IntentType, List[str]] = field(default_factory=dict)
    keyword_index: Dict[str, List[str]] = field(default_factory=dict)

    def add_qa(self, qa: QACorrespondence):
        self.qa_pairs[qa.qa_id] = qa
        if qa.intent not in self.intent_index:
            self.intent_index[qa.intent] = []
        self.intent_index[qa.intent].append(qa.qa_id)
        for pattern in qa.question_patterns:
            tokens = pattern.lower().split()
            for token in tokens:
                if len(token) > 3:
                    if token not in self.keyword_index:
                        self.keyword_index[token] = []
                    self.keyword_index[token].append(qa.qa_id)

    def get_by_intent(self, intent: IntentType) -> List[QACorrespondence]:
        ids = self.intent_index.get(intent, [])
        return [self.qa_pairs[qid] for qid in ids if qid in self.qa_pairs]

    def get_by_keyword(self, keyword: str) -> List[QACorrespondence]:
        ids = self.keyword_index.get(keyword.lower(), [])
        return [self.qa_pairs[qid] for qid in ids if qid in self.qa_pairs]

    def get_all(self) -> Dict[str, QACorrespondence]:
        return dict(self.qa_pairs)
