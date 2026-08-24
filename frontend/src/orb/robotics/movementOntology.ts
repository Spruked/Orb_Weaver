import type { RobotCommand } from "./robotMovement.types";

// Executable mirror of movement_skg.owl. The OWL file remains the semantic
// source of truth; this narrow policy is the browser-side safety boundary.
export const MOVEMENT_ONTOLOGY_SOURCE = "movement_skg.owl";
export const MOVEMENT_ONTOLOGY_VERSION = "http://spruked.com/orbweaver/movement";

export const MOVEMENT_INTENTS = [
  "Present", "Listen", "Guide", "Inspect", "Avoid", "Transition", "Rest", "Summon",
  "Ambient", "Dormant", "Awaken",
] as const;

export const MOVEMENT_URGENCY = ["calm", "normal", "immediate"] as const;
export const MOVEMENT_APPROACHES = [
  "decelerate_on_arrive", "hold_steady", "circle_and_present",
] as const;

type OntologyCommand = RobotCommand & {
  targetZone?: string;
  targetZoneId?: string;
  targetRoute?: string;
  targetsZone?: string;
};

const has = (values: readonly string[], value: unknown): boolean =>
  typeof value === "string" && values.includes(value);

export function validateMovementOntologyCommand(
  command: RobotCommand,
  currentWorldStateSequence: number,
): { ok: true; ontologySource: string } | { ok: false; reason: string; ontologySource: string } {
  const candidate = command as OntologyCommand;
  const fail = (reason: string) => ({ ok: false as const, reason, ontologySource: MOVEMENT_ONTOLOGY_SOURCE });

  if (!has(MOVEMENT_INTENTS, candidate.intent)) return fail("ontology_invalid_intent");
  if (!has(MOVEMENT_URGENCY, candidate.urgency)) return fail("ontology_invalid_urgency");
  if (!has(MOVEMENT_APPROACHES, candidate.approachBehavior)) return fail("ontology_invalid_approach");
  if (!Number.isInteger(candidate.worldStateSequence)) return fail("ontology_invalid_world_state_sequence");
  if (candidate.worldStateSequence !== currentWorldStateSequence) return fail("stale_world_state");

  const zone = candidate.targetZone || candidate.targetZoneId || candidate.targetsZone;
  if (candidate.intent === "Rest" && zone === "BottomRightRestZone") {
    return fail("ontology_rest_bottom_right_forbidden");
  }
  if (zone === "SidebarOccupiedZone" && candidate.targetZone === "ContentLeft") {
    return fail("ontology_disjoint_zones");
  }

  return { ok: true, ontologySource: MOVEMENT_ONTOLOGY_SOURCE };
}
