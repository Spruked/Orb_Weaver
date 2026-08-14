import asyncio
from urllib.robotparser import RobotFileParser

from app.crawler.engine import OrbWeaverCrawler


def test_vite_module_shell_requires_rendering():
    crawler = OrbWeaverCrawler(delay=0.01)
    html = '<html><body><div id="app"></div><script type="module" src="/assets/index-abc.js"></script></body></html>'

    assert crawler._looks_like_spa_shell(html) is True


def test_next_shell_requires_rendering():
    crawler = OrbWeaverCrawler(delay=0.01)
    html = '<html><body><div id="__next"></div><script src="/_next/static/chunks/app.js"></script></body></html>'

    assert crawler._looks_like_spa_shell(html) is True


def test_content_complete_static_page_does_not_require_rendering():
    crawler = OrbWeaverCrawler(delay=0.01)
    html = '<html><body><main><h1>Documentation</h1><p>' + ('Useful static content. ' * 20) + '</p></main></body></html>'

    assert crawler._looks_like_spa_shell(html) is False


def test_robots_policy_blocks_fetch_and_records_evidence():
    crawler = OrbWeaverCrawler(delay=0.01)
    crawler.domain = "example.test"
    crawler.domain_key = "example.test"
    crawler.respect_robots = True
    parser = RobotFileParser()
    parser.parse(["User-agent: *", "Disallow: /private"])
    crawler.robots_parser = parser

    async def fail_fetch(*_args, **_kwargs):
        raise AssertionError("robots-blocked URL must not be fetched")

    crawler._fetch_page = fail_fetch
    blocked_url = "https://example.test/private"
    result = asyncio.run(crawler._crawl_page(None, blocked_url))

    assert result is None
    assert blocked_url in crawler.robots_blocked_urls
    assert blocked_url not in crawler.visited_urls
    assert crawler.get_crawl_stats()["robots_policy_enforced"] is True
