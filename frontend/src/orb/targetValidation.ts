import type { OrbKineticTransit, OrbPoint } from "./kineticTransit";

export type OrbTargetValidationResult =
  | {
      ok: true;
      targetId: string;
      element: HTMLElement;
      rect: DOMRect;
    }
  | {
      ok: false;
      targetId: string;
      reason: "missing" | "hidden" | "detached" | "invalid_target_id";
      fallbackPosition: OrbPoint;
    };

export type OrbTargetValidationOptions = {
  kineticTransit?: OrbKineticTransit;
  fallbackPosition?: OrbPoint;
  logger?: Pick<Console, "warn" | "info">;
};

const DEFAULT_FALLBACK: OrbPoint = { x: 24, y: 24 };

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

export function validateOrbTarget(
  targetId: string,
  options: OrbTargetValidationOptions = {},
): OrbTargetValidationResult {
  const fallbackPosition = options.fallbackPosition ?? DEFAULT_FALLBACK;
  const logger = options.logger ?? console;

  if (!targetId || typeof targetId !== "string") {
    options.kineticTransit?.haltToSafePosition();
    logger.warn("[orb-target-validation]", {
      reason: "invalid_target_id",
      fallbackPosition,
    });
    return { ok: false, targetId: "", reason: "invalid_target_id", fallbackPosition };
  }

  try {
    const selector = `[data-orb-target="${CSS.escape(targetId)}"]`;
    const element = document.querySelector<HTMLElement>(selector);

    if (!element) {
      options.kineticTransit?.haltToSafePosition();
      logger.warn("[orb-target-validation]", { targetId, reason: "missing", fallbackPosition });
      return { ok: false, targetId, reason: "missing", fallbackPosition };
    }

    if (!document.body.contains(element)) {
      options.kineticTransit?.haltToSafePosition();
      logger.warn("[orb-target-validation]", { targetId, reason: "detached", fallbackPosition });
      return { ok: false, targetId, reason: "detached", fallbackPosition };
    }

    if (!isVisible(element)) {
      options.kineticTransit?.haltToSafePosition();
      logger.warn("[orb-target-validation]", { targetId, reason: "hidden", fallbackPosition });
      return { ok: false, targetId, reason: "hidden", fallbackPosition };
    }

    return { ok: true, targetId, element, rect: element.getBoundingClientRect() };
  } catch (error) {
    options.kineticTransit?.haltToSafePosition();
    logger.warn("[orb-target-validation]", {
      targetId,
      reason: error instanceof Error ? error.message : "dom_exception",
      fallbackPosition,
    });
    return { ok: false, targetId, reason: "missing", fallbackPosition };
  }
}
