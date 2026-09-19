import { authStore } from './api';

function defaultApiBaseUrl() {
  if (typeof window === 'undefined') return '';
  const { hostname, port, protocol } = window.location;
  const apiHostname = hostname === '0.0.0.0' ? '127.0.0.1' : hostname;
  const pairedApiPorts: Record<string, string> = {
    '16510': '16500',
    '16610': '16600',
    '16666': '19667',
    '16667': '19667',
    '16777': '16776',
  };
  const isLocalOrPrivateHost =
    port === '16510' ||
    hostname === 'localhost' ||
    hostname === '127.0.0.1' ||
    hostname === '0.0.0.0' ||
    hostname === '::1' ||
    hostname.startsWith('192.168.') ||
    hostname.startsWith('10.') ||
    /^172\.(1[6-9]|2\d|3[0-1])\./.test(hostname);
  return isLocalOrPrivateHost ? `${protocol}//${apiHostname}:${pairedApiPorts[port] || '16500'}` : '';
}

const API_BASE_URL = process.env.REACT_APP_API_URL || defaultApiBaseUrl();

export interface CustomerReviewPackageStatus {
  schema: 'orb_weaver.customer_review_package.v1';
  eligible: boolean;
  ready: boolean;
  reason?: string;
  crawl_id?: string;
  audit_id?: string;
  files?: string[];
  entitlement?: {
    tier: 'package_1' | 'package_2';
    price_cents: number;
    sku?: string | null;
    name?: string | null;
    checkout_order_id: string;
    payment_verified_at?: string | null;
  };
  required_paid_packages?: Array<{ tier: string; price_cents: number }>;
}

function authHeaders(): HeadersInit {
  const token = authStore.getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function getCustomerReviewPackageStatus(projectId: string): Promise<CustomerReviewPackageStatus> {
  const response = await fetch(`${API_BASE_URL}/api/projects/${encodeURIComponent(projectId)}/customer-review-package`, {
    headers: authHeaders(),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail || response.statusText || 'Could not load customer review package status.');
  }
  return response.json();
}

export async function downloadCustomerReviewPackage(projectId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/projects/${encodeURIComponent(projectId)}/customer-review-package/download`, {
    headers: authHeaders(),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail || response.statusText || 'Could not download customer review package.');
  }
  const blob = await response.blob();
  const disposition = response.headers.get('Content-Disposition') || '';
  const filenameMatch = disposition.match(/filename="?([^";]+)"?/i);
  const filename = filenameMatch?.[1] || `orb-weaver-review-${projectId}.zip`;
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
