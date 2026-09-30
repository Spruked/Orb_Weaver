from pathlib import Path

from app.core.timekeeping import event_timestamp, stamp_record


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_iss_event_timestamp_contains_complete_time_envelope() -> None:
    envelope = event_timestamp(source="test")
    required = {
        "iss_time_ns",
        "epoch_timestamp_ns",
        "standard_timestamp",
        "julian_timestamp",
        "iss_timestamp",
        "stardate",
        "local_display_time",
        "reference_frame",
        "clock_id",
        "proper_time_ns",
        "mission_elapsed_ns",
        "uncertainty_ns",
        "relativistic_correction_ns",
        "anchor_hash",
    }
    assert required.issubset(envelope)
    assert envelope["iss_time_ns"] > 0


def test_stamp_record_preserves_legacy_fields_and_adds_iss_ordering() -> None:
    record = stamp_record({"event": "test"}, source="test")
    assert record["timestamp_schema"] == "orb_weaver.iss_timestamp.v1"
    assert record["timestamp_envelope"]["iss_time_ns"] == record["iss_time_ns"]
    assert record["recorded_at"] == record["timestamp"]
    assert record["created_at"] == record["timestamp"]
    assert record["updated_at"] == record["timestamp"]


def test_syncrometer_source_and_manufactured_copy_are_git_free() -> None:
    source = REPO_ROOT / "vault_system" / "Interplanetary_Stardate_Syncrometer"
    manufactured = REPO_ROOT / "manufacturing" / "templates" / "Website_Orb_Final" / "backend" / "vendor" / "interplanetary_stardate_syncrometer"
    assert (source / "iss_module" / "core" / "utils.py").is_file()
    assert (manufactured / "iss_module" / "core" / "utils.py").is_file()
    assert not (source / ".git").exists()
    assert not any(path.name == ".git" for path in manufactured.rglob("*"))
