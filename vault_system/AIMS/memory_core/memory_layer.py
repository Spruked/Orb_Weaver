"""
memory_layer.py
CognitiveMemoryLayer — the single import a host system needs.

Wires the three tiers together into one interface:

    write(...)            -> STM (fast, cheap, may be forgotten)
    commit(...)            -> LTM (permanent, hash+glyph+tri-timestamp chained)
    judge(...)             -> Vault (distilled claim, a priori or a posteriori)
    link(...) / truth(...) -> SKG  (relations + the queryable source of truth)
    run_maintenance_cycle() -> sweeps STM, prunes/improves the Vault, and
                                runs a recursive self-evaluation pass over
                                the SKG — this is the "gets better over
                                time on its own" hook a host system should
                                call periodically (e.g. on an idle timer
                                or after N writes).

Nothing in this file assumes an LLM, an agent identity, a mission
system, or any external time/identity authority. Any system with
"things worth remembering, judging, and revisiting" can adopt it by
constructing one CognitiveMemoryLayer against a local directory.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Union

from .long_term import LongTermMemory, EntryType, ImmutableEntry
from .short_term import ShortTermMemory, STMItem
from .vault import Vault, VaultAtom, VaultType
from .skg import SKGBackend, SKGTrio, Relation
from .indexes import VaultIndexes
from .retrieval_ledger import RetrievalLedger
from .session_memory import SessionMemory
from .outcomes import OutcomeSignal
from .schema import SCHEMA_VERSION, SchemaManager
from .maintenance import memory_telemetry_snapshot


_RETRIEVAL_MODE_MAP = {
    "PRIOR_ONLY": "a_priori",
    "POSTERIOR_ONLY": "a_posteriori",
    "COLLECTIVE": "collective",
    # Backward-compatible internal spellings.
    "A_PRIORI": "a_priori",
    "A_POSTERIORI": "a_posteriori",
}


class AIMSMemorySystem:
    def __init__(
        self,
        store_path: Path,
        matrix_id: str = "long_term_matrix",
        stm_capacity: int = 500,
        stm_decay_half_life_seconds: float = 900.0,
        glyph_key: Optional[Union[str, bytes]] = None,
        glyph_key_id: Optional[str] = None,
        glyph_keys: Optional[Mapping[str, Union[str, bytes]]] = None,
        security_mode: Optional[str] = None,
        skg_backend_factory: Optional[Callable[[str], SKGBackend]] = None,
    ):
        self.store_path = Path(store_path)
        self.schema = SchemaManager(self.store_path)
        self.long_term = LongTermMemory(
            self.store_path,
            matrix_id=matrix_id,
            glyph_key=glyph_key,
            glyph_key_id=glyph_key_id,
            glyph_keys=glyph_keys,
            security_mode=security_mode,
        )
        self.short_term = ShortTermMemory(
            capacity=stm_capacity, decay_half_life_seconds=stm_decay_half_life_seconds
        )
        self.vault = Vault(
            self.store_path,
            matrix_id=matrix_id,
            glyph_key=glyph_key,
            glyph_key_id=glyph_key_id,
            glyph_keys=glyph_keys,
            security_mode=security_mode,
        )
        self.skg_trio = SKGTrio(self.vault, backend_factory=skg_backend_factory)
        # v0.2 compatibility surface. New host integrations should prefer
        # `skg_trio` to make domain ownership explicit.
        self.skg = self.skg_trio
        self.indexes = VaultIndexes(self.store_path / "indexes" / "vault_indexes.sqlite")
        self.indexes.rebuild(self.vault)
        self.retrieval_ledger = RetrievalLedger(self.store_path / "retrieval" / "retrieval_ledger.sqlite")
        self.sessions: Dict[str, SessionMemory] = {}

    # ---------- short-term ingress ----------

    def observe(self, content: Dict[str, Any], tags: Optional[List[str]] = None) -> STMItem:
        """Fast, cheap, possibly-forgotten intake. Use for raw perception
        / candidate facts that haven't earned permanence or judgment yet.
        """
        return self.short_term.put(content, tags=tags)

    def start_session(self, session_id: Optional[str] = None) -> SessionMemory:
        session = SessionMemory(session_id)
        self.sessions[session.session_id] = session
        return session

    def remember_session_event(self, session_id: str, kind: str, payload: Dict[str, Any],
                               tags: Optional[List[str]] = None, relevance: float = 0.5) -> Dict[str, Any]:
        session = self.sessions.get(session_id) or self.start_session(session_id)
        return session.record(kind, payload, tags, relevance).to_dict()

    def session_context(self, session_id: str, query: str = "", limit: int = 24) -> Dict[str, Any]:
        session = self.sessions.get(session_id)
        if not session: raise ValueError("Unknown active session")
        return {"session": session.summary(), "context": session.context(query, limit)}

    def finalize_session_outcome(
        self, session_id: str, outcome: Dict[str, Any], writer_id: str = "system",
        visitor_key: Optional[str] = None, site_scope: Optional[str] = None,
    ) -> ImmutableEntry:
        """Persist only an explicit durable outcome package, never raw session events."""
        session = self.sessions.get(session_id)
        if not session: raise ValueError("Unknown active session")
        allowed = {"goals", "decisions", "completed_actions", "successful_tools", "unresolved_items", "evidence_references", "outcome"}
        package = {key: value for key, value in outcome.items() if key in allowed}
        # The durable package is intentionally an allowlist: raw session events
        # and transcript content never cross this boundary.
        if visitor_key:
            package["visitor_key"] = visitor_key
        if site_scope:
            package["site_scope"] = site_scope
        package["session_event_count"] = len(session.events())
        return self.commit(EntryType.LEARNING, {"event": "session_outcome", "outcome_package": package},
                           metadata={"durable_outcome": True}, writer_id=writer_id)

    def retrieve_prior_session_outcomes(
        self, visitor_key: str, query: str = "", limit: int = 4,
        site_scope: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve only explicit durable outcome packages for a recognized visitor.

        Long-term entries remain immutable source records. This method returns
        a small relevant view and never rehydrates volatile raw-session events.
        """
        terms = {term.casefold() for term in query.split() if term}
        matches: List[Dict[str, Any]] = []
        for entry in self.long_term.iterate_entries():
            if entry.entry_type != EntryType.LEARNING:
                continue
            content = entry.content
            if content.get("event") != "session_outcome":
                continue
            package = content.get("outcome_package")
            if not isinstance(package, dict) or package.get("visitor_key") != visitor_key:
                continue
            # A scoped caller must never receive legacy or differently scoped
            # records. Unscoped retrieval remains available to the core API's
            # existing callers, but Website ORB always supplies a scope.
            if site_scope and package.get("site_scope") != site_scope:
                continue
            searchable = " ".join(str(package.get(key, "")) for key in (
                "goals", "decisions", "completed_actions", "successful_tools",
                "unresolved_items", "evidence_references", "outcome",
            )).casefold()
            score = (sum(term in searchable for term in terms) / max(1, len(terms))) if terms else 0.0
            matches.append({
                "entry_id": entry.entry_id,
                "outcome_package": {key: value for key, value in package.items() if key != "visitor_key"},
                "context_score": score,
                "recorded_at": entry.tri_timestamp.standard,
            })
        return sorted(matches, key=lambda item: (-item["context_score"], item["recorded_at"]), reverse=False)[:max(1, limit)]

    def reinforce_observation(self, item_id: str) -> Optional[STMItem]:
        return self.short_term.touch(item_id)

    # ---------- long-term commit ----------

    def commit(
        self,
        entry_type: EntryType,
        content: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        writer_id: str = "system",
    ) -> ImmutableEntry:
        """Permanent, hash+glyph+tri-timestamp chained write. Use for
        anything that must never be silently forgotten, whether or not
        it has been judged true yet.
        """
        return self.long_term.write_entry(entry_type, content, metadata=metadata, writer_id=writer_id)

    def rotate_glyph_key(self, new_key: Union[str, bytes], new_key_id: str, writer_id: str = "system") -> Dict[str, ImmutableEntry]:
        """Rotate both authoritative ledgers while retaining historical key IDs."""
        vault_ledger = self.vault.event_ledger
        if vault_ledger is None:
            raise RuntimeError("Persistent Vault ledger is required for key rotation")
        vault_event = vault_ledger.rotate_glyph_key(new_key, new_key_id, writer_id=writer_id)
        memory_event = self.long_term.rotate_glyph_key(new_key, new_key_id, writer_id=writer_id)
        return {"vault_event": vault_event, "memory_event": memory_event}

    # ---------- vault admission ----------

    def assert_apriori(self, statement: str, metadata: Optional[Dict[str, Any]] = None,
                       authority_class: str = "assertion") -> VaultAtom:
        """Declare a foundational axiom. Not derived from any entry;
        asserted by design. Immune to pruning below its confidence floor.
        """
        atom = self.vault.add_apriori(statement, metadata=metadata, authority_class=authority_class)
        self.indexes.upsert(atom)
        return atom

    def derive_aposteriori(
        self,
        statement: str,
        source_entries: List[ImmutableEntry],
        metadata: Optional[Dict[str, Any]] = None,
        initial_confidence: float = 0.5, authority_class: str = "assertion",
    ) -> VaultAtom:
        """Distill a claim from one or more committed long-term entries.
        Starts on probation; earns ACTIVE status (and counts toward
        source_of_truth()) only through reinforcement over time.
        """
        atom = self.vault.add_aposteriori(
            statement,
            derived_from=[e.entry_id for e in source_entries],
            metadata=metadata,
            initial_confidence=initial_confidence, authority_class=authority_class,
        )
        # Long-term records are immutable provenance, not SKG nodes. The atom
        # retains their entry IDs in `derived_from`; graph edges are Vault atom
        # relationships and are routed by epistemic domain.
        self.indexes.upsert(atom)
        return atom

    def promote_from_short_term(
        self,
        item: STMItem,
        statement: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> VaultAtom:
        """Take an STM candidate (see ShortTermMemory.promotion_candidates)
        and give it a permanent home: commit it to long-term memory, then
        distill it into an a posteriori vault atom in one step.
        """
        entry = self.commit(
            EntryType.OBSERVATION,
            content=item.content,
            metadata={**(metadata or {}), "promoted_from_stm": item.item_id, "tags": item.tags},
        )
        return self.derive_aposteriori(statement, [entry], metadata=metadata)

    # ---------- relations ----------

    def link(self, source_atom_id: str, target_atom_id: str, relation: Relation, weight: float = 1.0):
        return self.skg.link(source_atom_id, target_atom_id, relation, weight=weight)

    def retrieve(
        self, query: str, mode: str = "COLLECTIVE", limit: int = 20,
        site_scope: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Route a public retrieval mode through its derived index and receipt it."""
        requested_mode = mode.upper()
        try:
            index_name = _RETRIEVAL_MODE_MAP[requested_mode]
        except KeyError as error:
            raise ValueError("mode must be PRIOR_ONLY, POSTERIOR_ONLY, or COLLECTIVE") from error
        results = self.indexes.search(
            self.vault, query, index_name=index_name, limit=limit,
            utilities=self.retrieval_ledger.utilities(), skg_weight_for=self.skg.relevance_weight,
            metadata_filter=(lambda metadata: metadata.get("site_scope") == site_scope) if site_scope else None,
        )
        return self.retrieval_ledger.record(requested_mode, query, results)

    def retrieval(self, retrieval_id: str) -> Optional[Dict[str, Any]]:
        return self.retrieval_ledger.get(retrieval_id)

    def record_retrieval_feedback(self, retrieval_id: str, useful_atom_ids: List[str]) -> str:
        return self.evaluate_cognitive_outcome(retrieval_id, useful_atom_ids=useful_atom_ids)["feedback_id"]

    def evaluate_cognitive_outcome(
        self, retrieval_id: str, cognitive_event_id: Optional[str] = None, outcome_id: Optional[str] = None,
        useful_atom_ids: Optional[List[str]] = None, harmful_atom_ids: Optional[List[str]] = None,
        irrelevant_atom_ids: Optional[List[str]] = None, evidence_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Link a returned set to an outcome, durable utility, and SKG changes."""
        receipt = self.retrieval(retrieval_id)
        if receipt is None:
            raise ValueError("Unknown retrieval_id")
        useful, harmful = useful_atom_ids or [], harmful_atom_ids or []
        feedback = self.retrieval_ledger.record_feedback(
            retrieval_id, useful, harmful, irrelevant_atom_ids or [], cognitive_event_id,
            outcome_id, evidence_ids or [],
        )
        evaluation = self.vault.record_cognitive_evaluation({
            "retrieval_id": retrieval_id, "retrieval_set_hash": receipt["retrieval_set_hash"],
            "cognitive_event_id": cognitive_event_id, "outcome_id": outcome_id,
            "useful_atom_ids": useful, "harmful_atom_ids": harmful,
            "irrelevant_atom_ids": irrelevant_atom_ids or [], "evidence_ids": evidence_ids or [],
            "utility_changes": feedback["utility_changes"], "tri_timestamp": feedback["tri_timestamp"],
        })
        edges = self.skg.update_edges_from_outcome(useful, harmful, evidence_ids or [])
        return {**feedback, "evaluation": evaluation, "updated_edges": [edge.to_dict() for edge in edges]}

    def record_outcome_signal(self, signal: OutcomeSignal) -> Dict[str, Any]:
        outcome = self.retrieval_ledger.record_outcome_signal(signal)
        edge_updates = []
        if signal.is_material and signal.retrieval_id:
            receipt = self.retrieval(signal.retrieval_id)
            atom_ids = []
            for result in (receipt or {}).get("results", []):
                payload = result.get("returned_payload_snapshot") or result
                atom_id = payload.get("atom_id") if isinstance(payload, dict) else None
                if atom_id:
                    atom_ids.append(atom_id)
            positive = signal.outcome in {"successful", "completed", "useful", "resolved"}
            negative = signal.outcome in {"failed", "harmful", "abandoned", "irrelevant"}
            if positive or negative:
                edge_updates = self.skg.update_edges_from_outcome(
                    atom_ids if positive else [], atom_ids if negative else [], signal.evidence_ids,
                )
        evaluation = self.vault.record_cognitive_evaluation({
            "outcome_signal": outcome,
            "derived_edge_updates": [edge.to_dict() for edge in edge_updates],
        })
        return {**outcome, "evaluation": evaluation,
                "updated_edges": [edge.to_dict() for edge in edge_updates]}

    def maintenance_snapshot(self) -> Dict[str, Any]:
        return memory_telemetry_snapshot(self, SCHEMA_VERSION, self.schema.version)

    def merge_skg_nodes(self, canonical_atom_id: str, merged_atom_ids: List[str], reason: str = "identity_reconciled") -> Dict[str, str]:
        return self.skg.merge_nodes(canonical_atom_id, merged_atom_ids, reason)

    # ---------- query surface ----------

    def truth(self, min_confidence: float = 0.0) -> List[Dict[str, Any]]:
        """The current source of truth: active, sufficiently-confident
        vault atoms, with their support/contradiction/derivation edges.
        This is what the rest of a host system should consult when it
        needs to know 'what does this system currently believe.'
        """
        return self.skg.source_of_truth(min_confidence=min_confidence)

    def trace(self, atom_id: str) -> Dict[str, Any]:
        """Walk an atom back to the primary long-term entries it was
        derived from, for audit / explainability.
        """
        atom = self.vault.get(atom_id)
        if not atom:
            return {}
        entries = [
            self.long_term.read_entry(entry_id=eid).to_dict()
            for eid in atom.derived_from
            if self.long_term.read_entry(entry_id=eid)
        ]
        return {"atom": atom.to_dict(), "primary_entries": entries}

    # ---------- maintenance ----------

    def run_maintenance_cycle(self, self_eval_passes: int = 3) -> Dict[str, Any]:
        """The self-tending heartbeat: forget what STM no longer needs,
        prune/improve the vault, and recursively re-evaluate the SKG so
        that newer knowledge can retroactively change older standing.
        Call this periodically (idle timer, after N commits, etc.) —
        nothing about this layer requires it to run on any fixed clock.
        """
        stm_evicted = self.short_term.sweep()
        eval_summary = self.skg.recursive_self_evaluate(max_passes=self_eval_passes)
        self.indexes.rebuild(self.vault)
        return {
            "stm_evicted": stm_evicted,
            "stm_stats": self.short_term.stats(),
            "self_evaluation": eval_summary,
            "vault_stats": self.vault.stats(),
            "ltm_stats": self.long_term.get_statistics(),
        }

    def full_status(self) -> Dict[str, Any]:
        return {
            "long_term": self.long_term.get_statistics(),
            "short_term": self.short_term.stats(),
            "vault": self.vault.stats(),
            "skg": self.skg.stats(),
            "indexes": self.indexes.status(),
            "schema_version": self.schema.version,
            "active_sessions": len(self.sessions),
            "outcomes": self.retrieval_ledger.outcome_statistics(),
        }

    def close(self) -> None:
        """Release optional derived backend resources; Vault records remain open authority."""
        self.skg_trio.close()


# Compatibility alias for hosts using the pre-A.I.M.S. class name.
CognitiveMemoryLayer = AIMSMemorySystem
