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
    assert result.covered_concepts[0].supporting_excerpt == result.spoken_output


def test_prompt_requires_evidence_for_every_required_concept():
    from app.orb.tour_evaluation import tour_prompt

    prompt = tour_prompt({
        'required_concepts': [
            {'id': 'PRESENCE_AND_CONTROL', 'description': 'Speak naturally and click to stop.'},
            {'id': 'VERIFIED_GUIDANCE', 'description': 'Point only to verified live targets.'},
        ],
    })
    assert 'exactly one entry for every object in required_concepts' in prompt
    assert 'Every detail in that concept\'s description must be spoken' in prompt


def test_sequence_pass_uses_controller_ids_and_actual_live_speech():
    payload = response()
    payload['covered_concepts'][0]['supporting_excerpt'] = 'Words the model did not speak.'
    result = parse_tour_evaluation(json.dumps(payload), ['WEAVER_IDENTITY'])
    assert result.covered_concepts[0].concept_id == 'WEAVER_IDENTITY'
    assert result.covered_concepts[0].supporting_excerpt == payload['spoken_output']
    assert parse_tour_evaluation(json.dumps(response()), ['OTHER']).covered_concepts[0].concept_id == 'OTHER'


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
