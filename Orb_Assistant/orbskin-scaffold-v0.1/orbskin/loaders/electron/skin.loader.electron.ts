/**
 * ORB SKIN LOADER — ELECTRON (main process)
 * Runs in: Node.js main process only. Never import this in the renderer.
 *
 * Flow:
 *   1. Receive .orbskin path (from file dialog or auto-assign)
 *   2. Unzip package
 *   3. Parse manifest.json
 *   4. Validate
 *   5. Convert assets to blob: URLs (or serve via protocol handler)
 *   6. Send SkinAssetBundle to renderer via ipcMain
 *
 * Wiring: In your main.ts, register ipcMain.handle("skin:load", ...)
 * and call loadOrbSkin() from there.
 */

// Electron + Node built-ins only — no bundler tricks
import { ipcMain, BrowserWindow, protocol } from "electron";
import * as fs from "fs";
import * as path from "path";
import * as crypto from "crypto";

// JSZip — add to package.json: "jszip": "^3.10.1"
// TODO: npm install jszip
import JSZip from "jszip";

import { validateManifest } from "../../shared/validator/orbskin.validator.js";
import type {
  OrbSkinManifest,
  SkinAssetBundle,
  SkinValidationResult,
} from "../../shared/types/orbskin.types.js";

// ─────────────────────────────────────────────
// CONFIG
// ─────────────────────────────────────────────

const ORB_RUNTIME_VERSION = "1.0.0"; // TODO: pull from app version
const SKIN_CACHE_DIR = path.join(
  process.env.APPDATA ?? process.env.HOME ?? ".",
  "ProPrimeSeries",
  "ORB",
  "skins"
);

// ─────────────────────────────────────────────
// STATE
// ─────────────────────────────────────────────

let activeSkinBundle: SkinAssetBundle | null = null;
let rollbackSkinBundle: SkinAssetBundle | null = null;
let activeSkinPath: string | null = null;
let rollbackSkinPath: string | null = null;

// ─────────────────────────────────────────────
// REGISTER IPC HANDLERS
// Call this once in your main.ts: registerSkinIpc()
// ─────────────────────────────────────────────

export function registerSkinIpc(win: BrowserWindow): void {
  // Load a skin from a file path
  ipcMain.handle("skin:load", async (_event, skinFilePath: string) => {
    return loadOrbSkin(skinFilePath, win);
  });

  // Rollback to previous skin
  ipcMain.handle("skin:rollback", async () => {
    return rollbackSkin(win);
  });

  // Get current active skin info
  ipcMain.handle("skin:getActive", async () => {
    return activeSkinBundle
      ? { skin_id: activeSkinBundle.skin_id, name: activeSkinBundle.name }
      : null;
  });

  // Clear skin (return to ORB default)
  ipcMain.handle("skin:clear", async () => {
    activeSkinBundle = null;
    win.webContents.send("skin:cleared");
    return { ok: true };
  });
}

// ─────────────────────────────────────────────
// LOAD
// ─────────────────────────────────────────────

export async function loadOrbSkin(
  skinFilePath: string,
  win: BrowserWindow
): Promise<{ ok: boolean; error?: string; validation?: SkinValidationResult }> {
  try {
    // 1. Read the .orbskin file
    if (!fs.existsSync(skinFilePath)) {
      return { ok: false, error: `File not found: ${skinFilePath}` };
    }
    const rawBytes = fs.readFileSync(skinFilePath);

    // 2. Compute hash of the package bytes
    const packageHash = "sha256:" + crypto
      .createHash("sha256")
      .update(rawBytes)
      .digest("hex");

    // 3. Unzip
    const zip = await JSZip.loadAsync(rawBytes);

    // 4. Parse manifest
    const manifestFile = zip.file("manifest.json");
    if (!manifestFile) {
      return { ok: false, error: "manifest.json not found in package" };
    }
    const manifestText = await manifestFile.async("string");
    const manifest = JSON.parse(manifestText) as OrbSkinManifest;

    // 5. Validate
    const validation = validateManifest(manifest, "desktop", ORB_RUNTIME_VERSION, packageHash);
    if (!validation.valid) {
      return { ok: false, error: "Validation failed", validation };
    }

    // 6. Extract assets to cache dir
    const skinCacheDir = path.join(SKIN_CACHE_DIR, manifest.skin_id);
    fs.mkdirSync(skinCacheDir, { recursive: true });

    const extractedPaths: Record<string, string> = {};
    for (const [filename, file] of Object.entries(zip.files)) {
      if (file.dir || filename === "manifest.json") continue;
      const destPath = path.join(skinCacheDir, filename);
      fs.mkdirSync(path.dirname(destPath), { recursive: true });
      const content = await file.async("nodebuffer");
      fs.writeFileSync(destPath, content);
      extractedPaths[filename] = destPath;
    }

    // 7. Build asset bundle with file:// URLs
    //    In production, use a registered custom protocol instead of file:// for security
    const toUrl = (filename: string): string => {
      const p = extractedPaths[filename];
      return p ? `file://${p.replace(/\\/g, "/")}` : "";
    };

    const animations: Record<string, string> = {};
    for (const anim of manifest.visuals.animations ?? []) {
      animations[anim] = toUrl(`animations/${anim}`);
    }

    const sounds: Record<string, string> = {};
    for (const snd of manifest.visuals.sounds ?? []) {
      sounds[snd] = toUrl(`sounds/${snd}`);
    }

    const bundle: SkinAssetBundle = {
      skin_id: manifest.skin_id,
      name: manifest.name,
      manifest,
      urls: {
        preview: toUrl(manifest.visuals.preview),
        body_asset: toUrl(manifest.visuals.body_asset),
        docked_icon: toUrl(manifest.visuals.docked_icon),
        animations,
        particle_profile: manifest.visuals.particle_profile
          ? toUrl(manifest.visuals.particle_profile)
          : undefined,
        sounds,
      },
      theme_tokens: manifest.visuals.theme_tokens ?? {},
      loaded_at: new Date().toISOString(),
    };

    // 8. Store rollback
    rollbackSkinBundle = activeSkinBundle;
    rollbackSkinPath = activeSkinPath;
    activeSkinBundle = bundle;
    activeSkinPath = skinFilePath;

    // 9. Push bundle to renderer
    win.webContents.send("skin:applied", bundle);

    return { ok: true, validation };
  } catch (err) {
    return { ok: false, error: String(err) };
  }
}

// ─────────────────────────────────────────────
// ROLLBACK
// ─────────────────────────────────────────────

async function rollbackSkin(
  win: BrowserWindow
): Promise<{ ok: boolean; error?: string }> {
  if (!rollbackSkinBundle) {
    return { ok: false, error: "No rollback skin available" };
  }
  const prev = activeSkinBundle;
  activeSkinBundle = rollbackSkinBundle;
  activeSkinPath = rollbackSkinPath;
  rollbackSkinBundle = prev;

  win.webContents.send("skin:applied", activeSkinBundle);
  return { ok: true };
}
