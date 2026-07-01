#!/usr/bin/env python3
"""
ORB SKIN PACKER — builds a .orbskin package from a source directory.

Usage:
  python pack.py --src ./my-skin-folder --out ./my-skin.orbskin
  python pack.py --src ./my-skin-folder  # outputs <skin_id>.orbskin

Source folder must contain:
  manifest.json        (with package_hash left blank — packer fills it in)
  preview.png
  body.png or body.glb
  docked-icon.svg
  animations/          (optional)
  particles/           (optional)
  sounds/              (optional)
  license.json         (optional)
"""

import argparse
import hashlib
import io
import json
import os
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

# ─────────────────────────────────────────────
# REQUIRED FILES
# ─────────────────────────────────────────────

REQUIRED_ROOT_FILES = ["manifest.json", "preview.png", "docked-icon.svg"]

# ─────────────────────────────────────────────
# PACK
# ─────────────────────────────────────────────

def pack(src_dir: Path, out_path: Path) -> None:
    src_dir = src_dir.resolve()
    if not src_dir.is_dir():
        die(f"Source directory not found: {src_dir}")

    # Validate required files exist
    for f in REQUIRED_ROOT_FILES:
        if not (src_dir / f).exists():
            die(f"Missing required file: {f}")

    # body asset — accept either .png or .glb
    body_png = src_dir / "body.png"
    body_glb = src_dir / "body.glb"
    if not body_png.exists() and not body_glb.exists():
        die("Missing body asset: body.png or body.glb required")

    # Load and parse manifest
    manifest_path = src_dir / "manifest.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    skin_id = manifest.get("skin_id")
    if not skin_id:
        die("manifest.json is missing skin_id")

    # Default out path to <skin_id>.orbskin if not specified
    if out_path is None:
        out_path = Path(f"{skin_id}.orbskin")

    # ── Step 1: Collect all files ──────────────────────────────────────────
    all_files: list[tuple[str, Path]] = []  # (archive_name, disk_path)

    for disk_path in src_dir.rglob("*"):
        if disk_path.is_dir():
            continue
        rel = disk_path.relative_to(src_dir)
        archive_name = rel.as_posix()
        if archive_name == "manifest.json":
            continue  # We'll write manifest last, after computing hash
        all_files.append((archive_name, disk_path))

    # ── Step 2: Build zip in memory (without manifest) to compute hash ─────
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for archive_name, disk_path in sorted(all_files):
            zf.write(disk_path, archive_name)

    # Hash the zip bytes (without manifest) — this is what the loader verifies
    asset_bytes = buf.getvalue()
    asset_hash = hashlib.sha256(asset_bytes).hexdigest()
    package_hash = f"sha256:{asset_hash}"

    # ── Step 3: Update manifest with hash and signed_at ────────────────────
    if "integrity" not in manifest:
        manifest["integrity"] = {}
    manifest["integrity"]["package_hash"] = package_hash
    manifest["integrity"]["manifest_hash"] = ""  # filled after manifest is serialized
    if not manifest["integrity"].get("signed_at"):
        manifest["integrity"]["signed_at"] = datetime.now(timezone.utc).isoformat()
    if not manifest["integrity"].get("publisher_signature"):
        manifest["integrity"]["publisher_signature"] = "unsigned"
    if not manifest["integrity"].get("runtime_min_version"):
        manifest["integrity"]["runtime_min_version"] = "1.0.0"

    # Manifest hash (of the manifest JSON itself, with package_hash already set)
    manifest_json = json.dumps(manifest, indent=2, ensure_ascii=False)
    manifest_hash = "sha256:" + hashlib.sha256(manifest_json.encode("utf-8")).hexdigest()
    manifest["integrity"]["manifest_hash"] = manifest_hash

    # Re-serialize with manifest_hash filled in
    manifest_json = json.dumps(manifest, indent=2, ensure_ascii=False)

    # ── Step 4: Build final zip with manifest included ─────────────────────
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # Write manifest first
        zf.writestr("manifest.json", manifest_json)
        # Write all assets
        for archive_name, disk_path in sorted(all_files):
            zf.write(disk_path, archive_name)

    print(f"✓ Packed: {out_path}")
    print(f"  skin_id:      {skin_id}")
    print(f"  name:         {manifest.get('name', '(unnamed)')}")
    print(f"  package_hash: {package_hash}")
    print(f"  size:         {out_path.stat().st_size:,} bytes")
    print(f"  files:        {len(all_files) + 1} (including manifest)")


# ─────────────────────────────────────────────
# VERIFY
# ─────────────────────────────────────────────

