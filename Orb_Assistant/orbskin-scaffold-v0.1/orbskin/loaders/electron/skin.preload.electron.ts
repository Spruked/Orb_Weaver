/**
 * ORB SKIN — ELECTRON PRELOAD
 * Exposes skin IPC to the React renderer via contextBridge.
 * Add this to your existing preload.ts — do not create a second preload.
 *
 * In renderer, access via: window.orbSkin.load(path)
 */

import { contextBridge, ipcRenderer } from "electron";
import type { SkinAssetBundle, SkinValidationResult } from "../../shared/types/orbskin.types.js";

contextBridge.exposeInMainWorld("orbSkin", {
  /** Load a .orbskin file by path */
  load: (skinFilePath: string): Promise<{ ok: boolean; error?: string; validation?: SkinValidationResult }> =>
    ipcRenderer.invoke("skin:load", skinFilePath),

  /** Rollback to the previous skin */
  rollback: (): Promise<{ ok: boolean; error?: string }> =>
    ipcRenderer.invoke("skin:rollback"),

  /** Get current active skin ID and name */
  getActive: (): Promise<{ skin_id: string; name: string } | null> =>
    ipcRenderer.invoke("skin:getActive"),

  /** Clear active skin — return to ORB default */
  clear: (): Promise<{ ok: true }> =>
    ipcRenderer.invoke("skin:clear"),

  /** Listen for skin applied events (push from main process) */
  onSkinApplied: (cb: (bundle: SkinAssetBundle) => void) => {
    ipcRenderer.on("skin:applied", (_event, bundle) => cb(bundle));
  },

  /** Listen for skin cleared */
  onSkinCleared: (cb: () => void) => {
    ipcRenderer.on("skin:cleared", () => cb());
  },

  /** Remove all skin listeners (call on component unmount) */
  removeAllListeners: () => {
    ipcRenderer.removeAllListeners("skin:applied");
    ipcRenderer.removeAllListeners("skin:cleared");
  },
});

// TypeScript declaration for renderer
declare global {
  interface Window {
    orbSkin: {
      load: (path: string) => Promise<{ ok: boolean; error?: string; validation?: SkinValidationResult }>;
      rollback: () => Promise<{ ok: boolean; error?: string }>;
      getActive: () => Promise<{ skin_id: string; name: string } | null>;
      clear: () => Promise<{ ok: true }>;
      onSkinApplied: (cb: (bundle: SkinAssetBundle) => void) => void;
      onSkinCleared: (cb: () => void) => void;
      removeAllListeners: () => void;
    };
  }
}
