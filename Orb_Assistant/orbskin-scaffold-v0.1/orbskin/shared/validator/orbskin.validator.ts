/**
 * ORB SKIN VALIDATOR — shared pure logic
 * No filesystem. No network. Works in Node, browser, Tauri webview.
 * Loose for scaffolding — tighten rules per conflict resolution.
 */

import type {
  OrbSkinManifest,
  SkinValidationResult,
  ValidationIssue,
  OrbTarget,
} from "../types/orbskin.types.js";

import { ORBSKIN_SCHEMA_VERSION } from "../types/orbskin.types.js";

// ─────────────────────────────────────────────
// MAIN ENTRY
// ─────────────────────────────────────────────

export function validateManifest(
  raw: unknown,
  forTarget: OrbTarget,
  runtimeVersion: string,
  packageHash: string
): SkinValidationResult {
  const errors: ValidationIssue[] = [];
  const warnings: ValidationIssue[] = [];

  // Must be an object
  if (!raw || typeof raw !== "object") {
    return bail("MISSING_MANIFEST", "manifest.json missing or not an object");
  }

  const m = raw as Record<string, unknown>;

  // Schema version
  if (m.schema_version !== ORBSKIN_SCHEMA_VERSION) {
    warnings.push({
      code: "SCHEMA_VERSION_MISMATCH",
      field: "schema_version",
      message: `Expected ${ORBSKIN_SCHEMA_VERSION}, got ${m.schema_version} — may still load`,
    });
  }

  // Required string fields
  for (const f of ["skin_id", "name", "version"]) {
    if (!m[f] || typeof m[f] !== "string") {
      errors.push({ code: "MISSING_FIELD", field: f, message: `"${f}" required` });
    }
  }

  // Creator block
  const creator = m.creator as Record<string, unknown> | undefined;
  if (!creator?.creator_id || !creator?.display_name) {
    errors.push({ code: "MISSING_FIELD", field: "creator", message: "creator.creator_id and creator.display_name required" });
  }

  // Classification + target compatibility
  const cls = m.classification as Record<string, unknown> | undefined;
  if (!cls) {
    errors.push({ code: "MISSING_FIELD", field: "classification", message: '"classification" block required' });
  } else if (Array.isArray(cls.supported_orbs)) {
    const supported = cls.supported_orbs as string[];
    if (!supported.includes(forTarget) && !supported.includes("all")) {
      errors.push({
        code: "UNSUPPORTED_TARGET",
        field: "classification.supported_orbs",
        message: `Skin does not support target "${forTarget}". Supported: ${supported.join(", ")}`,
      });
    }
  }

  // Visuals block
  const vis = m.visuals as Record<string, unknown> | undefined;
  if (!vis) {
    errors.push({ code: "MISSING_FIELD", field: "visuals", message: '"visuals" block required' });
  } else {
    for (const f of ["preview", "body_asset", "docked_icon"]) {
      if (!vis[f] || typeof vis[f] !== "string") {
        errors.push({ code: "MISSING_ASSET", field: `visuals.${f}`, message: `"visuals.${f}" required` });
      }
    }
  }

  // Behavior hard walls — these never change regardless of tier
  const bl = m.behavior_limits as Record<string, unknown> | undefined;
  if (!bl) {
    errors.push({ code: "MISSING_FIELD", field: "behavior_limits", message: '"behavior_limits" block required' });
  } else {
    const hardFalse = ["may_add_permissions", "may_add_tools", "may_add_network_access", "may_add_llm_access"];
    for (const f of hardFalse) {
      if (bl[f] !== false) {
        errors.push({
          code: "BEHAVIOR_VIOLATION",
          field: `behavior_limits.${f}`,
          message: `"${f}" must be false — skins cannot expand ORB authority`,
        });
      }
    }
    if (bl.changes_visuals_only !== true) {
      errors.push({
        code: "BEHAVIOR_VIOLATION",
        field: "behavior_limits.changes_visuals_only",
        message: '"changes_visuals_only" must be true',
      });
    }
  }

  // Rights block
  const rights = m.rights as Record<string, unknown> | undefined;
  if (!rights) {
    errors.push({ code: "MISSING_FIELD", field: "rights", message: '"rights" block required' });
  } else if (rights.expiry_date && typeof rights.expiry_date === "string") {
    const exp = Date.parse(rights.expiry_date);
    if (!isNaN(exp) && exp < Date.now()) {
      errors.push({ code: "LICENSE_EXPIRED", field: "rights.expiry_date", message: `License expired: ${rights.expiry_date}` });
    }
  }

  // Integrity + hash check
  const integ = m.integrity as Record<string, unknown> | undefined;
  if (!integ) {
    errors.push({ code: "MISSING_FIELD", field: "integrity", message: '"integrity" block required' });
  } else {
    if (integ.package_hash && packageHash) {
      const stored = stripPrefix(integ.package_hash as string);
      const actual = stripPrefix(packageHash);
      if (stored !== actual) {
        errors.push({
          code: "HASH_MISMATCH",
          field: "integrity.package_hash",
          message: `Hash mismatch. Stored: ${stored.slice(0, 12)}… Actual: ${actual.slice(0, 12)}…`,
        });
      }
    }
    // Runtime version check — loose, just warn for now
    if (integ.runtime_min_version && typeof integ.runtime_min_version === "string") {
      if (!semverGte(runtimeVersion, integ.runtime_min_version as string)) {
        warnings.push({
          code: "RUNTIME_VERSION_LOW",
          field: "integrity.runtime_min_version",
          message: `Skin prefers runtime >= ${integ.runtime_min_version}, current: ${runtimeVersion}`,
        });
      }
    }
  }

  return {
    valid: errors.length === 0,
    skin_id: (m.skin_id as string) ?? "unknown",
    errors,
    warnings,
    validated_at: new Date().toISOString(),
  };
}

// ─────────────────────────────────────────────
// HELPERS
// ─────────────────────────────────────────────

function bail(code: string, message: string): SkinValidationResult {
  return {
    valid: false,
    skin_id: "unknown",
    errors: [{ code, message }],
    warnings: [],
    validated_at: new Date().toISOString(),
  };
}

function stripPrefix(hash: string): string {
  return hash.startsWith("sha256:") ? hash.slice(7) : hash;
}

function parseSemver(v: string): [number, number, number] {
  const p = v.replace(/^v/, "").split(".").map(Number);
  return [p[0] ?? 0, p[1] ?? 0, p[2] ?? 0];
}

function semverGte(a: string, b: string): boolean {
  const [am, an, ap] = parseSemver(a);
  const [bm, bn, bp] = parseSemver(b);
  if (am !== bm) return am > bm;
  if (an !== bn) return an > bn;
  return ap >= bp;
}
