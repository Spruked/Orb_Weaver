from pathlib import Path

import pytest

from app.core.storage import (
    BROWSER_REVIEWS_ROOT,
    CLIENTS_ROOT,
    COGNITION_ROOT,
    DATABASES_ROOT,
    GLOBAL_INTELLIGENCE_ROOT,
    IMMUTABLE_STORAGE_LAW,
    POSTERIORI_ROOT,
    REPORTS_ROOT,
    TTS_CACHE_ROOT,
    VAULT_ROOT,
    canonical_database_url,
    client_root,
    require_vault_path,
)


def test_all_storage_roots_are_children_of_the_canonical_vault():
    for path in (
        CLIENTS_ROOT,
        COGNITION_ROOT,
        DATABASES_ROOT,
        GLOBAL_INTELLIGENCE_ROOT,
        POSTERIORI_ROOT,
        REPORTS_ROOT,
        TTS_CACHE_ROOT,
        BROWSER_REVIEWS_ROOT,
    ):
        assert path == VAULT_ROOT or VAULT_ROOT in path.parents


def test_legacy_sqlite_url_is_rewritten_into_vault_databases():
    database_url = canonical_database_url("sqlite:///./data/orb_weaver.db")
    assert database_url.startswith("sqlite:////")
    assert str(DATABASES_ROOT.resolve()) in database_url
    assert database_url.endswith("/orb_weaver.db")


def test_client_domains_resolve_to_one_vault_tree():
    path = client_root("https://OrbWeaver.Spruked.com/some/path")
    assert path.parent == CLIENTS_ROOT
    assert path.name == "orbweaver.spruked.com"


def test_immutable_storage_law_is_executable_and_external_paths_fail_closed(tmp_path):
    assert "customer" in IMMUTABLE_STORAGE_LAW
    assert "checkout" in IMMUTABLE_STORAGE_LAW
    assert require_vault_path(GLOBAL_INTELLIGENCE_ROOT) == GLOBAL_INTELLIGENCE_ROOT.resolve()
    with pytest.raises(ValueError, match="canonical vault_system"):
        require_vault_path(tmp_path / "parallel-data", "test data")
    with pytest.raises(ValueError, match="External application databases"):
        canonical_database_url("postgresql://parallel.example/orb_weaver")
    with pytest.raises(ValueError, match="In-memory application databases"):
        canonical_database_url("sqlite:///:memory:")


def test_legacy_substrate_paths_are_only_links_into_the_canonical_vault():
    repository_root = Path(__file__).resolve().parents[2]
    expected = {
        repository_root / "substrate" / "clients": CLIENTS_ROOT,
        repository_root / "substrate" / "global_intelligence": GLOBAL_INTELLIGENCE_ROOT,
    }
    for legacy_path, canonical_path in expected.items():
        assert legacy_path.is_symlink()
        assert legacy_path.resolve() == canonical_path.resolve()
