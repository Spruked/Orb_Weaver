from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Mapping, Optional

from .compile_vaults import COMPILER_VERSION, compile_all


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.manufacturing.dock_station_builder import build_customer_dock_station  # noqa: E402
from app.manufacturing.manifests import stable_manifest_hash, write_json  # noqa: E402
from app.manufacturing.validator import package_tree_hash, validate_required_paths  # noqa: E402
from app.orb.catalog_repository import CatalogRepository, create_catalog_database  # noqa: E402
from app.pack_generator.generator import generate_pack_file  # noqa: E402


MANUFACTURER_VERSION = "website-orb-manufacturer/1.0.0"
PAYLOAD_SCHEMA = "orb_weaver.website_orb_payload.v1"
RESULT_SCHEMA = "orb_weaver.website_orb_manufacturing_result.v1"
SCHEMA_ROOT = Path(__file__).resolve().parent / "schemas"
REQUIRED_PAYLOAD_FILES = (
    "payload/payload_manifest.json",
    "payload/site_config.json",
    "payload/catalog.db",
    "payload/site_world.json",
    "payload/pointers.json",
    "payload/pointer_correspondence.json",
    "payload/runtime_language.json",
    "payload/tool_cache.json",
    "payload/apriori/catalog.json",
    "payload/apriori/ontology.json",
    "payload/apriori/qa.json",
    "payload/apriori/policies.json",
    "manifests/verification_manifest.json",
    "manifests/storage_policy.json",
    "posteriori/verified_cases.json",
    "customer_memory/profile.json",
)
REQUIRED_DIRECTORIES = (
    "posteriori",
    "customer_memory",
    "memory",
    "knowledge_archive",
    "verified_outcomes",
    "indexes",
    "runtime",
    "cache",
    "audit",
    "manifests",
    "backups",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _safe_identifier(value: str, fallback: str) -> str:
    clean = re.sub(r"[^a-z0-9._-]+", "-", (value or "").strip().lower()).strip(".-")
    return (clean or fallback)[:80].rstrip(".-")


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def _load_document(value: Path | str | Mapping[str, Any]) -> Dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return json.loads(Path(value).read_text(encoding="utf-8"))


def _type_matches(value: Any, expected: str) -> bool:
    return {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "null": value is None,
    }.get(expected, True)


def validate_schema(document: Any, schema: Mapping[str, Any], path: str = "$") -> list[str]:
    failures: list[str] = []
    expected_types = schema.get("type")
    if expected_types:
        allowed = [expected_types] if isinstance(expected_types, str) else list(expected_types)
        if not any(_type_matches(document, expected) for expected in allowed):
            return [f"{path}: expected {'|'.join(allowed)}"]
    if "const" in schema and document != schema["const"]:
        failures.append(f"{path}: value does not match required constant")
    if "enum" in schema and document not in schema["enum"]:
        failures.append(f"{path}: value is not in the allowed set")
    if isinstance(document, str) and len(document) < int(schema.get("minLength", 0)):
        failures.append(f"{path}: string is too short")
    if isinstance(document, (int, float)) and not isinstance(document, bool):
        if "minimum" in schema and document < schema["minimum"]:
            failures.append(f"{path}: number is below minimum")
        if "maximum" in schema and document > schema["maximum"]:
            failures.append(f"{path}: number is above maximum")
    if isinstance(document, list):
        if len(document) < int(schema.get("minItems", 0)):
            failures.append(f"{path}: array has too few items")
        item_schema = schema.get("items")
        if item_schema:
            for index, item in enumerate(document):
                failures.extend(validate_schema(item, item_schema, f"{path}[{index}]"))
    if isinstance(document, dict):
        for key in schema.get("required", []):
            if key not in document:
                failures.append(f"{path}.{key}: required value is missing")
        properties = schema.get("properties") or {}
        for key, value in document.items():
            if key in properties:
                failures.extend(validate_schema(value, properties[key], f"{path}.{key}"))
            elif schema.get("additionalProperties") is False:
                failures.append(f"{path}.{key}: additional property is not allowed")
    return failures


def _validate_named_schema(document: Dict[str, Any], filename: str) -> list[str]:
    schema = json.loads((SCHEMA_ROOT / filename).read_text(encoding="utf-8"))
    return validate_schema(document, schema)


def _compile_site_world(evidence: Dict[str, Any], source_context: Dict[str, Any]) -> Dict[str, Any]:
    existing = source_context.get("site_world") or source_context.get("latest_context") or {}
    pages = evidence.get("pages") or []
    route_hints = dict(existing.get("route_hints") or {})
    for page in pages:
        if page.get("route"):
            route_hints.setdefault(str(page.get("title") or page["route"]), page["route"])
    key_facts = list(existing.get("key_facts") or [])
    for item in evidence.get("evidence") or []:
        if item.get("verified") is True and item.get("evidence_type") == "business_fact":
            payload = item.get("payload") or {}
            value = payload.get("value") or payload.get("text") or payload.get("label")
            if value:
                key_facts.append(str(value))
    return {
        "schema": "orb_weaver.website_orb_site_world.v1",
        "site_id": str(evidence["site_id"]),
        "domain": evidence["domain"],
        "site_name": existing.get("site_name") or existing.get("brand") or evidence["domain"],
        "base_url": existing.get("base_url") or f"https://{evidence['domain']}",
        "site_summary": existing.get("site_summary"),
        "source": "manufactured_verified_evidence",
        "source_scan_id": evidence["scan_id"],
        "generated_at": _now(),
        "pages": pages,
        "route_hints": route_hints,
        "key_facts": list(dict.fromkeys(key_facts)),
        "primary_user_tasks": existing.get("primary_user_tasks") or [],
        "visitor_tools": existing.get("visitor_tools") or [],
        "knowledge_chunks": existing.get("knowledge_chunks") or {"chunks": []},
        "answer_boundaries": existing.get("answer_boundaries") or [],
    }


def _compile_pointers(evidence: Dict[str, Any], source_context: Dict[str, Any]) -> Dict[str, Any]:
    existing = source_context.get("pointer_plot_map") or source_context.get("pointers") or {}
    if existing.get("records"):
        return {**existing, "site_id": str(evidence["site_id"]), "domain": evidence["domain"]}
    records = []
    for item in evidence.get("evidence") or []:
        target_id = item.get("pointer_target_id")
        if not target_id or item.get("verified") is not True:
            continue
        payload = item.get("payload") or {}
        records.append({
            "target_id": str(target_id),
            "page_route": item.get("route") or "",
            "target_type": payload.get("target_type") or item.get("evidence_type") or "content",
            "meaning": payload.get("name") or payload.get("title") or payload.get("label") or str(target_id),
            "intent_aliases": payload.get("intent_aliases") or payload.get("aliases") or [],
            "semantic_locator": item.get("selector"),
            "confidence": float(item.get("confidence", 1.0)),
            "confidence_class": "VERIFIED",
            "pointer_health": "OWNER_VERIFIED",
            "runtime_policy": {"may_point": True, "requires_live_verification": True},
            "content_fingerprint": item["content_hash"],
        })
    return {
        "schema": "orb_weaver.pointer_plot_map.v1",
        "site_id": str(evidence["site_id"]),
        "domain": evidence["domain"],
        "generated_at": _now(),
        "records": records,
    }


def _compile_runtime_language(catalog: Dict[str, Any], qa: Dict[str, Any]) -> Dict[str, Any]:
    phrases = []
    for entry in catalog.get("entries") or []:
        phrases.append({"canonical": entry["name"], "aliases": entry.get("attributes", {}).get("aliases", [])})
    for entry in qa.get("entries") or []:
        phrases.append({"canonical": entry["question"], "aliases": entry.get("aliases") or []})
    return {"schema": "orb_weaver.website_orb_runtime_language.v1", "generated_at": _now(), "phrases": phrases}


def _compile_tool_cache(catalog: Dict[str, Any], qa: Dict[str, Any], source_context: Dict[str, Any]) -> Dict[str, Any]:
    existing = source_context.get("tool_cache") or {}
    entries = list(existing.get("entries") or [])
    entries.extend({
        "id": f"qa:{entry['qa_id']}",
        "intents": [entry["question"], *(entry.get("aliases") or [])],
        "spoken_output": entry["answer"],
        "evidence_ids": entry["source_evidence_ids"],
        "route": entry.get("route"),
    } for entry in qa.get("entries") or [])
    return {"schema": "orb_weaver.website_orb_tool_cache.v1", "generated_at": _now(), "entries": entries}


def _default_site_config(evidence: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    config = {
        "schema": "orb_weaver.website_orb_site_config.v1",
        "site_id": str(evidence["site_id"]),
        "domain": evidence["domain"],
        "base_url": f"https://{evidence['domain']}",
        "orb_name": "Weaver",
        "voice": {"provider": "kokoro", "voice": "am_echo", "format": "wav", "sample_rate_hz": 24000},
        "providers": {
            "routing_mode": "local_only",
            "primary": {"provider": "local_openai_compatible", "endpoint_ref": "LOCAL_LLM_URL", "model_ref": "LOCAL_LLM_MODEL"},
            "fallback": {"enabled": False},
            "credential_policy": "server_side_references_only",
        },
        "runtime_lanes": ["control", "catalog", "apriori", "posteriori", "site_world", "local_model", "external_provider", "articulation"],
        "storage": {"single_vault": True, "quota_bytes": 5368709120, "warning_percent": 80, "hard_stop_percent": 100},
        "behavior": {"rest_after_inactivity_seconds": 300, "live_target_verification_required": True, "browser_speech_synthesis": False},
    }
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(config.get(key), dict):
            config[key] = {**config[key], **value}
        else:
            config[key] = value
    return config


def _verification_manifest(
    evidence: Dict[str, Any],
    build_id: str,
    artifacts: Dict[str, Path],
    owner_verification: Dict[str, Any],
) -> Dict[str, Any]:
    approved = set(owner_verification.get("approved_artifacts") or [])
    rejected = set(owner_verification.get("rejected_artifacts") or [])
    approved_at = owner_verification.get("approved_at") or (_now() if approved else None)
    records = []
    if "*" in approved:
        approved = set(artifacts)
    for name, path in sorted(artifacts.items()):
        status = "rejected" if name in rejected else "approved" if name in approved else "pending"
        records.append({
            "artifact": name,
            "content_hash": _sha256(path),
            "status": status,
            "approved_at": approved_at if status == "approved" else None,
            "notes": None,
        })
    blocked = []
    pending = [item["artifact"] for item in records if item["status"] != "approved"]
    if pending:
        blocked.append("owner_verification_incomplete:" + ",".join(pending))
    return {
        "schema": "orb_weaver.website_orb.verification_manifest.v1",
        "site_id": str(evidence["site_id"]),
        "domain": evidence["domain"],
        "build_id": build_id,
        "generated_at": _now(),
        "owner": owner_verification.get("owner"),
        "artifacts": records,
        "shipping_gate": {
            "all_required_artifacts_approved": not pending,
            "package_allowed": not pending,
            "blocked_reasons": blocked,
        },
    }


def _initialize_vault(vault_root: Path, evidence: Dict[str, Any]) -> None:
    for relative in REQUIRED_DIRECTORIES:
        (vault_root / relative).mkdir(parents=True, exist_ok=True)
    _write_json(vault_root / "posteriori" / "verified_cases.json", {
        "schema": "orb_weaver.website_orb_verified_cases.v1",
        "site_id": str(evidence["site_id"]),
        "domain": evidence["domain"],
        "generated_at": _now(),
        "cases": [],
    })
    (vault_root / "posteriori" / "interactions.jsonl").write_text("", encoding="utf-8")
    _write_json(vault_root / "customer_memory" / "profile.json", {
        "schema": "orb_weaver.customer_memory.v1", "site_id": str(evidence["site_id"]), "items": []
    })
    _write_json(vault_root / "manifests" / "storage_policy.json", {
        "schema": "orb_weaver.storage_policy.v1",
        "single_persistent_vault": True,
        "quota_bytes": 5368709120,
        "warning_percent": 80,
        "forbidden_payload_names": [".git", ".env", "node_modules", "__pycache__", "secrets"],
    })


def validate_delivery_readiness(
    *,
    vault_root: Path,
    compiled: Dict[str, Dict[str, Any]],
    verification_manifest: Dict[str, Any],
    dock_result: Optional[Dict[str, Any]],
    package_result: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    failures: list[str] = []
    required = [{"path": path, "type": "file"} for path in REQUIRED_PAYLOAD_FILES]
    required.extend({"path": path, "type": "directory"} for path in REQUIRED_DIRECTORIES)
    path_validation = validate_required_paths(vault_root, required)
    failures.extend(f"payload:{item}" for item in path_validation.get("missing", []))
    failures.extend(f"forbidden:{item}" for item in path_validation.get("forbidden_payloads", []))
    failures.extend(f"symlink:{item}" for item in path_validation.get("symlinks", []))

    schema_files = {
        "catalog": "catalog.v1.json",
        "ontology": "ontology.v1.json",
        "qa": "qa.v1.json",
        "policies": "policies.v1.json",
        "pointer_correspondence": "pointer_correspondence.v1.json",
    }
    schema_results: Dict[str, list[str]] = {}
    for name, filename in schema_files.items():
        schema_results[name] = _validate_named_schema(compiled[name], filename)
        failures.extend(f"schema:{name}:{failure}" for failure in schema_results[name])
    verification_failures = _validate_named_schema(verification_manifest, "verification_manifest.v1.json")
    failures.extend(f"schema:verification_manifest:{failure}" for failure in verification_failures)
    runtime_schema_files = {
        "payload_manifest": "payload_manifest.v1.json",
        "site_config": "site_config.v1.json",
        "site_world": "site_world.v1.json",
        "pointers": "pointers.v1.json",
        "runtime_language": "runtime_language.v1.json",
        "tool_cache": "tool_cache.v1.json",
    }
    runtime_schema_results: Dict[str, list[str]] = {}
    for name, filename in runtime_schema_files.items():
        try:
            document = json.loads((vault_root / "payload" / f"{name}.json").read_text(encoding="utf-8"))
            runtime_schema_results[name] = _validate_named_schema(document, filename)
        except (OSError, json.JSONDecodeError) as exc:
            runtime_schema_results[name] = [f"$: unreadable payload ({exc.__class__.__name__})"]
        failures.extend(f"schema:{name}:{failure}" for failure in runtime_schema_results[name])
    if not verification_manifest.get("shipping_gate", {}).get("package_allowed"):
        failures.extend(verification_manifest.get("shipping_gate", {}).get("blocked_reasons") or ["owner_verification_incomplete"])

    catalog_validation = CatalogRepository(vault_root / "payload" / "catalog.db").validate()
    if not catalog_validation["valid"]:
        failures.append(str(catalog_validation["reason"]))
    for filename in ("site_world.json", "pointers.json", "pointer_correspondence.json", "site_config.json"):
        try:
            json.loads((vault_root / "payload" / filename).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            failures.append(f"payload_unreadable:{filename}")
    posteriori_path = vault_root / "posteriori" / "verified_cases.json"
    posteriori = json.loads(posteriori_path.read_text(encoding="utf-8")) if posteriori_path.is_file() else {}
    if posteriori.get("cases") != [] or (vault_root / "posteriori" / "interactions.jsonl").read_text(encoding="utf-8") != "":
        failures.append("posteriori_not_clean")
    if not dock_result or not dock_result.get("passed"):
        failures.append("dock_station_validation_failed")
    elif dock_result.get("payload_tree_hash") != package_tree_hash(vault_root)["tree_hash"]:
        failures.append("dock_station_payload_hash_mismatch")
    if package_result is not None:
        package_path = Path(package_result.get("path") or "")
        if not package_path.is_file() or package_result.get("sha256") != _sha256(package_path):
            failures.append("orbpack_integrity_failed")
        else:
            with zipfile.ZipFile(package_path) as archive:
                vault_roots = {name.split("/vault_system/", 1)[0] for name in archive.namelist() if "/vault_system/" in name}
                if len(vault_roots) != 1:
                    failures.append("orbpack_single_vault_contract_failed")
    return {
        "passed": not failures,
        "delivery_ready": not failures,
        "failures": failures,
        "path_validation": path_validation,
        "schema_validation": {
            **schema_results,
            **runtime_schema_results,
            "verification_manifest": verification_failures,
        },
        "catalog_validation": catalog_validation,
        "dock_station_validation": dock_result,
        "package_validation": package_result,
    }


def _set_dock_delivery_state(dock_station: Path, ready: bool, summary: Dict[str, Any]) -> Dict[str, Any]:
    manifest_path = dock_station / "deployment" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["manufacturing_pass"]["delivery_ready"] = ready
    manifest["manufacturing_pass"]["readiness_failures"] = summary.get("failure_reasons") or []
    manifest["paths"]["manufacturing_result"] = "deployment/manufacturing-result.json"
    manifest.pop("manifest_hash", None)
    manifest["manifest_hash"] = stable_manifest_hash(manifest)
    write_json(manifest_path, manifest)
    write_json(dock_station / "deployment" / "manufacturing-result.json", summary)
    return manifest


def manufacture_website_orb(
    *,
    evidence: Path | str | Mapping[str, Any],
    output_root: Path | str,
    owner_verification: Optional[Dict[str, Any]] = None,
    site_config: Optional[Dict[str, Any]] = None,
    source_context: Optional[Dict[str, Any]] = None,
    build_id: Optional[str] = None,
    tier: str = "website-orb",
    ephemeral: bool = False,
    status_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    def report_status(status: str, **details: Any) -> None:
        if status_callback:
            status_callback(status, details)

    report_status("preparing")
    document = _load_document(evidence)
    evidence_failures = _validate_named_schema(document, "full_scan_evidence.v1.json")
    if evidence_failures:
        result = {
            "schema": RESULT_SCHEMA,
            "status": "failed",
            "delivery_ready": False,
            "failure_reasons": [f"evidence:{failure}" for failure in evidence_failures],
        }
        report_status("failed", delivery_ready=False, failure_reasons=result["failure_reasons"])
        return result

    resolved_build_id = _safe_identifier(build_id or f"build-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}", "build")
    report_status("compiling", build_id=resolved_build_id)
    customer_id = _safe_identifier(document["domain"], "customer")
    root = Path(output_root).expanduser().resolve()
    build_root = root / resolved_build_id
    if build_root.exists():
        raise FileExistsError(f"Manufacturing build already exists: {build_root}")
    vault_root = build_root / "vault_system"
    payload_root = vault_root / "payload"
    payload_root.mkdir(parents=True)
    _initialize_vault(vault_root, document)

    compiled = compile_all(document)
    context = dict(source_context or {})
    site_world = _compile_site_world(document, context)
    pointers = _compile_pointers(document, context)
    runtime_language = _compile_runtime_language(compiled["catalog"], compiled["qa"])
    tool_cache = _compile_tool_cache(compiled["catalog"], compiled["qa"], context)
    resolved_site_config = _default_site_config(document, dict(site_config or {}))

    artifact_documents = {
        "site_config.json": resolved_site_config,
        "site_world.json": site_world,
        "pointers.json": pointers,
        "pointer_correspondence.json": compiled["pointer_correspondence"],
        "runtime_language.json": runtime_language,
        "tool_cache.json": tool_cache,
        "apriori/catalog.json": compiled["catalog"],
        "apriori/ontology.json": compiled["ontology"],
        "apriori/qa.json": compiled["qa"],
        "apriori/policies.json": compiled["policies"],
    }
    artifacts: Dict[str, Path] = {}
    for name, payload in artifact_documents.items():
        path = payload_root / name
        _write_json(path, payload)
        artifacts[name] = path
    catalog_path = payload_root / "catalog.db"
    create_catalog_database(catalog_path, compiled["catalog"].get("entries") or [])
    artifacts["catalog.db"] = catalog_path
    evidence_path = vault_root / "audit" / "full_scan_evidence.json"
    _write_json(evidence_path, document)

    verification = _verification_manifest(document, resolved_build_id, artifacts, dict(owner_verification or {}))
    verification_path = vault_root / "manifests" / "verification_manifest.json"
    _write_json(verification_path, verification)
    payload_manifest = {
        "schema": PAYLOAD_SCHEMA,
        "manufacturer_version": MANUFACTURER_VERSION,
        "compiler_version": COMPILER_VERSION,
        "build_id": resolved_build_id,
        "site_id": str(document["site_id"]),
        "domain": document["domain"],
        "generated_at": _now(),
        "source": {"scan_id": document["scan_id"], "scanner_version": document["scanner_version"], "captured_at": document["captured_at"]},
        "artifacts": {name: {"path": f"payload/{name}", "sha256": _sha256(path)} for name, path in artifacts.items()},
        "verification": {"path": "manifests/verification_manifest.json", "sha256": _sha256(verification_path), "approved": verification["shipping_gate"]["package_allowed"]},
        "required_runtime_capabilities": resolved_site_config["runtime_lanes"],
    }
    _write_json(payload_root / "payload_manifest.json", payload_manifest)

    report_status("awaiting_verification" if not verification["shipping_gate"]["package_allowed"] else "assembling", build_id=resolved_build_id)
    dock_result = build_customer_dock_station(
        customer_id=customer_id,
        deployment_id=resolved_build_id,
        builds_root=build_root / "assembly",
        payload_root=vault_root,
        manufacturing_metadata={
            "build_id": resolved_build_id,
            "site_id": str(document["site_id"]),
            "domain": document["domain"],
            "payload_manifest_hash": _sha256(payload_root / "payload_manifest.json"),
        },
    )
    report_status("validating", build_id=resolved_build_id)
    preliminary = validate_delivery_readiness(
        vault_root=vault_root,
        compiled=compiled,
        verification_manifest=verification,
        dock_result=dock_result,
    )
    dock_station = Path(dock_result["dock_station"]) if dock_result.get("dock_station") else None
    summary = {
        "schema": RESULT_SCHEMA,
        "build_id": resolved_build_id,
        "site_id": str(document["site_id"]),
        "domain": document["domain"],
        "source_evidence_version": document["scanner_version"],
        "source_scan_id": document["scan_id"],
        "generated_at": _now(),
        "delivery_ready": False,
        "failure_reasons": preliminary["failures"],
        "payload_manifest": "app/orb/template/runtime/vault_system/payload/payload_manifest.json",
        "verification_manifest": "app/orb/template/runtime/vault_system/manifests/verification_manifest.json",
    }
    if dock_station:
        _set_dock_delivery_state(dock_station, False, summary)

    package_result = None
    if preliminary["passed"] and dock_station:
        package_result = generate_pack_file(
            scan_data=document,
            site_id=str(document["site_id"]),
            domain=document["domain"],
            tier=tier,
            output_dir=build_root / "packages",
            assembled_dock_station=dock_station,
            manufacturing_result=summary,
            ephemeral=ephemeral,
        )
    final_validation = validate_delivery_readiness(
        vault_root=vault_root,
        compiled=compiled,
        verification_manifest=verification,
        dock_result=dock_result,
        package_result=package_result,
    ) if package_result else preliminary
    delivery_ready = bool(final_validation["passed"] and package_result)
    summary.update({"delivery_ready": delivery_ready, "failure_reasons": final_validation["failures"]})
    if dock_station:
        final_manifest = _set_dock_delivery_state(dock_station, delivery_ready, summary)
        if delivery_ready:
            package_result = generate_pack_file(
                scan_data=document,
                site_id=str(document["site_id"]),
                domain=document["domain"],
                tier=tier,
                output_dir=build_root / "packages",
                assembled_dock_station=dock_station,
                manufacturing_result=summary,
                ephemeral=ephemeral,
            )
            final_validation = validate_delivery_readiness(
                vault_root=vault_root,
                compiled=compiled,
                verification_manifest=verification,
                dock_result=dock_result,
                package_result=package_result,
            )
            delivery_ready = final_validation["passed"]
            summary.update({"delivery_ready": delivery_ready, "failure_reasons": final_validation["failures"]})
        else:
            final_manifest = _set_dock_delivery_state(dock_station, False, summary)
    else:
        final_manifest = None

    result = {
        **summary,
        "status": "ready" if delivery_ready else "awaiting_verification" if any("owner_verification" in reason for reason in summary["failure_reasons"]) else "failed",
        "generated_artifacts": {name: str(path) for name, path in artifacts.items()},
        "verification_status": verification["shipping_gate"],
        "package_paths": {
            "build_root": str(build_root),
            "vault_root": str(vault_root),
            "dock_station": str(dock_station) if dock_station else None,
            "orbpack": package_result.get("path") if package_result else None,
        },
        "hashes": {
            "source_evidence": _json_hash(document),
            "payload_tree": package_tree_hash(vault_root)["tree_hash"],
            "dock_template_tree": dock_result.get("template_tree_hash") if dock_result else None,
            "dock_package_tree": package_tree_hash(dock_station)["tree_hash"] if dock_station else None,
            "dock_manifest": final_manifest.get("manifest_hash") if final_manifest else None,
            "orbpack": package_result.get("sha256") if package_result else None,
        },
        "validation_results": final_validation,
    }
    _write_json(build_root / "manufacturing-result.json", result)
    report_status(result["status"], build_id=resolved_build_id, delivery_ready=delivery_ready, failure_reasons=result["failure_reasons"])
    return result
