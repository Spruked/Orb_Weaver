from __future__ import annotations

import json
import hashlib
import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.storage import require_vault_path
from app.orb.site_learning import clean_slate_files, learning_loop_template


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
    "website_orb_learning/",
    "website_orb_learning/posteriori/",
    "website_orb_learning/stump_ledger/",
    "website_orb_learning/promotion_queue/",
    "website_orb_learning/indexes/",
)


def _safe_name(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "_", value.strip().lower())
    return cleaned.strip("._-") or "orb_site"


def _archive_directory(archive: zipfile.ZipFile, source: Path, archive_root: str) -> None:
    for target in sorted(source.rglob("*"), key=lambda item: item.relative_to(source).as_posix()):
        relative = target.relative_to(source).as_posix()
        destination = f"{archive_root.rstrip('/')}/{relative}"
        if target.is_symlink():
            raise ValueError(f"Pack source contains a forbidden symlink: {relative}")
        if target.is_dir():
            archive.writestr(f"{destination}/", "")
        elif target.is_file():
            archive.write(target, destination)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def generate_pack_file(
    scan_data: Dict,
    site_id: str,
    domain: str,
    tier: str,
    output_dir: Path | str,
    *,
    assembled_dock_station: Optional[Path | str] = None,
    manufacturing_result: Optional[Dict[str, Any]] = None,
    ephemeral: bool = False,
) -> Dict:
    requested_output = Path(output_dir).expanduser().resolve()
    if ephemeral:
        if Path("/tmp") not in requested_output.parents:
            raise ValueError("Ephemeral ORB pack output must remain under /tmp")
        output_root = requested_output
    else:
        output_root = require_vault_path(requested_output, "ORB pack output")
    output_root.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.utcnow().isoformat()
    filename = f"{_safe_name(domain)}_{tier}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.orbpack"
    pack_path = output_root / filename
    client_key = _safe_name(domain)
    dock_station = Path(assembled_dock_station).resolve() if assembled_dock_station else None
    embedded_vault = dock_station / "app" / "orb" / "template" / "runtime" / "vault_system" if dock_station else None
    if dock_station and (not dock_station.is_dir() or not embedded_vault.is_dir()):
        raise ValueError("Assembled Dock Station must contain its manufactured vault_system")
    vault_root = "dock-station/app/orb/template/runtime/vault_system" if dock_station else "vault_system"
    manifest = {
        "schema": "orb_weaver.tpc_pack.v1",
        "site_id": site_id,
        "domain": domain,
        "tier": tier,
        "generated_at": generated_at,
        "source": "orb_weaver",
        "storage_contract": {
            "schema": "orb_weaver.single_vault.v1",
            "root": vault_root,
            "single_storage_authority": True,
            "client_root": f"{vault_root}/clients/{client_key}",
            "rule": "No component may create a second vault_system or persist outside this root.",
        },
        "site_learning_loop": learning_loop_template(site_id, domain),
        "delivery": {
            "assembled_dock_station": bool(dock_station),
            "delivery_ready": bool((manufacturing_result or {}).get("delivery_ready")),
            "build_id": (manufacturing_result or {}).get("build_id"),
            "manufacturing_manifest": "dock-station/deployment/manufacturing-result.json" if dock_station else None,
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
        if dock_station:
            _archive_directory(archive, dock_station, "dock-station")
        else:
            archive.writestr("vault_system/README.md", vault_readme)
            archive.writestr("vault_system/vault-manifest.json", json.dumps(vault_manifest, indent=2))
            for directory in VAULT_DIRECTORIES:
                archive.writestr(f"vault_system/{directory}", "")
            client_base = f"vault_system/clients/{client_key}/"
            archive.writestr("vault_system/clients/", "")
            archive.writestr(client_base, "")
            for directory in CLIENT_DIRECTORIES:
                archive.writestr(f"{client_base}{directory}", "")
            for relative_path, contents in clean_slate_files(site_id, domain).items():
                archive.writestr(f"{client_base}{relative_path}", contents)
            scan_payload = json.dumps(scan_data, indent=2, default=str)
            archive.writestr(f"{client_base}current/scan_data.json", scan_payload)
    return {
        "filename": filename,
        "path": str(pack_path),
        "size_bytes": pack_path.stat().st_size,
        "sha256": _sha256(pack_path),
        "generated_at": generated_at,
        "tier": tier,
        "domain": domain,
        "assembled_dock_station": bool(dock_station),
    }
