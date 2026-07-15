import { validateOrbPointerTarget, type OrbPointerRecord } from "../targetValidation";
import type { RobotCommand, RobotTelemetry, RobotTelemetryEvent } from "./robotMovement.types";
import {
  calculateSpatialVector,
  deactivateEndEffector,
  deployEndEffector,
  requireVerifiedTargetElement,
  startTargetLock,
  validateCommand,
  type SpatialGoal,
} from "./webActuator.hal";
import "./webActuator.hal.css";

const VALID_ACTION_TYPES = new Set([
  "NAVIGATE_TO_TARGET",
  "NAVIGATE_AND_ILLUMINATE",
  "PRESENT_NEAR_TARGET",
  "ENTER_REST",
  "RETURN_TO_PRESENCE",
]);

const VALID_INTENTS = new Set([
  "Present",
  "Listen",
  "Guide",
  "Inspect",
  "Avoid",
  "Transition",
  "Rest",
  "Summon",
]);

const VALID_APPROACH_BEHAVIORS = new Set([
  "decelerate_on_arrive",
  "hold_steady",
  "circle_and_present",
]);

type TelemetrySink = (event: RobotTelemetry) => void;

type BeginMovementInput = {
  command: RobotCommand;
  pointerRecord: OrbPointerRecord;
  currentWorldStateSequence: number;
  onTelemetry?: TelemetrySink;
};

type BeginMovementFailure = {
  ok: false;
  reason: string;
};

type BeginMovementSuccess = {
  ok: true;
  targetElement: HTMLElement;
  targetRect: DOMRect;
  normalizedGoal: SpatialGoal;
  refreshTarget: () => DOMRect | null;
  getLatestGoal: () => SpatialGoal;
  complete: () => void;
  cancel: (reason?: string) => void;
};

type BeginMovementResult = BeginMovementFailure | BeginMovementSuccess;

type ActiveMovement = {
  command: RobotCommand;
  targetElement: HTMLElement;
  targetRect: DOMRect;
  latestGoal: SpatialGoal;
  lockStopper: () => void;
  telemetrySink?: TelemetrySink;
};

export class OrbRoboticsMovementController {
  private activeMovement: ActiveMovement | null = null;

  private emit(
    command: RobotCommand,
    event: RobotTelemetryEvent,
    telemetrySink?: TelemetrySink,
    reason?: string,
  ): void {
    const payload: RobotTelemetry = {
      commandId: command.commandId,
      event,
      targetId: command.targetId,
      timestamp: Date.now(),
      reason,
    };
    telemetrySink?.(payload);
  }

  private closedVocabularyReason(command: RobotCommand): string | null {
    if (!VALID_ACTION_TYPES.has(command.actionType)) return "invalid_action_type";
    if (!VALID_INTENTS.has(command.intent)) return "invalid_intent";
    if (!VALID_APPROACH_BEHAVIORS.has(command.approachBehavior)) return "invalid_approach_behavior";
    return null;
  }

  private clearActiveMovement(): void {
    if (!this.activeMovement) return;
    this.activeMovement.lockStopper();
    this.activeMovement = null;
    deactivateEndEffector();
  }

  beginMovement(input: BeginMovementInput): BeginMovementResult {
    const { command, pointerRecord, currentWorldStateSequence, onTelemetry } = input;

    this.clearActiveMovement();
    this.emit(command, "COMMAND_ACCEPTED", onTelemetry);

    const closedVocabularyError = this.closedVocabularyReason(command);
    if (closedVocabularyError) {
      this.emit(command, "SAFETY_BLOCKED", onTelemetry, closedVocabularyError);
      return { ok: false, reason: closedVocabularyError };
    }

    const commandValidation = validateCommand(command, currentWorldStateSequence);
    if (!commandValidation.ok) {
      this.emit(command, "SAFETY_BLOCKED", onTelemetry, commandValidation.reason);
      return { ok: false, reason: commandValidation.reason };
    }

    this.emit(command, "TARGET_RESOLVING", onTelemetry);
    const targetValidation = validateOrbPointerTarget(pointerRecord, { logger: console });
    if (!targetValidation.ok) {
      this.emit(command, "SAFETY_BLOCKED", onTelemetry, targetValidation.reason);
      return { ok: false, reason: targetValidation.reason };
    }

    const verifiedTarget = requireVerifiedTargetElement(targetValidation.element, command.targetId);
    if (!verifiedTarget.ok) {
      this.emit(command, "TARGET_LOST", onTelemetry, verifiedTarget.reason);
      this.emit(command, "COMMAND_CANCELLED", onTelemetry, verifiedTarget.reason);
      return { ok: false, reason: verifiedTarget.reason };
    }

    this.emit(command, "TARGET_VERIFIED", onTelemetry);

    let targetElement = verifiedTarget.element;
    let targetRect = targetValidation.rect;
    let latestGoal = calculateSpatialVector(targetElement);

    const lockStopper = startTargetLock(
      targetElement,
      (nextGoal) => {
        latestGoal = nextGoal;
        this.emit(command, "MOTION_PROGRESS", onTelemetry);
      },
      () => {
        this.emit(command, "TARGET_LOST", onTelemetry, "target_detached_or_hidden");
        this.emit(command, "COMMAND_CANCELLED", onTelemetry, "target_detached_or_hidden");
        this.clearActiveMovement();
      },
    );

    this.activeMovement = {
      command,
      targetElement,
      targetRect,
      latestGoal,
      lockStopper,
      telemetrySink: onTelemetry,
    };

    this.emit(command, "MOTION_STARTED", onTelemetry);

    if (command.endEffector?.type === "PING_LIGHT") {
      this.emit(command, "END_EFFECTOR_ACTIVE", onTelemetry);
      deployEndEffector(targetElement, command.endEffector.duration, command.endEffector.intensity);
      window.setTimeout(() => {
        if (this.activeMovement?.command.commandId === command.commandId) {
          this.emit(command, "END_EFFECTOR_COMPLETE", onTelemetry);
        }
      }, 40);
    }

    const refreshTarget = (): DOMRect | null => {
      const refreshed = validateOrbPointerTarget(pointerRecord, { logger: console });
      if (!refreshed.ok) {
        this.emit(command, "TARGET_LOST", onTelemetry, refreshed.reason);
        return null;
      }
      const verified = requireVerifiedTargetElement(refreshed.element, command.targetId);
      if (!verified.ok) {
        this.emit(command, "TARGET_LOST", onTelemetry, verified.reason);
        return null;
      }

      targetElement = verified.element;
      targetRect = refreshed.rect;
      latestGoal = calculateSpatialVector(targetElement);

      if (this.activeMovement?.command.commandId === command.commandId) {
        this.activeMovement.targetElement = targetElement;
        this.activeMovement.targetRect = targetRect;
        this.activeMovement.latestGoal = latestGoal;
      }

      return targetRect;
    };

    return {
      ok: true,
      targetElement,
      targetRect,
      normalizedGoal: latestGoal,
      refreshTarget,
      getLatestGoal: () => latestGoal,
      complete: () => {
        this.emit(command, "ARRIVAL_CONFIRMED", onTelemetry);
        this.emit(command, "COMMAND_COMPLETE", onTelemetry);
      },
      cancel: (reason?: string) => {
        this.emit(command, "COMMAND_CANCELLED", onTelemetry, reason || "cancelled_by_controller");
        this.clearActiveMovement();
      },
    };
  }

  dispose(): void {
    this.clearActiveMovement();
  }
}
