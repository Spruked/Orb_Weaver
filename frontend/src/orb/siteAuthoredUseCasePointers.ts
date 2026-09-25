import type { WebsiteOrbPointerRecord } from '../services/api';

// Owner-authored identities for the eight public use-case headings. These are
// not coordinates and are not blanket authority: each exact heading must be
// present in the live DOM, then Pointer validates it again before Point/Ping.
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

export function observedUseCasePointerRecords(): WebsiteOrbPointerRecord[] {
  if (window.location.pathname !== '/use-cases') return [];
  return USE_CASE_POINTER_TITLES.flatMap((title, index) => {
    const targetId = `use-case-${index + 1}`;
    const selector = `[data-orb-target="${targetId}"] h3`;
    const heading = document.querySelector<HTMLElement>(selector);
    if (!heading || heading.textContent?.replace(/\s+/g, ' ').trim() !== title) return [];
    return [{
      target_id: targetId,
      page_route: '/use-cases',
      target_type: 'heading',
      baseRank: 4,
      rankEvidence: ['site_owner_authored_use_case_tour_target', 'exact_rendered_heading_match'],
      rankSource: 'site_authored_live_witness',
      pointer_class: 'live_guidance',
      meaning: `heading: ${title}`,
      direct_aliases: [title],
      intent_aliases: [title],
      content_fingerprint: title.toLowerCase(),
      semantic_locator: selector,
      structural_context: { tag: 'h3' },
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
