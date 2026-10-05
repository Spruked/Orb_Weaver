import type { OrbKineticTransit, OrbPoint } from "./kineticTransit";

export type OrbTargetValidationResult =
  | {
      ok: true;
      targetId: string;
      element: HTMLElement;
      rect: DOMRect;
      method?: "data_orb_target" | "scoped_pointer_record" | "raw_pointer_record";
    }
  | {
      ok: false;
      targetId: string;
      reason: "missing" | "hidden" | "detached" | "invalid_target_id" | "identity_mismatch" | "ambiguous" | "policy_blocked";
      fallbackPosition: OrbPoint;
    };

export type OrbTargetValidationOptions = {
  kineticTransit?: OrbKineticTransit;
  fallbackPosition?: OrbPoint;
  logger?: Pick<Console, "warn" | "info">;
};

const DEFAULT_FALLBACK: OrbPoint = { x: 24, y: 24 };

export type OrbPointerRecord = {
  target_id: string;
  semantic_locator: string;
  content_fingerprint: string;
  meaning?: string;
  direct_aliases?: string[];
  intent_aliases?: string[];
  confidence_class?: "VERIFIED" | "STABLE" | "UNCERTAIN" | "BLOCKED";
  runtime_policy?: {
    may_point?: boolean;
    requires_live_verification?: boolean;
    requires_user_confirmation?: boolean;
    reason?: string;
  } & Record<string, unknown>;
  structural_context?: {
    parent_locator?: string | number | boolean | null;
    parent_heading?: string | number | boolean | null;
    tag?: string | number | boolean | null;
  } & Record<string, string | number | boolean | null | undefined>;
};

