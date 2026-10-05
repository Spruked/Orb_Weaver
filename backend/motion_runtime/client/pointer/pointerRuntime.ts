/**
 * Canonical pointer escalation runtime orchestration.
 *
 * This package remains authoritative for escalation from ordinary ORB
 * operation into either:
 * 1. pointer escalation (resolution -> recovery -> refusal if unresolved), or
 * 2. human escalation (handled separately in orbEscalation.ts).
 *
 * Pointer Plot remains the authority for what may be pointed to.
 * LiDAR/telemetry accelerate live localization after authority and
 * permissions have already been established.
 *
 * The intended successful point path is now:
 * Pointer Plot authority -> resolution/recovery -> live localization ->
 * Prime ORB safe standoff -> micro-MORB exact point -> verified completion ->
 * micro-MORB dissolves.
 *
 * TODO(integration): wire these hooks to the real ORB cognition, LiDAR,
 * telemetry, Kokoro, and animation systems. Keep the control-flow order.
 */

import { cancelInFlightGuidance, type OrbState } from "./orbState";
import { resolveTarget, CONFIDENCE_FLOOR } from "./pointerResolution";
import type { CandidateCorrection, PlotRecord } from "./pointerPlotTypes";

export interface Hooks {
  /** Match visitor query intent against the Pointer Plot Map. Returns
   *  the best-matching record, or null if nothing plausible exists. */
  matchIntent(query: string, plotMap: PlotRecord[]): Promise<PlotRecord | null>;

  /** Speak a line aloud via Kokoro (or equivalent TTS). */
  speak(line: string): Promise<void>;

  /**
   * Move the Prime ORB toward a safe standoff position near the resolved
   * target. Nearby targets may no-op here while still preserving clearance.
   */
  playPrimeStandoffApproach(element: Element): Promise<void>;

  /**
   * Deploy the micro-MORB to the exact resolved target location. This is the
   * precise point, not the Prime ORB body.
   */
  deployMicroMorb(element: Element): Promise<void>;

  /** Verify the exact point completed successfully before dissolve. */
  verifyPointCompletion(element: Element): Promise<boolean>;

  /** Dissolve the micro-MORB after verified completion or safe abort. */
  dissolveMicroMorb(): Promise<void>;

  /** Play the ploop sound at exact target acquisition. Must respect mute state. */
  playPloop(intensity: "full" | "soft"): void;

  /** Persist a candidate correction (Package B never writes to the
   *  authoritative PlotRecord directly — see promotion.py). */
  saveCandidateCorrection(correction: CandidateCorrection): Promise<void>;

  /** Attempt a targeted, current-page-only recovery scan. Must NOT
   *  crawl other pages or the whole site. */
  attemptLocalizedRecovery(record: PlotRecord): Promise<Element | null>;

  /** Log a resolution/recovery failure event for the promotion/stale-hit
   *  tracking system (see promotion.py's evaluate_stale_hits). */
  logRecoveryFailure(targetId: string): void;
}

const REPING_COOLDOWN_MS = 8000;
let lastPingAt = 0;

