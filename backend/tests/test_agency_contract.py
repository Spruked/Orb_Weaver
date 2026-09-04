from app.agency.contract import agency_contract_status, load_primitive_registry


def test_canonical_agency_registry_loads():
    registry = load_primitive_registry()
    assert registry["schema"] == "tti.primitives.v1"
    assert registry["registry_version"] == "1.0.0"
    assert len(registry["motion"]) == 11
    assert len(registry["speech"]) == 4
    assert len(registry["expression"]) == 7
    assert "focus_on" in registry["motion"]
    assert "speak" in registry["speech"]
    assert "acknowledge" in registry["expression"]


def test_agency_status_is_ready_with_canonical_files():
    status = agency_contract_status(active_connections=2)
    assert status["schema"] == "tti.agency_status.v1"
    assert status["status"] == "ready"
    assert status["contract_present"] is True
    assert status["primitives_present"] is True
    assert status["active_orb_telemetry_connections"] == 2
    assert status["core4_authority"] == "existing_orb_weaver_core4"
    assert status["errors"] == []
