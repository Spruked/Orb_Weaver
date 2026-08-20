A Priori Vault — Settled Truth Data Store
=========================================

This directory holds the compiled, owner-approved, crawl-verified truth
that the ORB Assistant uses for direct lookups.

Populate this folder with Orb Weaver output:

  catalog.json      → Product/service catalog (prices, SKUs, availability)
  ontology.json     → Business understanding graph (or site.skg)
  qa.json           → Verified question/answer correspondences
  policies.json     → Owner-approved policy rules

These files are READ-ONLY at runtime. The A Priori Vault does not learn.
It is settled truth — loaded once per crawl, refreshed when Orb Weaver re-runs.

DO NOT EDIT these files manually unless you are the site owner.
