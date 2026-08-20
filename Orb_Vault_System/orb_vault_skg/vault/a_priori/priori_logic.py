"""
orb/vault/a_priori/priori_logic.py
Main A Priori Vault coordinator.
Settled truth layer: catalog, ontology, policy, QA.
"""

from __future__ import annotations
from typing import Dict, List, Any, Optional

from ..shared.types import (
    ResolutionResult, IntentType, CatalogEntry, Entity, Relation,
    QACorrespondence, PolicyRule
)
from ..shared.constants import VaultConstants

from .catalog_logic import CatalogLogic
from .catalog_cognitive import CatalogCognitiveState
from .ontology_logic import OntologyLogic
from .ontology_cognitive import OntologyCognitiveState
from .qa_logic import QALogic
from .qa_cognitive import QACognitiveState
from .loader import PrioriLoader


class PrioriVault:
    """
    A Priori Vault -- settled truth layer.
    Contains: catalog, ontology, policy, QA.
    Direct lookup. No learning. Owner-approved or crawl-verified.
    """

    def __init__(self, weaver_output_dir: str):
        self.loader = PrioriLoader(weaver_output_dir)
        loaded = self.loader.load_all()

        self.catalog_state: CatalogCognitiveState = loaded["catalog"]
        self.ontology_state: OntologyCognitiveState = loaded["ontology"]
        self.qa_state: QACognitiveState = loaded["qa"]
        self.policies: List[PolicyRule] = loaded["policies"]

        self.catalog_logic = CatalogLogic()
        self.ontology_logic = OntologyLogic()
        self.qa_logic = QALogic()

    def query(self, query_text: str, intent: IntentType, entities: List[str]) -> ResolutionResult:
        if intent == IntentType.PRODUCT_PRICE:
            if entities:
                return self.catalog_logic.price_lookup(self.catalog_state.get_all(), entities[0])

        elif intent == IntentType.PRODUCT_AVAILABILITY:
            if entities:
                return self.catalog_logic.availability_lookup(self.catalog_state.get_all(), entities[0])

        elif intent == IntentType.PRODUCT_INFO:
            if entities:
                return self.catalog_logic.spec_lookup(self.catalog_state.get_all(), entities[0])

        elif intent == IntentType.CATEGORY_BROWSE:
            if entities:
                results = self.catalog_logic.list_by_category(self.catalog_state.get_all(), entities[0])
                if results:
                    names = [r.name for r in results[:10]]
                    return ResolutionResult(
                        success=True,
                        answer=f"In {entities[0]} we have: {', '.join(names)}",
                        data={"products": [r.to_price_dict() for r in results]},
                        source="a_priori_catalog",
                        confidence=0.90,
                    )

        elif intent == IntentType.SERVICE_INQUIRY:
            if entities:
                return self.ontology_logic.find_service_description(
                    self.ontology_state.entities, self.ontology_state.relations, entities[0]
                )

        elif intent == IntentType.HOURS_LOCATION:
            return self.ontology_logic.find_business_summary(self.ontology_state.entities)

        elif intent == IntentType.CONTACT_INFO:
            depts = self.ontology_state.get_entities_by_type(EntityType.DEPARTMENT)
            if depts:
                info = []
                for d in depts[:3]:
                    phone = d.attributes.get("phone", "")
                    email = d.attributes.get("email", "")
                    parts = [d.canonical_name]
                    if phone:
                        parts.append(f"Phone: {phone}")
                    if email:
                        parts.append(f"Email: {email}")
                    info.append(" -- ".join(parts))
                return ResolutionResult(
                    success=True,
                    answer="Contact info: " + "; ".join(info),
                    source="a_priori_ontology",
                    confidence=0.90,
                )

        qa_result = self.qa_logic.query_qa(self.qa_state.get_all(), query_text, intent)
        if qa_result.success:
            return qa_result

        if entities:
            for entity in entities:
                entity_obj = self.ontology_state.get_entity_by_name(entity)
                if entity_obj:
                    related = self.ontology_logic.find_related_offerings(
                        self.ontology_state.entities, self.ontology_state.relations, entity_obj.entity_id
                    )
                    if related:
                        names = [r.canonical_name for r in related[:5]]
                        return ResolutionResult(
                            success=True,
                            answer=f"Related to {entity}: {', '.join(names)}",
                            source="a_priori_ontology",
                            confidence=0.80,
                            entity_id=entity_obj.entity_id,
                        )

        return ResolutionResult(
            success=False,
            source="a_priori",
            resolution_path=["a_priori", "no_match"],
        )

    def get_catalog_export(self) -> List[Dict[str, Any]]:
        return self.catalog_logic.export_to_dict(self.catalog_state.get_all())

    def get_entity(self, name: str) -> Optional[Entity]:
        return self.ontology_state.get_entity_by_name(name)

    def get_product(self, name_or_sku: str) -> Optional[CatalogEntry]:
        entry = self.catalog_state.get_by_name(name_or_sku)
        if not entry:
            entry = self.catalog_state.get_by_sku(name_or_sku)
        return entry

    def reload(self):
        loaded = self.loader.load_all()
        self.catalog_state = loaded["catalog"]
        self.ontology_state = loaded["ontology"]
        self.qa_state = loaded["qa"]
        self.policies = loaded["policies"]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "catalog_entries": len(self.catalog_state.entries),
            "ontology_entities": len(self.ontology_state.entities),
            "ontology_relations": len(self.ontology_state.relations),
            "qa_pairs": len(self.qa_state.qa_pairs),
            "policies": len(self.policies),
        }
