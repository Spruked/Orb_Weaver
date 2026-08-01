# Context & Correspondence Orchestrator (CCO) v1.0.0

Governed ORBS runtime conductor for task analysis, context reduction, Vault retrieval,
evidence packaging, correspondence routing, provenance, budgeting, promotion, and
articulation handoff.

## Architecture

- **Task Analysis**: Determine intent, entities, information needs, constraints and budget.
- **Retrieval**: Pull the relevant Site World, Vault, semantic index and verified prior cases.
- **Context Reduction**: Build a bounded working context without losing required evidence.
- **Vault Compile**: Deterministically compile ORBS structured records with provenance.
- **Correspondence Routing**: Prepare evidence for the Correspondence Engine.
- **Governance**: Preserve source boundaries, confidence caps, promotion gates and write-back rules.

## ORBS Integration

> **Vault is authoritative. CCO builds disposable working projections.**
> **Correspondence Engine reasons. LLM only articulates governed output.**

```
Task / Website ORB perception
    ↓
Context & Correspondence Orchestrator
    ↓
Site World + Vault evidence package
    ↓
Correspondence Engine
    ↓
Articulation model
    ↓
Execution Governor / answer / write-back decision
```

## Quick Start

```bash
pip install -r requirements.txt
python -m context_correspondence_orchestrator.api.main
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/compress` | POST | Create a CCO working context package |
| `/v1/context/run` | POST | Run a task against a stored CCO context package |
| `/v1/canary/test` | POST | Test for scope leakage |
| `/health` | GET | System health |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CCO_LLM_PROVIDER` | `local` | `local`, `openai` |
| `CCO_HANDLE_STORE_PATH` | `./data/handles` | Storage path |
| `CCO_DEFAULT_TTL_SECONDS` | `86400` | Handle TTL |

## Canary Testing

Run canary tests to detect:
- **Scope leakage**: CCO answer path straying outside its task domain
- **Factual loss**: Required evidence missing from the working context
- **Hallucination risk**: Confidence assessment
