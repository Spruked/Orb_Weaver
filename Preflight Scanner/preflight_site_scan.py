"""
preflight_site_scan.py
Lightweight site reconnaissance module for ORB SSI.
Runs before full SSI index build. Produces site_preflight_report.json only.
Does not build SKG, MORB, or LLM pack.
"""

import asyncio
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

import aiohttp
from aiohttp import ClientTimeout


class FetchedResponse:
    def __init__(self, status: int, text: str):
        self.status = status
        self._text = text

    async def text(self) -> str:
        return self._text

# ---------------------------------------------------------------------------
# Optional imports from existing SSI codebase — compile-safe fallback
# ---------------------------------------------------------------------------
try:
    from scanner_logic import normalize_url, get_domain
except ImportError:
    def normalize_url(url: str) -> str:
        url = url.strip().rstrip("/")
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        return url

    def get_domain(url: str) -> str:
        return urlparse(url).netloc

try:
    from ssi_engine import SSI_CONFIG
except ImportError:
    SSI_CONFIG = {
        "user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "timeout": 15,
        "max_concurrent": 10,
        "respect_robots": True,
    }

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger("preflight_scanner")
if not logger.handlers:
    _handler = logging.FileHandler("scanner.log")
    _handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    ))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
CHAT_WIDGET_PATTERNS = [
    re.compile(r"intercom\.io", re.I),
    re.compile(r"crisp\.chat", re.I),
    re.compile(r"tawk\.to", re.I),
    re.compile(r"zendesk\.com", re.I),
    re.compile(r"drift\.com", re.I),
    re.compile(r"livechatinc\.com", re.I),
    re.compile(r"olark\.com", re.I),
    re.compile(r"purechat\.com", re.I),
    re.compile(r"chatbot", re.I),
    re.compile(r"chat-widget", re.I),
    re.compile(r"chat\.js", re.I),
    re.compile(r"widget\.js.*chat", re.I),
]

ASSISTANT_API_PATTERNS = [
    re.compile(r"api\.[^/]+/chat", re.I),
    re.compile(r"api\.[^/]+/assistant", re.I),
    re.compile(r"/api/v\d+/chat", re.I),
    re.compile(r"/api/v\d+/message", re.I),
    re.compile(r"/api/v\d+/bot", re.I),
    re.compile(r"openai\.com", re.I),
    re.compile(r"anthropic\.com", re.I),
    re.compile(r"cohere\.ai", re.I),
    re.compile(r"dialogflow", re.I),
    re.compile(r"rasa\.io", re.I),
]

CMS_FRAMEWORK_PATTERNS = {
    "WordPress": [
        re.compile(r"/wp-content/", re.I),
        re.compile(r"/wp-includes/", re.I),
        re.compile(r"wp-json", re.I),
        re.compile(r"wordpress", re.I),
    ],
    "Drupal": [
        re.compile(r"/sites/default/", re.I),
        re.compile(r"drupal\.js", re.I),
    ],
    "Joomla": [
        re.compile(r"/media/jui/", re.I),
        re.compile(r"joomla", re.I),
    ],
    "Shopify": [
        re.compile(r"cdn\.shopify\.com", re.I),
        re.compile(r"shopify", re.I),
    ],
    "Wix": [
        re.compile(r"static\.wixstatic\.com", re.I),
        re.compile(r"wix\.com", re.I),
    ],
    "Squarespace": [
        re.compile(r"squarespace\.com", re.I),
        re.compile(r"static1\.squarespace\.com", re.I),
    ],
    "React": [
        re.compile(r"react\.js", re.I),
        re.compile(r"react-dom", re.I),
        re.compile(r"__REACT_ROOT__", re.I),
        re.compile(r"data-reactroot", re.I),
    ],
    "Vue": [
        re.compile(r"vue\.js", re.I),
        re.compile(r"vue-router", re.I),
        re.compile(r"__VUE__", re.I),
    ],
    "Next.js": [
        re.compile(r"__NEXT_DATA__", re.I),
        re.compile(r"/_next/static/", re.I),
    ],
    "Nuxt": [
        re.compile(r"__NUXT__", re.I),
        re.compile(r"/_nuxt/", re.I),
    ],
    "Angular": [
        re.compile(r"angular\.js", re.I),
        re.compile(r"ng-app", re.I),
        re.compile(r"@angular", re.I),
    ],
    "Gatsby": [
        re.compile(r"___gatsby", re.I),
        re.compile(r"/gatsby-browser", re.I),
    ],
}

