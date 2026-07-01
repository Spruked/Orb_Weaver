/**
 * ORB SKIN — WEB ORB RENDERER BRIDGE
 * Runs in the React frontend of the website ORB.
 * Fetches the active skin bundle from FastAPI and pushes into SkinContext.
 * Also exposes functions for the UI to load/rollback/clear skins.
 *
 * Usage: call useWebSkinBridge() once at your ORB root component.
 */

import { useEffect, useCallback } from "react";
import { useSkin } from "../../renderer/useSkinAssets.js";
import type { SkinAssetBundle } from "../../shared/types/orbskin.types.js";

// ─────────────────────────────────────────────
// CONFIG
// ─────────────────────────────────────────────

const API_BASE = (import.meta as Record<string, unknown>).env?.VITE_API_URL ?? "http://localhost:8000/api";

// ─────────────────────────────────────────────
// BRIDGE HOOK
// ─────────────────────────────────────────────

/**
 * On mount, fetch the active bundle from FastAPI and push it into SkinContext.
 * The Web ORB doesn't have a push channel by default — it polls or relies on
 * the UI triggering a load. For real-time push, wire up a WebSocket or SSE here.
 */
export function useWebSkinBridge(): {
  loadSkin: (file: File) => Promise<{ ok: boolean; error?: string }>;
  rollback: () => Promise<{ ok: boolean; error?: string }>;
  clearSkin: () => Promise<{ ok: boolean; error?: string }>;
} {
  const { applyBundle, clear } = useSkin();

  // Fetch active skin on mount
  useEffect(() => {
    fetchActiveBundle()
      .then((bundle) => {
        if (bundle) applyBundle(bundle);
      })
      .catch((e) => console.warn("[OrbSkin] Could not fetch active bundle:", e));
  }, [applyBundle]);

  const loadSkin = useCallback(
    async (file: File): Promise<{ ok: boolean; error?: string }> => {
      const result = await webLoadSkin(file);
      if (result.ok && result.bundle) {
        applyBundle(result.bundle);
      }
      return result;
    },
    [applyBundle]
  );

  const rollback = useCallback(async (): Promise<{ ok: boolean; error?: string }> => {
    const result = await webRollbackSkin();
    if (result.ok && result.bundle) {
      applyBundle(result.bundle);
    }
    return result;
  }, [applyBundle]);

  const clearSkin = useCallback(async (): Promise<{ ok: boolean; error?: string }> => {
    const result = await webClearSkin();
    if (result.ok) clear();
    return result;
  }, [clear]);

  return { loadSkin, rollback, clearSkin };
}

// ─────────────────────────────────────────────
// API CALLS
// ─────────────────────────────────────────────

async function fetchActiveBundle(): Promise<SkinAssetBundle | null> {
  const res = await fetch(`${API_BASE}/skin/bundle`);
  if (!res.ok) return null;
  const data = await res.json();
  return data.bundle ?? null;
}

export async function webLoadSkin(
  file: File
): Promise<{ ok: boolean; bundle?: SkinAssetBundle; error?: string }> {
  const form = new FormData();
  form.append("file", file, file.name);

  try {
    const res = await fetch(`${API_BASE}/skin/load`, { method: "POST", body: form });
    const data = await res.json();

    if (!res.ok || !data.ok) {
      return { ok: false, error: data.error ?? `HTTP ${res.status}` };
    }
    return { ok: true, bundle: data.bundle };
  } catch (e) {
    return { ok: false, error: String(e) };
  }
}

export async function webRollbackSkin(): Promise<{ ok: boolean; bundle?: SkinAssetBundle; error?: string }> {
  try {
    const res = await fetch(`${API_BASE}/skin/rollback`, { method: "POST" });
    const data = await res.json();
    if (!res.ok || !data.ok) return { ok: false, error: data.detail ?? `HTTP ${res.status}` };
    return { ok: true, bundle: data.bundle };
  } catch (e) {
    return { ok: false, error: String(e) };
  }
}

export async function webClearSkin(): Promise<{ ok: boolean; error?: string }> {
  try {
    const res = await fetch(`${API_BASE}/skin/clear`, { method: "DELETE" });
    const data = await res.json();
    if (!res.ok || !data.ok) return { ok: false, error: data.detail ?? `HTTP ${res.status}` };
    return { ok: true };
  } catch (e) {
    return { ok: false, error: String(e) };
  }
}
