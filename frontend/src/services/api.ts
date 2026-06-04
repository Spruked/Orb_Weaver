const isLocalHost =
  typeof window !== 'undefined' && ['localhost', '127.0.0.1'].includes(window.location.hostname);
const API_BASE_URL = process.env.REACT_APP_API_URL || (isLocalHost ? 'http://127.0.0.1:16500' : '');
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

async function download(path: string, filename: string) {
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
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
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
  business_name: string;
  contact_name?: string | null;
  phone?: string | null;
  status: string;
  created_at?: string | null;
}

export interface AuthResponse {
  token: string;
  customer: Customer;
}

export interface CrawlConfig {
  max_pages: number;
  delay: number;
  max_depth: number;
  competitor_domains?: string[];
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
  status: string;
  config?: CrawlConfig;
  created_at?: string;
  start_time?: string;
  end_time?: string;
  pages_crawled?: number;
  pages_found?: number;
  errors_count?: number;
  stats?: Record<string, number | boolean>;
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
  signup: (payload: {
    email: string;
    password: string;
    business_name: string;
    contact_name?: string | null;
    phone?: string | null;
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
  listProjects: () => request<Project[]>('/api/projects'),
  createProject: (project: { name?: string | null; domain: string; ga4_property_id?: string | null }) =>
    request<Project>('/api/projects', {
      method: 'POST',
      body: JSON.stringify(project)
    }),
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
  getCrawlJob: (jobId: string) => request<CrawlJob>(`/api/crawl-jobs/${jobId}`),
  getCrawlPages: (jobId: string) => request<PagesResponse>(`/api/crawl-jobs/${jobId}/pages?limit=200`),
  runAudit: (jobId: string) =>
    request<{ audit_id: string; status: string; message: string }>(`/api/crawl-jobs/${jobId}/audit`, {
      method: 'POST'
    }),
  getAuditReport: (auditId: string) => request<AuditReportResponse>(`/api/audit-reports/${auditId}`),
  getReportCompiler: (projectId: string) => request<ReportCompilerPayload>(`/api/projects/${projectId}/report-compiler`),
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
  auditPdf: (auditId: string) => `${API_BASE_URL}/api/audit-reports/${auditId}/export/pdf`
};

export const downloads = {
  crawlCsv: (jobId: string) => download(`/api/crawl-jobs/${jobId}/export/csv`, `crawl_${jobId}.csv`),
  auditCsv: (auditId: string) => download(`/api/audit-reports/${auditId}/export/csv`, `audit_${auditId}.csv`),
  auditPdf: (auditId: string) => download(`/api/audit-reports/${auditId}/export/pdf`, `audit_${auditId}.pdf`)
};
