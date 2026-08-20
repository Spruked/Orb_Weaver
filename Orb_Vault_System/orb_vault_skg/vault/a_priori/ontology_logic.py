"""
orb/vault/a_priori/ontology_logic.py
Business ontology -- what the business does, relationships, departments, policies.
"""

from __future__ import annotations
from typing import Dict, List, Any, Optional

from ..shared.types import Entity, Relation, RelationType, EntityType, ResolutionResult, IntentType


class OntologyLogic:
    """
    Ontology traversal and resolution.
    Answers: what service is for, which department handles X, what route fulfills intent.
    """

    @staticmethod
    def resolve_intent_to_department(
        entities: Dict[str, Entity],
        relations: Dict[str, Relation],
        intent: IntentType
    ) -> ResolutionResult:
        intent_entities = [
            e for e in entities.values()
            if e.entity_type == EntityType.INTENT and intent.name in e.canonical_name
        ]
        if not intent_entities:
            return ResolutionResult(success=False, source="a_priori_ontology")

        intent_entity = intent_entities[0]
        for rel in relations.values():
            if (rel.relation_type == RelationType.HANDLED_BY and
                rel.source_id == intent_entity.entity_id):
                dept = entities.get(rel.target_id)
                if dept:
                    return ResolutionResult(
                        success=True,
                        answer=f"That would be handled by {dept.canonical_name}.",
                        data={"department": dept.canonical_name, "dept_id": dept.entity_id},
                        source="a_priori_ontology",
                        confidence=rel.confidence.value,
                        resolution_path=["ontology", "intent_to_department"],
                    )
        return ResolutionResult(success=False, source="a_priori_ontology")

    @staticmethod
    def find_service_description(
        entities: Dict[str, Entity],
        relations: Dict[str, Relation],
        service_name: str
    ) -> ResolutionResult:
        service = None
        for e in entities.values():
            if e.entity_type == EntityType.SERVICE and service_name.lower() in e.canonical_name.lower():
                service = e
                break

        if not service:
            return ResolutionResult(success=False, source="a_priori_ontology")

        desc = service.attributes.get("description", "")
        purpose = service.attributes.get("purpose", "")
        answer = f"{service.canonical_name}"
        if desc:
            answer += f": {desc}"
        if purpose:
            answer += f" This service is for {purpose}."

        return ResolutionResult(
            success=True,
            answer=answer,
            data=service.attributes,
            source="a_priori_ontology",
            confidence=0.90,
            entity_id=service.entity_id,
        )

    @staticmethod
    def find_related_offerings(
        entities: Dict[str, Entity],
        relations: Dict[str, Relation],
        entity_id: str,
        relation_type: RelationType = RelationType.BELONGS_TO
    ) -> List[Entity]:
        related = []
        for rel in relations.values():
            if rel.relation_type == relation_type:
                if rel.source_id == entity_id:
                    target = entities.get(rel.target_id)
                    if target:
                        related.append(target)
                elif rel.target_id == entity_id:
                    source = entities.get(rel.source_id)
                    if source:
                        related.append(source)
        return related

    @staticmethod
    def traverse_policy_chain(entities: Dict[str, Entity], relations: Dict[str, Relation], topic: str) -> ResolutionResult:
        policies = []
        for e in entities.values():
            if e.entity_type == EntityType.POLICY and topic.lower() in e.canonical_name.lower():
                policies.append(e)

        if not policies:
            return ResolutionResult(success=False, source="a_priori_ontology")

        answers = []
        for p in policies:
            stmt = p.attributes.get("statement", "")
            if stmt:
                answers.append(f"{p.canonical_name}: {stmt}")

        return ResolutionResult(
            success=True,
            answer=" ".join(answers),
            data={"policies": [p.entity_id for p in policies]},
            source="a_priori_ontology",
            confidence=0.90,
        )

    @staticmethod
    def find_business_summary(entities: Dict[str, Entity]) -> ResolutionResult:
        business = None
        for e in entities.values():
            if e.entity_type == EntityType.CATEGORY and "business" in e.canonical_name.lower():
                business = e
                break

        if not business:
            services = [e for e in entities.values() if e.entity_type == EntityType.SERVICE]
            if services:
                names = [s.canonical_name for s in services[:5]]
                return ResolutionResult(
                    success=True,
                    answer=f"We offer: {', '.join(names)}.",
                    source="a_priori_ontology",
                    confidence=0.80,
                )
            return ResolutionResult(success=False, source="a_priori_ontology")

        desc = business.attributes.get("description", "We provide various products and services.")
        return ResolutionResult(
            success=True,
            answer=desc,
            data=business.attributes,
            source="a_priori_ontology",
            confidence=0.95,
            entity_id=business.entity_id,
        )
