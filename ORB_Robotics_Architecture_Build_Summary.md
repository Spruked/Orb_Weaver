# ORB Robotics Architecture — Build Summary
The three-module split is sound. The first thing to build is **not one of the three modules themselves**; it is the strict protocol they all share.

## First build artifact: the ORB command-and-telemetry contract
Create one canonical schema, preferably:

```
shared/contracts/orb_robot_protocol.schema.json
```
Then generate or mirror:

```
frontend/src/orb/robotics/orbRobotProtocol.ts
backend/app/orb/robotics/orb_robot_protocol.py
```
This prevents the browser, backend, reasoner, pointer runtime, and future physical actuator from quietly developing incompatible message formats.

The current project already has this same cross-language pattern for `PlotRecord`: the Python schema and TypeScript schema contain the same semantic target fields, including `target_id`, locator, confidence, allowed actions, status, and verification timestamp.

---

# 1. Final target architecture

```
┌─────────────────────────────────────────────────────────────┐
│ MODULE 3 — COGNITIVE AND GOVERNANCE COMMAND STACK           │
│                                                             │
│ Site-world cognition · visitor intent · planning · doctrine │
│                                                             │
│ Output: governed semantic command                           │
│ { intent, target_id, profiles, world_state_sequence }       │
└──────────────────────────────┬──────────────────────────────┘
                               │ validated async command
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ MODULE 2 — SPATIAL MEMORY, HAL AND ACTUATION                │
│                                                             │
│ Pointer map · SKG · target verification · world state       │
│ HAL · trajectory planner · target lock · safety supervisor  │
│ ping-light end effector · motion telemetry                  │
└──────────────────────────────┬──────────────────────────────┘
                               │ arrival / tool / state events
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ MODULE 1 — SENSORIMOTOR AND COMMUNICATION STACK             │
│                                                             │
│ Listening · STT · Qwen TTS · audio playback · amplitude     │
│ speech telemetry · bounded voice-synchronized expression    │
└─────────────────────────────────────────────────────────────┘
```
The layers communicate asynchronously. None of them should reach into another module and mutate its internal state directly.

For the current browser build, they may initially coexist in the same application bundle while remaining logically isolated. Actual fault isolation can then use:

- `AudioWorklet` for audio processing;
- a Web Worker for planning or telemetry processing;
- the main rendering thread for Framer Motion and DOM-bound actuation;
- backend/local services for cognition and Qwen generation.
Separate physical processors are appropriate later, but forcing every browser module into a separate OS process immediately would add complexity without improving today’s movement repair.

---

# 2. Canonical command contract
The reasoner selects **where and why**. It never selects raw motor, animation, timing, or color values.

```
type MovementIntent =
  | "PRESENT"
  | "LISTEN"
  | "GUIDE"
  | "INSPECT"
  | "AVOID"
  | "TRANSITION"
  | "REST"
  | "SUMMON"
  | "HUMAN_HANDOFF";

type RobotActionType =
  | "NAVIGATE_TO_TARGET"
  | "NAVIGATE_AND_ILLUMINATE"
  | "PRESENT_NEAR_TARGET"
  | "ENTER_REST"
  | "RETURN_TO_PRESENCE"
  | "HOLD_POSITION";

interface OrbRobotCommand {
  commandId: string;
  issuedAt: number;

  worldStateSequence: number;

  actionType: RobotActionType;
  movementIntent: MovementIntent;

  targetId?: string;
  targetZone?: OrbZone;

  velocityProfile: "calm" | "normal" | "urgent";
  arrivalProfile: "soft" | "present" | "focused";
  holdProfile: "steady" | "subtle_float" | "observing";

  speech?: {
    text: string;
    voice: "qwen";
    synchronization: "concurrent" | "after_arrival";
  };

  endEffector?: {
    type: "PING_LIGHT";
    durationProfile: "brief" | "standard" | "extended";
    intensityProfile: "low" | "medium" | "high";
  };
}
```
`OrbZone` should also be closed vocabulary:

