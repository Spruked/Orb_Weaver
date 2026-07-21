import json
import os
import subprocess
import sys
from pathlib import Path


def test_sf_orb_uses_complete_cognitive_pipeline_and_does_not_bypass_on_vault_hit(
    tmp_path,
):
    vault_root = tmp_path / "vault_system"
    apriori = vault_root / "apriori" / "apriori_core.json"
    apriori.parent.mkdir(parents=True)
    apriori.write_text(
        json.dumps(
            {
                "canonical_truths": [
                    {"id": "TEST_TRUTH", "predicate": "retrieved evidence"}
                ]
            }
        ),
        encoding="utf-8",
    )
    script = r'''
import json
from Orb_Assistant.src.orb_controller import SF_ORB_Controller

controller = SF_ORB_Controller()
fast = controller.cognitively_emerge({
    "type": "cursor_movement",
    "intent": "TEST_TRUTH",
    "coordinates": [240, 180],
    "velocity": 2.0,
    "meta": {"test_mode": True},
})
ordinary = controller.cognitively_emerge({
    "type": "user_question",
    "text": "What evidence is available?",
    "meta": {"test_mode": True},
})
full = controller.cognitively_emerge({
    "type": "explicit_deep_reasoning",
    "text": "Reconcile conflicting evidence.",
    "meta": {"test_mode": True, "deep_reasoning": True},
})
controller.skg_usage_ledger.flush()
controller.cali_reflection_recorder.flush()
print(json.dumps({
    "fast": {
        "components": fast.cognitive_components,
        "vault_retrieval": fast.vault_retrieval,
        "validation": fast.validation_witness,
        "latency_ms": fast.latency_ms,
        "execution_record": fast.execution_record,
    },
    "ordinary": {
        "components": ordinary.cognitive_components,
        "latency_ms": ordinary.latency_ms,
        "execution_record": ordinary.execution_record,
    },
    "full": {
        "components": full.cognitive_components,
        "latency_ms": full.latency_ms,
        "execution_record": full.execution_record,
    },
}))
'''
    environment = os.environ.copy()
    environment["ORB_WEAVER_VAULT_ROOT"] = str(vault_root)
    environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[1],
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(completed.stdout.strip().splitlines()[-1])
    fast = result["fast"]
    components = fast["components"]

    assert components["path"] == "vault_supported_fast"
    assert components["core_4"] == []
    assert components["hlsf"] is False
    assert components["bayesian_selection"] is False
    assert components["deductive_skg"] is True
    assert components["inductive_skg"] is False
    assert components["intuitive_skg"] is False
    assert components["learned_habits"] is False
    assert components["vault_retrieval_queried"] is True
    assert components["vault_match_found"] is True
    assert components["cali_reflection"] is False
    assert components["final_validators"] == ["deductive"]
    assert fast["vault_retrieval"]["source"] == "APRIORI"
    assert fast["validation"]["checked"] is True
    assert fast["execution_record"]["selected_lane"] == "vault_supported_fast"
    assert fast["execution_record"]["routing_reason"]
    assert fast["execution_record"]["modules_invoked"]
    assert fast["execution_record"]["validators_invoked"] == ["deductive"]
    assert fast["execution_record"]["may_advance_stage_governor"] is False

    ordinary = result["ordinary"]["components"]
    assert ordinary["path"] == "ordinary_reasoning"
    assert ordinary["core_4"] == ["hume", "kant", "locke", "spinoza"]
    assert ordinary["hlsf"] is True
    assert ordinary["bayesian_selection"] is True
    assert ordinary["deductive_skg"] is True
    assert ordinary["intuitive_skg"] is False
    assert ordinary["cali_reflection"] is False

    full = result["full"]["components"]
    assert full["path"] == "full_escalation"
    assert full["core_4"] == ["hume", "kant", "locke", "spinoza"]
    assert full["hlsf"] is True
    assert full["bayesian_selection"] is True
    assert full["deductive_skg"] is True
    assert full["inductive_skg"] is True
    assert full["intuitive_skg"] is True
    assert full["cali_reflection"] is True
    assert full["final_validators"] == ["deductive", "inductive", "intuitive"]
    assert set(full["logic_seed_ids"]) == {
        "INDUCTIVE_CURSOR_001",
        "INDUCTIVE_MORAL_001",
        "INTUITIVE_JUMP_001",
    }
    assert result["fast"]["latency_ms"] >= 0
    assert result["ordinary"]["latency_ms"] >= 0
    assert result["full"]["latency_ms"] >= 0
    assert (
        vault_root
        / "observations"
        / "cognition"
        / "workers"
        / "sf_orb_controller"
        / "cognitive_component_usage.jsonl"
    ).is_file()


def test_ledger_failure_is_observational_and_does_not_rerun_cognition(tmp_path):
    vault_root = tmp_path / "vault_system"
    apriori = vault_root / "apriori" / "apriori_core.json"
    apriori.parent.mkdir(parents=True)
    apriori.write_text(
        json.dumps(
            {"canonical_truths": [{"id": "FAULT_TRUTH", "predicate": "valid"}]}
        ),
        encoding="utf-8",
    )
    script = r'''
import json
from Orb_Assistant.src.orb_controller import SF_ORB_Controller

controller = SF_ORB_Controller()
calls = {"deductive": 0, "results": 0}
original_advise = controller.deductive_engine.advise_orb
def counted_advise(*args, **kwargs):
    calls["deductive"] += 1
    return original_advise(*args, **kwargs)
def failed_ledger(*_args, **_kwargs):
    raise OSError("injected ledger failure")
controller.deductive_engine.advise_orb = counted_advise
controller.skg_usage_ledger.record = failed_ledger
result = controller.cognitively_emerge({
    "type": "user_question",
    "text": "FAULT_TRUTH",
    "meta": {"test_mode": True},
})
calls["results"] += 1
print(json.dumps({
    "calls": calls,
    "result": result.pulse(),
    "controller_error": controller.last_observational_error,
}))
'''
    environment = os.environ.copy()
    environment["ORB_WEAVER_VAULT_ROOT"] = str(vault_root)
    environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[1],
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout.strip().splitlines()[-1])
    record = payload["result"]["execution_record"]

    assert payload["calls"] == {"deductive": 1, "results": 1}
    assert payload["result"]["final_verdict"] == "valid"
    assert record["selected_lane"] == "vault_supported_fast"
    assert record["confidence_after_validation"] > 0
    assert "deductive_skg" in record["modules_invoked"]
    assert record["observational_errors"][0]["result_preserved"] is True
    assert payload["controller_error"]["component"] == "SKGUsageLedger"
