import type { OrbLoaderConfig, OrbSkinSelection } from './types';
import { DEFAULT_ORB_SKIN } from './skin-registry';

export const FACTORY_SKIN: Readonly<OrbSkinSelection> = DEFAULT_ORB_SKIN;

export function factoryAssetUrl(config: OrbLoaderConfig): string {
  if (config.factoryAssetUrl) return new URL(config.factoryAssetUrl, window.location.href).toString();
  const runtimeOrigin = new URL(config.runtime, window.location.href).origin;
  return new URL(FACTORY_SKIN.bodyAssetUrl, runtimeOrigin).toString();
}

export function preloadSkin(url: string): Promise<boolean> {
  return new Promise((resolve) => {
    const image = new Image();
    image.onload = () => resolve(true);
    image.onerror = () => resolve(false);
    image.src = url;
  });
}

export async function prepareSkinAsset(url: string): Promise<{ url: string; dispose: () => void } | null> {
  if (url.startsWith('blob:')) return await preloadSkin(url) ? { url, dispose: () => undefined } : null;
  try {
    const response = await fetch(url, { mode: 'cors', credentials: 'omit', cache: 'force-cache' });
    if (!response.ok) return null;
    const blob = await response.blob();
    if (!blob.type.startsWith('image/')) return null;
    const objectUrl = URL.createObjectURL(blob);
    if (!await preloadSkin(objectUrl)) {
      URL.revokeObjectURL(objectUrl);
      return null;
    }
    return { url: objectUrl, dispose: () => URL.revokeObjectURL(objectUrl) };
  } catch {
    return null;
  }
}

export function approvedSkinAssetUrl(raw: string): string | null {
  try {
    const url = new URL(raw, window.location.href);
    const local = url.hostname === 'localhost' || url.hostname === '127.0.0.1' || url.hostname === '[::1]';
    return url.protocol === 'https:' || url.protocol === 'blob:' || (local && url.protocol === 'http:') ? url.toString() : null;
  } catch {
    return null;
  }
}
