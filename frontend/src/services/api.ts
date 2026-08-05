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
const ORB_RECONNECT_MESSAGE = 'I am reconnecting to my response service. Please try again in a moment.';

export const authStore = {
  getToken: () => localStorage.getItem(TOKEN_KEY),
  setToken: (token: string) => localStorage.setItem(TOKEN_KEY, token),
  clearToken: () => localStorage.removeItem(TOKEN_KEY)
};

export class ApiError extends Error {
  constructor(message: string, public readonly code?: string, public readonly status?: number) {
    super(message);
    this.name = 'ApiError';
  }
}

function apiUrl(path: string) {
  return `${API_BASE_URL}${path}`;
}

function mediaUrl(path?: string | null) {
  if (!path) return '';
  if (/^https?:\/\//i.test(path)) return path;
  return apiUrl(path);
}

async function parseJsonResponse<T>(response: Response, requestUrl: string): Promise<T> {
  const contentType = response.headers.get('Content-Type') || '';

  if (process.env.NODE_ENV !== 'production') {
    console.debug('[Orb Weaver API]', {
      requestUrl,
      status: response.status,
      contentType,
    });
  }

  if (!response.ok) {
    const body = contentType.includes('application/json') ? await response.json().catch(() => null) : null;
    const message = body?.detail || body?.message || response.statusText;
    throw new ApiError(message || ORB_RECONNECT_MESSAGE, body?.code, response.status);
  }

  if (!contentType.includes('application/json')) {
    throw new Error(ORB_RECONNECT_MESSAGE);
  }

  return response.json();
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const token = authStore.getToken();
  const requestUrl = apiUrl(path);
  const response = await fetch(requestUrl, {
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers
    },
    ...options
  });

  return parseJsonResponse<T>(response, requestUrl);
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

async function uploadForm<T>(path: string, formData: FormData, options?: RequestInit): Promise<T> {
  const token = authStore.getToken();
  const requestUrl = apiUrl(path);
  const response = await fetch(requestUrl, {
    method: 'POST',
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers
    },
    body: formData,
    signal: options?.signal
  });

  return parseJsonResponse<T>(response, requestUrl);
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

export interface OrbsAllowedAction {
  name: string;
  display_label: string;
  confirmation_required: boolean;
  allowed_input_fields: string[];
  permitted_input_fields: string[];
  destination_route?: string | null;
  destination_verified: boolean;
  reason_available?: string | null;
  idempotency_required: boolean;
}

export interface OrbsStageSnapshot {
  schema: 'orb_weaver.orbs_stage_snapshot.v1';
  customer_id: string;
  snapshot_version: string;
  project_id: string;
  project_display_name: string;
  build_order_id?: string | null;
  current_stage: string;
  stage_status: string;
  completed_stages: string[];
  blocking_reason?: string | null;
  customer_action_required?: string | null;
  next_recommended_action?: string | null;
  approved_stage_evidence: Record<string, unknown>;
  approved_destination_route?: string | null;
  approved_destination_verified: boolean;
  updated_at: string;
  allowed_actions: OrbsAllowedAction[];
}

export interface DockBusinessObjective {
  objective_id: string;
  name: string;
  enabled: boolean;
  completion_evidence: string[];
  required_fields: string[];
  permitted_routes: string[];
  permitted_tools: string[];
  escalation_route: string;
  success_condition: string;
  failure_condition: string;
}

export interface DockAdditionalGuideRail {
  guide_rail_id: string;
  name: string;
  enabled: boolean;
  applies_when: string;
  orb_should: string;
  orb_must_not: string;
  permitted_actions: string[];
  required_evidence: string[];
  escalate_when: string;
  priority: 'low' | 'medium' | 'high' | 'critical';
  effective_from?: string | null;
  effective_until?: string | null;
  owner_note: string;
}

export interface DockSituationConditions {
  current_pages: string[];
  visitor_types: string[];
  workflow_stages: string[];
  product_categories: string[];
  business_hours: string[];
  geographic_eligibility: string[];
  minimum_confidence?: number | null;
  authentication_states: Array<'anonymous' | 'authenticated'>;
  active_promotions: string[];
  prior_history_terms: string[];
}

export interface DockSituationalGuideRail {
  guide_rail_id: string;
  name: string;
  enabled: boolean;
  conditions: DockSituationConditions;
  orb_should: string;
  orb_must_not: string;
  permitted_actions: string[];
  required_evidence: string[];
  escalate_when: string;
  priority: 'low' | 'medium' | 'high' | 'critical';
  owner_note: string;
}

export interface DockConfiguration {
  schema: 'orb_weaver.orb_dock_configuration.v1';
  appearance: { skin_id: string };
  llm: {
    provider: 'runtime_default' | 'ollama_local' | 'openai_api' | 'anthropic_api' | 'openai_compatible';
    model?: string | null;
    base_url?: string | null;
    api_key_env?: string | null;
    temperature: number;
    max_output_tokens: number;
  };
  behavior: {
    tone: 'warm' | 'calm' | 'professional' | 'playful' | 'direct';
    response_style: 'concise' | 'guided' | 'diagnostic' | 'sales_assistant';
    greeting_enabled: boolean;
    startup_listening_enabled: boolean;
    voice_only: boolean;
    mute_by_default: boolean;
    sleep_by_default: boolean;
    greeting_script: string;
    job_description: string;
    persona_notes: string;
    must_follow_rules: string[];
    must_not_rules: string[];
    prohibited_tone: string[];
  };
  business_objectives: DockBusinessObjective[];
  additional_guide_rails: DockAdditionalGuideRail[];
  situational_guide_rails: DockSituationalGuideRail[];
}

export interface DockCompileIssue {
  path: string;
  code: string;
  message: string;
}

export interface OrbDockStation {
  schema: 'orb_weaver.orb_dock_station.v1';
  project: { id: string; name: string; domain: string };
  locked_doctrine: { hash: string; rules: Array<{ id: string; label: string; rule: string }> };
  configuration: DockConfiguration;
  publication: {
    status: 'draft' | 'published';
    version: number;
    compiled_hash?: string | null;
    published_at?: string | null;
    updated_at?: string | null;
  };
  compile: {
    publishable: boolean;
    blockers: DockCompileIssue[];
    warnings: DockCompileIssue[];
    preview_hash: string;
  };
  latest_crawl?: CrawlJob | null;
  skins: Array<{ skin_id: string; display_name: string; asset_path: string; factory_default?: boolean }>;
  llm_options: Array<{ id: DockConfiguration['llm']['provider']; label: string; description: string }>;
}

export interface DockOllamaStatus {
  configured: boolean;
  reachable: boolean;
  endpoint?: string | null;
  message: string;
  models: Array<{ name: string; size: number; modified_at?: string | null }>;
}

export interface OrbsActionSubmission {
  project_id: string;
  build_order_id?: string | null;
  action: string;
  expected_stage: string;
  snapshot_version: string;
  inputs: Record<string, unknown>;
  confirmation_evidence?: Record<string, unknown>;
}

export interface OrbsGuestSession {
  schema: 'orb_weaver.orbs_guest_session.v1';
  guest_session_id: string;
  landing_intent: string;
  selected_tier_interest?: string | null;
  website_url?: string | null;
  original_cta_destination: string;
  current_onboarding_step: string;
  completed_onboarding_steps: string[];
  non_sensitive_questionnaire_answers: Record<string, unknown>;
  created_at: string;
  expires_at: string;
  version: number;
}

export interface OrbsGuestMergeResult {
  schema: 'orb_weaver.orbs_guest_merge_result.v1';
  merge_status: 'merged' | 'idempotent_replay';
  guest_session_id: string;
  customer_id: string;
  project_id: string;
  onboarding_record_id: string;
  original_cta_destination: string;
  transferred_fields: string[];
  consumed_at: string;
  fresh_snapshot: OrbsStageSnapshot;
}

export type LifecycleJobType = 'MAP_CRAWL' | 'SITE_SCAN' | 'ORB_SCAN' | 'POINTER_RECOVERY' | 'FULL_AUDIT' | 'PREFLIGHT' | 'SENTINEL';

export interface LifecycleReviewItem {
  id: string;
  lifecycle_job_id: string;
  severity: string;
  category: string;
  title: string;
  details: Record<string, unknown>;
  status: string;
  reviewer?: string | null;
  decision?: 'approve' | 'reject' | 'waive' | null;
  notes?: string | null;
  signature_hash?: string | null;
  created_at?: string | null;
  decided_at?: string | null;
}

export interface LifecycleJob {
  id: string;
  project_id: string;
  job_type: LifecycleJobType;
  status: string;
  phase: string;
  progress: { current: number; total: number };
  config: Record<string, unknown>;
  result: Record<string, unknown>;
  evidence_root?: string | null;
  manifest_hash?: string | null;
  previous_run_id?: string | null;
  previous_manifest_hash?: string | null;
  created_at?: string | null;
  start_time?: string | null;
  end_time?: string | null;
  review_items: LifecycleReviewItem[];
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

interface MarketplaceProductResponse {
  id: string;
  system_number?: string | null;
  title: string;
  slug?: string | null;
  description?: string | null;
  price_cents?: number | null;
  currency?: string | null;
  category?: string | null;
  tier?: string | null;
  primary_image_url?: string | null;
  images?: Array<{ file_url?: string | null }>;
}

function formatMarketplacePrice(priceCents?: number | null, currency = 'usd') {
  const amount = (priceCents || 0) / 100;
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency.toUpperCase(),
    maximumFractionDigits: amount % 1 === 0 ? 0 : 2,
  }).format(amount);
}

