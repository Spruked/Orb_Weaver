// Closed vocabulary the LLM is allowed to emit. No raw numbers, no colors,
// no durations — those live in the lookup tables below, owned by the HAL.

export type MovementIntent =
  | "Present" | "Listen" | "Guide" | "Inspect"
  | "Avoid" | "Transition" | "Rest" | "Summon"
  | "Ambient" | "Dormant" | "Awaken";

export type Urgency = "calm" | "normal" | "immediate";

export type ApproachBehavior =
  | "decelerate_on_arrive" | "hold_steady" | "circle_and_present";

export type EndEffectorType = "PING_LIGHT" | "NONE";
export type PingDuration = "brief" | "standard" | "extended";
export type PingIntensity = "low" | "medium" | "high";

export interface RobotCommand {
  commandId: string;
  actionType:
    | "NAVIGATE_TO_TARGET" | "NAVIGATE_AND_ILLUMINATE"
    | "PRESENT_NEAR_TARGET" | "ENTER_REST" | "RETURN_TO_PRESENCE";
  targetId?: string;
  intent: MovementIntent;
  urgency: Urgency;
  approachBehavior: ApproachBehavior;
  endEffector?: {
    type: EndEffectorType;
    duration: PingDuration;
    intensity: PingIntensity;
  };
  speech?: { text: string };
  reason: string; // for logging/telemetry only — not authoritative
  worldStateSequence: number; // must match the HAL's currently loaded map
}

export type RobotTelemetryEvent =
  | "COMMAND_ACCEPTED" | "TARGET_RESOLVING" | "TARGET_VERIFIED" | "TARGET_LOST"
  | "MOTION_STARTED" | "MOTION_PROGRESS" | "ARRIVAL_CONFIRMED"
  | "END_EFFECTOR_ACTIVE" | "END_EFFECTOR_COMPLETE" | "COMMAND_COMPLETE"
  | "COMMAND_CANCELLED" | "SAFETY_BLOCKED";

export interface RobotTelemetry {
  commandId: string;
  event: RobotTelemetryEvent;
  targetId?: string;
  timestamp: number;
  reason?: string;
}

// The ONLY place raw physical values exist. The LLM never sees these maps —
// it only ever emits the enum keys above.
export const URGENCY_TO_DURATION_MS: Record<Urgency, number> = {
  calm: 9000,
  normal: 6000,
  immediate: 2200,
};

export const PING_DURATION_MS: Record<PingDuration, number> = {
  brief: 900,
  standard: 1500,
  extended: 2600,
};

export const PING_INTENSITY_ALPHA: Record<PingIntensity, number> = {
  low: 0.25,
  medium: 0.4,
  high: 0.6,
};
