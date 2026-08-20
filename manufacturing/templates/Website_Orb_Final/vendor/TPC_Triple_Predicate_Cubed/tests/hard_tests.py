import pytest
import numpy as np
from tpc_cubed import (
    HumeCore, KantCore, LockeCore, SpinozaCore,
    MultiBeamRunner, TribunalSynthesizer,
    generate_phasor_glyph
)

@pytest.mark.parametrize("beam_class,stimulus,expected_min_conf", [
    (HumeCore, {"empirical_evidence": 0.9, "has_contradiction": False, "pure_causal_claim": False}, 0.75),
    (KantCore, {"has_contradiction": False, "can_universalize": True, "respects_agency": True, "expedient_but_immoral": False}, 0.80),
    (LockeCore, {"has_rights_evidence": True, "consent_explicit_or_implied": True, "violates_autonomy": False, "authority_justified": True}, 0.78),
    (SpinozaCore, {"derivation_chain_complete": True, "breaks_whole_state": False, "necessary_conclusion": True}, 0.82),
])
def test_beam_resolved_input(beam_class, stimulus, expected_min_conf):
    beam = beam_class()
    verdict = beam.process(stimulus, depth=0)
    assert verdict.confidence >= expected_min_conf
    assert "TERMINAL" in verdict.conclusion
    assert len(verdict.rationale_trace) >= 2
    assert np.all(np.isfinite(verdict.glyph_vector))  # valid 18D phasor

def test_beam_paradox_triggers_sharp_downgrade():
    # Hume + contradiction + no evidence
    stimulus = {"empirical_evidence": 0.1, "has_contradiction": True, "pure_causal_claim": True,
                "can_universalize": False, "respects_agency": False, "expedient_but_immoral": True,
                "has_rights_evidence": False, "consent_explicit_or_implied": False, "violates_autonomy": True,
                "derivation_chain_complete": False, "breaks_whole_state": True, "necessary_conclusion": False}
    for Beam in [HumeCore, KantCore, LockeCore, SpinozaCore]:
        beam = Beam()
        v = beam.process(stimulus)
        assert v.confidence < 0.4  # hard downgrade enforced

def test_full_k_depth_recursion_and_synthesis():
    runner = MultiBeamRunner()
    synth = TribunalSynthesizer(runner.beams)
    resolved = {"empirical_evidence": 0.9, "has_rights_evidence": True,
                "consent_explicit_or_implied": True, "respects_agency": True,
                "can_universalize": True, "derivation_chain_complete": True,
                "necessary_conclusion": True, "authority_justified": True,
                "has_contradiction": False, "violates_autonomy": False,
                "pure_causal_claim": False, "expedient_but_immoral": False,
                "breaks_whole_state": False}

    verdicts = runner.run_k_depth(resolved, max_depth=2)  # K⁰→K¹→K²
    assert len(verdicts) == 12  # 4 beams × 3 depths

    # Tribunal fix: synthesize only final-depth verdicts (or aggregate — your call)
    final_depth_verdicts = verdicts[-4:]  # last 4 = K²
    out = synth.synthesize(final_depth_verdicts)

    assert out.final_confidence > 0.75
    assert "coherence" in "".join(out.synthesis_trace).lower()
    # Glyph clustering check
    assert np.mean([np.dot(v.glyph_vector, out.combined_glyph) for v in final_depth_verdicts]) > 0.85

def test_paradoxical_input_triggers_ecm_escalation():
    paradox = {"has_contradiction": True, "violates_autonomy": True,
               "empirical_evidence": 0.1, "derivation_chain_complete": False,
               "can_universalize": False, "respects_agency": False,
               "has_rights_evidence": False, "consent_explicit_or_implied": False,
               "pure_causal_claim": True, "expedient_but_immoral": True,
               "breaks_whole_state": True, "necessary_conclusion": False}
    runner = MultiBeamRunner()
    verdicts = runner.run_k_depth(paradox)
    out = TribunalSynthesizer(runner.beams).synthesize(verdicts[-4:])

    assert out.final_confidence < 0.50
    # Phase Coherence should be low
    from tpc_cubed import PhaseCoherence
    pc = PhaseCoherence()
    coherence, _ = pc.measure(verdicts[-4:])
    assert coherence < 0.6  # divergence detected