```
type OrbZone =
  | "TARGET_ADJACENT"
  | "VIEWPORT_CENTER"
  | "CONTENT_LEFT"
  | "CONTENT_RIGHT"
  | "UPPER_RIGHT_REST"
  | "VISITOR_ACTIVE_REGION";
```
The LLM must never output:

```
pixel coordinates
velocity floats
thrust values
easing curves
hex colors
brightness percentages
raw pulse durations
direct DOM selectors
motor voltage
laser power
```
The HAL and actuator translate the profiles into deterministic values.

---

# 3. Module 1 — Sensorimotor and communication

## Responsibilities
Module 1 owns:

- microphone permission;
- listening state;
- STT;
- Qwen TTS requests;
- audio buffering and playback;
- interruption and cancellation;
- speech start/end telemetry;
- bounded amplitude data for visual expression;
- warm-state latency behavior.
It does not decide where Weaver moves.

## Required interfaces

```
interface SpeechCommand {
  commandId: string;
  text: string;
  voice: "qwen";
  priority: "normal" | "handoff" | "urgent";
}

interface VoiceTelemetry {
  commandId: string;
  event:
    | "LISTENING_STARTED"
    | "UTTERANCE_DETECTED"
    | "SPEECH_GENERATING"
    | "SPEECH_STARTED"
    | "SPEECH_ENDED"
    | "SPEECH_CANCELLED"
    | "VOICE_ERROR";
  timestamp: number;
}
```
Amplitude may control only bounded expression:

```
small shell pulse
subtle glow response
minor vertical buoyancy
tiny rotation
mouth/light activity
```
It must not alter the destination, path, collision limits, or movement velocity.

---

# 4. Module 2 — Spatial memory, HAL and actuation
This is the most important implementation module for the current work.

## 4.1 Load the map before autonomous action
At boot, Module 2 loads:

```
Pointer Plot Map
current route map
site spatial SKG
fixed interface chrome
owner-defined exclusions
movement doctrine
world-state sequence
```
The live site currently reports:

```
1,090 pointer records
39 mapped routes
0 duplicate target IDs
```
That is already enough semantic geography for the first navigation computer.

## 4.2 Resolve targets through the existing verification chain
The HAL must not blindly run `document.querySelector()` and trust the result.

The existing resolver defines this order:

1. semantic locator;
2. content fingerprint;
3. accessibility role and name;
4. localized visual verification.
Below the confidence floor, Weaver must remain voice-only.

The current first tier works through `querySelector`, but fingerprint, accessibility, and visual verification are still integration placeholders.

## 4.3 Web HAL
After resolution returns a verified `Element`, the web HAL converts it into temporary spatial telemetry:

```
interface SpatialGoal {
  normalizedX: number;
  normalizedY: number;
  normalizedZ: number;
  strategy:
    | "element_center"
    | "present_beside"
    | "approach_edge"
    | "observe_from_distance";
}
```
Normalized coordinates are **ephemeral runtime values**. They do not replace semantic locators or target IDs in the map.

## 4.4 World-state sequencing
Every map or page-state replacement increments:

```
worldStateSequence
```
Every command carries the sequence it was planned against.

Before moving:

```
if (command.worldStateSequence !== currentWorldStateSequence) {
  cancelCommand("STALE_WORLD_STATE");
  reResolveTarget();
}
```
This protects against:

- navigation;
- DOM replacement;
- CMS edits;
- responsive reflow;
- opened accordions;
- collapsed menus;
- new crawl output;
- layout changes while the reasoner is deciding.

## 4.5 Target-lock engine
A verified element must remain tracked during the movement and ping.

The target-lock layer responds to:

```
scroll
resize
layout shift
sticky headers
menu expansion
route changes
element removal
responsive breakpoint changes
```
If the element disappears or verification confidence drops, the runtime cancels cleanly and reports `TARGET_LOST`. It must not keep moving toward stale coordinates.

## 4.6 Deterministic trajectory planner
The planner owns:

