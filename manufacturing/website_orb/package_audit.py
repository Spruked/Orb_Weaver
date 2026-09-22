"""Negative checks on the actual delivered ZIP, not just compiler output."""
from __future__ import annotations
import hashlib
import json
import zipfile

FACTORY_MARKERS = ("orbweaver.spruked.com", "/founding-beta", "/investor-contact",
                   "basic visitor orb", "$488.88", "ask weaver",
                   "i know where i am on orb weaver", "target_5e65a33ee51e")
FORBIDDEN_PATHS = ("compiled_orb/", "dock-station/", "node_modules/", "__pycache__/",
                   "frontend/public/voice/", "orb_vault_skg/vaults/")


def audit_package(path, evidence: dict, config: dict) -> dict:
    authorized_input = json.dumps([evidence, config], ensure_ascii=False).casefold()
    findings, observed, checked = [], [], 0
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            if any(part in name for part in FORBIDDEN_PATHS):
                findings.append({"path": name, "reason": "forbidden_template_or_factory_tree"})
            if name.endswith("/"):
                continue
            checked += 1
            text = archive.read(name).decode("utf-8", errors="replace").casefold()
            for marker in FACTORY_MARKERS:
                if marker not in text:
                    continue
                # Only scan-derived data may legitimately mention the factory.
                attributable = "/vault_system/" in name and marker in authorized_input
                record = {"path": name, "marker": marker, "present_in_customer_input": attributable}
                observed.append(record)
                if not attributable:
                    findings.append(record)
        names = archive.namelist()
        for required in ("manifest.json", "website-orb/run.py", "website-orb/INSTALL.md", "website-orb/assets/widget.js"):
            if required not in names:
                findings.append({"path": required, "reason": "missing_install_file"})
    return {"schema": "website_orb.package_isolation_audit.v1", "passed": not findings,
            "files_checked": checked, "marker_set": list(FACTORY_MARKERS), "observed": observed,
            "findings": findings, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "scope": "Known factory markers and excluded trees; shared schema/code identifiers are permitted."}
