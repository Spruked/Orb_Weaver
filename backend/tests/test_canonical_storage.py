from app.core.storage import (
    BROWSER_REVIEWS_ROOT,
    CLIENTS_ROOT,
    COGNITION_ROOT,
    DATABASES_ROOT,
    POSTERIORI_ROOT,
    REPORTS_ROOT,
    TTS_CACHE_ROOT,
    VAULT_ROOT,
    canonical_database_url,
    client_root,
)


def test_all_storage_roots_are_children_of_the_canonical_vault():
    for path in (
        CLIENTS_ROOT,
        COGNITION_ROOT,
        DATABASES_ROOT,
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