FORM_PATTERNS = [
    re.compile(r"<form", re.I),
    re.compile(r"type=\"email\"", re.I),
    re.compile(r"type=\"tel\"", re.I),
    re.compile(r"contact", re.I),
    re.compile(r"get.in.touch", re.I),
    re.compile(r"reach.out", re.I),
]

AUTH_PATTERNS = [
    re.compile(r"login", re.I),
    re.compile(r"signin", re.I),
    re.compile(r"sign-in", re.I),
    re.compile(r"auth", re.I),
    re.compile(r"account", re.I),
    re.compile(r"password", re.I),
    re.compile(r"register", re.I),
    re.compile(r"signup", re.I),
    re.compile(r"sign-up", re.I),
]

PRODUCT_PATTERNS = [
    re.compile(r"product", re.I),
    re.compile(r"shop", re.I),
    re.compile(r"store", re.I),
    re.compile(r"catalog", re.I),
    re.compile(r"item", re.I),
    re.compile(r"price", re.I),
    re.compile(r"add.to.cart", re.I),
    re.compile(r"buy.now", re.I),
]

CHECKOUT_PATTERNS = [
    re.compile(r"checkout", re.I),
    re.compile(r"cart", re.I),
    re.compile(r"basket", re.I),
    re.compile(r"payment", re.I),
    re.compile(r"billing", re.I),
    re.compile(r"order", re.I),
    re.compile(r"shipping", re.I),
]

BOOKING_PATTERNS = [
    re.compile(r"book", re.I),
    re.compile(r"appointment", re.I),
    re.compile(r"schedule", re.I),
    re.compile(r"reservation", re.I),
    re.compile(r"calendar", re.I),
    re.compile(r"availability", re.I),
]

BLOG_PATTERNS = [
    re.compile(r"blog", re.I),
    re.compile(r"news", re.I),
    re.compile(r"article", re.I),
    re.compile(r"post", re.I),
    re.compile(r"insights", re.I),
    re.compile(r"stories", re.I),
]

PRIVACY_PATTERNS = [
    re.compile(r"privacy", re.I),
    re.compile(r"privacy-policy", re.I),
    re.compile(r"data-protection", re.I),
    re.compile(r"gdpr", re.I),
    re.compile(r"ccpa", re.I),
]

TERMS_PATTERNS = [
    re.compile(r"terms", re.I),
    re.compile(r"terms-of-service", re.I),
    re.compile(r"terms-of-use", re.I),
    re.compile(r"tos", re.I),
    re.compile(r"legal", re.I),
]

PLACEHOLDER_PATTERNS = [
    re.compile(r"coming\s+soon", re.I),
    re.compile(r"under\s+construction", re.I),
    re.compile(r"page\s+not\s+found", re.I),
    re.compile(r"404", re.I),
    re.compile(r"maintenance", re.I),
    re.compile(r"temporarily\s+unavailable", re.I),
]

CORS_RISK_PATTERNS = [
    re.compile(r"fetch\s*\(", re.I),
    re.compile(r"XMLHttpRequest", re.I),
    re.compile(r"axios\.get", re.I),
    re.compile(r"axios\.post", re.I),
    re.compile(r"\.ajax\s*\(", re.I),
]

THIRD_PARTY_SCRIPT_PATTERNS = [
    re.compile(r"google-analytics\.com", re.I),
    re.compile(r"googletagmanager\.com", re.I),
    re.compile(r"facebook\.net", re.I),
    re.compile(r"connect\.facebook\.net", re.I),
    re.compile(r"twitter\.com", re.I),
    re.compile(r"x\.com", re.I),
    re.compile(r"linkedin\.com", re.I),
    re.compile(r"hubspot\.com", re.I),
    re.compile(r"marketo\.net", re.I),
    re.compile(r"segment\.com", re.I),
    re.compile(r"mixpanel\.com", re.I),
    re.compile(r"hotjar\.com", re.I),
    re.compile(r"cloudflare\.com", re.I),
    re.compile(r"jsdelivr\.net", re.I),
    re.compile(r"unpkg\.com", re.I),
    re.compile(r"cdnjs\.cloudflare\.com", re.I),
]

