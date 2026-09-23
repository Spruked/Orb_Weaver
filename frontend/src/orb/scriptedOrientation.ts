export type ScriptedOrientationStep = {
  route?: string;
  selector?: string;
  pointerTargetIds?: readonly string[];
  simulation?: 'product_price_research' | 'desktop_diagnostics';
  /** Audit batches are deliberately prime-sized to make omissions obvious. */
  auditTaskCount?: 3 | 5 | 7 | 11;
  /** Ends authored narration and returns control to the guest-led ORB. */
  handoffToLiveConversation?: boolean;
  /** Scroll the page independently while this stop is being narrated. */
  scrollToEndDuringSpeech?: boolean;
  text?: string;
};

// The landing visit is deliberately linear. Cognition warms alongside this
// authored narration, then takes questions only after every core concept has
// been introduced.
export const LANDING_FULL_TOUR_SCRIPT: readonly ScriptedOrientationStep[] = [
  {
    selector: '#beat-1',
    pointerTargetIds: ['orb-weaver-suite-logo'],
    text: 'Welcome to the guided Orb Weaver tour. A web is woven, thread by thread, on purpose — and so is real website intelligence. Nothing here is accidental or improvised. I will walk you through how Orb Weaver works as a governed intelligence layer that sits atop a website, interpreting its structure, relationships, and purpose. When we reach the end of this authored sequence, I will be ready to answer any questions you have from verified knowledge rather than free-form invention.',
  },
  {
    selector: '#weaver-first-encounter',
    pointerTargetIds: ['what_weaver_does', 'what_to_say', 'watch_weaver_guide', 'interrupt_or_guide'],
    text: 'I am Weaver, your Website ORB host. I am not a general-purpose chatbot floating over a page. I am a site-specific intelligence whose cognition is grounded in verified page evidence, a governed knowledge base, and explicitly approved relationships. I understand this website, answer only from what can be proven, and guide you to the right place when showing is faster than explaining. You remain in full control throughout the experience; I never take silent actions or assume authority I have not been given.',
  },
  {
    selector: '#beat-2',
    text: 'For years, a crawl has told us which pages exist on a site. That is the easy, structural part: list the URLs, extract the text, build a search index. A weave goes further. It discovers the purpose those pages share, maps the relationships between them, and identifies the decisions, policies, products, and journeys that give the site its actual meaning. Crawl is inventory. Weave is understanding.',
  },
  {
    selector: '#beat-3',
    text: 'Your website is not just a stack of pages. It is a living network of products, services, people, policies, questions, and decisions. Products connect to policies. Questions connect to answers. People connect to decisions. Pages belong to visitor journeys. That relationship map is where useful intelligence actually lives. Most tools never look past the surface text; Orb Weaver is built to read the connections.',
  },
  {
    selector: '#beat-4',
    text: 'Here is the core problem with most website assistants: they sound confident while they are guessing. Ask one a pricing question and you will often get an answer that feels plausible but may be months out of date, pulled from a training corpus rather than the live site. That is not intelligence. That is a language model rolling dice. Orb Weaver refuses that pattern.',
  },
  {
    selector: '#beat-5',
    text: 'I do not work that way. Every answer I give traces back to something actually verified about this website — not a hunch, not a statistically likely paragraph, not an external assumption. If I do not know something, I say so and I find out from the governed evidence instead of inventing a fluent reply. The difference is the difference between a chatbot and a site-specific ORB.',
  },
  {
    selector: '#beat-6',
    text: 'That is how trust is built here — not by promising I am always right, but by proving the provenance of every answer. Once that foundation of verified state is in place, the rest of what an ORB can do for a visitor becomes far more powerful and far safer. Trust is not a marketing claim; it is an operating boundary I am not allowed to cross.',
  },
  {
    selector: '#beat-7',
    text: 'When the weave is complete, I can greet a visitor with context, guide them with precision, understand what they are trying to accomplish, help them past friction, and bring them to a useful finish instead of leaving them to wander and hope they find what they need. The weave turns a collection of pages into a guided environment.',
  },
  {
    selector: '#beat-8',
    text: 'None of that guidance is improvised. It is governed by verified state, bounded permissions, and your explicit control at every step. I can point to a live target only after the geometry has been validated. I can explain only what the evidence supports. I never silently take actions, invent authority, or convert guidance into unapproved automation. Trust is a rule I do not get to break.',
  },
  {
    selector: '#beat-9',
    text: 'Orb Weaver builds that intelligence through the 28-Weave process: explicit, structured work that compiles website knowledge, live pointer intelligence, and a learning system that improves over time. Its distinct weaves include a priori knowledge (what the site declares), a posteriori learning (what visitors reveal), multi-funnel continuity (journey stitching across sessions and paths), and pointer intelligence (LiDAR-inspired geometry that lets me move and highlight with precision rather than guess).',
  },
  {
    selector: '#weave-business-outcomes',
    text: 'The practical outcomes of a completed weave are measurable: clearer visitor journeys, less abandonment, stronger trust, better engagement, and faster decisions — both for the people visiting the site and for the teams that serve them. Orb Weaver is not a novelty layer; it is an intelligence system designed to improve the real economics of a website.',
  },
  {
    selector: '#beat-10',
    pointerTargetIds: ['run-free-preflight'],
    text: 'The first step for any site is Preflight: a free readiness scan that inspects what can be woven, identifies gaps, and shows the operator what intelligence is possible before any full assembly begins. It is safe, non-invasive, and evidence-based. From here I will take you through the rest of the public site so you can see the system in context, right up to account creation when you are ready.',
  },
];

