# Desktop ORB Assistant — NOW Movement and Diagnostic Surface

Status: **prepared architecture and product contract**. This document does not claim that every scanner or adapter is already implemented.

## Purpose

The Desktop ORB Assistant is the primary desktop home for deep MCP tools, local runtime awareness, machine diagnostics, window/control guidance, voice presence, and embodied movement.

A diagnostic-capable Desktop ORB requires three categories of knowledge:

1. what to observe on the machine;
2. what to interpret from that evidence;
3. what to research when local evidence is not enough.

It must remain inside the **system domain** and outside the **personal domain** unless the owner grants a separate, explicit capability.

---

## 1. Movement System Contract

### Current FieldMotion baseline

The Desktop ORB movement baseline is the intent-driven FieldMotion system.

```text
maxSpeed:         0.64
accel:            0.04
damping:          0.983
steerMul:         0.74
maxAcceleration:  0.065
```

The movement update contract is:

```javascript
update({
  currentPosition,
  targetZone,
  intentProfile,
  screenBounds,
  maxAcceleration = 0.065
})
```

The movement result is expected to expose:

```javascript
{
  position,
  velocity,
  fieldState: {
    intensity,
    turbulence
  }
}
```

### Shared movement intent vocabulary

Website ORBs and Desktop ORBs may use different renderers, but they should consume the same high-level movement intentions:

- `ATTENTION_ACQUIRE`
- `GUIDE_TO_TARGET`
- `PRESENT_INFORMATION`
- `WAIT_WITH_PURPOSE`
- `RETURN_TO_COMPANION_POSITION`
- `INTERRUPT`
- `CELEBRATE`
- `WARN`

### Locked movement doctrine

- The ORB moves because it has a reason, target, or communicative purpose.
- Cursor position is an input signal, not movement authority.
- No random wandering, twitching, frantic bouncing, or decorative motion.
- No forced corner parking or indefinite idle hovering.
- A brief pause is allowed only when the pause communicates purpose.
- The ORB must never linger, stall, loiter, or remain indecisively in one place.
- Movement should be slower, controlled, and legible as machine intent.
- The ORB must remain visible, clickable/tappable, and reachable.
- Pointer guidance must avoid covering the target control.
- Choreography such as freestyle, waltz, or salsa belongs in an explicit performance lane and must not leak into ordinary guidance.

### Movement integration target

The shared movement layer should be organized around:

```text
motion/
  field_motion
  trajectory_control
  anti_linger
  target_clearance
  intent_profiles
  choreography/
```

The renderer remains platform-specific. The movement intent contract, anti-linger rules, target-clearance rules, and trajectory policy should be reusable by both Website ORBs and the Desktop ORB.

---

## 2. Core Diagnostic Knowledge

The Desktop ORB must understand these domains before it can interpret machine evidence responsibly:

- `system_state_model` — CPU, RAM, GPU, disk, processes, threads, and I/O load;
- `os_health_signals` — event logs, crashes, hangs, warnings, and update failures;
- `driver_stack` — GPU, audio, USB, HID, chipset, and related driver state;
- `network_model` — interfaces, DNS, routing, latency, jitter, packet loss, and local listeners;
- `security_posture` — firewall state, antivirus state, signatures, and suspicious runtime behavior;
- `storage_integrity` — SMART data, file-system errors, capacity, and I/O latency;
- `thermal_model` — temperatures, throttling, clocks, and fan behavior;
- `power_model` — power plans, battery state where applicable, sleep, wake, and power instability signals;
- `app_behavior` — resource patterns, crashes, update state, and dependency failures;
- `llm_runtime_state` — model identity, load state, VRAM usage, inference health, latency, and endpoint readiness;
- `orb_subsystems` — perception, motion, voice, cognition, Vault, MCP adapters, and local service health.

---

## 3. Permitted PC Scan Surface

The scanner should collect evidence only from approved system interfaces and selected project/runtime scopes.

### System and hardware

- CPU load, frequency, temperature, and throttling evidence;
- GPU load, VRAM, clocks, temperature, thermal limits, and active compute processes;
- RAM allocation, pressure, paging, and swap activity;
- disk capacity, SMART status, file-system warnings, and I/O latency;
- motherboard sensors when available through a trusted adapter;
- USB, audio, camera, microphone, and other peripheral status.

### Operating system

- Windows System and Application event logs;
- Security event summaries only where the owner has explicitly enabled that diagnostic permission;
- process table, command line where permitted, parent/child relationships, CPU, RAM, disk, and GPU usage;
- startup items, scheduled tasks, and autoruns;
- Windows service state and failure history;
- driver versions, device status, and mismatch indicators;
- narrowly defined registry health keys required for a diagnosed subsystem.

### Network

- interface and adapter state;
- IP configuration, routes, gateways, and DNS servers;
- latency, jitter, and packet-loss tests initiated for a diagnostic purpose;
- DNS resolution timing and failures;
- firewall rules relevant to the selected process or endpoint;
- listening loopback and local-network ports;
- process-to-port association;
- unexpected outbound connections presented as evidence, not automatically classified as malicious.

### Security

- antivirus product state, definition freshness, real-time protection state, and quarantine summaries;
- executable signing state and file provenance for a selected suspicious process;
- failed service starts, repeated login failures, lockout events, and abnormal listener changes;
- suspicious-process indicators based on evidence and confidence, never name recognition alone.

### Applications

- application crash reports and stack traces;
- process resource usage over time;
- installed version and update state where a supported source exists;
- missing runtime dependencies;
- selected application configuration and logs only when the owner chooses that application or project.

### LLM and ORB runtime

