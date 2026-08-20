"""
orb/vault/a_priori/ontology_cognitive.py
Cognitive state for ontology graph.
"""

from __future__ import annotations
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from ..shared.types import Entity, Relation, EntityType, RelationType


@dataclass
class OntologyCognitiveState:
    """
    Stores business ontology as entity-relationship graph.
    """

    entities: Dict[str, Entity] = field(default_factory=dict)
    relations: Dict[str, Relation] = field(default_factory=dict)
    type_index: Dict[EntityType, List[str]] = field(default_factory=dict)
    relation_type_index: Dict[RelationType, List[str]] = field(default_factory=dict)
    name_index: Dict[str, str] = field(default_factory=dict)

    def add_entity(self, entity: Entity):
        self.entities[entity.entity_id] = entity
        if entity.entity_type not in self.type_index:
            self.type_index[entity.entity_type] = []
        self.type_index[entity.entity_type].append(entity.entity_id)
        self.name_index[entity.canonical_name.lower()] = entity.entity_id
        for alias in entity.aliases:
            self.name_index[alias.lower()] = entity.entity_id

    def add_relation(self, relation: Relation):
        self.relations[relation.relation_id] = relation
        if relation.relation_type not in self.relation_type_index:
            self.relation_type_index[relation.relation_type] = []
        self.relation_type_index[relation.relation_type].append(relation.relation_id)

    def get_entity_by_name(self, name: str) -> Optional[Entity]:
        entity_id = self.name_index.get(name.lower())
        if entity_id:
            return self.entities.get(entity_id)
        return None

    def get_entities_by_type(self, entity_type: EntityType) -> List[Entity]:
        ids = self.type_index.get(entity_type, [])
        return [self.entities[eid] for eid in ids if eid in self.entities]

    def get_relations_for_entity(self, entity_id: str, direction: str = "both") -> List[Relation]:
        results = []
        for rel in self.relations.values():
            if direction in ("both", "outgoing") and rel.source_id == entity_id:
                results.append(rel)
            if direction in ("both", "incoming") and rel.target_id == entity_id:
                results.append(rel)
        return results

    def get_neighbors(self, entity_id: str) -> List[Entity]:
        rels = self.get_relations_for_entity(entity_id)
        neighbor_ids = set()
        for rel in rels:
            if rel.source_id == entity_id:
                neighbor_ids.add(rel.target_id)
            else:
                neighbor_ids.add(rel.source_id)
        return [self.entities[nid] for nid in neighbor_ids if nid in self.entities]
