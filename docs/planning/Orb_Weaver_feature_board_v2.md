# Orb Weaver Active Build Board — v3.1 Source-Aligned

This replaces the older “v2 Amended” board and revises the prior v3 draft after reviewing the current source files.

The active correction is:

Orb Weaver is no longer only a planned feature board. It is an active Website ORB Intelligence Engine with working crawl/audit/dashboard/report/account surfaces, a public landing concept, preflight flow, marketplace/cart direction, and a partially built pointer/escalation package.

The board should now focus on:

1. connecting the live ORB to the full compiled site-world,
2. canonicalizing duplicate/older frontend ORB behavior,
3. wiring the pointer package into the real crawler/runtime,
4. hardening storefront/fulfillment,
5. keeping the product positioned as a website consultant, not a chatbot.

---

## 1. Core Product Position

Orb Weaver is not a chatbot platform.

Orb Weaver is a Website ORB Intelligence Engine.

The public product promise is:

* scan a website,
* build a deep intelligence layer,
* compile usable site knowledge,
* deploy an ORB that can explain, guide, and help visitors or owners understand the website.

The ORB should be positioned as a website consultant that inhabits the website, not as:

* ChatGPT for websites,
* a floating assistant,
* an avatar,
* a bottom-right chat bubble,
* a generic AI widget.

The ORB should guide, teach, explain, present, recommend, and remember.

### O.R.B.S. Architectural Definition

**O.R.B.S. — Origin of Reasoning Bilateral Substrate**

This is architecturally accurate because the system combines:

* two substrates: cognitive and behavioral,
* two surfaces: internal reasoning and external embodiment,
* two processes: fast cognition and human-tempo action.

Together, these form a third emergent layer: a sovereign assistant with real cognition, real embodiment, and real human alignment.

This is the architectural meaning of an ORB and the foundation for what Orb Weaver is building.

---

## 2. Runtime Architecture Baseline

The corrected SKG/site-world architecture remains valid, but it should no longer be called an amendment.

It is baseline law.

At scan/build time, Orb Weaver should compile:

* crawl output,
* scan output,
* project profile,
* page content,
* route map,
* semantic page meaning,
* preflight findings,
* audit findings,
* product/service facts,
* owner-approved facts,
* pointer plot map,
* target metadata,
* route boundaries,
* allowed actions,
* escalation rules,
* local site memory,
* current public route map.

The live ORB should not construct a “Current Page Capsule” from scratch on every route change.

Route change should be lookup-only:

1. detect current route,
2. load matching precompiled site-world/SKG route record,
3. update current-page context,
4. no expensive live assembly.

Visitor question flow:

1. receive visitor question,
2. classify intent,
3. reason against the compiled site-world plus current route record,
4. select answer/action candidate,
5. check boundary/permission rules,
6. if guidance is needed, pass the selected target to pointer runtime,
7. pointer runtime verifies live DOM target before movement/highlight,
8. if target cannot be verified, answer voice-only and do not guess.

---

## 3. Highest-Priority Defect: Live ORB Context Injection

The biggest active product risk is not lack of concept.

The risk is that the live Website ORB may still be reaching the LLM or voice path without the full compiled site-world.

The ORB must not run from:

* a tiny prompt pack,
* canned answers,
* a short identity JSON,
* isolated public facts,
* hardcoded product blurbs.

The ORB must run from the whole compiled operational site-world.

Required repair:

Trace the actual live Website ORB request path and confirm which artifacts feed it.

The live ORB should receive:

* current URL,
* current route,
* page title,
* visible page text,
* matching route record,
* site profile,
* scan/crawl content,
* audit summary,
* preflight summary,
* target map,
* product facts,
* pricing facts,
* permitted actions,
* escalation limits,
* route relationships,
* owner-approved language.

Acceptance condition:

A visitor can ask an unscripted question about Orb Weaver, ask follow-ups, ask where to go next, and the ORB responds as though it knows the site it inhabits.

It must not sound like a generic assistant with a small prompt.

---

## 4. Pointer System Status

The pointer system should no longer be described as merely planned.

Current status:

