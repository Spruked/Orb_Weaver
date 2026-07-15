#!/usr/bin/env python3
"""Consolidate every Orb Weaver storage root into repo-root vault_system.

Dry-run is the default. Use --apply to copy/merge data into the canonical vault.
Use --finalize only after Orb Weaver services are stopped; it removes legacy
files only after an identical canonical copy has been verified.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
VAULT_ROOT = REPO_ROOT / "vault_system"

CANONICAL_DIRS = (
    VAULT_ROOT / "clients",
    VAULT_ROOT / "databases",
    VAULT_ROOT / "posteriori",
    VAULT_ROOT / "apriori",
    VAULT_ROOT / "reports",
    VAULT_ROOT / "indexes",
    VAULT_ROOT / "manifests",
    VAULT_ROOT / "schemas",
    VAULT_ROOT / "runtime" / "tts_cache",
    VAULT_ROOT / "runtime" / "browser_reviews",
    VAULT_ROOT / "runtime" / "state",
    VAULT_ROOT / "runtime" / "logs",
    VAULT_ROOT / "backups" / "migration_conflicts",
)


@dataclass
class Operation:
    source: str
    destination: str
    action: str
    detail: str = ""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def files_under(root: Path) -> Iterable[Path]:
    if not root.exists():
        return ()
    return (path for path in root.rglob("*") if path.is_file() and not path.is_symlink())


def ensure_layout(apply: bool) -> None:
    if not apply:
        return
    for directory in CANONICAL_DIRS:
        directory.mkdir(parents=True, exist_ok=True)


def sqlite_backup(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(f"file:{source}?mode=ro", uri=True) as source_db:
        with sqlite3.connect(destination) as destination_db:
            source_db.backup(destination_db)


def conflict_destination(source_label: str, relative_path: Path) -> Path:
    return (
        VAULT_ROOT
        / "backups"
        / "migration_conflicts"
        / source_label
        / relative_path
    )


def migrate_file(
    source: Path,
    destination: Path,
    *,
    source_label: str,
    relative_path: Path,
    apply: bool,
    finalize: bool,
    operations: list[Operation],
) -> None:
    source_hash = sha256(source)

    if destination.exists():
        destination_hash = sha256(destination)
        if source_hash == destination_hash:
            action = "verified-duplicate"
            if apply and finalize:
                source.unlink()
                action = "removed-verified-duplicate"
            operations.append(Operation(str(source), str(destination), action))
            return

        conflict = conflict_destination(source_label, relative_path)
        operations.append(
            Operation(
                str(source),
                str(conflict),
                "preserve-conflict",
                "Canonical destination already contained different data.",
            )
        )
        if apply:
            conflict.parent.mkdir(parents=True, exist_ok=True)
            if not conflict.exists() or sha256(conflict) != source_hash:
                shutil.copy2(source, conflict)
            if finalize and conflict.exists() and sha256(conflict) == source_hash:
                source.unlink()
        return

    operations.append(Operation(str(source), str(destination), "copy-to-vault"))
    if not apply:
        return

    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.suffix.lower() in {".db", ".sqlite", ".sqlite3"}:
        sqlite_backup(source, destination)
    else:
        shutil.copy2(source, destination)

    if sha256(source) != sha256(destination):
        raise RuntimeError(f"Verification failed after copying {source} to {destination}")

    if finalize:
        source.unlink()
        operations[-1].action = "moved-to-vault"


def migrate_tree(
    source_root: Path,
    destination_root: Path,
    source_label: str,
    *,
    apply: bool,
    finalize: bool,
    operations: list[Operation],
) -> None:
    if not source_root.exists() or source_root.resolve() == destination_root.resolve():
        return

    for source in files_under(source_root):
        relative = source.relative_to(source_root)
        migrate_file(
            source,
            destination_root / relative,
            source_label=source_label,
            relative_path=relative,
            apply=apply,
            finalize=finalize,
            operations=operations,
        )


def malformed_client_roots() -> list[Path]:
    backend = REPO_ROOT / "backend"
    roots: list[Path] = []
    if not backend.exists():
        return roots

    for candidate in backend.rglob("clients"):
        if not candidate.is_dir():
            continue
        relative_text = str(candidate.relative_to(backend))
        if (
            "R_Drive_Substrate" in relative_text
            or relative_text.startswith("R:")
            or relative_text.startswith("R_")
        ):
            roots.append(candidate)
    return sorted(set(roots))


def remove_empty_legacy_directories() -> None:
    legacy_roots = (
        REPO_ROOT / "backend" / "data",
        REPO_ROOT / "data" / "tts_cache",
        REPO_ROOT / "substrate" / "clients",
        REPO_ROOT / "Orb_Assistant" / "vault_system" / "posteriori",
        REPO_ROOT / "Orb_Assistant" / "src" / "vault_system" / "posteriori",
        *malformed_client_roots(),
    )
    for root in legacy_roots:
        if not root.exists():
            continue
        for directory in sorted(
            (path for path in root.rglob("*") if path.is_dir()),
            key=lambda path: len(path.parts),
            reverse=True,
        ):
            try:
                directory.rmdir()
            except OSError:
                pass
        try:
            root.rmdir()
        except OSError:
            pass


def write_manifest(operations: list[Operation], mode: str) -> Path | None:
    if mode == "dry-run":
        return None
    manifest_root = VAULT_ROOT / "manifests"
    manifest_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = manifest_root / f"vault_migration_{stamp}.json"
    payload = {
        "schema": "orb-weaver.vault-migration.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "canonical_vault": str(VAULT_ROOT),
        "operations": [asdict(operation) for operation in operations],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Copy and verify legacy data into the canonical vault.",
    )
    parser.add_argument(
        "--finalize",
        action="store_true",
        help="After successful verification, remove legacy copies. Stop services first.",
    )
    args = parser.parse_args()

    apply = args.apply or args.finalize
    finalize = args.finalize
    mode = "finalize" if finalize else "apply" if apply else "dry-run"

    ensure_layout(apply)
    operations: list[Operation] = []

    # Databases.
    backend_data = REPO_ROOT / "backend" / "data"
    for database_name in ("orb_weaver.db", "orb_weaver_check.db"):
        source = backend_data / database_name
        if source.exists():
            migrate_file(
                source,
                VAULT_ROOT / "databases" / database_name,
                source_label="backend-data",
                relative_path=Path(database_name),
                apply=apply,
                finalize=finalize,
                operations=operations,
            )

    # Generated voice assets.
    migrate_tree(
        backend_data / "tts_cache",
        VAULT_ROOT / "runtime" / "tts_cache",
        "backend-tts-cache",
        apply=apply,
        finalize=finalize,
        operations=operations,
    )
    migrate_tree(
        REPO_ROOT / "data" / "tts_cache",
        VAULT_ROOT / "runtime" / "tts_cache",
        "root-data-tts-cache",
        apply=apply,
        finalize=finalize,
        operations=operations,
    )

    # Client scans, crawls, Site Worlds, pointer maps, reports and manifests.
    migrate_tree(
        REPO_ROOT / "substrate" / "clients",
        VAULT_ROOT / "clients",
        "substrate-clients",
        apply=apply,
        finalize=finalize,
        operations=operations,
    )
    for index, source_root in enumerate(malformed_client_roots(), start=1):
        migrate_tree(
            source_root,
            VAULT_ROOT / "clients",
            f"malformed-backend-clients-{index}",
            apply=apply,
            finalize=finalize,
            operations=operations,
        )

    # Learned memory.
    migrate_tree(
        REPO_ROOT / "Orb_Assistant" / "vault_system" / "posteriori",
        VAULT_ROOT / "posteriori",
        "orb-assistant-posteriori",
        apply=apply,
        finalize=finalize,
        operations=operations,
    )
    migrate_tree(
        REPO_ROOT / "Orb_Assistant" / "src" / "vault_system" / "posteriori",
        VAULT_ROOT / "posteriori",
        "orb-assistant-src-posteriori",
        apply=apply,
        finalize=finalize,
        operations=operations,
    )

    if finalize:
        remove_empty_legacy_directories()

    manifest = write_manifest(operations, mode)

    print(f"Mode: {mode}")
    print(f"Canonical vault: {VAULT_ROOT}")
    print(f"Operations: {len(operations)}")
    for operation in operations:
        print(f"{operation.action}: {operation.source} -> {operation.destination}")
    if manifest:
        print(f"Manifest: {manifest}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
