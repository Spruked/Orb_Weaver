from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


CATALOG_SCHEMA = "orb_weaver.catalog_sqlite.v1"


def _normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


def create_catalog_database(path: Path | str, entries: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        destination.unlink()

    with sqlite3.connect(destination) as connection:
        connection.executescript(
            """
            PRAGMA journal_mode=DELETE;
            PRAGMA foreign_keys=ON;
            CREATE TABLE metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE catalog_entries (
                entity_id TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,
                name TEXT NOT NULL,
                normalized_name TEXT NOT NULL,
                sku TEXT,
                normalized_sku TEXT,
                description TEXT,
                category TEXT,
                price_amount REAL,
                sale_price_amount REAL,
                currency TEXT,
                price_display TEXT,
                billing_period TEXT,
                availability TEXT,
                route TEXT NOT NULL,
                source_url TEXT NOT NULL,
                source_evidence_ids TEXT NOT NULL,
                pointer_target_id TEXT,
                confidence REAL NOT NULL,
                content_hash TEXT NOT NULL,
                attributes TEXT NOT NULL,
                verified INTEGER NOT NULL CHECK (verified IN (0, 1))
            );
            CREATE INDEX idx_catalog_name ON catalog_entries(normalized_name);
            CREATE INDEX idx_catalog_sku ON catalog_entries(normalized_sku);
            CREATE INDEX idx_catalog_type ON catalog_entries(entity_type);
            """
        )
        connection.execute("INSERT INTO metadata(key, value) VALUES (?, ?)", ("schema", CATALOG_SCHEMA))

        inserted = 0
        for entry in entries:
            if entry.get("verified") is not True:
                continue
            price = entry.get("price") or {}
            attributes = dict(entry.get("attributes") or {})
            sale_price = attributes.get("sale_price")
            if isinstance(sale_price, dict):
                sale_price = sale_price.get("amount")
            connection.execute(
                """
                INSERT INTO catalog_entries (
                    entity_id, entity_type, name, normalized_name, sku, normalized_sku,
                    description, category, price_amount, sale_price_amount, currency,
                    price_display, billing_period, availability, route, source_url,
                    source_evidence_ids, pointer_target_id, confidence, content_hash,
                    attributes, verified
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (
                    str(entry["entity_id"]),
                    str(entry["entity_type"]),
                    str(entry["name"]),
                    _normalized(str(entry["name"])),
                    entry.get("sku"),
                    _normalized(str(entry.get("sku") or "")) or None,
                    entry.get("description"),
                    entry.get("category"),
                    price.get("amount"),
                    sale_price,
                    price.get("currency"),
                    price.get("display_text"),
                    price.get("billing_period"),
                    json.dumps(entry.get("availability"), separators=(",", ":")),
                    str(entry.get("route") or ""),
                    str(entry["source_url"]),
                    json.dumps(entry.get("source_evidence_ids") or []),
                    entry.get("pointer_target_id"),
                    float(entry.get("confidence", 1.0)),
                    str(entry["content_hash"]),
                    json.dumps(attributes, sort_keys=True),
                ),
            )
            inserted += 1
        connection.execute("INSERT INTO metadata(key, value) VALUES (?, ?)", ("entry_count", str(inserted)))
        connection.commit()

    return {"schema": CATALOG_SCHEMA, "path": str(destination), "entry_count": inserted}


@dataclass(frozen=True)
class CatalogMatch:
    record: Dict[str, Any]
    score: float
    match_type: str


class CatalogRepository:
    def __init__(self, path: Path | str):
        self.path = Path(path)

    def validate(self) -> Dict[str, Any]:
        if not self.path.is_file():
            return {"valid": False, "reason": "catalog_database_missing", "entry_count": 0}
        try:
            with sqlite3.connect(f"file:{self.path}?mode=ro", uri=True) as connection:
                schema = connection.execute("SELECT value FROM metadata WHERE key = 'schema'").fetchone()
                count = connection.execute("SELECT COUNT(*) FROM catalog_entries WHERE verified = 1").fetchone()[0]
            if not schema or schema[0] != CATALOG_SCHEMA:
                return {"valid": False, "reason": "catalog_schema_invalid", "entry_count": count}
            return {"valid": True, "reason": None, "entry_count": count}
        except (sqlite3.Error, OSError) as exc:
            return {"valid": False, "reason": f"catalog_unreadable:{exc}", "entry_count": 0}

    def lookup(self, query: str, *, entity_type: Optional[str] = None) -> Optional[CatalogMatch]:
        clean_query = _normalized(query)
        if not clean_query or not self.path.is_file():
            return None
        rows = self._rows(entity_type)
        exact = next(
            (
                row for row in rows
                if clean_query == row["normalized_name"]
                or (row["normalized_sku"] and clean_query == row["normalized_sku"])
            ),
            None,
        )
        if exact:
            match_type = "sku" if exact["normalized_sku"] == clean_query else "exact"
            return CatalogMatch(self._record(exact), 1.0, match_type)

        query_tokens = set(clean_query.split())
        best: Optional[CatalogMatch] = None
        for row in rows:
            candidate_tokens = set(str(row["normalized_name"]).split())
            if row["normalized_sku"]:
                candidate_tokens.add(str(row["normalized_sku"]))
            overlap = query_tokens & candidate_tokens
            if not overlap:
                continue
            containment = 0.92 if row["normalized_name"] in clean_query else 0.0
            score = max(containment, len(overlap) / max(1, len(candidate_tokens)))
            candidate = CatalogMatch(self._record(row), round(score, 3), "fuzzy")
            if score >= 0.5 and (best is None or score > best.score):
                best = candidate
        return best

    def lookup_sku(self, sku: str) -> Optional[CatalogMatch]:
        clean_sku = _normalized(sku)
        if not clean_sku or not self.path.is_file():
            return None
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM catalog_entries WHERE normalized_sku = ? AND verified = 1 LIMIT 1",
                (clean_sku,),
            ).fetchone()
        return CatalogMatch(self._record(row), 1.0, "sku") if row else None

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        return connection

    def _rows(self, entity_type: Optional[str]) -> list[sqlite3.Row]:
        with self._connect() as connection:
            if entity_type:
                return connection.execute(
                    "SELECT * FROM catalog_entries WHERE verified = 1 AND entity_type = ?",
                    (entity_type,),
                ).fetchall()
            return connection.execute("SELECT * FROM catalog_entries WHERE verified = 1").fetchall()

    @staticmethod
    def _record(row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "entity_id": row["entity_id"],
            "entity_type": row["entity_type"],
            "name": row["name"],
            "sku": row["sku"],
            "description": row["description"],
            "category": row["category"],
            "price": {
                "amount": row["price_amount"],
                "sale_amount": row["sale_price_amount"],
                "currency": row["currency"],
                "display_text": row["price_display"],
                "billing_period": row["billing_period"],
            },
            "availability": json.loads(row["availability"]),
            "route": row["route"],
            "source_url": row["source_url"],
            "source_evidence_ids": json.loads(row["source_evidence_ids"]),
            "pointer_target_id": row["pointer_target_id"],
            "confidence": row["confidence"],
            "content_hash": row["content_hash"],
            "attributes": json.loads(row["attributes"]),
            "verified": bool(row["verified"]),
        }
