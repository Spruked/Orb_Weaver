export interface ActiveOrbProjectContext {
  project_id: string;
  canonical_domain: string;
  canonical_base_url: string;
  selected_crawl_job_id?: string | null;
  active_customer_route: string;
}

const STORAGE_KEY = 'orb_weaver.active_orb_project_context';
export const ACTIVE_ORB_PROJECT_CONTEXT_EVENT = 'orb-weaver:active-orb-project-context';

export function normalizeOrbDomain(rawDomain?: string | null): string {
  const value = String(rawDomain || '').trim();
  if (!value) return '';
  try {
    return new URL(/^https?:\/\//i.test(value) ? value : `https://${value}`).hostname.toLowerCase();
  } catch {
    return value.replace(/^https?:\/\//i, '').replace(/\/.*$/, '').toLowerCase();
  }
}

export function canonicalOrbBaseUrl(rawDomain?: string | null): string {
  const domain = normalizeOrbDomain(rawDomain);
  return domain ? `https://${domain}` : '';
}

export function normalizeCustomerRoute(rawRoute?: string | null): string {
  const value = String(rawRoute || '/').trim() || '/';
  if (/^https?:\/\//i.test(value)) {
    try {
      const parsed = new URL(value);
      return `${parsed.pathname || '/'}${parsed.search || ''}${parsed.hash || ''}`;
    } catch {
      return '/';
    }
  }
  return value.startsWith('/') ? value : `/${value}`;
}

export function buildCustomerPageCapsuleUrl(context?: ActiveOrbProjectContext | null): string {
  if (!context?.canonical_base_url) return window.location.href;
  const base = context.canonical_base_url.endsWith('/')
    ? context.canonical_base_url
    : `${context.canonical_base_url}/`;
  const route = normalizeCustomerRoute(context.active_customer_route);
  return new URL(route.replace(/^\//, ''), base).toString();
}

function coerceContext(value: unknown): ActiveOrbProjectContext | null {
  if (!value || typeof value !== 'object') return null;
  const candidate = value as Partial<ActiveOrbProjectContext>;
  const canonicalDomain = normalizeOrbDomain(candidate.canonical_domain);
  const canonicalBaseUrl = candidate.canonical_base_url || canonicalOrbBaseUrl(canonicalDomain);
  if (!candidate.project_id || !canonicalDomain || !canonicalBaseUrl) return null;
  return {
    project_id: String(candidate.project_id),
    canonical_domain: canonicalDomain,
    canonical_base_url: canonicalBaseUrl.replace(/\/$/, ''),
    selected_crawl_job_id: candidate.selected_crawl_job_id ? String(candidate.selected_crawl_job_id) : null,
    active_customer_route: normalizeCustomerRoute(candidate.active_customer_route),
  };
}

export function getActiveOrbProjectContext(): ActiveOrbProjectContext | null {
  try {
    return coerceContext(JSON.parse(window.localStorage.getItem(STORAGE_KEY) || 'null'));
  } catch {
    return null;
  }
}

export function setActiveOrbProjectContext(context: ActiveOrbProjectContext): ActiveOrbProjectContext | null {
  const normalized = coerceContext(context);
  if (!normalized) return null;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(normalized));
  window.dispatchEvent(new CustomEvent(ACTIVE_ORB_PROJECT_CONTEXT_EVENT, { detail: normalized }));
  return normalized;
}
