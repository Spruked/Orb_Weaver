import importlib.util
import json
from pathlib import Path


COMPILER_PATH = Path.cwd() / "manufacturing" / "website_orb" / "compile_vaults.py"


def _load_compiler():
    spec = importlib.util.spec_from_file_location("website_orb_compile_vaults", COMPILER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_compile_vaults_uses_only_verified_settled_truth(tmp_path):
    compiler = _load_compiler()
    document = {
        "schema": "orb_weaver.full_scan_evidence.v1",
        "site_id": "true-mark-1",
        "domain": "truemark.example",
        "scan_id": "scan-1",
        "captured_at": "2026-08-19T00:00:00+00:00",
        "scanner_version": "test",
        "pages": [],
        "evidence": [
            {
                "evidence_id": "prod-1",
                "evidence_type": "product",
                "source_url": "https://truemark.example/product",
                "route": "/product",
                "selector": "#buy",
                "pointer_target_id": "target-buy",
                "content_hash": "hash-prod-1",
                "confidence": 0.99,
                "verified": True,
                "payload": {
                    "entity_id": "product-1",
                    "name": "Verified Product",
                    "sku": "SKU-1",
                    "price": {"amount": 99.0, "currency": "USD", "display_text": "$99"},
                    "allowed_actions": ["point", "highlight", "scroll"],
                },
            },
            {
                "evidence_id": "prod-guess",
                "evidence_type": "product",
                "source_url": "https://truemark.example/guess",
                "route": "/guess",
                "content_hash": "hash-guess",
                "confidence": 0.5,
                "verified": False,
                "payload": {"name": "Unverified Guess", "price": "$1"},
            },
            {
                "evidence_id": "faq-1",
                "evidence_type": "faq",
                "source_url": "https://truemark.example/faq",
                "route": "/faq",
                "content_hash": "hash-faq",
                "confidence": 1.0,
                "verified": True,
                "payload": {"question": "What is it?", "answer": "A verified answer."},
            },
            {
                "evidence_id": "policy-approved",
                "evidence_type": "policy",
                "source_url": "https://truemark.example/policy",
                "route": "/policy",
                "content_hash": "hash-policy-1",
                "confidence": 1.0,
                "verified": True,
                "payload": {"title": "Returns", "text": "Approved return policy.", "owner_approved": True},
            },
            {
                "evidence_id": "policy-not-approved",
                "evidence_type": "policy",
                "source_url": "https://truemark.example/policy-2",
                "route": "/policy-2",
                "content_hash": "hash-policy-2",
                "confidence": 1.0,
                "verified": True,
                "payload": {"title": "Draft", "text": "Not owner approved.", "owner_approved": False},
            },
        ],
    }

    written = compiler.write_build(document, tmp_path)
    catalog = json.loads(Path(written["catalog"]).read_text())
    qa = json.loads(Path(written["qa"]).read_text())
    policies = json.loads(Path(written["policies"]).read_text())
    pointers = json.loads(Path(written["pointer_correspondence"]).read_text())

    assert [item["name"] for item in catalog["entries"]] == ["Verified Product"]
    assert catalog["entries"][0]["price"]["amount"] == 99.0
    assert catalog["entries"][0]["price"]["currency"] == "USD"
    assert qa["entries"][0]["answer"] == "A verified answer."
    assert [rule["title"] for rule in policies["rules"]] == ["Returns"]
    assert pointers["records"][0]["pointer_target_id"] == "target-buy"
    assert pointers["records"][0]["entity_id"] == "product-1"
