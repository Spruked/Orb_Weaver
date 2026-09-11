# Visitor Interaction Doctrine — Governed Nine-of-Clubs Navigation

## Status

This is the required acceptance doctrine for the Website ORB's dynamic guided
experience. It does not authorize an ungoverned destination, action, or claim.
It replaces linear narration as the sufficient definition of Target One
acceptance.

### Implementation status — 2026-09-11

The source lane now has the first bounded implementation: authored questions
have finite useful outcomes; deterministic answer classification returns a
stable semantic category; the Website Tour Stage Governor alone maps that
category to an issued legal route; and the current journey preserves asked
questions, answer signals, visited routes, recent Weaver statements, and a
pending/active route;
and arrival continues the conversation on the selected page. Tour concept
coverage is accepted only from an exact supporting excerpt that survives the
visitor-speech boundary. A missing live cognition service returns a
non-advancing failure instead of fallback narration.

This is not final Target One acceptance. The complete eligible-destination
graph, per-destination live Pointer/DOM proof, a fully iterative cross-page
curriculum, and a successful same-release-candidate live-model/STT journey
remain evidence requirements.

## Principle

Questions are navigation intelligence, not filler dialogue. Each question
must reduce uncertainty about the visitor's interest while preserving a useful
governed next move. The visitor participates in selecting a conversational
route; the Stage Governor retains authority over eligible destinations,
permissions, actions, and completion.

The interaction is a bounded funnel: explain briefly, ask a constrained
engagement question, interpret the answer, select an allowed next destination,
guide there only after live verification, and retain the answer for the
session. The route may vary; factual authority and safety may not.

## Question contract

Every Weaver question must provide:

1. a documented learning or commercial purpose;
2. a bounded answer space with two or more useful outcomes;
3. no default conversation-killing yes/no exit or generic continuation ask;
4. a deterministic mapping from answer meaning to an already allowed next
   destination or explanation branch;
5. the concept coverage it helps establish; and
6. session-scoped memory so substantially equivalent questions are not
   repeated.

Questions must not become an interrogation, fabricate a visitor profile, or
turn a choice into action authority. A visitor can interrupt, decline to
answer, or ask another question; the fallback is a useful governed explanation
or a preserved state, never a fabricated completion.

### Nine-of-Clubs pattern

The interaction progressively narrows uncertainty without pretending the
visitor has only one acceptable answer. Do not ask generic continuation or
yes/no questions such as “Would you like me to show you how Preflight works?”
Their easiest answer is an exit and they reveal no useful navigation intent.

Use paired, useful choices instead. For example:

| Question intent | Bounded answer meaning | Eligible governed next destination |
| --- | --- | --- |
| “What Orb Weaver discovers” vs. “what Weaver does with what it knows” | discovery/understanding vs. capability/action | intelligence/weave evidence vs. guidance/cognition capability |
| “Knowing what a visitor needs” vs. “helping them get there” | understanding vs. verified guidance | Site World/intelligence vs. LiDAR/pointer guidance |
| “Visitors not finding an offer” vs. “understanding it but not acting” | discovery friction vs. conversion friction | navigation/offer evidence vs. transaction/Preflight capability |

The table is an interaction pattern, not a hardcoded script. The deterministic
tour controller classifies the answer into the documented bounded meanings,
then selects only from destinations the current Stage Governor state has made
eligible. The language model may vary the question and transition language; it
never invents a destination or treats a choice as action consent.

## Navigation contract

For each governed interaction state, the backend supplies a finite eligible
destination set and the frontend may select only from that set. An answer may
choose among Landing, Features/capability evidence, LiDAR/guidance, How It
Works/intelligence, and Preflight only when the current stage explicitly
allows that destination and its live target validates.

Cross-page movement preserves session-scoped interaction answers, covered
concepts, interruption state, and the next eligible destination set. A route
change never grants completion, action authority, or permission to use stale
pointer geometry.

The visitor-responsive progression is therefore:

```text
brief governed explanation
  -> constrained useful question
  -> bounded answer classification
  -> Stage Governor eligible-destination selection
  -> route transition and live DOM/Pointer verification
  -> next explanation, retaining session context
```

## Articulation and progression

Deterministic systems own facts, Site World evidence, required concepts,
eligible destinations, pointer verification, permissions, progression, and
completion. The language model owns wording, analogy, transitions, visitor
response, and non-repetitive natural articulation within those rails.

Dynamic-tour acceptance requires a live configured cognition service. If it is
unavailable, the runtime may state that conversational reasoning is temporarily
unavailable, preserve visitor progress, and offer a governed recovery path.
It must not present generic fallback speech as successful concept coverage or
advance the tour because a non-empty string was spoken.

## Required evidence per turn

The release-candidate trace records: current state and stop, objective,
required concepts, supplied Site World/current-page evidence, eligible
destinations, answer classification, selected destination, model invocation
and source, raw model speech, final sanitized visitor speech, accepted
concepts with evidence, pointer verification, and the exact advancement or
non-advancement reason.