def verify(orbskin_path: Path) -> None:
    """Quick integrity check on a packed .orbskin file."""
    if not orbskin_path.exists():
        die(f"File not found: {orbskin_path}")

    raw = orbskin_path.read_bytes()

    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            names = zf.namelist()
            if "manifest.json" not in names:
                die("manifest.json not found in package")

            manifest_text = zf.read("manifest.json").decode("utf-8")
            manifest = json.loads(manifest_text)
    except zipfile.BadZipFile:
        die("File is not a valid zip/orbskin package")
    except json.JSONDecodeError as e:
        die(f"Invalid manifest JSON: {e}")

    integ = manifest.get("integrity", {})
    stored_hash = integ.get("package_hash", "")

    # Re-build asset zip to verify hash
    buf = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(raw)) as src_zf:
        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as dst_zf:
            for name in sorted(src_zf.namelist()):
                if name == "manifest.json":
                    continue
                dst_zf.writestr(name, src_zf.read(name))

    actual_hash = "sha256:" + hashlib.sha256(buf.getvalue()).hexdigest()

    stored_clean = stored_hash.lstrip("sha256:")
    actual_clean = actual_hash.lstrip("sha256:")

    if stored_clean == actual_clean:
        print(f"✓ Integrity OK: {orbskin_path.name}")
        print(f"  skin_id: {manifest.get('skin_id')}")
        print(f"  name:    {manifest.get('name')}")
        print(f"  hash:    {actual_hash}")
    else:
        print(f"✗ HASH MISMATCH: {orbskin_path.name}")
        print(f"  stored:  {stored_hash}")
        print(f"  actual:  {actual_hash}")
        sys.exit(1)


# ─────────────────────────────────────────────
# SCAFFOLD
# ─────────────────────────────────────────────

def scaffold(dest_dir: Path, skin_id: str, skin_name: str) -> None:
    """Create a starter skin folder with placeholder files."""
    import ulid as _ulid  # pip install python-ulid
    real_id = f"orbskin_{_ulid.ULID()}" if not skin_id.startswith("orbskin_") else skin_id

    dest_dir.mkdir(parents=True, exist_ok=True)
    (dest_dir / "animations").mkdir(exist_ok=True)
    (dest_dir / "particles").mkdir(exist_ok=True)
    (dest_dir / "sounds").mkdir(exist_ok=True)

    manifest = {
        "schema_version": "1.0",
        "skin_id": real_id,
        "name": skin_name,
        "version": "1.0.0",
        "description": f"A new ORB skin: {skin_name}",
        "creator": {
            "creator_id": "truemark_creator_YOUR_ID",
            "display_name": "Your Name",
            "verified": False
        },
        "classification": {
            "tier": "basic",
            "edition_type": "unlimited",
            "supported_orbs": ["website", "desktop"],
            "commercial_use": False
        },
        "visuals": {
            "preview": "preview.png",
            "body_asset": "body.png",
            "docked_icon": "docked-icon.svg",
            "animations": [],
            "theme_tokens": {
                "orb_primary_color": "#6C63FF",
                "orb_glow_color": "#A89BFF",
                "orb_shadow_color": "#1a1a2e"
            }
        },
        "behavior_limits": {
            "changes_visuals_only": True,
            "may_change_voice_style": False,
            "may_change_personality_language": False,
            "may_add_permissions": False,
            "may_add_tools": False,
            "may_add_network_access": False,
            "may_add_llm_access": False
        },
        "marketplace": {
            "price_type": "fixed",
            "base_price_usd": 0.88,
            "marketplace_fee_percent": 7,
            "creator_royalty_percent": 0
        },
        "rights": {
            "license_type": "personal",
            "transferable": False,
            "resellable": False,
            "max_active_orbs": 1
        },
        "collectible": {
            "minted": False,
            "provenance_record_id": f"tmr_{_ulid.ULID()}"
        },
        "integrity": {
            "package_hash": "",
            "manifest_hash": "",
            "publisher_signature": "unsigned",
            "signed_at": "",
            "runtime_min_version": "1.0.0"
        }
    }

    with open(dest_dir / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    # Placeholder assets
    (dest_dir / "preview.png").write_bytes(b"")
    (dest_dir / "body.png").write_bytes(b"")
    (dest_dir / "docked-icon.svg").write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><circle cx="16" cy="16" r="14" fill="#6C63FF"/></svg>'
    )

    print(f"✓ Scaffold created: {dest_dir}")
    print(f"  skin_id: {real_id}")
    print(f"  Add your assets, then run: python pack.py --src {dest_dir}")


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

def die(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="ORB Skin Packer")
    sub = parser.add_subparsers(dest="cmd")

    # pack
    p_pack = sub.add_parser("pack", help="Pack a skin folder into .orbskin")
    p_pack.add_argument("--src", required=True, help="Source skin folder")
    p_pack.add_argument("--out", default=None, help="Output .orbskin path")

    # verify
    p_verify = sub.add_parser("verify", help="Verify a .orbskin package")
    p_verify.add_argument("file", help=".orbskin file to verify")

    # scaffold
    p_scaffold = sub.add_parser("scaffold", help="Create a starter skin folder")
    p_scaffold.add_argument("--dest", required=True, help="Destination folder")
    p_scaffold.add_argument("--id", default="orbskin_NEW", help="skin_id")
    p_scaffold.add_argument("--name", default="My New Skin", help="Skin display name")

    args = parser.parse_args()

    if args.cmd == "pack":
        pack(Path(args.src), Path(args.out) if args.out else None)
    elif args.cmd == "verify":
        verify(Path(args.file))
    elif args.cmd == "scaffold":
        scaffold(Path(args.dest), args.id, args.name)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