- llama.cpp executable identity and launch arguments;
- local model identity, GGUF path, load time, context size, and endpoint health;
- CUDA device detection, GPU-layer offload, VRAM allocation, and inference latency;
- Qwen TTS endpoint, GPU/CPU use, synthesis latency, and errors;
- microphone health, input level, noise floor, and device availability;
- speech-to-text readiness and latency;
- motion frame timing, dropped frames, target resolution, and anti-linger state;
- voice pipeline latency and synthesis failures;
- MCP server health and tool registration;
- Vault schema consistency, manifest integrity, and corruption checks.

---

## 4. Interpretation Surface

Raw metrics are not diagnoses. The interpretation layer should correlate evidence across time and subsystems.

It should be able to determine or rank evidence for conditions such as:

- CPU saturation versus one runaway process;
- physical RAM pressure versus a memory leak;
- GPU VRAM exhaustion versus shared-memory spill;
- thermal throttling versus ordinary high utilization;
- disk capacity pressure versus failing storage;
- endpoint failure versus firewall blockage versus process absence;
- audio-device failure versus microphone permission or sample-rate mismatch;
- model endpoint healthy but ORB integration path broken;
- animation slowdown caused by renderer frame loss versus model inference load;
- duplicate local model servers competing for GPU memory;
- service startup failure caused by permissions, path drift, missing DLLs, or port occupancy.

Every diagnosis should retain:

- observed evidence;
- source and timestamp;
- confidence;
- competing explanations;
- recommended next verification;
- owner-approved action boundary.

---

## 5. Research Surface

When local evidence identifies a product, version, error, device, or advisory requiring current external knowledge, the ORB may research:

- official GPU, chipset, audio, USB, and device-driver updates;
- Microsoft Windows known issues and update notes;
- official application release notes and bug trackers;
- official security advisories and CVEs;
- hardware specifications and thermal limits;
- llama.cpp and Qwen runtime documentation;
- quantization, CUDA, context, and VRAM optimization guidance;
- network and DNS troubleshooting from authoritative sources.

Research must be tied to observed local evidence. It must not become unrestricted browsing presented as diagnosis.

---

## 6. Prohibited Scan Surface

The diagnostic system must not scan or index:

- personal documents;
- email contents;
- browser history;
- passwords or credential stores;
- encrypted personal stores;
- cloud-account contents;
- financial records;
- private messages;
- photos or personal media;
- unrelated project folders.

A separate user-requested tool may access a personal source under its own explicit permission and purpose, but that access is not part of Desktop ORB diagnostics.

---

## 7. Desktop Endpoint Discovery

Desktop endpoint discovery should be handled by a local Desktop Scan Bridge or the approved Desktop MCP service, not by a public webpage.

The endpoint inventory should include:

- loopback listeners;
- approved local-network listeners;
- owning process and executable path where permitted;
- service identity;
- launch arguments where permitted;
- expected health path;
- protocol and authentication boundary;
- model or service identity returned by the endpoint;
- selected-project manifests and declared ports;
- current readiness, latency, and last failure.

The scanner must distinguish:

```text
port open
service responding
expected service responding
expected model or capability ready
normal ORB path verified end to end
```

These are not equivalent states.

---

## 8. Desktop Pointer Logic

Desktop pointer guidance extends the Website ORB pointer doctrine to windows and application controls.

### Preferred target sources

1. explicit application adapter targets;
2. Windows UI Automation and accessibility-tree identity;
3. stable window title, process identity, control role, name, automation id, and parent context;
4. bounded visual recovery only when semantic targeting is unavailable.

Screenshots and raw coordinates must not be the primary identity system.

### Desktop target identity

A deterministic desktop target should be derived from evidence similar to:

```text
process + window identity + control role + automation id + accessible name + parent context
```

A pointer record should preserve:

- target id;
- application/process scope;
- window identity;
- control role and accessible name;
- automation id or adapter locator;
- parent context;
- permitted actions;
- aliases;
- confidence;
- target-clearance geometry;
- recovery policy.

### Runtime resolution

Before moving or pointing, the Desktop ORB must:

1. verify the expected process and window;
2. resolve the target through the adapter or accessibility tree;
3. verify role, name, parent context, visibility, and enabled state;
4. calculate a target zone and clearance area;
5. request `GUIDE_TO_TARGET` from the movement system;
6. point without covering the control;
7. refuse to click or type unless the current permission and Stage Governor action allow it.

If target identity cannot be verified, the ORB should explain where the control is expected and request owner guidance instead of guessing.

---

## 9. Diagnostic Pipeline

```text
Owner request or detected health concern
  -> permission and scope check
  -> system evidence collectors
  -> endpoint and application adapters
  -> normalized Diagnostic Surface Map
  -> correlation and interpretation
  -> confidence and competing explanations
  -> current-source research when required
  -> spoken/visual explanation
  -> pointer guidance to the relevant control
  -> owner-approved action
  -> verification scan
  -> Vault-backed diagnostic record
```

All persistent evidence, manifests, diagnostic records, learned observations, and reports remain subject to Orb Weaver's one-Vault law.

---

## 10. Initial Implementation Order

1. Canonical Diagnostic Surface Map schema.
2. Read-only system collectors for CPU, RAM, GPU, disk, process, service, event-log, network, and local endpoint state.
3. ORB runtime adapter for llama.cpp, Qwen TTS, voice, motion, MCP, and Vault health.
4. Desktop target-map schema using Windows UI Automation/accessibility evidence.
5. Shared movement intent and anti-linger contract.
6. Diagnostics UI showing evidence, confidence, and recommended verification.
7. Owner-approved action adapters.
8. External research lane tied to observed evidence.

The first release should remain read-only except for explicit owner-approved verification actions.