```
velocity
acceleration
deceleration
curvature
arrival offset
collision avoidance
sidebar avoidance
viewport boundaries
active-control avoidance
reversal limits
rest placement
motion cancellation
```
The LLM may request `urgent`, but the planner decides the maximum safe interpretation of urgent.

## 4.7 Safety supervisor
Hard rules cannot be overridden by cognition:

```
remain visible
remain clickable and tappable
never hide behind the sidebar
never block the active control
never rest in the bottom-right
remain inside viewport bounds
cancel on stale world state
cancel on target loss
confirm before sensitive navigation or actions
```
The current pointer runtime already requires confirmation for cross-page or confirmation-marked actions.

## 4.8 Ping-light end effector
The PNG pointer and bloom become a tool adapter:

```
interface EndEffectorAdapter {
  activate(
    element: Element,
    durationProfile: "brief" | "standard" | "extended",
    intensityProfile: "low" | "medium" | "high"
  ): Promise<void>;

  deactivate(): void;
}
```
The LLM knows only `PING_LIGHT`. It does not know whether the implementation is PNG, CSS, canvas, projection, LED, or another future device.

The existing runtime already preserves the doctrinal sequence:

```
confidence
→ resolution
→ localized recovery
→ travel
→ bloom
→ ploop
```
That sequence should remain intact while the hooks are connected to the new HAL and actuator.

## 4.9 Telemetry ledger
Module 2 reports:

```
type RobotTelemetryEvent =
  | "COMMAND_ACCEPTED"
  | "TARGET_RESOLVING"
  | "TARGET_VERIFIED"
  | "TARGET_LOST"
  | "MOTION_STARTED"
  | "MOTION_PROGRESS"
  | "ARRIVAL_CONFIRMED"
  | "END_EFFECTOR_ACTIVE"
  | "END_EFFECTOR_COMPLETE"
  | "COMMAND_COMPLETE"
  | "COMMAND_CANCELLED"
  | "SAFETY_BLOCKED";
```
Telemetry may produce:

- candidate corrections;
- failure history;
- route-friction evidence;
- performance analytics;
- owner-facing recommendations.
It must not silently rewrite the authoritative map from one visitor session. Runtime recovery already records candidate evidence rather than directly rewriting the map.

---

# 5. Module 3 — Cognitive and governance command stack

## Responsibilities
Module 3 owns:

- full compiled Site World;
- visitor intent;
- conversational reasoning;
- target selection;
- movement intent;
- explanation and speech drafting;
- escalation classification;
- governance validation;
- command dispatch.
It has no direct access to Framer Motion, DOM mutation, motors, illumination hardware, or audio buffers.

## Governance firewall
The sample firewall should not validate raw `thrust_intensity`, because raw thrust should never exist in the LLM command.

It should validate:

```
class GovernanceWrapper {
  verifyCommand(
    command: OrbRobotCommand,
    world: CurrentWorldState
  ): GovernanceDecision {
    if (!isSchemaValid(command)) return deny("INVALID_SCHEMA");
    if (!isClosedVocabulary(command)) return deny("UNSAFE_RAW_VALUE");
    if (command.worldStateSequence !== world.sequence) {
      return deny("STALE_WORLD_STATE");
    }

    if (command.targetId && !world.targetIds.has(command.targetId)) {
      return deny("UNKNOWN_TARGET");
    }

    if (!actionAllowedForTarget(command, world)) {
      return deny("ACTION_NOT_ALLOWED");
    }

    if (violatesPrivacyDoctrine(command)) {
      return deny("PRIVACY_BLOCK");
    }

    if (violatesEscalationOwnership(command, world)) {
      return deny("HUMAN_OWNS_ISSUE");
    }

    return allow(command);
  }
}
```
The governance wrapper can downgrade a command:

```
urgent → normal
navigate → point only
navigate and illuminate → illuminate only
```
It can also refuse it completely.

---

# 6. Movement behavior agreed in this thread
These requirements belong in Module 2’s doctrine and state machine.

