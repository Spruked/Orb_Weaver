from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import re
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[3]
AGENCY_ROOT = REPO_ROOT / "agency"
CONTRACT_PATH = AGENCY_ROOT / "AGENCY_CONTRACT.md"
PRIMITIVES_PATH = AGENCY_ROOT / "primitives.yaml"
SOURCE_COMMIT = "e151c5640d933dc488dc8629b1c6a8f0e6d8fcb2"

REQUIRED_MOTION = {
    "idle_in_region",
    "focus_on",
    "approach",
    "point",
    "servo_orbit",
    "smooth_glide",
}
REQUIRED_SPEECH = {"speak", "whisper", "announce", "silent"}
REQUIRED_EXPRESSION = {
    "acknowledge",
    "listen",
    "think",
    "celebrate",
    "reassure",
    "confused",
}


def _file_sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_primitive_registry(path: Path = PRIMITIVES_PATH) -> Dict[str, Any]:
    """Parse the small canonical primitive registry without adding a YAML dependency."""
    if not path.is_file():
        raise FileNotFoundError(path)

    registry: Dict[str, Any] = {
        "registry_version": None,
        "schema": None,
        "motion": [],
        "speech": [],
        "expression": [],
    }
    section: str | None = None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("registry_version:"):
            registry["registry_version"] = line.split(":", 1)[1].strip().strip('"\'')
            continue
        if line.startswith("schema:"):
            registry["schema"] = line.split(":", 1)[1].strip().strip('"\'')
            continue
        if line in {"motion:", "speech:", "expression:"}:
            section = line[:-1]
            continue
        match = re.match(r"-\s+id:\s+([A-Za-z0-9_\-]+)$", line)
        if match and section:
            registry[section].append(match.group(1))

    return registry


def _missing(required: set[str], actual: List[str]) -> List[str]:
    return sorted(required.difference(actual))


def agency_contract_status(active_connections: int = 0) -> Dict[str, Any]:
    contract_present = CONTRACT_PATH.is_file()
    primitives_present = PRIMITIVES_PATH.is_file()
    errors: List[str] = []
    registry: Dict[str, Any] = {
        "registry_version": None,
        "schema": None,
        "motion": [],
        "speech": [],
        "expression": [],
    }

    if not contract_present:
        errors.append("Canonical AGENCY_CONTRACT.md is missing")
    if primitives_present:
        try:
            registry = load_primitive_registry()
        except Exception as exc:
            errors.append(f"Primitive registry parse failed: {exc}")
    else:
        errors.append("Canonical primitives.yaml is missing")

    if registry.get("schema") != "tti.primitives.v1":
        errors.append("Primitive registry schema is not tti.primitives.v1")

    for label, required in (
        ("motion", REQUIRED_MOTION),
        ("speech", REQUIRED_SPEECH),
        ("expression", REQUIRED_EXPRESSION),
    ):
        missing = _missing(required, list(registry.get(label) or []))
        if missing:
            errors.append(f"Missing {label} primitives: {', '.join(missing)}")

    all_ids = [
        *list(registry.get("motion") or []),
        *list(registry.get("speech") or []),
        *list(registry.get("expression") or []),
    ]
    duplicates = sorted({primitive_id for primitive_id in all_ids if all_ids.count(primitive_id) > 1})
    if duplicates:
        errors.append(f"Duplicate primitive ids: {', '.join(duplicates)}")

    return {
        "schema": "tti.agency_status.v1",
        "status": "ready" if not errors else "degraded",
        "habitat": "website",
        "source_commit": SOURCE_COMMIT,
        "registry_version": registry.get("registry_version"),
        "registry_schema": registry.get("schema"),
        "contract_present": contract_present,
        "primitives_present": primitives_present,
        "contract_sha256": _file_sha256(CONTRACT_PATH),
        "primitives_sha256": _file_sha256(PRIMITIVES_PATH),
        "primitive_counts": {
            "motion": len(registry.get("motion") or []),
            "speech": len(registry.get("speech") or []),
            "expression": len(registry.get("expression") or []),
        },
        "active_orb_telemetry_connections": int(active_connections),
        "core4_authority": "existing_orb_weaver_core4",
        "adapter_authority": "consume_authorized_envelopes_only",
        "errors": errors,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
