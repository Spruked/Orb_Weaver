#!/usr/bin/env python3
"""Consolidate Orb Weaver storage into repository-root vault_system.

Dry-run is the default. Stop Orb Weaver services before using --apply or
--finalize so databases and active cache files cannot change while copied.

--apply copies and hash-verifies every recognized legacy record.
--finalize additionally removes only verified legacy copies and replaces
necessary old paths with compatibility symlinks into the canonical vault.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
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
    VAULT_ROOT / "integrations" / "cali_crm",
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
    if not root.exists() or root.is_symlink():
        return ()
    return (
        path
        for path in root.rglob("*")
        if path.is_file() and not path.is_symlink()
    )


def ensure_layout(apply: bool) -> None:
    if not apply:
        return
    for directory in CANONICAL_DIRS:
        directory.mkdir(parents=True, exist_ok=True)


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
    if not source_root.exists() or source_root.is_symlink():
        return
    if source_root.resolve() == destination_root.resolve():
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


def malformed_roots(named: str) -> list[Path]:
    """Find Linux directories created from Windows-style R-drive settings."""
    roots: list[Path] = []
    for candidate in REPO_ROOT.rglob(named):
        if not candidate.is_dir() or candidate.is_symlink():
            continue
        relative_text = str(candidate.relative_to(REPO_ROOT))
        if (
            "R_Drive_Substrate" in relative_text
            or "R:\\" in relative_text
            or "/R:/" in f"/{relative_text}/"
        ):
            roots.append(candidate)
    return sorted(set(roots))


def remove_empty_tree(root: Path) -> None:
    if not root.exists() or root.is_symlink():
        return
    for directory in sorted(
        (path for path in root.rglob("*") if path.is_dir() and not path.is_symlink()),
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


def install_symlink(
    legacy_path: Path,
    canonical_path: Path,
    operations: list[Operation],
) -> None:
    if legacy_path.is_symlink():
        if legacy_path.resolve() == canonical_path.resolve():
            operations.append(
                Operation(str(legacy_path), str(canonical_path), "symlink-already-canonical")
            )
            return
        legacy_path.unlink()

    if legacy_path.exists():
        if legacy_path.is_dir():
            remove_empty_tree(legacy_path)
        if legacy_path.exists():
            operations.append(
                Operation(
                    str(legacy_path),
                    str(canonical_path),
                    "symlink-blocked",
                    "Legacy path still contains unverified data.",
                )
            )
            return

    legacy_path.parent.mkdir(parents=True, exist_ok=True)
    canonical_path.mkdir(parents=True, exist_ok=True)
    legacy_path.symlink_to(canonical_path, target_is_directory=True)
    operations.append(Operation(str(legacy_path), str(canonical_path), "installed-symlink"))


def migrate_known_storage(
    *,
    apply: bool,
    finalize: bool,
    operations: list[Operation],
) -> tuple[list[Path], list[Path]]:
    backend_data = REPO_ROOT / "backend" / "data"

    for database_name in ("orb_weaver.db", "orb_weaver_check.db"):
        source = backend_data / database_name
        if source.exists() and not source.is_symlink():
            migrate_file(
                source,
                VAULT_ROOT / "databases" / database_name,
                source_label="backend-data",
                relative_path=Path(database_name),
                apply=apply,
                finalize=finalize,
                operations=operations,
            )

    for source_root, label in (
        (backend_data / "tts_cache", "backend-tts-cache"),
        (REPO_ROOT / "data" / "tts_cache", "root-data-tts-cache"),
        (REPO_ROOT / "Orb_Assistant" / "audio_cache", "orb-assistant-audio-cache"),
    ):
        migrate_tree(
            source_root,
            VAULT_ROOT / "runtime" / "tts_cache",
            label,
            apply=apply,
            finalize=finalize,
            operations=operations,
        )

    migrate_tree(
        REPO_ROOT / "substrate" / "clients",
        VAULT_ROOT / "clients",
        "substrate-clients",
        apply=apply,
        finalize=finalize,
        operations=operations,
    )

    malformed_client_roots = malformed_roots("clients")
    for index, source_root in enumerate(malformed_client_roots, start=1):
        migrate_tree(
            source_root,
            VAULT_ROOT / "clients",
            f"malformed-client-root-{index}",
            apply=apply,
            finalize=finalize,
            operations=operations,
        )

    for source_root, label in (
        (
            REPO_ROOT / "backend" / "vault_system" / "posteriori",
            "backend-posteriori",
        ),
        (
            REPO_ROOT / "Orb_Assistant" / "vault_system" / "posteriori",
            "orb-assistant-posteriori",
        ),
        (
            REPO_ROOT / "Orb_Assistant" / "src" / "vault_system" / "posteriori",
            "orb-assistant-src-posteriori",
        ),
        (
            REPO_ROOT / "Orb_Assistant" / "electron" / "src" / "vault_system" / "posteriori",
            "orb-assistant-electron-posteriori",
        ),
    ):
        migrate_tree(
            source_root,
            VAULT_ROOT / "posteriori",
            label,
            apply=apply,
            finalize=finalize,
            operations=operations,
        )

    for source_root, label in (
        (REPO_ROOT / "backend" / "report_compiler", "backend-reports"),
        (REPO_ROOT / "reports", "root-reports"),
    ):
        migrate_tree(
            source_root,
            VAULT_ROOT / "reports",
            label,
            apply=apply,
            finalize=finalize,
            operations=operations,
        )

    for source_root, label in (
        (REPO_ROOT / "browser_reviews", "root-browser-reviews"),
        (REPO_ROOT / "backend" / "browser_reviews", "backend-browser-reviews"),
    ):
        migrate_tree(
            source_root,
            VAULT_ROOT / "runtime" / "browser_reviews",
            label,
            apply=apply,
            finalize=finalize,
            operations=operations,
        )

    malformed_crm_roots = malformed_roots("cali_crm")
    for index, source_root in enumerate(malformed_crm_roots, start=1):
        migrate_tree(
            source_root,
            VAULT_ROOT / "integrations" / "cali_crm",
            f"malformed-cali-crm-root-{index}",
            apply=apply,
            finalize=finalize,
            operations=operations,
        )

    return malformed_client_roots, malformed_crm_roots


def install_compatibility_links(
    malformed_client_roots: list[Path],
    malformed_crm_roots: list[Path],
    operations: list[Operation],
) -> None:
    backend_data = REPO_ROOT / "backend" / "data"
    links = [
        (backend_data / "tts_cache", VAULT_ROOT / "runtime" / "tts_cache"),
        (REPO_ROOT / "data" / "tts_cache", VAULT_ROOT / "runtime" / "tts_cache"),
        (REPO_ROOT / "substrate" / "clients", VAULT_ROOT / "clients"),
        (
            REPO_ROOT / "backend" / "vault_system" / "posteriori",
            VAULT_ROOT / "posteriori",
        ),
        (
            REPO_ROOT / "Orb_Assistant" / "vault_system" / "posteriori",
            VAULT_ROOT / "posteriori",
        ),
        (
            REPO_ROOT / "Orb_Assistant" / "src" / "vault_system" / "posteriori",
            VAULT_ROOT / "posteriori",
        ),
        (
            REPO_ROOT / "Orb_Assistant" / "electron" / "src" / "vault_system" / "posteriori",
            VAULT_ROOT / "posteriori",
        ),
        (REPO_ROOT / "backend" / "report_compiler", VAULT_ROOT / "reports"),
        (REPO_ROOT / "reports", VAULT_ROOT / "reports"),
        (
            REPO_ROOT / "backend" / "browser_reviews",
            VAULT_ROOT / "runtime" / "browser_reviews",
        ),
        (
            REPO_ROOT / "browser_reviews",
            VAULT_ROOT / "runtime" / "browser_reviews",
        ),
    ]
    links.extend((root, VAULT_ROOT / "clients") for root in malformed_client_roots)
    links.extend(
        (root, VAULT_ROOT / "integrations" / "cali_crm")
        for root in malformed_crm_roots
    )

    for legacy_path, canonical_path in links:
        install_symlink(legacy_path, canonical_path, operations)

    for database_name in ("orb_weaver.db", "orb_weaver_check.db"):
        canonical_database = VAULT_ROOT / "databases" / database_name
        legacy_database = backend_data / database_name
        if not canonical_database.exists():
            continue
        if legacy_database.is_symlink():
            if legacy_database.resolve() == canonical_database.resolve():
                continue
            legacy_database.unlink()
        if legacy_database.exists():
            operations.append(
                Operation(
                    str(legacy_database),
                    str(canonical_database),
                    "database-link-blocked",
                    "Legacy database still contains unverified data.",
                )
            )
            continue
        legacy_database.parent.mkdir(parents=True, exist_ok=True)
        legacy_database.symlink_to(canonical_database)
        operations.append(
            Operation(str(legacy_database), str(canonical_database), "installed-symlink")
        )


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
        help="Copy and verify legacy data into the canonical vault. Stop services first.",
    )
    parser.add_argument(
        "--finalize",
        action="store_true",
        help="Remove verified legacy copies and install compatibility links.",
    )
    args = parser.parse_args()

    apply = args.apply or args.finalize
    finalize = args.finalize
    mode = "finalize" if finalize else "apply" if apply else "dry-run"

    if apply:
        print("IMPORTANT: Orb Weaver services must be stopped during this migration.")

    ensure_layout(apply)
    operations: list[Operation] = []
    malformed_client_roots, malformed_crm_roots = migrate_known_storage(
        apply=apply,
        finalize=finalize,
        operations=operations,
    )

    if finalize:
        install_compatibility_links(
            malformed_client_roots,
            malformed_crm_roots,
            operations,
        )

    manifest = write_manifest(operations, mode)

    print(f"Mode: {mode}")
    print(f"Canonical vault: {VAULT_ROOT}")
    print(f"Operations: {len(operations)}")
    for operation in operations:
        print(f"{operation.action}: {operation.source} -> {operation.destination}")
        if operation.detail:
            print(f"  {operation.detail}")
    if manifest:
        print(f"Manifest: {manifest}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
