import { clearActiveOrbProjectContext } from './activeProjectContext';

type RuntimeGuardOptions = {
  authenticated: boolean;
};

const STARTUP_GATE_SELECTOR = '.ow-cut-startup-gate.is-ready';
const STARTUP_BUTTON_SELECTOR = '.ow-cut-startup-button:not(:disabled)';
const ORB_POSITION_SELECTOR = '.ow-v2-orb-position';
const ORB_SPEECH_SELECTOR = '.ow-v2-orb-speech';

const runtimeWindow = window as any;

function preferControlledOrbStt(): void {
  const controlledRecorderAvailable = Boolean(
    navigator.mediaDevices?.getUserMedia && typeof MediaRecorder !== 'undefined'
  );
  if (!controlledRecorderAvailable) return;

  for (const key of ['SpeechRecognition', 'webkitSpeechRecognition'] as const) {
    const existing = runtimeWindow[key];
    if (existing && !runtimeWindow[`__ORB_NATIVE_${key}__`]) {
      runtimeWindow[`__ORB_NATIVE_${key}__`] = existing;
    }
    try {
      Object.defineProperty(runtimeWindow, key, {
        configurable: true,
        writable: true,
        value: undefined,
      });
    } catch {
      try {
        runtimeWindow[key] = undefined;
      } catch {
        // If the browser prevents shadowing the native constructor, the
        // mounted ORB will retain its existing browser-recognition fallback.
      }
    }
  }
}

function installAutomaticStartupHandoff(): void {
  const completeReadyGate = (): boolean => {
    const gate = document.querySelector<HTMLElement>(STARTUP_GATE_SELECTOR);
    const button = gate?.querySelector<HTMLButtonElement>(STARTUP_BUTTON_SELECTOR);
    if (!gate || !button) return false;

    // Product doctrine: the splash hands off automatically. A synthetic
    // click invokes the existing React gate-completion path without exposing
    // a mandatory Start ORB control to the visitor.
    button.click();
    return true;
  };

  if (completeReadyGate()) return;

  const observer = new MutationObserver(() => {
    if (!completeReadyGate()) return;
    observer.disconnect();
  });
  observer.observe(document.documentElement, {
    childList: true,
    subtree: true,
    attributes: true,
    attributeFilter: ['class', 'disabled'],
  });
}

function installSpeechBubbleViewportGuard(): void {
  let frame: number | null = null;

  const positionBubble = () => {
    const orb = document.querySelector<HTMLElement>(ORB_POSITION_SELECTOR);
    const bubble = orb?.querySelector<HTMLElement>(ORB_SPEECH_SELECTOR);
    if (!orb || !bubble) {
      frame = null;
      return;
    }

    const orbRect = orb.getBoundingClientRect();
    const viewportPadding = 12;
    const width = Math.min(360, Math.max(180, window.innerWidth - viewportPadding * 2));
    const maxHeight = Math.min(280, Math.max(120, window.innerHeight * 0.52));
    const globalLeft = Math.max(
      viewportPadding,
      Math.min(
        orbRect.left + orbRect.width / 2 - width / 2,
        window.innerWidth - width - viewportPadding,
      ),
    );

    bubble.style.position = 'absolute';
    bubble.style.left = `${globalLeft - orbRect.left}px`;
    bubble.style.right = 'auto';
    bubble.style.width = `${width}px`;
    bubble.style.maxWidth = `${width}px`;
    bubble.style.maxHeight = `${maxHeight}px`;
    bubble.style.overflowY = 'auto';
    bubble.style.overflowWrap = 'anywhere';
    bubble.style.transform = 'none';

    const measuredHeight = Math.min(maxHeight, Math.max(44, bubble.scrollHeight));
    const canFitBelow = orbRect.bottom + 10 + measuredHeight <= window.innerHeight - viewportPadding;
    bubble.style.top = canFitBelow
      ? `${orbRect.height + 10}px`
      : `${-measuredHeight - 10}px`;

    frame = window.requestAnimationFrame(positionBubble);
  };

  const ensurePositioning = () => {
    if (frame != null) return;
    if (!document.querySelector(ORB_SPEECH_SELECTOR)) return;
    frame = window.requestAnimationFrame(positionBubble);
  };

  const observer = new MutationObserver(ensurePositioning);
  observer.observe(document.documentElement, { childList: true, subtree: true });
  ensurePositioning();
}

export function installWebsiteOrbRuntimeGuards(options: RuntimeGuardOptions): void {
  if (runtimeWindow.__ORB_WEAVER_RUNTIME_GUARDS_INSTALLED__) return;
  runtimeWindow.__ORB_WEAVER_RUNTIME_GUARDS_INSTALLED__ = true;

  // A stale owner/customer project selection must never leak into the public
  // Website ORB. Logged-in account routes retain their selected project.
  if (!options.authenticated && window.location.pathname === '/') {
    clearActiveOrbProjectContext();
  }

  // The controlled MediaRecorder -> Faster Whisper path is authoritative when
  // available. Browser SpeechRecognition remains only a capability fallback.
  preferControlledOrbStt();

  // Restore splash -> ORB automatic handoff and keep response text on-screen.
  installAutomaticStartupHandoff();
  installSpeechBubbleViewportGuard();
}
