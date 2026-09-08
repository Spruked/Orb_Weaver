from __future__ import annotations

import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

from manufacturing.website_orb.orchestrator import REQUIRED_PAYLOAD_FILES, manufacture_website_orb


def _evidence():
    return {
        "schema": "orb_weaver.full_scan_evidence.v1",
        "site_id": "site-1",
        "domain": "example.com",
        "scan_id": "scan-1",
        "captured_at": "2026-08-20T12:00:00+00:00",
        "scanner_version": "test-scanner/1.0",
        "pages": [{"page_id": "home", "url": "https://example.com/", "route": "/", "title": "Home", "content_hash": "page-hash"}],
        "evidence": [
            {
                "evidence_id": "product-1",
                "evidence_type": "product",
                "source_url": "https://example.com/product",
                "route": "/product",
                "selector": "#buy",
                "pointer_target_id": "buy-product",
                "content_hash": "product-hash",
                "confidence": 1.0,
                "verified": True,
                "payload": {"entity_id": "product-1", "name": "Known Product", "sku": "SKU-1", "price": {"amount": 49, "currency": "USD", "display_text": "$49"}},
            },
            {
                "evidence_id": "faq-1",
                "evidence_type": "faq",
                "source_url": "https://example.com/faq",
                "route": "/faq",
                "content_hash": "faq-hash",
                "confidence": 1.0,
                "verified": True,
                "payload": {"question": "When do you ship?", "answer": "We ship on weekdays."},
            },
        ],
    }


