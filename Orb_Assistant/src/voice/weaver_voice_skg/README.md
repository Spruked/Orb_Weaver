# Weaver Voice & Personality SKG

**Weaver** is the voice and personality layer for the ORBS Stage Articulation system. He is an original character — not a chatbot, not a script library — who speaks with conviction, structure, gravitas, and humane wit across every stage of the ORBS customer funnel.

## Quick Start

```bash
# 1. Place this SKG in your ORBS plugins directory
cp -r weaver_voice_skg /path/to/orbs/plugins/

# 2. Install dependencies (only PyYAML for cognitive state)
pip install pyyaml

# 3. Run tests
python -m pytest tests/test_weaver_voice.py -v

# 4. Use in your application
from logic.weaver_articulation import articulate, evaluate_tone

response = articulate({
    "stage_id": "landing_page",
    "screen_stable_at": time.time(),
    "visitor_input_active": False,
    "evidence": {"page_count": 42},
    "allowed_actions": ["start_preflight"],
    "recommended_action": "start_preflight",
    "situation_description": "Visitor arrives"
})

print(response.text)  # Weaver's response
print(response.humor_level)  # HumorLevel.FULL
print(response.first_person_compliant)  # True
```

## What Weaver Is

- **Deterministic:** Stage state drives tone. No randomness. No LLM creativity.
- **Evidence-bound:** Humor only fires when attached to real findings.
- **First-person:** "I'll scan your site." Not "The system will conduct a scan."
- **Stage-governed:** Full personality on landing. Quiet confidence at checkout. Celebratory at launch.
- **Anti-decoration compliant:** Delivers guidance or hands off. Never just floats.

## What Weaver Is Not

- ❌ A chatbot with "banter mode"
- ❌ An LLM generating original jokes
- ❌ A script library of pre-written lines
- ❌ An impersonation of Zig Ziglar, Brian Tracy, Earl Nightingale, or Robin Williams
- ❌ A tribunal convergence node

## File Overview

| File | Purpose |
|------|---------|
| `worker.json` | SKG contract, governance flags, entry points |
| `logic/weaver_articulation.py` | Core engine. Tone selection, evidence binding, first-person enforcement, anti-decoration checks |
| `cognitive_state/weaver_cognitive_state.yaml` | Personality dimensions, behavioral constants, humor dial, bit structure rules |
| `voice_presets/*.json` | Four tone presets: Full, Focused, Quiet, Celebratory |
| `stage_mappings/stage_to_humor_level.json` | Stage→tone mapping + intent routing table |
| `templates/sample_dialogues.json` | Reference dialogue examples (not a script library) |
| `tests/test_weaver_voice.py` | 10 test classes, full funnel traversal |
| `docs/SPEC.md` | Complete architecture and integration spec |

## Humor Levels

| Level | Stages | Example |
|-------|--------|---------|
| **Full** | Landing, Demo, Preflight, Crawl | "Give me thirty seconds. I'm faster than I look — and I look extremely aerodynamic." |
| **Focused** | Audit, Package, Questionnaire | "The good news is the technical foundation is strong. The less-good news is the content score appears to have left the building." |
| **Quiet** | Commitment, Signature, Checkout | "This is the real part. Take a look, sign when you're ready, and I'll get to work." |
| **Celebratory** | Payment, Live, Launch | "I'm live on your website right now. Go look. I'll wait — I'm very patient, it's kind of my whole thing." |

## Governance

- `humor_requires_evidence: true` — Jokes downgrade without evidence
- `first_person_mandatory: true` — Third-person auto-detected and corrected
- `anti_decoration.stabilization_threshold_ms: 2500` — Must speak or hand off within 2.5s
- `tone_authority: stage_governor_snapshot` — Tone derives from Governor, not internal reasoning

## License

Internal ORBS Architecture — see worker.json contract.
