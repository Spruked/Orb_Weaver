# ORB Vault SKG System

## Architecture

```
Orb_Vault_System/
│
├── Orb_Vault/                  ← RUNTIME CODE (this package)
│   ├── a_priori/               ← Settled truth logic
│   ├── a_posteriori/           ← Learned experience logic
│   ├── orb_assistant/          ← VaultCoordinator + QueryRouter
│   └── shared/                 ← Types, confidence, constants
│
└── vaults/                     ← PERSISTENT DATA (auto-created)
    ├── A_Priori_Vault/         ← Compiled data from Orb Weaver
    │   ├── catalog.json
    │   ├── ontology.json
    │   ├── qa.json
    │   └── policies.json
    │
    └── A_Posteriori_Vault/    ← Learned experience data
        ├── posteriori_state.json
        └── ledger/
            ├── ledger_00000.jsonl
            ├── ledger_00001.jsonl
            └── ...
```

## A Priori Vault — Settled Truth

Loaded from Orb Weaver output. Four subsystems:

| Subsystem | Purpose | Files |
|-----------|---------|-------|
| **Catalog** | Product/service dictionary with prices, SKUs, availability | `catalog_logic.py`, `catalog_cognitive.py` |
| **Ontology** | Business understanding: departments, services, policies, relationships | `ontology_logic.py`, `ontology_cognitive.py` |
| **QA** | Verified question/answer correspondences | `qa_logic.py`, `qa_cognitive.py` |
| **Loader** | Reads Orb Weaver output (`catalog.json`, `ontology.json`, `qa.json`, `policies.json`) | `loader.py` |

### Catalog Schema
```json
{
  "product_id": "alp-001",
  "name": "Alpine Ridge Tent",
  "sku": "ALP-RDG-4P",
  "current_price": 349.00,
  "sale_price": 299.00,
  "currency": "USD",
  "variant": "4-Person",
  "availability": "In Stock",
  "source_url": "/products/alpine-ridge",
  "last_seen": "2026-08-19T12:00:00Z"
}
```

### Query Flow (A Priori)
```
"How much is the Alpine Ridge tent?"
    ↓
intent = PRODUCT_PRICE, entity = "Alpine Ridge"
    ↓
Catalog lookup → $349
    ↓
Natural response → TTS
```
**No LLM. No TPC. Direct hit.**

---

## A Posteriori Vault — Learned Experience

### Lifecycle
```
NEW EXPERIENCE
    ↓
candidate node / edge
    ↓
verification (multi-signal)
    ↓
promotion
    ↓
usage reinforces weight
    ↓
repeated success strengthens relationship
```

### Degradation → Pruning
```
contradiction     ─┐
staleness          │
source change      ├→ weaken / merge / compress / retire
low usefulness     │
duplication       ─┘
poor outcomes     ─┘
```

**Pruning is based on usefulness and validity, NOT age.**

### Verification Signals
- `REPETITION` — same pattern observed multiple times
- `OUTCOME_SUCCESS` — led to successful resolution
- `SOURCE_CONSISTENT` — underlying data unchanged
- `OWNER_APPROVED` — explicit owner validation
- `CROSS_REFERENCE` — confirmed by independent path

### Self-Improvement
- Successful usage reinforces confidence (+0.03 per success, streak bonuses)
- Fast resolutions get micro-boosts
- Time decay applies to unused knowledge (half-life: 30 days)
- Periodic maintenance runs: decay → contradiction detection → pruning → promotion evaluation

### Confidence Caps
- Default cap: 0.95
- Under peer tension: 0.75
- Promotion threshold: 0.60 minimum

---

## Integration with ORB Assistant

```python
from vault.orb_assistant import VaultCoordinator, QueryRouter
from vault.shared.types import IntentType

# Initialize — defaults automatically point to ../vaults/
coordinator = VaultCoordinator()
#   weaver_output_dir defaults to:  ../vaults/A_Priori_Vault
#   posteriori_data_dir defaults to: ../vaults/A_Posteriori_Vault

# Route a query
intent, entities, conf = QueryRouter.route(
    "How much is the Alpine Ridge tent?",
    catalog_names=["Alpine Ridge Tent", "Summit Pack"]
)

# Resolve through vault stack
result = coordinator.resolve(
    query_text="How much is the Alpine Ridge tent?",
    intent=intent,
    entities=entities,
    session_id="sess_abc123"
)

# Result flows:
# 1. A Priori catalog → direct price → answer
# 2. A Priori ontology/QA → business knowledge
# 3. A Posteriori learned → verified experience patterns
# 4. Escalate to TPC/LLM if all vault layers miss

# Report outcome for learning
coordinator.report_outcome(
    query_text="...",
    intent=intent,
    entities=entities,
    resolution_source="a_priori_catalog",
    answer="$349",
    success=True,
    session_id="sess_abc123"
)

# Periodic maintenance (daily cron)
coordinator.run_maintenance()
```

