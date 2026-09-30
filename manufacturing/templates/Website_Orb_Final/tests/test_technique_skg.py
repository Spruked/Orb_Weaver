from backend.cognition.technique_skg import behavior_pack_metadata, technique_guidance_prompt, technique_skg


def test_manufactured_runtime_contains_exact_41_technique_registry() -> None:
    registry = technique_skg()
    techniques = registry["Techniques"]
    assert len(techniques) == 41
    assert techniques[0]["id"] == "Technique_1_SPIN"
    assert techniques[-1]["id"] == "Technique_41_ConsentComplianceGate"
    assert all(item["sequenced_by"] == "NockNineOfClubs" for item in techniques)


def test_technique_guidance_is_advisory_and_preserves_consent_gate() -> None:
    guidance = technique_guidance_prompt()
    assert "ADVISORY ONLY" in guidance
    assert "no execution authority" in guidance
    assert "Technique_41_ConsentComplianceGate" in guidance
    assert "Rule_ConsentRequired" in guidance


def test_behavior_pack_keeps_site_configuration_below_factory_behavior() -> None:
    metadata = behavior_pack_metadata()
    assert metadata["id"] == "website-orb-standard-behavior"
    assert metadata["version"] == "1.0.0"
    assert metadata["startup_contract"] == "short_scripted_startup_then_live_runtime"
    assert "site_world_evidence" in metadata["customer_payload_scope"]
    assert "visitor_override" in metadata["layers"]
