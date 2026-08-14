export type OrbConnectionState = 'loading' | 'online' | 'pending' | 'offline';

export interface OrbLoaderConfig {
  siteId: string;
  runtime: string;
  ws?: string;
  version?: string;
  debug?: boolean;
  factoryAssetUrl?: string;
}

export interface OrbSkinSelection {
  skinId: string;
  displayName?: string;
  bodyAssetUrl: string;
  customizationState?: 'FACTORY_DEFAULT' | 'CUSTOM';
}

export interface OrbVisibleControl {
  tag: string;
  role?: string;
  type?: string;
  text?: string;
  name?: string;
  href?: string;
}

export interface OrbSiteSnapshot {
  url: string;
  host: string;
  pathname: string;
  title: string;
  viewport: { width: number; height: number };
  visible_controls: OrbVisibleControl[];
  captured_at: string;
}

export interface OrbPointerRecord {
  target_id: string;
  page_route?: string;
  target_type?: string;
  meaning?: string;
  semantic_locator: string;
  content_fingerprint?: string;
  confidence?: number;
  confidence_class?: 'VERIFIED' | 'STABLE' | 'UNCERTAIN' | 'BLOCKED';
  runtime_policy?: { may_point?: boolean; [key: string]: unknown };
  direct_aliases?: string[];
  intent_aliases?: string[];
  topic_aliases?: string[];
  structural_context?: { tag?: string; parent_locator?: string; [key: string]: unknown };
  finding_class?: 'CONFIRMED' | 'TRANSIENT' | 'DYNAMIC' | 'CONFLICT' | 'UNVERIFIED' | 'PASSED';
  finding_subreason?: string;
  pointer_health?: 'NEW' | 'VERIFIED' | 'RECOVERED' | 'OWNER_VERIFIED' | 'OWNER_REJECTED' | 'DEPRECATED' | 'REMOVED';
}

export interface OrbBootstrapResponse {
  schema: string;
  status: 'ready' | 'awaiting_scan';
  site: { site_id: string; name?: string; domain: string; context_domain?: string; loader_version: string };
  site_world: Record<string, unknown>;
  page_capsule: Record<string, unknown>;
  pointer_map: { record_count: number; records: OrbPointerRecord[]; by_page: Record<string, string[]>; quality?: Record<string, unknown>; recovery?: Record<string, unknown> };
  pointer_guidance?: { status: string; target_guidance_available: boolean; safe_pointer_count: number; blocked_pointer_count: number; map_recovery_required: boolean; automatic_recovery_attempts_maximum: number };
  deployment_preflight?: { passed: boolean; blockers: string[] };
  orb_identity?: {
    skin_id: string;
    display_name: string;
    asset_path: string;
    asset_sha256: string;
    customization_state: 'FACTORY_DEFAULT' | 'CUSTOM';
    owner_consent_required: boolean;
    owner_editable: boolean;
    immutable_default: boolean;
    reversible: boolean;
    fallback_enabled: boolean;
  };
  operating_policy?: ({ version?: number } & Record<string, unknown>) | null;
  capabilities: Record<string, unknown>;
  endpoints: Record<string, string>;
  observed_page?: OrbSiteSnapshot;
}

export interface OrbRuntimeResponse {
  transcript: string;
  spoken_output: string;
  cognitive_pulse?: { pointer_matches?: Array<{ target_id?: string }>; [key: string]: unknown } | null;
  tts_audio_url?: string | null;
}

export interface OrbMountHandle {
  unmount: () => void;
  ask: (text: string) => Promise<void>;
  pointTo: (targetId: string) => boolean;
  setSkin: (skin: OrbSkinSelection) => Promise<boolean>;
  restoreFactory: () => void;
  getStatus: () => { mounted: boolean; online: boolean; route: string; skinId: string; customizationState: 'FACTORY_DEFAULT' | 'CUSTOM' };
}

declare global {
  interface Window {
    OrbWeaverConfig?: Partial<OrbLoaderConfig>;
    OrbWeaver?: OrbMountHandle & { version: string; siteId: string; mount?: () => OrbMountHandle };
    __ORB_WEAVER_LOADER_V1__?: { mounted: boolean; handle: OrbMountHandle };
  }
}