* Data contract exists.
* Python schema exists.
* TypeScript mirror exists.
* Runtime state model exists.
* Resolution chain exists.
* Pointer runtime ordering exists.
* Human escalation control flow exists.
* Promotion/stale-hit logic exists.
* Several implementation hooks are still TODO.

The next task is not “invent pointer intelligence.”

The next task is:

Wire every `TODO(integration)` point into Orb Weaver’s real crawler, DOM, animation, TTS, storage, and support/escalation systems.

Do not change the doctrine order.

The protected pointer order is:

1. confidence check,
2. resolve target,
3. localized recovery if needed,
4. point/travel animation,
5. ping bloom,
6. ploop,
7. candidate correction if recovery found a better locator,
8. never write runtime corrections directly into the authoritative map.

The ORB must never point at a maybe.

---

## 5. Pointer Resolution Requirements

The live pointer system must use a resolution chain, not screen coordinates.

Resolution order:

1. semantic locator,
2. content fingerprint,
3. accessibility role/name,
4. localized visual verification using OCR/Tesseract-style fallback only within the current viewport or section.

Rules:

* No raw pixel coordinates as the authority.
* No cross-page navigation without explicit confirmation.
* No full-site scan from the pointer runtime.
* No guessed highlights.
* No click for the visitor unless the route/action explicitly permits it and confirmation has happened.
* If target confidence is below the floor, answer verbally only.
* If target is unresolved, answer verbally only and log the failure/candidate correction path.

---

## 6. OCR Runtime Support

OCR is now part of the active build board.

Orb Weaver needs a dual-runtime OCR setup.

### WSL Tesseract

Primary for:

* WSL-native OCR pipelines,
* backend processing,
* scan tooling,
* substrate work,
* Python automation,
* document processing.

### Windows Tesseract

Required for:

* Desktop ORB,
* Tauri apps,
* Windows-side OCR,
* PowerShell tests,
* any Windows app that needs `tesseract.exe`.

Installed location:

`C:\Program Files\Tesseract-OCR`

Rule:

Keep both.

Do not collapse OCR to WSL-only because Windows desktop apps cannot directly execute the Linux WSL binary without a bridge.

Optional future bridge:

Windows ORB → local API bridge → WSL OCR service → OCR response.

That bridge is useful later, but Windows Tesseract remains required for direct Desktop/Tauri OCR.

---

## 7. Frontend ORB Canonicalization

This remains one of the highest-priority cleanup items.

There appear to be older and newer ORB-on-page implementations.

The live Website ORB must have one canonical runtime component.

Immediate audit:

* identify every frontend ORB component,
* determine which component is actually mounted on the live site,
* remove or wrap duplicate behavior,
* preserve useful movement/voice/presence logic,
* remove stale identity strings such as CALI/Caleon from the public Website ORB path unless intentionally scoped to Desktop CALI.

Canonical public Website ORB identity:

Weaver.

Desktop CALI remains separate.

Do not blur Website Weaver and Desktop CALI.

---

## 8. Voice and Speech Behavior

Website ORB voice remains intentional.

Mobile behavior:

* user taps speaker,
* no unwanted automatic speaking,
* voice works in public contexts,
* user controls when it talks.

Needed improvements:

* replace black notification-style speech panel with an attached glass panel from the ORB,
* keep the text echo small and attached,
* no separate general text chat UI,
* only show human chat box during governed escalation,
* speaker-mode output must work reliably,
* use low-latency normal TTS,
* do not use live voice cloning for standard visitor guidance.

Priority is understanding first, movement second.

---

## 9. Website ORB Presentation

Movement should support explanation.

The ORB should:

* move toward relevant cards,
* look at or orient toward relevant information,
* highlight important UI,
* guide attention,
* remain alive but not distracting,
* expand while speaking,
* restore instantly when summoned.

Current movement doctrine:

* no forced parking or sleep locations,
* no upper-right sleep state,
* no lower-right chat-bubble parking,
* no corner docking,
* remain visible, clickable or tappable, and free to move smoothly throughout the site,
* never become stuck or unavailable to visitors,
* use intentional embodied movement rather than random decoration,
* show a browser ping light at the verified target when providing pointer or directional guidance.

Movement must never be random decoration.

The public product demonstration should show a live moving ORB, not just a static logo.

---

## 10. Modern JavaScript / SPA Scan Capture

