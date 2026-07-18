import { mountOrb } from './orb-mount';
import { DEFAULT_ORB_SKIN } from './skin-registry';
import type { OrbLoaderConfig, OrbMountHandle } from './types';

const bool = (value: unknown) => String(value || '').toLowerCase() === 'true';

export function configFromScript(script: HTMLScriptElement | null = document.currentScript as HTMLScriptElement | null): OrbLoaderConfig {
  const global = window.OrbWeaverConfig || {};
  return {
    siteId: script?.dataset.orbSiteId || global.siteId || '',
    runtime: script?.dataset.orbRuntime || global.runtime || '',
    ws: script?.dataset.orbWs || global.ws,
    version: script?.dataset.orbVersion || global.version || '1',
    debug: bool(script?.dataset.orbDebug ?? global.debug),
    factoryAssetUrl: script?.dataset.orbFactoryAsset || global.factoryAssetUrl || (
      script?.src ? new URL(DEFAULT_ORB_SKIN.bodyAssetUrl, script.src).toString() : undefined
    ),
  };
}

export function bootstrapOrb(config: OrbLoaderConfig): OrbMountHandle {
  if (!config.siteId || !config.runtime) {
    throw new Error('Orb Weaver requires data-orb-site-id and data-orb-runtime');
  }
  return mountOrb(config);
}
