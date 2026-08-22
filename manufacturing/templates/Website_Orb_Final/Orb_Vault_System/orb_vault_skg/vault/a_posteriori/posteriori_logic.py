"""
orb/vault/a_posteriori/posteriori_logic.py
Main A Posteriori Vault coordinator.
Orchestrates experience -> candidate -> verification -> promotion -> reinforcement -> pruning.
"""

from __future__ import annotations
from typing import Dict, List, Any, Optional
from datetime import datetime

from ..shared.types import (
    Experience, KnowledgeNode, KnowledgeState, ResolutionResult,
    IntentType, VerificationSignal, DegradationSignal, EntityType
)
from ..shared.confidence import ConfidenceEngine
from ..shared.constants import VaultConstants

from .ledger import ExperienceLedger
from .experience_logic import ExperienceLogic
from .experience_cognitive import ExperienceCognitiveState
from .verification_logic import VerificationLogic
from .verification_cognitive import VerificationCognitiveState
from .promotion_logic import PromotionLogic
from .promotion_cognitive import PromotionCognitiveState
from .reinforcement_logic import ReinforcementLogic
from .reinforcement_cognitive import ReinforcementCognitiveState
from .contradiction_logic import ContradictionLogic
from .contradiction_cognitive import ContradictionCognitiveState
from .pruning_logic import PruningLogic
from .pruning_cognitive import PruningCognitiveState
from .merger_logic import MergerLogic
from .merger_cognitive import MergerCognitiveState


