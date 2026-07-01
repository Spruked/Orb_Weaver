/**
 * ORB SKIN TYPES — shared across all targets
 * Kept loose for scaffolding. Tighten per conflict resolution.
 */

export const ORBSKIN_SCHEMA_VERSION = "1.0";
export const ORBSKIN_EXTENSION = ".orbskin";

// -- Target types --
export type OrbTarget = "website" | "desktop" | "browser" | "all";

// -- Tier / edition --
export type SkinTier = "basic" | "premium" | "collectible" | "branded";
export type EditionType = "unlimited" | "limited" | "one_of_one";
export type LicenseType = "personal" | "commercial" | "enterprise";
export type PriceType = "fixed" | "market" | "auction";

// -- Activation state --
export type SkinStatus =
  | "idle"
  | "validating"
  | "active"
  | "invalid"
  | "rolled_back";

// ─────────────────────────────────────────────
// MANIFEST  (lives inside every .orbskin zip)
// ─────────────────────────────────────────────

export interface OrbSkinManifest {
  schema_version: string;
  skin_id: string;
  name: string;
  version: string;
  description?: string;
  creator: {
    creator_id: string;
    display_name: string;
    verified?: boolean;
  };
  classification: {
    tier: SkinTier;
    edition_type: EditionType;
    supported_orbs: OrbTarget[];
    commercial_use: boolean;
  };
  visuals: {
    preview: string;         // preview.png
    body_asset: string;      // body.png or body.glb
    docked_icon: string;     // docked-icon.svg
    animations: string[];    // filenames inside animations/
    particle_profile?: string;
    sounds?: string[];
    theme_tokens?: Record<string, string>; // loose for now
  };
  behavior_limits: {
    changes_visuals_only: boolean;
    may_change_voice_style: boolean;
    may_change_personality_language: boolean;
    may_add_permissions: boolean;
    may_add_tools: boolean;
    may_add_network_access: boolean;
    may_add_llm_access: boolean;
  };
  marketplace?: {
    price_type: PriceType;
    base_price_usd: number;
    marketplace_fee_percent: number;
    creator_royalty_percent: number;
  };
  rights: {
    license_type: LicenseType;
    transferable: boolean;
    resellable: boolean;
    max_active_orbs: number;
    expiry_date?: string; // ISO8601, null = perpetual
  };
  collectible?: {
    minted: boolean;
    chain?: string;
    contract_address?: string;
    token_id?: string;
    provenance_record_id?: string;
    edition_number?: number;
    edition_total?: number;
  };
  integrity: {
    package_hash: string;      // sha256:<hex>
    manifest_hash: string;     // sha256:<hex>
    publisher_signature: string;
    signed_at: string;
    runtime_min_version: string;
    runtime_max_version?: string;
  };
}

// ─────────────────────────────────────────────
// ASSET BUNDLE  (what loaders produce for React)
// ─────────────────────────────────────────────

/**
 * All three loaders (Electron, Tauri, Web) resolve to this.
 * Assets are URLs — could be:
 *   - blob: URLs        (Electron/Web, from unpacked bytes)
 *   - asset:// URLs     (Tauri custom protocol)
 *   - http://localhost  (FastAPI dev / Web ORB)
 * React renderer doesn't care which.
 */
export interface SkinAssetBundle {
  skin_id: string;
  name: string;
  manifest: OrbSkinManifest;
  urls: {
    preview: string;
    body_asset: string;
    docked_icon: string;
    animations: Record<string, string>; // key = filename, value = URL
    particle_profile?: string;
    sounds?: Record<string, string>;
  };
  theme_tokens: Record<string, string>;
  loaded_at: string;
}

// ─────────────────────────────────────────────
// VALIDATION RESULT
// ─────────────────────────────────────────────

export interface SkinValidationResult {
  valid: boolean;
  skin_id: string;
  errors: ValidationIssue[];
  warnings: ValidationIssue[];
  validated_at: string;
}

export interface ValidationIssue {
  code: string;
  field?: string;
  message: string;
}

// ─────────────────────────────────────────────
// ACTIVE STATE  (runtime carries this)
// ─────────────────────────────────────────────

export interface ActiveSkinState {
  status: SkinStatus;
  current: SkinAssetBundle | null;
  rollback: SkinAssetBundle | null;
  last_changed: string;
}