Still active.

Problem:

Some SPA scans find routes but capture the same thin shell content instead of real rendered page meaning.

Required improvement:

Add rendered-browser capture so scans can collect:

* rendered text,
* buttons,
* forms,
* links,
* route states,
* headings,
* CTAs,
* product/service cards,
* modals where appropriate,
* targetable UI elements.

Preserve existing seeded/context route behavior for:

`/account`, `/dashboard`, `/cart`, `/checkout`, `/login`, `/signup`, `/admin`, `/privacy`, `/terms`, `/sitemap.xml`, `/robots.txt`.

Acceptance condition:

A JavaScript-heavy site must produce different meaningful route records for different rendered pages, not repeated shell summaries.

---

## 11. Scan-to-ORB Package

Every paid scan should reliably produce a deployable intelligence package.

Required outputs:

* Website Intelligence Report,
* compiled site-world / SKG,
* route records,
* page summaries,
* visitor target map,
* pointer plot map,
* ORB configuration,
* deployment recommendation,
* crawl inventory,
* issue register,
* entity/brand-language summary,
* preflight summary,
* audit summary,
* route-level permission boundaries,
* before/after baseline for rescans.

The compiled site-world is not just a report artifact.

It is the operational world the ORB inhabits.

---

## 12. Dashboard, Reports, and Account Surfaces

These are not only future plans.

The source shows active app surfaces for:

* Dashboard,
* Projects,
* Crawl Jobs,
* GA4 Analytics,
* Reports,
* Cart,
* Account,
* Admin customers.

This means the board should treat these as active product surfaces needing hardening, not conceptual placeholders.

Needed hardening:

* make report exports reliable,
* make audit PDF/CSV generation reliable,
* make crawl CSV reliable,
* make “Open PDF” reliable,
* make account/customer records consistent,
* make cart/entitlements connect to fulfillment,
* make admin/customer access reliable.

---

## 13. Preflight

Preflight is no longer a detached future idea.

It exists as an active product path and should be treated as a conversion/front-door system.

Preflight role:

* no-account or lightweight scan entry,
* fit/readiness check,
* lead qualification,
* account creation hook,
* upgrade path into paid scan or Website ORB package.

Preflight should remain separate from live ORB cognition, but it should feed:

* customer project profile,
* scan readiness,
* recommended install mode,
* warnings,
* sitemap/auth/product/blog/checkout detection,
* sales qualification,
* paid package recommendation.

---

## 14. Historical Intelligence and Memory

The strategy is now stronger than the old board.

Do not keep every raw scan forever.

Keep:

* newest crawl,
* newest audit,
* newest scan,
* newest compiled knowledge,
* newest recommendations,
* newest semantic graph.

Compress older scans into compact historical intelligence.

Example:

“July 10: homepage H1 corrected. Score improved from 74 to 81.”

The ORB should remember:

* what changed,
* who changed it,
* when,
* why,
* whether it improved the website,
* owner preferences,
* corrections,
* recurring issues,
* terminology,
* successful fixes.

Memory should delete by usefulness, not age.

---

## 15. Presentation Mode

The ORB should not simply answer with raw audit labels.

Every meaningful answer should follow this shape:

Finding
Reason
Evidence
Recommendation
Offer deeper explanation

Example:

Instead of only saying:

“Missing H1 tags.”

The ORB should explain:

* what happened,
* why it matters,
* which pages are affected,
* what to fix first,
* what improvement to expect,
* whether the owner wants a walkthrough.

---

## 16. Website Tour Mode

Website Tour Mode should remain a major future feature.

The ORB should be able to say:

“Let’s review your three highest-impact issues.”

Then guide through:

1. issue one,
2. evidence,
3. recommendation,
4. next issue,
5. final summary.

This turns Orb Weaver from a dashboard into an interactive website consultation.

---

## 17. Storefront, Marketplace, Fulfillment, and Entitlements

The marketplace/cart direction is active enough to remain high priority.

Website ORB products should align to the current pricing/tier doctrine, not stale Basic/Enhanced/Master language unless that is deliberately restored.

Use current tier language:

* Basic,
* Enhanced,
* Platinum,
* Enterprise.

Paid purchases must automatically create:

