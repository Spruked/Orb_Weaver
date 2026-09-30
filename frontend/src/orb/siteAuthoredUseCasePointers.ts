import type { WebsiteOrbPointerRecord } from '../services/api';

// Owner-authored identities for the eight public use-case cards. These are not
// coordinates and are not blanket authority: each exact card and heading must
// be present in the live DOM, then Pointer validates it again before Point/Ping.
export const USE_CASE_POINTER_TITLES = [
  'Product discovery',
  'Sales and conversion',
  'Forms and applications',
  'Bookings and appointments',
  'Customer support',
  'Onboarding',
  'Guided website tours',
  'Complex decisions',
] as const;

const SECURITY_QUICK_TITLES = [
  'What can the ORB do?',
  'What can it NOT do?',
  "Can it control my customer's computer?",
  'Can it click buttons automatically?',
  'Can it purchase things?',
  'Can it submit forms?',
] as const;

const SECURITY_TRUST_TITLES = [
  'Control Plane',
  'Verification',
  'Stage Governor',
  'Tool Permissions',
  'Pointer Verification',
  'Visitor Always Remains in Control',
] as const;

export function observedSecurityPointerRecords(): WebsiteOrbPointerRecord[] {
  if (window.location.pathname !== '/security') return [];
  const records: WebsiteOrbPointerRecord[] = [];
  const addRecord = (targetId: string, title: string, expectedTag: 'ARTICLE' | 'SECTION' = 'ARTICLE') => {
    const card = document.querySelector<HTMLElement>(`[data-orb-target="${targetId}"]`);
    if (!card || card.tagName !== expectedTag) return;
    const visibleText = card.textContent?.replace(/\s+/g, ' ').trim() || '';
    if (!visibleText.includes(title)) return;
    records.push({
      target_id: targetId,
      page_route: '/security',
      target_type: 'other',
      baseRank: 4,
      rankEvidence: ['site_owner_authored_security_box', 'exact_rendered_box_text_match'],
      rankSource: 'site_authored_live_witness',
      pointer_class: 'live_guidance',
      meaning: `security box: ${title}`,
      direct_aliases: [title],
      intent_aliases: ['security', 'trust architecture', title],
      content_fingerprint: `security:${targetId}:${title.toLowerCase()}`,
      semantic_locator: `[data-orb-target="${targetId}"]`,
      structural_context: { tag: 'article' },
      confidence: 1,
      confidence_class: 'VERIFIED',
      runtime_policy: {
        may_point: true,
        may_click: false,
        may_navigate: false,
        requires_live_verification: true,
        reason: 'exact_site_authored_security_box_live_witness',
      },
    });
  };
  SECURITY_QUICK_TITLES.forEach((title, index) => addRecord(`security-quick-${index + 1}`, title));
  SECURITY_TRUST_TITLES.forEach((title, index) => addRecord(`security-trust-${index + 1}`, title));
  addRecord('security-bottom-line', 'The ORB helps visitors move forward.', 'SECTION');
  return records;
}

export function observedLeadPagePointerRecords(): WebsiteOrbPointerRecord[] {
  const isBeta = window.location.pathname === '/founding-beta';
  const isInvestor = window.location.pathname === '/investor-contact';
  if (!isBeta && !isInvestor) return [];
  const targetId = isBeta ? 'tour-founding-beta' : 'tour-investor-contact';
  const main = document.querySelector<HTMLElement>(`[data-orb-target="${targetId}"]`);
  const heading = main?.querySelector('h1');
  if (!main || main.tagName !== 'MAIN' || !heading) return [];
  const label = isBeta ? 'Founding Beta application' : 'Investor conversation';
  return [{
    target_id: targetId,
    page_route: window.location.pathname,
    target_type: 'other',
    baseRank: 5,
    rankEvidence: ['site_owner_authored_lead_page_target', 'live_form_page_heading'],
    rankSource: 'site_authored_live_witness',
    pointer_class: 'live_guidance',
    meaning: label,
    direct_aliases: [label, isBeta ? 'beta signup' : 'investor contact'],
    intent_aliases: ['next step', 'contact', 'signup assistance'],
    content_fingerprint: `${targetId}:${heading.textContent?.replace(/\s+/g, ' ').trim().toLowerCase()}`,
    semantic_locator: `[data-orb-target="${targetId}"]`,
    structural_context: { tag: 'main' },
    confidence: 1,
    confidence_class: 'VERIFIED',
    runtime_policy: {
      may_point: true,
      may_click: false,
      may_navigate: false,
      requires_live_verification: true,
      reason: 'exact_site_authored_lead_page_live_witness',
    },
  }];
}

export function observedDesktopOrbPointerRecords(): WebsiteOrbPointerRecord[] {
  if (window.location.pathname !== '/now/desktop-orb') return [];
  const targetId = 'desktop-orb-coming-soon';
  const heading = document.querySelector<HTMLElement>(`[data-orb-target="${targetId}"]`);
  if (!heading || heading.tagName !== 'H1') return [];
  return [{
    target_id: targetId,
    page_route: '/now/desktop-orb',
    target_type: 'heading',
    baseRank: 5,
    rankEvidence: ['site_owner_authored_desktop_orb_tour_target', 'coming_soon_product_statement'],
    rankSource: 'site_authored_live_witness',
    pointer_class: 'live_guidance',
    meaning: 'heading: Desktop ORB Assistant coming soon',
    direct_aliases: ['Desktop ORB Assistant coming soon', 'Desktop ORB coming soon'],
    intent_aliases: ['desktop orb', 'desktop diagnostics'],
    content_fingerprint: 'desktop-orb-assistant-coming-soon',
    semantic_locator: `[data-orb-target="${targetId}"]`,
    structural_context: { tag: 'h1' },
    confidence: 1,
    confidence_class: 'VERIFIED',
    runtime_policy: {
      may_point: true,
      may_click: false,
      may_navigate: false,
      requires_live_verification: true,
      reason: 'exact_site_authored_desktop_orb_live_witness',
    },
  }];
}

export function observedUseCasePointerRecords(): WebsiteOrbPointerRecord[] {
  if (window.location.pathname !== '/use-cases') return [];
  return USE_CASE_POINTER_TITLES.flatMap((title, index) => {
    const targetId = `use-case-${index + 1}`;
    const selector = `[data-orb-target="${targetId}"]`;
    const card = document.querySelector<HTMLElement>(selector);
    const heading = card?.querySelector<HTMLElement>('h3');
    if (!card || !heading || heading.textContent?.replace(/\s+/g, ' ').trim() !== title) return [];
    return [{
      target_id: targetId,
      page_route: '/use-cases',
      target_type: 'other',
      baseRank: 4,
      rankEvidence: ['site_owner_authored_use_case_tour_target', 'exact_rendered_heading_match'],
      rankSource: 'site_authored_live_witness',
      pointer_class: 'live_guidance',
      meaning: `use case: ${title}`,
      direct_aliases: [title],
      intent_aliases: [title],
      content_fingerprint: title.toLowerCase(),
      semantic_locator: selector,
      structural_context: { tag: 'article' },
      confidence_class: 'VERIFIED',
      runtime_policy: {
        may_point: true,
        may_click: false,
        may_navigate: false,
        requires_live_verification: true,
        reason: 'exact_site_authored_heading_live_witness',
      },
    }];
  });
}
