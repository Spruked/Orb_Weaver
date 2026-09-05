import React, { useEffect, useRef, useState } from "react";
import PublicHeader from "../components/PublicHeader";
import PublicFooter from "../components/PublicFooter";
import OrbBurst from "./OrbBurst";
import { api, authStore } from "../services/api";
import { trackOnboardingEvent } from "../services/analytics";
import { createIntentGuestSession, LandingIntent } from "../onboarding/guestOnboarding";
import "./Landing.css";

const LANDING_SPLASH_SESSION_KEY = "orbweaver-landing-splash-played";
const LANDING_SPLASH_COMPLETE_SESSION_KEY = "orbweaver-landing-splash-complete";
const STARTUP_GREETING_SESSION_KEY = "orbweaver-startup-greeting-played";
const FIRST_ENCOUNTER_STORAGE_KEY = "orbweaver-first-encounter-state";
const SHOWROOM_INTRO_AUDIO_URL = "/orb/voice/weaver-showroom-intro-am-michael.wav";
const POST_INTRO_READINESS_ATTEMPTS = 4;
const POST_INTRO_READINESS_RETRY_MS = 2000;
const INTRO_CAPTION_CUES = [
  { start: 0.429, end: 1.55, text: "Hello." },
  { start: 1.55, end: 3.402, text: "I am Weaver, the Orb Weaver Website Assistant." },
  { start: 3.98, end: 7.268, text: "I can help you with anything you need. I am not a chatbot." },
  { start: 7.78, end: 15.797, text: "I make this website intelligent, so you can find things easier, navigate faster, process your orders quicker, and resolve issues seamlessly." },
  { start: 16.374, end: 21.068, text: "Just call me Weaver. Feel free to ask a question in your normal way and I will answer." },
  { start: 21.632, end: 22.534, text: "Let's get started." },
];

type IntroAudioState = "preloading" | "playing" | "autoplay_blocked" | "error" | "warming" | "blocked";
type StartupReadinessResult = { ready: boolean; error?: string; [key: string]: unknown };

// A fresh customer crawl is not a prerequisite for Weaver to host Orb
// Weaver's own landing page.  The opening only needs the proven live voice
// path and the landing page's verified guidance map; Preflight later obtains
// the visitor's site intelligence.
const landingTourRuntimeReady = (readiness: StartupReadinessResult): boolean => {
  if (readiness.ready) return true;
  const proofs = readiness.proofs as Record<string, { ready?: boolean }> | undefined;
  return ["STT_READY", "COGNITION_READY", "KOKORO_READY", "POINTER_READY", "GOVERNANCE_READY"]
    .every((proof) => proofs?.[proof]?.ready === true);
};

