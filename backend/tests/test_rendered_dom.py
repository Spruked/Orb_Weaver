import asyncio

from app.crawler.rendered_dom import (
    install_rendered_dom_support,
    looks_like_unrendered_app_shell,
    resolve_browser_executable,
    summarize_dom_signals,
)


def test_detects_legacy_create_react_app_shell():
    html = """
    <html><body><div id="root"></div>
    <script src="/static/js/main.123.js"></script></body></html>
    """

    assert looks_like_unrendered_app_shell(html) is True


def test_detects_vite_module_shell():
    html = """
    <html><head><script type="module" src="/assets/index-123.js"></script></head>
    <body><div id="app"></div></body></html>
    """

    signals = summarize_dom_signals(html)
    assert signals["has_app_root"] is True
    assert signals["has_module_script"] is True
    assert looks_like_unrendered_app_shell(html) is True


def test_detects_next_application_shell():
    html = """
    <html><head><script src="/_next/static/chunks/main.js"></script></head>
    <body><div id="__next"></div></body></html>
    """

    assert looks_like_unrendered_app_shell(html) is True


def test_does_not_render_an_ordinary_content_page():
    html = """
    <html><body>
      <header><a href="/">Home</a><a href="/pricing">Pricing</a></header>
      <main><h1>TrueMark Mint</h1><p>Create durable proof records for important digital objects.</p>
      <button>Create a Free Record</button></main>
    </body></html>
    """

    assert looks_like_unrendered_app_shell(html) is False


def test_browser_resolution_honors_configured_absolute_path(tmp_path, monkeypatch):
    browser = tmp_path / "chromium"
    browser.write_text("test", encoding="utf-8")
    monkeypatch.setenv("CHROME_PATH", str(browser))

    assert resolve_browser_executable() == str(browser)


def test_render_failure_is_reported_as_unresolved_shell():
    class FakeCrawler:
        def __init__(self):
            self.rendered = "<html><body><div id='app'></div><script type='module' src='/assets/app.js'></script></body></html>"

        def _normalize_url(self, url):
            return url.rstrip("/")

        def _looks_like_spa_shell(self, html):
            return False

        def _chrome_executable(self):
            return None

        async def _render_page_dom(self, url):
            return self.rendered

        async def crawl(self, start_url, seed_urls=None):
            return []

        def get_crawl_stats(self):
            return {}

    install_rendered_dom_support(FakeCrawler)
    crawler = FakeCrawler()

    result = asyncio.run(crawler._render_page_dom("https://example.test/app"))
    stats = crawler.get_crawl_stats()["rendered_dom"]

    assert result is None
    assert stats["status"] == "failed_unresolved_application_shell"
    assert stats["attempted"] == 1
    assert stats["failed"] == 1
    assert stats["unresolved_app_shell_count"] == 1