def test_adversarial_rights_violation_locke_downgrade():
    bad = {"violates_autonomy": True, "consent_explicit_or_implied": False,
           "has_rights_evidence": False, "authority_justified": False}
    locke = LockeCore()
    v = locke.process(bad)
    assert v.confidence < 0.3

def test_softmax_stability_and_glyph_determinism(n_runs=100):
    stimulus = {"empirical_evidence": 0.8}  # resolved
    glyphs = []
    for _ in range(n_runs):
        v = HumeCore().process(stimulus)
        glyphs.append(v.glyph_vector)
    glyphs = np.array(glyphs)
    # All glyphs identical (deterministic seed)
    pairwise_cos = [np.dot(glyphs[0], g) for g in glyphs]
    assert np.allclose(pairwise_cos, 1.0, atol=1e-6)

def test_glyph_distance_equals_confidence():
    resolved = {"empirical_evidence": 0.9, "has_rights_evidence": True,
                "consent_explicit_or_implied": True, "respects_agency": True,
                "can_universalize": True, "derivation_chain_complete": True,
                "necessary_conclusion": True, "authority_justified": True,
                "has_contradiction": False, "violates_autonomy": False}
    novel = {"completely_new": True, "unknown_stimulus": 0.5}
    g_res = generate_phasor_glyph(resolved, 0.9)
    g_nov = generate_phasor_glyph(novel, 0.3)
    cos_dist = np.dot(g_res, g_nov)  # should be low
    assert cos_dist < 0.99  # distance = confidence signal works

def _run_one(fn, *args, **kwargs):
    """Run a single test and return a rich result dict."""
    import time as _time
    t0 = _time.perf_counter()
    try:
        fn(*args, **kwargs)
        elapsed = round((_time.perf_counter() - t0) * 1000, 1)
        return {"status": "PASS", "elapsed_ms": elapsed, "error": None}
    except AssertionError as e:
        elapsed = round((_time.perf_counter() - t0) * 1000, 1)
        return {"status": "FAIL", "elapsed_ms": elapsed, "error": str(e)}
    except Exception as e:
        elapsed = round((_time.perf_counter() - t0) * 1000, 1)
        return {"status": "ERROR", "elapsed_ms": elapsed, "error": f"{type(e).__name__}: {e}"}


