"""Validate the installed customer payload before loading any knowledge."""
from __future__ import annotations

import hashlib
import json
from .storage import canonical_vault_root, require_vault_path

REQUIRED = {"site_config.json", "site_world.json", "pointers.json", "catalog.db",
            "pointer_correspondence.json", "runtime_language.json", "tool_cache.json",
            "lexical_index.json", "knowledge_chunks.json", "retrieval_index.json", "permissions.json",
            "apriori/catalog.json", "apriori/ontology.json", "apriori/site_skg.json",
            "apriori/qa.json", "apriori/policies.json", "apriori/elimination_graph.json"}


def validate_payload() -> dict:
    root = canonical_vault_root()
    manifest = json.loads((root / "payload/payload_manifest.json").read_text())
    if not REQUIRED.issubset(manifest.get("artifacts", {})):
        raise RuntimeError("Required customer artifacts are missing from the manifest")

    def checked(relative: str, expected: str) -> bytes:
        path = require_vault_path(root / relative, "manifest artifact")
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise RuntimeError(f"Customer artifact hash mismatch: {relative}")
        return data

    verification = manifest["verification"]
    checked(manifest["source"]["evidence_path"], manifest["source"]["evidence_sha256"])
    approval = json.loads(checked(verification["path"], verification["sha256"]))
    for key in ("site_id", "domain", "build_id"):
        if str(approval.get(key)) != str(manifest[key]):
            raise RuntimeError("Approval belongs to another customer build")
    if verification.get("approved") is not True or approval["shipping_gate"].get("package_allowed") is not True:
        raise RuntimeError("Customer payload has not been approved")
    approved = {item["artifact"]: item for item in approval["artifacts"]}
    for name, item in manifest["artifacts"].items():
        if item["path"] != "payload/" + name:
            raise RuntimeError("Unexpected artifact path")
        owner_record = approved.get(name, {})
        if owner_record.get("status") != "approved" or owner_record.get("content_hash") != item["sha256"]:
            raise RuntimeError(f"Customer approval does not match artifact: {name}")
        raw = checked(item["path"], item["sha256"])
        if name.endswith(".json"):
            data = json.loads(raw)
            for key, expected in (("site_id", str(manifest["site_id"])), ("domain", manifest["domain"]),
                                  ("source_scan_id", str(manifest["source"]["scan_id"]))):
                if key in data and str(data[key]) != expected:
                    raise RuntimeError(f"Foreign or stale artifact: {name}:{key}")
    return manifest
