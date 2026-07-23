# RAG, Lexicon, and Retrieval Decision

Date: 2026-07-22

## Decision

Do not treat RAG as a new independent subsystem. Retrieval work is blocked
behind a lexicon readiness audit because the current codebase does not yet
show a first-class lexicon scanner, lexicon database, knowledge chunk table, or
retrieval index contract.

The current implementation has useful crawl-time semantic and entity signals,
but those are not the same as the lexicon layer described in the architecture.

## Current Audit Finding

Found in code:

- `backend/app/crawler/engine.py` performs deterministic page semantic analysis.
- `backend/app/crawler/engine.py` extracts named entities and can optionally ask
  the local LLM for entity categories.
- `backend/app/models/database.py` stores `semantic_analysis` and
  `entity_analysis` JSON on `crawled_pages`.
- pointer records use aliases for target intent matching, but that is pointer
  identity support, not site knowledge lexicon normalization.
- `vault_system/README.md` and `backend/app/core/storage.py` define the canonical
  Vault layout and generated indexes root.

Not found:

- lexicon scanner module
- `lexicon_terms` table or Vault record set
- `lexicon_aliases` table or Vault record set
- first-class entity/relationship store for site knowledge
- knowledge chunk builder
- embedding/index manager
- retrieval service
- retrieval logs

The existing crawl/entity analysis can be used as source material for a
lexicon implementation, but it should not be documented as a completed lexicon
dependency until those records and contracts exist.

## Required Build Order

1. Define the Vault-owned site knowledge record shape.
2. Promote crawl-derived terms/entities into explicit lexicon records.
3. Add alias, entity, relationship, source, lifecycle, tenant, project, orb, and
   knowledge-version fields.
4. Add tests proving tenant/project filtering and lifecycle exclusion.
5. Build knowledge chunks from lexicon-backed source records.
6. Add derived keyword/vector indexes as rebuildable views only.
7. Add the retrieval service against those records.

Until step 4 exists, query normalization, entity resolution, alias matching,
and RAG retrieval behavior are provisional.

## Retrieval Conflict Policy

Use hard filters first:

1. tenant, project, and orb match
2. active lifecycle state
3. current or requested knowledge version

Then score candidates by content type and intent. Freshness must not globally
outrank exact lexicon/entity match.

For named entities, product codes, service names, SKUs, policies by title, and
site-specific terminology:

1. source authority
2. exact lexicon/entity match
3. current knowledge version
4. freshness
5. semantic relevance

For volatile facts such as hours, pricing, availability, deadlines, event
dates, policy windows, and status notices:

1. source authority
2. current knowledge version
3. freshness
4. exact lexicon/entity match
5. semantic relevance

For general explanatory content:

1. source authority
2. current knowledge version
3. exact lexicon/entity match
4. semantic relevance
5. freshness

When two active, equally authoritative candidates still contradict each other,
the retrieval service must return an explicit conflict status instead of
forcing a speakable answer.

## Central Rule

The crawl supplies source material. The lexicon normalizes site language only
after its records exist and are audited. The Vault owns authoritative
knowledge. Search indexes are rebuildable derivatives. Orb Assistant receives
evidence packages and does not crawl, index, version, or resolve conflicts on
its own.
