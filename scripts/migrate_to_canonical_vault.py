#!/usr/bin/env python3
"""Consolidate Orb Weaver storage into repository-root vault_system.

Dry-run is the default. Stop Orb Weaver services before using --apply or
--finalize so databases and active cache files cannot change while copied.

--apply copies and hash-verifies every recognized legacy record.
--finalize additionally removes only verified legacy copies. It does not
recreate legacy storage paths.
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
    VAULT_ROOT / "cognition" / "workers",
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


def malformed_client_roots() -> list[Path]:
    backend = REPO_ROOT / "backend"
    if not backend.exists():
        return []

    roots: list[Path] = []
    for candidate in backend.rglob("clients"):
        if not candidate.is_dir() or candidate.is_symlink():
            continue
        relative_text = str(candidate.relative_to(backend))
        if (
            "R_Drive_Substrate" in relative_text
            or relative_text.startswith("R:")
            or relative_text.startswith("R_")
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
    canonical_path.parent.mkdir(parents=True, exist_ok=True)
    if canonical_path.suffix == "":
        canonical_path.mkdir(parents=True, exist_ok=True)
    legacy_path.symlink_to(canonical_path, target_is_directory=canonical_path.is_dir())
    operations.append(Operation(str(legacy_path), str(canonical_path), "installed-symlink"))


def migrate_known_storage(
    *,
    apply: bool,
    finalize: bool,
    operations: list[Operation],
) -> list[Path]:
    backend_data = REPO_ROOT / "backend" / "data"

    database_sources = (
        (backend_data / "orb_weaver.db", "backend-data", "orb_weaver.db"),
        (backend_data / "orb_weaver_check.db", "backend-data", "orb_weaver_check.db"),
        (REPO_ROOT / "data" / "orb_weaver.db", "root-data", "orb_weaver.db"),
        (REPO_ROOT / ".runtime" / "dev" / "orb_weaver.db", "runtime-dev", "orb_weaver.db"),
    )
    for source, source_label, database_name in database_sources:
        if source.exists() and not source.is_symlink():
            migrate_file(
                source,
                VAULT_ROOT / "databases" / database_name,
                source_label=source_label,
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

    for worker_name in (
        "deductive_SKG",
        "deductive_validator",
        "inductive_skg",
        "inductive_validator",
        "intuitive_skg",
        "intuitive_validator",
    ):
        migrate_tree(
            REPO_ROOT / "Orb_Assistant" / "src" / "logic_seeds" / worker_name / "vault",
            VAULT_ROOT / "cognition" / "workers" / worker_name.lower(),
            f"orb-cognition-{worker_name.lower()}",
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

    malformed_roots = malformed_client_roots()
    for index, source_root in enumerate(malformed_roots, start=1):
        migrate_tree(
            source_root,
            VAULT_ROOT / "clients",
            f"malformed-backend-clients-{index}",
            apply=apply,
            finalize=finalize,
            operations=operations,
        )

    for source_root, label in (
        (
            REPO_ROOT / "Orb_Assistant" / "vault_system" / "posteriori",
            "orb-assistant-posteriori",
        ),
        (
            REPO_ROOT / "Orb_Assistant" / "src" / "vault_system" / "posteriori",
            "orb-assistant-src-posteriori",
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

    for source, label, destination_name in (
        (REPO_ROOT / "scanner.log", "root-scanner-log", "preflight_scanner_legacy_root.log"),
        (REPO_ROOT / "backend" / "scanner.log", "backend-scanner-log", "preflight_scanner_legacy_backend.log"),
    ):
        if source.exists() and not source.is_symlink():
            migrate_file(
                source,
                VAULT_ROOT / "runtime" / "logs" / destination_name,
                source_label=label,
                relative_path=Path(destination_name),
                apply=apply,
                finalize=finalize,
                operations=operations,
            )

    return malformed_roots


def install_compatibility_links(
    malformed_roots: list[Path],
    operations: list[Operation],
) -> None:
    # All callers resolve the canonical root directly. Compatibility links can
    # be mistaken for another store, so finalization leaves legacy paths absent.
    for root in malformed_roots:
        remove_empty_tree(root)


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
    malformed_roots = migrate_known_storage(
        apply=apply,
        finalize=finalize,
        operations=operations,
    )

    if finalize:
        install_compatibility_links(malformed_roots, operations)

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