## Active presence
Weaver should:

- move calmly and purposefully;
- avoid repeated full-screen sweeps;
- avoid rapid reversals and bouncing;
- not behave as though demanding attention;
- use semantic movement decisions rather than random wandering;
- remain fully clickable during all movement.

## Rest mode
After five minutes of genuine visitor inactivity:

```
intent: REST
zone: UPPER_RIGHT_REST
```
Then Weaver:

- moves smoothly to the upper-right;
- dims;
- shows a small “Click me” cue;
- remains loaded and fully warm;
- does not stop voice services;
- does not unload cognition;
- does not introduce restart latency;
- immediately returns when clicked, tapped, or summoned.
The bottom-right remains forbidden as a resting position.

## Sidebar
The sidebar is a hard exclusion zone. The source has already been changed so the left movement boundary is calculated from the live `<aside>` bounding rectangle rather than from an eight-pixel screen edge.

## Active motion timing
The local source has also been changed from:

```
3–5 second travel
120–480 ms pause
```
to:

```
6.5–10.5 second travel
1.8–4.2 second pause
```
Those values should become actuator profile mappings rather than permanent global decision logic.

## Opacity
Normal opacity must be increased. Rest mode has its own lower opacity profile. The exact values belong in the visual actuator, not in the LLM or ontology.

---

# 7. Human escalation requirements
The existing escalation state machine already separates:

```
explicit human request
frustration-only offer
confirmed escalation
human-owned issue
returned case
```
An explicit human request confirms immediately. Frustration alone triggers an offer and requires confirmation. Sensitive information is excluded unless separately approved.

The required UI behavior is:

1. Visitor asks for or demands a human.
2. Current pointer guidance is cancelled cleanly.
3. Weaver moves to horizontal center.
4. The only human-agent chat bubble appears beneath Weaver.
5. The human owns that specific issue.
6. Weaver observes under governed memory rules but does not type into the agent conversation.
7. The agent explicitly hands control back.
8. The chat bubble disappears.
9. Weaver resumes control.
The suppression rule remains scoped to the escalated issue and must never globally mute Weaver.

The shared state already has independent primary, guidance, and escalation tracks, including cancellation of in-flight guidance during escalation.

---

# 8. Build sequence

## Phase 1 — Freeze the shared protocol
Create:

```
orb_robot_protocol.schema.json
movement_intent vocabulary
zone vocabulary
command envelope
telemetry envelope
world-state sequence contract
end-effector profiles
governance result contract
```
This is the first interface boundary to draft.

## Phase 2 — Build Module 2 around the current pointer runtime
Create:

```
frontend/src/orb/robotics/
├── orbRobotProtocol.ts
├── movementOntology.ts
├── webHal.ts
├── safetySupervisor.ts
├── trajectoryPlanner.ts
├── targetLock.ts
├── telemetryBus.ts
├── pingLightTool.ts
└── movementController.ts
```
Connect these through the existing `pointerRuntime.ts` hooks rather than rewriting its doctrinal order.

## Phase 3 — Convert `AutonomousOrb` into an actuator host
`AutonomousOrb.tsx` should stop being the authority that randomly decides destinations.

It should become responsible for:

```
rendering
animation controls
drag/click interaction
visual states
receiving validated movement commands
reporting actuator telemetry
```
Random movement remains only as a tightly governed fallback when no semantic activity exists.

## Phase 4 — Complete pointer resolution integrations
Implement:

```
content fingerprint matching
ARIA role/accessibility-name matching
localized visual verification
stable correction locator generation
off-screen directional cue
target-lock resynchronization
```
These are currently identified integration gaps.

## Phase 5 — Extract Module 1
Move voice responsibilities out of the large ORB component into:

```
voiceCommandBus
qwenTtsAdapter
speechPlaybackController
listeningController
voiceTelemetry
amplitudeExpressionBridge
```

## Phase 6 — Build Module 3 planner and governance
Connect:

