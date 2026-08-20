import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
COCHLEAR_PROCESSOR_DIR = ROOT / "cochlear_processor_3.0"

for path in (ROOT, COCHLEAR_PROCESSOR_DIR):
    path_text = str(path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)

from processor import AdaptiveCochlearProcessor
from core.geometric_primitives import GlyphSignature, PHI
from core.pipeline import TriplePredicateCubed
from philosophers.base import MultiBeamRunner


def demo_basic_reasoning():
    print("=" * 60)
    print("TRIPLE PREDICATE CUBED - DEMONSTRATION")
    print("=" * 60)

    tpc = TriplePredicateCubed()
    test_inputs = [
        "What is the nature of causation?",
        "Is it ethical to manipulate consent?",
        "Can we prove geometric necessity?",
        "What is the role of empirical evidence?",
        "Tell me about universal moral principles",
        "What is 2+2?",
    ]

    print(f"\nGolden Ratio (PHI): {PHI:.6f}")
    print("Dimensions: 18")
    print("Confidence Cap: 0.95")
    print("\n" + "-" * 60)

    for index, input_text in enumerate(test_inputs, 1):
        print(f"\nQuery {index}: '{input_text}'")
        result = tpc.process(input_text, input_type="text")
        print(f"  Conclusion: {result.conclusion.upper()}")
        print(f"  Confidence: {result.confidence:.3f} (capped at 0.95)")
        print(f"  Phase Coherence: {result.phase_coherence:.3f}")
        print(f"  ECM Escalated: {result.escalated}")
        print(f"  Contract Valid: {result.contract_valid}")
        print("  Philosopher Votes:")
        for name, details in result.philosopher_breakdown.items():
            if isinstance(details, dict):
                print(
                    f"    - {name.capitalize()}: {details.get('verdict', 'N/A')} "
                    f"(conf: {details.get('confidence', 0):.3f})"
                )

    print("\n" + "=" * 60)
    print("FINAL SYSTEM STATS")
    print("=" * 60)
    stats = tpc.get_stats()
    print(f"Total queries: {stats['queries_processed']}")
    print(f"HLSF nodes: {stats['hlsf_nodes']}")
    print(f"Vault entries: {stats['vault_stats']['total_entries']}")
    print(f"Drift status: {stats['drift_status']['status']}")
    print(f"Edge cutter: {'Active' if stats['edge_cutter_active'] else 'Inactive'}")
    egf_stats = stats.get("egf_field_stats", {})
    print(f"EGF steps: {egf_stats.get('step_count', 0)}")
    print(f"EGF broadcasts: {egf_stats.get('broadcast_count', 0)}")
    print(f"EGF diffusion energy: {egf_stats.get('diffusion_energy', 0.0):.6f}")
    print(f"EGF last signal energy: {stats.get('egf_last_signal_energy', 0.0):.6f}")


def demo_geometric_signatures():
    print("\n" + "=" * 60)
    print("GEOMETRIC SIGNATURE DEMONSTRATION")
    print("=" * 60)

    text1 = "Empirical evidence suggests causation"
    text2 = "Causation is observed through empirical study"
    text3 = "Abstract metaphysics without observation"

    processor = AdaptiveCochlearProcessor()
    sig1 = GlyphSignature.from_stimulus(processor.process(text1), "text1")
    sig2 = GlyphSignature.from_stimulus(processor.process(text2), "text2")
    sig3 = GlyphSignature.from_stimulus(processor.process(text3), "text3")

    print(f"\nText 1: '{text1}'")
    print(f"Text 2: '{text2}'")
    print(f"Text 3: '{text3}'")
    print("\nGeometric distances (lower = more similar):")
    print(f"  1 vs 2 (similar): {sig1.geometric_distance(sig2):.3f}")
    print(f"  1 vs 3 (different): {sig1.geometric_distance(sig3):.3f}")
    print(f"  2 vs 3 (different): {sig2.geometric_distance(sig3):.3f}")
    print("\nCertainty scores:")
    print(f"  Sig 1: {sig1.certainty:.3f}")
    print(f"  Sig 2: {sig2.certainty:.3f}")
    print(f"  Sig 3: {sig3.certainty:.3f}")


def demo_philosopher_beams():
    print("\n" + "=" * 60)
    print("FOUR-BEAM CONSTRAINT ARCHITECTURE")
    print("=" * 60)

    runner = MultiBeamRunner()
    tests = [
        ("Observed pattern with clear data", "empirical"),
        ("Universal moral law applies", "universal"),
        ("Consent was explicitly given", "consent"),
        ("Geometric proof step by step", "geometric"),
    ]

    processor = AdaptiveCochlearProcessor()
    for text, category in tests:
        stimulus = processor.process(text)
        verdicts = runner.run_parallel(stimulus, depth=0)
        coherence = runner.calculate_phase_coherence(verdicts)
        print(f"\nInput: '{text}' [{category}]")
        print(f"Phase Coherence: {coherence:.3f}")
        print("Beam Verdicts:")
        for name, verdict in verdicts.items():
            print(
                f"  {name.capitalize():8} | {verdict.verdict.upper():8} | "
                f"conf: {verdict.confidence:.3f} | {verdict.reasoning[:40]}..."
            )


if __name__ == "__main__":
    demo_basic_reasoning()
    demo_geometric_signatures()
    demo_philosopher_beams()

    print("\n" + "=" * 60)
    print("DEMONSTRATION COMPLETE")
    print("=" * 60)