EXCLUDE_RECOMMENDATION_PATTERNS = [
    re.compile(r"/admin", re.I),
    re.compile(r"/wp-admin", re.I),
    re.compile(r"/dashboard", re.I),
    re.compile(r"/cpanel", re.I),
    re.compile(r"/login", re.I),
    re.compile(r"/logout", re.I),
    re.compile(r"/cart", re.I),
    re.compile(r"/checkout", re.I),
    re.compile(r"/api/", re.I),
    re.compile(r"\.pdf$", re.I),
    re.compile(r"\.zip$", re.I),
    re.compile(r"\.exe$", re.I),
]

CUSTOM_BEHAVIOR_FLAGS = [
    (re.compile(r"e-commerce", re.I), "ecommerce_detected"),
    (re.compile(r"membership", re.I), "membership_portal"),
    (re.compile(r"subscription", re.I), "subscription_flow"),
    (re.compile(r"course", re.I), "learning_management"),
    (re.compile(r"forum", re.I), "community_forum"),
    (re.compile(r"support", re.I), "support_portal"),
    (re.compile(r"ticket", re.I), "ticketing_system"),
    (re.compile(r"search", re.I), "site_search_present"),
]


# ---------------------------------------------------------------------------
# PreflightScanner
# ---------------------------------------------------------------------------

