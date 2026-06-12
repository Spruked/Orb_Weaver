import asyncio
import aiohttp
import time
import json
from urllib.parse import urljoin, urlparse, urldefrag
from bs4 import BeautifulSoup
from typing import Set, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import hashlib
import re
from collections import Counter
from xml.etree import ElementTree as ET

from app.core.config import settings

@dataclass
class PageData:
    url: str
    title: Optional[str] = None
    meta_description: Optional[str] = None
    h1: Optional[str] = None
    h2_tags: List[str] = field(default_factory=list)
    word_count: int = 0
    status_code: Optional[int] = None
    load_time_ms: Optional[float] = None
    canonical_url: Optional[str] = None
    robots_meta: Optional[str] = None
    schema_markup: List[Dict] = field(default_factory=list)
    internal_links: int = 0
    external_links: int = 0
    images_count: int = 0
    images_without_alt: int = 0
    ssl_enabled: bool = False
    content_hash: Optional[str] = None
    redirect_chain: List[str] = field(default_factory=list)
    is_indexable: bool = True
    has_sitemap: bool = False
    has_robots_txt: bool = False
    mobile_viewport: bool = False
    open_graph: Dict = field(default_factory=dict)
    twitter_cards: Dict = field(default_factory=dict)
    heading_structure: List[Dict] = field(default_factory=list)
    duplicate_content_risk: bool = False
    semantic_analysis: Dict = field(default_factory=dict)
    schema_analysis: Dict = field(default_factory=dict)
    internal_link_targets: List[Dict] = field(default_factory=list)
    entity_analysis: Dict = field(default_factory=dict)
    mobile_ux_analysis: Dict = field(default_factory=dict)
    template_signature: Optional[str] = None
    crawl_depth: int = 0

    def to_dict(self) -> Dict:
        return {
            'url': self.url,
            'title': self.title,
            'meta_description': self.meta_description,
            'h1': self.h1,
            'h2_tags': self.h2_tags,
            'word_count': self.word_count,
            'status_code': self.status_code,
            'load_time_ms': self.load_time_ms,
            'canonical_url': self.canonical_url,
            'robots_meta': self.robots_meta,
            'schema_markup': self.schema_markup,
            'internal_links': self.internal_links,
            'external_links': self.external_links,
            'images_count': self.images_count,
            'images_without_alt': self.images_without_alt,
            'ssl_enabled': self.ssl_enabled,
            'content_hash': self.content_hash,
            'is_indexable': self.is_indexable,
            'has_sitemap': self.has_sitemap,
            'has_robots_txt': self.has_robots_txt,
            'mobile_viewport': self.mobile_viewport,
            'open_graph': self.open_graph,
            'twitter_cards': self.twitter_cards,
            'heading_structure': self.heading_structure,
            'duplicate_content_risk': self.duplicate_content_risk,
            'semantic_analysis': self.semantic_analysis,
            'schema_analysis': self.schema_analysis,
            'internal_link_targets': self.internal_link_targets,
            'entity_analysis': self.entity_analysis,
            'mobile_ux_analysis': self.mobile_ux_analysis,
            'template_signature': self.template_signature,
            'crawl_depth': self.crawl_depth
        }

