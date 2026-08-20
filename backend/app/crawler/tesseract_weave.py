"""Measured Tesseract and LiDAR weave support for canonical full scans.

The Tesseract weave inventories every visual or document resource that may
contain visitor-visible text. It does not claim OCR was performed; it records
raw candidates, provenance, and resource classes for downstream OCR workers.

The LiDAR weave inventories pointer identities that can be resolved by the
existing LiDAR 2D Mapping / Coordinate Cache runtime. Server-side crawling does
not have live viewport geometry, so this module reports mapping readiness
without inventing coordinates or visibility claims.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import PurePosixPath
from typing import Dict, Iterable, List, Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

OCR_DOCUMENT_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".odt", ".ods", ".odp", ".rtf", ".txt", ".csv",
}
OCR_IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif",
    ".webp", ".avif", ".heic", ".svg",
}
OCR_EXTENSIONS = OCR_DOCUMENT_EXTENSIONS | OCR_IMAGE_EXTENSIONS
CSS_URL_PATTERN = re.compile(r"url\(\s*(['\"]?)(.*?)\1\s*\)", re.IGNORECASE)


def _extension(url: str) -> str:
    path = urlparse(url).path
    return PurePosixPath(path).suffix.lower()


def _normalize_candidate(raw: str, base_url: str) -> Optional[str]:
    value = (raw or "").strip().strip("'\"")
    if not value or value.startswith(("data:", "blob:", "javascript:", "mailto:", "tel:")):
        return None
    return urljoin(base_url, value)


def _srcset_urls(value: str, base_url: str) -> Iterable[str]:
    for candidate in (value or "").split(","):
        raw = candidate.strip().split(" ", 1)[0]
        normalized = _normalize_candidate(raw, base_url)
        if normalized:
            yield normalized


def _resource_record(url: str, page_url: str, source: str, tag: str) -> Dict:
    extension = _extension(url)
    if extension in OCR_DOCUMENT_EXTENSIONS:
        resource_class = "document"
    elif extension == ".svg":
        resource_class = "vector_image"
    elif extension in OCR_IMAGE_EXTENSIONS:
        resource_class = "image"
    else:
        resource_class = "visual_surface"
    return {
        "url": url,
        "page_url": page_url,
        "source": source,
        "tag": tag,
        "extension": extension,
        "resource_class": resource_class,
        "ocr_status": "candidate_discovered",
    }


def collect_tesseract_candidates(soup: BeautifulSoup, page_url: str) -> Dict:
    """Collect all OCR-eligible resources and visual surfaces from one page."""
    records: Dict[str, Dict] = {}

    def add(raw: str, source: str, tag: str, *, require_extension: bool = False) -> None:
        normalized = _normalize_candidate(raw, page_url)
        if not normalized:
            return
        extension = _extension(normalized)
        if require_extension and extension not in OCR_EXTENSIONS:
            return
        key = f"{normalized}|{source}|{tag}"
        records[key] = _resource_record(normalized, page_url, source, tag)

    for tag in soup.find_all(["img", "source"]):
        for attr in ("src", "data-src", "data-lazy-src", "data-original"):
            if tag.get(attr):
                add(tag.get(attr), attr, tag.name)
        for attr in ("srcset", "data-srcset"):
            for resource_url in _srcset_urls(tag.get(attr, ""), page_url):
                add(resource_url, attr, tag.name)

    for tag in soup.find_all(["a", "link"], href=True):
        add(tag.get("href"), "href", tag.name, require_extension=True)

    for tag in soup.find_all(["object", "embed"]):
        if tag.get("data"):
            add(tag.get("data"), "data", tag.name)
        if tag.get("src"):
            add(tag.get("src"), "src", tag.name)
    for tag in soup.find_all("iframe", src=True):
        add(tag.get("src"), "iframe_src", tag.name, require_extension=True)
    for tag in soup.find_all("video", poster=True):
        add(tag.get("poster"), "poster", tag.name)

    for tag in soup.find_all(style=True):
        for _quote, raw in CSS_URL_PATTERN.findall(tag.get("style", "")):
            add(raw, "inline_style", tag.name)
    for style_tag in soup.find_all("style"):
        for _quote, raw in CSS_URL_PATTERN.findall(style_tag.get_text(" ", strip=False)):
            add(raw, "style_block", "style")

    inline_svg_count = len(soup.find_all("svg"))
    canvas_count = len(soup.find_all("canvas"))
    picture_count = len(soup.find_all("picture"))

    resources = sorted(records.values(), key=lambda row: (row["url"], row["source"]))
    class_counts = Counter(row["resource_class"] for row in resources)
    extension_counts = Counter(row["extension"] or "extensionless" for row in resources)

    return {
        "status": "candidate_inventory_complete",
        "page_url": page_url,
        "resource_count": len(resources),
        "resources": resources,
        "resource_classes": dict(sorted(class_counts.items())),
        "extensions": dict(sorted(extension_counts.items())),
        "inline_svg_count": inline_svg_count,
        "canvas_count": canvas_count,
        "picture_count": picture_count,
        "visual_surface_count": inline_svg_count + canvas_count + picture_count,
        "ocr_execution_status": "not_run_during_discovery",
        "note": "Every candidate is preserved for downstream OCR; discovery does not assert extracted text.",
    }


def build_lidar_candidate_inventory(page_url: str, pointer_records: List[Dict]) -> Dict:
    """Report pointer identities eligible for live LiDAR 2D Mapping."""
    target_ids = sorted({
        str(row.get("target_id") or row.get("id"))
        for row in pointer_records or []
        if row.get("target_id") or row.get("id")
    })
    dynamic_count = sum(
        1 for row in pointer_records or []
        if row.get("dynamic") or row.get("is_dynamic") or row.get("requires_live_validation")
    )
    return {
        "status": "candidate_inventory_complete" if pointer_records else "no_pointer_candidates",
        "page_url": page_url,
        "pointer_candidate_count": len(pointer_records or []),
        "persistent_target_count": len(target_ids),
        "persistent_target_ids": target_ids,
        "dynamic_candidate_count": dynamic_count,
        "geometry_status": "runtime_measurement_required",
        "coordinate_cache_status": "eligible" if pointer_records else "not_applicable",
        "live_validation_required": True,
        "note": "LiDAR geometry, occlusion, drift, and viewport coordinates must be measured in the live browser runtime.",
    }


def summarize_weaves(pages: Iterable) -> Dict:
    """Aggregate measured Tesseract and LiDAR outputs into crawl statistics."""
    page_rows = list(pages)
    tesseract_urls = set()
    pages_with_candidates = 0
    inline_surfaces = 0
    tesseract_classes: Counter = Counter()
    lidar_candidates = 0
    lidar_persistent_targets = set()
    lidar_dynamic = 0
    lidar_routes = set()

    for page in page_rows:
        semantic = getattr(page, "semantic_analysis", {}) or {}
        tesseract = semantic.get("tesseract_weave") or {}
        resources = tesseract.get("resources") or []
        if resources or tesseract.get("visual_surface_count"):
            pages_with_candidates += 1
        inline_surfaces += int(tesseract.get("visual_surface_count") or 0)
        for row in resources:
            if row.get("url"):
                tesseract_urls.add(row["url"])
            if row.get("resource_class"):
                tesseract_classes[row["resource_class"]] += 1

        lidar = semantic.get("lidar_weave") or {}
        lidar_candidates += int(lidar.get("pointer_candidate_count") or 0)
        lidar_dynamic += int(lidar.get("dynamic_candidate_count") or 0)
        lidar_persistent_targets.update(lidar.get("persistent_target_ids") or [])
        if lidar.get("pointer_candidate_count"):
            lidar_routes.add(getattr(page, "url", ""))

    return {
        "tesseract_weave": {
            "status": "complete",
            "pages_scanned": len(page_rows),
            "pages_with_candidates": pages_with_candidates,
            "unique_resource_count": len(tesseract_urls),
            "visual_surface_count": inline_surfaces,
            "resource_classes": dict(sorted(tesseract_classes.items())),
            "ocr_execution_status": "candidate_inventory_complete",
        },
        "lidar_weave": {
            "status": "candidate_inventory_complete" if lidar_candidates else "no_pointer_candidates",
            "routes_with_targets": len(lidar_routes),
            "pointer_candidate_count": lidar_candidates,
            "persistent_target_count": len(lidar_persistent_targets),
            "dynamic_candidate_count": lidar_dynamic,
            "geometry_status": "runtime_measurement_required",
            "live_validation_required": True,
        },
    }
