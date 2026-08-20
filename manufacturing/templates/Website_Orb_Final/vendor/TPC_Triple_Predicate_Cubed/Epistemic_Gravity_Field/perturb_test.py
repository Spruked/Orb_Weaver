"""
perturb_test.py
Controlled Perturbation Test for Epistemic Gravity Field
Validates that gravity breaks under inversion and re-forms upon restoration
"""

import numpy as np
import torch

from space_field import SpaceFieldCognition, SpaceFieldConfig


# If SpaceFieldConfig were frozen, you could unfreeze via this wrapper:
# def unfreeze_config(field):
#     object.__setattr__(field.config, "_frozen", False)


def run_controlled_perturbation(
    field: SpaceFieldCognition,
    baseline_steps: int = 1000,
    perturb_steps: int = 400,
    recovery_steps: int = 1000,
    log_every: int = 25,
    max_pressure: float = 0.02,
):
    """
    Three-phase validation:
    1. BASELINE: Establish epistemic gravity (center certain, outer exploratory)
    2. PERTURB: Invert temperature + swap cadence (break gravity on purpose)
    3. RECOVERY: Restore defaults (verify gravity re-forms as an attractor)
    """

    cfg = field.config

    # Capture original physics parameters
    defaults = {
        "TEMP_MIN": cfg.TEMP_MIN,
        "TEMP_MAX": cfg.TEMP_MAX,
        "CENTER_UPDATE_EVERY": cfg.CENTER_UPDATE_EVERY,
        "OUTER_UPDATE_EVERY": cfg.OUTER_UPDATE_EVERY,
    }

    def log_stats(phase: str, step: int):
        stats = field.get_field_stats()
        c = stats["center_entropy"]
        o = stats["outer_entropy"]
        p = stats["renewal_pressure"]
        gap = o - c  # Positive = gravity intact (outer chaotic, center certain)
        print(
            f"[{phase}] step={step:5d} | center={c:.4f} | outer={o:.4f} | "
            f"gap={gap:+.4f} | pressure={p*100:.2f}%"
        )
        return c, o, p, gap

    baseline_gaps = []
    perturb_gaps = []
    recovery_gaps = []
    all_pressures = []

    print("\n" + "=" * 70)
    print("CONTROLLED PERTURBATION TEST - EPISTEMIC GRAVITY VALIDATION")
    print("=" * 70)

    # ==========================================
    # PHASE A: BASELINE (Gravity Establishment)
    # ==========================================
    print("\n>>> PHASE A: BASELINE (establishing lawful gravity)...")
    for i in range(1, baseline_steps + 1):
        field.step()
        if i % log_every == 0:
            _, _, _, gap = log_stats("BASE", field.step_count)
            baseline_gaps.append(gap)

    mean_baseline = np.mean(baseline_gaps)
    print(
        f"\n[BASELINE RESULT] Mean gravity gap: {mean_baseline:+.4f} "
        f"(target: >0.05, got: {'✓' if mean_baseline > 0 else '✗'})"
    )

    assert mean_baseline > 0, (
        f"BASELINE FAIL: Gravity not established (gap={mean_baseline:.4f}). "
        f"Field may need longer warmup or geometry is broken."
    )

    # ==========================================
    # PHASE B: PERTURB (Intentional Destruction)
    # ==========================================
    print("\n>>> PHASE B: PERTURB (inverting gravity via geometry)...")
    print("     Inverting temperature gradient (center→hot, outer→cold)...")
    print("     Swapping update cadence (center slows, outer accelerates)...")

    # Modify config
    cfg.TEMP_MIN, cfg.TEMP_MAX = defaults["TEMP_MAX"], defaults["TEMP_MIN"]
    cfg.CENTER_UPDATE_EVERY, cfg.OUTER_UPDATE_EVERY = (
        defaults["OUTER_UPDATE_EVERY"],
        defaults["CENTER_UPDATE_EVERY"],
    )

    # Invert precomputed temperature tensor around midpoint
    t = field.cubes.temperature
    field.cubes.temperature = t.max() + t.min() - t

    for i in range(1, perturb_steps + 1):
        field.step()
        if i % log_every == 0:
            _, _, p, gap = log_stats("PERT", field.step_count)
            perturb_gaps.append(gap)
            all_pressures.append(p)

    mean_perturb = np.mean(perturb_gaps)
    max_perturb = np.max(perturb_gaps)
    print(f"\n[PERTURB RESULT] Mean gap: {mean_perturb:+.4f} | Max gap: {max_perturb:+.4f}")
    print("     Target: gravity should break (gap ≤ 0 at least briefly)")

    # Perturb success = gravity broke (gap went negative or flat)
    assert max_perturb <= 0 or mean_perturb < 0, (
        f"PERTURB FAIL: Gravity survived inversion (gap stayed positive). "
        f"This suggests hard-coded geometry that can't adapt."
    )
    print("     ✓ Gravity successfully broken")

    # ==========================================
    # PHASE C: RECOVERY (Attractor Re-formation)
    # ==========================================
    print("\n>>> PHASE C: RECOVERY (restoring defaults)...")
    print("     Restoring temperature gradient and cadence...")

    # Restore physics
    cfg.TEMP_MIN, cfg.TEMP_MAX = defaults["TEMP_MIN"], defaults["TEMP_MAX"]
    cfg.CENTER_UPDATE_EVERY = defaults["CENTER_UPDATE_EVERY"]
    cfg.OUTER_UPDATE_EVERY = defaults["OUTER_UPDATE_EVERY"]

    # Restore temperature tensor (double-invert returns original)
    t = field.cubes.temperature
    field.cubes.temperature = t.max() + t.min() - t

    for i in range(1, recovery_steps + 1):
        field.step()
        if i % log_every == 0:
            _, _, p, gap = log_stats("RECV", field.step_count)
            recovery_gaps.append(gap)
            all_pressures.append(p)

    mean_recovery = np.mean(recovery_gaps)
    print(f"\n[RECOVERY RESULT] Mean gravity gap: {mean_recovery:+.4f}")

    assert mean_recovery > 0, (
        f"RECOVERY FAIL: Gravity did not re-form (gap={mean_recovery:.4f}). "
        f"Field failed to return to attractor state."
    )

    # ==========================================
    # METABOLIC SANITY CHECK
    # ==========================================
    max_pressure_observed = np.max(all_pressures)
    print(
        f"\n[METABOLIC CHECK] Max renewal pressure: {max_pressure_observed*100:.2f}% "
        f"(limit: 2.0%) {'✓' if max_pressure_observed < max_pressure else '✗'}"
    )

    assert max_pressure_observed < max_pressure, (
        f"METABOLIC FAIL: Churn spike detected ({max_pressure_observed*100:.2f}%). "
        f"Perturbation caused mass death (check TTL variance)."
    )

    # ==========================================
    # FINAL VERDICT
    # ==========================================
    print("\n" + "=" * 70)
    print("✅ CONTROLLED PERTURBATION TEST PASSED")
    print("=" * 70)
    print(f"Baseline gravity:  {mean_baseline:+.4f} (established)")
    print(f"Perturb chaos:     {mean_perturb:+.4f} (broke as intended)")
    print(f"Recovery gravity:  {mean_recovery:+.4f} (attractor confirmed)")
    print(f"System stability:  {max_pressure_observed*100:.2f}% renewal pressure")
    print("\nCONCLUSION: Epistemic Gravity is a lawful structural attractor.")
    print("The field self-organizes toward center-compression under lawful geometry.")

    return {
        "baseline_gap": float(mean_baseline),
        "perturb_gap": float(mean_perturb),
        "recovery_gap": float(mean_recovery),
        "max_pressure": float(max_pressure_observed),
        "attractor_valid": True,
    }


if __name__ == "__main__":
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Initializing Space-Field on {device}...")

    field = SpaceFieldCognition(device=device)

    results = run_controlled_perturbation(
        field,
        baseline_steps=1000,
        perturb_steps=400,
        recovery_steps=1000,
        log_every=50,
    )
