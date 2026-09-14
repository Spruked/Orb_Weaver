import { webcrypto } from 'crypto';
import { api } from '../services/api';
import { createInitialJourneyState } from '../state/tourControllerStore';
import { createTourAgencyRuntime } from './agencyRuntime';
import { activeAgencyExcursion, clearAgencySessionCache } from './agencySessionCache';

declare const test: (name: string, run: () => void | Promise<void>) => void;
declare const expect: any;
declare const jest: any;
Object.defineProperty(globalThis, 'crypto', { value: webcrypto, configurable: true });

const visibleRect = () => ({ x: 10, y: 10, width: 160, height: 40, top: 10, right: 170, bottom: 50, left: 10, toJSON: () => ({}) } as DOMRect);

const pointer = (targetId: string, route: string, tag: string, meaning: string, mayNavigate = false): any => ({
  target_id: targetId,
  page_route: route,
  target_type: mayNavigate ? 'link' : 'control',
  meaning,
  direct_aliases: [meaning],
  intent_aliases: [meaning],
  content_fingerprint: `${targetId}-fingerprint`,
  semantic_locator: `[data-orb-target="${targetId}"]`,
  confidence: 1,
  confidence_class: 'VERIFIED',
  pointer_health: 'OWNER_VERIFIED',
  structural_context: { tag },
  runtime_policy: { may_point: true, may_navigate: mayNavigate, requires_live_verification: true, requires_user_confirmation: false },
});

test('cross-page demonstration rehydrates short-term context and returns to the governed origin', async () => {
  clearAgencySessionCache();
  window.history.replaceState({}, '', '/');
  document.body.innerHTML = '<main><section id="beat-1">Current site content</section><a data-orb-target="lidar-link" href="/lidar-guidance">LiDAR guidance</a></main>';
  const homeLink = document.querySelector('[data-orb-target="lidar-link"]') as HTMLElement;
  homeLink.getBoundingClientRect = visibleRect;

  let state = createInitialJourneyState();
  const navigations: string[] = [];
  let guideCalls = 0;
  const records = [
    pointer('lidar-link', '/', 'a', 'LiDAR guidance', true),
    pointer('lidar-demo', '/lidar-guidance', 'button', 'Live LiDAR demo'),
  ];
  const cognition = jest.spyOn(api, 'websiteOrbAgency').mockImplementation(async (operation: string, payload: any) => {
    if (operation === 'observe') return { event_id: `evidence-${payload.outcome || payload.source}`, source: payload.source };
    return { result: { selected_candidate_id: window.location.pathname === '/' ? 'move:navigate:lidar-link' : 'move:demonstrate:lidar-demo' }, source: 'test-provider' };
  });
  try {
    const host = {
      read: () => state,
      save: (next: any) => { state = next; },
      pointers: () => records,
      capsule: () => ({ current_url: `https://example.test${window.location.pathname}`, page_summary: 'Verified current page' } as any),
      targetUrl: () => 'https://example.test/',
      worldRevision: () => 1,
      speak: async () => true,
      guide: async () => { guideCalls += 1; return true; },
      navigate: (route: string) => { navigations.push(route); window.history.pushState({}, '', route); },
      telemetry: () => undefined,
    };

    const originRuntime = createTourAgencyRuntime(host);
    expect(await originRuntime.turn(new AbortController().signal)).toBe('awaiting_visitor');
    expect(navigations).toEqual(['/lidar-guidance']);
    expect(state.interaction.activeDestinationRoute).toBe('/lidar-guidance');
    expect(activeAgencyExcursion()?.status).toBe('PENDING_ARRIVAL');

    document.body.innerHTML = '<main><button data-orb-target="lidar-demo">Live LiDAR demo</button></main>';
    const demo = document.querySelector('[data-orb-target="lidar-demo"]') as HTMLElement;
    demo.getBoundingClientRect = visibleRect;

    const destinationRuntime = createTourAgencyRuntime(host);
    expect(await destinationRuntime.turn(new AbortController().signal)).toBe('awaiting_visitor');
    expect(guideCalls).toBe(1);
    expect(navigations).toEqual(['/lidar-guidance', '/']);
    expect(state.interaction.activeDestinationRoute).toBeNull();
    expect(activeAgencyExcursion()).toBeNull();
  } finally {
    cognition.mockRestore();
    clearAgencySessionCache();
    window.history.replaceState({}, '', '/');
  }
});
