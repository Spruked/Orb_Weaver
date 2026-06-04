from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from app.crawler.engine import PageData
from app.core.config import settings

@dataclass
class SEOIssue:
    severity: str  # critical, warning, opportunity
    category: str  # technical, content, on-page, performance, security
    title: str
    description: str
    affected_urls: List[str] = field(default_factory=list)
    recommendation: str = ""
    impact_score: int = 0  # 1-100

    def to_dict(self) -> Dict:
        return {
            'severity': self.severity,
            'category': self.category,
            'title': self.title,
            'description': self.description,
            'affected_urls': self.affected_urls[:10],  # Limit for display
            'recommendation': self.recommendation,
            'impact_score': self.impact_score
        }

@dataclass
class AuditScore:
    overall: float = 0.0
    seo: float = 0.0
    performance: float = 0.0
    accessibility: float = 0.0
    content: float = 0.0
    technical: float = 0.0
    mobile: float = 0.0
    security: float = 0.0
    authority: float = 0.0
    schema: float = 0.0

    def to_dict(self) -> Dict:
        return {
            'overall': round(self.overall, 1),
            'seo': round(self.seo, 1),
            'performance': round(self.performance, 1),
            'accessibility': round(self.accessibility, 1),
            'content': round(self.content, 1),
            'technical': round(self.technical, 1),
            'mobile': round(self.mobile, 1),
            'security': round(self.security, 1),
            'authority': round(self.authority, 1),
            'schema': round(self.schema, 1)
        }

