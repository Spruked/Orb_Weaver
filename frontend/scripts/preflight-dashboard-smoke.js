const { chromium } = require('playwright');

const APP_URL = process.env.APP_URL || 'http://127.0.0.1:16510/';
const API_ORIGIN = process.env.API_ORIGIN || 'http://127.0.0.1:16500';

const customer = {
  id: 'customer-smoke',
  email: 'smoke@example.com',
  full_name: 'Smoke Tester',
  business_name: 'Smoke Test Company',
  status: 'active',
};

const project = {
  id: 'project-smoke',
  name: 'Shiloh Ridge',
  domain: 'shilohridgekatahdins.com',
  ga4_property_id: null,
  created_at: '2026-06-11T00:00:00Z',
  latest_crawl_id: '33',
  latest_crawl_status: 'completed',
  latest_pages_crawled: 8,
  latest_audit_id: '12',
  latest_audit_score: 88,
};

const latestAudit = {
  id: '12',
  created_at: '2026-06-11T20:00:00Z',
  report: {
    scores: { overall: 88, technical: 91, content: 84, ux: 86, authority: 79 },
    summary: {
      total_pages: 8,
      public_pages: 6,
      pages_excluded_from_public_seo_scoring: 2,
      total_issues: 3,
      critical_count: 0,
      warning_count: 1,
      opportunity_count: 2,
      avg_load_time: 410,
      orb_context_entities: 14,
      orb_context_thin_content_pages: 1,
      route_category_counts: { product: 3, blog: 2, policy: 1, admin: 2 },
    },
    issues: {
      critical: [],
      warnings: [
        {
          title: 'Missing alt text on product hero image',
          severity: 'warning',
          impact_score: 5,
          recommendation: 'Add descriptive alt text for screen reader clarity.',
          details: 'A product page image is missing alt text.',
        },
      ],
      opportunities: [
        {
          title: 'Add schema to FAQ section',
          severity: 'opportunity',
          impact_score: 3,
          recommendation: 'Add FAQ schema for richer search visibility.',
          details: 'FAQ entries can be marked up as structured data.',
        },
      ],
    },
    top_issues: [
      {
        title: 'Improve image accessibility coverage',
        severity: 'warning',
        impact_score: 5,
        recommendation: 'Complete missing alt attributes on product and feature images.',
      },
    ],
    pointer_summary: {
      status: 'passed',
      record_count: 8,
      routes_with_pointers: 6,
      duplicate_target_ids: 0,
      target_type_counts: { cta: 4, nav: 2, form: 2 },
    },
    planned_tool_calls: [],
  },
};

const combinedDashboard = {
  project,
  latest_audit: latestAudit,
  crawl_summary: { total_pages: 8 },
  audit_scores: { overall: 88, technical: 91, content: 84 },
  audit_issues: {
    total_issues: 3,
    critical_count: 0,
    warning_count: 1,
    opportunity_count: 2,
    total_pages: 8,
    avg_load_time: 410,
  },
  ga4_data: { traffic_overview: { totals: { sessions: 0 } }, device_breakdown: [] },
  top_issues: [],
};

const preflightNotRun = {
  status: 'not_run',
  project,
};

const preflightReport = {
  site_url: 'https://shilohridgekatahdins.com',
  scan_timestamp: '2026-06-11T22:52:17Z',
  pages_scanned: 13,
  confidence: 0.9,
  recommended_install_mode: 'full_new_install',
  warnings: ['Found protected/auth pages.'],
  detected: {
    sitemap_xml: true,
    sitemap_url_count: 8,
    robots_txt: true,
    has_auth_pages: true,
    has_products: true,
    has_blog: true,
  },
};

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1366, height: 900 } });
  const consoleMessages = [];

  page.on('console', (message) => {
    if (['error', 'warning'].includes(message.type())) {
      consoleMessages.push(`${message.type()}: ${message.text()}`);
    }
  });

  await page.addInitScript(() => {
    localStorage.setItem('orb_weaver_customer_token', 'smoke-token');
  });

  await page.route(`${API_ORIGIN}/api/auth/me`, (route) => route.fulfill({ json: customer }));
  await page.route(`${API_ORIGIN}/api/projects`, (route) => route.fulfill({ json: [project] }));
  await page.route(`${API_ORIGIN}/api/combined/${project.id}/dashboard`, (route) =>
    route.fulfill({ json: combinedDashboard })
  );
  await page.route(`${API_ORIGIN}/api/projects/${project.id}/preflight`, (route) => {
    if (route.request().method() === 'POST') {
      return route.fulfill({ json: preflightReport });
    }
    return route.fulfill({ json: preflightNotRun });
  });

  await page.goto(APP_URL, { waitUntil: 'networkidle' });
  await page.getByText('Completed audit results').waitFor();
  const preflightHeading = page.getByRole('heading', { name: /Preflight readiness/i });
  await preflightHeading.waitFor();
  const preflightCard = page.locator('details.card', {
    has: preflightHeading,
  });
  await preflightCard.waitFor();
  await preflightCard.locator('summary').click();
  await page.getByText('Preflight is required').waitFor();

  await preflightCard.getByRole('button', { name: /Run preflight/i }).click();
  await preflightCard.getByText('13').first().waitFor();
  await preflightCard.getByText('90%').waitFor();
  await preflightCard.getByText('Confidence').waitFor();
  await preflightCard.getByText('Sitemap').waitFor();
  await preflightCard.getByText('Warnings').waitFor();
  await page.getByText('13 pages checked').waitFor();

  if (consoleMessages.length) {
    throw new Error(`Console warnings/errors detected:\n${consoleMessages.join('\n')}`);
  }

  await browser.close();
  console.log('Preflight dashboard smoke test passed');
}

main().catch(async (error) => {
  console.error(error);
  process.exit(1);
});
