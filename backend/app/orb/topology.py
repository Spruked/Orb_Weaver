from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger("orb.semantic_topology")


def _data_orb_attrs(tag: Tag) -> Dict[str, str]:
    return {
        str(key): str(value)
        for key, value in tag.attrs.items()
        if str(key).startswith("data-orb-")
    }


def _compact_text(value: str, limit: int = 120) -> str:
    return " ".join((value or "").split())[:limit]


def _selector_hint(tag: Tag) -> str:
    if tag.get("id"):
        return f"#{tag.get('id')}"
    data_target = tag.get("data-orb-target")
    if data_target:
        return f'[data-orb-target="{data_target}"]'
    classes = tag.get("class") or []
    if isinstance(classes, list) and classes:
        return f"{tag.name}.{'.'.join(str(item) for item in classes[:3])}"
    return str(tag.name)


@dataclass
class SemanticTopologyScraper:
    timeout_seconds: float = 3.0
    user_agent: str = "Orb-Weaver-Topology/1.0"
    previous_valid_graph: Optional[Dict[str, Any]] = field(default=None)

    def scan(self, target_url: str) -> Dict[str, Any]:
        if not isinstance(target_url, str) or not target_url.strip():
            return self._fallback("invalid_target_url")

        normalized_target = self._normalize_target(target_url)
        try:
            html = self._fetch_html(normalized_target)
            graph = self._parse(normalized_target, html)
            self.previous_valid_graph = graph
            return graph
        except Exception as exc:
            logger.warning("Topology scan failed for %s: %s", normalized_target, exc)
            return self._fallback(str(exc), normalized_target)

    def _normalize_target(self, target_url: str) -> str:
        value = target_url.strip()
        if not value.startswith(("http://", "https://")):
            value = f"https://{value}"
        return value

    def _fetch_html(self, target_url: str) -> str:
        headers = {"User-Agent": self.user_agent, "Accept": "text/html,application/xhtml+xml"}
        with httpx.Client(timeout=self.timeout_seconds, follow_redirects=True, headers=headers) as client:
            response = client.get(target_url)
            response.raise_for_status()
            return response.text

    def _parse(self, target_url: str, html: str) -> Dict[str, Any]:
        soup = BeautifulSoup(html, "lxml")
        detected_paths = self._extract_paths(target_url, soup)
        forms = self._extract_forms(target_url, soup)
        orb_targets = self._extract_orb_targets(soup)

        return {
            "url": target_url,
            "origin": self._origin(target_url),
            "detected_paths": detected_paths,
            "forms": forms,
            "orb_targets": orb_targets,
            "counts": {
                "anchors": len(detected_paths),
                "forms": len(forms),
                "orb_targets": len(orb_targets),
            },
            "valid": True,
            "stale": False,
            "error": None,
        }

    def _extract_paths(self, target_url: str, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        paths: List[Dict[str, Any]] = []
        seen = set()
        for anchor in soup.find_all("a", href=True):
            href = str(anchor.get("href") or "").strip()
            if not href or href.startswith(("mailto:", "tel:", "javascript:")):
                continue
            absolute = urljoin(target_url, href)
            dedupe_key = absolute.split("#", 1)[0]
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            parsed = urlparse(absolute)
            paths.append({
                "href": absolute,
                "path": parsed.path or "/",
                "text": _compact_text(anchor.get_text(" ", strip=True)),
                "same_origin": self._origin(absolute) == self._origin(target_url),
                "data_orb": _data_orb_attrs(anchor),
            })
        return paths

    def _extract_forms(self, target_url: str, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        forms: List[Dict[str, Any]] = []
        for index, form in enumerate(soup.find_all("form")):
            action = str(form.get("action") or target_url)
            controls = []
            for field_tag in form.find_all(["input", "select", "textarea", "button"]):
                controls.append({
                    "tag": field_tag.name,
                    "name": field_tag.get("name"),
                    "type": field_tag.get("type"),
                    "data_orb": _data_orb_attrs(field_tag),
                })
            forms.append({
                "index": index,
                "action": urljoin(target_url, action),
                "method": str(form.get("method") or "GET").upper(),
                "id": form.get("id"),
                "name": form.get("name"),
                "data_orb": _data_orb_attrs(form),
                "controls": controls,
            })
        return forms

    def _extract_orb_targets(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        targets: List[Dict[str, Any]] = []
        for tag in soup.find_all(
            lambda candidate: isinstance(candidate, Tag)
            and any(str(key).startswith("data-orb-") for key in candidate.attrs)
        ):
            if not isinstance(tag, Tag):
                continue
            targets.append({
                "tag": tag.name,
                "selector": _selector_hint(tag),
                "id": tag.get("id"),
                "text": _compact_text(tag.get_text(" ", strip=True)),
                "attributes": _data_orb_attrs(tag),
            })
        return targets

    def _origin(self, url: str) -> str:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")

    def _fallback(self, reason: str, target_url: Optional[str] = None) -> Dict[str, Any]:
        if self.previous_valid_graph:
            graph = dict(self.previous_valid_graph)
            graph["stale"] = True
            graph["valid"] = True
            graph["error"] = reason
            return graph
        return {
            "url": target_url or "",
            "origin": "",
            "detected_paths": [],
            "forms": [],
            "orb_targets": [],
            "counts": {"anchors": 0, "forms": 0, "orb_targets": 0},
            "valid": False,
            "stale": True,
            "error": reason,
        }


_DEFAULT_SCRAPER = SemanticTopologyScraper()


def scan_semantic_topology(target_url: str, previous_valid_graph: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    if previous_valid_graph is not None:
        _DEFAULT_SCRAPER.previous_valid_graph = dict(previous_valid_graph)
    return _DEFAULT_SCRAPER.scan(target_url)