### Custom Paths
```python
# If your vaults live elsewhere:
coordinator = VaultCoordinator(
    weaver_output_dir="/custom/path/to/priori_data",
    posteriori_data_dir="/custom/path/to/posteriori_data"
)
```

---

## File Inventory

### Shared Infrastructure
| File | Purpose |
|------|---------|
| `shared/types.py` | Core dataclasses: Entity, Relation, KnowledgeNode, Experience, etc. |
| `shared/confidence.py` | Confidence calculation, decay, reinforcement, cap enforcement |
| `shared/constants.py` | All thresholds and operational constants |

### A Posteriori (16 files)
| File | Purpose |
|------|---------|
| `ledger.py` | Immutable append-only experience ledger |
| `experience_logic.py` | Create experiences, extract candidates |
| `experience_cognitive.py` | Buffer, queue, pattern index |
| `verification_logic.py` | Multi-signal verification evaluation |
| `verification_cognitive.py` | Verification tracking state |
| `promotion_logic.py` | Candidate → promoted gate |
| `promotion_cognitive.py` | Promotion history tracking |
| `reinforcement_logic.py` | Usage-based confidence reinforcement |
| `reinforcement_cognitive.py` | Usage history, trend analysis |
| `contradiction_logic.py` | Conflict detection (node-node, node-priori) |
| `contradiction_cognitive.py` | Active contradiction tracking |
| `pruning_logic.py` | Usefulness/validity-based pruning decisions |
| `pruning_cognitive.py` | Pruning history, retired archive |
| `merger_logic.py` | Deduplication, merge, compress clusters |
| `merger_cognitive.py` | Canonical form tracking |
| `posteriori_logic.py` | **Main coordinator** |

### A Priori (8 files)
| File | Purpose |
|------|---------|
| `catalog_logic.py` | Price, availability, spec lookups |
| `catalog_cognitive.py` | Multi-index catalog storage |
| `ontology_logic.py` | Business ontology traversal |
| `ontology_cognitive.py` | Entity-relationship graph storage |
| `qa_logic.py` | Pattern-matching Q&A resolution |
| `qa_cognitive.py` | QA correspondence storage |
| `loader.py` | Orb Weaver output ingestion |
| `priori_logic.py` | **Main coordinator** |

### ORB Assistant Integration (2 files)
| File | Purpose |
|------|---------|
| `vault_coordinator.py` | Orchestrates both vaults, TTI routing |
| `query_router.py` | Intent classification, entity extraction |

---

## Design Principles

1. **Logic/Cognitive Separation** — Every subsystem has `_logic.py` (deterministic algorithms) and `_cognitive.py` (mutable state). They live in the same folder, connected by local imports.

2. **Immutable Ledger** — All experiences append to an immutable JSONL ledger. No deletions. Integrity verifiable by hash.

3. **Bounded Confidence** — Caps enforced at 0.95 default, 0.75 under tension. No absolute truth declarations.

4. **Self-Pruning, Not Age-Pruning** — Knowledge is retired based on degradation signals and usefulness scores, not calendar age.

5. **A Priori Wins** — If posteriori contradicts settled truth, posteriori loses automatically.

6. **Site-Agnostic** — No hardcoded sites. Discovers Orb Weaver output at runtime.

7. **No External Calls Within Vaults** — All logic is internal. No LLM, no API calls, no network during vault operations.

---

## Maintenance Schedule

| Task | Frequency | Method |
|------|-----------|--------|
| Posteriori maintenance | Daily | `coordinator.run_maintenance()` |
| Reload A Priori | After each Orb Weaver crawl | `coordinator.reload_priori()` |
| Ledger integrity check | Weekly | `coordinator.posteriori.ledger.verify_integrity()` |
| State persistence | Every 5 min / 10% of ingests | Automatic |
