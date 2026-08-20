"""
orb/vault/a_priori/catalog_logic.py
Product/service catalog operations.
Direct lookups. No reasoning. Settled truth from crawl.
"""

from __future__ import annotations
from typing import Dict, List, Any, Optional

from ..shared.types import CatalogEntry, EntityType, ResolutionResult, IntentType


class CatalogLogic:
    """
    Catalog lookup engine.
    Answers: price, availability, SKU, variant, spec queries directly.
    """

    @staticmethod
    def lookup_by_name(
        catalog: Dict[str, CatalogEntry],
        name: str,
        fuzzy: bool = True
    ) -> Optional[CatalogEntry]:
        for entry in catalog.values():
            if entry.name.lower() == name.lower():
                return entry
            if name.lower() in entry.name.lower():
                return entry

        if fuzzy:
            name_tokens = set(name.lower().split())
            best_match = None
            best_score = 0.0
            for entry in catalog.values():
                entry_tokens = set(entry.name.lower().split())
                if not entry_tokens:
                    continue
                overlap = len(name_tokens & entry_tokens) / len(name_tokens | entry_tokens)
                if overlap > best_score and overlap > 0.5:
                    best_score = overlap
                    best_match = entry
            return best_match
        return None

    @staticmethod
    def lookup_by_sku(catalog: Dict[str, CatalogEntry], sku: str) -> Optional[CatalogEntry]:
        for entry in catalog.values():
            if entry.sku and entry.sku.lower() == sku.lower():
                return entry
        return None

    @staticmethod
    def price_lookup(catalog: Dict[str, CatalogEntry], product_name: str) -> ResolutionResult:
        entry = CatalogLogic.lookup_by_name(catalog, product_name)
        if not entry:
            return ResolutionResult(
                success=False,
                source="a_priori_catalog",
                resolution_path=["catalog", "price_lookup", "not_found"],
            )

        price_data = entry.to_price_dict()
        if entry.sale_price and entry.sale_price < entry.current_price:
            answer = f"{entry.name} is on sale for ${entry.sale_price:.2f} (regular ${entry.current_price:.2f})"
        else:
            answer = f"{entry.name} is ${entry.current_price:.2f}"

        if entry.availability:
            answer += f". Availability: {entry.availability}."

        return ResolutionResult(
            success=True,
            answer=answer,
            data=price_data,
            source="a_priori_catalog",
            confidence=0.95 if entry.owner_verified else 0.85,
            entity_id=entry.entry_id,
            resolution_path=["catalog", "price_lookup", "direct_hit"],
        )

    @staticmethod
    def availability_lookup(catalog: Dict[str, CatalogEntry], product_name: str) -> ResolutionResult:
        entry = CatalogLogic.lookup_by_name(catalog, product_name)
        if not entry:
            return ResolutionResult(success=False, source="a_priori_catalog")

        avail = entry.availability or "unknown"
        answer = f"{entry.name} is currently {avail}."

        return ResolutionResult(
            success=True,
            answer=answer,
            data={"availability": avail, "sku": entry.sku},
            source="a_priori_catalog",
            confidence=0.90,
            entity_id=entry.entry_id,
        )

    @staticmethod
    def spec_lookup(catalog: Dict[str, CatalogEntry], product_name: str, spec_key: Optional[str] = None) -> ResolutionResult:
        entry = CatalogLogic.lookup_by_name(catalog, product_name)
        if not entry:
            return ResolutionResult(success=False, source="a_priori_catalog")

        if spec_key and spec_key in entry.specifications:
            answer = f"{entry.name} {spec_key}: {entry.specifications[spec_key]}"
            data = {spec_key: entry.specifications[spec_key]}
        else:
            specs = ", ".join([f"{k}={v}" for k, v in entry.specifications.items()])
            answer = f"{entry.name} specifications: {specs}"
            data = entry.specifications

        return ResolutionResult(
            success=True,
            answer=answer,
            data=data,
            source="a_priori_catalog",
            confidence=0.90,
            entity_id=entry.entry_id,
        )

    @staticmethod
    def list_by_category(catalog: Dict[str, CatalogEntry], category: str) -> List[CatalogEntry]:
        results = []
        for entry in catalog.values():
            if entry.entry_type == EntityType.PRODUCT:
                if category.lower() in entry.name.lower():
                    results.append(entry)
                elif "category" in entry.attributes:
                    if entry.attributes["category"].lower() == category.lower():
                        results.append(entry)
        return results

    @staticmethod
    def export_to_dict(catalog: Dict[str, CatalogEntry]) -> List[Dict[str, Any]]:
        return [entry.to_price_dict() for entry in catalog.values()]
