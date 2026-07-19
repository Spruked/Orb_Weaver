# ORB Marketplace Architecture

## Platform role

The **ORB Marketplace** is the trusted distribution, licensing, update, and management layer for the ORBS ecosystem. It is more than a skin catalog or download page: it turns the shared ORBS runtime into a platform where customers can acquire complete ORBs and separately install compatible appearance, voice, motion, knowledge, language, and tool packages.

Every Marketplace product must preserve the separation between the shared runtime and its versioned configuration:

```text
Shared ORBS runtime
  -> verified platform adapter
  -> licensed ORB product
  -> approved capability packages
  -> owner-selected identity packages
  -> versioned install/update/rollback
```

The Marketplace must never silently grant a tool, apply detected branding, replace the immutable Factory Default, or bypass ownership, consent, runtime permission, or deployment-review gates.

## V1 buyer-seller focus

The first commercial Website ORB target is the transaction relationship between buyers and sellers. Marketplace sites are especially valuable because the same deployment may guide browsing and registered buyers while separately supporting prospective and active sellers.

Marketplace participant state may select an approved buyer, account-holder, seller-onboarding, or active-seller flow, but it must never replace the host's authentication or authorization. Buyer information, seller tools, listing administration, order state, and marketplace policies remain separated by the host application's access controls.

The canonical workflows, safeguards, and acceptance criteria are defined in `docs/ORB_WEAVER_V1_TRANSACTIONAL_DOCTRINE.md`.

## Product families

The Marketplace can distribute complete ORBs for different environments and purposes:

- **Website ORBs:** site-aware voice guides with Site World knowledge, verified pointer guidance, form assistance, product/document explanations, and policy-bounded browser actions.
- **Desktop ORBs:** Windows, macOS, or Linux companions for application guidance, settings, files, accessibility, and explicitly approved host tools.
- **Business ORBs:** customer service, sales, HR, training, compliance, inventory, manufacturing, and logistics assistants.
- **Industry ORBs:** packages designed for medical, legal, agriculture, construction, automotive, aviation, education, real estate, hospitality, energy, and other governed domains.
- **Home ORBs:** personal and family assistants for recipes, smart-home guidance, hobbies, pet care, gardening, and personal organization.
- **Educational ORBs:** teaching companions for mathematics, science, history, programming, languages, music, and engineering.
- **Entertainment ORBs:** storytellers, tour guides, museum hosts, fictional characters, historical interpreters, and children's companions.
- **Enterprise ORBs:** governed deployments for internal knowledge, documentation, help desks, compliance, and multi-site organizations.

Category labels describe discovery and packaging; they do not weaken safety, evidence, licensing, or professional-use boundaries.

## Enhancement packages

Complete ORBs and enhancements are different product types. Enhancements may include:

- premium skins;
- voice packs;
- motion packs;
- knowledge packs;
- language packs;
- tool plugins and service adapters.

Skins are appearance-only. A skin installation or rollback must not rebuild Site World or Pointer Map, restart runtime, disconnect WebSocket, or change permissions. Every compatible ORB retains `orb_factory_default_v1` as its immutable, permanent visual fallback.

Knowledge and tool packages require stronger review than cosmetic packages. They must declare sources, version, supported runtime, permissions, data access, network access, confirmation policy, and revocation behavior. Regulated or high-impact packages require domain-appropriate review and must not imply professional authorization merely because they are listed.

## Creator ecosystem

Approved third-party creators may publish ORBs and enhancement packages. Each listing should provide:

- product description and screenshots;
- an isolated demo where appropriate;
- supported platforms and runtime versions;
- declared capabilities and permissions;
- data-handling and network requirements;
- version history and support policy;
- license and transfer terms;
- security/review status;
- customer reviews that are clearly distinct from verification evidence.

Creator revenue sharing is a commercial layer over the same technical trust chain. Payment does not substitute for package verification or owner approval.

## Discovery taxonomy

The public catalog may organize products under Featured, New Releases, Popular, Business, Education, Healthcare, Government, Retail, Finance, Technology, Agriculture, Entertainment, Productivity, Home, Enterprise, and Open Source. One product may have multiple discovery categories while retaining one canonical product identity and version history.

## Delivery and lifecycle

Marketplace delivery should support:

```text
discover
  -> inspect compatibility and permissions
  -> purchase or acquire license
  -> owner/admin approval when required
  -> verified installation
  -> health and entitlement checks
  -> atomic update
  -> explicit rollback
  -> revocation or transfer
```

Customers may download, install, update, restore prior versions, transfer eligible licenses, and synchronize entitlements across approved devices or sites. Updates must be signed/versioned and recoverable. Runtime, Site World, Pointer Map, skin, knowledge, and tool revisions remain separately identifiable so a cosmetic update cannot masquerade as a capability update.

## Surfaces and hosting

The Marketplace is both a web service and an integrated ORB surface:

- Orb Weaver web application;
- Website ORBs where the owner enables Marketplace access;
- Desktop ORBs;
- future mobile ORBs.

`marketplace.orbweaver.spruked.com` is the intended dedicated public hostname. It is an architecture target, not a statement that the hostname or standalone service is currently deployed. The existing repository route surface remains `/marketplace` until a verified standalone deployment supersedes it.

An embedded Marketplace must not interrupt the host site's primary task or purchase without clear user action. Website owners can disable embedded discovery while retaining installed-product management.

## Commercial model

Supported commercial forms may include free products, one-time purchases, subscriptions, enterprise and organization-wide licenses, premium enhancement packs, custom business ORBs, support plans, and creator revenue sharing. Entitlements must be explicit, portable where the license permits, auditable, and revocable without destroying customer-owned evidence or configuration history.

## Trust requirements

Marketplace publication and installation should enforce:

- stable publisher and product identities;
- signed, content-addressed packages;
- declared runtime compatibility;
- malware and dependency scanning;
- permission and data-access review;
- owner/admin consent for material capabilities;
- per-asset brand consent and ownership verification;
- immutable Factory Default availability;
- versioned installation evidence and rollback;
- vulnerability, deprecation, and removal notices;
- separation of customer data from creator analytics;
- no automatic promotion of reviews or generated claims into verified knowledge.

## Revenue and product vision

The Marketplace supports an ecosystem of specialized intelligent assistants rather than isolated chatbots or static downloads. Products share a consistent ORBS runtime and lifecycle while expressing distinct appearance, voice, motion, knowledge, tools, and purpose. The result is a recognizable platform experience across websites, desktops, organizations, homes, education, entertainment, and enterprise deployments.

The stable architecture name is **ORB Marketplace**. “The ORB Exchange” may be evaluated later as a public campaign or merchandising label, but it should not create a second product identity or incompatible catalog.
