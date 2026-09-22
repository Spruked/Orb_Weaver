from __future__ import annotations

import re
import shutil
import unicodedata
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from .manifests import customer_manifest, load_template_manifest, write_json
from .validator import package_tree_hash as hash_package_tree
from .validator import validate_required_paths, verification_report


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TEMPLATE_ROOT = REPO_ROOT / "manufacturing" / "templates" / "dock_station_master"
DEFAULT_WEBSITE_ORB_TEMPLATE_ROOT = REPO_ROOT / "manufacturing" / "templates" / "Website_Orb_Final"
DEFAULT_BUILDS_ROOT = REPO_ROOT / "builds"
ID_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9._-]{0,78}[a-z0-9])?$")
WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}


def _windows_collision_key(value: str) -> str:
    return value.rstrip(" .").casefold()


def validate_identifier(value: str, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    if value != unicodedata.normalize("NFC", value):
        raise ValueError(f"{field_name} uses ambiguous Unicode normalization")
    if not value or value.strip() != value:
        raise ValueError(f"{field_name} must not be empty or padded")
    if not value.isascii():
        raise ValueError(f"{field_name} must be ASCII")
    if "/" in value or "\\" in value or ".." in value:
        raise ValueError(f"{field_name} must not contain traversal")
    if not ID_PATTERN.fullmatch(value):
        raise ValueError(f"{field_name} must use lowercase letters, numbers, dots, underscores, or hyphens")
    base_name = value.split(".", 1)[0].upper()
    if base_name in WINDOWS_RESERVED_NAMES:
        raise ValueError(f"{field_name} is a Windows-reserved name")
    if _windows_collision_key(value) != value:
        raise ValueError(f"{field_name} is unsafe on case-insensitive filesystems")
    return value


def validate_build_ids(customer_id: str, deployment_id: str) -> Dict[str, str]:
    customer = validate_identifier(customer_id, field_name="customer_id")
    deployment = validate_identifier(deployment_id, field_name="deployment_id")
    return {"customer_id": customer, "deployment_id": deployment}


def _copy_template(template_root: Path, build_root: Path) -> None:
    source = template_root / "dock-station"
    destination = build_root / "dock-station"
    if destination.exists():
        raise FileExistsError(f"Build destination already exists: {destination}")
    shutil.copytree(source, destination, symlinks=True)


def _copy_website_orb_template(template_root: Path, destination: Path) -> Dict[str, Any]:
    required = [
        {"path": "backend/app.py", "type": "file"},
        {"path": "frontend/widget.js", "type": "file"},
        {"path": "run.py", "type": "file"},
        {"path": "INSTALL.md", "type": "file"},
        {"path": "Orb_Vault_System/orb_vault_skg/vault/orb_assistant/vault_coordinator.py", "type": "file"},
    ]
    validation = validate_required_paths(template_root, required)
    # The upstream gold repository currently tracks development bytecode. It is
    # never copied into a manufactured package.
    source_forbidden = [
        path for path in validation.get("forbidden_payloads", [])
        if "__pycache__" not in path and not path.endswith((".pyc", ".pyo"))
    ]
    if validation.get("missing") or validation.get("wrong_type") or validation.get("unsafe_paths") or source_forbidden or validation.get("symlinks"):
        raise ValueError(f"Website ORB golden template is invalid: {validation}")
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    # Positive runtime allowlist: do not copy historical compiled_orb data,
    # source archives, old Vaults, recorded speech, or factory documents.
    for relative in ("backend", "Orb_Vault_System/orb_vault_skg/vault"):
        source = template_root / relative
        if source.is_dir():
            shutil.copytree(source, destination / relative,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", "*.test.*", "*_test.py"))
    for relative in ("run.py", "INSTALL.md"):
        source = template_root / relative
        if source.is_file():
            shutil.copy2(source, destination / relative)
    primitive = Path("vendor/TPC_Triple_Predicate_Cubed/core/geometric_primitives.py")
    (destination / primitive).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(template_root / primitive, destination / primitive)
    # The SKG implementation is shipped as code, not as a second package-local
    # persistence authority.  The manufactured runtime receives its one Vault
    # below runtime/vault_system during payload injection.
    legacy_skg_vaults = destination / "Orb_Vault_System" / "orb_vault_skg" / "vaults"
    if legacy_skg_vaults.exists():
        shutil.rmtree(legacy_skg_vaults)

    # Website ORB uses only the vendored geometric primitives.  Do not ship the
    # vendor API, its results vault, substrate tooling, or its own vault module
    # as an accidentally runnable persistence surface.
    vendor_root = destination / "vendor" / "TPC_Triple_Predicate_Cubed"
    for relative in ("api", "results", "tools", "vaults", "results_vault.py", "start_tpc_api.bat"):
        candidate = vendor_root / relative
        if candidate.is_dir():
            shutil.rmtree(candidate)
        elif candidate.exists():
            candidate.unlink()
    (destination / "deployment").mkdir(exist_ok=True)
    (destination / "assets").mkdir(exist_ok=True)
    shutil.copy2(template_root / "frontend/widget.js", destination / "assets/widget.js")
    return hash_package_tree(destination)


def _inject_website_orb_payload(payload_root: Path, orb_template: Path) -> None:
    runtime_vault = orb_template / "runtime" / "vault_system"
    if runtime_vault.exists():
        shutil.rmtree(runtime_vault)
    runtime_vault.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(payload_root, runtime_vault, symlinks=True)

    # All operating and knowledge artifacts are read from this one Vault.
    # There is no compiled_orb mirror or fall-through to source fixtures.


def _build_required_paths(required_paths: list[Any]) -> list[Any]:
    return [
        {
            **path,
            "path": path["path"].replace("dock-station/", "", 1),
        } if isinstance(path, dict) and str(path.get("path", "")).startswith("dock-station/") else path
        for path in required_paths
    ] + [
        {"path": "deployment/manifest.json", "type": "file"},
        {"path": "reports", "type": "directory"},
    ]


def _remove_staging(staging_root: Path) -> None:
    if staging_root.exists():
        shutil.rmtree(staging_root)


def build_customer_dock_station(
    *,
    customer_id: str,
    deployment_id: str,
    template_root: Optional[Path] = None,
    builds_root: Optional[Path] = None,
    payload_root: Optional[Path] = None,
    website_orb_template_root: Optional[Path] = None,
    manufacturing_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    resolved_template = (template_root or DEFAULT_TEMPLATE_ROOT).resolve()
    resolved_builds = (builds_root or DEFAULT_BUILDS_ROOT).resolve()
    ids = validate_build_ids(customer_id, deployment_id)
    template_manifest = load_template_manifest(resolved_template)
    required_paths = template_manifest.get("required_paths", [])
    template_validation = validate_required_paths(resolved_template, required_paths)
    if not template_validation["passed"]:
        return {
            "status": "template_invalid",
            "template_root": str(resolved_template),
            "template_validation": template_validation,
        }
    template_tree = hash_package_tree(resolved_template / "dock-station")
    if template_tree["symlinks"]:
        return {
            "status": "template_invalid",
            "template_root": str(resolved_template),
            "template_validation": {
                **template_validation,
                "passed": False,
                "symlinks": sorted(set(template_validation.get("symlinks", []) + template_tree["symlinks"])),
            },
        }

    resolved_payload = payload_root.resolve() if payload_root else None
    payload_tree = hash_package_tree(resolved_payload) if resolved_payload else None
    if resolved_payload and (not resolved_payload.is_dir() or payload_tree["symlinks"]):
        raise ValueError("Website ORB payload must be an existing symlink-free directory")

    build_root = resolved_builds / ids["customer_id"] / ids["deployment_id"]
    if build_root.exists():
        raise FileExistsError(f"Build destination already exists: {build_root}")

    staging_root = resolved_builds / ".staging" / f"{ids['customer_id']}.{ids['deployment_id']}.{uuid.uuid4().hex}"
    staging_dock_station = staging_root / "dock-station"
    build_root.parent.mkdir(parents=True, exist_ok=True)
    staging_root.parent.mkdir(parents=True, exist_ok=True)

    try:
        _copy_template(resolved_template, staging_root)
        website_orb_tree = None
        resolved_website_orb_template = (
            website_orb_template_root.resolve()
            if website_orb_template_root
            else DEFAULT_WEBSITE_ORB_TEMPLATE_ROOT.resolve() if template_root is None else None
        )
        if resolved_website_orb_template:
            website_orb_tree = _copy_website_orb_template(
                resolved_website_orb_template,
                staging_dock_station / "app" / "orb" / "template",
            )
        if resolved_payload:
            _inject_website_orb_payload(resolved_payload, staging_dock_station / "app" / "orb" / "template")
        manifest = customer_manifest(
            template_manifest=template_manifest,
            customer_id=ids["customer_id"],
            deployment_id=ids["deployment_id"],
            template_tree_hash=template_tree["tree_hash"],
            payload_tree_hash=payload_tree["tree_hash"] if payload_tree else None,
            manufacturing_metadata=manufacturing_metadata,
        )
        write_json(staging_dock_station / "deployment" / "manifest.json", manifest)
        (staging_dock_station / "reports").mkdir(parents=True, exist_ok=True)

        build_required_paths = _build_required_paths(required_paths)
        if resolved_payload:
            build_required_paths.append({"path": "app/orb/template/runtime/vault_system/payload/payload_manifest.json", "type": "file"})
        build_validation = validate_required_paths(staging_dock_station, build_required_paths)
        package_tree = hash_package_tree(staging_dock_station)
        report_path = staging_dock_station / "reports" / "verification-report.json"
        report = verification_report(
            customer_id=ids["customer_id"],
            deployment_id=ids["deployment_id"],
            template_validation=template_validation,
            build_validation=build_validation,
            manifest_hash=manifest["manifest_hash"],
            template_tree_hash=template_tree["tree_hash"],
            package_tree_hash=package_tree["tree_hash"],
            template_file_hashes=template_tree["files"],
            package_file_hashes=package_tree["files"],
        )
        write_json(report_path, report)

        final_validation = validate_required_paths(
            staging_dock_station,
            build_required_paths + [{"path": "reports/verification-report.json", "type": "file"}],
        )
        report = verification_report(
            customer_id=ids["customer_id"],
            deployment_id=ids["deployment_id"],
            template_validation=template_validation,
            build_validation=final_validation,
            manifest_hash=manifest["manifest_hash"],
            template_tree_hash=template_tree["tree_hash"],
            package_tree_hash=package_tree["tree_hash"],
            template_file_hashes=template_tree["files"],
            package_file_hashes=package_tree["files"],
        )
        write_json(report_path, report)

        if not report["passed"]:
            _remove_staging(staging_root)
            return {
                "status": "validation_failed",
                "template_root": str(resolved_template),
                "template_validation": template_validation,
                "build_validation": final_validation,
                "passed": False,
            }

        staging_root.rename(build_root)
    except Exception:
        _remove_staging(staging_root)
        raise

    return {
        "status": "created" if report["passed"] else "validation_failed",
        "build_root": str(build_root),
        "dock_station": str(build_root / "dock-station"),
        "deployment_manifest": str(build_root / "dock-station" / "deployment" / "manifest.json"),
        "verification_report": str(build_root / "dock-station" / "reports" / "verification-report.json"),
        "manifest_hash": manifest["manifest_hash"],
        "template_tree_hash": template_tree["tree_hash"],
        "package_tree_hash": package_tree["tree_hash"],
        "payload_tree_hash": payload_tree["tree_hash"] if payload_tree else None,
        "website_orb_template_tree_hash": website_orb_tree["tree_hash"] if website_orb_tree else None,
        "passed": report["passed"],
    }
