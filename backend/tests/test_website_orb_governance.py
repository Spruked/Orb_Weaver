from app.orb.governance import (
    compile_website_orb_governance,
    finalize_governance_trace,
    prompt_layers,
)


def _compiled():
    return compile_website_orb_governance(
        website_context={
            "site_name": "Orb Weaver",
            "domain": "orbweaver.spruked.com",
            "site_summary": "Website intelligence",
            "visitor_tools": [{"id": "pointer_guidance_if_target_verified"}],
        },
        page_capsule={"route": "/features", "page_summary": "Features"},
        operating_policy={"version": "test-policy"},
        memory_context={"scope": "public_visitor"},
        transcript="What does Orb Weaver do?",
    )


def test_compiler_preserves_complete_standard_and_layers():
    compiled = _compiled()
    standard = compiled["persistent"]["professional_inculcation"]
    assert len(standard) > 50_000
    assert "Ground reasoning in evidence" in compiled["persistent"]["core_four"]
    assert "complete website orb professional inculcation" in standard.lower()
    prompt = prompt_layers(compiled)
    assert "PERSISTENT / IMMUTABLE LAYER" in prompt
    assert "DEPLOYMENT LAYER" in prompt
    assert "TURN LAYER" in prompt
    assert "TPC resolves deterministic truth" in prompt


def test_final_trace_reports_deterministic_and_doctrine_stages():
    compiled = _compiled()
    trace = finalize_governance_trace(
        compiled,
        resolved={
            "source_lane": "site_world",
            "evidence_ids": ["site_world:site_summary"],
            "verification_state": "verified",
        },
        doctrine_trace={
            "doctrine_version": "orb-weaver-articulation/1.0.0",
            "checksum": {"passed": True, "failures": []},
        },
    )
    assert trace["tpc_state"] == "passed"
    assert trace["tpc_verification"]["evidence_ids"] == ["site_world:site_summary"]
    assert trace["doctrine_checksum"] is True
    assert trace["status"] == "approved"
