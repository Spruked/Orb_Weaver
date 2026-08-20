"""
orb/vault/a_priori/loader.py
Loads A Priori vault data from Orb Weaver output.
Reads: site.skg, catalog.json, ontology.json, policy.json, qa.json
"""

from __future__ import annotations
from typing import Dict, List, Any, Optional
import json
from pathlib import Path

from ..shared.types import (
    CatalogEntry, Entity, Relation, EntityType, RelationType,
    QACorrespondence, PolicyRule, VaultTimestamp, IntentType, Confidence
)

from .catalog_cognitive import CatalogCognitiveState
from .ontology_cognitive import OntologyCognitiveState
from .qa_cognitive import QACognitiveState


class PrioriLoader:
    """
    Loads settled truth from Orb Weaver compiled output.
    Site-agnostic: discovers files at runtime.
    """

    def __init__(self, weaver_output_dir: str):
        self.output_dir = Path(weaver_output_dir)

    def load_all(self) -> Dict[str, Any]:
        return {
            "catalog": self.load_catalog(),
            "ontology": self.load_ontology(),
            "qa": self.load_qa(),
            "policies": self.load_policies(),
        }

    def load_catalog(self) -> CatalogCognitiveState:
        state = CatalogCognitiveState()
        catalog_file = self.output_dir / "catalog.json"
        if not catalog_file.exists():
            for alt in ["products.json", "inventory.json", "site_catalog.json"]:
                alt_path = self.output_dir / alt
                if alt_path.exists():
                    catalog_file = alt_path
                    break

        if catalog_file.exists():
            with open(catalog_file, "r") as f:
                data = json.load(f)
            for item in data.get("entries", data if isinstance(data, list) else []):
                price = item.get("price") if isinstance(item.get("price"), dict) else {}
                attributes = item.get("attributes") if isinstance(item.get("attributes"), dict) else {}
                entity_type = str(item.get("entity_type") or "").lower()
                entry = CatalogEntry(
                    entry_id=item.get("entity_id", item.get("product_id", item.get("id", f"cat_{hash(str(item))}"))),
                    entry_type=EntityType.SERVICE if entity_type == "service" else EntityType.PRODUCT,
                    name=item.get("name", "Unknown"),
                    sku=item.get("sku"),
                    current_price=item.get("current_price", price.get("amount")),
                    sale_price=item.get("sale_price", attributes.get("sale_price")),
                    currency=item.get("currency", price.get("currency") or "USD"),
                    variant=item.get("variant"),
                    availability=item.get("availability"),
                    specifications=item.get("specifications", attributes),
                    attributes={**attributes, "category": item.get("category") or attributes.get("category", "uncategorized")},
                    source_url=item.get("source_url", ""),
                    source_element=item.get("source_element", ""),
                    crawl_version=item.get("crawl_version", ""),
                    owner_verified=item.get("owner_verified", item.get("verified", False)),
                )
                state.add_entry(entry)
        return state

    def load_ontology(self) -> OntologyCognitiveState:
        state = OntologyCognitiveState()
        ontology_file = self.output_dir / "ontology.json"
        if not ontology_file.exists():
            ontology_file = self.output_dir / "site.skg"

        if ontology_file.exists():
            with open(ontology_file, "r") as f:
                data = json.load(f)
            for e_data in data.get("entities", data.get("nodes", [])):
                raw_type = str(e_data.get("type", e_data.get("node_type", "CATEGORY"))).upper()
                entity_type = EntityType.__members__.get(raw_type, EntityType.CATEGORY)
                entity = Entity(
                    entity_id=e_data.get("id", e_data.get("entity_id", e_data.get("node_id", ""))),
                    entity_type=entity_type,
                    canonical_name=e_data.get("name", e_data.get("canonical_name", e_data.get("label", ""))),
                    aliases=e_data.get("aliases", []),
                    attributes=e_data.get("attributes", {}),
                    source_url=e_data.get("source_url", ""),
                )
                state.add_entity(entity)
            for r_data in data.get("relations", data.get("edges", [])):
                raw_relation = str(r_data.get("type", r_data.get("relation", "BELONGS_TO"))).upper()
                relation_type = RelationType.__members__.get(raw_relation, RelationType.BELONGS_TO)
                relation = Relation(
                    relation_id=r_data.get("id", r_data.get("relation_id", r_data.get("edge_id", ""))),
                    relation_type=relation_type,
                    source_id=r_data.get("source", r_data.get("source_id", r_data.get("from_node", ""))),
                    target_id=r_data.get("target", r_data.get("target_id", r_data.get("to_node", ""))),
                    weight=r_data.get("weight", 1.0),
                    attributes=r_data.get("attributes", {}),
                )
                state.add_relation(relation)
        return state

    def load_qa(self) -> QACognitiveState:
        state = QACognitiveState()
        qa_file = self.output_dir / "qa.json"
        if not qa_file.exists():
            qa_file = self.output_dir / "correspondences.json"

        if qa_file.exists():
            with open(qa_file, "r") as f:
                data = json.load(f)
            for q_data in data.get("qa_pairs", data.get("entries", data if isinstance(data, list) else [])):
                questions = q_data.get("questions", q_data.get("question_patterns"))
                if not questions and q_data.get("question"):
                    questions = [q_data["question"], *(q_data.get("aliases") or [])]
                raw_intent = str(q_data.get("intent", "GENERAL")).upper()
                qa = QACorrespondence(
                    qa_id=q_data.get("id", q_data.get("qa_id", "")),
                    question_patterns=questions or [],
                    answer_template=q_data.get("answer", q_data.get("answer_template", "")),
                    answer_variables=q_data.get("variables", []),
                    intent=IntentType.__members__.get(raw_intent, IntentType.GENERAL),
                    source=q_data.get("source", "owner"),
                )
                state.add_qa(qa)
        return state

    def load_policies(self) -> List[PolicyRule]:
        policies = []
        policy_file = self.output_dir / "policies.json"
        if policy_file.exists():
            with open(policy_file, "r") as f:
                data = json.load(f)
            for p_data in data.get("policies", data.get("rules", data if isinstance(data, list) else [])):
                policy = PolicyRule(
                    rule_id=p_data.get("id", p_data.get("rule_id", p_data.get("policy_id", ""))),
                    category=p_data.get("category", "general"),
                    statement=p_data.get("statement", p_data.get("text", "")),
                    conditions=p_data.get("conditions", []),
                    exceptions=p_data.get("exceptions", []),
                    priority=p_data.get("priority", 5),
                    source=p_data.get("source", "owner"),
                )
                policies.append(policy)
        return policies