def test_manufacturer_builds_complete_delivery_ready_package(tmp_path):
    result = manufacture_website_orb(
        evidence=_evidence(),
        output_root=tmp_path,
        build_id="build-verified",
        owner_verification={"owner": "owner-1", "approved_artifacts": ["*"]},
        ephemeral=True,
    )

    assert result["status"] == "ready"
    assert result["delivery_ready"] is True
    vault_root = Path(result["package_paths"]["vault_root"])
    assert all((vault_root / relative).exists() for relative in REQUIRED_PAYLOAD_FILES)
    assert result["validation_results"]["catalog_validation"]["entry_count"] == 1
    dock_manifest = json.loads((Path(result["package_paths"]["dock_station"]) / "deployment" / "manifest.json").read_text())
    assert dock_manifest["manufacturing_pass"]["delivery_ready"] is True
    orb_template = Path(result["package_paths"]["dock_station"]) / "app" / "orb" / "template"
    assert (orb_template / "backend" / "app.py").is_file()
    assert (orb_template / "frontend" / "src" / "WebsiteORB.tsx").is_file()
    runtime_vault = orb_template / "runtime" / "vault_system"
    assert json.loads((runtime_vault / "payload" / "apriori" / "catalog.json").read_text())["entries"][0]["entity_id"] == "product-1"
    assert not (orb_template / "Orb_Vault_System" / "orb_vault_skg" / "vaults").exists()
    assert not (orb_template / "vendor" / "TPC_Triple_Predicate_Cubed" / "results").exists()
    assert not (orb_template / "vendor" / "TPC_Triple_Predicate_Cubed" / "vaults").exists()
    assert not (orb_template / "vendor" / "TPC_Triple_Predicate_Cubed" / "api").exists()

    package_env = {**os.environ, "PYTHONPATH": str(orb_template), "ORB_WEAVER_VAULT_ROOT": str(runtime_vault)}
    package_probe = """
import json
from backend.cognition.answer_engine import _get_vault_coordinator, answer_from_world
answer = answer_from_world('How much is Known Product?', '/', {'route': '/'}, {}, [])
coordinator = _get_vault_coordinator()
print(json.dumps({'answer': answer['answer'], 'priori': coordinator.priori_dir, 'posteriori': coordinator.posteriori_dir}))
"""
    first = subprocess.run([sys.executable, "-c", package_probe], env=package_env, text=True, capture_output=True, check=True)
    first_payload = json.loads(first.stdout.strip().splitlines()[-1])
    assert first_payload["answer"]
    assert Path(first_payload["priori"]).is_relative_to(runtime_vault)
    assert Path(first_payload["posteriori"]).is_relative_to(runtime_vault)
    assert (runtime_vault / "posteriori" / "orb_vault_skg" / "ledger" / "ledger_00000.jsonl").is_file()
    provenance = runtime_vault / "audit" / "glyph_trace" / "skg_runtime.jsonl"
    assert provenance.is_file()
    assert json.loads(provenance.read_text().splitlines()[-1])["event"] == "skg_resolution"

    # A fresh process reloads the same canonical knowledge/learning namespace.
    second = subprocess.run([sys.executable, "-c", package_probe], env=package_env, text=True, capture_output=True, check=True)
    second_payload = json.loads(second.stdout.strip().splitlines()[-1])
    assert second_payload["answer"] == first_payload["answer"]

    fail_closed_env = {key: value for key, value in package_env.items() if key != "ORB_WEAVER_VAULT_ROOT"}
    missing_root = subprocess.run([sys.executable, "-c", "from backend.cognition.answer_engine import answer_from_world; answer_from_world('How much is Known Product?', '/', {'route': '/'}, {}, [])"], env=fail_closed_env, text=True, capture_output=True)
    assert missing_root.returncode != 0
    assert "ORB_WEAVER_VAULT_ROOT is required" in missing_root.stderr
    assert not (orb_template / "Orb_Vault_System" / "orb_vault_skg" / "vaults").exists()

    answer_probe = "from backend.cognition.answer_engine import answer_from_world; answer_from_world('How much is Known Product?', '/', {'route': '/'}, {}, [])"
    rejected_roots = (
        tmp_path / "outside-vault",
        orb_template / "Orb_Vault_System" / "orb_vault_skg" / "vaults",
        orb_template / "vendor" / "TPC_Triple_Predicate_Cubed" / "results",
        runtime_vault / ".." / ".." / "escaped-vault",
    )
    for rejected_root in rejected_roots:
        rejected = subprocess.run(
            [sys.executable, "-c", answer_probe],
            env={**package_env, "ORB_WEAVER_VAULT_ROOT": str(rejected_root)},
            text=True,
            capture_output=True,
        )
        assert rejected.returncode != 0
        assert "must reference the manufactured runtime/vault_system root" in rejected.stderr

    # A correctly named canonical location may not escape by resolving to an
    # external directory through a symlink.
    external_vault = tmp_path / "external-symlink-vault"
    runtime_vault.rename(external_vault)
    runtime_vault.symlink_to(external_vault, target_is_directory=True)
    symlinked_root = subprocess.run([sys.executable, "-c", answer_probe], env=package_env, text=True, capture_output=True)
    assert symlinked_root.returncode != 0
    assert "must not be a symbolic link" in symlinked_root.stderr
    with zipfile.ZipFile(result["package_paths"]["orbpack"]) as archive:
        names = archive.namelist()
    assert "dock-station/app/orb/template/runtime/vault_system/payload/catalog.db" in names
    assert "dock-station/app/orb/template/backend/app.py" in names
    assert "dock-station/app/orb/template/Orb_Vault_System/orb_vault_skg/vault/orb_assistant/vault_coordinator.py" in names
    assert sum(name.endswith("payload/payload_manifest.json") for name in names) == 1
    assert not any("Orb_Vault_System/orb_vault_skg/vaults/" in name for name in names)
    assert not any("vendor/TPC_Triple_Predicate_Cubed/results/" in name for name in names)
    assert not any("vendor/TPC_Triple_Predicate_Cubed/vaults/" in name for name in names)
    assert not any("vendor/TPC_Triple_Predicate_Cubed/api/" in name for name in names)


def test_manufacturer_blocks_unverified_delivery(tmp_path):
    result = manufacture_website_orb(
        evidence=_evidence(),
        output_root=tmp_path,
        build_id="build-pending",
        ephemeral=True,
    )
    assert result["status"] == "awaiting_verification"
    assert result["delivery_ready"] is False
    assert result["package_paths"]["orbpack"] is None
    assert any("owner_verification_incomplete" in reason for reason in result["failure_reasons"])


def test_manufacturer_reports_lifecycle_and_invalid_evidence_failure(tmp_path):
    stages = []
    result = manufacture_website_orb(
        evidence=_evidence(),
        output_root=tmp_path,
        build_id="build-stages",
        owner_verification={"owner": "owner-1", "approved_artifacts": ["*"]},
        ephemeral=True,
        status_callback=lambda status, details: stages.append((status, details)),
    )
    assert [status for status, _ in stages] == ["preparing", "compiling", "assembling", "validating", "ready"]
    assert stages[-1][1]["delivery_ready"] is True
    assert result["delivery_ready"] is True

    failed_stages = []
    failed = manufacture_website_orb(
        evidence={"schema": "orb_weaver.full_scan_evidence.v1"},
        output_root=tmp_path,
        status_callback=lambda status, details: failed_stages.append((status, details)),
    )
    assert [status for status, _ in failed_stages] == ["preparing", "failed"]
    assert failed["delivery_ready"] is False