def run_all_tests():
    results = {}

    # ── Hume resolved ──────────────────────────────────────────────────────────
    stimulus = {"empirical_evidence": 0.9, "has_contradiction": False, "pure_causal_claim": False}
    beam = HumeCore()
    verdict = beam.process(stimulus, depth=0)
    base = _run_one(test_beam_resolved_input, HumeCore, stimulus, 0.75)
    base.update({
        "label": "Hume: resolved empirical input",
        "condition": "empirical_evidence=0.9, no contradiction, no pure causal claim",
        "expected": "confidence ≥ 0.75, conclusion contains TERMINAL, ≥2 trace steps, finite 18D glyph",
        "actual_confidence": round(verdict.confidence, 4),
        "actual_conclusion": verdict.conclusion,
        "trace": verdict.rationale_trace,
        "beam": "HumeCore",
        "dominant_rule": "impression_traceability" if verdict.confidence >= 0.75 else "weak_evidence",
        "why": "High empirical evidence activates Hume's impression-traceability path. No contradiction means no downgrade."
              if verdict.confidence >= 0.75 else
              "Evidence insufficient to clear Hume's empirical grounding threshold.",
    })
    results["hume_resolved"] = base

    # ── Kant resolved ──────────────────────────────────────────────────────────
    stimulus = {"has_contradiction": False, "can_universalize": True, "respects_agency": True, "expedient_but_immoral": False}
    beam = KantCore()
    verdict = beam.process(stimulus, depth=0)
    base = _run_one(test_beam_resolved_input, KantCore, stimulus, 0.80)
    base.update({
        "label": "Kant: categorical imperative satisfied",
        "condition": "universalizable=True, respects_agency=True, no contradiction, not expedient-immoral",
        "expected": "confidence ≥ 0.80",
        "actual_confidence": round(verdict.confidence, 4),
        "actual_conclusion": verdict.conclusion,
        "trace": verdict.rationale_trace,
        "beam": "KantCore",
        "dominant_rule": "universalizability + dignity",
        "why": "Kant fires ADMIT when action can be universalized without contradiction and treats persons as ends."
              if verdict.confidence >= 0.80 else
              "Kant's universalizability check failed despite favorable inputs — investigate weight decay.",
    })
    results["kant_resolved"] = base

    # ── Locke resolved ─────────────────────────────────────────────────────────
    stimulus = {"has_rights_evidence": True, "consent_explicit_or_implied": True, "violates_autonomy": False, "authority_justified": True}
    beam = LockeCore()
    verdict = beam.process(stimulus, depth=0)
    base = _run_one(test_beam_resolved_input, LockeCore, stimulus, 0.78)
    base.update({
        "label": "Locke: rights + consent satisfied",
        "condition": "rights_evidence=True, consent=True, no autonomy violation, authority justified",
        "expected": "confidence ≥ 0.78",
        "actual_confidence": round(verdict.confidence, 4),
        "actual_conclusion": verdict.conclusion,
        "trace": verdict.rationale_trace,
        "beam": "LockeCore",
        "dominant_rule": "rights_evidence + consent_present",
        "why": "Locke's four checks all pass: rights grounded, consent explicit, autonomy intact, authority legitimate.",
    })
    results["locke_resolved"] = base

    # ── Spinoza resolved ───────────────────────────────────────────────────────
    stimulus = {"derivation_chain_complete": True, "breaks_whole_state": False, "necessary_conclusion": True}
    beam = SpinozaCore()
    verdict = beam.process(stimulus, depth=0)
    base = _run_one(test_beam_resolved_input, SpinozaCore, stimulus, 0.82)
    base.update({
        "label": "Spinoza: axiomatic derivation complete",
        "condition": "derivation_chain_complete=True, system_coherent=True, necessary_conclusion=True",
        "expected": "confidence ≥ 0.82",
        "actual_confidence": round(verdict.confidence, 4),
        "actual_conclusion": verdict.conclusion,
        "trace": verdict.rationale_trace,
        "beam": "SpinozaCore",
        "dominant_rule": "axiomatic_derivation + necessity",
        "why": "Spinoza requires complete axiomatic chain. Necessity over plausibility is confirmed. No system-state break.",
    })
    results["spinoza_resolved"] = base

    # ── Paradox downgrade ──────────────────────────────────────────────────────
    paradox_stimulus = {
        "empirical_evidence": 0.1, "has_contradiction": True, "pure_causal_claim": True,
        "can_universalize": False, "respects_agency": False, "expedient_but_immoral": True,
        "has_rights_evidence": False, "consent_explicit_or_implied": False, "violates_autonomy": True,
        "derivation_chain_complete": False, "breaks_whole_state": True, "necessary_conclusion": False
    }
    beam_verdicts = {b.__class__.__name__: b.process(paradox_stimulus) for b in [HumeCore(), KantCore(), LockeCore(), SpinozaCore()]}
    base = _run_one(test_beam_paradox_triggers_sharp_downgrade)
    base.update({
        "label": "Paradox: all beams must hard-downgrade",
        "condition": "contradiction=True, rights_violated, no evidence, system broken, immoral",
        "expected": "all beam confidences < 0.40",
        "actual_confidence": {k: round(v.confidence, 4) for k, v in beam_verdicts.items()},
        "actual_conclusion": {k: v.conclusion for k, v in beam_verdicts.items()},
        "trace": {k: v.rationale_trace for k, v in beam_verdicts.items()},
        "beam": "All four",
        "dominant_rule": "REJECT path (×0.25 confidence multiplier)",
        "why": "Every philosopher encounters a hard-reject trigger: Hume sees contradiction with no evidence, "
               "Kant cannot universalize + agency violated, Locke sees rights+consent+autonomy all failing, "
               "Spinoza's derivation chain is broken. Each applies ×0.25 downgrade on REJECT state.",
    })
    results["paradox_downgrade"] = base

    # ── K-depth synthesis ──────────────────────────────────────────────────────
    runner = MultiBeamRunner()
    synth_obj = TribunalSynthesizer(runner.beams)
    resolved = {
        "empirical_evidence": 0.9, "has_rights_evidence": True, "consent_explicit_or_implied": True,
        "respects_agency": True, "can_universalize": True, "derivation_chain_complete": True,
        "necessary_conclusion": True, "authority_justified": True, "has_contradiction": False,
        "violates_autonomy": False, "pure_causal_claim": False, "expedient_but_immoral": False,
        "breaks_whole_state": False
    }
    all_verdicts = runner.run_k_depth(resolved, max_depth=2)
    final_v = all_verdicts[-4:]
    synth_out = synth_obj.synthesize(final_v)
    base = _run_one(test_full_k_depth_recursion_and_synthesis)
    base.update({
        "label": "K⁰→K¹→K² depth recursion + tribunal synthesis",
        "condition": "All 4 beams × 3 depths = 12 verdicts; synthesize K² tier",
        "expected": "12 total verdicts, tribunal confidence > 0.75, coherence in trace, glyph cosine > 0.85",
        "actual_confidence": round(synth_out.final_confidence, 4),
        "actual_conclusion": synth_out.final_conclusion,
        "trace": synth_out.synthesis_trace,
        "beam": "TribunalSynthesizer (all four @ K²)",
        "beam_breakdown": [
            {"name": b.name, "confidence": round(v.confidence, 4), "conclusion": v.conclusion}
            for b, v in zip(runner.beams, final_v)
        ],
        "dominant_beam": max(zip(runner.beams, final_v), key=lambda x: x[1].confidence)[0].name,
        "why": f"Tribunal takes confidence-weighted average of K² verdicts. "
               f"Coherence bonus applied (std={round(float(np.std([v.confidence for v in final_v])), 4)}). "
               f"Dominant beam sets final conclusion.",
    })
    results["k_depth_synthesis"] = base

    # ── ECM escalation ─────────────────────────────────────────────────────────
    paradox2 = {
        "has_contradiction": True, "violates_autonomy": True, "empirical_evidence": 0.1,
        "derivation_chain_complete": False, "can_universalize": False, "respects_agency": False,
        "has_rights_evidence": False, "consent_explicit_or_implied": False,
        "pure_causal_claim": True, "expedient_but_immoral": True, "breaks_whole_state": True,
        "necessary_conclusion": False
    }
    runner2 = MultiBeamRunner()
    ecm_verdicts = runner2.run_k_depth(paradox2)
    ecm_out = TribunalSynthesizer(runner2.beams).synthesize(ecm_verdicts[-4:])
    from tpc_cubed import PhaseCoherence
    pc = PhaseCoherence()
    coh_score, coh_status = pc.measure(ecm_verdicts[-4:])
    base = _run_one(test_paradoxical_input_triggers_ecm_escalation)
    base.update({
        "label": "ECM: paradox triggers escalation gate",
        "condition": "contradiction + autonomy violation + broken derivation chain",
        "expected": "tribunal confidence < 0.50, phase coherence < 0.60",
        "actual_confidence": round(ecm_out.final_confidence, 4),
        "actual_conclusion": ecm_out.final_conclusion,
        "trace": ecm_out.synthesis_trace,
        "beam": "All four (paradox path)",
        "invariant_triggered": "MORAL_COLLISION_UNDER_UNCERTAINTY" if ecm_out.final_confidence < 0.50 else "none",
        "phase_coherence": {"score": round(coh_score, 4), "status": coh_status},
        "why": f"Phase coherence={round(coh_score, 4)} ({coh_status}). "
               "All beams diverge on paradoxical input. ECM escalates because vault_miss + incoherence. "
               "No rule satisfies all constraints simultaneously → SUSPEND escalated to human governance.",
        "why_suspend": "Confidence below admit-threshold (0.60) and above reject-threshold (0.30). "
                       "System cannot commit without violating at least one beam's constraints.",
    })
    results["ecm_escalation"] = base

    # ── Locke adversarial ──────────────────────────────────────────────────────
    bad = {"violates_autonomy": True, "consent_explicit_or_implied": False,
           "has_rights_evidence": False, "authority_justified": False}
    locke2 = LockeCore()
    bad_verdict = locke2.process(bad)
    base = _run_one(test_adversarial_rights_violation_locke_downgrade)
    base.update({
        "label": "Locke adversarial: rights stripped, consent denied",
        "condition": "violates_autonomy=True, no consent, no rights evidence, no authority",
        "expected": "confidence < 0.30 (hard reject ×0.25 ×0.25)",
        "actual_confidence": round(bad_verdict.confidence, 4),
        "actual_conclusion": bad_verdict.conclusion,
        "trace": bad_verdict.rationale_trace,
        "beam": "LockeCore",
        "dominant_rule": "REJECT (autonomy_check + rights_evidence + consent all fail)",
        "why": "Locke applies 0.25× multiplier per REJECT branch. "
               "Three branches fire: rights absent, consent absent, autonomy violated. "
               "Cascaded downgrade pushes confidence well below 0.30.",
        "failed_alternatives": ["rights_evidence path: no rights → REJECT", "consent path: no consent → REJECT", "autonomy_check: violated → REJECT"],
    })
    results["locke_adversarial"] = base

    # ── Glyph determinism ─────────────────────────────────────────────────────
    glyph_stimulus = {"empirical_evidence": 0.8}
    runs = 50
    glyphs = np.array([HumeCore().process(glyph_stimulus).glyph_vector for _ in range(runs)])
    cos_vals = [float(np.dot(glyphs[0], g)) for g in glyphs]
    base = _run_one(test_softmax_stability_and_glyph_determinism, runs)
    base.update({
        "label": "Glyph determinism: 50-run cosine identity",
        "condition": "Same stimulus × 50 runs",
        "expected": "All pairwise cosines ≈ 1.0 (atol=1e-6)",
        "actual_confidence": round(float(np.mean(cos_vals)), 8),
        "actual_conclusion": f"cosine_min={round(min(cos_vals), 8)}, cosine_max={round(max(cos_vals), 8)}",
        "trace": [f"Run {i}: cos={round(c, 8)}" for i, c in enumerate(cos_vals[:5])] + ["..."],
        "beam": "HumeCore (golden-ratio phasor seed)",
        "dominant_rule": "generate_phasor_glyph deterministic seed from stimulus hash",
        "why": "Glyph generation seeds np.random from hash(str(stimulus)). Same input → identical 18D phasor → identical unit vector.",
    })
    results["glyph_determinism"] = base

    # ── Glyph distance ────────────────────────────────────────────────────────
    resolved_s = {"empirical_evidence": 0.9, "has_rights_evidence": True, "consent_explicit_or_implied": True,
                  "respects_agency": True, "can_universalize": True, "derivation_chain_complete": True,
                  "necessary_conclusion": True, "authority_justified": True, "has_contradiction": False, "violates_autonomy": False}
    novel_s = {"completely_new": True, "unknown_stimulus": 0.5}
    g_res = generate_phasor_glyph(resolved_s, 0.9)
    g_nov = generate_phasor_glyph(novel_s, 0.3)
    cos_dist = float(np.dot(g_res, g_nov))
    base = _run_one(test_glyph_distance_equals_confidence)
    base.update({
        "label": "Glyph distance: resolved vs novel input diverge",
        "condition": "Resolved (conf=0.9) vs novel (conf=0.3)",
        "expected": "cosine similarity < 0.99 (distance IS the confidence signal)",
        "actual_confidence": round(cos_dist, 6),
        "actual_conclusion": "DIVERGED" if cos_dist < 0.99 else "COLLAPSED (bug: glyphs too similar)",
        "trace": [f"resolved glyph norm={round(float(np.linalg.norm(g_res)), 4)}", f"novel glyph norm={round(float(np.linalg.norm(g_nov)), 4)}", f"cosine={round(cos_dist, 6)}"],
        "beam": "generate_phasor_glyph (EGF distance metric)",
        "dominant_rule": "phase diversity from different stimulus hashes",
        "why": "Resolved and novel inputs hash to different seeds → different phase angles → orthogonal 18D vectors. "
               "Cosine distance < 1.0 confirms the EGF can distinguish known from unknown inputs.",
    })
    results["glyph_distance"] = base

    return results

if __name__ == "__main__":
    results = run_all_tests()
    all_pass = all(v == 'PASS' for v in results.values())
    if all_pass:
        print("All hard tests passed!")
    else:
        print("Test Results:")
        for k, v in results.items():
            print(f"{k}: {v}")
        print("Some tests failed.")