class OrbWeaverCrawler:
    def __init__(self, max_pages: int = None, delay: float = None, max_depth: int = None, progress_callback=None):
        self.max_pages = max_pages or settings.CRAWL_MAX_PAGES
        self.delay = delay or settings.CRAWL_DELAY
        self.max_depth = max_depth or settings.CRAWL_MAX_DEPTH
        self.progress_callback = progress_callback
        self.last_progress_emit = 0.0
        self.timeout = aiohttp.ClientTimeout(total=settings.CRAWL_TIMEOUT)
        self.user_agent = settings.CRAWL_USER_AGENT
        self.respect_robots = settings.CRAWL_RESPECT_ROBOTS

        self.visited_urls: Set[str] = set()
        self.discovered_urls: Set[str] = set()
        self.crawled_data: List[PageData] = []
        self.domain: Optional[str] = None
        self.domain_key: Optional[str] = None
        self.robots_rules: Optional[str] = None
        self.sitemap_urls: Set[str] = set()
        self.sitemap_indexes: Set[str] = set()
        self.depth_limit_hits = 0
        self.max_page_limit_hit = False

    def _emit_progress(self, force: bool = False) -> None:
        if not self.progress_callback:
            return
        now = time.time()
        if not force and now - self.last_progress_emit < 1:
            return
        self.last_progress_emit = now
        self.progress_callback(self)

    def _normalize_url(self, url: str) -> str:
        url, _ = urldefrag(url)
        return url.rstrip('/')

    def _is_same_domain(self, url: str) -> bool:
        parsed = urlparse(url)
        return self._domain_key(parsed.netloc) == self.domain_key

    def _domain_key(self, netloc: str) -> str:
        host = netloc.lower().split("@")[-1].split(":")[0]
        return host[4:] if host.startswith("www.") else host

    async def _collect_sitemap_urls(self, session: aiohttp.ClientSession, sitemap_url: str, remaining_depth: int = 2) -> None:
        normalized_sitemap = self._normalize_url(sitemap_url)
        if remaining_depth < 0 or normalized_sitemap in self.sitemap_indexes:
            return

        self.sitemap_indexes.add(normalized_sitemap)
        try:
            async with session.get(sitemap_url, ssl=False) as resp:
                if resp.status != 200:
                    return
                sitemap_content = await resp.text()
        except Exception:
            return

        try:
            root = ET.fromstring(sitemap_content)
        except ET.ParseError:
            return

        root_name = root.tag.rsplit("}", 1)[-1].lower()
        locs = [
            (node.text or "").strip()
            for node in root.iter()
            if node.tag.rsplit("}", 1)[-1].lower() == "loc" and node.text
        ]

        if root_name == "sitemapindex":
            for child_sitemap in locs:
                if child_sitemap and self._is_same_domain(child_sitemap):
                    await self._collect_sitemap_urls(session, child_sitemap, remaining_depth - 1)
            return

        for page_url in locs:
            if page_url and self._is_same_domain(page_url):
                normalized_page = self._normalize_url(page_url)
                self.sitemap_urls.add(normalized_page)
                self.discovered_urls.add(normalized_page)
        self._emit_progress()

    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> Tuple[Set[str], Set[str], List[Dict]]:
        internal = set()
        external = set()
        internal_targets = []

        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.startswith(('mailto:', 'tel:', 'javascript:')):
                continue
            full_url = urljoin(base_url, href)
            normalized = self._normalize_url(full_url)
            anchor = link.get_text(" ", strip=True)[:120]

            if self._is_same_domain(normalized):
                internal.add(normalized)
                internal_targets.append({
                    'url': normalized,
                    'anchor': anchor,
                    'nofollow': 'nofollow' in (link.get('rel') or [])
                })
            else:
                external.add(normalized)

        return internal, external, internal_targets

    def _extract_schema_markup(self, soup: BeautifulSoup) -> List[Dict]:
        schemas = []

        # JSON-LD
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string or "{}")
                schemas.append({
                    'type': 'json-ld',
                    'data': data
                })
            except Exception as exc:
                schemas.append({
                    'type': 'json-ld',
                    'error': str(exc)[:200]
                })

        # Microdata
        for tag in soup.find_all(attrs={"itemscope": True}):
            itemtype = tag.get('itemtype', '')
            if itemtype:
                schemas.append({
                    'type': 'microdata',
                    'itemtype': itemtype
                })

        return schemas

    def _analyze_schema_markup(self, schemas: List[Dict]) -> Dict:
        schema_types = []
        invalid = []
        recommended = {'Organization', 'WebSite', 'WebPage', 'BreadcrumbList', 'Article', 'Product', 'FAQPage'}

        def collect_types(value):
            if isinstance(value, dict):
                raw_type = value.get('@type') or value.get('type')
                if isinstance(raw_type, list):
                    schema_types.extend(str(item) for item in raw_type)
                elif raw_type:
                    schema_types.append(str(raw_type))
                for nested in ('@graph', 'itemListElement', 'mainEntity'):
                    collect_types(value.get(nested))
            elif isinstance(value, list):
                for item in value:
                    collect_types(item)

        for schema in schemas:
            if schema.get('error'):
                invalid.append(schema['error'])
                continue
            collect_types(schema.get('data'))
            if schema.get('itemtype'):
                schema_types.append(str(schema['itemtype']).rstrip('/').split('/')[-1])

        unique_types = sorted(set(schema_types))
        return {
            'count': len(schemas),
            'types': unique_types,
            'json_ld_count': sum(1 for s in schemas if s.get('type') == 'json-ld'),
            'microdata_count': sum(1 for s in schemas if s.get('type') == 'microdata'),
            'invalid_count': len(invalid),
            'errors': invalid[:5],
            'recommended_missing': sorted(recommended - set(unique_types))[:5]
        }

    def _extract_open_graph(self, soup: BeautifulSoup) -> Dict:
        og = {}
        for tag in soup.find_all('meta', property=lambda x: x and x.startswith('og:')):
            og[tag['property']] = tag.get('content', '')
        return og

    def _extract_twitter_cards(self, soup: BeautifulSoup) -> Dict:
        tc = {}
        for tag in soup.find_all('meta', attrs={'name': lambda x: x and x.startswith('twitter:')}):
            tc[tag['name']] = tag.get('content', '')
        return tc

    def _analyze_heading_structure(self, soup: BeautifulSoup) -> Tuple[Optional[str], List[str], List[Dict]]:
        h1 = soup.find('h1')
        h1_text = h1.get_text(strip=True) if h1 else None

        h2_tags = []
        for h2 in soup.find_all('h2'):
            text = h2.get_text(strip=True)
            if text:
                h2_tags.append(text)

        heading_structure = []
        for i in range(1, 7):
            tags = soup.find_all(f'h{i}')
            for tag in tags:
                heading_structure.append({
                    'level': i,
                    'text': tag.get_text(strip=True)[:100]
                })

        return h1_text, h2_tags, heading_structure

    def _count_words(self, text: str) -> int:
        words = re.findall(r'\b\w+\b', text.lower())
        return len(words)

    def _semantic_analysis(self, text: str, title: Optional[str], h1: Optional[str], h2_tags: List[str]) -> Dict:
        stop_words = {
            'the', 'and', 'for', 'that', 'with', 'this', 'from', 'your', 'you', 'are', 'not', 'have',
            'has', 'was', 'were', 'will', 'can', 'our', 'all', 'but', 'about', 'into', 'than', 'then',
            'them', 'they', 'their', 'its', 'his', 'her', 'who', 'what', 'when', 'where', 'why', 'how',
            'page', 'home', 'contact', 'privacy', 'terms', 'blog', 'read', 'more', 'learn'
        }
        words = re.findall(r'\b[a-zA-Z][a-zA-Z0-9-]{2,}\b', text.lower())
        filtered = [word for word in words if word not in stop_words]
        counts = Counter(filtered)
        sentences = [s for s in re.split(r'[.!?]+', text) if s.strip()]
        avg_sentence_words = round(len(words) / len(sentences), 1) if sentences else 0
        unique_ratio = round((len(set(filtered)) / len(filtered)) * 100, 1) if filtered else 0
        keyword_source = " ".join([title or "", h1 or "", " ".join(h2_tags)])
        heading_terms = set(re.findall(r'\b[a-zA-Z][a-zA-Z0-9-]{2,}\b', keyword_source.lower()))
        top_terms = [{'term': term, 'count': count} for term, count in counts.most_common(12)]
        topical_overlap = [term for term, _count in counts.most_common(20) if term in heading_terms]
        orb_score = self._orb_semantic_score(
            text=text,
            title=title,
            h1=h1,
            h2_tags=h2_tags,
            filtered_words=filtered,
            counts=counts,
            heading_terms=heading_terms,
            avg_sentence_words=avg_sentence_words,
            question_count=text.count('?')
        )

        return {
            'top_terms': top_terms,
            'unique_term_ratio': unique_ratio,
            'avg_sentence_words': avg_sentence_words,
            'heading_term_overlap': topical_overlap[:10],
            'question_count': text.count('?'),
            'semantic_depth': 'strong' if len(filtered) >= 900 and unique_ratio >= 35 else 'moderate' if len(filtered) >= 300 else 'thin',
            'orb_semantic_score': orb_score
        }

    def _orb_semantic_score(
        self,
        text: str,
        title: Optional[str],
        h1: Optional[str],
        h2_tags: List[str],
        filtered_words: List[str],
        counts: Counter,
        heading_terms: Set[str],
        avg_sentence_words: float,
        question_count: int
    ) -> Dict:
        topic = h1 or title or "this page"
        topic_terms = [term for term in heading_terms if len(term) > 2]
        expected_terms = set(topic_terms)

        common_terms = [term for term, _count in counts.most_common(40)]
        expected_terms.update(common_terms[:10])
        expected_terms.update(term for heading in h2_tags for term in re.findall(r'\b[a-zA-Z][a-zA-Z0-9-]{2,}\b', heading.lower()))
        expected_terms = {term for term in expected_terms if term not in {'and', 'the', 'for', 'with'}}

        covered_expected = {term for term in expected_terms if counts.get(term, 0) >= 2 or term in topic_terms}
        topical_completeness = self._bounded_percent((len(covered_expected) / len(expected_terms)) * 100 if expected_terms else 0)

        word_count = len(filtered_words)
        unique_ratio = (len(set(filtered_words)) / word_count) * 100 if word_count else 0
        semantic_depth = self._bounded_percent(min(word_count / 900, 1) * 55 + min(unique_ratio / 45, 1) * 45)

        entities = self._extract_entities(text)
        entity_hits = [entity for entity in entities if entity.lower() in text.lower()]
        entity_coverage = self._bounded_percent(min(len(entity_hits) / 12, 1) * 100)

        qa_density = self._question_answer_density(text, question_count, word_count)
        readability_balance = self._readability_expertise_balance(avg_sentence_words, word_count, len(entities), unique_ratio)

        overall = self._bounded_percent(
            topical_completeness * 0.30 +
            semantic_depth * 0.25 +
            entity_coverage * 0.20 +
            qa_density * 0.15 +
            readability_balance * 0.10
        )

        return {
            'overall': overall,
            'topical_completeness': topical_completeness,
            'semantic_depth': semantic_depth,
            'entity_coverage': entity_coverage,
            'question_answer_density': qa_density,
            'readability_expertise_balance': readability_balance,
            'topic': topic,
            'expected_terms': sorted(expected_terms)[:40],
            'covered_terms': sorted(covered_expected)[:40],
            'entities': entities[:25],
            'reasoning_statement': f"Your article covers {overall}% of the expected semantic space for '{topic}'."
        }

    def _extract_entities(self, text: str) -> List[str]:
        candidates = re.findall(r'\b(?:[A-Z][a-zA-Z0-9-]{2,})(?:\s+[A-Z][a-zA-Z0-9-]{2,}){0,3}\b', text)
        ignored = {'Home', 'Contact', 'Privacy Policy', 'Terms', 'Read More'}
        counts = Counter(candidate.strip() for candidate in candidates if candidate.strip() not in ignored)
        return [entity for entity, _count in counts.most_common(30)]

    async def _entity_analysis(self, session: aiohttp.ClientSession, text: str, schema_analysis: Dict) -> Dict:
        entities = self._extract_entities(text)
        people = [e for e in entities if len(e.split()) >= 2 and not any(token in e for token in ('Inc', 'LLC', 'Company', 'Group', 'University'))]
        organizations = [e for e in entities if any(token in e for token in ('Inc', 'LLC', 'Company', 'Group', 'University', 'Association', 'Agency', 'Corp'))]
        locations = [e for e in entities if re.search(r'\b(City|County|State|Texas|Oklahoma|California|Florida|New York|USA|United States)\b', e)]
        products = [e for e in entities if re.search(r'\b(Plan|Pro|Plus|App|Software|Service|Product|Kit|Tool|System)\b', e)]
        schema_entities = schema_analysis.get('types', [])
        deterministic = {
            'named_entities': entities,
            'people': people[:15],
            'organizations': organizations[:15],
            'locations': locations[:15],
            'product_names': products[:15],
            'schema_org_entities': schema_entities,
            'source': 'deterministic-local'
        }
        llm_entities = await self._local_llm_entities(session, text[:6000])
        if not llm_entities:
            return deterministic
        return {
            **deterministic,
            **{key: llm_entities.get(key, deterministic.get(key, [])) for key in ('named_entities', 'people', 'organizations', 'locations', 'product_names')},
            'schema_org_entities': sorted(set(schema_entities + llm_entities.get('schema_org_entities', []))),
            'source': 'local-llm'
        }

    async def _local_llm_entities(self, session: aiohttp.ClientSession, text: str) -> Optional[Dict]:
        if not settings.LOCAL_LLM_URL or not settings.LOCAL_LLM_MODEL:
            return None
        prompt = (
            "Extract SEO knowledge graph entities from the page text. "
            "Return strict JSON with keys named_entities, product_names, locations, people, organizations, schema_org_entities. "
            f"Text:\n{text}"
        )
        try:
            async with session.post(
                settings.LOCAL_LLM_URL,
                json={
                    "model": settings.LOCAL_LLM_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                },
                ssl=False,
            ) as response:
                payload = await response.json()
                raw = payload.get("response") if isinstance(payload, dict) else None
                data = json.loads(raw) if isinstance(raw, str) else payload
                if isinstance(data, dict):
                    return {
                        key: [str(item) for item in data.get(key, []) if item]
                        for key in ("named_entities", "product_names", "locations", "people", "organizations", "schema_org_entities")
                    }
        except Exception:
            return None
        return None

    def _mobile_ux_analysis(self, soup: BeautifulSoup) -> Dict:
        viewport = soup.find('meta', attrs={'name': 'viewport'})
        viewport_content = viewport.get('content', '') if viewport else ''
        tap_candidates = soup.find_all(['a', 'button', 'input', 'select', 'textarea'])
        small_tap_targets = 0
        for tag in tap_candidates:
            style = tag.get('style', '')
            width = self._style_px(style, 'width')
            height = self._style_px(style, 'height')
            if (width and width < 44) or (height and height < 44):
                small_tap_targets += 1

        font_sizes = []
        for tag in soup.find_all(style=True):
            size = self._style_px(tag.get('style', ''), 'font-size')
            if size:
                font_sizes.append(size)
        small_fonts = sum(1 for size in font_sizes if size < 16)
        layout_shift_risk = sum(1 for img in soup.find_all('img') if not img.get('width') or not img.get('height'))
        score = 100
        if 'width=device-width' not in viewport_content:
            score -= 25
        score -= min(small_tap_targets * 4, 25)
        score -= min(small_fonts * 2, 20)
        score -= min(layout_shift_risk * 3, 25)

        return {
            'score': self._bounded_percent(score),
            'viewport_scaling': 'responsive' if 'width=device-width' in viewport_content else 'missing_or_fixed',
            'tap_target_count': len(tap_candidates),
            'small_tap_targets': small_tap_targets,
            'font_rules_checked': len(font_sizes),
            'small_font_rules': small_fonts,
            'mobile_cls_risk_elements': layout_shift_risk,
            'screenshot_capture': 'not_configured'
        }

    def _style_px(self, style: str, property_name: str) -> Optional[float]:
        match = re.search(rf'{re.escape(property_name)}\s*:\s*([0-9.]+)px', style, flags=re.I)
        return float(match.group(1)) if match else None

    def _template_signature(self, soup: BeautifulSoup, text: str) -> str:
        tag_path = []
        for tag in soup.find_all(['header', 'nav', 'main', 'article', 'section', 'aside', 'footer', 'h1', 'h2', 'p', 'form'])[:120]:
            classes = ' '.join(tag.get('class', [])[:3]) if isinstance(tag.get('class'), list) else ''
            tag_path.append(f"{tag.name}:{classes}")
        boilerplate = re.sub(r'\s+', ' ', text.lower())[:2000]
        return hashlib.sha256(("|".join(tag_path) + boilerplate[:500]).encode()).hexdigest()[:32]

    def _question_answer_density(self, text: str, question_count: int, word_count: int) -> int:
        if word_count == 0:
            return 0
        answer_markers = len(re.findall(r'\b(because|therefore|first|second|how|why|what|when|where|steps?|answer|solution|example)\b', text.lower()))
        question_score = min(question_count / 6, 1) * 45
        answer_score = min(answer_markers / 18, 1) * 55
        return self._bounded_percent(question_score + answer_score)

    def _readability_expertise_balance(self, avg_sentence_words: float, word_count: int, entity_count: int, unique_ratio: float) -> int:
        if word_count == 0:
            return 0
        readability = 100 - min(abs(avg_sentence_words - 18) * 4, 70)
        expertise = min(entity_count / 12, 1) * 45 + min(unique_ratio / 42, 1) * 55
        return self._bounded_percent(readability * 0.45 + expertise * 0.55)

    def _bounded_percent(self, value: float) -> int:
        return int(round(max(0, min(100, value))))

    def _generate_content_hash(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()[:32]

    def _check_robots_txt(self, url: str) -> bool:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        return robots_url

    async def _fetch_page(self, session: aiohttp.ClientSession, url: str) -> Tuple[Optional[str], Optional[int], Optional[float], List[str]]:
        start_time = time.time()
        redirects = []

        try:
            async with session.get(url, allow_redirects=True, ssl=False) as response:
                load_time = (time.time() - start_time) * 1000

                # Track redirects
                if response.history:
                    for resp in response.history:
                        redirects.append(str(resp.url))

                if response.status == 200:
                    text = await response.text()
                    return text, response.status, load_time, redirects
                else:
                    return None, response.status, load_time, redirects

        except asyncio.TimeoutError:
            return None, 408, (time.time() - start_time) * 1000, redirects
        except Exception as e:
            return None, 0, None, redirects

    async def _crawl_page(self, session: aiohttp.ClientSession, url: str, depth: int = 0) -> Optional[PageData]:
        normalized_url = self._normalize_url(url)
        self.discovered_urls.add(normalized_url)

        if depth > self.max_depth:
            self.depth_limit_hits += 1
            return None

        if len(self.visited_urls) >= self.max_pages:
            self.max_page_limit_hit = True
            return None

        if normalized_url in self.visited_urls:
            return None

        self.visited_urls.add(normalized_url)

        # Respect crawl delay
        await asyncio.sleep(self.delay)

        html, status_code, load_time, redirects = await self._fetch_page(session, url)

        if html is None:
            return PageData(
                url=url,
                status_code=status_code,
                load_time_ms=load_time,
                redirect_chain=redirects
            )

        soup = BeautifulSoup(html, 'lxml')
        text_content = soup.get_text(separator=' ', strip=True)

        # Extract data
        h1, h2_tags, heading_structure = self._analyze_heading_structure(soup)
        internal_links, external_links, internal_link_targets = self._extract_links(soup, url)
        schema_markup = self._extract_schema_markup(soup)
        schema_analysis = self._analyze_schema_markup(schema_markup)
        entity_analysis = await self._entity_analysis(session, text_content, schema_analysis)
        mobile_ux_analysis = self._mobile_ux_analysis(soup)
        template_signature = self._template_signature(soup, text_content)
        og_data = self._extract_open_graph(soup)
        twitter_data = self._extract_twitter_cards(soup)

        # Image analysis
        images = soup.find_all('img')
        images_without_alt = sum(1 for img in images if not img.get('alt'))

        # Meta tags
        title_tag = soup.find('title')
        title = title_tag.get_text(strip=True) if title_tag else None

        meta_desc = soup.find('meta', attrs={'name': 'description'})
        meta_description = meta_desc.get('content', '') if meta_desc else None

        canonical = soup.find('link', rel='canonical')
        canonical_url = canonical.get('href') if canonical else None

        robots = soup.find('meta', attrs={'name': 'robots'})
        robots_meta = robots.get('content') if robots else None

        viewport = soup.find('meta', attrs={'name': 'viewport'})
        mobile_viewport = bool(viewport)

        # Check SSL
        parsed = urlparse(url)
        ssl_enabled = parsed.scheme == 'https'

        # Check indexability
        is_indexable = True
        if robots_meta:
            if 'noindex' in robots_meta.lower():
                is_indexable = False

        page_data = PageData(
            url=url,
            title=title,
            meta_description=meta_description,
            h1=h1,
            h2_tags=h2_tags,
            word_count=self._count_words(text_content),
            status_code=status_code,
            load_time_ms=load_time,
            canonical_url=canonical_url,
            robots_meta=robots_meta,
            schema_markup=schema_markup,
            internal_links=len(internal_links),
            external_links=len(external_links),
            images_count=len(images),
            images_without_alt=images_without_alt,
            ssl_enabled=ssl_enabled,
            content_hash=self._generate_content_hash(text_content[:1000]),
            redirect_chain=redirects,
            is_indexable=is_indexable,
            mobile_viewport=mobile_viewport,
            open_graph=og_data,
            twitter_cards=twitter_data,
            heading_structure=heading_structure,
            semantic_analysis=self._semantic_analysis(text_content, title, h1, h2_tags),
            schema_analysis=schema_analysis,
            internal_link_targets=internal_link_targets,
            entity_analysis=entity_analysis,
            mobile_ux_analysis=mobile_ux_analysis,
            template_signature=template_signature,
            crawl_depth=depth
        )

        self.crawled_data.append(page_data)
        self._emit_progress()

        # Add internal links to queue
        for link in internal_links:
            normalized_link = self._normalize_url(link)
            self.discovered_urls.add(normalized_link)
            if normalized_link not in self.visited_urls and len(self.visited_urls) < self.max_pages:
                await self._crawl_page(session, link, depth + 1)
            elif normalized_link not in self.visited_urls and len(self.visited_urls) >= self.max_pages:
                self.max_page_limit_hit = True

        return page_data

    def _resolve_seed_urls(self, start_url: str, seed_urls: Optional[List[str]] = None) -> List[str]:
        resolved = []
        seen = set()
        for seed in seed_urls or []:
            raw_seed = (seed or "").strip()
            if not raw_seed:
                continue
            seed_url = urljoin(start_url.rstrip("/") + "/", raw_seed)
            normalized = self._normalize_url(seed_url)
            if normalized in seen or not self._is_same_domain(normalized):
                continue
            seen.add(normalized)
            resolved.append(normalized)
            self.discovered_urls.add(normalized)
        return resolved

    async def crawl(self, start_url: str, seed_urls: Optional[List[str]] = None) -> List[PageData]:
        parsed = urlparse(start_url)
        self.domain = parsed.netloc
        self.domain_key = self._domain_key(parsed.netloc)
        context_seed_urls = self._resolve_seed_urls(start_url, seed_urls)

        # Check for sitemap and robots.txt
        async with aiohttp.ClientSession(
            timeout=self.timeout,
            headers={'User-Agent': self.user_agent}
        ) as session:

            # Check robots.txt
            robots_url = self._check_robots_txt(start_url)
            try:
                async with session.get(robots_url, ssl=False) as resp:
                    if resp.status == 200:
                        self.robots_rules = await resp.text()
            except:
                pass

            # Check sitemap.xml
            sitemap_url = f"{parsed.scheme}://{parsed.netloc}/sitemap.xml"
            await self._collect_sitemap_urls(session, sitemap_url)
            self._emit_progress(force=True)

            # Start crawling
            await self._crawl_page(session, start_url)
            for seed_url in context_seed_urls:
                if len(self.visited_urls) >= self.max_pages:
                    self.max_page_limit_hit = True
                    break
                await self._crawl_page(session, seed_url, 0)
            for sitemap_url in sorted(self.sitemap_urls):
                if len(self.visited_urls) >= self.max_pages:
                    self.max_page_limit_hit = True
                    break
                if sitemap_url and self._is_same_domain(sitemap_url):
                    await self._crawl_page(session, sitemap_url, 0)
            self._emit_progress(force=True)

        # Post-processing: detect duplicate content
        content_hashes = {}
        for page in self.crawled_data:
            if page.content_hash in content_hashes:
                page.duplicate_content_risk = True
                content_hashes[page.content_hash].duplicate_content_risk = True
            else:
                content_hashes[page.content_hash] = page

        # Mark sitemap presence
        for page in self.crawled_data:
            page.has_sitemap = len(self.sitemap_urls) > 0
            page.has_robots_txt = self.robots_rules is not None

        return self.crawled_data

    def get_crawl_stats(self) -> Dict:
        discovered_count = len(self.discovered_urls)
        crawled_count = len(self.crawled_data)
        visited_count = len(self.visited_urls)
        skipped_estimate = max(discovered_count - visited_count, 0)
        return {
            'total_pages': len(self.crawled_data),
            'visited_urls': len(self.visited_urls),
            'discovered_urls': discovered_count,
            'pages_skipped_estimate': skipped_estimate,
            'sitemap_urls_found': len(self.sitemap_urls),
            'sitemap_indexes_found': len(self.sitemap_indexes),
            'has_robots_txt': self.robots_rules is not None,
            'queue_exhausted': not self.max_page_limit_hit and self.depth_limit_hits == 0 and skipped_estimate == 0,
            'max_page_limit_hit': self.max_page_limit_hit,
            'depth_limit_hit': self.depth_limit_hits > 0,
            'depth_limit_hits': self.depth_limit_hits,
            'max_pages_configured': self.max_pages,
            'max_depth_configured': self.max_depth,
            'host_normalization': {
                'input_host': self.domain,
                'canonical_host_key': self.domain_key,
                'www_equivalent': True
            },
            'avg_load_time': sum(p.load_time_ms for p in self.crawled_data if p.load_time_ms) / len([p for p in self.crawled_data if p.load_time_ms]) if any(p.load_time_ms for p in self.crawled_data) else 0,
            'ssl_pages': sum(1 for p in self.crawled_data if p.ssl_enabled),
            'indexable_pages': sum(1 for p in self.crawled_data if p.is_indexable),
            'duplicate_content_pages': sum(1 for p in self.crawled_data if p.duplicate_content_risk),
            'total_images': sum(p.images_count for p in self.crawled_data),
            'images_missing_alt': sum(p.images_without_alt for p in self.crawled_data),
            'total_internal_links': sum(p.internal_links for p in self.crawled_data),
            'total_external_links': sum(p.external_links for p in self.crawled_data),
            'schema_pages': sum(1 for p in self.crawled_data if p.schema_markup),
            'schema_errors': sum(p.schema_analysis.get('invalid_count', 0) for p in self.crawled_data),
            'semantic_thin_pages': sum(1 for p in self.crawled_data if p.semantic_analysis.get('semantic_depth') == 'thin'),
            'internal_link_edges': sum(len(p.internal_link_targets) for p in self.crawled_data),
            'avg_orb_semantic_score': sum(p.semantic_analysis.get('orb_semantic_score', {}).get('overall', 0) for p in self.crawled_data) / len(self.crawled_data) if self.crawled_data else 0,
            'low_orb_semantic_pages': sum(1 for p in self.crawled_data if p.semantic_analysis.get('orb_semantic_score', {}).get('overall', 0) < 65),
            'avg_mobile_ux_score': sum(p.mobile_ux_analysis.get('score', 0) for p in self.crawled_data) / len(self.crawled_data) if self.crawled_data else 0,
            'mobile_ux_problem_pages': sum(1 for p in self.crawled_data if p.mobile_ux_analysis.get('score', 100) < 70)
        }
