import { bootstrapOrb, configFromScript } from '../orb-client/bootstrap';

const script = document.currentScript as HTMLScriptElement | null;
const config = configFromScript(script);

if (config.debug) {
  console.info('[Orb Weaver] Loader requested', {
    source: script?.src || 'inline-bundle',
    siteId: config.siteId,
  });
}
try {
  bootstrapOrb(config);
} catch (error) {
  console.error('[Orb Weaver] Loader failed', error);
  window.dispatchEvent(new CustomEvent('orbweaver:Runtime failure', {
    detail: { stage: 'loader', message: error instanceof Error ? error.message : String(error) },
  }));
}