export async function handleVisitorQuery(
  query: string,
  plotMap: PlotRecord[],
  state: OrbState,
  hooks: Hooks,
): Promise<OrbState> {
  state = { ...state, primary: "processing", guidance: "none" };

  const record = await hooks.matchIntent(query, plotMap);

  if (!record || record.confidence < CONFIDENCE_FLOOR) {
    // No plausible target, or below the confidence floor — answer
    // verbally only. This branch is intentionally a dead end for
    // pointing: never point at a maybe.
    state = { ...state, primary: "speaking", guidance: "none" };
    return state;
  }

  state = { ...state, guidance: "resolving" };
  let result = await resolveTarget(record);

  if (result.status === "below_confidence") {
    state = { ...state, primary: "speaking", guidance: "none" };
    return state;
  }

  if (result.status === "unresolved") {
    // Map recovery path — Section 4, step 4.
    state = { ...state, guidance: "map_recovering" };
    await hooks.speak("One moment — I'm checking that.");

    const recovered = await hooks.attemptLocalizedRecovery(record);

    if (!recovered) {
      hooks.logRecoveryFailure(record.target_id);
      state = { ...state, primary: "speaking", guidance: "none" };
      return state; // honest voice-only fallback, no point
    }

    // Found via recovery — treat as resolved, and record evidence
    // for eventual promotion. Never write to the authoritative map here.
    await hooks.saveCandidateCorrection({
      target_id: record.target_id,
      new_locator: describeElementForCorrection(recovered),
      evidence: "localized_recovery",
      observed_count: 1,
      first_observed_at: new Date().toISOString(),
      last_observed_at: new Date().toISOString(),
    });

    result = {
      status: "resolved",
      target: { element: recovered, method: "visual_verification", onScreen: true },
    };
  }

  const target = result.target!;

  // Any successful match via a fallback tier (fingerprint, role, or
  // visual) means the stored semantic_locator no longer matches live
  // reality. Record evidence even though resolution succeeded — this
  // is a second entry point into the self-healing loop, distinct from
  // the map_recovering branch above (which only fires on total failure).
  if (result.divergedFromStoredLocator) {
    await hooks.saveCandidateCorrection({
      target_id: record.target_id,
      new_locator: describeElementForCorrection(target.element),
      evidence: `fallback_match:${target.method}`,
      observed_count: 1,
      first_observed_at: new Date().toISOString(),
      last_observed_at: new Date().toISOString(),
    });
  }

  if (!target.onScreen) {
    // Section 4, step 6 — same page, off-screen: verbal + directional
    // edge cue only, no ping, no ploop.
    state = { ...state, primary: "speaking", guidance: "none" };
    // TODO(integration): trigger directional edge-cue animation here.
    return state;
  }

  // Resolved and on-screen — Prime ORB safe standoff, micro-MORB exact point,
  // completion verification, then dissolve.
  state = { ...state, primary: "speaking", guidance: "pointer_traveling" };
  await hooks.playPrimeStandoffApproach(target.element);

  state = { ...state, guidance: "ping_blooming" };
  await hooks.deployMicroMorb(target.element);
  hooks.playPloop("full");
  const completed = await hooks.verifyPointCompletion(target.element);
  await hooks.dissolveMicroMorb();

  if (!completed) {
    hooks.logRecoveryFailure(record.target_id);
    state = { ...state, primary: "speaking", guidance: "none" };
    return state;
  }

  lastPingAt = Date.now();
  state = { ...state, guidance: "re-ping_available" };

  return state;
}

export async function handleRePingRequest(
  record: PlotRecord,
  state: OrbState,
  hooks: Hooks,
): Promise<OrbState> {
  const now = Date.now();
  const withinCooldown = now - lastPingAt < REPING_COOLDOWN_MS;

  const result = await resolveTarget(record);
  if (result.status !== "resolved" || !result.target?.onScreen) {
    return state; // don't re-ping something that's no longer verifiable
  }

  state = { ...state, primary: "presence", guidance: "re-ping_available" };
  await hooks.playPrimeStandoffApproach(result.target.element);
  await hooks.deployMicroMorb(result.target.element);

  if (!withinCooldown) {
    hooks.playPloop("soft");
    lastPingAt = now;
  }
  // within cooldown -> visual-only, no ploop, per doctrine

  const completed = await hooks.verifyPointCompletion(result.target.element);
  await hooks.dissolveMicroMorb();
  if (!completed) {
    return { ...state, guidance: "none" };
  }
  return state;
}

/**
 * Section 7/8 — cross-page navigation and hidden-content targets both
 * require explicit confirmation before any state-changing action.
 */
export function requiresExplicitConfirmation(record: PlotRecord, targetIsOnCurrentPage: boolean): boolean {
  if (!targetIsOnCurrentPage) return true;
  if (record.allowed_actions.includes("point_and_confirm_navigate")) return true;
  return false;
}

function describeElementForCorrection(element: Element): string {
  // TODO(integration): produce a real stable locator string from the
  // live element (e.g. a generated stable selector), not just a tag dump.
  return element.outerHTML.slice(0, 200);
}
