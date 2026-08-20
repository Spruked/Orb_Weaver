"""
orb/vault/a_priori/catalog_cognitive.py
Cognitive state for catalog storage and indexes.
"""

from __future__ import annotations
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from ..shared.types import CatalogEntry


@dataclass
class CatalogCognitiveState:
    """
    Catalog storage with multiple indexes for fast lookup.
    """

    entries: Dict[str, CatalogEntry] = field(default_factory=dict)
    name_index: Dict[str, str] = field(default_factory=dict)
    sku_index: Dict[str, str] = field(default_factory=dict)
    category_index: Dict[str, List[str]] = field(default_factory=dict)
    price_ranges: Dict[str, List[str]] = field(default_factory=dict)

    def add_entry(self, entry: CatalogEntry):
        self.entries[entry.entry_id] = entry
        self.name_index[entry.name.lower()] = entry.entry_id
        if entry.sku:
            self.sku_index[entry.sku.lower()] = entry.entry_id
        category = entry.attributes.get("category", "uncategorized")
        if category not in self.category_index:
            self.category_index[category] = []
        self.category_index[category].append(entry.entry_id)

    def get_by_id(self, entry_id: str) -> Optional[CatalogEntry]:
        return self.entries.get(entry_id)

    def get_by_name(self, name: str) -> Optional[CatalogEntry]:
        entry_id = self.name_index.get(name.lower())
        if entry_id:
            return self.entries.get(entry_id)
        return None

    def get_by_sku(self, sku: str) -> Optional[CatalogEntry]:
        entry_id = self.sku_index.get(sku.lower())
        if entry_id:
            return self.entries.get(entry_id)
        return None

    def get_by_category(self, category: str) -> List[CatalogEntry]:
        entry_ids = self.category_index.get(category, [])
        return [self.entries[eid] for eid in entry_ids if eid in self.entries]

    def get_all(self) -> Dict[str, CatalogEntry]:
        return dict(self.entries)

    def update_entry(self, entry: CatalogEntry):
        if entry.entry_id in self.entries:
            old = self.entries[entry.entry_id]
            self.name_index.pop(old.name.lower(), None)
            if old.sku:
                self.sku_index.pop(old.sku.lower(), None)
        self.add_entry(entry)

    def remove_entry(self, entry_id: str):
        if entry_id not in self.entries:
            return
        entry = self.entries[entry_id]
        self.entries.pop(entry_id, None)
        self.name_index.pop(entry.name.lower(), None)
        if entry.sku:
            self.sku_index.pop(entry.sku.lower(), None)
        category = entry.attributes.get("category", "uncategorized")
        if category in self.category_index:
            self.category_index[category] = [e for e in self.category_index[category] if e != entry_id]