```
compiled Site World
visitor intent
Movement SKG
target selection
governance validation
command dispatch
telemetry feedback
```
The reasoner should operate from the full compiled website world, not a small canned prompt pack.

## Phase 7 — Wire human escalation
Complete:

```
real escalation classifier
agent transport adapter
bubble UI
center positioning command
human-owned issue suppression
agent handback event
bubble removal
governed observation storage
```
The current file explicitly leaves classifier, vendor transport, sensitive-data response, and issue matching as integration work.

## Phase 8 — Tests, frontend build, then Docker rebuild
Do not rebuild Docker after each edit.

After all related source changes:

```
TypeScript compile
unit tests
pointer resolution tests
stale-state tests
target-lock tests
rest-mode timing test
sidebar exclusion test
escalation lifecycle test
frontend production build
single Docker rebuild
browser verification
```

---

# 9. Acceptance conditions
The build reaches the intended state when all of these work:

1. The reasoner can choose a valid `target_id` or governed zone.
2. Governance can reject invalid or stale commands.
3. The HAL resolves the semantic target through the full verification chain.
4. Weaver moves without receiving raw coordinates from the LLM.
5. Weaver continuously tracks a moving target during scroll or layout changes.
6. The ping-light remains attached to the verified element.
7. Telemetry confirms arrival and tool completion.
8. A lost target cancels safely instead of producing a false point.
9. Voice continues independently when movement is delayed.
10. Motion continues independently when TTS generation is delayed.
11. Five-minute rest mode works without unloading anything.
12. Weaver never hides behind the sidebar or rests bottom-right.
13. Human escalation opens the sole chat bubble and removes it after handback.
14. The same semantic command contract could later be consumed by a non-browser actuator.

---

# 10. Not included in this build, and why

## Raw LLM kinematics
Not included:

```
thrust
motor values
velocity floats
raw duration
brightness values
hex colors
pixel destinations
```
Reason: continuous actuator values must remain deterministic and safety-bounded.

## Direct LLM access to the DOM
Not included because the reasoner must select semantic targets; the resolver and HAL verify physical reality.

## Automatic authoritative-map rewriting
Not included because a single live session may encounter an A/B test, cookie banner, logged-in variant, or temporary layout. Live corrections remain evidence until scan-side verification.

## Full physical drone controller
Not included because no physical body, localization hardware, propulsion controller, obstacle sensors, emergency stop, or certified safety system is attached. The protocol remains compatible, but physical execution requires a separate actuator implementation.

## Laser end effector
Not included as a default physical implementation. A real laser would require deterministic power limits, interlocks, human detection, directional constraints, and emergency cutoff. The LLM must never directly energize one.

## `spatial_envelope` physics model
Reserved but not necessary for the first Website ORB actuator. The browser version needs verified rectangles, presentation offsets, and collision exclusion. Full body-clearance geometry becomes important with real mass and hardware.

## Runtime OWL reasoning on every animation frame
Not included because parsing and reasoning over OWL inside the motion loop would create unnecessary latency. The `.owl` ontology can remain the canonical semantic model, but it should compile into a small runtime JSON/TypeScript vocabulary for deterministic lookup.

## Autonomous abandoned-cart or sales-path optimization inside movement
Not part of the first motion build because commercial analytics, privacy policy, conversion inference, and owner approval are separate concerns. Module 2 may record telemetry; Module 3 may later reason over approved analytics.

## Vendor-specific human-support integration
Not yet included because the support vendor or local agent transport has not been selected. The adapter contract and bubble lifecycle can be built now without locking the product to one vendor.

## Anti-gravity propulsion or starship construction controls
Not included as implemented capability because those physical systems do not currently exist in this project. The architecture remains propulsion-independent so future bodies can use the same semantic planner and command contract without claiming unavailable hardware today.

---
The build should begin with the **shared robot protocol schema**, followed immediately by the **web HAL, safety supervisor, trajectory planner, target lock, and telemetry bus**. That establishes the robot body boundary first; cognition can then control it without becoming physically entangled with it.  this is the full implimenttaitoin.
