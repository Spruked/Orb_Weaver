export const ORB_MOVEMENT_DOCTRINE_VERSION = "2.0";
export const ORB_MOVEMENT_POLICY_VERSION = "2.0.0";

export type MovementAuthorization = {
  commandId: string;
  movementDoctrineVersion: string;
  movementPolicyVersion: string;
  policyHash: string;
  issuedAt: number;
  expiresAt: number;
  approvedDestination: { x: number; y: number };
  speechConstraintState: "free" | "speech_locked";
  governanceTraceId: string;
};

type MovementPolicyInput = {
  destination: { x: number; y: number };
  current: { x: number; y: number };
  viewport: { width: number; height: number };
  orbSize: number;
  speechActive: boolean;
  dormant: boolean;
  worldStateSequence: number;
  intent: string;
};

type MovementPolicyResult =
  | { ok: true; authorization: MovementAuthorization }
  | { ok: false; reason: string };

const finite = (value: number): boolean => Number.isFinite(value);

export function authorizeMovement(input: MovementPolicyInput): MovementPolicyResult {
  const { destination, viewport, orbSize } = input;
  if (![destination.x, destination.y, input.current.x, input.current.y, orbSize, input.worldStateSequence]
    .every(finite)) return { ok: false, reason: "movement_policy_invalid_geometry" };
  if (input.speechActive) return { ok: false, reason: "movement_policy_speech_locked" };
  if (input.dormant) return { ok: false, reason: "movement_policy_dormant" };
  if (destination.x < 0 || destination.y < 0 || destination.x + orbSize > viewport.width || destination.y + orbSize > viewport.height) {
    return { ok: false, reason: "movement_policy_outside_viewport" };
  }

  const issuedAt = Date.now();
  const commandId = `movement-${issuedAt}-${Math.random().toString(36).slice(2, 8)}`;
  const policyHash = [ORB_MOVEMENT_POLICY_VERSION, input.intent, input.worldStateSequence, destination.x, destination.y].join(":");
  return {
    ok: true,
    authorization: {
      commandId,
      movementDoctrineVersion: ORB_MOVEMENT_DOCTRINE_VERSION,
      movementPolicyVersion: ORB_MOVEMENT_POLICY_VERSION,
      policyHash,
      issuedAt,
      expiresAt: issuedAt + 1500,
      approvedDestination: destination,
      speechConstraintState: "free",
      governanceTraceId: `GT-MOV-${commandId}`,
    },
  };
}

export function assertMovementAuthorization(
  authorization: MovementAuthorization | null | undefined,
): asserts authorization is MovementAuthorization {
  if (!authorization || authorization.expiresAt < Date.now()) {
    throw new Error("movement_policy_authorization_missing_or_expired");
  }
}
