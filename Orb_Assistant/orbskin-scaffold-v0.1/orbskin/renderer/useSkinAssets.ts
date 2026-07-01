/**
 * SKIN ASSET BUNDLE — React side
 * Holds the resolved asset URLs and theme tokens.
 * Populated by whichever loader (Electron IPC, Tauri invoke, FastAPI fetch) is active.
 * React renderer reads from this — it never knows which loader ran.
 */

import { createContext, useContext, useState, useCallback, ReactNode } from "react";
import type { SkinAssetBundle, ActiveSkinState } from "../../shared/types/orbskin.types.js";

// ─────────────────────────────────────────────
// CONTEXT
// ─────────────────────────────────────────────

interface SkinContextValue {
  state: ActiveSkinState;
  applyBundle: (bundle: SkinAssetBundle) => void;
  rollback: () => void;
  clear: () => void;
}

const defaultState: ActiveSkinState = {
  status: "idle",
  current: null,
  rollback: null,
  last_changed: new Date().toISOString(),
};

const SkinContext = createContext<SkinContextValue | null>(null);

// ─────────────────────────────────────────────
// PROVIDER
// ─────────────────────────────────────────────

export function SkinProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<ActiveSkinState>(defaultState);

  const applyBundle = useCallback((bundle: SkinAssetBundle) => {
    setState((prev) => ({
      status: "active",
      current: bundle,
      rollback: prev.current ?? null,
      last_changed: new Date().toISOString(),
    }));
  }, []);

  const rollback = useCallback(() => {
    setState((prev) => {
      if (!prev.rollback) return prev;
      return {
        status: "rolled_back",
        current: prev.rollback,
        rollback: null,
        last_changed: new Date().toISOString(),
      };
    });
  }, []);

  const clear = useCallback(() => {
    setState({ ...defaultState, last_changed: new Date().toISOString() });
  }, []);

  return (
    <SkinContext.Provider value={{ state, applyBundle, rollback, clear }}>
      {children}
    </SkinContext.Provider>
  );
}

// ─────────────────────────────────────────────
// HOOK
// ─────────────────────────────────────────────

export function useSkin(): SkinContextValue {
  const ctx = useContext(SkinContext);
  if (!ctx) throw new Error("useSkin must be used inside <SkinProvider>");
  return ctx;
}

export function useSkinAssets(): SkinAssetBundle | null {
  return useSkin().state.current;
}

export function useSkinTokens(): Record<string, string> {
  return useSkin().state.current?.theme_tokens ?? {};
}
