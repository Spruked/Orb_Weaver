/**
 * ORB SKIN — TAURI RENDERER BRIDGE
 * Runs in the React/webview side of Tauri.
 * Calls Rust commands via invoke() and listens for emitted events.
 * Feeds results into SkinContext exactly like the Electron bridge.
 *
 * Usage: call useTauriSkinBridge() once at your ORB root component.
 *
 * Requires: @tauri-apps/api  (npm install @tauri-apps/api)
 */

import { useEffect, useCallback } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";
import { convertFileSrc } from "@tauri-apps/api/core";
import { useSkin } from "../../renderer/useSkinAssets.js";
import type { SkinAssetBundle } from "../../shared/types/orbskin.types.js";

// ─────────────────────────────────────────────
// BRIDGE HOOK
// ─────────────────────────────────────────────

export function useTauriSkinBridge(): void {
  const { applyBundle, clear } = useSkin();

  useEffect(() => {
    const unlisteners: UnlistenFn[] = [];

    // Listen for skin applied from Rust
    listen<RustSkinBundle>("skin:applied", (event) => {
      const bundle = rustBundleToAssetBundle(event.payload);
      applyBundle(bundle);
    }).then((unlisten) => unlisteners.push(unlisten));

    // Listen for skin cleared
    listen("skin:cleared", () => {
      clear();
    }).then((unlisten) => unlisteners.push(unlisten));

    return () => {
      unlisteners.forEach((fn) => fn());
    };
  }, [applyBundle, clear]);
}

// ─────────────────────────────────────────────
// COMMANDS  (call these from UI components)
// ─────────────────────────────────────────────

/** Load a .orbskin file by its filesystem path */
export async function tauriLoadSkin(
  filePath: string
): Promise<{ ok: boolean; error?: string }> {
  try {
    await invoke("load_orb_skin", { path: filePath });
    return { ok: true };
  } catch (err) {
    return { ok: false, error: String(err) };
  }
}

/** Rollback to the previous skin */
export async function tauriRollbackSkin(): Promise<{ ok: boolean; error?: string }> {
  try {
    await invoke("rollback_orb_skin");
    return { ok: true };
  } catch (err) {
    return { ok: false, error: String(err) };
  }
}

/** Clear active skin */
export async function tauriClearSkin(): Promise<{ ok: boolean; error?: string }> {
  try {
    await invoke("clear_orb_skin");
    return { ok: true };
  } catch (err) {
    return { ok: false, error: String(err) };
  }
}

/** Get active skin info without listening to events */
export async function tauriGetActiveSkin(): Promise<{ skin_id: string; name: string } | null> {
  try {
    return await invoke<{ skin_id: string; name: string } | null>("get_active_skin");
  } catch {
    return null;
  }
}

// ─────────────────────────────────────────────
// RUST → TS TYPE BRIDGE
// Rust sends file paths; we convert to asset:// URLs for the renderer
// ─────────────────────────────────────────────

interface RustSkinBundle {
  skin_id: string;
  name: string;
  manifest: unknown;
  urls: {
    preview: string;
    body_asset: string;
    docked_icon: string;
    animations: Record<string, string>;
    particle_profile?: string;
    sounds: Record<string, string>;
  };
  theme_tokens: Record<string, string>;
  loaded_at: string;
}

function rustBundleToAssetBundle(rust: RustSkinBundle): SkinAssetBundle {
  // convertFileSrc turns an absolute path into an asset:// URL
  // that Tauri's webview can load without needing allowlist exceptions
  const toUrl = (path: string): string => convertFileSrc(path);

  const animations: Record<string, string> = {};
  for (const [key, val] of Object.entries(rust.urls.animations)) {
    animations[key] = toUrl(val);
  }

  const sounds: Record<string, string> = {};
  for (const [key, val] of Object.entries(rust.urls.sounds)) {
    sounds[key] = toUrl(val);
  }

  return {
    skin_id: rust.skin_id,
    name: rust.name,
    manifest: rust.manifest as SkinAssetBundle["manifest"],
    urls: {
      preview: toUrl(rust.urls.preview),
      body_asset: toUrl(rust.urls.body_asset),
      docked_icon: toUrl(rust.urls.docked_icon),
      animations,
      particle_profile: rust.urls.particle_profile ? toUrl(rust.urls.particle_profile) : undefined,
      sounds,
    },
    theme_tokens: rust.theme_tokens,
    loaded_at: rust.loaded_at,
  };
}
