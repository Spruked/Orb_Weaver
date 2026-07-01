"""
ORB SKIN LOADER — WEB ORB (FastAPI)
Handles .orbskin packages for the website ORB / Orb Weaver backend.

Endpoints:
  POST   /skin/load          Upload and activate a .orbskin package
  POST   /skin/rollback      Rollback to previous skin
  GET    /skin/active        Get current active skin info
  DELETE /skin/clear         Clear active skin
  GET    /skin/asset/{path}  Serve an extracted skin asset

Wiring: Include this router in your main FastAPI app:
  from skin_loader import router as skin_router
  app.include_router(skin_router, prefix="/api")
"""

import hashlib
import io
import json
import os
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

SKIN_STORE_DIR = Path(os.getenv("ORB_SKIN_STORE", "./data/skins"))
RUNTIME_VERSION = "1.0.0"
ORB_TARGET = "website"

router = APIRouter(tags=["OrbSkin"])

# ─────────────────────────────────────────────
# IN-MEMORY STATE  (swap for DB/Redis in production)
# ─────────────────────────────────────────────

_state: dict = {
    "active": None,       # SkinBundle dict
    "rollback": None,     # SkinBundle dict
    "active_path": None,
    "rollback_path": None,
}

# ─────────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────────

class ValidationIssue(BaseModel):
    code: str
    field: Optional[str] = None
    message: str

class ValidationResult(BaseModel):
    valid: bool
    skin_id: str
    errors: list[ValidationIssue]
    warnings: list[ValidationIssue]
    validated_at: str

class SkinInfo(BaseModel):
    skin_id: str
    name: str
    loaded_at: str
    rollback_available: bool

# ─────────────────────────────────────────────
# VALIDATION  (mirrors TS validator logic)
# ─────────────────────────────────────────────

def validate_manifest(manifest: dict, for_target: str, package_hash: str) -> ValidationResult:
    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []
    now = datetime.now(timezone.utc).isoformat()

    # Schema version
    if manifest.get("schema_version") != "1.0":
        warnings.append(ValidationIssue(
            code="SCHEMA_VERSION_MISMATCH",
            field="schema_version",
            message=f"Expected 1.0, got {manifest.get('schema_version')} — may still load"
        ))

    # Required fields
    for field in ["skin_id", "name", "version"]:
        if not manifest.get(field):
            errors.append(ValidationIssue(code="MISSING_FIELD", field=field, message=f'"{field}" required'))

    # Creator
    creator = manifest.get("creator", {})
    if not creator.get("creator_id") or not creator.get("display_name"):
        errors.append(ValidationIssue(code="MISSING_FIELD", field="creator", message="creator.creator_id and creator.display_name required"))

    # Target compatibility
    cls = manifest.get("classification", {})
    supported = cls.get("supported_orbs", [])
    if supported and for_target not in supported and "all" not in supported:
        errors.append(ValidationIssue(
            code="UNSUPPORTED_TARGET",
            field="classification.supported_orbs",
            message=f'Skin does not support target "{for_target}". Supported: {", ".join(supported)}'
        ))

    # Visuals
    vis = manifest.get("visuals", {})
    if not vis:
        errors.append(ValidationIssue(code="MISSING_FIELD", field="visuals", message='"visuals" block required'))
    else:
        for f in ["preview", "body_asset", "docked_icon"]:
            if not vis.get(f):
                errors.append(ValidationIssue(code="MISSING_ASSET", field=f"visuals.{f}", message=f'"visuals.{f}" required'))

    # Behavior hard walls
    bl = manifest.get("behavior_limits", {})
    if not bl:
        errors.append(ValidationIssue(code="MISSING_FIELD", field="behavior_limits", message='"behavior_limits" block required'))
    else:
        if bl.get("changes_visuals_only") is not True:
            errors.append(ValidationIssue(
                code="BEHAVIOR_VIOLATION",
                field="behavior_limits.changes_visuals_only",
                message="changes_visuals_only must be true"
            ))
        for hard_false in ["may_add_permissions", "may_add_tools", "may_add_network_access", "may_add_llm_access"]:
            if bl.get(hard_false) is not False:
                errors.append(ValidationIssue(
                    code="BEHAVIOR_VIOLATION",
                    field=f"behavior_limits.{hard_false}",
                    message=f"{hard_false} must be false"
                ))

    # Rights / license expiry
    rights = manifest.get("rights", {})
    if rights.get("expiry_date"):
        try:
            expiry = datetime.fromisoformat(rights["expiry_date"])
            if expiry < datetime.now(timezone.utc):
                errors.append(ValidationIssue(
                    code="LICENSE_EXPIRED",
                    field="rights.expiry_date",
                    message=f'License expired: {rights["expiry_date"]}'
                ))
        except ValueError:
            warnings.append(ValidationIssue(code="INVALID_DATE", field="rights.expiry_date", message="Could not parse expiry_date"))

    # Hash check
    integ = manifest.get("integrity", {})
    if integ:
        stored_hash = integ.get("package_hash", "").lstrip("sha256:")
        actual_hash = package_hash.lstrip("sha256:")
        if stored_hash and actual_hash and stored_hash != actual_hash:
            errors.append(ValidationIssue(
                code="HASH_MISMATCH",
                field="integrity.package_hash",
                message=f"Hash mismatch. Stored: {stored_hash[:12]}... Actual: {actual_hash[:12]}..."
            ))

    return ValidationResult(
        valid=len(errors) == 0,
        skin_id=manifest.get("skin_id", "unknown"),
        errors=errors,
        warnings=warnings,
        validated_at=now
    )

