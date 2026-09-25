"""Compile the agnostic Nine-of-Clubs question registry for customer ORBs.

Orb Weaver's own showcase uses its frontend tour registry directly. Customer
clones receive a precompiled, site-bound copy instead: the semantic topology
is reusable, while wording slots and evidence bindings come from the selected
scan. The registry is advisory; the installed Governor still authorizes every
route, pointer, and consequential action.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping


REPO_ROOT = Path(__file__).resolve().parents[2]
CANONICAL_PATTERNS = REPO_ROOT / "frontend" / "src" / "tour" / "discovery" / "patterns.json"
REGISTRY_SCHEMA = "orb_weaver.website_orb.question_registry.v1"


def _load_patterns() -> list[Dict[str, Any]]:
    document = json.loads(CANONICAL_PATTERNS.read_text(encoding="utf-8"))
    patterns = document.get("patterns")
    if not isinstance(patterns, list) or len(patterns) != 50:
        raise ValueError("The canonical Nine-of-Clubs source must contain exactly 50 patterns")
    return patterns


def compile_question_registry(
    evidence: Mapping[str, Any],
    site_skg: Mapping[str, Any],
) -> Dict[str, Any]:
    """Create the clone's 50 selectable question references from scan evidence."""
    site_name = str(evidence.get("site_name") or evidence.get("domain") or "this site").strip()
    domain = str(evidence["domain"])
    site_id = str(evidence["site_id"])
    scan_id = str(evidence["scan_id"])
    patterns: list[Dict[str, Any]] = []
    for source in _load_patterns():
        pattern = json.loads(json.dumps(source))
        pattern["fallbackRendering"] = str(pattern["fallbackRendering"]).replace("{host}", site_name)
        pattern["fallbackStem"] = str(pattern["fallbackStem"]).replace("{host}", site_name)
        pattern["site_binding"] = {
            "site_name": site_name,
            "site_evidence_id": f"site:{site_id}",
            "scan_id": scan_id,
            "lexical_model": "payload/lexical_index.json",
        }
        pattern["authorization_contract"] = {
            "selection": "governor_only",
            "requires_live_verification": any(
                bool(choice.get("candidateAction", {}).get("requiresLiveVerification"))
                for choice in pattern.get("choices", [])
            ),
            "requires_explicit_consent": any(
                bool(choice.get("candidateAction", {}).get("requiresExplicitConsent"))
                for choice in pattern.get("choices", [])
            ),
        }
        patterns.append(pattern)

    return {
        "schema": REGISTRY_SCHEMA,
        "registry": "nine_of_clubs",
        "mode": "customer_clone_agnostic",
        "purpose": "Selectable question references for reducing visitor uncertainty through governed site interactions.",
        "site": {
            "site_id": site_id,
            "domain": domain,
            "name": site_name,
            "source_scan_id": scan_id,
            "source_fingerprint": site_skg.get("source_fingerprint"),
        },
        "question_count": len(patterns),
        "selection_contract": {
            "selectable_not_sequential": True,
            "one_question_per_turn": True,
            "no_generic_yes_no_exit": True,
            "do_not_repeat_answered_pattern": True,
            "answers_reduce_uncertainty_only": True,
            "site_evidence_is_not_action_authority": True,
            "governor_is_final_authority": True,
            "live_geometry_required_for_pointer_actions": True,
            "explicit_consent_required_for_consequential_actions": True,
        },
        "source": {
            "canonical_path": "frontend/src/tour/discovery/patterns.json",
            "canonical_pattern_count": 50,
            "compiled_from_scan": True,
        },
        "patterns": patterns,
    }