class PreflightScanner:
    """
    Lightweight site reconnaissance scanner.
    Faster than full SSI crawl. Produces site_preflight_report.json only.
    """

    def __init__(self, root_url: str, output_dir: str):
        self.root_url = normalize_url(root_url)
        self.output_dir = output_dir
        self.domain = get_domain(self.root_url)
        self.parsed_root = urlparse(self.root_url)
        self.session: Optional[aiohttp.ClientSession] = None
        self.semaphore: Optional[asyncio.Semaphore] = None
        self._start_time: float = 0.0
        self._pages_scanned: int = 0
        self._visited: Set[str] = set()
        self._external_domains: Set[str] = set()
        self._broken_links: List[str] = []
        self._placeholder_pages: List[str] = []
        self._cors_risks: List[str] = []
        self._third_party_scripts: List[str] = []
        self._exclude_recommendations: List[str] = []
        self._custom_behavior_flags: List[str] = []
        self._warnings: List[str] = []
        self._required_custom_steps: List[str] = []

    # -----------------------------------------------------------------------
    # Session helpers
    # -----------------------------------------------------------------------

    async def _init_session(self) -> None:
        timeout = ClientTimeout(total=SSI_CONFIG.get("timeout", 15))
        headers = {
            "User-Agent": SSI_CONFIG.get(
                "user_agent",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36",
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;"
                "q=0.9,image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "DNT": "1",
            "Connection": "keep-alive",
        }
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            headers=headers,
        )
        self.semaphore = asyncio.Semaphore(SSI_CONFIG.get("max_concurrent", 10))

    async def _close_session(self) -> None:
        if self.session:
            await self.session.close()
            self.session = None

    async def _fetch(self, url: str, method: str = "GET") -> Optional[FetchedResponse]:
        if self.session is None:
            return None
        try:
            async with self.semaphore:
                async with self.session.request(method, url, allow_redirects=True) as resp:
                    text = await resp.text()
                    return FetchedResponse(resp.status, text)
        except Exception as exc:
            logger.warning("Fetch failed for %s: %s", url, str(exc))
            return None

    # -----------------------------------------------------------------------
    # Detection helpers
    # -----------------------------------------------------------------------

    def _is_same_domain(self, url: str) -> bool:
        parsed = urlparse(url)
        return parsed.netloc == self.domain or parsed.netloc == ""

    def _is_external(self, url: str) -> bool:
        parsed = urlparse(url)
        return parsed.netloc != "" and parsed.netloc != self.domain

    def _collect_external_domain(self, url: str) -> None:
        parsed = urlparse(url)
        if parsed.netloc and parsed.netloc != self.domain:
            self._external_domains.add(parsed.netloc)

    def _any_pattern(self, text: str, patterns: List[re.Pattern]) -> bool:
        if not text:
            return False
        return any(p.search(text) for p in patterns)

    def _find_patterns(self, text: str, patterns: List[re.Pattern]) -> List[str]:
        if not text:
            return []
        found: List[str] = []
        for p in patterns:
            m = p.search(text)
            if m:
                found.append(m.group(0))
        return found

    def _detect_cms_framework(self, text: str) -> Optional[str]:
        scores: Dict[str, int] = {}
        for cms, patterns in CMS_FRAMEWORK_PATTERNS.items():
            score = sum(1 for p in patterns if p.search(text))
            if score:
                scores[cms] = score
        if not scores:
            return None
        return max(scores, key=scores.get)

    def _detect_chat_widget(self, text: str) -> bool:
        return self._any_pattern(text, CHAT_WIDGET_PATTERNS)

    def _detect_external_assistant_endpoint(self, text: str) -> Optional[str]:
        if not text:
            return None
        for p in ASSISTANT_API_PATTERNS:
            m = p.search(text)
            if m:
                return m.group(0)
        # Look for generic API endpoints in script tags or fetch calls
        api_match = re.search(
            r"""(?:fetch|axios|ajax)\s*\(\s*['"]([^'"]*(?:api|chat|bot|assistant)[^'"]*)['"]""",
            text,
            re.I,
        )
        if api_match:
            candidate = api_match.group(1)
            if candidate.startswith(("http://", "https://")):
                return candidate
        return None

    def _detect_forms(self, text: str, url: str) -> bool:
        return self._any_pattern(text, FORM_PATTERNS)

    def _detect_auth(self, text: str, url: str) -> bool:
        url_match = self._any_pattern(url, AUTH_PATTERNS)
        text_match = self._any_pattern(text, AUTH_PATTERNS)
        return url_match or text_match

    def _detect_products(self, text: str, url: str) -> bool:
        return self._any_pattern(text, PRODUCT_PATTERNS) or self._any_pattern(url, PRODUCT_PATTERNS)

    def _detect_checkout(self, text: str, url: str) -> bool:
        return self._any_pattern(text, CHECKOUT_PATTERNS) or self._any_pattern(url, CHECKOUT_PATTERNS)

    def _detect_booking(self, text: str, url: str) -> bool:
        return self._any_pattern(text, BOOKING_PATTERNS) or self._any_pattern(url, BOOKING_PATTERNS)

    def _detect_blog(self, text: str, url: str) -> bool:
        return self._any_pattern(text, BLOG_PATTERNS) or self._any_pattern(url, BLOG_PATTERNS)

    def _detect_pdfs(self, text: str, url: str) -> bool:
        if url.lower().endswith(".pdf"):
            return True
        return bool(re.search(r"""href=\"[^"]*\.pdf\"""", text, re.I))

    def _detect_privacy(self, text: str, url: str) -> bool:
        return self._any_pattern(url, PRIVACY_PATTERNS) or self._any_pattern(text, PRIVACY_PATTERNS)

    def _detect_terms(self, text: str, url: str) -> bool:
        return self._any_pattern(url, TERMS_PATTERNS) or self._any_pattern(text, TERMS_PATTERNS)

    def _detect_placeholder(self, text: str, url: str) -> bool:
        if self._any_pattern(text, PLACEHOLDER_PATTERNS):
            self._placeholder_pages.append(url)
            return True
        return False

    def _detect_cors_risks(self, text: str, url: str) -> None:
        if self._any_pattern(text, CORS_RISK_PATTERNS):
            # Extract external API calls
            for match in re.finditer(
                r"""(?:fetch|axios\.get|axios\.post|\.ajax)\s*\(\s*['"](https?://[^'"]+)['"]""",
                text,
                re.I,
            ):
                api_url = match.group(1)
                if self._is_external(api_url):
                    self._cors_risks.append(api_url)
                    self._collect_external_domain(api_url)

    def _detect_third_party_scripts(self, text: str, url: str) -> None:
        for p in THIRD_PARTY_SCRIPT_PATTERNS:
            for m in p.finditer(text):
                script_url = m.group(0)
                if script_url not in self._third_party_scripts:
                    self._third_party_scripts.append(script_url)

    def _detect_exclude_recommendations(self, url: str) -> None:
        for p in EXCLUDE_RECOMMENDATION_PATTERNS:
            if p.search(url) and url not in self._exclude_recommendations:
                self._exclude_recommendations.append(url)

    def _detect_custom_behavior_flags(self, text: str, url: str) -> None:
        for pattern, flag in CUSTOM_BEHAVIOR_FLAGS:
            if pattern.search(text) or pattern.search(url):
                if flag not in self._custom_behavior_flags:
                    self._custom_behavior_flags.append(flag)

    # -----------------------------------------------------------------------
    # Page analysis
    # -----------------------------------------------------------------------

    async def _analyze_page(self, url: str, depth: int = 0) -> Dict[str, Any]:
        """Fetch and analyze a single page. Returns detection dict."""
        result: Dict[str, Any] = {
            "url": url,
            "status": None,
            "chat_widget": False,
            "external_assistant_endpoint": None,
            "forms": False,
            "auth": False,
            "products": False,
            "checkout": False,
            "booking": False,
            "blog": False,
            "pdfs": False,
            "privacy": False,
            "terms": False,
            "placeholder": False,
            "links": [],
        }

        if url in self._visited:
            return result
        self._visited.add(url)
        self._pages_scanned += 1

        resp = await self._fetch(url)
        if resp is None:
            if self._is_same_domain(url):
                self._broken_links.append(url)
            result["status"] = 0
            return result

        result["status"] = resp.status

        if resp.status != 200:
            if self._is_same_domain(url):
                self._broken_links.append(url)
            return result

        try:
            text = await resp.text()
        except Exception as exc:
            logger.warning("Failed to read body for %s: %s", url, str(exc))
            text = ""

        result["chat_widget"] = self._detect_chat_widget(text)
        result["external_assistant_endpoint"] = self._detect_external_assistant_endpoint(text)
        result["forms"] = self._detect_forms(text, url)
        result["auth"] = self._detect_auth(text, url)
        result["products"] = self._detect_products(text, url)
        result["checkout"] = self._detect_checkout(text, url)
        result["booking"] = self._detect_booking(text, url)
        result["blog"] = self._detect_blog(text, url)
        result["pdfs"] = self._detect_pdfs(text, url)
        result["privacy"] = self._detect_privacy(text, url)
        result["terms"] = self._detect_terms(text, url)
        result["placeholder"] = self._detect_placeholder(text, url)

        self._detect_cors_risks(text, url)
        self._detect_third_party_scripts(text, url)
        self._detect_exclude_recommendations(url)
        self._detect_custom_behavior_flags(text, url)

        # Extract links for further crawling (same domain only, limited depth)
        if depth < 2:
            links = re.findall(r"""href=\"([^"\s>]+)\"""", text)
            for link in links:
                absolute = urljoin(url, link)
                parsed = urlparse(absolute)
                if parsed.scheme not in ("http", "https"):
                    continue
                if self._is_same_domain(absolute):
                    normalized = absolute.split("#")[0]
                    if normalized not in self._visited:
                        result["links"].append(normalized)
                else:
                    self._collect_external_domain(absolute)

        return result

    # -----------------------------------------------------------------------
    # robots.txt & sitemap.xml
    # -----------------------------------------------------------------------

    async def _check_robots_txt(self) -> Dict[str, Any]:
        result = {"present": False, "disallow_count": 0, "disallow_rules": []}
        url = urljoin(self.root_url, "/robots.txt")
        resp = await self._fetch(url)
        if resp is None or resp.status != 200:
            return result
        result["present"] = True
        try:
            text = await resp.text()
        except Exception:
            return result
        for line in text.splitlines():
            line = line.strip()
            if line.lower().startswith("disallow:"):
                path = line[len("disallow:"):].strip()
                result["disallow_count"] += 1
                result["disallow_rules"].append(path)
        return result

    async def _check_sitemap_xml(self) -> Dict[str, Any]:
        result = {"present": False, "url_count": 0, "urls": []}
        url = urljoin(self.root_url, "/sitemap.xml")
        resp = await self._fetch(url)
        if resp is None or resp.status != 200:
            # Try robots.txt sitemap directive
            robots = await self._check_robots_txt()
            if robots["present"]:
                for line in (await (await self._fetch(urljoin(self.root_url, "/robots.txt"))).text()).splitlines():
                    if line.lower().startswith("sitemap:"):
                        sitemap_url = line[len("sitemap:"):].strip()
                        sitemap_resp = await self._fetch(sitemap_url)
                        if sitemap_resp and sitemap_resp.status == 200:
                            try:
                                sitemap_text = await sitemap_resp.text()
                                urls = re.findall(r"<loc>([^<]+)</loc>", sitemap_text)
                                result["present"] = True
                                result["url_count"] = len(urls)
                                result["urls"] = urls[:50]  # cap stored URLs
                                return result
                            except Exception:
                                pass
            return result
        try:
            text = await resp.text()
        except Exception:
            return result
        result["present"] = True
        urls = re.findall(r"<loc>([^<]+)</loc>", text)
        result["url_count"] = len(urls)
        result["urls"] = urls[:50]
        return result

    # -----------------------------------------------------------------------
    # Install mode logic
    # -----------------------------------------------------------------------

    def _determine_install_mode(
        self,
        has_chat_widget: bool,
        external_assistant: Optional[str],
        cms_framework: Optional[str],
    ) -> str:
        # Check for existing SSI artifacts
        if os.path.isdir(self.output_dir):
            for fname in ("site.skg", "site_context.llmpack", "morb_chunks"):
                artifact_path = os.path.join(self.output_dir, fname)
                if os.path.exists(artifact_path):
                    return "ssi_retrofit"

        if has_chat_widget and external_assistant:
            return "external_orb_wire"
        if has_chat_widget and not external_assistant:
            return "orb_replacement"
        if cms_framework and cms_framework not in ("React", "Vue", "Next.js", "Nuxt", "Angular", "Gatsby"):
            return "custom_api_integration"
        return "full_new_install"

    # -----------------------------------------------------------------------
    # Required custom steps & warnings
    # -----------------------------------------------------------------------

    def _build_custom_steps(
        self,
        has_chat_widget: bool,
        external_assistant: Optional[str],
        has_auth: bool,
        has_checkout: bool,
        has_booking: bool,
        cms_framework: Optional[str],
    ) -> List[str]:
        steps: List[str] = []
        if has_chat_widget and external_assistant:
            steps.append(
                "Wire ORB into existing chat widget via external assistant API endpoint."
            )
        elif has_chat_widget and not external_assistant:
            steps.append(
                "Replace existing chat widget with ORB bubble. Preserve chat history if possible."
            )
        if has_auth:
            steps.append(
                "Configure ORB auth context: do not index login/session pages."
            )
        if has_checkout:
            steps.append(
                "Mark checkout flow as excluded from SSI indexing."
            )
        if has_booking:
            steps.append(
                "Mark booking/scheduling pages as excluded from SSI indexing."
            )
        if cms_framework == "WordPress":
            steps.append(
                "Install ORB WordPress plugin or enqueue ORB script in theme footer."
            )
        elif cms_framework == "Shopify":
            steps.append(
                "Inject ORB script via Shopify theme liquid or app embed."
            )
        elif cms_framework == "Squarespace":
            steps.append(
                "Add ORB script via Squarespace Code Injection header/footer."
            )
        elif cms_framework == "Wix":
            steps.append(
                "Add ORB via Wix Custom Element or Velo backend integration."
            )
        elif cms_framework in ("React", "Next.js", "Vue", "Nuxt", "Angular", "Gatsby"):
            steps.append(
                f"Integrate ORB React/Vue component or script tag into {cms_framework} root layout."
            )
        return steps

    def _build_warnings(
        self,
        broken_links: List[str],
        placeholder_pages: List[str],
        cors_risks: List[str],
        has_auth: bool,
        has_checkout: bool,
    ) -> List[str]:
        warnings: List[str] = []
        if broken_links:
            warnings.append(
                f"Found {len(broken_links)} broken link(s) on same domain."
            )
        if placeholder_pages:
            warnings.append(
                f"Found {len(placeholder_pages)} placeholder/unfinished page(s)."
            )
        if cors_risks:
            warnings.append(
                f"Detected {len(cors_risks)} external API call(s) — review CORS policy before ORB integration."
            )
        if has_auth:
            warnings.append(
                "Auth pages detected — ensure ORB does not expose session data."
            )
        if has_checkout:
            warnings.append(
                "E-commerce checkout detected — PCI scope review recommended before ORB deployment."
            )
        return warnings

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    async def scan(self) -> Dict[str, Any]:
        """
        Run the preflight scan and return the report dict.
        Also writes site_preflight_report.json to output_dir.
        """
        self._start_time = time.time()
        await self._init_session()

        try:
            # Seed crawl from root + sitemap URLs
            sitemap_info = await self._check_sitemap_xml()
            seed_urls: List[str] = [self.root_url]
            if sitemap_info["present"]:
                seed_urls.extend(sitemap_info["urls"][:20])

            # BFS crawl (same domain, limited depth)
            to_scan = list(dict.fromkeys(seed_urls))  # preserve order, dedupe
            page_results: List[Dict[str, Any]] = []

            while to_scan and self._pages_scanned < 50:
                batch = to_scan[:10]
                to_scan = to_scan[10:]
                tasks = [self._analyze_page(url) for url in batch]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for res in results:
                    if isinstance(res, Exception):
                        logger.error("Page analysis error: %s", str(res))
                        continue
                    page_results.append(res)
                    for link in res.get("links", []):
                        if link not in self._visited and link not in to_scan:
                            to_scan.append(link)

            # Aggregate detections
            has_chat_widget = any(r.get("chat_widget") for r in page_results)
            external_assistant = None
            for r in page_results:
                ep = r.get("external_assistant_endpoint")
                if ep:
                    external_assistant = ep
                    break
            cms_framework = None
            for r in page_results:
                cf = self._detect_cms_framework(
                    await (await self._fetch(r["url"])).text()
                    if r["status"] == 200 else ""
                )
                if cf:
                    cms_framework = cf
                    break
            has_forms = any(r.get("forms") for r in page_results)
            has_auth = any(r.get("auth") for r in page_results)
            has_products = any(r.get("products") for r in page_results)
            has_checkout = any(r.get("checkout") for r in page_results)
            has_booking = any(r.get("booking") for r in page_results)
            has_blog = any(r.get("blog") for r in page_results)
            has_pdfs = any(r.get("pdfs") for r in page_results)
            has_privacy = any(r.get("privacy") for r in page_results)
            has_terms = any(r.get("terms") for r in page_results)

            robots_info = await self._check_robots_txt()

            install_mode = self._determine_install_mode(
                has_chat_widget, external_assistant, cms_framework
            )
            custom_steps = self._build_custom_steps(
                has_chat_widget, external_assistant, has_auth, has_checkout, has_booking, cms_framework
            )
            warnings = self._build_warnings(
                self._broken_links, self._placeholder_pages, self._cors_risks, has_auth, has_checkout
            )

            # Deduplicate lists
            self._cors_risks = list(dict.fromkeys(self._cors_risks))
            self._broken_links = list(dict.fromkeys(self._broken_links))
            self._placeholder_pages = list(dict.fromkeys(self._placeholder_pages))
            self._third_party_scripts = list(dict.fromkeys(self._third_party_scripts))
            self._external_domains = sorted(self._external_domains)
            self._exclude_recommendations = list(dict.fromkeys(self._exclude_recommendations))
            self._custom_behavior_flags = list(dict.fromkeys(self._custom_behavior_flags))

            scan_duration = round(time.time() - self._start_time, 2)

            # Confidence score
            confidence = 0.5
            if self._pages_scanned >= 10:
                confidence += 0.2
            if sitemap_info["present"]:
                confidence += 0.1
            if robots_info["present"]:
                confidence += 0.1
            if cms_framework:
                confidence += 0.1
            confidence = round(min(confidence, 1.0), 2)

            report: Dict[str, Any] = {
                "site_url": self.root_url,
                "scan_timestamp": datetime.now(timezone.utc).isoformat(),
                "scan_duration": scan_duration,
                "detected": {
                    "existing_chat_widget": has_chat_widget,
                    "external_assistant_endpoint": external_assistant,
                    "cms_framework": cms_framework or "unknown",
                    "has_contact_form": has_forms,
                    "has_auth_pages": has_auth,
                    "has_products": has_products,
                    "has_checkout": has_checkout,
                    "has_booking": has_booking,
                    "has_blog": has_blog,
                    "has_pdfs": has_pdfs,
                    "robots_txt": robots_info["present"],
                    "robots_disallow_count": robots_info["disallow_count"],
                    "sitemap_xml": sitemap_info["present"],
                    "sitemap_url_count": sitemap_info["url_count"],
                    "cors_risks": self._cors_risks,
                    "broken_links": self._broken_links,
                    "placeholder_pages": self._placeholder_pages,
                    "privacy_page": has_privacy,
                    "terms_page": has_terms,
                    "external_domains": self._external_domains,
                    "third_party_scripts": self._third_party_scripts,
                    "exclude_recommendations": self._exclude_recommendations,
                    "custom_behavior_flags": self._custom_behavior_flags,
                },
                "recommended_install_mode": install_mode,
                "required_custom_steps": custom_steps,
                "warnings": warnings,
                "pages_scanned": self._pages_scanned,
                "confidence": confidence,
            }

            # Write report
            os.makedirs(self.output_dir, exist_ok=True)
            report_path = os.path.join(self.output_dir, "site_preflight_report.json")
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

            logger.info("Preflight scan complete. Report saved to %s", report_path)
            return report

        finally:
            await self._close_session()
