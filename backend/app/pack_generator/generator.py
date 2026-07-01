from __future__ import annotations

import json
import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict


def _safe_name(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "_", value.strip().lower())
    return cleaned.strip("._-") or "orb_site"


def generate_pack_file(scan_data: Dict, site_id: str, domain: str, tier: str, output_dir: Path | str) -> Dict:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.utcnow().isoformat()
    filename = f"{_safe_name(domain)}_{tier}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.orbpack"
    pack_path = output_root / filename
    manifest = {
        "schema": "orb_weaver.tpc_pack.v1",
        "site_id": site_id,
        "domain": domain,
        "tier": tier,
        "generated_at": generated_at,
        "source": "orb_weaver",
    }
    with zipfile.ZipFile(pack_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, indent=2, default=str))
        archive.writestr("scan_data.json", json.dumps(scan_data, indent=2, default=str))
    return {
        "filename": filename,
        "path": str(pack_path),
        "size_bytes": pack_path.stat().st_size,
        "generated_at": generated_at,
        "tier": tier,
        "domain": domain,
    }
