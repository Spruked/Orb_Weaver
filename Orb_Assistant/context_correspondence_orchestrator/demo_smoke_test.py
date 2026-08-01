"""
Smoke test / demo for the correspondence_engine scaffold.

Demonstrates:
  1. EvidenceItem, CorrespondenceVector, KnowledgeAtom, CorrespondenceEdge
     construction and validation — MANDATORY, all working.
  2. weighted_euclidean_distance — working.
  3. Vault storage + covariance_matrix — working (given >= 2 atoms).
  4. MahalanobisGate correctly REFUSING to engage, because
     covariance_stability_check / drift_velocity_check are
     unimplemented. This is the CORRECT current behavior — it must
     fail loudly, not silently approve.
  5. SemanticSublimator.sublimate() correctly REFUSING to run,
     because extraction rules are undesigned (gaps.py: GAP_F).

Run: python demo_smoke_test.py
"""

from datetime import datetime

from correspondence_engine import (
    EvidenceItem, CorrespondenceVector, KnowledgeAtom, CorrespondenceEdge,
    RelationType, SemanticSublimator, Vault, geometry, gaps,
)


def main():
    now = datetime.now()

    # 1. EvidenceItem — mandatory, works.
    ev = EvidenceItem(
        claim="Off-balance-sheet entities hid billions in debt",
        source="SEC Investigation Report",
        confidence=0.95,
        degradation_signal=0.9,
        timestamp=now,
        supports_dimension="representation",
        corroboration_count=5,
    )
    print("1. EvidenceItem OK:", ev.summary())

    # 2. CorrespondenceVector + KnowledgeAtom — mandatory, works.
    vec_a = CorrespondenceVector(reality=0.7, representation=0.9, purpose=0.6, personhood=0.5, continuity=0.6)
    vec_b = CorrespondenceVector(reality=0.6, representation=0.8, purpose=0.5, personhood=0.4, continuity=0.5)

    atom_a = KnowledgeAtom("atom_1", "observation A", vec_a, confidence=0.9, provenance="SEC report", timestamp=now)
    atom_b = KnowledgeAtom("atom_2", "observation B", vec_b, confidence=0.8, provenance="Bankruptcy filing", timestamp=now)
    print("2. KnowledgeAtom OK:", atom_a.atom_id, atom_b.atom_id)

    # 3. Distance — mandatory, works.
    dist = geometry.weighted_euclidean_distance(vec_a, vec_b)
    print("3. weighted_euclidean_distance OK:", round(dist, 4))

    # 4. Vault + edge + covariance — mandatory, works.
    vault = Vault()
    vault.add_atom(atom_a)
    vault.add_atom(atom_b)
    vault.add_edge(CorrespondenceEdge(
        "atom_1", "atom_2", RelationType.CORROBORATES,
        weight=0.8, confidence=0.85, timestamp=now,
    ))
    cov = vault.covariance_matrix()
    print("4. Vault + covariance_matrix OK, shape:", cov.shape)

    # 5. MahalanobisGate — correctly refuses to engage. This SHOULD
    #    raise, because covariance_stability_check / drift_velocity_check
    #    are unimplemented. That's the intended, honest behavior —
    #    not a bug in this demo.
    gate = geometry.MahalanobisGate(
        geometry.MahalanobisGateConfig(min_claims_for_mahalanobis=2)
    )
    try:
        gate.should_use_mahalanobis(vault)
        print("5. UNEXPECTED: gate engaged without stability/drift checks implemented")
    except NotImplementedError as e:
        print("5. MahalanobisGate correctly refused (expected):", e)

    # 6. Sublimator — correctly refuses to run (GAP_F).
    sub = SemanticSublimator()
    try:
        sub.sublimate([ev])
        print("6. UNEXPECTED: sublimator produced a claim without extraction rules")
    except NotImplementedError as e:
        print("6. SemanticSublimator correctly refused (expected):", e)

    print(f"\nOpen architectural gaps registered: {len(gaps.ALL_GAPS)}")
    print("See correspondence_engine/gaps.py for full detail on each.")


if __name__ == "__main__":
    main()