class PosterioriVault:
    """
    A Posteriori Vault -- the learned experience layer.
    Self-improving. Self-pruning. Bounded confidence.
    """

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.ledger = ExperienceLedger(f"{data_dir}/ledger")

        self.exp_logic = ExperienceLogic()
        self.ver_logic = VerificationLogic()
        self.prom_logic = PromotionLogic()
        self.reinf_logic = ReinforcementLogic()
        self.contr_logic = ContradictionLogic()
        self.prune_logic = PruningLogic()
        self.merge_logic = MergerLogic()

        self.exp_cog = ExperienceCognitiveState()
        self.ver_cog = VerificationCognitiveState()
        self.prom_cog = PromotionCognitiveState()
        self.reinf_cog = ReinforcementCognitiveState()
        self.contr_cog = ContradictionCognitiveState()
        self.prune_cog = PruningCognitiveState()
        self.merge_cog = MergerCognitiveState()

        self._load_state()

    def _load_state(self):
        import json, os
        state_file = f"{self.data_dir}/posteriori_state.json"
        if os.path.exists(state_file):
            with open(state_file, "r") as f:
                data = json.load(f)
            for node_data in data.get("nodes", []):
                node = self._deserialize_node(node_data)
                self.exp_cog.candidate_queue[node.node_id] = node
                if node.state == KnowledgeState.PROMOTED:
                    self.prom_cog.promoted_nodes[node.node_id] = node

    def _save_state(self):
        import json
        state_file = f"{self.data_dir}/posteriori_state.json"
        all_nodes = {}
        all_nodes.update(self.exp_cog.candidate_queue)
        all_nodes.update(self.prom_cog.promoted_nodes)
        data = {
            "nodes": [self._serialize_node(n) for n in all_nodes.values()],
            "stats": self.get_stats(),
        }
        with open(state_file, "w") as f:
            json.dump(data, f, indent=2)

    def _serialize_node(self, node: KnowledgeNode) -> Dict[str, Any]:
        return {
            "node_id": node.node_id,
            "node_type": node.node_type.name,
            "content": node.content,
            "confidence_value": node.confidence.value,
            "confidence_cap": node.confidence.cap,
            "confidence_provenance": list(node.confidence.provenance),
            "state": node.state.name,
            "created_at": node.created_at.to_dict(),
            "verified_at": node.verified_at.to_dict() if node.verified_at else None,
            "promoted_at": node.promoted_at.to_dict() if node.promoted_at else None,
            "last_reinforced": node.last_reinforced.to_dict() if node.last_reinforced else None,
            "access_count": node.access_count,
            "success_streak": node.success_streak,
            "failure_streak": node.failure_streak,
            "verification_signals": {signal.name: count for signal, count in node.verification_signals.items()},
            "degradation_signals": {signal.name: count for signal, count in node.degradation_signals.items()},
            "merged_into": node.merged_into,
        }

    def _deserialize_node(self, data: Dict[str, Any]) -> KnowledgeNode:
        from ..shared.types import Confidence, DegradationSignal, VerificationSignal, VaultTimestamp
        timestamp = lambda value: VaultTimestamp(**value) if value else None
        return KnowledgeNode(
            node_id=data["node_id"],
            node_type=EntityType[data["node_type"]],
            content=data["content"],
            confidence=Confidence(
                value=data["confidence_value"],
                cap=data["confidence_cap"],
                provenance=list(data.get("confidence_provenance") or []),
            ),
            state=KnowledgeState[data["state"]],
            created_at=VaultTimestamp(**data["created_at"]),
            verified_at=timestamp(data.get("verified_at")),
            promoted_at=timestamp(data.get("promoted_at")),
            last_reinforced=timestamp(data.get("last_reinforced")),
            access_count=data.get("access_count", 0),
            success_streak=data.get("success_streak", 0),
            failure_streak=data.get("failure_streak", 0),
            verification_signals={VerificationSignal[name]: count for name, count in (data.get("verification_signals") or {}).items()},
            degradation_signals={DegradationSignal[name]: count for name, count in (data.get("degradation_signals") or {}).items()},
            merged_into=data.get("merged_into"),
        )

    # PUBLIC API

    def ingest_experience(
        self,
        query_text: str,
        detected_intent: IntentType,
        detected_entities: List[str],
        resolution_path: str,
        resolution_result: str,
        outcome_success: bool,
        session_id: str = "",
        user_feedback: Optional[str] = None
    ) -> str:
        exp = self.exp_logic.create_experience(
            query_text=query_text,
            detected_intent=detected_intent,
            detected_entities=detected_entities,
            resolution_path=resolution_path,
            resolution_result=resolution_result,
            outcome_success=outcome_success,
            session_id=session_id,
            user_feedback=user_feedback,
        )
        ledger_hash = self.ledger.append(exp)
        self.exp_cog.add_to_buffer(exp)
        self.exp_cog.index_experience(exp)

        if outcome_success:
            candidate = self.exp_logic.extract_candidate_node(exp)
            if candidate:
                self._process_candidate(candidate, exp)

        self._save_state()
        return exp.experience_id

    def query(self, query_text: str, intent: IntentType, entities: List[str]) -> ResolutionResult:
        best_match = None
        best_score = 0.0

        for node in self.prom_cog.promoted_nodes.values():
            score = self._match_score(node, query_text, intent, entities)
            if score > best_score and score > 0.6:
                best_score = score
                best_match = node

        if best_match:
            self._reinforce_node(best_match, success=True)
            return ResolutionResult(
                success=True,
                answer=best_match.content.get("resolution_result"),
                data={"confidence": best_match.confidence.value, "node_id": best_match.node_id},
                source="a_posteriori",
                confidence=best_match.confidence.value,
                entity_id=best_match.node_id,
                resolution_path=["a_posteriori", "promoted_node"],
            )

        return ResolutionResult(success=False, source="a_posteriori")

    def report_outcome(self, node_id: str, success: bool, query_text: str = ""):
        node = (
            self.prom_cog.promoted_nodes.get(node_id) or
            self.exp_cog.candidate_queue.get(node_id)
        )
        if node:
            self._reinforce_node(node, success, query_text)

    def run_maintenance(self):
        now = datetime.utcnow().timestamp()
        total = len(self.exp_cog.candidate_queue) + len(self.prom_cog.promoted_nodes)
        retired = len(self.prune_cog.retired_nodes)

        if not self.prune_logic.should_periodic_prune(total, retired, self.prune_cog.last_prune_timestamp):
            self._evaluate_promotions()
            self._save_state()
            return

        self.prune_cog.last_prune_timestamp = now
        all_nodes = {}
        all_nodes.update(self.exp_cog.candidate_queue)
        all_nodes.update(self.prom_cog.promoted_nodes)

        # 1. Time decay
        for node in list(all_nodes.values()):
            self.reinf_logic.decay_stale_knowledge(node)

        # 2. Detect contradictions
        for node in list(all_nodes.values()):
            if node.state in (KnowledgeState.RETIRED, KnowledgeState.MERGED):
                continue
            contradictions = self.contr_logic.find_all_contradictions(node, all_nodes)
            for contr in contradictions:
                self.contr_cog.register_contradiction(contr)
                node.add_degradation_signal(DegradationSignal.CONTRADICTION)

        # 3. Evaluate for pruning
        for node in list(all_nodes.values()):
            if node.state in (KnowledgeState.RETIRED, KnowledgeState.MERGED):
                continue

            action, details = self.prune_logic.evaluate_for_pruning(node)

            if action == "retire":
                self.prune_logic.execute_retire(node, details["reason"])
                self.prune_cog.archive_node(node)
                self._remove_from_active(node.node_id)
                self.prune_cog.record_prune(node.node_id, "retire", details["reason"])

            elif action == "weaken":
                self.prune_logic.execute_weaken(node, details["reason"])
                self.prune_cog.record_prune(node.node_id, "weaken", details["reason"])

            elif action == "merge":
                dupes = self.merge_logic.find_duplicates(all_nodes)
                for group in dupes:
                    if node.node_id in group:
                        canonical = self.merge_logic.merge_nodes(all_nodes, group)
                        self.merge_cog.register_canonical(canonical, group)
                        for sid in group:
                            self._remove_from_active(sid)
                        self.prom_cog.register_promotion(canonical, "merged_canonical")
                        self.prune_cog.record_prune(node.node_id, "merge", details["reason"])
                        break

            elif action == "compress":
                intent = node.content.get("intent", "")
                entities = set(node.content.get("entities", []))
                pattern = self.merge_logic.compress_cluster(all_nodes, intent, entities)
                if pattern:
                    source_ids = [
                        n.node_id for n in all_nodes.values()
                        if n.content.get("intent") == intent
                        and set(n.content.get("entities", [])) & entities
                    ]
                    self.merge_cog.register_compression(pattern, source_ids)
                    self.prom_cog.register_promotion(pattern, "compressed_pattern")

        # 4. Evaluate promotions
        self._evaluate_promotions()

        self._save_state()

    def _evaluate_promotions(self):
        """Promotion is event-driven; it must not wait for the pruning schedule."""
        for node in list(self.exp_cog.candidate_queue.values()):
            should_promote, reason = self.prom_logic.evaluate_promotion(node)
            if should_promote:
                self.prom_logic.promote(node)
                self.exp_cog.remove_candidate(node.node_id)
                self.prom_cog.register_promotion(node, reason)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "ledger": self.ledger.get_stats(),
            "candidates": self.exp_cog.get_candidate_count(),
            "promoted": self.prom_cog.get_promoted_count(),
            "pruning": self.prune_cog.get_stats(),
            "contradictions_active": len(self.contr_cog.active_contradictions),
        }

    # INTERNAL

    def _process_candidate(self, candidate: KnowledgeNode, exp: Experience):
        existing = None
        for cid, cnode in self.exp_cog.candidate_queue.items():
            if self.exp_logic.extract_intent_entity_pattern(exp) == self.exp_logic.extract_intent_entity_pattern(
                Experience(
                    experience_id="", timestamp=exp.timestamp,
                    query_text=cnode.content.get("query_pattern", ""),
                    detected_intent=exp.detected_intent,
                    detected_entities=cnode.content.get("entities", []),
                    resolution_path=cnode.content.get("resolution_path", ""),
                    resolution_result=cnode.content.get("resolution_result", ""),
                    outcome_success=True,
                )
            ):
                existing = cnode
                break

        if existing:
            aliases = existing.content.setdefault("aliases", [])
            if candidate.content.get("query_pattern") != existing.content.get("query_pattern"):
                alias = candidate.content.get("query_pattern")
                if alias and alias not in aliases:
                    aliases.append(alias)
            existing.add_verification_signal(VerificationSignal.REPETITION)
            existing.access_count += 1
            if exp.outcome_success:
                existing.success_streak += 1
            self.ver_logic.evaluate_candidate(existing, [exp])
        else:
            self.exp_cog.queue_candidate(candidate)

    def _reinforce_node(self, node: KnowledgeNode, success: bool, query_text: str = ""):
        self.reinf_logic.reinforce_from_usage(node, success, query_text)
        self.reinf_cog.record_usage(node.node_id, success, query_text)
        if node.node_id in self.prom_cog.promoted_nodes:
            self.prom_cog.promoted_nodes[node.node_id] = node

    def _match_score(self, node: KnowledgeNode, query_text: str, intent: IntentType, entities: List[str]) -> float:
        score = 0.0
        node_intent = node.content.get("intent", "")
        if node_intent == intent.name:
            score += 0.4

        node_entities = set(node.content.get("entities", []))
        query_entities = set(entities)
        if node_entities and query_entities:
            overlap = len(node_entities & query_entities) / len(node_entities | query_entities)
            score += overlap * 0.3

        patterns = [node.content.get("query_pattern", ""), *(node.content.get("aliases") or [])]
        text_sim = max((self.exp_logic._text_similarity(query_text, pattern) for pattern in patterns), default=0.0)
        exact_alias = " ".join(query_text.lower().split()) in {
            " ".join(str(pattern).lower().split()) for pattern in patterns
        }
        if exact_alias:
            text_sim = 1.0
        score += 0.7 if exact_alias else text_sim * 0.45
        score *= (0.5 + node.confidence.value * 0.5)
        return score

    def _remove_from_active(self, node_id: str):
        self.exp_cog.candidate_queue.pop(node_id, None)
        self.prom_cog.promoted_nodes.pop(node_id, None)

    def _maybe_save(self):
        self._save_state()
