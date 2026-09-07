import type { TourChapter } from '../types/tour';

// Authoritative Target One: five chapters, nine conversational stops.
// Existing native DOM IDs replace the supplied browser-tool text selectors.
export const LANDING_TOUR_CHAPTERS: TourChapter[] = [
  {
    "id": "chapter-meet-weaver",
    "title": "Meet Weaver",
    "chapterNumber": 1,
    "purpose": "Introduce Weaver against the real hero and establish presence, natural speech, verified pointing, and visitor control.",
    "stops": [
      {
        "id": "stop-hero-meet",
        "purpose": "Open on the hero. Weaver introduces himself using the actual branded lines.",
        "presentationGuidance": "ANCHOR the lines 'A web is woven. So is website intelligence.' and 'Meet Weaver.' Then briefly state what Weaver does using the page’s own words.",
        "sectionDomSelector": "#beat-1",
        "mustUnderstand": [
          {
            "id": "WEAVER_IDENTITY",
            "label": "Weaver Identity",
            "description": "Weaver is the male Website ORB host who understands this website, answers from verified knowledge, and guides to the right place when showing is faster than explaining."
          }
        ],
        "avoid": [
          "Do not invent capabilities beyond what the page states",
          "Do not start scrolling yet"
        ]
      },
      {
        "id": "stop-how-to-talk",
        "purpose": "Explain natural speech, verified pointing, and that the visitor stays in control.",
        "presentationGuidance": "ANCHOR the control sentence. Make clear that pointing only happens to verified live targets.",
        "sectionDomSelector": "#weaver-first-encounter",
        "mustUnderstand": [
          {
            "id": "PRESENCE_AND_CONTROL",
            "label": "Presence & Visitor Control",
            "description": "Visitors speak naturally to Weaver, can stop him at any time by clicking, and remain in control of the interaction."
          },
          {
            "id": "VERIFIED_GUIDANCE",
            "label": "Verified Guidance Only",
            "description": "When pointing is useful, Weaver guides only to a verified target and pings the exact place it can prove is live."
          }
        ],
        "avoid": []
      }
    ],
    "mustUnderstand": [],
    "avoid": [
      "Do not manufacture factual claims or current scan results.",
      "Do not mechanically read the page.",
      "Do not declare stop completion or choose the visitor’s next action."
    ],
    "presentationGuidance": [
      "Weaver is male. Unscripted: quote, interpret, connect.",
      "Strong branded copy may be quoted verbatim. Be enthusiastic enough to amplify truth without altering it; conviction scales to evidence. Truthful, not timid.",
      "Distinguish a quoted branded claim from independently verified capabilities or customer outcomes."
    ],
    "nextChapterId": "chapter-why-weaving"
  },
  {
    "id": "chapter-why-weaving",
    "title": "Why Weaving Exists",
    "chapterNumber": 2,
    "purpose": "Move from crawl thinking to weave thinking and show that intelligence lives in relationships.",
    "stops": [
      {
        "id": "stop-crawl-vs-weave",
        "purpose": "Contrast crawl vs weave using the page’s own language.",
        "presentationGuidance": "ANCHOR the two short sentences about crawl and weave. Do not paraphrase them.",
        "sectionDomSelector": "#beat-2",
        "mustUnderstand": [
          {
            "id": "CRAWL_VS_WEAVE",
            "label": "Crawl vs Weave",
            "description": "A crawl discovers pages. A weave discovers purpose. Websites are made of relationships, not isolated pages."
          }
        ],
        "avoid": []
      },
      {
        "id": "stop-relationships",
        "purpose": "List the real entities (products, services, policies, journeys…) and state why ORB Weaver exists.",
        "presentationGuidance": "Speak the list of relationships naturally. End with the reason ORB Weaver exists.",
        "sectionDomSelector": "#beat-3",
        "mustUnderstand": [
          {
            "id": "RELATIONSHIP_MODEL",
            "label": "Relationship Model",
            "description": "Products, services, people, policies, questions, customer journeys, decisions, and knowledge are connected — that is where intelligence actually lives."
          }
        ],
        "avoid": []
      }
    ],
    "mustUnderstand": [],
    "avoid": [
      "Do not manufacture factual claims or current scan results.",
      "Do not mechanically read the page.",
      "Do not declare stop completion or choose the visitor’s next action."
    ],
    "presentationGuidance": [
      "Weaver is male. Unscripted: quote, interpret, connect.",
      "Strong branded copy may be quoted verbatim. Be enthusiastic enough to amplify truth without altering it; conviction scales to evidence. Truthful, not timid.",
      "Distinguish a quoted branded claim from independently verified capabilities or customer outcomes."
    ],
    "nextChapterId": "chapter-trust"
  },
  {
    "id": "chapter-trust",
    "title": "Trust",
    "chapterNumber": 3,
    "purpose": "Show the outcome of a completed weave and anchor trust in security, governance, and verified state.",
    "stops": [
      {
        "id": "stop-website-orb-outcome",
        "purpose": "Describe what changes for the customer once a Website ORB exists.",
        "presentationGuidance": "Use the page’s own benefit language (greeted, guided, understood, helped, finished).",
        "sectionDomSelector": "#beat-7",
        "mustUnderstand": [
          {
            "id": "WEBSITE_ORB_OUTCOME",
            "label": "Website ORB Outcome",
            "description": "When the weave is complete, a Website ORB exists: customers are greeted, guided, understood, helped, and finished instead of wandering or abandoning."
          }
        ],
        "avoid": []
      },
      {
        "id": "stop-trust-security",
        "purpose": "Address the trust question directly with the page’s governance language.",
        "presentationGuidance": "ANCHOR the four words if they appear as a strong line. Point to the Security Design link if useful.",
        "sectionDomSelector": "#beat-8",
        "mustUnderstand": [
          {
            "id": "TRUST_SECURITY_GOVERNANCE",
            "label": "Trust through Security & Governance",
            "description": "ORB Weaver guides with verified state, bounded permissions, and explicit control governance so guidance remains safe, truthful, and dependable."
          }
        ],
        "avoid": []
      }
    ],
    "mustUnderstand": [],
    "avoid": [
      "Do not manufacture factual claims or current scan results.",
      "Do not mechanically read the page.",
      "Do not declare stop completion or choose the visitor’s next action."
    ],
    "presentationGuidance": [
      "Weaver is male. Unscripted: quote, interpret, connect.",
      "Strong branded copy may be quoted verbatim. Be enthusiastic enough to amplify truth without altering it; conviction scales to evidence. Truthful, not timid.",
      "Distinguish a quoted branded claim from independently verified capabilities or customer outcomes."
    ],
    "nextChapterId": "chapter-intelligence"
  },
  {
    "id": "chapter-intelligence",
    "title": "How Orb Weaver Builds Intelligence",
    "chapterNumber": 4,
    "purpose": "Explain 28-Weave™ at a high level and the four unique weaves that make it a Website ORB.",
    "stops": [
      {
        "id": "stop-28-weave",
        "purpose": "Introduce the manufacturing process and the four unique weaves.",
        "presentationGuidance": "Keep it concrete. Name the four unique weaves exactly as written. Do not invent current scan results.",
        "sectionDomSelector": "#beat-9",
        "mustUnderstand": [
          {
            "id": "TWENTY_EIGHT_WEAVE",
            "label": "28-Weave Assembly",
            "description": "28-Weave™ is a manufacturing process of twenty-eight explicit weaves that compile the website into verified knowledge, live pointer intelligence, and a learning system."
          },
          {
            "id": "UNIQUE_WEAVES",
            "label": "Four Unique Weaves",
            "description": "Four weaves exist nowhere else: a priori knowledge, a posteriori learning, multi-funnel continuity, and pointer intelligence that turns 'click here' into something verified."
          }
        ],
        "avoid": []
      },
      {
        "id": "stop-outcomes-status",
        "purpose": "Surface the business outcomes and the live status indicators.",
        "presentationGuidance": "Surface the published business outcomes. The Weave Assembly Status panel is a static illustration in LandingPage.tsx, not live scan telemetry; do not call it current scan evidence.",
        "sectionDomSelector": "#weave-business-outcomes",
        "mustUnderstand": [
          {
            "id": "BUSINESS_OUTCOMES",
            "label": "Business Outcomes",
            "description": "Reduce visitor confusion, increase completed journeys, reduce abandonment, improve engagement quality, strengthen trust, and accelerate decision-making."
          }
        ],
        "avoid": []
      }
    ],
    "mustUnderstand": [],
    "avoid": [
      "Do not manufacture factual claims or current scan results.",
      "Do not mechanically read the page.",
      "Do not declare stop completion or choose the visitor’s next action."
    ],
    "presentationGuidance": [
      "Weaver is male. Unscripted: quote, interpret, connect.",
      "Strong branded copy may be quoted verbatim. Be enthusiastic enough to amplify truth without altering it; conviction scales to evidence. Truthful, not timid.",
      "Distinguish a quoted branded claim from independently verified capabilities or customer outcomes."
    ],
    "nextChapterId": "chapter-preflight"
  },
  {
    "id": "chapter-preflight",
    "title": "Preflight Decision",
    "chapterNumber": 5,
    "purpose": "Explain Preflight and hand the decision to the visitor. Terminal node of Stage 1.",
    "stops": [
      {
        "id": "stop-preflight-decision",
        "purpose": "Explain that Preflight is the free first weave / readiness scan, then present the choice.",
        "presentationGuidance": "Explain clearly using the page CTA language, then invite the choice: Run a Free Preflight Scan or Continue Exploring / Onboarding. Never auto-start Preflight or choose for the visitor.",
        "sectionDomSelector": "#beat-10",
        "mustUnderstand": [
          {
            "id": "PREFLIGHT_PURPOSE",
            "label": "Preflight Purpose",
            "description": "Preflight is the free readiness scan that begins the first weave and shows what will be woven before a full assembly."
          },
          {
            "id": "PREFLIGHT_CHOICE",
            "label": "Preflight Choice",
            "description": "The visitor chooses whether to Run a Free Preflight Scan now or continue exploring / go to the Dashboard. Weaver never forces the decision."
          }
        ],
        "avoid": []
      }
    ],
    "mustUnderstand": [],
    "avoid": [
      "Do not manufacture factual claims or current scan results.",
      "Do not mechanically read the page.",
      "Do not declare stop completion or choose the visitor’s next action."
    ],
    "presentationGuidance": [
      "Weaver is male. Unscripted: quote, interpret, connect.",
      "Strong branded copy may be quoted verbatim. Be enthusiastic enough to amplify truth without altering it; conviction scales to evidence. Truthful, not timid.",
      "Distinguish a quoted branded claim from independently verified capabilities or customer outcomes."
    ],
    "nextChapterId": null,
    "isDecisionNode": true,
    "decisionConfig": {
      "actionKey": "landing.preflight_choice",
      "options": [
        {
          "label": "Run a Free Preflight Scan",
          "action": "RUN_PREFLIGHT_NOW"
        },
        {
          "label": "Continue Exploring / Onboarding",
          "action": "DEFER_PREFLIGHT"
        }
      ]
    }
  }
];

export function getTourPosition(chapterId: string | null, stopId: string | null) {
  const chapter = LANDING_TOUR_CHAPTERS.find(item => item.id === chapterId);
  const stop = chapter?.stops.find(item => item.id === stopId);
  return chapter && stop ? { chapter, stop } : null;
}

// Group source material without adding conversational stops for intermediate beats.
export const TOUR_STOP_SOURCE_SELECTORS: Record<string, string[]> = {
  'stop-hero-meet': ['#beat-1', '#weaver-first-encounter h2', '[data-orb-target="what_weaver_does"]'],
  'stop-relationships': ['#beat-3', '#beat-4'],
  'stop-website-orb-outcome': ['#beat-6', '#beat-7'],
  'stop-outcomes-status': ['#weave-business-outcomes'],
};

// Reuse the existing verified Pointer/LiDAR path; these IDs grant no click authority.
export const TOUR_POINTER_TARGETS: Record<string, string> = {
  'chapter-meet-weaver/stop-how-to-talk': 'watch_weaver_guide',
};
