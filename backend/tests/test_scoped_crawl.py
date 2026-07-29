from app.crawler.engine import PageData
from app.crawler.scoped import (
    _deduplicate_pages,
    _path_matches_prefix,
    _recalculate_duplicate_risk,
    _scope_and_seeds,
)


class _CrawlerStub:
    @staticmethod
    def _normalize_url(url: str) -> str:
        return url.rstrip("/")


def test_scope_marker_is_removed_from_owner_seeds():
    scope, seeds = _scope_and_seeds([
        "orb-scope:changed",
        "/products/one",
        "/products/two",
    ])

    assert scope == "changed"
    assert seeds == ["/products/one", "/products/two"]


def test_unknown_scope_does_not_override_full_default():
    scope, seeds = _scope_and_seeds(["orb-scope:anything", "/products"])

    assert scope == "full"
    assert seeds == ["/products"]


def test_section_prefix_does_not_escape_to_neighboring_path():
    prefixes = {"/products"}

    assert _path_matches_prefix("https://example.com/products", prefixes)
    assert _path_matches_prefix("https://example.com/products/one", prefixes)
    assert not _path_matches_prefix("https://example.com/product-support", prefixes)
    assert not _path_matches_prefix("https://example.com/account", prefixes)


def test_new_page_replaces_old_page_at_same_normalized_url():
    old = PageData(url="https://example.com/products/one/", title="Old")
    untouched = PageData(url="https://example.com/about", title="About")
    refreshed = PageData(url="https://example.com/products/one", title="New")

    merged = _deduplicate_pages(_CrawlerStub(), [old, untouched, refreshed])

    assert [page.url for page in merged] == [
        "https://example.com/products/one",
        "https://example.com/about",
    ]
    assert merged[0].title == "New"


def test_duplicate_risk_is_recomputed_after_authoritative_merge():
    first = PageData(url="https://example.com/a", content_hash="same")
    second = PageData(url="https://example.com/b", content_hash="same")
    third = PageData(url="https://example.com/c", content_hash="unique")

    _recalculate_duplicate_risk([first, second, third])

    assert first.duplicate_content_risk is True
    assert second.duplicate_content_risk is True
    assert third.duplicate_content_risk is False
