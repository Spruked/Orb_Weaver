from bs4 import BeautifulSoup

from app.crawler.tesseract_weave import (
    build_lidar_candidate_inventory,
    collect_tesseract_candidates,
    summarize_weaves,
)


def test_tesseract_collects_images_documents_srcsets_and_visual_surfaces():
    soup = BeautifulSoup(
        """
        <html><head>
          <style>.hero { background-image: url('/media/hero.webp'); }</style>
          <link rel="icon" href="/favicon.png">
        </head><body>
          <picture>
            <source srcset="/images/a.png 1x, /images/a@2x.png 2x">
            <img src="/images/fallback.jpg" data-src="/images/lazy.avif">
          </picture>
          <a href="/documents/guide.pdf">Guide</a>
          <a href="/documents/workbook.xlsx">Workbook</a>
          <video poster="/media/poster.jpg"></video>
          <div style="background:url('/media/card.png')"></div>
          <svg><text>Visible label</text></svg>
          <canvas></canvas>
        </body></html>
        """,
        "lxml",
    )

    result = collect_tesseract_candidates(soup, "https://example.com/start")
    urls = {row["url"] for row in result["resources"]}

    assert "https://example.com/images/a.png" in urls
    assert "https://example.com/images/a@2x.png" in urls
    assert "https://example.com/images/fallback.jpg" in urls
    assert "https://example.com/images/lazy.avif" in urls
    assert "https://example.com/documents/guide.pdf" in urls
    assert "https://example.com/documents/workbook.xlsx" in urls
    assert "https://example.com/media/hero.webp" in urls
    assert "https://example.com/media/card.png" in urls
    assert "https://example.com/media/poster.jpg" in urls
    assert result["inline_svg_count"] == 1
    assert result["canvas_count"] == 1
    assert result["picture_count"] == 1
    assert result["ocr_execution_status"] == "not_run_during_discovery"


def test_tesseract_rejects_data_blob_and_non_media_links():
    soup = BeautifulSoup(
        """
        <img src="data:image/png;base64,abc">
        <img src="blob:https://example.com/abc">
        <a href="/ordinary-page">Not a document</a>
        """,
        "lxml",
    )

    result = collect_tesseract_candidates(soup, "https://example.com/")
    assert result["resources"] == []


def test_lidar_inventory_reports_candidates_without_inventing_geometry():
    result = build_lidar_candidate_inventory(
        "https://example.com/apply",
        [
            {"target_id": "target_1"},
            {"target_id": "target_2", "requires_live_validation": True},
        ],
    )

    assert result["pointer_candidate_count"] == 2
    assert result["persistent_target_count"] == 2
    assert result["dynamic_candidate_count"] == 1
    assert result["geometry_status"] == "runtime_measurement_required"
    assert result["live_validation_required"] is True


def test_weave_summary_aggregates_measured_page_outputs():
    class Page:
        def __init__(self):
            self.url = "https://example.com/"
            self.semantic_analysis = {
                "tesseract_weave": {
                    "resources": [
                        {"url": "https://example.com/a.png", "resource_class": "image"},
                        {"url": "https://example.com/guide.pdf", "resource_class": "document"},
                    ],
                    "visual_surface_count": 1,
                },
                "lidar_weave": {
                    "pointer_candidate_count": 3,
                    "persistent_target_ids": ["a", "b", "c"],
                    "dynamic_candidate_count": 1,
                },
            }

    summary = summarize_weaves([Page()])
    assert summary["tesseract_weave"]["unique_resource_count"] == 2
    assert summary["tesseract_weave"]["visual_surface_count"] == 1
    assert summary["lidar_weave"]["pointer_candidate_count"] == 3
    assert summary["lidar_weave"]["persistent_target_count"] == 3


def test_unscanned_historical_pages_are_not_reported_as_complete():
    from app.crawler.engine import PageData
    result = summarize_weaves([PageData(url="https://example.com/")])
    assert result["lidar_weave"]["status"] == "not_scanned"
    assert result["tesseract_weave"]["pages_scanned"] == 0
    assert result["tesseract_weave"]["status"] == "not_scanned"


def test_crawler_emits_mapping_evidence_from_fetched_html():
    import asyncio
    from app.crawler.engine import OrbWeaverCrawler

    crawler = OrbWeaverCrawler(delay=0)
    crawler.domain = crawler.domain_key = "example.com"

    async def fetch(*args):
        return ('<html><body><h1>Contact us</h1><a href="/contact">Contact our team</a>'
                '<img src="/hero.png" alt="Our team"></body></html>', 200, 10, [])

    crawler._fetch_page = fetch
    page = asyncio.run(crawler._crawl_page(None, "https://example.com/"))
    assert page is not None
    semantic = page.semantic_analysis
    assert semantic["lidar_weave"]["pointer_candidate_count"] > 0
    assert semantic["tesseract_weave"]["resource_count"] == 1
    crawler.crawled_data = [page]
    summary = crawler.get_crawl_stats()
    assert summary["lidar_weave"]["routes_with_targets"] == 1
    assert summary["lidar_weave"]["geometry_status"] == "runtime_measurement_required"