// Kept as an alias for callers that still use the previous exported name.
export const LANDING_OPENING_SCRIPT = LANDING_FULL_TOUR_SCRIPT;

// Native public pages only. Marketplace lives on a separately redirected
// surface, so it cannot preserve this in-browser tour session or its proven
// final handoff to account creation.
export const SITE_TOUR_SCRIPT: readonly ScriptedOrientationStep[] = [
  ...LANDING_FULL_TOUR_SCRIPT,
  {
    route: '/features',
    pointerTargetIds: ['tour-features'],
    text: 'Now we move into the Website ORB feature set — the place where the experience becomes practical. Here I can recognize a visitor’s context, explain what is actually on the page from verified evidence, and visibly guide them toward a next step that has been checked against the live site. The important point is not a chat bubble floating over a website. It is a guided environment built on real page evidence, governed permissions, and continuous validation.',
  },
  {
    pointerTargetIds: ['tour-features'],
    simulation: 'product_price_research',
    auditTaskCount: 3,
    text: 'Watch this Morb research deployment. I am staging three independently auditable product-and-price research tasks. Morbs are single-function researchers: they investigate a bounded question and return evidence for review. The batch size is deliberately prime so any omission is obvious. In this demo the work stays entirely on-site, makes no live price claims, and initiates no purchase. It simply shows how specialized, auditable research can extend a guided visitor experience without breaking the trust boundary.',
  },
  {
    route: '/lidar-guidance',
    pointerTargetIds: ['tour-lidar-guidance'],
    text: 'This is the navigation system behind the movement you are watching. I build a live, LiDAR-inspired two-dimensional map of the page, reconcile it with verified targets, and validate the geometry again before I point. That is why I can leave the text I was reading, travel toward the correct control, and ping it with precision. I do not guess coordinates or click on the visitor’s behalf. Every movement is checked against current page geometry so the guidance remains trustworthy even as the layout changes.',
  },
  {
    route: '/how-it-works',
    pointerTargetIds: ['tour-how-it-works'],
    text: 'This page lays out the operating sequence that turns a website into a guided environment. First I discover what is actually present on the live page. Then I reconcile that evidence with the verified knowledge base. Next I confirm which paths and actions are allowed under the current permissions. Only after those checks do I present a next step. It is a disciplined handoff from knowledge to action, designed so a visitor can move forward with confidence rather than hope.',
  },
  {
    route: '/security',
    pointerTargetIds: ['tour-security'],
    text: 'Security is not an afterthought in Orb Weaver — it is the rulebook behind every visible action. I work only from verified state, stay inside bounded permissions, and leave control with the visitor at every moment. I can point to a live target and explain it; I do not silently perform actions, invent authority, or turn guidance into an unapproved automation. The same governance that protects the visitor also protects the operator’s brand and legal posture.',
  },
  {
    route: '/weaving',
    pointerTargetIds: ['tour-weaving'],
    text: 'This is the weaving layer itself. A useful website is more than a collection of URLs. Products connect to policies, questions connect to answers, people connect to decisions, and every page belongs to one or more visitor journeys. The weave preserves those relationships so the guidance I offer carries context instead of repeating generic text. Without the weave, an assistant can only surface isolated facts. With the weave, it can support a coherent experience.',
  },
  {
    route: '/web-weave',
    pointerTargetIds: ['tour-web-weave'],
    text: 'Web Weave is the operator workflow that keeps proposed website changes accountable. It gives teams a clear path to inspect a change, approve it, verify it against the live evidence, and preserve the same governance boundary you have seen throughout this tour. The goal is not merely to edit a page. The goal is to keep the site understandable and trustworthy after the change so the ORB’s knowledge and the visitor’s experience stay aligned.',
  },
  {
    route: '/now/desktop-orb',
    pointerTargetIds: ['tour-desktop-orb'],
    simulation: 'desktop_diagnostics',
    auditTaskCount: 5,
    text: 'Welcome to the Desktop ORB view — the deeper workspace for operators who need more than visitor-facing guidance. Here specialized Morbs can carry out approved diagnostics, surface bounded findings, and make system health easier to inspect. The batch of five diagnostic tasks is again prime-sized for auditability. The Website ORB hosts the visitor journey; the Desktop ORB helps the team keep that journey reliable, observable, and governed.',
  },
  {
    route: '/founding-beta',
    pointerTargetIds: ['tour-founding-beta'],
    text: 'This is the Founding Beta invitation. It is intended for a focused group of website operators who want to run real ORB deployments close to real decisions, then shape the product with direct feedback. The value of the beta is practical evidence: what visitors actually need, what operators need to operate safely, and where a governed ORB produces the clearest results. It is a partnership, not a passive trial.',
  },
  {
    route: '/investor-contact',
    pointerTargetIds: ['tour-investor-contact'],
    text: 'This is the investor conversation point. It brings together the product thesis, the market opportunity, the deployment model, and the funding path behind Orb Weaver. When a visitor is ready to discuss those questions directly, I can bring them here and keep the discussion grounded in the same verified product story you have seen throughout the tour rather than in abstract claims.',
  },
  {
    route: '/preflight',
    pointerTargetIds: ['preflight-website-url', 'run-preflight-scan'],
    scrollToEndDuringSpeech: true,
    text: 'Here is Preflight, the first practical check for a website considering an ORB. I have highlighted the website field and the Run Preflight button. Enter a public site you own or are authorized to review, then choose Run Preflight yourself. I will never submit a scan for you. The results appear here quickly. While the scan works, I will keep moving through the tour. Account creation comes next; after that, we can optionally review your Preflight together before you decide whether a deeper full-site scan is worthwhile.',
  },
  {
    route: '/signup',
    // Arrival is intentionally silent: from here, Weaver responds to the
    // visitor and helps with account creation rather than continuing a script.
    handoffToLiveConversation: true,
  },
];

