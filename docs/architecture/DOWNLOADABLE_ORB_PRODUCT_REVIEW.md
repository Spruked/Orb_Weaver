# Downloadable Website ORB Product Review

## Review scope

This review covers the customer-facing clone template at
`manufacturing/templates/Website_Orb_Final`, its scan-to-manufacture path, the
`.orbpack` download contract, and the scan/package commercial surface.

## Product conclusion

The downloadable ORB is a site-specific runtime package, not a copy of the
Orb Weaver factory. A completed customer package is compiled from the
customer's completed scan and approved configuration, then delivered as a ZIP
with `manifest.json` and `website-orb/`. The installed clone has its own
`runtime/vault_system/`, site world, SKG, lexical index, report context,
pointer map, policies, and learning-loop files. It does not require the
factory database, factory API, factory vocabulary, or Dock Station application
to answer its core text and route questions.

The package is installable with Python 3.10+, but it is not a static-site
upload. It needs a customer-controlled Python service behind HTTPS. Speech
requires customer-controlled STT/TTS providers and browser microphone
permission; those services and model weights are not bundled.

## Clone template inventory

| Area | Verified source | Customer value |
| --- | --- | --- |
| Runtime | `backend/app.py`, `run.py`, `backend/runtime/` | Local route lookup, site-world context, governed answers, bootstrap, and maintenance |
| Scan-derived knowledge | `runtime/vault_system/payload/` | Site SKG, lexical aliases, knowledge chunks, retrieval index, catalog, policies, and route context |
| Commercial evidence | `payload/apriori/catalog.json`, `catalog.db`, `ontology.json`, `qa.json` | Products, services, offers, specifications, FAQs, and approved facts |
| Spatial guidance | `payload/pointers.json`, `pointer_correspondence.json`, `permissions.json` | Candidate targets and guidance permissions; live DOM verification remains mandatory |
| Widget | `assets/widget.js` / generated frontend widget | Embeddable visitor-facing ORB with customer-site origin checks |
| Voice | `backend/voice_runtime.py`, `INSTALL.md` | Provider boundary for STT/TTS; text remains available when speech providers are absent |
| Integrity | `payload/payload_manifest.json`, `backend/integrity.py` | Site/scan identity, artifact hashes, approval state, and package tamper checks |
| Storage | `runtime/vault_system/` | One authoritative installed storage root |
| Maintenance | `/orb/maintenance/status`, `/orb/maintenance/cycle` | Owner-triggered product delta and affected-target reverification; pending changes do not silently replace verified state |

## Scan products and recommended customer packages

The commercial structure now distinguishes evidence products from installed
runtime editions:

| Product family | Package | Includes |
| --- | --- | --- |
| Scan | Basic Website Intelligence Scan | Discovery, crawl inventory, content, navigation, basic technical health, foundational SEO, baseline spatial mapping, and downloadable evidence |
| Scan | Enhanced Website Intelligence Scan | Basic plus deeper semantics, customer journeys, conversion paths, product intelligence, accessibility, responsive layouts, and expanded spatial analysis |
| Scan | Platinum Website Intelligence Scan | Enhanced plus the complete applicable capability dataset, advanced spatial/workflow analysis, commercial opportunities, verification evidence, and comprehensive recommendations |
| Specialized | SEO Intelligence Package | Technical SEO, search visibility, structured data, indexing, content opportunities, and supported keyword/competitive analysis |
| Specialized | Dandy Advertising Intelligence Package | Site Prominence, Commercial Opportunity, Campaign Readiness, campaign briefs, Dandy Show production briefs, traceable evidence, and connected advertising data where available |
| ORB | Basic Website Visitor ORB | Site-specific visitor guidance, voice-first interaction, approved context, and basic verified navigation |
| ORB | Enhanced Website Intelligence ORB | Basic plus expanded scan evidence, commercial/SEO/Dandy/spatial context, and learning-loop runtime context |
| ORB | Platinum Website ORB w/Premium Dock Station | Enhanced plus Premium Dock Station owner controls, deployment workflow, maintenance, and launch verification |

The Platinum scan must represent the complete applicable scanning capability
defined by the Master Capability List; it is not merely a larger PDF. The
full scanning engine remains capable of collecting authorized measurements,
while customer entitlement controls which analyses, reports, exports, and
runtime capabilities are delivered. Expensive analyses and external API calls
should run only when required by the purchased package. The Basic scan is the
recommended starting point, and a Basic ORB may be offered from a smaller
approved evidence set only when the installation readiness and target-quality
gates pass.

Dandy is a Tagless Advertising Intelligence product: connected analytics may
enrich it later, but it stands on public website evidence alone. Its three
assessments are deliberately separate—Site Prominence, Commercial Opportunity,
and Campaign Readiness—so homepage placement or price cannot be mistaken for
profitability or sales volume. Findings retain source URL, scan timestamp,
evidence type, and verification status. Campaign briefs are distinct from
Dandy Show production briefs; public staff information never authorizes use of
a person's identity or likeness.

Dandy lifecycle states are `discovered`, `production_ready`, `owner_review`,
and `approved_for_publication`. The approved export endpoint fails closed until
the last state is explicitly recorded with rights, offer-term, and brand
review confirmations.

## Commercial implementation

The authoritative catalog is exposed at `GET /api/orb/package-catalog` and is
persisted under the canonical Vault as `marketing/orb_package_catalog.json`.
All eight package records start with `price_cents: null`, `pricing_status: tbd`,
and `purchasable: false`. This prevents an unpriced package from becoming a
$0 checkout item.

The public pricing page is `/pricing`. It shows the four scan products and the
three ORB editions, clearly labels TBD pricing, and does not imply a purchase
is available before approval.

Admins can manage package price, visibility, and purchasability at
`/admin/packages` or through:

- `GET /api/admin/orb/package-catalog`
- `PATCH /api/admin/orb/package-catalog/{sku}`

The API rejects `purchasable: true` when no price is set. Setting a price does
not by itself authorize a package; the administrator must also explicitly
enable purchase. Checkout fulfillment and automatic post-payment ORB
entitlement remain governed by the existing ORBS stage flow and are not
silently bypassed by this catalog.

## Remaining acceptance gates

- Set real prices and purchase policy after owner approval.
- Map each approved package SKU to checkout entitlements and fulfillment.
- Run a clean-host `.orbpack` install behind HTTPS with real STT/TTS providers.
- Run browser/layout/accessibility acceptance against a representative
  customer site.
- Verify a complete scan → package build → download → install → launch flow.
- Confirm live pointer recovery and target verification on each customer site;
  extracted pointer count alone is not deployment approval.

The package remains a truthful, evidence-bound installable ORB. It must not
claim production voice, live pointer completion, or purchase availability until
those external and owner-controlled gates are verified.