const cssEscape = (value: string): string => {
  if (typeof CSS !== "undefined" && typeof CSS.escape === "function") {
    return CSS.escape(value);
  }
  return value.replace(/["\\]/g, "\\$&");
};

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

const normalizeText = (value: string): string =>
  (value || "").replace(/\s+/g, " ").trim().toLowerCase();

const visibleText = (element: HTMLElement): string => {
  if (["INPUT", "TEXTAREA", "SELECT"].includes(element.tagName)) {
    return normalizeText(
      [
        element.getAttribute("aria-label") || "",
        element.getAttribute("placeholder") || "",
        element.getAttribute("name") || "",
        element.textContent || "",
      ].join(" "),
    );
  }
  return normalizeText(element.textContent || "");
};

const expectedFragments = (record: OrbPointerRecord): string[] => {
  const aliases = record.direct_aliases || record.intent_aliases || [];
  const fromMeaning = (record.meaning || "").replace(/^[^:]+:\s*/, "");
  return [fromMeaning, ...aliases]
    .map((value) => normalizeText(value).slice(0, 120))
    .filter((value) => value.length >= 2);
};

const elementMatchesRecord = (element: HTMLElement, record: OrbPointerRecord): boolean => {
  const expectedTag = String(record.structural_context?.tag || "").toLowerCase();
  if (expectedTag && element.tagName.toLowerCase() !== expectedTag) {
    return false;
  }

  const currentText = visibleText(element);
  const fragments = expectedFragments(record);
  if (!fragments.length) {
    return true;
  }
  return fragments.some((fragment) => {
    if (currentText === fragment) return true;
    if (currentText.length < 5 || fragment.length < 5) return false;
    return (currentText.includes(fragment) || fragment.includes(currentText))
      && Math.min(currentText.length, fragment.length) / Math.max(currentText.length, fragment.length) >= 0.65;
  });
};

const queryElements = (selector: string): HTMLElement[] => {
  if (!selector) return [];
  try {
    return Array.from(document.querySelectorAll<HTMLElement>(selector));
  } catch {
    return [];
  }
};

type ResolvedPointerElement =
  | { element: HTMLElement; method: "scoped_pointer_record" | "raw_pointer_record" }
  | { ambiguous: true };

const resolvePointerElement = (record: OrbPointerRecord): ResolvedPointerElement | null => {
  const parentLocator = String(record.structural_context?.parent_locator || "").trim();
  const semanticLocator = String(record.semantic_locator || "").trim();
  const scopedSelector = parentLocator ? `${parentLocator} ${semanticLocator}` : semanticLocator;

  const scopedMatches = queryElements(scopedSelector).filter((element) => elementMatchesRecord(element, record));
  if (scopedMatches.length > 1) return { ambiguous: true };
  if (scopedMatches.length === 1) return { element: scopedMatches[0], method: "scoped_pointer_record" };

  if (parentLocator) return null;

  const rawMatches = queryElements(semanticLocator).filter((element) => elementMatchesRecord(element, record));
  if (rawMatches.length > 1) return { ambiguous: true };
  if (rawMatches.length === 1) return { element: rawMatches[0], method: "raw_pointer_record" };

  return null;
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
    const selector = `[data-orb-target="${cssEscape(targetId)}"]`;
    const elements = queryElements(selector);

    if (!elements.length) {
      options.kineticTransit?.haltToSafePosition();
      logger.warn("[orb-target-validation]", { targetId, reason: "missing", fallbackPosition });
      return { ok: false, targetId, reason: "missing", fallbackPosition };
    }

    if (elements.length > 1) {
      options.kineticTransit?.haltToSafePosition();
      logger.warn("[orb-target-validation]", { targetId, reason: "ambiguous", matchCount: elements.length, fallbackPosition });
      return { ok: false, targetId, reason: "ambiguous", fallbackPosition };
    }

    const element = elements[0];

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

    return { ok: true, targetId, element, rect: element.getBoundingClientRect(), method: "data_orb_target" };
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

export function validateOrbPointerTarget(
  record: OrbPointerRecord,
  options: OrbTargetValidationOptions = {},
): OrbTargetValidationResult {
  const targetId = record?.target_id || "";
  const fallbackPosition = options.fallbackPosition ?? DEFAULT_FALLBACK;
  const logger = options.logger ?? console;

  if (!targetId || !record.semantic_locator) {
    options.kineticTransit?.haltToSafePosition();
    logger.warn("[orb-target-validation]", { targetId, reason: "invalid_target_id", fallbackPosition });
    return { ok: false, targetId, reason: "invalid_target_id", fallbackPosition };
  }

  const confidenceAllowsGuidance = record.confidence_class === "VERIFIED" || record.confidence_class === "STABLE";
  if (!confidenceAllowsGuidance || record.runtime_policy?.may_point !== true) {
    options.kineticTransit?.haltToSafePosition();
    logger.warn("[orb-target-validation]", {
      targetId,
      reason: "policy_blocked",
      confidenceClass: record.confidence_class,
      runtimePolicy: record.runtime_policy,
      fallbackPosition,
    });
    return { ok: false, targetId, reason: "policy_blocked", fallbackPosition };
  }

  const resolved = resolvePointerElement(record);
  if (resolved && "ambiguous" in resolved) {
    options.kineticTransit?.haltToSafePosition();
    logger.warn("[orb-target-validation]", {
      targetId,
      reason: "ambiguous",
      semanticLocator: record.semantic_locator,
      parentLocator: record.structural_context?.parent_locator,
      fallbackPosition,
    });
    return { ok: false, targetId, reason: "ambiguous", fallbackPosition };
  }
  if (!resolved) {
    options.kineticTransit?.haltToSafePosition();
    logger.warn("[orb-target-validation]", {
      targetId,
      reason: "identity_mismatch",
      semanticLocator: record.semantic_locator,
      parentLocator: record.structural_context?.parent_locator,
      fallbackPosition,
    });
    return { ok: false, targetId, reason: "identity_mismatch", fallbackPosition };
  }

  if (!document.body.contains(resolved.element)) {
    options.kineticTransit?.haltToSafePosition();
    logger.warn("[orb-target-validation]", { targetId, reason: "detached", fallbackPosition });
    return { ok: false, targetId, reason: "detached", fallbackPosition };
  }

  if (!isVisible(resolved.element)) {
    options.kineticTransit?.haltToSafePosition();
    logger.warn("[orb-target-validation]", { targetId, reason: "hidden", fallbackPosition });
    return { ok: false, targetId, reason: "hidden", fallbackPosition };
  }

  return {
    ok: true,
    targetId,
    element: resolved.element,
    rect: resolved.element.getBoundingClientRect(),
    method: resolved.method,
  };
}
