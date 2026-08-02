from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List


FORBIDDEN_PAYLOAD_NAMES = {
    ".git",
    "__pycache__",
    "node_modules",
    "venv",
    ".venv",
    "dist",
}


def _utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _normalize_requirement(requirement: Any) -> Dict[str, str]:
    if isinstance(requirement, str):
        return {"path": requirement, "type": "any"}
    path = str(requirement.get("path", "")).strip()
    expected_type = str(requirement.get("type", "any")).strip().lower() or "any"
    return {"path": path, "type": expected_type}


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _contained_target(root: Path, relative_path: str) -> Path | None:
    raw = Path(relative_path)
    if raw.is_absolute() or ".." in raw.parts:
        return None
    resolved_root = root.resolve()
    target = (resolved_root / raw).resolve(strict=False)
    if not _is_relative_to(target, resolved_root):
        return None
    return target


def _type_matches(target: Path, expected_type: str) -> bool:
    if expected_type == "any":
        return target.exists()
    if expected_type == "file":
        return target.is_file()
    if expected_type == "directory":
        return target.is_dir()
    return False


def _relative(root: Path, target: Path) -> str:
    return target.relative_to(root).as_posix()


def find_forbidden_payloads(root: Path) -> Dict[str, List[str]]:
    if not root.exists():
        return {"forbidden_payloads": [], "symlinks": []}
    forbidden: List[str] = []
    symlinks: List[str] = []
    for target in root.rglob("*"):
        if target.is_symlink():
            symlinks.append(_relative(root, target))
            continue
        if target.name in FORBIDDEN_PAYLOAD_NAMES:
            forbidden.append(_relative(root, target))
        elif target.suffix in {".pyc", ".pyo"}:
            forbidden.append(_relative(root, target))
    return {"forbidden_payloads": sorted(forbidden), "symlinks": sorted(symlinks)}


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def package_tree_hash(root: Path) -> Dict[str, Any]:
    resolved_root = root.resolve()
    files: List[Dict[str, Any]] = []
    symlinks: List[str] = []
    for target in sorted(resolved_root.rglob("*"), key=lambda item: item.relative_to(resolved_root).as_posix()):
        relative_path = target.relative_to(resolved_root).as_posix()
        if target.is_symlink():
            symlinks.append(relative_path)
            continue
        if not target.is_file():
            continue
        files.append({
            "path": relative_path,
            "sha256": hash_file(target),
            "size_bytes": target.stat().st_size,
        })
    canonical = json.dumps(files, sort_keys=True, separators=(",", ":"))
    return {
        "tree_hash": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "files": files,
        "symlinks": symlinks,
    }


def validate_required_paths(root: Path, required_paths: Iterable[Any]) -> Dict[str, Any]:
    missing: List[str] = []
    wrong_type: List[Dict[str, str]] = []
    unsafe_paths: List[str] = []
    present: List[str] = []
    resolved_root = root.resolve()
    for raw_requirement in required_paths:
        requirement = _normalize_requirement(raw_requirement)
        relative_path = requirement["path"]
        expected_type = requirement["type"]
        target = _contained_target(resolved_root, relative_path)
        if target is None:
            unsafe_paths.append(relative_path)
            continue
        if target.is_symlink():
            wrong_type.append({
                "path": relative_path,
                "expected": expected_type,
                "actual": "symlink",
            })
            continue
        if not target.exists():
            missing.append(relative_path)
        elif _type_matches(target, expected_type):
            present.append(relative_path)
        else:
            wrong_type.append({
                "path": relative_path,
                "expected": expected_type,
                "actual": "directory" if target.is_dir() else "file" if target.is_file() else "other",
            })
    forbidden = find_forbidden_payloads(resolved_root)
    return {
        "passed": not missing and not wrong_type and not unsafe_paths and not forbidden["forbidden_payloads"] and not forbidden["symlinks"],
        "checked_at": _utc_now(),
        "present": present,
        "missing": missing,
        "wrong_type": wrong_type,
        "unsafe_paths": unsafe_paths,
        "forbidden_payloads": forbidden["forbidden_payloads"],
        "symlinks": forbidden["symlinks"],
    }


def verification_report(
    *,
    customer_id: str,
    deployment_id: str,
    template_validation: Dict[str, Any],
    build_validation: Dict[str, Any],
    manifest_hash: str,
    template_tree_hash: str,
    package_tree_hash: str,
    template_file_hashes: List[Dict[str, Any]],
    package_file_hashes: List[Dict[str, Any]],
) -> Dict[str, Any]:
    return {
        "schema": "orb_weaver.customer_dock_station_verification_report.v1",
        "customer_id": customer_id,
        "deployment_id": deployment_id,
        "passed": bool(template_validation.get("passed") and build_validation.get("passed")),
        "template_validation": template_validation,
        "build_validation": build_validation,
        "manifest_hash": manifest_hash,
        "template_tree_hash": template_tree_hash,
        "package_tree_hash": package_tree_hash,
        "template_file_hashes": template_file_hashes,
        "package_file_hashes": package_file_hashes,
        "generated_at": _utc_now(),
    }
