import type { TourEngagementQuestion } from '../../types/tour';
import { freezeRegistry } from './registry';

/** Existing issued question IDs and two-choice meanings must survive session restore. */
export const LEGACY_ENGAGEMENT_QUESTIONS: Readonly<Record<string, TourEngagementQuestion>> = freezeRegistry(
{
  "discovery-or-guidance": {
    "id": "discovery-or-guidance",
    "intent": "Learn whether the visitor wants to understand Site World discovery or see verified visitor guidance.",
    "prompt": "Are you more interested in what Orb Weaver discovers about a site, or what Weaver can do with that understanding once it has it?",
    "options": [
      {
        "id": "discovery",
        "semanticCategory": "SITE_DISCOVERY",
        "keywords": [
          "discover",
          "discovery",
          "learn",
          "intelligence",
          "weave",
          "site world",
          "know"
        ]
      },
      {
        "id": "guidance",
        "semanticCategory": "VERIFIED_GUIDANCE",
        "keywords": [
          "do",
          "does",
          "help",
          "guide",
          "guidance",
          "show",
          "action",
          "get there"
        ]
      }
    ]
  },
  "understanding-or-helping": {
    "id": "understanding-or-helping",
    "intent": "Learn whether the visitor values understanding needs or verified guidance toward an outcome.",
    "prompt": "When someone gets stuck on a website, which matters more to you: the site knowing what they need, or actually helping them get there?",
    "options": [
      {
        "id": "understanding",
        "semanticCategory": "VISITOR_UNDERSTANDING",
        "keywords": [
          "knowing",
          "know",
          "understand",
          "understanding",
          "need",
          "needs"
        ]
      },
      {
        "id": "helping",
        "semanticCategory": "VISITOR_ASSISTANCE",
        "keywords": [
          "help",
          "helping",
          "get there",
          "guide",
          "guidance",
          "show"
        ]
      }
    ]
  },
  "discovery-or-conversion": {
    "id": "discovery-or-conversion",
    "intent": "Learn whether the visitor's commercial concern is discovery friction or next-step conversion friction.",
    "prompt": "For your own site, is the bigger problem visitors not finding what you offer, or understanding it but still not taking the next step?",
    "options": [
      {
        "id": "discovery",
        "semanticCategory": "DISCOVERY_FRICTION",
        "keywords": [
          "not finding",
          "find",
          "finding",
          "discover",
          "discovery",
          "offer"
        ]
      },
      {
        "id": "conversion",
        "semanticCategory": "CONVERSION_FRICTION",
        "keywords": [
          "next step",
          "taking",
          "act",
          "action",
          "convert",
          "conversion",
          "understand"
        ]
      }
    ]
  }
}
);