const PAGE_ORIENTATIONS: Record<string, string> = {
  '/features':
    'This page explains the Website ORB features: verified answers grounded in live site evidence, guided navigation that respects real page geometry, and the operational tools that support a useful visitor journey. The emphasis is on reducing confusion and increasing confidence, not on adding another chat surface.',
  '/lidar-guidance':
    'This is the page that explains the LiDAR-inspired two-dimensional visual navigation system. Weaver builds a live geometric map of the page, reconciles it with verified targets, and re-validates before every pointer movement so guidance remains precise even as layouts change.',
  '/how-it-works':
    'This page explains how Orb Weaver turns website evidence into governed, useful guidance. The sequence is deliberate: discover what is present, reconcile with verified knowledge, confirm allowed paths, then present a next step. Knowledge becomes action only after the checks pass.',
  '/security':
    'This page explains the security and governance boundary that underlies every ORB action: verified state, bounded permissions, and explicit visitor control. No silent actions, no invented authority, no unapproved automation.',
  '/preflight':
    'This is the Preflight page. It begins with a free, public readiness check that shows what can be woven and where attention is needed before any deeper Website ORB assembly begins.',
  '/marketplace':
    'This page introduces the Orb Weaver marketplace and the Website ORB options available for deployment, each designed to fit different operator needs while preserving the same governance model.',
  '/now/desktop-orb':
    'This page explains the Desktop ORB — the deeper operator workspace for approved diagnostic and guidance tools. It complements the visitor-facing Website ORB by giving the team visibility and control over system health.',
  '/web-weave':
    'This page explains the Web Weave workflow and the approval boundary for making website changes. Changes remain accountable so the site stays understandable and the ORB’s knowledge stays aligned with reality.',
  '/weaving':
    'This page explains the principles behind weaving website intelligence from verified relationships rather than isolated pages. The weave is what turns a site into a coherent guided environment.',
  '/founding-beta':
    'This is the Founding Beta page — an invitation to a limited group of website operators to run real ORB deployments, gather practical evidence, and help shape the product while it is still being refined.',
  '/investor-contact':
    'This is the investor contact page for private conversations about the product thesis, market opportunity, deployment model, and path forward, kept grounded in the verified product story.',
};

export const scriptedPageOrientation = (pathname: string): ScriptedOrientationStep | null => {
  if (pathname === '/' || pathname === '/signup') return null;
  const text =
    PAGE_ORIENTATIONS[pathname] ||
    (pathname.startsWith('/marketplace/')
      ? 'This page describes a specific Orb Weaver marketplace option and how it fits into the Website ORB system while preserving the same governance and verification model.'
      : null);
  if (text) return { text };
  const pageName =
    pathname
      .split('/')
      .filter(Boolean)
      .pop()
      ?.replace(/[-_]/g, ' ')
      .replace(/\b\w/g, (letter) => letter.toUpperCase()) || 'current';
  return {
    text: `This is the ${pageName} page. I will give you the essential context grounded in what is verified here first, then remain available when you choose to continue.`,
  };
};
