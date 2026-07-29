import React, { useEffect, useRef, useState } from "react";
import { api } from "../services/api";
import { selectOrbStartupGreeting } from "../orb/startupGreetings";
import "./OrbStartupGreeting.css";

const INTRO_PLAYED_KEY = "orbweaver-startup-greeting-played";
const MIN_VISUAL_MS = 6500;
const MIN_VISUAL_AFTER_VOICE_MS = 3500;
const MAX_VISUAL_MS = 22000;
const EXCLUDED_ROUTES = new Set(["/signup", "/login", "/welcome"]);

const readSessionFlag = (): boolean => {
  try {
    return window.sessionStorage.getItem(INTRO_PLAYED_KEY) === "1";
  } catch {
    return false;
  }
};

const writeSessionFlag = (): void => {
  try {
    window.sessionStorage.setItem(INTRO_PLAYED_KEY, "1");
  } catch {
    // The intro still works when session storage is unavailable.
  }
};

export const OrbStartupGreeting: React.FC = () => {
  const [greeting] = useState(() => selectOrbStartupGreeting());
  const [visible, setVisible] = useState(() => {
    if (EXCLUDED_ROUTES.has(window.location.pathname)) return false;
    return !readSessionFlag();
  });
  const [phase, setPhase] = useState("Waking the machinery behind the curtain.");
  const shouldRunRef = useRef(visible);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    if (!shouldRunRef.current) return;

    const controller = new AbortController();
    const startedAt = Date.now();
    let cancelled = false;
    let visualTimer: number | null = null;
    let maxVisualTimer: number | null = null;
    let playbackStarted = false;

    const unlockEvents: Array<keyof WindowEventMap> = ["pointerdown", "touchstart", "keydown"];

    const markPlayedAndHide = () => {
      writeSessionFlag();
      setVisible(false);
    };

    const removeUnlockListeners = () => {
      unlockEvents.forEach((eventName) => window.removeEventListener(eventName, retryPlayback));
    };

    const scheduleVisualDismiss = () => {
      const elapsed = Date.now() - startedAt;
      const delay = Math.max(MIN_VISUAL_MS - elapsed, MIN_VISUAL_AFTER_VOICE_MS);
      if (visualTimer) window.clearTimeout(visualTimer);
      visualTimer = window.setTimeout(markPlayedAndHide, delay);
    };

    const retryPlayback = () => {
      const audio = audioRef.current;
      if (!audio || playbackStarted || cancelled) return;
      void audio.play()
        .then(() => {
          playbackStarted = true;
          setPhase("Weaver is speaking while the site finishes warming up.");
          removeUnlockListeners();
          scheduleVisualDismiss();
        })
        .catch(() => {
          setPhase("Voice is ready. Click or tap once to hear Weaver.");
        });
    };

    maxVisualTimer = window.setTimeout(markPlayedAndHide, MAX_VISUAL_MS);

    // These requests begin immediately and run together behind the greeting.
    void api.websiteOrbCapabilities().catch(() => undefined);
    void api.websiteOrbPageCapsule(window.location.href, controller.signal).catch(() => undefined);

    const prepareGreeting = async () => {
      try {
        setPhase("Warming Weaver’s voice and site intelligence.");
        const result = await api.websiteOrbTts(greeting.text, controller.signal);
        if (cancelled || !result.tts_audio_url) {
          setPhase("The site is ready. Weaver’s voice service is still connecting.");
          return;
        }

        const audio = new Audio(api.orbMediaUrl(result.tts_audio_url));
        audio.preload = "auto";
        audio.volume = 0.86;
        audioRef.current = audio;
        audio.onended = () => {
          removeUnlockListeners();
          markPlayedAndHide();
        };
        audio.onerror = () => {
          setPhase("The site is ready. Weaver’s voice service is still connecting.");
        };

        unlockEvents.forEach((eventName) => window.addEventListener(eventName, retryPlayback, { passive: true }));
        retryPlayback();
      } catch {
        if (!cancelled) {
          setPhase("The site is ready. Weaver’s voice service is still connecting.");
        }
      }
    };

    void prepareGreeting();

    return () => {
      cancelled = true;
      controller.abort();
      removeUnlockListeners();
      if (visualTimer) window.clearTimeout(visualTimer);
      if (maxVisualTimer) window.clearTimeout(maxVisualTimer);
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.src = "";
        audioRef.current = null;
      }
    };
  }, [greeting.text]);

  if (!visible) return null;

  return (
    <section className="orb-startup-splash" aria-label="Weaver introduction">
      <div className="orb-startup-card">
        <div className="orb-startup-orb" aria-hidden="true">
          <div className="orb-startup-halo" />
          <img src="/orb-skins/tuxorb.png" alt="" draggable={false} />
        </div>

        <div className="orb-startup-copy">
          {greeting.text.split("\n\n").map((paragraph, index) => (
            <p key={`${greeting.id}-${index}`}>{paragraph}</p>
          ))}
        </div>

        <div className="orb-startup-phase" aria-live="polite">
          <span className="orb-startup-phase-light" aria-hidden="true" />
          {phase}
        </div>
      </div>
    </section>
  );
};

export default OrbStartupGreeting;
