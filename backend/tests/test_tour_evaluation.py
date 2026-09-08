import json
import pytest
from app.orb.tour_evaluation import parse_tour_evaluation


def response():
    speech = 'I am Weaver, your Website ORB host. I guide you using verified website knowledge.'
    return {'spoken_output': speech, 'covered_concepts': [{'concept_id': 'WEAVER_IDENTITY', 'supporting_excerpt': speech}]}


def test_accepts_model_fence_and_id_alias_without_changing_generated_words():
    payload = response()
    payload['covered_concepts'][0]['id'] = payload['covered_concepts'][0].pop('concept_id')
    result = parse_tour_evaluation('```json\n' + json.dumps(payload) + '\n```', {'WEAVER_IDENTITY'})
    assert result.spoken_output == payload['spoken_output']
    assert result.covered_concepts[0].concept_id == 'WEAVER_IDENTITY'


def test_sequence_pass_accepts_plain_live_model_speech():
    result = parse_tour_evaluation('A live unscripted tour response.', ['WEAVER_IDENTITY'])
    assert result.spoken_output == 'A live unscripted tour response.'
    assert result.covered_concepts == []


def test_normalizes_private_finding_index_and_markdown_before_speech():
    result = parse_tour_evaluation(
        '**You are currently at the "Finding 0" stop of our tour.** The report needs browser verification.',
        ['PREFLIGHT_FINDING'],
    )
    assert result.spoken_output == 'The report needs browser verification.'


def test_normalizes_private_tour_stop_lead_sentence_before_speech():
    result = parse_tour_evaluation(
        "We're here at the current tour stop, where we're explaining the verified finding. The report needs browser verification.",
        ['PREFLIGHT_FINDING'],
    )
    assert result.spoken_output == 'The report needs browser verification.'


def test_normalizes_current_tour_stop_variant_before_speech():
    result = parse_tour_evaluation(
        'You are on the current tour stop, where we explain the verified finding. The report needs browser verification.',
        ['PREFLIGHT_FINDING'],
    )
    assert result.spoken_output == 'The report needs browser verification.'


def test_normalizes_card_list_markers_and_private_next_stop_line_before_speech():
    result = parse_tour_evaluation(
        'What Weaver found: - Found 3 broken links. - Found 21 unfinished pages. We\'re now moving on to the next stop.',
        ['PREFLIGHT_FINDING'],
    )
    assert result.spoken_output == 'What Weaver found: Found 3 broken links. Found 21 unfinished pages.'


def test_suppresses_repeated_weaver_introduction_outside_identity_stop():
    result = parse_tour_evaluation(
        "I'm Weaver, and I guide only to verified targets.",
        ['VERIFIED_GUIDANCE'],
    )
    assert result.spoken_output == 'I guide only to verified targets.'


def test_removes_the_full_sentence_when_repeated_identity_is_embedded_in_it():
    result = parse_tour_evaluation(
        "You're standing here, and I'm Weaver. Speak naturally and stay in control.",
        ['PRESENCE_AND_CONTROL'],
    )
    assert result.spoken_output == 'Speak naturally and stay in control.'


def test_prompt_requires_semantic_evidence_without_verbatim_reproduction():
    from app.orb.tour_evaluation import tour_prompt

    prompt = tour_prompt({
        'required_concepts': [
            {'id': 'PRESENCE_AND_CONTROL', 'description': 'Speak naturally and click to stop.'},
            {'id': 'VERIFIED_GUIDANCE', 'description': 'Point only to verified live targets.'},
        ],
    })
    assert 'meaningfully addressed' in prompt
    assert 'mechanically enumerate every detail' in prompt
    assert "Weaver has already been introduced" in prompt
    assert 'Every detail in that concept\'s description must be spoken' not in prompt