function normalizeMarketplaceProduct(product: MarketplaceProductResponse): MarketplaceItem {
  const slugOrId = product.slug || product.id;
  return {
    item_id: String(product.id),
    market_index_code: product.system_number || `ORB-MKT.${product.id}`,
    name: product.title,
    price: formatMarketplacePrice(product.price_cents, product.currency || 'usd'),
    badge: product.tier || 'Marketplace',
    description: product.description || 'Marketplace product listing.',
    features: ['Live marketplace listing'],
    href: `/marketplace/products/${slugOrId}`,
    category: product.category || 'uncategorized',
    tier_access: product.tier ? [product.tier] : ['basic', 'premium', 'platinum'],
    rights_status: 'marketplace',
    rarity: 'standard',
    image_src: product.primary_image_url || product.images?.find((image) => image.file_url)?.file_url || undefined,
    sku: product.system_number || null,
    purchasable: false,
  };
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

export type CheckoutProvider = 'stripe' | 'paypal' | 'square' | 'venmo';

export interface AdminCustomer extends Customer {
  project_count: number;
  cart_item_count: number;
  checkout_order_count: number;
  last_checkout_status?: string | null;
}

export interface CaliCrmContact {
  id: string | number;
  display_name: string;
  contact_type: string;
  company_name?: string | null;
  role_title?: string | null;
  email?: string | null;
  phone?: string | null;
  website?: string | null;
  relationship_status: string;
  tags: string[];
  notes?: string;
  dossier_path?: string | null;
  created_at: string;
  updated_at: string;
}

export interface CrawlConfig {
  max_pages: number;
  delay: number;
  max_depth: number;
  competitor_domains?: string[];
  seed_urls?: string[];
  include_admin_sections?: boolean;
}

export interface ScanAssemblyMetric {
  label: string;
  value: number | string | boolean;
  total?: number | string | null;
}

export interface ScanAssemblyStage {
  id: string;
  label: string;
  status: 'not_started' | 'waiting' | 'running' | 'complete' | 'failed' | string;
  metrics: ScanAssemblyMetric[];
  note?: string | null;
}

export interface ScanAssemblyStatus {
  schema: 'orb_weaver.scan_assembly_status.v1';
  crawl_job_id: string;
  overall_status: string;
  crawl_delay_seconds: number;
  stages: ScanAssemblyStage[];
}

export interface AuditDelta {
  has_previous: boolean;
  latest_audit_id?: string;
  previous_audit_id?: string;
  deltas: Record<string, number>;
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
  pointer_guidance?: Record<string, unknown>;
  deployment_preflight?: { passed: boolean; blockers: string[] };
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
  assembly_status?: ScanAssemblyStatus;
  pointer_summary?: PointerSummary;
  planned_tool_calls?: PlannedToolCall[];
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

export interface PointerSummary {
  schema?: string;
  record_count: number;
  routes_with_pointers: number;
  duplicate_target_ids: number;
  target_type_counts?: Record<string, number>;
  extraction_status?: string;
  runtime_guidance_status?: string;
  pointer_recovery_status?: string;
  guidance_eligible_count?: number;
  quality?: {
    status?: string;
    recovery_required?: boolean;
    stable_count?: number;
    uncertain_count?: number;
    duplicate_conflict_count?: number;
    confidence_classes?: Record<string, number>;
    triggers?: string[];
  };
  status: string;
}

export interface PlannedToolCall {
  id: string;
  tool: string;
  scope: string;
  trigger: string;
  purpose: string;
  status: string;
  requires_mcp: boolean;
  route?: string;
  section?: string;
  target_type?: string;
  target_id?: string;
  anchor_strategy?: string;
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
    public_pages?: number;
    route_category_counts?: Record<string, number>;
    pages_excluded_from_public_seo_scoring?: number;
    excluded_from_public_seo_scoring?: Record<string, string[]>;
    admin_pages_scanned?: number;
    admin_pages_excluded_from_public_seo_scoring?: number;
    admin_urls?: string[];
    transactional_pages_excluded_from_public_seo_scoring?: number;
    transactional_urls?: string[];
    crawl_control_resources?: number;
    orb_context_entities?: number;
    orb_context_thin_content_pages?: number;
    avg_load_time: number;
  };
  top_issues: SEOIssue[];
  pointer_summary?: PointerSummary;
  planned_tool_calls?: PlannedToolCall[];
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

export interface WebsiteOrbVoiceResponse {
  transcript: string;
  spoken_output: string;
  cognitive_pulse?: Record<string, unknown> | null;
  llm_source: string;
  memory_context?: Record<string, unknown> | null;
  tts_audio_url?: string | null;
  tts_provider?: string | null;
  tts_error?: string | null;
}

export interface WebsiteOrbPointerRecord {
  target_id: string;
  page_route: string;
  target_type: string;
  meaning?: string;
  intent_aliases?: string[];
  direct_aliases?: string[];
  topic_aliases?: string[];
  content_fingerprint: string;
  semantic_locator: string;
  structural_context?: Record<string, string | number | boolean | null | undefined>;
  confidence?: number;
  confidence_class?: 'VERIFIED' | 'STABLE' | 'UNCERTAIN' | 'BLOCKED';
  finding_class?: 'CONFIRMED' | 'TRANSIENT' | 'DYNAMIC' | 'CONFLICT' | 'UNVERIFIED' | 'PASSED';
  finding_subreason?: string;
  pointer_health?: 'NEW' | 'VERIFIED' | 'RECOVERED' | 'OWNER_VERIFIED' | 'DEPRECATED' | 'REMOVED';
  uncertainty_reasons?: string[];
}

export interface WebsiteOrbPointerMap {
  schema: string;
  generated_at?: string | null;
  project_id?: string | null;
  source_crawl_job_id?: string | null;
  domain?: string | null;
  record_count: number;
  records: WebsiteOrbPointerRecord[];
  by_page: Record<string, string[]>;
  quality: Record<string, unknown>;
  recovery: Record<string, unknown>;
}

export interface WebsiteOrbPageCapsule {
  schema: string;
  site_name?: string | null;
  domain?: string | null;
  current_url: string;
  route: string;
  page_purpose: string;
  page_summary?: string | null;
  likely_visitor_tasks: string[];
  top_pointer_targets: WebsiteOrbPointerRecord[];
  secondary_pointer_targets: WebsiteOrbPointerRecord[];
  relevant_navigation: Record<string, string>;
  relevant_guiderails: string[];
}

export interface WebsiteOrbTtsResponse {
  text: string;
  tts_audio_url?: string | null;
  tts_provider?: string | null;
  tts_error?: string | null;
}

export interface WebsiteOrbCapabilities {
  schema: string;
  orb_id: string;
  role: string;
  cognition_source: string;
  current_orb_source_available: boolean;
  legacy_electron_source_available: boolean;
  tesseract: {
    available: boolean;
    binary?: string | null;
    tessdata_prefix?: string | null;
    website_runtime?: {
      available: boolean;
      binary?: string | null;
      tessdata_prefix?: string | null;
      purpose?: string;
    };
    windows_app_runtime?: {
      available: boolean;
      binary?: string | null;
      purpose?: string;
    };
  };
  local_llm?: {
    configured: boolean;
    ready: boolean;
    model?: string | null;
    checked_at?: string | null;
    error?: string | null;
  };
  chrome_devtools_mcp: {
    enabled: boolean;
    public_enabled: boolean;
    available: boolean;
    runner: string;
  };
  orb_desktop_mcp?: {
    enabled: boolean;
    available: boolean;
    root: string;
    server: string;
    runner: string;
  };
  voice: Record<string, string | boolean>;
  tools: string[];
}

export interface OrbToolCatalog {
  schema: string;
  orb_id: string;
  scope: string;
  customer_id: string;
  product_boundary?: string;
  tools: Array<{
    id: string;
    label: string;
    description: string;
    requires_project: boolean;
    available: boolean;
    availability:
      | 'installed'
      | 'registered'
      | 'disabled'
      | 'owner_only'
      | 'runtime_allowed'
      | 'temporarily_authorized'
      | 'blocked';
    installed: boolean;
    registered: boolean;
    owner_only: boolean;
    declared_capability: string;
    blocked_reason: string;
    activation_chain: string[];
    mcp_tools?: string[];
    legacy_ids?: string[];
  }>;
  capabilities: WebsiteOrbCapabilities;
}

export interface OrbToolResult {
  schema: string;
  status: string;
  tool: string;
  mcp_tool?: string;
  generated_at: string;
  project_id?: string;
  summary?: unknown;
  result?: unknown;
  transcript?: string;
  spoken_output?: string;
  llm_source?: string;
  cognitive_pulse?: Record<string, unknown> | null;
}

export interface OrbMemoryItem {
  id: string;
  category: string;
  key: string;
  value: string;
  source: string;
  confidence: number;
  enabled: boolean;
  metadata: Record<string, unknown>;
  created_at?: string | null;
  updated_at?: string | null;
  expires_at?: string | null;
}

export interface OrbMemorySummary {
  scope: 'authenticated_user' | 'anonymous_session';
  durable: boolean;
  user_id?: string;
  items: OrbMemoryItem[];
  recent_context?: Record<string, unknown> | null;
  retention?: Record<string, unknown>;
  policy?: string;
}

export interface GA4FullReport {
  traffic_overview?: {
    totals?: Record<string, number>;
    data?: Array<Record<string, string | number>>;
  };
  top_pages?: Array<Record<string, string | number>>;
  search_queries?: Array<Record<string, string | number>>;
  device_breakdown?: Array<Record<string, string | number>>;
  country_breakdown?: Array<Record<string, string | number>>;
  conversion_events?: Array<Record<string, string | number>>;
}

export const api = {
  getOrbsStage: (projectId: string) =>
    request<OrbsStageSnapshot>(`/api/projects/${projectId}/orbs-stage`),
  submitOrbsStageAction: (projectId: string, payload: OrbsActionSubmission, idempotencyKey: string) =>
    request<OrbsStageSnapshot>(`/api/projects/${projectId}/orbs-stage/actions`, {
      method: 'POST',
      headers: { 'Idempotency-Key': idempotencyKey },
      body: JSON.stringify(payload)
    }),
  getOrbDock: (projectId: string) =>
    request<OrbDockStation>(`/api/projects/${projectId}/orb-dock`),
  saveOrbDock: (projectId: string, payload: DockConfiguration) =>
    request<OrbDockStation>(`/api/projects/${projectId}/orb-dock`, {
      method: 'PUT',
      body: JSON.stringify(payload)
    }),
  compileOrbDock: (projectId: string) =>
    request<OrbDockStation>(`/api/projects/${projectId}/orb-dock/compile`, { method: 'POST' }),
  publishOrbDock: (projectId: string) =>
    request<OrbDockStation>(`/api/projects/${projectId}/orb-dock/publish`, { method: 'POST' }),
  getOrbDockOllama: (projectId: string) =>
    request<DockOllamaStatus>(`/api/projects/${projectId}/orb-dock/ollama`),
  pullOrbDockOllamaModel: (projectId: string, model: string) =>
    request<{ status: string; model: string }>(`/api/projects/${projectId}/orb-dock/ollama/pull`, {
      method: 'POST',
      body: JSON.stringify({ model })
    }),
  websiteOrbVoice: (
    audio: Blob,
    signal?: AbortSignal,
    context?: { project_id?: string | null; target_url?: string | null }
  ) => {
    const formData = new FormData();
    formData.append('audio', audio, 'website-orb.webm');
    if (context?.project_id) {
      formData.append('project_id', context.project_id);
    }
    if (context?.target_url) {
      formData.append('target_url', context.target_url);
    }
    return uploadForm<WebsiteOrbVoiceResponse>('/api/orb/website-voice', formData, { signal });
  },
  websiteOrbText: (
    transcript: string,
    synthesizeTts = true,
    signal?: AbortSignal,
    context?: { project_id?: string | null; target_url?: string | null }
  ) =>
    request<WebsiteOrbVoiceResponse>('/api/orb/website-text', {
      method: 'POST',
      body: JSON.stringify({ transcript, synthesize_tts: synthesizeTts, ...(context || {}) }),
      signal
    }),
  websiteOrbTts: (text: string, signal?: AbortSignal) =>
    request<WebsiteOrbTtsResponse>('/api/orb/tts', {
      method: 'POST',
      body: JSON.stringify({ text }),
      signal
    }),
  websiteOrbPointerMap: (domain?: string, signal?: AbortSignal) => {
    const query = domain ? `?domain=${encodeURIComponent(domain)}` : '';
    return request<WebsiteOrbPointerMap>(`/api/orb/pointer-map${query}`, { signal });
  },
  websiteOrbPageCapsule: (targetUrl: string, signal?: AbortSignal) =>
    request<WebsiteOrbPageCapsule>(`/api/orb/page-capsule?target_url=${encodeURIComponent(targetUrl)}`, { signal }),
  orbMediaUrl: mediaUrl,
  websiteOrbCapabilities: () => request<WebsiteOrbCapabilities>('/api/orb/capabilities'),
  orbToolCatalog: () => request<OrbToolCatalog>('/api/orb/tools/catalog'),
  runOrbTool: (payload: {
    tool: string;
    project_id?: string | null;
    target_url?: string | null;
    transcript?: string | null;
    mcp_tool?: string | null;
    params?: Record<string, unknown>;
  }) =>
    request<OrbToolResult>('/api/orb/tools/run', {
      method: 'POST',
      body: JSON.stringify(payload)
    }),
  orbMemory: () => request<OrbMemorySummary>('/api/orb/memory'),
  upsertOrbMemory: (payload: {
    category: string;
    key: string;
    value: string;
    source?: string;
    confidence?: number;
    enabled?: boolean;
    metadata?: Record<string, unknown>;
  }) =>
    request<OrbMemoryItem>('/api/orb/memory', {
      method: 'POST',
      body: JSON.stringify(payload)
    }),
  clearOrbMemoryItem: (memoryId: string | number) =>
    request<{ status: string; id: string }>(`/api/orb/memory/${memoryId}`, { method: 'DELETE' }),
  clearOrbMemory: () =>
    request<{ status: string; deleted_memory_items: number }>('/api/orb/memory', { method: 'DELETE' }),
  publicPreflight: (websiteUrl: string) =>
    request<PublicPreflightReport>('/api/public/preflight', {
      method: 'POST',
      body: JSON.stringify({ website_url: websiteUrl })
    }),
  createOrbsGuestSession: (payload: {
    landing_intent: string;
    selected_tier_interest?: string | null;
    website_url?: string | null;
    original_cta_destination: string;
    current_onboarding_step: string;
    completed_onboarding_steps: string[];
    non_sensitive_questionnaire_answers: Record<string, unknown>;
  }) =>
    request<OrbsGuestSession>('/api/orbs/guest-sessions', {
      method: 'POST',
      body: JSON.stringify(payload)
    }),
  mergeOrbsGuestSession: (guestSessionId: string, payload: {
    schema: 'orb_weaver.orbs_guest_merge_request.v1';
    guest_session_id: string;
    idempotency_key: string;
    project_display_name?: string | null;
  }) =>
    request<OrbsGuestMergeResult>(`/api/orbs/guest-sessions/${encodeURIComponent(guestSessionId)}/merge`, {
      method: 'POST',
      body: JSON.stringify(payload)
    }),
  signup: (payload: {
    email: string;
    password: string;
    full_name: string;
    business_name?: string | null;
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
    guest_session_id?: string | null;
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
  listMarketplaceItems: async (category?: string) => {
    const products = await request<MarketplaceProductResponse[]>(
      `/api/marketplace/public/products${category ? `?category=${encodeURIComponent(category)}` : ''}`
    );
    return products.map(normalizeMarketplaceProduct);
  },
  getCart: () => request<CartPayload>('/api/cart'),
  upsertCartItem: (payload: { sku: string; quantity: number }) =>
    request<CartPayload>('/api/cart/items', {
      method: 'POST',
      body: JSON.stringify(payload)
    }),
  deleteCartItem: (sku: string) => request<CartPayload>(`/api/cart/items/${encodeURIComponent(sku)}`, { method: 'DELETE' }),
  createCheckout: (provider: CheckoutProvider) =>
    request<CheckoutOrder>('/api/cart/checkout', {
      method: 'POST',
      body: JSON.stringify({ provider })
    }),
  listCheckoutOrders: () => request<CheckoutOrder[]>('/api/checkout/orders'),
  adminListCustomers: () => request<AdminCustomer[]>('/api/admin/customers'),
  adminExportCustomersToCaliCrm: () =>
    request<{
      status: string;
      record_count: number;
      path: string;
      crm_url: string;
    }>('/api/admin/cali-crm/export-customers', {
      method: 'POST'
    }),
  adminListCaliCrmContacts: () =>
    request<{ schema: string; database_path: string; dossier_root: string; contacts: CaliCrmContact[] }>('/api/admin/cali-crm/contacts'),
  adminCreateCaliCrmContact: (payload: {
    display_name: string;
    contact_type?: string;
    company_name?: string | null;
    role_title?: string | null;
    email?: string | null;
    phone?: string | null;
    website?: string | null;
    relationship_status?: string;
    tags?: string[];
    notes?: string;
  }) =>
    request<{ schema: string; database_path: string; contact: CaliCrmContact; dossier: { path: string; manifest: string; folders: string[] } }>('/api/admin/cali-crm/contacts', {
      method: 'POST',
      body: JSON.stringify(payload)
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
  listLifecycleJobs: (projectId: string) =>
    request<LifecycleJob[]>(`/api/projects/${projectId}/lifecycle-jobs`),
  startLifecycleJob: (
    projectId: string,
    jobType: LifecycleJobType,
    config: { max_pages?: number; delay?: number; max_depth?: number; seed_urls?: string[]; include_admin_sections?: boolean; source_job_id?: number } = {}
  ) =>
    request<LifecycleJob>(`/api/projects/${projectId}/lifecycle-jobs/${jobType.toLowerCase().replace(/_/g, '-')}`, {
      method: 'POST',
      body: JSON.stringify(config)
    }),
  getLifecycleJob: (jobId: string) => request<LifecycleJob>(`/api/lifecycle-jobs/${jobId}`),
  cancelLifecycleJob: (jobId: string) =>
    request<LifecycleJob>(`/api/lifecycle-jobs/${jobId}/cancel`, { method: 'POST' }),
  decideLifecycleReviewItem: (jobId: string, itemId: string, decision: 'approve' | 'reject' | 'waive', notes = '') =>
    request<{ job: LifecycleJob; review_item: LifecycleReviewItem }>(
      `/api/lifecycle-jobs/${jobId}/review-items/${itemId}/decision`,
      { method: 'POST', body: JSON.stringify({ decision, notes }) }
    ),
  decidePointerAuthority: (jobId: string, targetId: string, decision: 'approve' | 'reject', notes = '') =>
    request<{ job: LifecycleJob; target_id: string; decision: string; signature_hash: string; pointer: WebsiteOrbPointerRecord }>(
      `/api/lifecycle-jobs/${jobId}/pointers/${encodeURIComponent(targetId)}/authority`,
      { method: 'POST', body: JSON.stringify({ decision, notes }) }
    ),
  verifyLifecycleEvidence: (jobId: string) =>
    request<{ valid: boolean; previous_manifest_chain_valid: boolean }>(`/api/lifecycle-jobs/${jobId}/evidence/verify`),
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
  cancelCrawlJob: (jobId: string) =>
    request<CrawlJob>(`/api/crawl-jobs/${jobId}/cancel`, { method: 'POST' }),
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
      latest_crawl?: CrawlJob | null;
      latest_audit?: AuditReportResponse | null;
      audit_delta?: AuditDelta | null;
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
