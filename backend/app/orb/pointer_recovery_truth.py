"""Convert automatic pointer recovery into a safe-subset authority model.

Unverified pointers are quarantined rather than globally blocking already proven
points. Multi-render recovery promotions become VERIFIED only when the existing
recovery reconciler has found the same durable, unique identity across its
independent browser renders. This implements the product rule: missing is
acceptable; wrong is not.
"""

from __future__ import annotations

from datetime import datetime, timezone
from functools import wraps
from typing import Any, Dict


def install_safe_subset_pointer_recovery() -> None:
    from app.orb import pointer_recovery

    original = pointer_recovery.reconcile_pointer_recovery
    if getattr(original, "_orb_safe_subset_truth_installed", False):
        return

    @wraps(original)
    def truth_reconcile(baseline_map: Dict[str, Any], capture: Dict[str, Any]) -> Dict[str, Any]:
        result = original(baseline_map, capture)
        auto_verified = 0
        quarantined = 0
        now = datetime.now(timezone.utc).isoformat()

        for record in result.get("records") or []:
            if not isinstance(record, dict):
                continue
            recovery_status = str(record.get("recovery_status") or "")
            if recovery_status == "promoted":
                evidence = dict(record.get("confidence_evidence") or {})
                verification = str(evidence.get("verification_resolution") or "")
                if verification != "consistent_across_recovery_renders":
                    # A promotion without the expected two-render evidence cannot
                    # acquire runtime authority.
                    record["recovery_status"] = "quarantined"
                    record["status"] = "quarantined"
                    record["confidence_class"] = "UNVERIFIED"
                    record["lifecycle_state"] = "QUARANTINED"
                    record["pointer_health"] = "QUARANTINED"
                    record["runtime_policy"] = {
                        "behavior": "explain_without_unverified_point",
                        "may_point": False,
                        "must_verify_before_action": True,
                        "requires_confirmation": True,
                    }
                    quarantined += 1
                    continue

                record["confidence_class"] = "VERIFIED"
                record["lifecycle_state"] = "REVERIFIED"
                record["pointer_health"] = "VERIFIED"
                record["recovery_status"] = "auto_verified"
                record["runtime_policy"] = {
                    "behavior": "guide_and_live_verify_before_action",
                    "may_point": True,
                    "must_verify_before_action": True,
                    "requires_confirmation": False,
                }
                evidence.update({
                    "sentinel_resolution": "pointer_recovery_multi_render_rescan_passed",
                    "automatic_verification_authority": "durable_unique_identity_across_independent_renders",
                    "last_verified_time": now,
                })
                record["confidence_evidence"] = evidence
                record["last_verified_at"] = now
                auto_verified += 1
            elif recovery_status == "visual_review_required":
                # Keep evidence for later repair but remove the record from the
                # active runtime set. It cannot globally veto proven pointers.
                record["recovery_status"] = "quarantined"
                record["status"] = "quarantined"
                record["confidence_class"] = "UNVERIFIED"
                record["lifecycle_state"] = "QUARANTINED"
                record["pointer_health"] = "QUARANTINED"
                record["runtime_policy"] = {
                    "behavior": "explain_without_unverified_point",
                    "may_point": False,
                    "must_verify_before_action": True,
                    "requires_confirmation": True,
                }
                quarantined += 1

        recovery = dict(result.get("recovery") or {})
        originally_unresolved = int(recovery.get("unresolved_count") or 0)
        recovery.update({
            "auto_verified_count": auto_verified,
            "quarantined_count": max(quarantined, originally_unresolved),
            "active_unresolved_count": 0,
            # Compatibility: lifecycle uses unresolved_count as an active-runtime
            # blocker. Quarantined records are intentionally outside that set.
            "unresolved_count": 0,
            "safe_subset_policy": "verified_points_active_unverified_points_quarantined",
        })
        result["recovery"] = recovery
        result["quality"] = pointer_recovery.assess_pointer_quality(result)
        result["guidance_authority"] = {
            "policy": "verified_subset_only",
            "verified_count": pointer_recovery.guidance_eligible_pointer_count(result),
            "quarantined_count": recovery["quarantined_count"],
            "wrong_target_tolerance": 0,
        }
        return result

    setattr(truth_reconcile, "_orb_safe_subset_truth_installed", True)
    pointer_recovery.reconcile_pointer_recovery = truth_reconcile


__all__ = ["install_safe_subset_pointer_recovery"]
