function defaultApiBaseUrl() {
  if (typeof window === 'undefined') return '';

  const { hostname, port, protocol } = window.location;
  const apiHostname = hostname === '0.0.0.0' ? '127.0.0.1' : hostname;
  const isLocalOrPrivateHost =
    port === '16510' ||
    hostname === 'localhost' ||
    hostname === '127.0.0.1' ||
    hostname === '0.0.0.0' ||
    hostname === '::1' ||
    hostname.startsWith('192.168.') ||
    hostname.startsWith('10.') ||
    /^172\.(1[6-9]|2\d|3[0-1])\./.test(hostname);

  return isLocalOrPrivateHost ? `${protocol}//${apiHostname}:16500` : '';
}

const API_BASE_URL = process.env.REACT_APP_API_URL || defaultApiBaseUrl();
const TOKEN_KEY = 'orb_weaver_customer_token';

export const authStore = {
  getToken: () => localStorage.getItem(TOKEN_KEY),
  setToken: (token: string) => localStorage.setItem(TOKEN_KEY, token),
  clearToken: () => localStorage.removeItem(TOKEN_KEY)
};

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const token = authStore.getToken();
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers
    },
    ...options
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const message = body?.detail || body?.message || response.statusText;
    throw new Error(message);
  }

  return response.json();
}

function filenameFromDisposition(disposition: string | null) {
  if (!disposition) return '';
  const match = disposition.match(/filename="?([^"]+)"?/i);
  return match?.[1] || '';
}

async function fetchBlob(path: string) {
  const token = authStore.getToken();
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    }
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail || response.statusText);
  }
  return {
    data: await response.blob(),
    filename: filenameFromDisposition(response.headers.get('Content-Disposition'))
  };
}

async function fetchText(path: string) {
  const token = authStore.getToken();
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    }
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail || response.statusText);
  }
  return {
    data: await response.text(),
    filename: filenameFromDisposition(response.headers.get('Content-Disposition'))
  };
}