class SEOAuditor:
    def __init__(self):
        self.issues: List[SEOIssue] = []
        self.scores = AuditScore()

    def _add_issue(self, issue: SEOIssue):
        self.issues.append(issue)

    def _check_title_tags(self, pages: List[PageData]) -> Tuple[float, List[SEOIssue]]:
        issues = []
        total_score = 100
        affected = []

        for page in pages:
            if not page.title:
                affected.append(page.url)
                total_score -= 5
            elif len(page.title) > settings.MAX_TITLE_LENGTH:
                affected.append(page.url)
                total_score -= 2
            elif len(page.title) < 10:
                affected.append(page.url)
                total_score -= 2

        if affected:
            issues.append(SEOIssue(
                severity='critical' if any(not p.title for p in pages) else 'warning',
                category='on-page',
                title='Title Tag Issues',
                description=f'{len(affected)} pages have missing, too long, or too short title tags',
                affected_urls=affected[:10],
                recommendation='Ensure every page has a unique title tag between 10-60 characters',
                impact_score=85 if any(not p.title for p in pages) else 60
            ))

        return max(0, total_score), issues

    def _check_meta_descriptions(self, pages: List[PageData]) -> Tuple[float, List[SEOIssue]]:
        issues = []
        total_score = 100
        affected = []

        for page in pages:
            if not page.meta_description:
                affected.append(page.url)
                total_score -= 3
            elif len(page.meta_description) > settings.MAX_META_DESC_LENGTH:
                affected.append(page.url)
                total_score -= 1
            elif len(page.meta_description) < 50:
                affected.append(page.url)
                total_score -= 1

        if affected:
            issues.append(SEOIssue(
                severity='warning',
                category='on-page',
                title='Meta Description Issues',
                description=f'{len(affected)} pages have missing or poorly optimized meta descriptions',
                affected_urls=affected[:10],
                recommendation='Write compelling meta descriptions between 50-160 characters',
                impact_score=55
            ))

        return max(0, total_score), issues

    def _check_headings(self, pages: List[PageData]) -> Tuple[float, List[SEOIssue]]:
        issues = []
        total_score = 100
        missing_h1 = []
        multiple_h1 = []

        for page in pages:
            if not page.h1:
                missing_h1.append(page.url)
                total_score -= 5

            h1_count = sum(1 for h in page.heading_structure if h['level'] == 1)
            if h1_count > 1:
                multiple_h1.append(page.url)
                total_score -= 3

        if missing_h1:
            issues.append(SEOIssue(
                severity='critical',
                category='on-page',
                title='Missing H1 Tags',
                description=f'{len(missing_h1)} pages are missing H1 headings',
                affected_urls=missing_h1[:10],
                recommendation='Every page should have exactly one H1 tag that describes the main topic',
                impact_score=80
            ))

        if multiple_h1:
            issues.append(SEOIssue(
                severity='warning',
                category='on-page',
                title='Multiple H1 Tags',
                description=f'{len(multiple_h1)} pages have more than one H1 tag',
                affected_urls=multiple_h1[:10],
                recommendation='Use only one H1 per page. Use H2-H6 for subsections',
                impact_score=50
            ))

        return max(0, total_score), issues

    def _check_content_quality(self, pages: List[PageData]) -> Tuple[float, List[SEOIssue]]:
        issues = []
        total_score = 100
        thin_content = []
        duplicate_content = []
        weak_semantics = []
        low_orb_scores = []

        for page in pages:
            if page.word_count < settings.MIN_CONTENT_WORDS:
                thin_content.append(page.url)
                total_score -= 3

            if page.duplicate_content_risk:
                duplicate_content.append(page.url)
                total_score -= 5

            if page.semantic_analysis.get('semantic_depth') == 'thin':
                weak_semantics.append(page.url)
                total_score -= 2

            if page.semantic_analysis.get('orb_semantic_score', {}).get('overall', 100) < 65:
                low_orb_scores.append(page.url)
                total_score -= 3

        if thin_content:
            issues.append(SEOIssue(
                severity='warning',
                category='content',
                title='Thin Content',
                description=f'{len(thin_content)} pages have less than {settings.MIN_CONTENT_WORDS} words',
                affected_urls=thin_content[:10],
                recommendation='Expand thin pages with comprehensive, valuable content',
                impact_score=65
            ))

        if duplicate_content:
            issues.append(SEOIssue(
                severity='critical',
                category='content',
                title='Duplicate Content',
                description=f'{len(duplicate_content)} pages may have duplicate content',
                affected_urls=duplicate_content[:10],
                recommendation='Use canonical tags or rewrite content to be unique',
                impact_score=90
            ))

        if weak_semantics:
            issues.append(SEOIssue(
                severity='warning',
                category='content',
                title='Weak Semantic Coverage',
                description=f'{len(weak_semantics)} pages have shallow topical depth or low semantic coverage',
                affected_urls=weak_semantics[:10],
                recommendation='Expand pages around the primary topic, related entities, questions, and supporting subtopics',
                impact_score=62
            ))

        if low_orb_scores:
            issues.append(SEOIssue(
                severity='warning',
                category='content',
                title='Low ORB Semantic Space Score',
                description=f'{len(low_orb_scores)} pages cover less than 65% of their expected semantic space',
                affected_urls=low_orb_scores[:10],
                recommendation='Add missing entities, questions, supporting subtopics, and schema-aligned language',
                impact_score=74
            ))

        return max(0, total_score), issues

    def _check_performance(self, pages: List[PageData]) -> Tuple[float, List[SEOIssue]]:
        issues = []
        total_score = 100
        slow_pages = []

        avg_load = sum(p.load_time_ms for p in pages if p.load_time_ms) / len([p for p in pages if p.load_time_ms]) if any(p.load_time_ms for p in pages) else 0

        for page in pages:
            if page.load_time_ms and page.load_time_ms > 3000:  # 3 seconds
                slow_pages.append(page.url)
                total_score -= 5
            elif page.load_time_ms and page.load_time_ms > 1500:  # 1.5 seconds
                total_score -= 2

        if slow_pages:
            issues.append(SEOIssue(
                severity='critical' if avg_load > 3000 else 'warning',
                category='performance',
                title='Slow Page Load Times',
                description=f'{len(slow_pages)} pages load slower than 3 seconds. Average: {avg_load:.0f}ms',
                affected_urls=slow_pages[:10],
                recommendation='Optimize images, enable compression, use CDN, minimize JavaScript',
                impact_score=85 if avg_load > 3000 else 70
            ))

        return max(0, total_score), issues

    def _check_security(self, pages: List[PageData]) -> Tuple[float, List[SEOIssue]]:
        issues = []
        total_score = 100
        non_ssl = []

        for page in pages:
            if not page.ssl_enabled:
                non_ssl.append(page.url)
                total_score -= 10

        if non_ssl:
            issues.append(SEOIssue(
                severity='critical',
                category='security',
                title='Missing SSL/HTTPS',
                description=f'{len(non_ssl)} pages are not served over HTTPS',
                affected_urls=non_ssl[:10],
                recommendation='Install SSL certificate and redirect HTTP to HTTPS',
                impact_score=95
            ))

        return max(0, total_score), issues

    def _check_images(self, pages: List[PageData]) -> Tuple[float, List[SEOIssue]]:
        issues = []
        total_score = 100
        missing_alt = []

        for page in pages:
            if page.images_without_alt > 0:
                missing_alt.append(page.url)
                total_score -= 2

        if missing_alt:
            issues.append(SEOIssue(
                severity='warning',
                category='accessibility',
                title='Images Missing Alt Text',
                description=f'{len(missing_alt)} pages have images without alt text',
                affected_urls=missing_alt[:10],
                recommendation='Add descriptive alt text to all images for accessibility and SEO',
                impact_score=45
            ))

        return max(0, total_score), issues

    def _check_mobile(self, pages: List[PageData]) -> Tuple[float, List[SEOIssue]]:
        issues = []
        total_score = 100
        no_viewport = []
        weak_mobile_ux = []

        for page in pages:
            if not page.mobile_viewport:
                no_viewport.append(page.url)
                total_score -= 10
            if page.mobile_ux_analysis.get('score', 100) < 70:
                weak_mobile_ux.append(page.url)
                total_score -= 5

        if no_viewport:
            issues.append(SEOIssue(
                severity='critical',
                category='technical',
                title='Missing Mobile Viewport',
                description=f'{len(no_viewport)} pages lack mobile viewport meta tag',
                affected_urls=no_viewport[:10],
                recommendation='Add <meta name="viewport" content="width=device-width, initial-scale=1">',
                impact_score=85
            ))

        if weak_mobile_ux:
            issues.append(SEOIssue(
                severity='warning',
                category='technical',
                title='Mobile UX Simulation Risks',
                description=f'{len(weak_mobile_ux)} pages show mobile tap target, viewport, font, or CLS risk',
                affected_urls=weak_mobile_ux[:10],
                recommendation='Increase tap target size, define image dimensions, use responsive viewport, and keep mobile font sizes legible',
                impact_score=78
            ))

        return max(0, total_score), issues

    def _check_technical(self, pages: List[PageData], stats: Dict) -> Tuple[float, List[SEOIssue]]:
        issues = []
        total_score = 100

        # Check for sitemap
        if not stats.get('has_sitemap', False):
            issues.append(SEOIssue(
                severity='warning',
                category='technical',
                title='Missing XML Sitemap',
                description='No XML sitemap was found on the website',
                recommendation='Create and submit an XML sitemap to Google Search Console',
                impact_score=60
            ))
            total_score -= 15

        # Check for robots.txt
        if not stats.get('has_robots_txt', False):
            issues.append(SEOIssue(
                severity='warning',
                category='technical',
                title='Missing robots.txt',
                description='No robots.txt file was found',
                recommendation='Create a robots.txt file to guide search engine crawlers',
                impact_score=40
            ))
            total_score -= 10

        # Check canonical tags
        missing_canonical = [p.url for p in pages if not p.canonical_url]
        if missing_canonical:
            issues.append(SEOIssue(
                severity='warning',
                category='technical',
                title='Missing Canonical Tags',
                description=f'{len(missing_canonical)} pages lack canonical tags',
                affected_urls=missing_canonical[:10],
                recommendation='Add canonical tags to prevent duplicate content issues',
                impact_score=55
            ))
            total_score -= 10

        template_counts = {}
        for page in pages:
            if page.template_signature:
                template_counts.setdefault(page.template_signature, []).append(page.url)
        repeated_templates = [urls for urls in template_counts.values() if len(urls) >= 3]

        if repeated_templates:
            affected = [url for urls in repeated_templates for url in urls[:3]]
            issues.append(SEOIssue(
                severity='warning',
                category='content',
                title='Repeated Template or Boilerplate Pattern',
                description=f'{len(repeated_templates)} repeated page template clusters were detected',
                affected_urls=affected[:10],
                recommendation='Differentiate page body copy, titles, meta descriptions, and section structure for pages sharing a template',
                impact_score=72
            ))
            total_score -= 8

        return max(0, total_score), issues

    def _check_schema(self, pages: List[PageData]) -> Tuple[float, List[SEOIssue]]:
        issues = []
        total_score = 100
        missing_schema = [p.url for p in pages if not p.schema_markup]
        invalid_schema = [
            p.url for p in pages
            if p.schema_analysis and p.schema_analysis.get('invalid_count', 0) > 0
        ]

        if pages and len(missing_schema) > len(pages) * 0.5:
            issues.append(SEOIssue(
                severity='opportunity',
                category='schema',
                title='Schema Markup Opportunity',
                description=f'{len(missing_schema)} pages lack structured data',
                recommendation='Add schema markup (JSON-LD) for rich snippets and ORB-readable business context',
                impact_score=50
            ))
            total_score -= 20

        if invalid_schema:
            issues.append(SEOIssue(
                severity='warning',
                category='schema',
                title='Invalid Schema Markup',
                description=f'{len(invalid_schema)} pages contain invalid structured data blocks',
                affected_urls=invalid_schema[:10],
                recommendation='Validate JSON-LD and microdata, then fix parsing errors before publishing',
                impact_score=68
            ))
            total_score -= 25

        return max(0, total_score), issues

    def _check_internal_link_graph(self, pages: List[PageData]) -> Tuple[float, List[SEOIssue]]:
        issues = []
        total_score = 100
        known_urls = {p.url.rstrip('/') for p in pages}
        low_outlinks = []
        orphan_candidates = []
        incoming_counts = {url: 0 for url in known_urls}

        for page in pages:
            if page.status_code == 200 and page.internal_links < 2:
                low_outlinks.append(page.url)
                total_score -= 2
            for target in page.internal_link_targets:
                target_url = (target.get('url') or '').rstrip('/')
                if target_url in incoming_counts:
                    incoming_counts[target_url] += 1

        for page in pages:
            normalized = page.url.rstrip('/')
            if page.status_code == 200 and incoming_counts.get(normalized, 0) == 0:
                orphan_candidates.append(page.url)
                total_score -= 3

        if low_outlinks:
            issues.append(SEOIssue(
                severity='opportunity',
                category='technical',
                title='Weak Internal Link Distribution',
                description=f'{len(low_outlinks)} pages have fewer than two internal outgoing links',
                affected_urls=low_outlinks[:10],
                recommendation='Add contextual internal links to relevant service, category, and supporting content pages',
                impact_score=52
            ))

        if len(orphan_candidates) > 1:
            issues.append(SEOIssue(
                severity='warning',
                category='technical',
                title='Potential Orphan Pages',
                description=f'{len(orphan_candidates)} crawled pages have no incoming links from other crawled pages',
                affected_urls=orphan_candidates[:10],
                recommendation='Link these pages from navigation, hub pages, or related body content',
                impact_score=66
            ))

        return max(0, total_score), issues

    def _check_indexability(self, pages: List[PageData]) -> Tuple[float, List[SEOIssue]]:
        issues = []
        total_score = 100
        non_indexable = [p.url for p in pages if not p.is_indexable]

        if non_indexable:
            issues.append(SEOIssue(
                severity='warning',
                category='technical',
                title='Non-Indexable Pages',
                description=f'{len(non_indexable)} pages have noindex directives',
                affected_urls=non_indexable[:10],
                recommendation='Review noindex tags. Ensure important pages are indexable',
                impact_score=70
            ))
            total_score -= len(non_indexable) * 2

        return max(0, total_score), issues

    def audit(self, pages: List[PageData], stats: Dict) -> Dict:
        self.issues = []

        # Run all checks
        title_score, title_issues = self._check_title_tags(pages)
        desc_score, desc_issues = self._check_meta_descriptions(pages)
        heading_score, heading_issues = self._check_headings(pages)
        content_score, content_issues = self._check_content_quality(pages)
        perf_score, perf_issues = self._check_performance(pages)
        security_score, security_issues = self._check_security(pages)
        image_score, image_issues = self._check_images(pages)
        mobile_score, mobile_issues = self._check_mobile(pages)
        tech_score, tech_issues = self._check_technical(pages, stats)
        schema_score, schema_issues = self._check_schema(pages)
        index_score, index_issues = self._check_indexability(pages)
        link_graph_score, link_graph_issues = self._check_internal_link_graph(pages)

        # Collect all issues
        all_issues = (title_issues + desc_issues + heading_issues + content_issues + 
                     perf_issues + security_issues + image_issues + mobile_issues + 
                     tech_issues + schema_issues + index_issues + link_graph_issues)
        self.issues = all_issues

        # Calculate category scores
        self.scores.seo = (title_score + desc_score + heading_score + index_score) / 4
        self.scores.performance = perf_score
        self.scores.accessibility = (image_score + mobile_score) / 2
        self.scores.content = content_score
        self.scores.technical = (tech_score + index_score) / 2
        self.scores.mobile = mobile_score
        self.scores.security = security_score
        self.scores.authority = link_graph_score
        self.scores.schema = schema_score

        # Overall score weights: content/semantic depth is highest by design.
        self.scores.overall = (
            self.scores.content * 0.25 +
            self.scores.technical * 0.15 +
            self.scores.security * 0.12 +
            self.scores.performance * 0.12 +
            self.scores.accessibility * 0.10 +
            self.scores.mobile * 0.10 +
            self.scores.authority * 0.10 +
            self.scores.schema * 0.06
        )

        # Categorize issues
        critical = [i for i in all_issues if i.severity == 'critical']
        warnings = [i for i in all_issues if i.severity == 'warning']
        opportunities = [i for i in all_issues if i.severity == 'opportunity']

        return {
            'scores': self.scores.to_dict(),
            'issues': {
                'critical': [i.to_dict() for i in critical],
                'warnings': [i.to_dict() for i in warnings],
                'opportunities': [i.to_dict() for i in opportunities]
            },
            'summary': {
                'total_issues': len(all_issues),
                'critical_count': len(critical),
                'warning_count': len(warnings),
                'opportunity_count': len(opportunities),
                'total_pages': len(pages),
                'avg_load_time': stats.get('avg_load_time', 0)
            },
            'top_issues': [i.to_dict() for i in sorted(all_issues, key=lambda x: x.impact_score, reverse=True)[:10]]
        }
