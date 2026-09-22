export type VerifiedRouteNavigation = {
  route: string;
  pointerTargetId: string;
  label: string;
  aliases: readonly string[];
};

// These are first-party, owner-authored routes. They are not crawler guesses:
// the arrival handler still requires the live pointer registry and DOM check
// before presenting any target on the destination page.
export const VERIFIED_ROUTE_NAVIGATIONS: readonly VerifiedRouteNavigation[] = [
  { route: '/lidar-guidance', pointerTargetId: 'tour-lidar-guidance', label: 'LiDAR visual navigation', aliases: ['navigation page', 'lidar navigation', 'lidar guidance', 'visual navigation'] },
  { route: '/features', pointerTargetId: 'tour-features', label: 'Website ORB features', aliases: ['features page', 'orb features'] },
  { route: '/how-it-works', pointerTargetId: 'tour-how-it-works', label: 'how Orb Weaver works', aliases: ['how it works', 'how does it work'] },
  { route: '/security', pointerTargetId: 'tour-security', label: 'security', aliases: ['security page', 'security'] },
  { route: '/weaving', pointerTargetId: 'tour-weaving', label: 'weaving', aliases: ['weaving page', 'weaving'] },
  { route: '/web-weave', pointerTargetId: 'tour-web-weave', label: 'Web Weave', aliases: ['web weave', 'web-weave'] },
  { route: '/now/desktop-orb', pointerTargetId: 'tour-desktop-orb', label: 'Desktop ORB', aliases: ['desktop orb', 'desktop version', 'diagnostics page'] },
  { route: '/preflight', pointerTargetId: 'tour-preflight', label: 'Preflight', aliases: ['preflight page', 'preflight'] },
  { route: '/privacy', pointerTargetId: 'tour-privacy', label: 'privacy', aliases: ['privacy page', 'privacy'] },
  { route: '/terms', pointerTargetId: 'tour-terms', label: 'terms', aliases: ['terms page', 'terms'] },
];

const DIRECT_ROUTE_VERBS = /\b(take me|bring me|go to|navigate to|open|show me|visit)\b/i;

export const resolveDirectRouteNavigation = (transcript: string): VerifiedRouteNavigation | null => {
  const normalized = transcript.replace(/\s+/g, ' ').trim().toLowerCase();
  if (!DIRECT_ROUTE_VERBS.test(normalized)) return null;
  return VERIFIED_ROUTE_NAVIGATIONS.find((entry) => (
    entry.aliases.some((alias) => normalized.includes(alias))
  )) || null;
};