function escapeHtml(value: string) {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

async function openJsonDocument(path: string) {
  const opened = window.open('', '_blank', 'noopener,noreferrer');
  if (!opened) return;
  opened.document.write('<!doctype html><title>Loading report...</title><body style="font-family: system-ui, sans-serif; padding: 18px;">Loading report...</body>');
  opened.document.close();

  const file = await fetchText(path);
  let body = file.data;
  try {
    body = JSON.stringify(JSON.parse(file.data), null, 2);
  } catch {
    // Existing legacy report files may contain non-JSON text. Show them as-is.
  }

  const title = file.filename || 'report.json';
  opened.document.open();
  opened.document.write(`<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>${escapeHtml(title)}</title>
    <style>
      body { margin: 0; background: #f8fafc; color: #111827; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; }
      header { position: sticky; top: 0; padding: 14px 18px; background: #ffffff; border-bottom: 1px solid #e5e7eb; font-family: Inter, system-ui, sans-serif; font-weight: 700; }
      pre { margin: 0; padding: 18px; white-space: pre-wrap; word-break: break-word; line-height: 1.55; font-size: 13px; }
    </style>
  </head>
  <body>
    <header>${escapeHtml(title)}</header>
    <pre>${escapeHtml(body)}</pre>
  </body>
</html>`);
  opened.document.close();
}

async function openBlob(path: string) {
  const blob = await fetchBlob(path);
  const url = URL.createObjectURL(blob.data);
  window.open(url, '_blank', 'noopener,noreferrer');
  window.setTimeout(() => URL.revokeObjectURL(url), 60000);
}

async function downloadAuto(path: string) {
  const blob = await fetchBlob(path);
  const url = URL.createObjectURL(blob.data);
  const link = document.createElement('a');
  link.href = url;
  link.download = blob.filename || 'download';
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export interface Project {
  id: string;
  name: string;
  domain: string;
  ga4_property_id?: string | null;
  ga4_measurement_id?: string | null;
  created_at?: string;
  latest_crawl_id?: string | null;
  latest_crawl_status?: string;
  latest_pages_crawled?: number | null;
  latest_audit_id?: string | null;
  latest_audit_score?: number | null;
  folder_title?: string;
}

export interface Customer {
  id: string;
  email: string;
  full_name?: string | null;
  business_name: string;
  company_name?: string | null;
  contact_name?: string | null;
  phone?: string | null;
  address_line1?: string | null;
  address_line2?: string | null;
  city?: string | null;
  state?: string | null;
  postal_code?: string | null;
  country?: string | null;
  business_phone?: string | null;
  business_address_line1?: string | null;
  business_address_line2?: string | null;
  business_city?: string | null;
  business_state?: string | null;
  business_postal_code?: string | null;
  business_country?: string | null;
  tax_id?: string | null;
  is_admin?: boolean;
  status: string;
  created_at?: string | null;
  updated_at?: string | null;
  last_login_at?: string | null;
}

export interface AuthResponse {
  token: string;
  customer: Customer;
}

export interface Product {
  sku: string;
  name: string;
  description: string;
  unit_amount_cents: number;
  currency: string;
}

export interface MarketplaceItem {
  item_id: string;
  market_index_code: string;
  name: string;
  price: string;
  badge: string;
  description: string;
  features: string[];
  href: string;
  category: string;
  tier_access: string[];
  rights_status: string;
  rarity: string;
  image_src?: string;
  sku?: string | null;
  purchasable: boolean;
}

export interface CartItem {
  id: string;
  sku: string;
  name: string;
  unit_amount_cents: number;
  currency: string;
  quantity: number;
  line_total_cents: number;
  metadata?: Record<string, string>;
}

export interface CartPayload {
  items: CartItem[];
  total_amount_cents: number;
  currency: string;
}

export interface CheckoutOrder {
  id: string;
  provider: string;
  status: string;
  amount_cents: number;
  currency: string;
  provider_order_id?: string | null;
  checkout_url?: string | null;
  line_items: CartItem[];
  error?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface AdminCustomer extends Customer {
  project_count: number;
  cart_item_count: number;
  checkout_order_count: number;
  last_checkout_status?: string | null;
}

export interface CrawlConfig {
  max_pages: number;
  delay: number;
  max_depth: number;
  competitor_domains?: string[];
  seed_urls?: string[];
}

export interface PreflightReport {
  status?: 'not_run' | string;
  site_url?: string;
  scan_timestamp?: string;
  scan_duration?: number;
  detected?: {
    existing_chat_widget?: boolean;
    external_assistant_endpoint?: string | null;
    cms_framework?: string | null;
    has_contact_form?: boolean;
    has_auth_pages?: boolean;
    has_products?: boolean;
    has_checkout?: boolean;
    has_booking?: boolean;
    has_blog?: boolean;
    has_pdfs?: boolean;
    robots_txt?: boolean;
    robots_disallow_count?: number;
    sitemap_xml?: boolean;
    sitemap_url_count?: number;
    cors_risks?: string[];
    broken_links?: string[];
    placeholder_pages?: string[];
    privacy_page?: boolean;
    terms_page?: boolean;
    external_domains?: string[];
    third_party_scripts?: string[];
    exclude_recommendations?: string[];
    custom_behavior_flags?: string[];
  };
  recommended_install_mode?: string;
  required_custom_steps?: string[];
  warnings?: string[];
  pages_scanned?: number;
  confidence?: number;
  project?: Project;
  orb_weaver_project?: {
    project_id?: string;
    domain?: string;
    name?: string;
    output_dir?: string;
  };
}

export interface CrawledPage {
  url: string;
  title?: string | null;
  status_code?: number | null;
  load_time_ms?: number | null;
  word_count?: number;
  internal_links?: number;
  external_links?: number;
  images_count?: number;
  images_without_alt?: number;
  is_indexable?: boolean;
  ssl_enabled?: boolean;
  semantic_analysis?: {
    top_terms?: Array<{ term: string; count: number }>;
    semantic_depth?: string;
    unique_term_ratio?: number;
    avg_sentence_words?: number;
    heading_term_overlap?: string[];
    question_count?: number;
    orb_semantic_score?: {
      overall: number;
      topical_completeness: number;
      semantic_depth: number;
      entity_coverage: number;
      question_answer_density: number;
      readability_expertise_balance: number;
      topic: string;
      reasoning_statement: string;
    };
  };
  schema_analysis?: {
    count?: number;
    types?: string[];
    invalid_count?: number;
    errors?: string[];
    recommended_missing?: string[];
  };
  internal_link_targets?: Array<{ url: string; anchor?: string; nofollow?: boolean }>;
  entity_analysis?: {
    named_entities?: string[];
    people?: string[];
    organizations?: string[];
    locations?: string[];
    product_names?: string[];
    schema_org_entities?: string[];
    source?: string;
  };
  mobile_ux_analysis?: {
    score?: number;
    viewport_scaling?: string;
    small_tap_targets?: number;
    small_font_rules?: number;
    mobile_cls_risk_elements?: number;
    screenshot_capture?: string;
  };
  template_signature?: string | null;
  crawl_depth?: number;
}

export interface CrawlJob {
  id: string;
  project_id: string;
  project_name?: string;
  project_domain?: string;
  status: string;
  config?: CrawlConfig;
  created_at?: string;
  start_time?: string;
  end_time?: string;
  pages_crawled?: number;
  pages_found?: number;
  errors_count?: number;
  stats?: Record<string, number | boolean | string | Record<string, number | boolean | string | null>>;
  pages?: CrawledPage[];
  historical?: {
    has_previous: boolean;
    previous_stats?: Record<string, number>;
    current_stats?: Record<string, number>;
    deltas?: Record<string, number>;
  } | null;
  internal_link_graph?: {
    nodes: Array<{ url: string; title?: string | null; inbound: number; outbound: number; status_code?: number | null }>;
    edges: Array<{ source: string; target: string; anchor?: string; nofollow?: boolean }>;
    orphan_candidates: Array<{ url: string; title?: string | null; inbound: number; outbound: number; status_code?: number | null }>;
  } | null;
  authority_flow?: {
    pages: Array<Record<string, string | number | boolean | null>>;
    segments: Record<string, { avg_authority: number; pages: number }>;
    insights: string[];
  } | null;
  knowledge_graph?: {
    nodes: Array<{ id: string; label: string; type: string; url?: string }>;
    edges: Array<{ source: string; target: string; relationship: string }>;
    hubs: Array<{ id: string; label: string; mentions: number }>;
    topic_clusters: Array<{ topic: string; pages: string[]; page_count: number }>;
    missing_pillar_pages: Array<{ entity: string; reason: string }>;
    internal_linking_suggestions: Array<Record<string, string>>;
  } | null;
  trend_model?: {
    metrics: Record<string, { rolling_average: number; slope: number; anomaly: boolean; expected_next_month: number; seasonality: string }>;
  } | null;
  competitors?: Array<{
    domain: string;
    error?: string;
    stats?: Record<string, number | boolean>;
    top_terms?: Array<{ term: string; count: number }>;
    schema_types?: Array<{ type: string; count: number }>;
    entities?: Array<{ entity: string; count: number }>;
    questions?: Array<{ question: string; count: number }>;
  }>;
  competitor_gap?: {
    missing_topics: string[];
    missing_entities: string[];
    missing_questions: string[];
    missing_schema_types: string[];
    missing_internal_link_hubs: string[];
  } | null;
  template_detection?: {
    repeated_layouts: Array<{ signature: string; page_count: number; duplicate_text_probability: number; pages: string[]; orb_statement: string }>;
    duplicated_titles: Array<{ title: string; count: number }>;
    duplicated_meta_descriptions: Array<{ meta_description: string; count: number }>;
  } | null;
  error?: string;
}

export interface PagesResponse {
  total: number;
  pages: CrawledPage[];
}

export interface SEOIssue {
  severity: string;
  category: string;
  title: string;
  description: string;
  affected_urls?: string[];
  recommendation: string;
  impact_score: number;
}

export interface AuditReportPayload {
  scores: Record<string, number>;
  issues: {
    critical: SEOIssue[];
    warnings: SEOIssue[];
    opportunities: SEOIssue[];
  };
  summary: {
    total_issues: number;
    critical_count: number;
    warning_count: number;
    opportunity_count: number;
    total_pages: number;
    avg_load_time: number;
  };
  top_issues: SEOIssue[];
}

export interface AuditReportResponse {
  id: string;
  crawl_job_id: string;
  project?: Project | null;
  created_at: string;
  report: AuditReportPayload;
}

export interface ReportCompilerPayload {
  project: Project;
  latest_crawl?: CrawlJob | null;
  latest_audit?: {
    id: string;
    created_at: string;
    report: AuditReportPayload;
  } | null;
  files: string[];
}

export interface PublicPreflightReport {
  schema: string;
  generated_at: string;
  site_url: string;
  notice: string;
  outcome: 'basic_orb_recommended' | 'recommended' | 'needs_browser_verification' | 'needs_further_review' | 'not_recommended' | 'not_ready_any_orb';
  outcome_title: string;
  summary: string;
  premium_status?: string;
  recommended_next_step?: string;
  primary_cta?: string;
  secondary_ctas?: string[];
  fit_score: number;
  complexity: 'small' | 'medium' | 'large';
  install_path: string;
  reasons: string[];
  likely_orb_benefits: string[];
  basic_checks: {
    site_loaded: boolean;
    https_checked: boolean;
    sample_pages_read: number;
    sitemap_detected: boolean;
    robots_detected: boolean;
    contact_or_conversion_signals: boolean;
    login_or_checkout_detected: boolean;
    sample_broken_link_count: number;
  };
  limited_findings: {
    cms_or_framework: string;
    existing_chat_widget: boolean;
    forms_detected: boolean;
    products_detected: boolean;
    booking_detected: boolean;
    blog_detected: boolean;
    sitemap_url_count: number;
    warnings: string[];
  };
  next_steps: string[];
  browser_verification?: {
    status: string;
    reason?: string;
    summary?: {
      console_message_count?: number;
      network_request_count?: number;
      lighthouse_scores?: Record<string, number>;
    };
    artifacts?: {
      screenshot?: string | null;
      lighthouse_dir?: string | null;
    };
  };
}

export interface BrowserReviewResult {
  schema?: string;
  status: string;
  generated_at?: string;
  url?: string;
  label?: string;
  review_dir?: string;
  artifacts?: {
    screenshot?: string | null;
    lighthouse_dir?: string | null;
  };
  summary?: {
    console_message_count?: number;
    network_request_count?: number;
    lighthouse_scores?: Record<string, number>;
  };
  error?: string | null;
}

export interface BrowserLabCatalog {
  schema: string;
  enabled: boolean;
  public_enabled: boolean;
  product_boundary: string;
  groups: Record<string, {
    label: string;
    tools: Record<string, string>;
  }>;
}

export interface BrowserLabResult {
  schema: string;
  tool: string;
  status: string;
  generated_at: string;
  run_dir?: string;
  result?: {
    command?: string[];
    returncode?: number;
    stdout?: unknown;
    stderr?: string;
    ok?: boolean;
    mcp_error?: string | null;
  };
  reason?: string;
}

export interface GA4FullReport {
  traffic_overview?: {
    totals?: Record<string, number>;
  };
  top_pages?: Array<Record<string, string | number>>;
  search_queries?: Array<Record<string, string | number>>;
  device_breakdown?: Array<Record<string, string | number>>;
  country_breakdown?: Array<Record<string, string | number>>;
}

export const api = {
  publicPreflight: (websiteUrl: string) =>
    request<PublicPreflightReport>('/api/public/preflight', {
      method: 'POST',
      body: JSON.stringify({ website_url: websiteUrl })
    }),
  signup: (payload: {
    email: string;
    password: string;
    full_name: string;
    business_name?: string | null;
    company_name?: string | null;
    contact_name?: string | null;
    phone?: string | null;
    address_line1: string;
    address_line2?: string | null;
    city: string;
    state: string;
    postal_code: string;
    country: string;
    business_phone?: string | null;
    business_address_line1?: string | null;
    business_address_line2?: string | null;
    business_city?: string | null;
    business_state?: string | null;
    business_postal_code?: string | null;
    business_country?: string | null;
    tax_id?: string | null;
  }) =>
    request<AuthResponse>('/api/auth/signup', {
      method: 'POST',
      body: JSON.stringify(payload)
    }),
  login: (payload: { email: string; password: string }) =>
    request<AuthResponse>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify(payload)
    }),
  me: () => request<Customer>('/api/auth/me'),
  logout: () => request<{ status: string }>('/api/auth/logout', { method: 'POST' }),
  listProducts: () => request<Product[]>('/api/products'),
  listMarketplaceItems: (category?: string) =>
    request<MarketplaceItem[]>(`/api/marketplace/items${category ? `?category=${encodeURIComponent(category)}` : ''}`),
  getCart: () => request<CartPayload>('/api/cart'),
  upsertCartItem: (payload: { sku: string; quantity: number }) =>
    request<CartPayload>('/api/cart/items', {
      method: 'POST',
      body: JSON.stringify(payload)
    }),
  deleteCartItem: (sku: string) => request<CartPayload>(`/api/cart/items/${encodeURIComponent(sku)}`, { method: 'DELETE' }),
  createCheckout: (provider: 'stripe' | 'paypal') =>
    request<CheckoutOrder>('/api/cart/checkout', {
      method: 'POST',
      body: JSON.stringify({ provider })
    }),
  listCheckoutOrders: () => request<CheckoutOrder[]>('/api/checkout/orders'),
  adminListCustomers: () => request<AdminCustomer[]>('/api/admin/customers'),
  adminExportCustomersToCaliCrm: () =>
    request<{ status: string; record_count: number; path: string; crm_url: string }>('/api/admin/cali-crm/export-customers', {
      method: 'POST'
    }),
  adminBrowserLabTools: () => request<BrowserLabCatalog>('/api/admin/browser-lab/tools'),
  adminRunBrowserLabTool: (payload: { tool: string; params: Record<string, unknown> }) =>
    request<BrowserLabResult>('/api/admin/browser-lab/run', {
      method: 'POST',
      body: JSON.stringify(payload)
    }),
  listProjects: () => request<Project[]>('/api/projects'),
  createProject: (project: { name?: string | null; domain: string; ga4_property_id?: string | null; ga4_measurement_id?: string | null }) =>
    request<Project>('/api/projects', {
      method: 'POST',
      body: JSON.stringify(project)
    }),
  updateProjectGA4Config: (projectId: string, payload: { ga4_property_id?: string | null; ga4_measurement_id?: string | null }) =>
    request<Project>(`/api/projects/${projectId}/ga4/config`, {
      method: 'POST',
      body: JSON.stringify(payload)
    }),
  importProjectGA4: (projectId: string, payload: { ga4_property_id?: string | null; ga4_measurement_id?: string | null; days?: number } = {}) =>
    request<{ status: string; imported_page_rows: number; artifact_path: string; traffic_totals: Record<string, number>; project: Project }>(
      `/api/projects/${projectId}/ga4/import`,
      {
        method: 'POST',
        body: JSON.stringify(payload)
      }
    ),
  deleteProject: (id: string) =>
    request<{ status: string }>(`/api/projects/${id}`, { method: 'DELETE' }),
  startCrawl: (projectId: string, config: CrawlConfig) =>
    request<CrawlJob>(`/api/projects/${projectId}/crawl`, {
      method: 'POST',
      body: JSON.stringify(config)
    }),
  recrawlProject: (projectId: string, config: CrawlConfig) =>
    request<CrawlJob>(`/api/projects/${projectId}/recrawl`, {
      method: 'POST',
      body: JSON.stringify(config)
    }),
  reauditProject: (projectId: string) =>
    request<{ audit_id: string; status: string; message: string }>(`/api/projects/${projectId}/reaudit`, {
      method: 'POST'
    }),
  getProjectPreflight: (projectId: string) => request<PreflightReport>(`/api/projects/${projectId}/preflight`),
  runProjectPreflight: (projectId: string) =>
    request<PreflightReport>(`/api/projects/${projectId}/preflight`, {
      method: 'POST',
      body: JSON.stringify({})
    }),
  runProjectBrowserReview: (projectId: string) =>
    request<BrowserReviewResult>(`/api/projects/${projectId}/browser-review`, {
      method: 'POST'
    }),
  getCrawlJob: (jobId: string) => request<CrawlJob>(`/api/crawl-jobs/${jobId}`),
  listCrawlJobs: () => request<CrawlJob[]>('/api/crawl-jobs'),
  getCrawlPages: (jobId: string) => request<PagesResponse>(`/api/crawl-jobs/${jobId}/pages?limit=200`),
  runAudit: (jobId: string) =>
    request<{ audit_id: string; status: string; message: string }>(`/api/crawl-jobs/${jobId}/audit`, {
      method: 'POST'
    }),
  getAuditReport: (auditId: string) => request<AuditReportResponse>(`/api/audit-reports/${auditId}`),
  getReportCompiler: (projectId: string) => request<ReportCompilerPayload>(`/api/projects/${projectId}/report-compiler`),
  createTPCPack: (projectId: string, tier: 'basic' | 'enhanced' | 'premium') =>
    request<{ status: string; project: Project; pack: Record<string, any>; download_url: string }>(
      `/api/projects/${projectId}/tpc-pack`,
      {
        method: 'POST',
        body: JSON.stringify({ tier })
      }
    ),
  listTPCPacks: (projectId: string) =>
    request<{ packs: Array<{ filename: string; size_kb: number; generated_at: string; download_url: string }> }>(
      `/api/projects/${projectId}/tpc-packs`
    ),
  getCombinedDashboard: (projectId: string) =>
    request<{
      project: Project;
      crawl_summary?: Record<string, number | boolean> | null;
      audit_scores?: Record<string, number> | null;
      audit_issues?: AuditReportPayload['summary'] | null;
      ga4_data?: GA4FullReport | null;
      top_issues?: SEOIssue[] | null;
    }>(`/api/combined/${projectId}/dashboard`),
  getGA4Overview: (propertyId: string, days: string) =>
    request<GA4FullReport>(`/api/ga4/${propertyId}/overview?days=${days}`)
};

export const fileUrls = {
  crawlCsv: (jobId: string) => `${API_BASE_URL}/api/crawl-jobs/${jobId}/export/csv`,
  auditCsv: (auditId: string) => `${API_BASE_URL}/api/audit-reports/${auditId}/export/csv`,
  auditPdf: (auditId: string) => `${API_BASE_URL}/api/audit-reports/${auditId}/export/pdf`,
  reportFile: (projectId: string, filename: string, disposition: 'inline' | 'attachment' = 'inline') =>
    `${API_BASE_URL}/api/projects/${projectId}/report-files/${encodeURIComponent(filename)}?disposition=${disposition}`,
  tpcPack: (projectId: string, filename: string) =>
    `${API_BASE_URL}/api/projects/${projectId}/tpc-pack/download/${encodeURIComponent(filename)}`
};

export const downloads = {
  crawlCsv: (jobId: string) => downloadAuto(`/api/crawl-jobs/${jobId}/export/csv`),
  auditCsv: (auditId: string) => downloadAuto(`/api/audit-reports/${auditId}/export/csv`),
  auditPdf: (auditId: string) => downloadAuto(`/api/audit-reports/${auditId}/export/pdf`),
  reportFile: (projectId: string, filename: string) =>
    downloadAuto(`/api/projects/${projectId}/report-files/${encodeURIComponent(filename)}?disposition=attachment`),
  tpcPack: (projectId: string, filename: string) =>
    downloadAuto(`/api/projects/${projectId}/tpc-pack/download/${encodeURIComponent(filename)}`)
};

export const openFiles = {
  auditPdf: (auditId: string) => openBlob(`/api/audit-reports/${auditId}/export/pdf?disposition=inline`),
  reportFile: (projectId: string, filename: string) =>
    filename.toLowerCase().endsWith('.json')
      ? openJsonDocument(`/api/projects/${projectId}/report-files/${encodeURIComponent(filename)}?disposition=inline`)
      : openBlob(`/api/projects/${projectId}/report-files/${encodeURIComponent(filename)}?disposition=inline`)
};
