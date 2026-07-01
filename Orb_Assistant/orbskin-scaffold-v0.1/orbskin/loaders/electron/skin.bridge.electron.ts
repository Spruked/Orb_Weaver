/**
 * ORB SKIN — ELECTRON RENDERER BRIDGE
 * Runs in the React renderer process.
 * Listens for skin:applied events from main process and pushes into SkinContext.
 *
 * Usage: Call useElectronSkinBridge() once at your ORB root component.
 */

import { useEffect } from "react";
import { useSkin } from "../../renderer/useSkinAssets.js";
import type { SkinAssetBundle } from "../../shared/types/orbskin.types.js";

export function useElectronSkinBridge(): void {
  const { applyBundle, clear } = useSkin();

  useEffect(() => {
    if (!window.orbSkin) {
      console.warn("[OrbSkin] window.orbSkin not available — is the preload loaded?");
      return;
    }

    window.orbSkin.onSkinApplied((bundle: SkinAssetBundle) => {
      applyBundle(bundle);
    });

    window.orbSkin.onSkinCleared(() => {
      clear();
    });

    return () => {
      window.orbSkin.removeAllListeners();
    };
  }, [applyBundle, clear]);
}