const LandingPage: React.FC = () => {
  const [pendingTarget, setPendingTarget] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [visibleBeats, setVisibleBeats] = useState<Record<string, boolean>>({ beat1: true });
  const [splashTrigger, setSplashTrigger] = useState(0);
  const [introBeat, setIntroBeat] = useState<number | null>(null);
  const [introAudioState, setIntroAudioState] = useState<IntroAudioState>("preloading");
  const introAudioRef = useRef<HTMLAudioElement | null>(null);
  const introPlaybackRequestRef = useRef<(() => void) | null>(null);
  const completeStartupGateRef = useRef<(voiceUnavailable?: boolean) => void>(() => undefined);
  const startupReadinessRef = useRef<Promise<StartupReadinessResult> | null>(null);

  const beginStartupWarmup = () => {
    if (startupReadinessRef.current) return startupReadinessRef.current;

    window.dispatchEvent(new CustomEvent("orbweaver:startup-intro", {
      detail: { phase: "STARTUP_WARMUP_STARTED" },
    }));

    startupReadinessRef.current = (async () => {
      let lastResult: StartupReadinessResult | null = null;
      let lastError: unknown = null;
      for (let attempt = 1; attempt <= POST_INTRO_READINESS_ATTEMPTS; attempt += 1) {
        window.dispatchEvent(new CustomEvent("orbweaver:startup-intro", {
          detail: { phase: "STARTUP_READINESS_CHECK", attempt },
        }));
        try {
          const readiness: StartupReadinessResult = { ...(await api.websiteOrbStartupReadiness(
            new URL(`${window.location.pathname}${window.location.search}`, "https://orbweaver.spruked.com").toString(),
          )) };
          lastResult = readiness;
          if (landingTourRuntimeReady(readiness)) {
            const readyForLandingTour = readiness.ready
              ? readiness
              : { ...readiness, ready: true, state: "LANDING_TOUR_READY" };
            window.dispatchEvent(new CustomEvent("orbweaver:startup-intro", {
              detail: { phase: "STARTUP_WARMUP_READY", readiness: readyForLandingTour },
            }));
            return readyForLandingTour;
          }
        } catch (error) {
          lastError = error;
        }
        if (attempt < POST_INTRO_READINESS_ATTEMPTS) {
          await new Promise<void>((resolve) => window.setTimeout(resolve, POST_INTRO_READINESS_RETRY_MS));
        }
      }
      const failure = lastResult || { ready: false, error: String(lastError || "readiness_timeout") };
      window.dispatchEvent(new CustomEvent("orbweaver:startup-intro", {
        detail: { phase: "STARTUP_WARMUP_BLOCKED", readiness: failure },
      }));
      return failure;
    })();
    return startupReadinessRef.current;
  };

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("orbStartupReset") === "1") {
      window.sessionStorage.removeItem(LANDING_SPLASH_SESSION_KEY);
      window.sessionStorage.removeItem(LANDING_SPLASH_COMPLETE_SESSION_KEY);
      window.sessionStorage.removeItem(STARTUP_GREETING_SESSION_KEY);
      window.sessionStorage.removeItem(FIRST_ENCOUNTER_STORAGE_KEY);
    }

    if (window.sessionStorage.getItem(LANDING_SPLASH_SESSION_KEY) === "1") {
      window.sessionStorage.setItem(LANDING_SPLASH_COMPLETE_SESSION_KEY, "1");
      window.dispatchEvent(new CustomEvent("orbweaver:startup-gate-complete", {
        detail: { splash_state: "skipped_session_once" },
      }));
      return;
    }

    void beginStartupWarmup();
    setSplashTrigger(Date.now());
  }, []);

  useEffect(() => {
    if (!splashTrigger) return;
    let cancelled = false;

    const emitIntro = (phase: string, detail: Record<string, unknown> = {}) => {
      window.dispatchEvent(new CustomEvent("orbweaver:startup-intro", { detail: { phase, ...detail } }));
    };

    const audio = new Audio(SHOWROOM_INTRO_AUDIO_URL);
    let playbackRequested = false;
    let introFailed = false;
    let startupCompletionRequested = false;
    audio.preload = "auto";
    introAudioRef.current = audio;
    setIntroAudioState("preloading");
    setIntroBeat(null);
    emitIntro("INTRO_AUDIO_REQUESTED", {
      provider: "kokoro",
      voice: "am_michael",
      asset: SHOWROOM_INTRO_AUDIO_URL,
    });

    const completeStartup = (voiceUnavailable = false) => {
      if (cancelled || startupCompletionRequested) return;
      startupCompletionRequested = true;
      completeStartupGateRef.current(voiceUnavailable);
    };

    const syncCaption = () => {
      if (cancelled) return;
      const cueIndex = INTRO_CAPTION_CUES.findIndex(
        (cue) => audio.currentTime >= cue.start && audio.currentTime < cue.end,
      );
      const nextCue = cueIndex >= 0 ? cueIndex : null;
      setIntroBeat((current) => (current === nextCue ? current : nextCue));
    };

    const fail = (phase: "INTRO_AUTOPLAY_BLOCKED" | "INTRO_AUDIO_ERROR", detail: Record<string, unknown> = {}) => {
      if (cancelled || introFailed) return;
      introFailed = true;
      setIntroBeat(null);
      setIntroAudioState(phase === "INTRO_AUTOPLAY_BLOCKED" ? "autoplay_blocked" : "error");
      emitIntro(phase, { ...detail });
      // Audible autoplay is normally blocked on a first visit. Keep the
      // startup cover in place and let one visitor tap resume the scripted
      // Web Audio path; do not silently discard the spoken introduction.
      if (phase === "INTRO_AUDIO_ERROR") completeStartup(true);
    };

    const startPlayback = () => {
      if (cancelled || introFailed || playbackRequested) return;
      playbackRequested = true;
      void audio.play().then(() => {
        if (cancelled || introFailed) return;
        setIntroAudioState("playing");
        syncCaption();
        emitIntro("INTRO_AUDIO_PLAYING", {
          provider: "kokoro",
          voice: "am_michael",
          asset: audio.currentSrc,
          duration: Number.isFinite(audio.duration) ? audio.duration : null,
          playResolved: true,
        });
      }).catch((error) => {
        const name = (error as Error)?.name;
        playbackRequested = false;
        fail(name === "NotAllowedError" ? "INTRO_AUTOPLAY_BLOCKED" : "INTRO_AUDIO_ERROR", {
          error: name || "AudioPlaybackError",
        });
      });
    };

    introPlaybackRequestRef.current = () => {
      if (cancelled) return;
      introFailed = false;
      setIntroAudioState("preloading");
      startPlayback();
    };

    audio.oncanplay = startPlayback;
    audio.ontimeupdate = syncCaption;
    audio.onerror = () => fail("INTRO_AUDIO_ERROR", { error: "MediaError" });
    audio.onabort = () => {
      if (!cancelled) fail("INTRO_AUDIO_ERROR", { error: "MediaAbort" });
    };
    audio.onended = () => {
      if (cancelled) return;
      setIntroBeat(null);
      emitIntro("INTRO_AUDIO_ENDED", { asset: audio.currentSrc, duration: audio.duration });
      window.sessionStorage.setItem(STARTUP_GREETING_SESSION_KEY, "1");
      completeStartup();
    };
    audio.load();
    if (audio.readyState >= HTMLMediaElement.HAVE_FUTURE_DATA) startPlayback();

    return () => {
      cancelled = true;
      introAudioRef.current?.pause();
      introAudioRef.current = null;
      introPlaybackRequestRef.current = null;
    };
  }, [splashTrigger]);

  useEffect(() => {
    if (!splashTrigger) return;
    window.dispatchEvent(new CustomEvent("orbweaver:startup-gate-started", {
      detail: { splash_state: "playing" },
    }));
  }, [splashTrigger]);

  const completeStartupGate = async (voiceUnavailable = false) => {
    if (!voiceUnavailable) setIntroAudioState("warming");
    const readiness = await beginStartupWarmup();
    if (readiness.ready) {
      window.sessionStorage.setItem(LANDING_SPLASH_SESSION_KEY, "1");
      window.sessionStorage.setItem(LANDING_SPLASH_COMPLETE_SESSION_KEY, "1");
      setSplashTrigger(0);
      window.dispatchEvent(new CustomEvent("orbweaver:startup-gate-complete", {
        detail: { splash_state: "complete", readiness_state: "READY", readiness },
      }));
      return;
    }

    window.sessionStorage.setItem(LANDING_SPLASH_SESSION_KEY, "1");
    window.sessionStorage.setItem(LANDING_SPLASH_COMPLETE_SESSION_KEY, "1");
    setSplashTrigger(0);
    window.dispatchEvent(new CustomEvent("orbweaver:startup-gate-complete", {
      detail: { splash_state: "complete", readiness_state: "BLOCKED", readiness_error: String(readiness.error || "readiness_timeout") },
    }));
  };
  completeStartupGateRef.current = (voiceUnavailable = false) => {
    void completeStartupGate(voiceUnavailable);
  };

  useEffect(() => {
    const observed = Array.from(document.querySelectorAll<HTMLElement>('[data-beat-id]'));
    if (!observed.length) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          const beatId = entry.target.getAttribute('data-beat-id');
          if (!beatId) return;
          setVisibleBeats((current) => (current[beatId] ? current : { ...current, [beatId]: true }));
          observer.unobserve(entry.target);
        });
      },
      { threshold: 0.1, rootMargin: '0px 0px 20% 0px' }
    );

    observed.forEach((node) => observer.observe(node));
    return () => observer.disconnect();
  }, []);

  const begin = async (target: string, intent: LandingIntent, tier: 'basic' | 'enhanced' | 'premium' | null = null) => {
    if (intent === 'dashboard' && authStore.getToken()) {
      window.location.assign('/dashboard');
      return;
    }
    setError('');
    setPendingTarget(target);
    trackOnboardingEvent('landing_signup_cta_clicked', { intent, ...(tier ? { tier } : {}) });
    try {
      await createIntentGuestSession(target, intent, tier);
      window.location.assign(target);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'We could not start onboarding. Please try again.');
      setPendingTarget(null);
    }
  };

  const beatClassName = (beatId: string, tone: 'hero' | 'neutral' | 'accent' = 'neutral') => {
    const visible = visibleBeats[beatId] ? 'is-visible' : '';
    return `ow-cut-beat ow-cut-beat-${tone} ${visible}`.trim();
  };

  return (
    <main className="ow-cut-page">
      {splashTrigger > 0 && (
        <div
          className="ow-cut-startup-gate"
          aria-live="polite"
        >
          {introBeat !== null && (
            <div className="ow-cut-startup-caption" key={INTRO_CAPTION_CUES[introBeat].text}>
              {INTRO_CAPTION_CUES[introBeat].text}
            </div>
          )}
          <div className="ow-cut-startup-burst" aria-hidden="true">
            <OrbBurst
              trigger={splashTrigger}
              size={260}
              color="blue"
              direction="out"
              onComplete={() => undefined}
            />
          </div>
          {(introAudioState === "autoplay_blocked" || introAudioState === "error" || introAudioState === "warming" || introAudioState === "blocked") && (
            <p className="ow-cut-startup-audio-status" role="status">
              {introAudioState === "warming"
                ? "Weaver is getting ready..."
                : introAudioState === "autoplay_blocked"
                  ? "Audio needs your permission. Start with Weaver to hear the introduction."
                  : introAudioState === "blocked"
                    ? "Voice temporarily unavailable."
                    : "Voice unavailable. Continuing startup..."}
            </p>
          )}
          {introAudioState === "autoplay_blocked" && (
            <button
              type="button"
              className="ow-cut-startup-button"
              onClick={() => introPlaybackRequestRef.current?.()}
            >
              Start with Weaver
            </button>
          )}
        </div>
      )}

      <div className="ow-cut-grid" />
      <div className="ow-cut-noise" />

      <PublicHeader theme="dark" />

      {/* BEAT 1 — Curiosity */}
      <section id="beat-1" data-beat-id="beat1" className={beatClassName('beat1', 'hero')}>
        <div className="ow-cut-shell ow-cut-shell-single">
          <div className="ow-cut-copy ow-cut-curiosity">
            <h1 className="ow-cut-word-reveal">A web is woven.</h1>
            <h1 className="ow-cut-word-reveal ow-cut-word-reveal-delayed">So is website intelligence.</h1>
          </div>
        </div>
      </section>

      <section id="weaver-first-encounter" data-beat-id="firstEncounter" className={beatClassName('firstEncounter', 'accent')}>
        <div className="ow-cut-shell ow-cut-shell-single">
          <div className="ow-cut-copy ow-cut-first-encounter">
            <h2>Meet Weaver.</h2>
            <div className="ow-cut-encounter-steps" aria-label="Weaver communication orientation">
              <p data-orb-target="what_weaver_does"><strong>What does Weaver do?</strong> It understands this website, answers from its verified knowledge, and guides you to the right place when showing is faster than explaining.</p>
              <p data-orb-target="what_to_say"><strong>What do I say?</strong> Anything you would ask a person who knows the site. Click Weaver, speak naturally, finish your thought, and pause.</p>
              <p id="watch-weaver-guide" data-orb-target="watch_weaver_guide"><strong>Watch Weaver guide.</strong> When pointing is useful, Weaver guides only to a verified target and pings the exact place it can prove is live.</p>
              <p data-orb-target="interrupt_or_guide"><strong>You stay in control.</strong> Click Weaver while it is talking to stop it. Click again when you want help.</p>
            </div>
          </div>
        </div>
      </section>

      {/* BEAT 2 — Challenge the belief */}
      <section id="beat-2" data-beat-id="beat2" className={beatClassName('beat2')}>
        <div className="ow-cut-shell ow-cut-shell-single">
          <div className="ow-cut-copy">
            <p>For thirty years we've accepted crawling as the way websites are understood.</p>
            <p className="ow-cut-preline"><strong>A crawl discovers pages.</strong></p>
            <p className="ow-cut-preline"><strong>A weave discovers purpose.</strong></p>
          </div>
        </div>
      </section>

      {/* BEAT 3 — The reveal */}
      <section id="beat-3" data-beat-id="beat3" className={beatClassName('beat3', 'accent')}>
        <div className="ow-cut-shell ow-cut-shell-split">
          <div className="ow-cut-copy">
            <p>Your website isn't made of pages.</p>
            <p><strong>It's made of relationships.</strong></p>
            <div className="ow-cut-strands" aria-label="Relationship strands">
              <p>Products.</p>
              <p>Services.</p>
              <p>People.</p>
              <p>Policies.</p>
              <p>Questions.</p>
              <p>Customer journeys.</p>
              <p>Decisions.</p>
              <p>Knowledge.</p>
            </div>
            <p className="ow-cut-emphasis">That's where intelligence actually lives.</p>
          </div>
          <div className="ow-cut-visual" aria-hidden="true">
            <img className="ow-cut-visual-image" src="/orbweaver1600.png" alt="Orb Weaver intelligence sphere with glowing blue core representing website knowledge" />
          </div>
        </div>
      </section>

      {/* BEAT 4 — Introduce ORB Weaver */}
      <section id="beat-4" data-beat-id="beat4" className={beatClassName('beat4')}>
        <div className="ow-cut-shell ow-cut-shell-single">
          <div className="ow-cut-copy">
            <p>That's why ORB Weaver exists.</p>
            <p>It doesn't stop when it finds your website.</p>
            <p><strong>That's where the real work begins.</strong></p>
          </div>
        </div>
      </section>

      {/* BEAT 5 — Explain weaving */}
      <section id="beat-5" data-beat-id="beat5" className={beatClassName('beat5', 'accent')}>
        <div className="ow-cut-shell ow-cut-shell-split">
          <div className="ow-cut-visual" aria-hidden="true">
            <img className="ow-cut-visual-image" src="/WORKORB1600.png" alt="Website ORB processing and weaving business data into contextual intelligence" />
          </div>
          <div className="ow-cut-copy">
            <p>Imagine taking every page.</p>
            <p>Every product.</p>
            <p>Every FAQ.</p>
            <p>Every customer journey.</p>
            <p>Every verified business fact.</p>
            <p>Every relationship between them.</p>
            <p className="ow-cut-pause" />
            <p className="ow-cut-emphasis"><strong>...and weaving them into one operational structure.</strong></p>
          </div>
        </div>
      </section>

      {/* BEAT 6 — Reveal the ORB */}
      <section id="beat-6" data-beat-id="beat6" className={beatClassName('beat6', 'hero')}>
        <div className="ow-cut-shell ow-cut-shell-reveal">
          <div className="ow-cut-copy">
            <p>When the final weave is complete, something new exists.</p>
            <h2 className="ow-cut-orb-reveal">A Website ORB.</h2>
          </div>
          <div className="ow-cut-reveal-visual" aria-hidden="true">
            <div className="ow-cut-reveal-orb-wrap">
              <img 
                src="/lightstreamorbblue1024.png" 
                alt="Luminous blue Website ORB with streaming light patterns representing real-time visitor guidance" 
                style={{
                  position: 'absolute',
                  inset: '12%',
                  width: '76%',
                  height: '76%',
                  objectFit: 'contain',
                  zIndex: 2,
                  filter: 'drop-shadow(0 0 40px rgba(108, 215, 238, 0.6))'
                }}
              />
              <div className="ow-cut-splash-bloom" />
              <div className="ow-cut-splash-ring ow-cut-splash-ring-a" />
              <div className="ow-cut-splash-ring ow-cut-splash-ring-b" />
              <div className="ow-cut-splash-ring ow-cut-splash-ring-c" />
            </div>
          </div>
        </div>
      </section>

      {/* BEAT 7 — So what (emotional hit) */}
      <section id="beat-7" data-beat-id="beat7" className={beatClassName('beat7', 'hero')}>
        <div className="ow-cut-shell ow-cut-shell-single">
          <div className="ow-cut-copy">
            <p>Your customers stop wandering.</p>
            <p>They stop abandoning forms.</p>
            <p>They stop asking the same questions twice.</p>
            <p>They stop leaving because they couldn't find what they needed.</p>
            <p className="ow-cut-pause" />
            <p className="ow-cut-emphasis"><strong>Instead — they're greeted. Guided. Understood. Helped. Finished.</strong></p>
            <h2>Your website becomes the best-informed employee you'll ever hire.</h2>
            <p className="ow-cut-emphasis"><strong>Not a service you rent.</strong></p>
            <p className="ow-cut-emphasis"><strong>An intelligence you own.</strong></p>
          </div>
        </div>
      </section>

      {/* BEAT 8 — Can I trust it? */}
      <section id="beat-8" data-beat-id="beat8" className={beatClassName('beat8', 'accent')}>
        <div className="ow-cut-shell ow-cut-shell-single">
          <div className="ow-cut-copy">
            <h2>Can I trust it?</h2>
            <p><strong>Security. Governance. Verification. Truth.</strong></p>
            <p>ORB Weaver guides with verified state, bounded permissions, and explicit control governance — so business guidance remains safe, truthful, and dependable.</p>
            <a className="ow-cut-link" href="/security">See Security Design →</a>
          </div>
        </div>
      </section>

      {/* BEAT 9 — How does it actually work? */}
      <section id="beat-9" data-beat-id="beat9" className={beatClassName('beat9')}>
        <div className="ow-cut-shell ow-cut-shell-technical">
          <div className="ow-cut-copy">
            <h2>How does it actually work?</h2>
            <h2>Beneath the Weave</h2>
            <p><strong>28-Weave™ Assembly.</strong></p>
            <p>Not a crawl. Not an audit. A manufacturing process — twenty-eight explicit weaves that compile your website into verified knowledge, live pointer intelligence, and a learning system that gets smarter every month.</p>
            <p>Four of those weaves exist nowhere else: <strong>a priori knowledge</strong> compiled from your own verified facts and policies, <strong>a posteriori knowledge</strong> that keeps learning after launch, <strong>multi-funnel continuity</strong> across every path a visitor can take, and <strong>pointer intelligence</strong> that turns "click here" into something verified, not guessed.</p>
            <p>The rest — SEO, accessibility, performance, security, schema — get handled too. But that's not what makes this a Website ORB instead of a website audit.</p>
            <p>Under the experience, ORB Weaver compiles website structure, verifies navigation targets, and coordinates guidance using governed runtime capabilities — so every answer is precise, not improvised.</p>
            <p className="ow-cut-emphasis"><strong>28-Weave™ becomes one web.</strong></p>
            <p>Not the web you already know. A new one — built from your own pages, products, and knowledge. Stronger every day, in the hands of ORB Weaver.</p>
            
            <h2 className="ow-cut-pause">Here's what that strength looks like:</h2>
            <ul className="ow-cut-list" aria-label="Commercial value outcomes">
              <li>Reduce visitor confusion — Help people understand where to go and what to do next.</li>
              <li>Increase completed journeys — Guide users from intent to completion across forms, checkout, and service workflows.</li>
              <li>Reduce abandonment — Support visitors at hesitation points before they drop out.</li>
              <li>Improve engagement quality — Create clearer, more useful interactions that keep visitors progressing.</li>
              <li>Strengthen trust — Use verified guidance and transparent behavior instead of guesswork.</li>
              <li>Accelerate decision-making — Shorten time from first visit to confident action.</li>
            </ul>

            <a className="ow-cut-link" href="/how-it-works">See How It Works →</a>
          </div>
          
          <div className="ow-cut-technical-visual" aria-hidden="true">
            <div className="ow-cut-technical-panel ow-cut-technical-panel-main">
              <div style={{
                padding: '20px',
                display: 'flex',
                flexDirection: 'column',
                gap: '12px',
                height: '100%'
              }}>
                <div style={{
                  fontSize: '11px',
                  fontWeight: 800,
                  letterSpacing: '0.12em',
                  color: 'rgba(108, 215, 238, 0.7)',
                  textTransform: 'uppercase'
                }}>Weave Assembly Status</div>
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '8px' }}>
                  {['Knowledge Graph', 'Pointer Intelligence', 'Route Verification', 'Guidance Mesh', 'A Priori Data', 'A Posteriori Learning'].map((item, i) => (
                    <div key={item} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <div style={{
                        width: '6px',
                        height: '6px',
                        borderRadius: '50%',
                        background: 'rgba(108, 215, 238, 0.8)',
                        boxShadow: '0 0 8px rgba(108, 215, 238, 0.6)'
                      }} />
                      <span style={{ fontSize: '13px', color: '#b8cad4' }}>{item}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            <div className="ow-cut-technical-panel ow-cut-technical-panel-orb">
              <img 
                src="/blueprintorb1600.png" 
                alt="Technical blueprint view of ORB Weaver architecture showing intelligent routing and guidance systems" 
                style={{
                  position: 'absolute',
                  inset: 0,
                  width: '100%',
                  height: '100%',
                  objectFit: 'cover',
                  borderRadius: '50%'
                }}
              />
            </div>
          </div>
        </div>
      </section>

      {/* BEAT 10 — The ending */}
      <section id="beat-10" data-beat-id="beat10" className={beatClassName('beat10', 'hero')}>
        <div className="ow-cut-copy">
          <p>Your website already contains everything it needs.</p>
          <p><strong>ORB Weaver weaves it together.</strong></p>
          <h2>Begin the First Weave.</h2>

          <div className="ow-cut-actions">
            <button
              id="landing-free-preflight"
              data-orb-target="run-free-preflight"
              className="ow-cut-primary"
              onClick={() => window.location.assign('/preflight')}
              disabled={Boolean(pendingTarget)}
            >
              Run a Free Preflight Scan
            </button>

            <button
              id="landing-dashboard"
              data-orb-target="launch-dashboard"
              className="ow-cut-secondary"
              onClick={() => begin('/login?next=/dashboard', 'dashboard')}
              disabled={Boolean(pendingTarget)}
            >
              {pendingTarget === '/login?next=/dashboard' ? 'Preparing...' : 'Launch Dashboard'}
            </button>
          </div>

          <p className="ow-cut-secondary-links">
            <a href="https://campaign.orbweaver.spruked.com">Campaign, Beta &amp; Investor Portal</a>
            <span>·</span>
            <a href="/features">Explore Business Features</a>
          </p>

          {error && <p className="ow-cut-error" role="alert">{error}</p>}
        </div>
      </section>

      <PublicFooter />
    </main>
  );
};

export default LandingPage;
