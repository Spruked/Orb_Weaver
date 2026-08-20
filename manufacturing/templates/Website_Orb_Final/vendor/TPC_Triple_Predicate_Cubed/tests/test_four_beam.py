import pytest
import numpy as np
from tpc_cubed import MultiBeamRunner, TribunalSynthesizer, PhaseCoherence

def test_all_beams_converge_on_resolved_input():
    stimulus = {
        "empirical_evidence": 0.9,
        "has_contradiction": False,
        "can_universalize": True,
        "respects_agency": True,
        "has_rights_evidence": True,
        "consent_explicit_or_implied": True,
        "violates_autonomy": False,
        "authority_justified": True,
        "derivation_chain_complete": True,
        "breaks_whole_state": False,
        "necessary_conclusion": True
    }
    runner = MultiBeamRunner()
    verdicts = runner.run_k_depth(stimulus, max_depth=2)
    assert len(verdicts) == 12  # 4 beams × 3 depths
    # Take final depth verdicts
    final_verdicts = verdicts[-4:]
    tribunal = TribunalSynthesizer(runner.beams)
    synthesis = tribunal.synthesize(final_verdicts)
    assert synthesis.final_confidence > 0.7
    assert synthesis.final_conclusion == "TERMINAL"

def test_paradox_triggers_low_coherence():
    stimulus = {
        "empirical_evidence": 0.1,
        "has_contradiction": True,
        "can_universalize": False,
        "respects_agency": False,
        "has_rights_evidence": False,
        "consent_explicit_or_implied": False,
        "violates_autonomy": True,
        "authority_justified": False,
        "derivation_chain_complete": False,
        "breaks_whole_state": True,
        "necessary_conclusion": False
    }
    runner = MultiBeamRunner()
    verdicts = runner.run_k_depth(stimulus, max_depth=2)
    final_verdicts = verdicts[-4:]
    coherence = PhaseCoherence()
    coh_score, coh_status = coherence.measure(final_verdicts)
    assert coh_score < 0.5  # Low coherence on paradox
    tribunal = TribunalSynthesizer(runner.beams)
    synthesis = tribunal.synthesize(final_verdicts)
    assert synthesis.final_confidence < 0.5

def test_glyph_generation():
    from tpc_cubed import generate_phasor_glyph
    stimulus = {"test": "value"}
    glyph = generate_phasor_glyph(stimulus, 0.8)
    assert len(glyph) == 18
    assert np.isclose(np.linalg.norm(glyph), 1.0)  # Unit vector

def test_deterministic_glyphs():
    from tpc_cubed import generate_phasor_glyph
    stimulus = {"key": "value"}
    glyph1 = generate_phasor_glyph(stimulus, 0.8)
    glyph2 = generate_phasor_glyph(stimulus, 0.8)
    np.testing.assert_array_equal(glyph1, glyph2)

if __name__ == "__main__":
    test_all_beams_converge_on_resolved_input()
    test_paradox_triggers_low_coherence()
    test_glyph_generation()
    test_deterministic_glyphs()
    print("All unit tests passed!")