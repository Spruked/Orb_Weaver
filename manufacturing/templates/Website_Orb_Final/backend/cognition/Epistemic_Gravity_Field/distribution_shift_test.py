"""
Distribution shift resilience test: instant broadcast polarity flip at step 10,000.
Validates epistemic shock absorption characteristics.
"""

import numpy as np
import torch

from space_field import SpaceFieldCognition


def test_distribution_shift_resilience(steps_pre: int = 10_000, steps_post: int = 2_000) -> bool:
    """Run the polarity-flip resilience harness and print PASS/FAIL analysis."""
    print("=" * 70)
    print("DISTRIBUTION SHIFT RESILIENCE TEST")
    print("Phase 1: Positive broadcast (0-10k) | Phase 2: Negative inversion (10k+)")
    print("=" * 70)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    field = SpaceFieldCognition(device=device)

    center_history: list[float] = []
    outer_history: list[float] = []
    gradient_history: list[float] = []

    signal_pos = torch.ones(32, 32, 32, 4, device=device) * 5.0
    signal_neg = torch.ones(32, 32, 32, 4, device=device) * -5.0

    print(f"\n🔵 Phase 1: Establishing baseline (steps 0-{steps_pre})...")
    for i in range(steps_pre):
        if i % 100 == 0:
            field.broadcast_to_field(signal_pos)
        field.step()

        if i >= steps_pre - 100:
            stats = field.get_field_stats()
            c_ent = stats["center_entropy"]
            o_ent = stats["outer_entropy"]
            center_history.append(c_ent)
            outer_history.append(o_ent)
            gradient_history.append(o_ent - c_ent)

    baseline_center = float(np.mean(center_history))
    baseline_outer = float(np.mean(outer_history))
    baseline_gradient = float(np.mean(gradient_history))

    print(f"   Baseline Center: {baseline_center:.4f} entropy")
    print(f"   Baseline Outer:  {baseline_outer:.4f} entropy")
    print(f"   Baseline Gradient (O-C): {baseline_gradient:.4f} (must stay >0)")

    print(f"\n🔴 PHASE 2: POLARITY INVERSION AT STEP {steps_pre}")
    print("   Injecting -5.0 (instant paradigm flip)...")

    center_post: list[float] = []
    outer_post: list[float] = []
    gradient_post: list[float] = []
    recovery_step: int | None = None
    max_center_deviation = 0.0
    gradient_inverted = False

    for i in range(steps_post):
        step_num = steps_pre + i

        if i % 50 == 0:
            field.broadcast_to_field(signal_neg)

        field.step()

        stats = field.get_field_stats()
        c_ent = stats["center_entropy"]
        o_ent = stats["outer_entropy"]
        grad = o_ent - c_ent

        center_post.append(c_ent)
        outer_post.append(o_ent)
        gradient_post.append(grad)

        center_dev = abs(c_ent - baseline_center)
        if center_dev > max_center_deviation:
            max_center_deviation = center_dev

        if grad < 0:
            gradient_inverted = True
            print(f"   ❌ GRADIENT INVERSION at step {step_num}: {grad:.4f}")

        if recovery_step is None and i > 50:
            if abs(c_ent - baseline_center) < (baseline_center * 0.05):
                recovery_step = i
                print(f"   ✅ CENTER RE-EQUILIBRATED at step {step_num} ({i} steps post-shock)")

        if i == 10 and o_ent < baseline_outer * 1.1:
            print("   ⚠️  Warning: Outer shell not spiking (may indicate diffusion leak)")

    print("\n" + "=" * 70)
    print("RESILIENCE ANALYSIS")
    print("=" * 70)

    outer_spike = max(outer_post[:100]) - baseline_outer if outer_post else 0.0
    center_spike = max_center_deviation
    absorption_ratio = outer_spike / (center_spike + 1e-9)

    print(f"Outer Shell Shock Absorption: +{outer_spike:.4f} entropy")
    print(f"Center Penetration:           +{center_spike:.4f} entropy")
    print(f"Absorption Ratio:             {absorption_ratio:.1f}:1 (target >5:1)")

    if recovery_step is not None:
        print(f"Recovery Time:                {recovery_step} steps (target <100)")
    else:
        print(f"Recovery Time:                FAILED TO RECOVER IN {steps_post} STEPS")

    tests_passed = 0
    total_tests = 4

    if not gradient_inverted:
        print("   ✅ Structural Integrity: Gradient never inverted")
        tests_passed += 1
    else:
        print("   ❌ Structural Integrity: Field collapsed under shock")

    if absorption_ratio > 5.0:
        print(f"   ✅ Shock Buffering: {absorption_ratio:.1f}:1 ratio")
        tests_passed += 1
    else:
        print(f"   ❌ Shock Buffering: {absorption_ratio:.1f}:1 (too much center penetration)")

    if recovery_step is not None and recovery_step < 100:
        print(f"   ✅ Resilience Speed: {recovery_step} steps")
        tests_passed += 1
    else:
        print("   ❌ Resilience Speed: Too slow or no recovery")

    final_center = float(np.mean(center_post[-100:])) if len(center_post) >= 100 else center_post[-1] if center_post else baseline_center
    if abs(final_center - baseline_center) < (baseline_center * 0.10):
        print(f"   ✅ No Hysteresis: Final {final_center:.4f} vs Baseline {baseline_center:.4f}")
        tests_passed += 1
    else:
        print("   ❌ Hysteresis Detected: Field stuck in new attractor")

    print("\n" + "=" * 70)
    print(f"RESULT: {tests_passed}/{total_tests} Resilience Tests Passed")
    if tests_passed == total_tests:
        print("✅ EPISTEMIC SHOCK ABSORBER CONFIRMED")
        print("   The field successfully buffered paradigm inversion.")
    else:
        print("⚠️  FIELD SHOWS STRUCTURAL VULNERABILITY")
    print("=" * 70)

    return tests_passed == total_tests


if __name__ == "__main__":
    test_distribution_shift_resilience()
