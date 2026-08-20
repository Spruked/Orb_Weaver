from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List


COMPILER_VERSION = "website-orb-vault-compiler/1.0.0"
COMMERCIAL_TYPES = {"product", "service", "plan", "fee"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _verified_evidence(document: Dict[str, Any], kinds: Iterable[str] | None = None) -> List[Dict[str, Any]]:
    allowed = set(kinds or [])
    results: List[Dict[str, Any]] = []
    for item in document.get("evidence", []):
        if item.get("verified") is not True:
            continue
        if allowed and item.get("evidence_type") not in allowed:
            continue
        results.append(item)
    return results


def _header(document: Dict[str, Any], schema: str) -> Dict[str, Any]:
    return {
        "schema": schema,
        "site_id": str(document["site_id"]),
        "domain": document["domain"],
        "generated_at": _now(),
        "compiler_version": COMPILER_VERSION,
    }


def _price(value: Any) -> Dict[str, Any] | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return {
            "amount": value,
            "currency": None,
            "display_text": None,
            "min_amount": None,
            "max_amount": None,
            "billing_period": None,
        }
    if isinstance(value, str):
        return {
            "amount": None,
            "currency": None,
            "display_text": value,
            "min_amount": None,
            "max_amount": None,
            "billing_period": None,
        }
    if isinstance(value, dict):
        return {
            "amount": value.get("amount"),
            "currency": value.get("currency"),
            "display_text": value.get("display_text") or value.get("text"),
            "min_amount": value.get("min_amount"),
            "max_amount": value.get("max_amount"),
            "billing_period": value.get("billing_period"),
        }
    return None


def compile_catalog(document: Dict[str, Any]) -> Dict[str, Any]:
    result = _header(document, "orb_weaver.website_orb.catalog.v1")
    entries: List[Dict[str, Any]] = []
    for item in _verified_evidence(document, COMMERCIAL_TYPES):
        payload = item.get("payload", {})
        name = payload.get("name") or payload.get("title")
        if not name:
            continue
        entries.append(
            {
                "entity_id": str(payload.get("entity_id") or item["evidence_id"]),
                "entity_type": item["evidence_type"],
                "name": str(name),
                "description": payload.get("description"),
                "sku": payload.get("sku"),
                "category": payload.get("category"),
                "price": _price(payload.get("price")),
                "availability": payload.get("availability"),
                "route": item.get("route", ""),
                "source_url": item["source_url"],
                "source_evidence_ids": [item["evidence_id"]],
                "pointer_target_id": item.get("pointer_target_id"),
                "verified": True,
                "confidence": float(item.get("confidence", 1.0)),
                "content_hash": item["content_hash"],
                "attributes": payload.get("attributes", {}),
            }
        )
    result["entries"] = entries
    return result


def compile_ontology(document: Dict[str, Any]) -> Dict[str, Any]:
    result = _header(document, "orb_weaver.website_orb.ontology.v1")
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []

    for item in _verified_evidence(document, COMMERCIAL_TYPES | {"business_fact", "contact"}):
        payload = item.get("payload", {})
        label = payload.get("name") or payload.get("title") or payload.get("label") or payload.get("value")
        if not label:
            continue
        node_id = str(payload.get("entity_id") or item["evidence_id"])
        nodes.append(
            {
                "node_id": node_id,
                "node_type": str(payload.get("node_type") or item["evidence_type"]),
                "label": str(label),
                "aliases": list(payload.get("aliases", [])),
                "route": item.get("route"),
                "source_url": item["source_url"],
                "source_evidence_ids": [item["evidence_id"]],
                "pointer_target_id": item.get("pointer_target_id"),
                "verified": True,
                "confidence": float(item.get("confidence", 1.0)),
                "content_hash": item["content_hash"],
                "attributes": payload.get("attributes", {}),
            }
        )
        for index, relation in enumerate(payload.get("relations", [])):
            if not isinstance(relation, dict) or not relation.get("relation") or not relation.get("to_node"):
                continue
            edges.append(
                {
                    "edge_id": str(relation.get("edge_id") or f"{node_id}:rel:{index}"),
                    "from_node": node_id,
                    "relation": str(relation["relation"]),
                    "to_node": str(relation["to_node"]),
                    "source_evidence_ids": [item["evidence_id"]],
                    "verified": True,
                    "confidence": float(item.get("confidence", 1.0)),
                }
            )

    result["nodes"] = nodes
    result["edges"] = edges
    return result


def compile_qa(document: Dict[str, Any]) -> Dict[str, Any]:
    result = _header(document, "orb_weaver.website_orb.qa.v1")
    entries: List[Dict[str, Any]] = []
    for item in _verified_evidence(document, {"faq"}):
        payload = item.get("payload", {})
        question = payload.get("question")
        answer = payload.get("answer")
        if not question or not answer:
            continue
        entries.append(
            {
                "qa_id": str(payload.get("qa_id") or item["evidence_id"]),
                "question": str(question),
                "answer": str(answer),
                "aliases": list(payload.get("aliases", [])),
                "route": item.get("route", ""),
                "source_url": item["source_url"],
                "source_evidence_ids": [item["evidence_id"]],
                "pointer_target_id": item.get("pointer_target_id"),
                "verified": True,
                "confidence": float(item.get("confidence", 1.0)),
                "content_hash": item["content_hash"],
            }
        )
    result["entries"] = entries
    return result


def compile_policies(document: Dict[str, Any]) -> Dict[str, Any]:
    result = _header(document, "orb_weaver.website_orb.policies.v1")
    rules: List[Dict[str, Any]] = []
    for item in _verified_evidence(document, {"policy"}):
        payload = item.get("payload", {})
        # Policies are not settled truth until the owner explicitly approves them.
        if payload.get("owner_approved") is not True:
            continue
        title = payload.get("title")
        text = payload.get("text")
        if not title or not text:
            continue
        rules.append(
            {
                "policy_id": str(payload.get("policy_id") or item["evidence_id"]),
                "category": str(payload.get("category") or "general"),
                "title": str(title),
                "text": str(text),
                "route": item.get("route", ""),
                "source_url": item["source_url"],
                "source_evidence_ids": [item["evidence_id"]],
                "effective_date": payload.get("effective_date"),
                "owner_approved": True,
                "verified": True,
                "content_hash": item["content_hash"],
            }
        )
    result["rules"] = rules
    return result


def compile_pointer_correspondence(document: Dict[str, Any]) -> Dict[str, Any]:
    result = _header(document, "orb_weaver.website_orb.pointer_correspondence.v1")
    records: List[Dict[str, Any]] = []
    for item in _verified_evidence(document):
        target_id = item.get("pointer_target_id")
        if not target_id:
            continue
        payload = item.get("payload", {})
        entity_id = payload.get("entity_id") or item["evidence_id"]
        allowed_actions = payload.get("allowed_actions") or ["point", "highlight", "scroll"]
        records.append(
            {
                "correspondence_id": str(payload.get("correspondence_id") or f"{entity_id}:{target_id}"),
                "entity_id": str(entity_id),
                "route": item.get("route", ""),
                "pointer_target_id": str(target_id),
                "source_url": item["source_url"],
                "selector": item.get("selector"),
                "semantic_label": payload.get("name") or payload.get("title") or payload.get("label"),
                "intent_aliases": list(payload.get("intent_aliases", [])),
                "allowed_actions": list(allowed_actions),
                "verified": True,
                "confidence": float(item.get("confidence", 1.0)),
                "content_hash": item["content_hash"],
            }
        )
    result["records"] = records
    return result


def compile_all(document: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {
        "catalog": compile_catalog(document),
        "ontology": compile_ontology(document),
        "qa": compile_qa(document),
        "policies": compile_policies(document),
        "pointer_correspondence": compile_pointer_correspondence(document),
    }


def write_build(document: Dict[str, Any], output_root: Path) -> Dict[str, str]:
    artifacts = compile_all(document)
    apriori = output_root / "A_Priori_Vault"
    compiled_orb = output_root / "compiled_orb"
    apriori.mkdir(parents=True, exist_ok=True)
    compiled_orb.mkdir(parents=True, exist_ok=True)

    written: Dict[str, str] = {}
    destinations = {
        "catalog": apriori / "catalog.json",
        "ontology": apriori / "ontology.json",
        "qa": apriori / "qa.json",
        "policies": apriori / "policies.json",
        "pointer_correspondence": compiled_orb / "pointer_correspondence.json",
    }
    for name, path in destinations.items():
        path.write_text(json.dumps(artifacts[name], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        written[name] = str(path)
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile owner-verified Website ORB vault artifacts from canonical Full Scan Evidence.")
    parser.add_argument("--input", required=True, help="Path to full_scan_evidence.json")
    parser.add_argument("--output", required=True, help="Manufacturing/current output directory")
    args = parser.parse_args()

    source = Path(args.input)
    output = Path(args.output)
    document = json.loads(source.read_text(encoding="utf-8"))
    if document.get("schema") != "orb_weaver.full_scan_evidence.v1":
        raise ValueError("Input must use orb_weaver.full_scan_evidence.v1")

    written = write_build(document, output)
    print(json.dumps({"compiler_version": COMPILER_VERSION, "written": written}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
