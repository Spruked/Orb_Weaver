from __future__ import annotations

import json
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
    with zipfile.ZipFile(result["package_paths"]["orbpack"]) as archive:
        names = archive.namelist()
    assert "dock-station/app/orb/template/runtime/vault_system/payload/catalog.db" in names
    assert sum(name.endswith("payload/payload_manifest.json") for name in names) == 1


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
