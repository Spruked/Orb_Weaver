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

const combinedDashboard = {
  project,
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
  const preflightCard = page.locator('.card', {
    has: page.getByRole('heading', { name: 'Preflight Readiness' }),
  });
  await preflightCard.waitFor();
  await preflightCard.getByText('No preflight report has been run for shilohridgekatahdins.com').waitFor();

  await preflightCard.getByRole('button', { name: 'Run Preflight' }).click();
  await preflightCard.getByText('13 pages scanned for shilohridgekatahdins.com').waitFor();
  await preflightCard.getByText('90%').waitFor();
  await preflightCard.getByText('Confidence').waitFor();
  await preflightCard.getByText('Sitemap').waitFor();
  await preflightCard.getByText('Auth Pages').waitFor();
  await preflightCard.getByText('Warnings').waitFor();

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