def test_sequence_pass_uses_controller_ids_and_actual_live_speech():
    payload = response()
    payload['covered_concepts'][0]['supporting_excerpt'] = 'Words the model did not speak.'
    result = parse_tour_evaluation(json.dumps(payload), ['WEAVER_IDENTITY'])
    assert result.covered_concepts[0].concept_id == 'WEAVER_IDENTITY'
    assert result.covered_concepts[0].supporting_excerpt == 'Words the model did not speak.'
    assert parse_tour_evaluation(json.dumps(response()), ['OTHER']).covered_concepts == []


@pytest.mark.parametrize('extra', [{'stop_complete': True}, {'chosenAction': 'RUN_PREFLIGHT_NOW'}])
def test_ignores_model_completion_and_action_authority(extra):
    result = parse_tour_evaluation(json.dumps({**response(), **extra}), ['WEAVER_IDENTITY'])
    assert result.covered_concepts[0].concept_id == 'WEAVER_IDENTITY'
    assert not hasattr(result, 'stop_complete')
    assert not hasattr(result, 'chosenAction')


def test_rejects_conflicting_keys_and_truncated_json():
    payload = response()
    payload['covered_concepts'][0]['id'] = 'OTHER'
    assert parse_tour_evaluation(json.dumps(payload), ['WEAVER_IDENTITY']).covered_concepts[0].concept_id == 'WEAVER_IDENTITY'
    assert parse_tour_evaluation('{"spoken_output":', ['WEAVER_IDENTITY']).spoken_output == '{"spoken_output":'


def test_guidance_pointer_identity_matches_the_landing_page_source():
    """Changing landing copy must not silently strand the verified tour target."""
    import ast
    import re
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    tree = ast.parse((root / 'backend/main.py').read_text())
    declaration = next(node for node in tree.body if isinstance(node, ast.AnnAssign)
                       and isinstance(node.target, ast.Name)
                       and node.target.id == 'ORB_WEAVER_SHOWCASE_POINTERS')
    records = ast.literal_eval(declaration.value)
    record = next(item for item in records if item['target_id'] == 'watch_weaver_guide')
    landing = (root / 'frontend/src/landing/LandingPage.tsx').read_text()
    paragraph = re.search(r'<p\b[^>]*data-orb-target="watch_weaver_guide"[^>]*>(.*?)</p>', landing).group(1)
    actual_text = re.sub(r'<[^>]+>', '', paragraph)
    assert record['meaning'] == actual_text
    assert record['semantic_locator'] == '[data-orb-target="watch_weaver_guide"]'
    assert record['structural_context']['tag'] == 'p'


def test_preflight_articulation_cannot_bypass_live_cognition_with_direct_tts():
    """The generated Preflight report is facts; its visitor wording must stay live."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    runtime = (root / 'frontend/src/landing/AutonomousOrb.tsx').read_text()
    start = runtime.index("const handlePreflightComplete")
    end = runtime.index("window.addEventListener('orbweaver:preflight-complete'", start)
    handler = runtime[start:end]

    assert 'api.websiteOrbText(' in handler
    assert 'api.websiteOrbTts(' not in handler
    assert 'await speakWithGeneratedAudio(result.spoken_output' in handler
    assert 'persisted report is factual authority' in handler
    assert "element.setAttribute('data-orb-target', targetId)" in handler
    assert "lidarCacheRef.current.injectFrame" in handler
    assert "semantic_locator: `[data-orb-target=\"${targetId}\"]`" in handler
    assert "preflight-result-${detail.generated_at}-${findingKey}" in handler
    assert "content_fingerprint: `preflight:${detail.generated_at}:${findingKey}`" in handler
    assert 'emitOrbRuntimeEvent("guidance_point_ping"' in runtime


def test_preflight_report_defers_its_event_until_the_root_orb_listener_can_attach():
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    page = (root / 'frontend/src/pages/PublicPreflight.tsx').read_text()
    start = page.index('useEffect(() => {\n    if (!report) return;')
    end = page.index('  }, [report]);', start)
    report_effect = page[start:end]

    assert "window.setTimeout(() =>" in report_effect
    assert "orbweaver:preflight-complete" in report_effect
    assert "window.clearTimeout(dispatchId)" in report_effect