# ─────────────────────────────────────────────
# PACKAGE PROCESSING
# ─────────────────────────────────────────────

def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def extract_skin_package(raw_bytes: bytes, skin_id: str) -> Path:
    """Extract .orbskin zip to SKIN_STORE_DIR/<skin_id>/"""
    dest_dir = SKIN_STORE_DIR / skin_id
    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
        for name in zf.namelist():
            zf.extract(name, dest_dir)

    return dest_dir

def build_asset_url(skin_id: str, filename: str) -> str:
    """Build the URL the React renderer will use to fetch this asset."""
    # Served by the GET /skin/asset/{path} endpoint below
    return f"/api/skin/asset/{skin_id}/{filename}"

def build_bundle(manifest: dict, skin_id: str) -> dict:
    vis = manifest.get("visuals", {})

    animations = {
        anim: build_asset_url(skin_id, f"animations/{anim}")
        for anim in vis.get("animations", [])
    }
    sounds = {
        snd: build_asset_url(skin_id, f"sounds/{snd}")
        for snd in vis.get("sounds", [])
    }

    return {
        "skin_id": skin_id,
        "name": manifest.get("name", ""),
        "manifest": manifest,
        "urls": {
            "preview": build_asset_url(skin_id, vis.get("preview", "")),
            "body_asset": build_asset_url(skin_id, vis.get("body_asset", "")),
            "docked_icon": build_asset_url(skin_id, vis.get("docked_icon", "")),
            "animations": animations,
            "particle_profile": build_asset_url(skin_id, vis["particle_profile"]) if vis.get("particle_profile") else None,
            "sounds": sounds,
        },
        "theme_tokens": vis.get("theme_tokens", {}),
        "loaded_at": datetime.now(timezone.utc).isoformat(),
    }

# ─────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────

@router.post("/skin/load")
async def load_skin(file: UploadFile = File(...)):
    """Upload and activate a .orbskin package."""
    if not file.filename or not file.filename.endswith(".orbskin"):
        raise HTTPException(status_code=400, detail="File must have .orbskin extension")

    raw_bytes = await file.read()
    package_hash = compute_sha256(raw_bytes)

    # Read and parse manifest
    try:
        with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
            if "manifest.json" not in zf.namelist():
                raise HTTPException(status_code=400, detail="manifest.json not found in package")
            manifest_text = zf.read("manifest.json").decode("utf-8")
            manifest = json.loads(manifest_text)
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid zip/orbskin package")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid manifest JSON: {e}")

    # Validate
    validation = validate_manifest(manifest, ORB_TARGET, package_hash)
    if not validation.valid:
        return JSONResponse(
            status_code=422,
            content={
                "ok": False,
                "error": "Validation failed",
                "validation": validation.model_dump()
            }
        )

    skin_id = manifest["skin_id"]

    # Extract
    try:
        extract_skin_package(raw_bytes, skin_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {e}")

    # Build bundle
    bundle = build_bundle(manifest, skin_id)

    # Store rollback
    _state["rollback"] = _state["active"]
    _state["active"] = bundle

    return {"ok": True, "bundle": bundle, "validation": validation.model_dump()}


@router.post("/skin/rollback")
async def rollback_skin():
    """Rollback to the previous skin."""
    if not _state["rollback"]:
        raise HTTPException(status_code=404, detail="No rollback skin available")

    current = _state["active"]
    _state["active"] = _state["rollback"]
    _state["rollback"] = current

    return {"ok": True, "bundle": _state["active"]}


@router.get("/skin/active")
async def get_active_skin():
    """Get current active skin info."""
    if not _state["active"]:
        return {"active": None, "rollback_available": False}

    b = _state["active"]
    return {
        "active": {
            "skin_id": b["skin_id"],
            "name": b["name"],
            "loaded_at": b["loaded_at"],
        },
        "rollback_available": _state["rollback"] is not None
    }


@router.get("/skin/bundle")
async def get_active_bundle():
    """Get the full active skin bundle (for React renderer to initialize from)."""
    if not _state["active"]:
        return {"bundle": None}
    return {"bundle": _state["active"]}


@router.delete("/skin/clear")
async def clear_skin():
    """Remove the active skin. ORB returns to default appearance."""
    _state["rollback"] = _state["active"]
    _state["active"] = None
    return {"ok": True}


@router.get("/skin/asset/{skin_id}/{file_path:path}")
async def serve_skin_asset(skin_id: str, file_path: str):
    """Serve an extracted skin asset file."""
    # Security: sanitize paths to prevent traversal
    safe_id = "".join(c for c in skin_id if c.isalnum() or c in "-_")
    asset_path = SKIN_STORE_DIR / safe_id / file_path

    # Resolve and verify it stays inside the skin dir
    try:
        resolved = asset_path.resolve()
        store_resolved = SKIN_STORE_DIR.resolve()
        if not str(resolved).startswith(str(store_resolved)):
            raise HTTPException(status_code=403, detail="Access denied")
    except Exception:
        raise HTTPException(status_code=403, detail="Invalid path")

    if not resolved.exists():
        raise HTTPException(status_code=404, detail=f"Asset not found: {file_path}")

    return FileResponse(resolved)