* customer record,
* entitlement,
* package access,
* download/install path,
* scan/report access,
* purchased intelligence pack access,
* marketplace/cart record.

Open issue to keep on board:

Premium Intelligence Pack purchase previously did not automatically fulfill customer access.

Acceptance condition:

A customer can buy, receive the correct entitlement, access the right pack/report/install path, and see it in their account without manual repair.

---

## 18. CRM Bridge and Human Escalation

CRM bridge remains a business-value feature.

Human escalation has a partial structured implementation and should be wired rather than reinvented.

Rules:

* explicit request triggers escalation,
* frustration-only prompts an offer,
* sensitive data requires separate approval,
* ORB must not write inside the human-agent chat bubble,
* after handoff, suppression is scoped only to that issue,
* the ORB stays available for unrelated questions.

CRM handoff should include:

* visitor intent,
* route context,
* issue summary,
* attempted guidance,
* target/page involved,
* approved contact details only when allowed.

---

## 19. Analytics Integration

GA4 is already part of the app structure and should remain optional.

Analytics should not become the center of Orb Weaver.

Use analytics to correlate:

* ORB guidance,
* retention,
* click paths,
* form starts,
* abandoned-cart reduction,
* time on site,
* device behavior,
* route friction.

Do not turn Orb Weaver into an ad dashboard.

---

## 20. Browser-Level Diagnostics

Still needed to make the scanner a true Website Intelligence Engine.

Add or strengthen:

* screenshots,
* page snapshots,
* JavaScript console errors,
* mobile emulation,
* Lighthouse-style performance review,
* accessibility review,
* network failures,
* slow resources,
* memory-growth signs,
* rendering problems,
* layout problems that affect pointer guidance.

---

## 21. Campaign Readiness Layer

Later upgrade.

Purpose:

* landing-page readiness score,
* message/offer-gap detection,
* CTA recommendations,
* page fixes,
* campaign asset format guidance,
* copy length guidance,
* timing/readiness recommendations.

This is not ad management.

It is pre-campaign site readiness intelligence.

---

## 22. Funding and Execution Track

The strategic review adds a non-code reality to the board.

The bottleneck is no longer primarily ideas.

The bottleneck is execution capacity.

Funding should support:

* founder runway,
* implementation help,
* premium AI development tools,
* API credits,
* larger model testing,
* GPU rental,
* deployment hardening,
* testing hardware,
* production infrastructure,
* security review.

GPU rental should remain a formal budget item for:

* model comparison,
* voice generation,
* load testing,
* quantization,
* concurrent ORB testing,
* cost analysis,
* deployment strategy.

---

## 23. Immediate Build Sequence

Use this order:

1. Trace the live Website ORB request path and prove whether full compiled site-world context is reaching the ORB.
2. Replace any tiny/static ORB prompt context with compiled site-world injection.
3. Audit and remove any remaining live page-capsule assembly that performs compute on route change.
4. Canonicalize the frontend ORB component path and remove stale CALI/Caleon strings from public Website Weaver.
5. Wire pointer package TODO integration points into real crawler/runtime/storage/TTS/animation systems.
6. Implement semantic locator and content fingerprint target resolution.
7. Add Tesseract visual fallback only as localized current-viewport/section verification.
8. Harden Preflight as the public conversion path.
9. Add rendered-browser capture for SPA/JavaScript sites.
10. Verify voice output and attached speech panel behavior.
11. Verify Windows Tesseract for Desktop/Tauri OCR.
12. Finish marketplace/cart entitlement fulfillment.
13. Wire CRM/human escalation handoff.
14. Add historical memory compression and rescan comparison.

---

## Retired / Stale From Older Board

Do not carry these forward as active framing:

* “v2 Amended” as the title.
* Treating SKG lookup architecture as a new amendment instead of baseline law.
* Treating pointer intelligence as only conceptual.
* Treating Preflight as detached from the product funnel.
* Mixing public Website Weaver with Desktop CALI.
* Treating Dashboard/Projects/Reports/Cart as future-only.
* Listing only Basic / Enhanced / Master unless deliberately reverting tiers.
* Using canned response packs as a substitute for compiled site-world cognition.
* Keeping two active frontend ORB implementations without a canonical decision.
