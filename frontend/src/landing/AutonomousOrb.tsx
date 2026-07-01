import React, { useCallback, useEffect, useRef, useState } from "react";
import { motion, useAnimationControls } from "framer-motion";
import { Orb } from "./Orb";
import { api } from "../services/api";

const wait = (ms: number) =>
  new Promise<void>((resolve) => window.setTimeout(resolve, ms));

type PulseKind = "intro" | "ripple" | "flare";

type PulseState = {
  id: number;
  kind: PulseKind;
} | null;

type OrbVoiceState = "idle" | "listening" | "speaking";

type Props = {
  size?: number;
  className?: string;
};

const HEADER_SAFE = 28;
const EDGE = 28;

export const AutonomousOrb: React.FC<Props> = ({
  size = 214,
  className = "",
}) => {
  const move = useAnimationControls();
  const surge = useAnimationControls();
  const glow = useAnimationControls();
  const presence = useAnimationControls();

  const activeRef = useRef(true);
  const reducedMotionRef = useRef(false);
  const positionRef = useRef({ x: 0, y: 0 });
  const recognitionRef = useRef<any>(null);
  const speechAudioRef = useRef<HTMLAudioElement | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const audioUnlockedRef = useRef(false);
  const statusTimerRef = useRef<number | null>(null);
  const avoidUntilRef = useRef(0);
  const lastAvoidRef = useRef(0);

  const [pulse, setPulse] = useState<PulseState>(null);
  const [voiceState, setVoiceState] = useState<OrbVoiceState>("idle");
  const [statusVisible, setStatusVisible] = useState(false);
  const [statusTitle, setStatusTitle] = useState("ORB online");
  const [statusLine, setStatusLine] = useState("Click to ask about Preflight, tools, or ORB deployment.");

  const bounds = () => {
    const minX = EDGE;
    const minY = HEADER_SAFE + EDGE;

    return {
      minX,
      minY,
      maxX: Math.max(minX, window.innerWidth - size - EDGE),
      maxY: Math.max(minY, window.innerHeight - size - EDGE),
    };
  };

  const clampPosition = (x: number, y: number) => {
    const { minX, minY, maxX, maxY } = bounds();

    return {
      x: Math.max(minX, Math.min(x, maxX)),
      y: Math.max(minY, Math.min(y, maxY)),
    };
  };

  const nextDestination = () => {
    const current = positionRef.current;
    const { minX, minY, maxX, maxY } = bounds();

    let candidate = current;

    for (let tries = 0; tries < 35; tries += 1) {
      const x = minX + Math.random() * Math.max(1, maxX - minX);
      const y = minY + Math.random() * Math.max(1, maxY - minY);

      const distance = Math.hypot(x - current.x, y - current.y);

      if (distance > Math.min(window.innerWidth * 0.24, 280)) {
        candidate = { x, y };
        break;
      }
    }

    return candidate;
  };

  const playPulse = async (kind: PulseKind, duration: number) => {
    const visibleDuration = Math.max(duration, kind === "ripple" ? 1150 : kind === "flare" ? 1450 : 2100);

    setPulse({
      id: Date.now() + Math.floor(Math.random() * 9999),
      kind,
    });

    await wait(visibleDuration);

    if (activeRef.current) {
      setPulse(null);
    }
  };

  const playLocalPresence = async () => {
    await presence.start({
      x: [0, 3, -2, 1, 0],
      y: [0, -4, 2, -1, 0],
      rotate: [0, 1.2, -0.8, 0],
      transition: {
        duration: 5 + Math.random() * 4,
        ease: "easeInOut",
      },
    });
  };

  const showStatus = useCallback((hideAfterMs?: number) => {
    setStatusVisible(true);
    if (statusTimerRef.current) {
      window.clearTimeout(statusTimerRef.current);
      statusTimerRef.current = null;
    }
    if (hideAfterMs) {
      statusTimerRef.current = window.setTimeout(() => {
        setStatusVisible(false);
        statusTimerRef.current = null;
      }, hideAfterMs);
    }
  }, []);

  const unlockAudio = useCallback(() => {
    if (audioUnlockedRef.current) return;
    audioUnlockedRef.current = true;

    const AudioContextCtor = (window as any).AudioContext || (window as any).webkitAudioContext;
    if (AudioContextCtor && !audioContextRef.current) {
      const context = new AudioContextCtor();
      audioContextRef.current = context;
      void context.resume?.();
    }

    const audio = new Audio(
      "data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAESsAACJWAAACABAAZGF0YQAAAAA="
    );
    audio.muted = true;
    void audio.play().catch(() => undefined);
  }, []);

  const summonToSpeechPosition = useCallback(async () => {
    if (reducedMotionRef.current) return;

    avoidUntilRef.current = Date.now() + 4200;

    const target = clampPosition(
      window.innerWidth / 2 - size / 2,
      window.innerHeight * 0.48 - size / 2
    );
    const current = positionRef.current;
    const distance = Math.hypot(target.x - current.x, target.y - current.y);

    await move.start({
      x: target.x,
      y: target.y,
      transition: {
        duration: Math.max(2.2, Math.min(4.8, distance / 165)),
        ease: [0.34, 0.78, 0.28, 1],
      },
    });

    if (activeRef.current) {
      positionRef.current = target;
    }
  }, [move, size]);

  const speak = useCallback(async (text: string, audioUrl?: string | null, provider?: string | null) => {
    showStatus();
    setStatusLine(text);
    setVoiceState("speaking");
    void summonToSpeechPosition();

    if (speechAudioRef.current) {
      speechAudioRef.current.pause();
      speechAudioRef.current = null;
    }

    if (!audioUrl) {
      setStatusTitle("TTS unavailable");
      setVoiceState("idle");
      showStatus(3600);
      return;
    }

    try {
      if (provider) {
        setStatusTitle(`Speaking with ${provider}`);
      }
      const audio = new Audio(api.orbMediaUrl(audioUrl));
      speechAudioRef.current = audio;
      audio.onended = () => {
        if (speechAudioRef.current === audio) {
          speechAudioRef.current = null;
        }
        setVoiceState("idle");
        showStatus(1400);
      };
      audio.onerror = () => {
        if (speechAudioRef.current === audio) {
          speechAudioRef.current = null;
        }
        setStatusTitle("TTS playback failed");
        setVoiceState("idle");
        showStatus(3600);
      };
      await audio.play();
    } catch {
      setStatusTitle("TTS playback blocked");
      setVoiceState("idle");
      showStatus(3600);
    }
  }, [showStatus, summonToSpeechPosition]);

  const speakWithGeneratedAudio = useCallback(async (text: string, audioUrl?: string | null, provider?: string | null) => {
    setStatusTitle("Preparing voice");
    setStatusLine(text);
    setVoiceState("speaking");
    showStatus();
    void summonToSpeechPosition();

    if (audioUrl) {
      await speak(text, audioUrl, provider);
      return;
    }

    try {
      const result = await api.websiteOrbTts(text);
      if (result.tts_error) {
        setStatusTitle(`TTS failed: ${result.tts_error}`);
        setVoiceState("idle");
        showStatus(5200);
        return;
      }
      await speak(text, result.tts_audio_url, result.tts_provider);
    } catch {
      setStatusTitle("TTS unavailable");
      setVoiceState("idle");
      showStatus(5200);
    }
  }, [showStatus, speak, summonToSpeechPosition]);

  const speakRecovery = useCallback(async (text: string) => {
    showStatus();
    try {
      const result = await api.websiteOrbTts(text);
      await speak(text, result.tts_audio_url, result.tts_provider);
    } catch {
      setStatusLine(text);
      setStatusTitle("TTS unavailable");
      setVoiceState("idle");
      showStatus(3600);
    }
  }, [showStatus, speak]);

  const askOrb = useCallback(async (transcript: string) => {
    const cleanTranscript = transcript.trim();
    if (!cleanTranscript) return;

    setStatusTitle("Thinking");
    setStatusLine("Preparing a response.");
    setVoiceState("speaking");
    showStatus();
    void summonToSpeechPosition();

    try {
      const result = await api.websiteOrbText(cleanTranscript, false);
      setStatusTitle("Voice response");
      setStatusLine(result.spoken_output);
      if (result.tts_error) {
        setStatusTitle(`TTS failed: ${result.tts_error}`);
      }
      await speakWithGeneratedAudio(result.spoken_output, result.tts_audio_url, result.tts_provider);
    } catch (error) {
      setStatusTitle("ORB route unavailable");
      void speakRecovery("I am reconnecting to my response service. Please try again in a moment.");
    }
  }, [showStatus, speakRecovery, speakWithGeneratedAudio, summonToSpeechPosition]);

  const handleOrbClick = useCallback(() => {
    unlockAudio();

    const SpeechRecognitionCtor =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognitionCtor) {
      const typed = window.prompt("Ask the ORB about Preflight, tools, Marketplace, or deployment.");
      if (typed) void askOrb(typed);
      return;
    }

    if (recognitionRef.current) {
      recognitionRef.current.stop();
      recognitionRef.current = null;
      setVoiceState("idle");
      setStatusVisible(false);
      return;
    }

    const recognition = new SpeechRecognitionCtor();
    recognitionRef.current = recognition;
    recognition.lang = "en-US";
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      setStatusTitle("Listening");
      setStatusLine("Speak naturally.");
      setVoiceState("listening");
      showStatus();
      void playPulse("ripple", 1150);
    };

    recognition.onresult = (event: any) => {
      const transcript = event.results?.[0]?.[0]?.transcript || "";
      recognitionRef.current = null;
      void askOrb(transcript);
    };

    recognition.onerror = () => {
      recognitionRef.current = null;
      setStatusTitle("Voice unavailable");
      void speakRecovery("Browser speech recognition is unavailable. You can still use public Preflight and account tools.");
    };

    recognition.onend = () => {
      recognitionRef.current = null;
      setVoiceState((current) => {
        if (current === "listening") {
          window.setTimeout(() => setStatusVisible(false), 700);
          return "idle";
        }
        return current;
      });
    };

    recognition.start();
  }, [askOrb, showStatus, speakRecovery, unlockAudio]);

  useEffect(() => {
    api.websiteOrbCapabilities()
      .then((payload) => {
        const toolLine = [
          payload.tesseract.available ? "Tesseract ready" : "Tesseract CLI missing",
          payload.chrome_devtools_mcp.available ? "MCP bridge detected" : "MCP optional",
          payload.current_orb_source_available ? "Cognition online" : "Cognition unavailable",
        ].join(" | ");
        setStatusLine(toolLine);
      })
      .catch(() => {
        setStatusLine("ORB online. Capability check unavailable.");
      });
  }, []);

  useEffect(() => {
    activeRef.current = true;
    reducedMotionRef.current = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    ).matches;

    const start = clampPosition(
      window.innerWidth * 0.66 - size / 2,
      window.innerHeight * 0.37 - size / 2
    );

    positionRef.current = start;
    move.set(start);

    const run = async () => {
      if (reducedMotionRef.current) {
        surge.set({ scale: 1, opacity: 1 });
        return;
      }

      const introAlreadyPlayed =
        window.sessionStorage.getItem("orbweaver-intro-played") === "1";

      if (!introAlreadyPlayed) {
        surge.set({ scale: 0.18, opacity: 0 });
        setPulse({ id: Date.now(), kind: "intro" });

        await surge.start({
          scale: [0.18, 1.55, 0.92, 1],
          opacity: [0, 1, 1, 1],
          transition: {
            duration: 2.1,
            ease: [0.16, 1, 0.3, 1],
            times: [0, 0.55, 0.8, 1],
          },
        });

        if (!activeRef.current) return;

        window.sessionStorage.setItem("orbweaver-intro-played", "1");
        setPulse(null);
      } else {
        surge.set({ scale: 1, opacity: 1 });
      }

      glow.start({
        opacity: [0.62, 0.96, 0.58, 0.88, 0.62],
        scale: [1, 1.1, 0.97, 1.06, 1],
        transition: {
          duration: 15,
          repeat: Infinity,
          ease: "easeInOut",
        },
      });

      await wait(700);

      while (activeRef.current) {
        if (Date.now() < avoidUntilRef.current) {
          await wait(450);
          continue;
        }

        const current = positionRef.current;
        const destination = nextDestination();
        const distance = Math.hypot(
          destination.x - current.x,
          destination.y - current.y
        );

        const longMove =
          distance > Math.min(window.innerWidth * 0.28, 340);

        const departurePulse =
          longMove && Math.random() < 0.16;

        const arrivalPulse =
          longMove && Math.random() < 0.42;

        if (departurePulse) {
          void playPulse("ripple", 920);
          await wait(260);
        } else {
          void playLocalPresence();
        }

        if (!activeRef.current) break;

        await move.start({
          x: destination.x,
          y: destination.y,
          transition: {
            duration: Math.max(3.1, Math.min(7.2, distance / 125)),
            ease: [0.34, 0.78, 0.28, 1],
          },
        });

        if (!activeRef.current) break;

        positionRef.current = destination;

        if (arrivalPulse) {
          void playPulse("flare", 1200);
        } else {
          void playLocalPresence();
        }

        if (!activeRef.current) break;

        await wait(850 + Math.random() * 1900);
      }
    };

    run();

    const handleResize = () => {
      const corrected = clampPosition(
        positionRef.current.x,
        positionRef.current.y
      );

      positionRef.current = corrected;
      move.set(corrected);
    };

    const handleMouseMove = (event: MouseEvent) => {
      if (reducedMotionRef.current) return;
      const now = Date.now();
      if (now - lastAvoidRef.current < 1250) return;

      const current = positionRef.current;
      const orbCenter = {
        x: current.x + size / 2,
        y: current.y + size / 2,
      };
      const dx = orbCenter.x - event.clientX;
      const dy = orbCenter.y - event.clientY;
      const distance = Math.hypot(dx, dy);
      const avoidRadius = Math.max(220, size * 1.04);

      if (distance > avoidRadius) return;

      lastAvoidRef.current = now;
      avoidUntilRef.current = now + 2600;

      const angle = distance > 0 ? Math.atan2(dy, dx) : Math.random() * Math.PI * 2;
      const closeness = 1 - Math.min(1, distance / avoidRadius);
      const push = 30 + closeness * 76;
      const sideSlip = (Math.random() - 0.5) * 24;
      const target = clampPosition(
        current.x + Math.cos(angle) * push + Math.cos(angle + Math.PI / 2) * sideSlip,
        current.y + Math.sin(angle) * push + Math.sin(angle + Math.PI / 2) * sideSlip
      );

      void move.start({
        x: target.x,
        y: target.y,
        transition: {
          duration: 2.45 + closeness * 1.05,
          ease: [0.34, 0.78, 0.28, 1],
        },
      }).then(() => {
        if (activeRef.current) {
          positionRef.current = target;
        }
      });
    };

    window.addEventListener("resize", handleResize);
    window.addEventListener("mousemove", handleMouseMove);

    return () => {
      activeRef.current = false;
      if (speechAudioRef.current) {
        speechAudioRef.current.pause();
      }
      if (statusTimerRef.current) {
        window.clearTimeout(statusTimerRef.current);
      }
      window.removeEventListener("resize", handleResize);
      window.removeEventListener("mousemove", handleMouseMove);
    };
  }, [glow, move, presence, size, surge]);

  const ringStyle = () => {
    if (pulse?.kind === "ripple") {
      return {
        rings: 2,
        color: "rgba(215,180,59,",
        maxScale: 1.6,
        duration: 0.82,
      };
    }

    if (pulse?.kind === "flare") {
      return {
        rings: 3,
        color: "rgba(91,200,230,",
        maxScale: 3.6,
        duration: 1.15,
      };
    }

    return {
      rings: 4,
      color: "rgba(91,200,230,",
      maxScale: 8.1,
      duration: 1.7,
    };
  };

  const visual = ringStyle();

  return (
    <>
    <button
      type="button"
      className="ow-v2-orb-summon"
      onClick={handleOrbClick}
      aria-label="Ask the ORB"
    >
      Ask ORB
    </button>
    <motion.div
      animate={move}
      className={`ow-v2-orb-position ${className}`}
      style={{
        position: "fixed",
        left: 0,
        top: 0,
        width: size,
        height: size,
        zIndex: 29,
        pointerEvents: "auto",
      }}
    >
      {pulse && (
        <div className="ow-v2-local-pulse" key={pulse.id}>
          <motion.div
            className="ow-v2-local-bloom"
            initial={{ scale: 0.1, opacity: 0 }}
            animate={{
              scale:
                pulse.kind === "intro"
                  ? [0.1, 1.2, 3.2]
                  : pulse.kind === "flare"
                  ? [0.12, 2.05]
                  : [0.12, 1.12],
              opacity: [0, 0.88, 0],
            }}
            transition={{
              duration: pulse.kind === "intro" ? 2 : visual.duration,
              ease: "easeOut",
            }}
          />

          {Array.from({ length: visual.rings }).map((_, index) => (
            <motion.div
              key={`${pulse.id}-${index}`}
              className="ow-v2-local-ring"
              style={{
                borderWidth: index === 0 ? 3 : 2,
                borderColor: `${visual.color}${0.78 - index * 0.16})`,
              }}
              initial={{ scale: 0.12, opacity: 0 }}
              animate={{
                scale: [0.12, visual.maxScale],
                opacity: [0.92, 0],
              }}
              transition={{
                duration: visual.duration,
                delay:
                  index *
                  (pulse.kind === "intro" ? 0.18 : 0.13),
                ease: [0.22, 0.61, 0.36, 1],
              }}
            />
          ))}

          {pulse.kind === "intro" && (
            <motion.div
              className="ow-v2-local-flash"
              initial={{ scale: 0.2, opacity: 0 }}
              animate={{
                scale: [0.2, 1.6, 0.4],
                opacity: [0, 0.9, 0],
              }}
              transition={{ duration: 0.9, ease: "easeOut" }}
            />
          )}
        </div>
      )}

      <motion.div animate={presence} style={{ transformOrigin: "center" }}>
        <motion.div animate={surge} style={{ transformOrigin: "center" }}>
          <motion.div animate={glow}>
            <div className="ow-v2-deploy-effect" aria-hidden="true">
              <span />
              <span />
              <span />
            </div>
            <Orb size={size} state={voiceState} onClick={handleOrbClick} />
          </motion.div>
        </motion.div>
      </motion.div>
      {statusVisible && (
        <div className="ow-v2-orb-status" aria-live="polite">
          <strong>{statusTitle}</strong>
          <span>{statusLine}</span>
        </div>
      )}
    </motion.div>
    </>
  );
};

export default AutonomousOrb;
