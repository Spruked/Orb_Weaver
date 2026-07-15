import type {
  RobotCommand,
} from "./robotMovement.types";
import {
  PING_DURATION_MS, PING_INTENSITY_ALPHA,
} from "./robotMovement.types";

export interface SpatialGoal {
  normalizedX: number;
  normalizedY: number;
  normalizedZ: number;
  strategy: "element_center" | "present_beside";
}

export type VerifiedTargetElement = HTMLElement;

type VerifiedTargetResult =
  | { ok: true; element: VerifiedTargetElement }
  | { ok: false; reason: "missing" | "detached" | "hidden" | "identity_mismatch" };

const isVisible = (element: HTMLElement): boolean => {
  const rect = element.getBoundingClientRect();
  const style = window.getComputedStyle(element);
  return (
    document.body.contains(element) &&
    rect.width > 0 &&
    rect.height > 0 &&
    style.display !== "none" &&
    style.visibility !== "hidden" &&
    Number(style.opacity || "1") > 0
  );
};

export function requireVerifiedTargetElement(
  element: HTMLElement | null | undefined,
  expectedTargetId?: string,
): VerifiedTargetResult {
  if (!element) {
    return { ok: false, reason: "missing" };
  }
  if (!document.body.contains(element) || !element.isConnected) {
    return { ok: false, reason: "detached" };
  }
  if (!isVisible(element)) {
    return { ok: false, reason: "hidden" };
  }
  if (expectedTargetId) {
    const boundTargetId = element.getAttribute("data-orb-target");
    if (boundTargetId && boundTargetId !== expectedTargetId) {
      return { ok: false, reason: "identity_mismatch" };
    }
  }
  return { ok: true, element };
}

export function calculateSpatialVector(element: VerifiedTargetElement): SpatialGoal {
  const rect = element.getBoundingClientRect();
  return {
    normalizedX: (rect.left + rect.width / 2) / window.innerWidth,
    normalizedY: (rect.top + rect.height / 2) / window.innerHeight,
    normalizedZ: 0,
    strategy: "element_center",
  };
}

// --- Continuous target-lock (the real gap the last drafts caught) -----
// Keeps tracking the verified element for the life of an active command,
// not just once at departure. Cancels itself if the element leaves the DOM.

export function startTargetLock(
  element: VerifiedTargetElement,
  onUpdate: (goal: SpatialGoal) => void,
  onLost: () => void,
): () => void {
  let active = true;
  let frameId = 0;

  const update = () => {
    if (!active) return;
    if (!element.isConnected || !document.body.contains(element) || !isVisible(element)) {
      onLost();
      return;
    }
    onUpdate(calculateSpatialVector(element));
    frameId = requestAnimationFrame(update);
  };

  frameId = requestAnimationFrame(update);
  return () => {
    active = false;
    cancelAnimationFrame(frameId);
  };
}

// --- Command validation -------------------------------------------------
// Defensive runtime check — TS types don't survive a network hop from an
// LLM call, so re-validate the enums actually landed in the allowed set.

const VALID_URGENCY = new Set(["calm", "normal", "immediate"]);
const VALID_DURATION = new Set(["brief", "standard", "extended"]);
const VALID_INTENSITY = new Set(["low", "medium", "high"]);

export function validateCommand(
  command: RobotCommand,
  currentWorldStateSequence: number,
): { ok: true } | { ok: false; reason: string } {
  if (command.worldStateSequence !== currentWorldStateSequence) {
    return { ok: false, reason: "stale_world_state" };
  }
  if (!VALID_URGENCY.has(command.urgency)) {
    return { ok: false, reason: "invalid_urgency" };
  }
  if (command.endEffector) {
    if (!VALID_DURATION.has(command.endEffector.duration)) {
      return { ok: false, reason: "invalid_duration" };
    }
    if (!VALID_INTENSITY.has(command.endEffector.intensity)) {
      return { ok: false, reason: "invalid_intensity" };
    }
  }
  return { ok: true };
}

// --- End-effector deployment (ping) -------------------------------------
// position: fixed matches getBoundingClientRect() viewport coordinates.
// Asset is a bundled import path, not a broken external URL.

export function deployEndEffector(
  element: VerifiedTargetElement,
  duration: import("./robotMovement.types").PingDuration,
  intensity: import("./robotMovement.types").PingIntensity,
): void {
  const goal = calculateSpatialVector(element);
  let container = document.getElementById("orb-active-ping");
  if (!container) {
    container = document.createElement("div");
    container.id = "orb-active-ping";
    container.className = "orb-target-ping";

    const img = document.createElement("img");
    img.src = "/orb-assets/pointer-light.png"; // bundled asset, not a bare URL
    img.className = "orb-pointer-image";
    container.appendChild(img);
    document.body.appendChild(container);
  }

  container.style.setProperty("--ping-alpha", String(PING_INTENSITY_ALPHA[intensity]));
  container.style.left = `${goal.normalizedX * window.innerWidth}px`;
  container.style.top = `${goal.normalizedY * window.innerHeight}px`;

  window.setTimeout(() => {
    container?.parentNode?.removeChild(container);
  }, PING_DURATION_MS[duration]);
}

export function deactivateEndEffector(): void {
  const existing = document.getElementById("orb-active-ping");
  if (existing?.parentNode) {
    existing.parentNode.removeChild(existing);
  }
}
