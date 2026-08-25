"""Truth-first pointer extraction policy.

Initial DOM extraction establishes a candidate identity; it does not establish
verification. This adapter prevents confidence heuristics from granting point
authority until the independent browser verification/recovery path has observed
the same intended element across fresh renders.
"""

from __future__ import annotations

from typing import Any, Dict


def install_pointer_truth_policy(pointer_plot_module) -> None:
    if getattr(pointer_plot_module, "_orb_pointer_truth_policy_installed", False):
        return

    original_extract = pointer_plot_module.extract_pointer_plot_records

    def truth_first_extract(*args, **kwargs):
        records = original_extract(*args, **kwargs)
        for record in records:
            if not isinstance(record, dict):
                continue

            # Confidence is useful ranking evidence, never verification evidence.
            record["candidate_confidence"] = float(record.get("confidence") or 0.0)
            record["confidence_class"] = "UNVERIFIED"
            record["lifecycle_state"] = "CANDIDATE"
            record["finding_class"] = "UNVERIFIED"
            record["finding_subreason"] = "initial_extraction_not_independently_verified"
            record["pointer_health"] = "NEW"
            record["runtime_policy"] = {
                "behavior": "candidate_only_until_independent_verification",
                "may_point": False,
                "must_verify_before_action": True,
                "requires_confirmation": True,
            }

            evidence: Dict[str, Any] = dict(record.get("confidence_evidence") or {})
            evidence["baseline_resolution"] = "observed_once"
            evidence["verification_resolution"] = "not_run"
            evidence["sentinel_resolution"] = "not_run"
            evidence.pop("last_verified_time", None)
            record["confidence_evidence"] = evidence
            record.pop("last_verified_at", None)

        return records

    pointer_plot_module.extract_pointer_plot_records = truth_first_extract
    pointer_plot_module._orb_pointer_truth_policy_installed = True
