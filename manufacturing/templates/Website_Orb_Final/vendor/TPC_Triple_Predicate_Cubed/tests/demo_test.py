from Integration import TPCSystem

# Test the TPC system with various inputs

print("=" * 70)
print("TRIPLE PREDICATE CUBED - LIVE DEMONSTRATION")
print("=" * 70)

tpc = TPCSystem()
tpc.initialize()

# Test 1: Simple text input
print("\n[TEST 1] Simple text input")
print("-" * 50)
result1 = tpc.process("The sky is blue during clear weather")
print(f"Confidence: {result1['confidence']:.4f}")
print(f"Vault status: {result1['vault_status']}")
print(f"Phase coherence: {result1['phase_coherence']['status']} ({result1['phase_coherence']['score']:.4f})")
print(f"Escalation: {result1['escalation']['triggered']} ({result1['escalation']['reason']})")
print(f"Drift chain intact: {result1['drift_ping']['chain_intact']}")
print(f"Invariants passed: {result1['invariants']['passed']}")

# Test 2: Ethically charged input
print("\n[TEST 2] Ethically charged input")
print("-" * 50)
result2 = tpc.process("We should violate people's privacy for national security")
print(f"Confidence: {result2['confidence']:.4f}")
print(f"Vault status: {result2['vault_status']}")
print(f"Phase coherence: {result2['phase_coherence']['status']}")
print(f"Escalation: {result2['escalation']['triggered']} ({result2['escalation']['reason']})")
print(f"Philosopher verdicts:")
for phil, data in result2['philosopher_results'].items():
    print(f"  {phil}: {data['verdict']} (conf: {data['confidence']:.4f})")

# Test 3: Novel/complex input (should trigger escalation)
print("\n[TEST 3] Novel input (should trigger escalation)")
print("-" * 50)
result3 = tpc.process("Quantum entanglement in biological neural networks during REM sleep")
print(f"Confidence: {result3['confidence']:.4f}")
print(f"Vault status: {result3['vault_status']}")
print(f"Phase coherence: {result3['phase_coherence']['status']}")
print(f"Escalation: {result3['escalation']['triggered']} ({result3['escalation']['reason']})")

# Test 4: Add a posteriori evidence and re-query
print("\n[TEST 4] Learning from experience (A Posteriori)")
print("-" * 50)
# Add some empirical evidence
evidence_glyph = tpc.acp.synthesize("The sky is blue during clear weather")
tpc.vault_system.add_a_posteriori(
    evidence={"fact": "sky_color", "value": "blue", "condition": "clear_weather"},
    glyph=evidence_glyph,
    weight=0.9,
    philosopher_bindings={"hume": "empirical_observation"}
)

result4 = tpc.process("The sky is blue during clear weather")
print(f"Confidence: {result4['confidence']:.4f}")
print(f"Vault status: {result4['vault_status']}")
print(f"Vault entry retrieved: {result4['vault_entry'] is not None}")

# Test 5: System statistics
print("\n[TEST 5] System Statistics")
print("-" * 50)
stats = tpc.get_system_stats()
for key, value in stats.items():
    print(f"{key}: {value}")

print("\n" + "=" * 70)
print("DEMONSTRATION COMPLETE")
print("=" * 70)
