"""
STANDALONE STRESS TEST for Space-Field 32³
Run this to verify all safety invariants hold under stress.
"""

import torch
import numpy as np
from space_field import SpaceFieldCognition


def run_diagnostic():
    """Hard validation with clear PASS/FAIL output"""
    print("=" * 70)
    print("SPACE-FIELD 32³ - STRESS & SANITY DIAGNOSTIC")
    print("=" * 70)

    device = "cpu"

    # === TEST 1: INK INJECTION (Memory Leak) ===
    print("\n🔴 TEST 1: Ink Injection Overload")
    field = SpaceFieldCognition(device=device)

    poison = torch.ones(32, 32, 32, 4, device=device) * 5.0
    for _ in range(100):
        field.broadcast_to_field(poison)
        field.step()

    max_val = field.diffusion.field.abs().max().item()
    assert max_val <= 10.0, f"FAIL: Field exceeded clamp at {max_val}"

    post_broadcast = field.diffusion.field.abs().mean().item()
    for _ in range(50):
        field.step()
    cooled = field.diffusion.field.abs().mean().item()

    assert cooled < post_broadcast, "FAIL: Field not decaying"
    assert cooled < 0.5, f"FAIL: Memory leak, field at {cooled}"
    print(f"   ✅ PASS: Max {max_val:.2f}, cooled to {cooled:.4f}")

    # === TEST 2: VACUUM BOUNDARY ===
    print("\n🔴 TEST 2: Vacuum Boundary (Fix 2)")
    field = SpaceFieldCognition(device=device)

    field.cubes.activation.zero_()
    field.cubes.activation[0] = 1.0  # Corner (0,0,0)
    mask = torch.zeros(field.n_cubes, dtype=torch.bool, device=device)
    mask[0] = True
    field._local_update(mask)
    corner_act = field.cubes.activation[0].item()

    field.cubes.activation.zero_()
    center_idx = 16 * 1024 + 16 * 32 + 16  # (16,16,16)
    field.cubes.activation[center_idx] = 1.0
    mask = torch.zeros(field.n_cubes, dtype=torch.bool, device=device)
    mask[center_idx] = True
    field._local_update(mask)
    center_act = field.cubes.activation[center_idx].item()

    assert corner_act < center_act, f"FAIL: Corner {corner_act} >= Center {center_act}"
    print(f"   ✅ PASS: Corner {corner_act:.4f} < Center {center_act:.4f}")

    # === TEST 3: DEATH WAVE ===
    print("\n🔴 TEST 3: Death Wave Synchronization")
    field = SpaceFieldCognition(device=device)

    respawns = []
    for _ in range(5000):
        dead_before = (field.cubes.ttl <= 0).sum().item()
        field.step()
        dead_after = (field.cubes.ttl <= 0).sum().item()
        if dead_after > dead_before:
            respawns.append(dead_after - dead_before)

    max_wave = max(respawns) if respawns else 0
    ttl_var = torch.var(field.cubes.ttl[field.cubes.shell_mask['center']]).item()

    assert ttl_var > 100, f"FAIL: TTL variance {ttl_var} too low"
    assert max_wave < 500, f"FAIL: Death wave of {max_wave} cubes"
    print(f"   ✅ PASS: Variance {ttl_var:.1f}, max wave {max_wave}")

    # === TEST 4: EPISTEMIC GRAVITY ===
    print("\n🔴 TEST 4: Epistemic Gravity")
    field = SpaceFieldCognition(device=device)

    for _ in range(500):
        field.step()

    stats = field.get_field_stats()
    c_ent = stats['center_entropy']
    o_ent = stats['outer_entropy']

    assert c_ent < o_ent, f"FAIL: Center {c_ent} >= Outer {o_ent}"
    print(f"   ✅ PASS: Center {c_ent:.4f} < Outer {o_ent:.4f}")

    print("\n" + "=" * 70)
    print("✅ ALL TESTS PASSED - ARCHITECTURE VALIDATED")
    print("=" * 70)
    print(f"\nStats:")
    print(f"  Center certainty: {c_ent:.4f} entropy (low = certain)")
    print(f"  Outer exploration: {o_ent:.4f} entropy (high = exploratory)")
    print(f"  Renewal pressure: {stats['renewal_pressure'] * 100:.1f}%")


if __name__ == "__main__":
    run_diagnostic()
