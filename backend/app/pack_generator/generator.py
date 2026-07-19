from __future__ import annotations

import json
import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict


VAULT_DIRECTORIES = (
    "apriori/",
    "posteriori/",
    "identity/",
    "permissions/",
    "site_or_environment_data/",
    "client_or_owner_data/",
    "short_term_memory/",
    "long_term_memory/",
    "workflow_state/",
    "observations/cognition/workers/",
    "verified_outcomes/",
    "runtime_state/",
    "persistent_cache/",
    "audit/",
    "databases/",
    "reports/",
    "indexes/",
    "manifests/",
    "schemas/",
    "integrations/",
    "runtime/tts_cache/",
    "runtime/state/",
    "runtime/logs/",
    "backups/",
)

CLIENT_DIRECTORIES = (
    "current/",
    "history/",
    "preflight/",
    "runs/",
    "recommendations/",
    "website_orb_context/",
    "claims/",
    "reports/",
    "visitor_questions/",
    "owner_seed_changes/",
    "local_index/",
)


def _safe_name(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "_", value.strip().lower())
    return cleaned.strip("._-") or "orb_site"


def generate_pack_file(scan_data: Dict, site_id: str, domain: str, tier: str, output_dir: Path | str) -> Dict:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.utcnow().isoformat()
    filename = f"{_safe_name(domain)}_{tier}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.orbpack"
    pack_path = output_root / filename
    client_key = _safe_name(domain)
    manifest = {
        "schema": "orb_weaver.tpc_pack.v1",
        "site_id": site_id,
        "domain": domain,
        "tier": tier,
        "generated_at": generated_at,
        "source": "orb_weaver",
        "storage_contract": {
            "schema": "orb_weaver.single_vault.v1",
            "root": "vault_system",
            "single_storage_authority": True,
            "client_root": f"vault_system/clients/{client_key}",
            "rule": "No component may create a second vault_system or persist outside this root.",
        },
    }
    vault_manifest = {
        "schema": "orb_weaver.single_vault.v1",
        "vault_id": f"orb-vault-{site_id}",
        "site_id": site_id,
        "domain": domain,
        "client_key": client_key,
        "single_storage_authority": True,
        "generated_at": generated_at,
        "namespaces": [path.rstrip("/") for path in VAULT_DIRECTORIES],
    }
    vault_readme = """# ORB Vault System\n\nThis is the downloaded ORB's only storage authority.\n\nAll scans and site-specific data belong under `clients/<domain>/`. Runtime, cognition, reports, indexes, manifests, databases, and backups remain separate namespaces inside this same `vault_system/` directory. No adapter or component may create another vault system elsewhere.\n"""
    with zipfile.ZipFile(pack_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, indent=2, default=str))
        archive.writestr("vault_system/README.md", vault_readme)
        archive.writestr("vault_system/vault-manifest.json", json.dumps(vault_manifest, indent=2))
        for directory in VAULT_DIRECTORIES:
            archive.writestr(f"vault_system/{directory}", "")
        client_base = f"vault_system/clients/{client_key}/"
        archive.writestr("vault_system/clients/", "")
        archive.writestr(client_base, "")
        for directory in CLIENT_DIRECTORIES:
            archive.writestr(f"{client_base}{directory}", "")
        scan_payload = json.dumps(scan_data, indent=2, default=str)
        archive.writestr(f"{client_base}current/scan_data.json", scan_payload)
    return {
        "filename": filename,
        "path": str(pack_path),
        "size_bytes": pack_path.stat().st_size,
        "generated_at": generated_at,
        "tier": tier,
        "domain": domain,
    }
