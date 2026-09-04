# TTI agency contract

**RAL = kernel. Weaver = habitat adapter. Skin Studio = costume. ROS = physical body adapter. NATS = nerves.**

Branches may not share code. They **must** share this contract. If a branch invents a parallel WorldState, proposal, or primitive name, it has forked the organism.

Repos stay separately named: kernel, habitat, costume. The platform is the contract, not a monorepo blob.

---

## Invariant

The model never owns WorldState.  
The model never signs `cmd.*`.  
A skin never changes what is allowed.  
An adapter never proposes and never judges.

```text
WorldState snapshot
        ↓
ActionProposal          (tool + speech + motion together)
        ↓
Core-4  →  CycleVerdict (veto > ask > revise > allow)
        ↓
CycleEnvelope           (same cycle_id on every lane)
        ↓
   TOOL / SPEECH / MOTION
        ↓
   adapters (DOM / voice+skin / ORB compositor / ROS)
        ↓
   reality → next WorldState
```

PLC / browser origin isolation sit **beside** this stack, not inside Core-4.

---

## 1. Canonical WorldState

Habitat implementations differ. The **interface** does not.

| Field | Meaning |
|---|---|
| `snapshot_id` | Unique id for this freeze |
| `etag` | Monotonic version; proposals must cite it |
| `habitat` | `website` \| `desktop_orb` \| `robot` |
| `timestamp` | `{ sec, nsec }` habitat clock |
| `observables` | Named things that exist now (DOM nodes, TF frames, components) |
| `capabilities` | Tools / bodies currently usable |
| `constraints` | `forbidden_regions`, `dangerous_actions`, `auth_level` |
| `tasks` | Active goals / task ids |
| `focus` | What the user (or camera) is on |
| `uncertainty` | Load, staleness, sensor health |
| `extra` | Habitat-private bag; tribunal must not require it |

Locke reads `observables`. Kant reads `constraints` + `capabilities`. Hume reads `uncertainty` + proposal confidence. Spinoza reads `tasks` vs tool/primitives.

A website snapshot and a robot snapshot are **substitutable** at the tribunal boundary.

---

## 2. Canonical ActionProposal

One cycle → **one** proposal. Tool, speech, and motion are co-emitted. Adapters **must not** invent a missing lane after `allow`.

Required: `cycle_id`, `world_etag`, `active_goal`, `intent_class`, `tool`, `speech`, `motion`, `confidence`, `risk_profile`.

Optional: `expression` — semantic affect for Skin (`acknowledge`, `confused`, …). Core-4 does not authorize shaders. It authorizes the **bound** speech mode + motion primitive. If `expression` implies a primitive not in the proposal, the proposal is invalid **before** tribunal (schema fail).

No adapter may add `tool` after verdict.

---

## 3. Primitive registry

Source of truth: `primitives.yaml`.

Three kinds:

| Kind | Who defines meaning | Who implements look |
|---|---|---|
| `motion` | Kernel | Costume (Skin) + body adapters (ORB / ROS) |
| `speech` | Kernel | Voice + Skin presentation |
| `expression` | Kernel (id + default binding) | Skin only |

A Skin Studio creator implements **how** `focus_on` looks, not **whether** it may run. They ship:

- visual shell, core renderer  
- motion primitive implementations  
- speech-mode presentation  
- expression → primitive mappings  
- state transitions  

They do **not** ship Kant, tool ids, or WorldState writers.

Gen-1 example: `expression: acknowledge` with `params.valence: love` binds to `motion: idle_in_region` + a crude heart in the default core. A later skin binds the same id to richer mesh. **Same approved id.**

Adding a primitive is a kernel version bump (`registry_version`). Skins targeting an unknown id must idle, not invent.

---

## 4. Canonical CycleEnvelope

Every lane message carries:

| Field | Rule |
|---|---|
| `event_id` | UUID |
| `cycle_id` | Ties proposal, verdict, tool, speech, motion, telemetry |
| `proposal_id` | Id of the ActionProposal |
| `verdict_id` | Id of CycleVerdict |
| `world_etag` | Snapshot the planner believed |
| `registry_version` | Primitive registry semver |
| `timestamp` | Habitat clock |
| `lane` | `tool` \| `speech` \| `motion` \| `telemetry` |
| `payload` | Lane-specific, primitives from the registry only |

NATS subject or in-process topic is a **transport**. The object is the same.

---

## 5. Adapter boundary

Adapters: `DomAdapter`, `OrbCompositorAdapter`, `RosAdapter`, `VoiceAdapter`, `SkinAdapter`.

They **consume** authorized envelopes and **return** telemetry (`observables` diffs, pose, utterance complete, errors).

They **never**:

- call the LLM  
- emit an ActionProposal  
- implement Core-4  
- widen the primitive set  
- publish `cmd.*` except the ROS/NATS bridge consuming already-allowed motion  

If NATS dies, adapters fail closed (hold last-safe / idle). They do not “complete the thought.”

---

## 6. Versioning

- `tti.worldstate.v1`  
- `tti.action_proposal.v1`  
- `tti.cycle_envelope.v1`  
- `tti.primitives.v1`  

RAL Core’s older enums (`whisper_hint`, `servo_orbit`, `smooth_glide`) are **aliases** in the registry, not a second vocabulary.
