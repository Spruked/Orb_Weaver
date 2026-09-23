# Customer Website ORB package audit — 2026-09-22

Status: customer-specific package compilation, extraction/startup, isolation and
authenticated build/download are verified in automated tests. This is not a
claim of production website installation or live microphone/TTS acceptance.

## 1. Exact inputs

`backend/main.py::_normalized_manufacturing_evidence` selects the completed
project crawl, not Weaver's resident Site World. It reads that crawl's
`CrawledPage` URL, title/H1, HTTP status, content hash, semantic analysis
(content excerpt and pointer records), internal links and schema markup.
Its lexical input is that crawl's `config.lexical_index`, or an index rebuilt
from those pages' top terms and pointer aliases. Unresolved rendered shells
and private/admin/system pages are not promoted into public runtime knowledge.

These become `full_scan_evidence.json`, bound to site ID, domain, scan ID,
scanner version and capture time. A rescan invalidates the previous scan
binding; obsolete normalizer versions are regenerated. The evidence snapshot
is retained under the customer's manufacturing Vault.

Additional explicit inputs are customer configuration/branding, the selected
site's published provider/behavior policy, and owner artifact approval. The
compiler accepts witnessed facts, FAQs, products/services, owner-approved
policies and `site_goals` in normalized evidence. Missing facts/goals stay
missing; no factory conversion objective is supplied automatically.

Unbound or stale `source_context` is rejected. Even correctly bound legacy
context cannot overlay Site World facts, tools or pointers. The production
caller supplies no such overlay.

## 2. Compilation and actual download layout

Build path: confirmed ORBS customer action → project manufacturing endpoint →
`manufacture_website_orb` → `compile_all` → clean runtime allowlist → ZIP audit.
The manufacturing assembly still uses the internal Dock Station builder, but
only its isolated Website ORB subtree enters the customer download.

| Customer output | Source and role |
| --- | --- |
| `apriori/site_skg.json` | Witnessed routes, concepts, entities, actions, pointers and lexical edges from this scan |
| `lexical_index.json` | This site's canonical terms/aliases; compiled alias lookup lives in the SKG |
| `knowledge_chunks.json`, `retrieval_index.json` | Verified text/FAQ/description chunks and their term-to-chunk index |
| `apriori/catalog.json`, `catalog.db`, `ontology.json`, `qa.json`, `policies.json` | Verified commercial/factual/FAQ data; policies require owner approval |
| `site_world.json`, `pointers.json`, `pointer_correspondence.json` | Scan-specific routes and target identities; live DOM validation still required |
| `apriori/elimination_graph.json` | Variable-length witnessed topic choices along approved site-goal paths; unknown/disconnected goals remain explicit |
| `permissions.json` | Answers, live-validated points and navigation proposals; no automated clicks/forms/desktop actions |
| `site_config.json`, `runtime_language.json`, `tool_cache.json` | Customer configuration and scan-derived language/FAQ responses, without host sales defaults |

The `.orbpack` is a ZIP containing `manifest.json` and `website-orb/`, with
`run.py`, `INSTALL.md`, `assets/widget.js`, backend/generic cognition code and
exactly one `runtime/vault_system/`. Old `compiled_orb` fixtures, seeded Vaults,
factory audio, vendor APIs/results, development tools and the Dock Station app
are excluded by positive allowlisting. The legacy React demo source is not the
shipped widget; the standalone widget needs no customer Node build.

The root manifest records site ID → scan ID/scanner version/evidence hash →
artifact schemas and SHA-256 values (including pointers, SKG and lexicon) →
compiler/manufacturer version and package build ID. The package result records
the completed ZIP hash. Owner approvals bind artifact hashes, and startup
checks the required artifact set, evidence, approvals, site/scan identities and
all payload hashes before loading the world. These are integrity checks, not
a signed publisher identity or remote attestation.

## 3. Runtime independence

The extracted package boots and answers from its installed customer Vault with
outbound socket connections disabled in the test process. Its bootstrap,
route/pointer lookup and text answer endpoints require no factory API or Site
World. A fresh process reloads the same customer knowledge namespace. Modified,
missing, foreign or redirected knowledge is rejected.

The browser widget calls only its script host's `/orb/` API. The approved site
origin is checked; CORS is configured from customer origins. Unknown routes do
not fall back to home-page pointers. Missing/ambiguous/hidden DOM targets do
not receive coordinates. Route changes cancel stale guidance. Navigation uses
visitor-selected links, not automatic clicks. Speech pulses only the eye while
audio actually plays; the orb body has fixed 96% opacity.

The confirmed, entitled customer action now explicitly says it approves scan
artifacts and builds the Website ORB. Payment, entitlement and review gates
remain. An authenticated download button uses the manufactured build ID.
The legacy pack-creation endpoint collects only a current approved runtime;
it no longer silently creates a data-only ZIP. Download checks project identity
and the completed archive hash.

## 4. Negative contamination evidence

Two unrelated fixtures (`garden.example` and `marine.example`) produce distinct
vocabularies/product data. Each completed archive contains its own product and
not the other's. The archive audit checks known factory URL/copy/route/target
markers and forbidden trees; an intentionally injected factory endpoint fails.
Shared `orb_weaver.*` schema names and generic code identifiers are allowed—
they are provenance/code, not customer knowledge. A factory term actually
present in approved customer input is reported as attributable, not hidden.
The marker set is finite; this is a regression check, not proof against every
possible synonym of factory copy.

An inspected Garden fixture download contained 98 files, 17 manifest-bound
payload artifacts, three routes (`/`, `/faq`, `/product`) and six compiled
lexical keys. The audit returned no observed factory markers and no findings.
ZIP: `garden.example_website-orb_20260922_233717.orbpack` (125,854 bytes).
SHA-256: `1dfd571198aa88069d52adef56dd846064d514925ad62d8e35dac1c2993fa6ab`.
This is a synthetic test package under pytest's temporary directory, not a
customer release. Rebuilding changes timestamps and therefore its ZIP hash.

## Verification and remaining acceptance

- 41 focused backend tests passed across manufacturing, SKG, isolation,
  single-Vault packaging and ORBS governance. Follow-up isolation/SKG run:
  13 passed. The extended confirmed build/download test also passed.
- Standalone widget DOM test passed: customer-only calls, governed unique
  targets, missing/duplicate target rejection, no clicks and route invalidation.
- Frontend `tsc --noEmit`, widget JavaScript syntax and `git diff --check` passed.

Still required before a production-ready claim: installation behind a customer's
HTTPS proxy, actual browser/layout/accessibility acceptance, real speech-provider
and microphone tests, and deployment-level quotas/rate limits. The packaged
cognition is the existing evidence/TPC runtime, not a bundled unrestricted LLM.
No model weights or STT/TTS servers are included; speech endpoints must be
configured by the customer. The speech form's route is now correctly preserved.
Optional EGF dependencies are not claimed available on a fresh customer machine.
Site goals need explicit owner-approved evidence; the compiler will not invent
a Beta/Investor funnel or business destination when that evidence is absent.

No production deployment, Docker operation or inference-model change was
performed for this audit.
