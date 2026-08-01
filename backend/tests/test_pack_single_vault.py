import json
import importlib
import sys
import zipfile
from pathlib import Path


BACKEND_PATH = str((Path.cwd() / "backend").resolve())
if BACKEND_PATH not in sys.path:
    sys.path.insert(0, BACKEND_PATH)


def test_downloaded_orb_pack_contains_exactly_one_vault_system(tmp_path, monkeypatch):
    from app.core import storage

    monkeypatch.setattr(storage, "VAULT_ROOT", tmp_path)
    sys.modules.pop("app.pack_generator.generator", None)
    sys.modules.pop("app.pack_generator", None)
    generator = importlib.import_module("app.pack_generator.generator")
    result = generator.generate_pack_file(
        scan_data={"pages": [{"url": "https://example.test/"}]},
        site_id="42",
        domain="Example.Test",
        tier="standard",
        output_dir=tmp_path,
    )

    with zipfile.ZipFile(result["path"]) as archive:
        names = archive.namelist()
        manifest = json.loads(archive.read("manifest.json"))
        vault_manifest = json.loads(archive.read("vault_system/vault-manifest.json"))
        learning_template = json.loads(archive.read("vault_system/clients/example.test/website_orb_learning/learning-loop-template.json"))

    assert all("vault_system/" not in name or name.startswith("vault_system/") for name in names)
    assert manifest["storage_contract"]["single_storage_authority"] is True
    assert manifest["storage_contract"]["client_root"] == "vault_system/clients/example.test"
    assert vault_manifest["schema"] == "orb_weaver.single_vault.v1"
    assert "vault_system/clients/example.test/current/scan_data.json" in names
    assert "vault_system/clients/example.test/website_orb_learning/learning-loop-template.json" in names
    assert "vault_system/clients/example.test/website_orb_learning/posteriori/interactions.jsonl" in names
    assert "vault_system/clients/example.test/website_orb_learning/stump_ledger/stump-ledger.json" in names
    assert "vault_system/clients/example.test/website_orb_learning/promotion_queue/promotion-queue.json" in names
    assert "vault_system/clients/example.test/website_orb_learning/verified_cases.json" in names
    assert "vault_system/runtime/tts_cache/" in names
    assert "vault_system/identity/" in names
    assert "vault_system/permissions/" in names
    assert "vault_system/short_term_memory/" in names
    assert "vault_system/long_term_memory/" in names
    assert "vault_system/observations/cognition/workers/" in names
    assert "vault_system/verified_outcomes/" in names
    assert "vault_system/persistent_cache/" in names
    assert "vault_system/audit/" in names
    assert "scan_data.json" not in names
    assert learning_template["scope"]["site_specific"] is True
    assert learning_template["scope"]["cross_customer_learning"] is False
    assert learning_template["promotion_gate"]["never_promote_from_one_conversation"] is True
