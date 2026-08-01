import React, { useCallback, useEffect, useRef, useState } from "react";
import { motion, useAnimationControls } from "framer-motion";
import { Volume2, VolumeX } from "lucide-react";
import { Orb } from "./Orb";
import { api, type WebsiteOrbPointerRecord } from "../services/api";
import { OrbRoboticsMovementController } from "../orb/robotics/movementController";
import type { RobotCommand } from "../orb/robotics/robotMovement.types";
import { selectOrbStartupGreeting } from "../orb/startupGreetings";

const wait = (ms: number) =>
  new Promise<void>((resolve) => window.setTimeout(resolve, ms));

const LATENCY_FILLER_PATHS = [
  "/orb/voice/latency-fillers/ack.wav",
  "/orb/voice/latency-fillers/thinking.wav",
  "/orb/voice/latency-fillers/working.wav",
];

const VOICE_UNAVAILABLE_MESSAGE = "Voice unavailable";
const MIN_RECORDING_MS = 700;
const END_SILENCE_MS = 850;
const ABSOLUTE_RECORDING_LIMIT_MS = 14000;
const SPEECH_LEVEL_THRESHOLD = 0.018;

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

const HEADER_SAFE = 96;
const ORB_OVERLAY_Z_INDEX = 2147483000;
const EDGE = 8;
const IDLE_TRAVEL_MIN_MS = 6500;
const IDLE_TRAVEL_MAX_MS = 10500;
const IDLE_PAUSE_MIN_MS = 1800;
const IDLE_PAUSE_MAX_MS = 4200;
const REST_AFTER_INACTIVITY_MS = 5 * 60 * 1000;
const ACTIVE_ORB_OPACITY = 1;
const REST_ORB_OPACITY = 0.55;
const normalizeIntentText = (value: string): string =>
  (value || "").replace(/\s+/g, " ").trim().toLowerCase();

const routeForUrl = (value?: string | null): string => {
  if (!value) return "/";
  try {
    return new URL(value, window.location.origin).pathname.replace(/\/+$/, "") || "/";
  } catch {
    return "/";
  }
};

const startupGreetingText = (): string => {
  const paragraphs = selectOrbStartupGreeting()
    .text
    .split(/\n\s*\n/)
    .map((paragraph) => paragraph.trim())
    .filter(Boolean);

  return [
    paragraphs[0] || "Welcome to Orb Weaver.",
    paragraphs[1] || "I’m Weaver, your website ORB.",
    "What brought you here?",
  ].join("\n\n");
};

export const AutonomousOrb: React.FC<Props> = ({
  size = 190,
  className = "",
}) => {
  const onboardingSafeMode = ['/signup', '/login', '/welcome'].includes(window.location.pathname);
  const move = useAnimationControls();
  const surge = useAnimationControls();
  const glow = useAnimationControls();
  const presence = useAnimationControls();
  const activeRef = useRef(true);
  const reducedMotionRef = useRef(false);
  const positionRef = useRef({ x: 0, y: 0 });
  const idleHeadingRef = useRef(Math.random() * Math.PI * 2);
  const movementControllerRef = useRef<OrbRoboticsMovementController | null>(null);
  const worldStateSequenceRef = useRef(1);
  const lastActivityAtRef = useRef(Date.now());
  const restModeRef = useRef(false);
  const pointerRecordsRef = useRef<WebsiteOrbPointerRecord[]>([]);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<BlobPart[]>([]);
  const recordingStreamRef = useRef<MediaStream | null>(null);
  const recordingStopTimerRef = useRef<number | null>(null);
  const recordingCancelledRef = useRef(false);
  const speechAudioRef = useRef<HTMLAudioElement | null>(null);
  const latencyAudioRef = useRef<HTMLAudioElement | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const speechSourceRef = useRef<AudioBufferSourceNode | null>(null);
  const audioUnlockedRef = useRef(false);
  const statusTimerRef = useRef<number | null>(null);
  const avoidUntilRef = useRef(0);
  const voiceRequestInFlightRef = useRef(false);
  const activeVoiceAbortControllerRef = useRef<AbortController | null>(null);
  const voiceTurnIdRef = useRef(0);
  const recordingMonitorTimerRef = useRef<number | null>(null);
  const recordingStartedAtRef = useRef(0);
  const speechDetectedRef = useRef(false);
  const silenceStartedAtRef = useRef<number | null>(null);
  const speakerBoostRef = useRef(false);
  const startupAutoStartedRef = useRef(false);
  const pageCapsuleRef = useRef<unknown>(null);
  const pointerTimerRef = useRef<number | null>(null);
  const [pulse, setPulse] = useState<PulseState>(null);
  const [voiceState, setVoiceState] = useState<OrbVoiceState>("idle");
  const [statusVisible, setStatusVisible] = useState(false);
  const [statusTitle, setStatusTitle] = useState("ORB online");
  const [statusLine, setStatusLine] = useState("Tap the ORB to speak.");
  const [speakerBoost, setSpeakerBoost] = useState(false);
  const [lastGuidedTarget, setLastGuidedTarget] = useState<string | null>(null);
  const [isResting, setIsResting] = useState(false);
  const [pointerBloom, setPointerBloom] = useState<{
    targetId: string;
    label: string;
    left: number;
    top: number;
    width: number;
    height: number;
    originAngle: number;
  } | null>(null);

 const bounds = useCallback(() => {
  const sidebar = document.querySelector<HTMLElement>("aside");
  let minX = EDGE;

  if (sidebar) {
    const rect = sidebar.getBoundingClientRect();
    const style = window.getComputedStyle(sidebar);

    const blocksLeftEdge =
      style.display !== "none" &&
      style.visibility !== "hidden" &&
      rect.width > 0 &&
      rect.left <= EDGE &&
      rect.right > EDGE;

    if (blocksLeftEdge) {
      minX = Math.ceil(rect.right) + EDGE;
    }
  }

  const minY = HEADER_SAFE + EDGE;

  return {
    minX,
    minY,
    maxX: Math.max(minX, window.innerWidth - size - EDGE),
    maxY: Math.max(minY, window.innerHeight - size - EDGE),
  };
}, [size]);
  const clampPosition = useCallback((x: number, y: number) => {
    const { minX, minY, maxX, maxY } = bounds();

    return {
      x: Math.max(minX, Math.min(x, maxX)),
      y: Math.max(minY, Math.min(y, maxY)),
    };
  }, [bounds]);

  const bumpWorldStateSequence = useCallback(() => {
    worldStateSequenceRef.current += 1;
  }, []);

  const markVisitorActivity = useCallback(() => {
    lastActivityAtRef.current = Date.now();
    if (restModeRef.current) {
      restModeRef.current = false;
      setIsResting(false);
      avoidUntilRef.current = Date.now() + 900;
    }
  }, []);

  const upperRightRestDestination = useCallback(() => {
    const { maxX, minY } = bounds();
    return clampPosition(maxX, minY + Math.max(16, size * 0.08));
  }, [bounds, clampPosition, size]);

 const nextDestination = useCallback(() => {
  const current = positionRef.current;
  const { minX, minY, maxX, maxY } = bounds();

  const minimumTravel = Math.max(70, size * 0.38);
  const maximumTravel = Math.max(
    minimumTravel + 30,
    Math.min(180, window.innerWidth * 0.12)
  );

  const forbiddenWidth = Math.max(220, size * 1.35);
  const forbiddenHeight = Math.max(220, size * 1.35);

  for (let attempt = 0; attempt < 18; attempt += 1) {
    const turnAmount = (Math.random() - 0.5) * 1.25;
    const heading = idleHeadingRef.current + turnAmount;
    const distance =
      minimumTravel + Math.random() * (maximumTravel - minimumTravel);

    const candidate = clampPosition(
      current.x + Math.cos(heading) * distance,
      current.y + Math.sin(heading) * distance
    );

    const insideBottomRightRestZone =
      candidate.x >= maxX - forbiddenWidth &&
      candidate.y >= maxY - forbiddenHeight;

    const actualTravel = Math.hypot(
      candidate.x - current.x,
      candidate.y - current.y
    );

    if (!insideBottomRightRestZone && actualTravel >= minimumTravel * 0.7) {
      idleHeadingRef.current = heading;
      return candidate;
    }
  }

  const centerHeading = Math.atan2(
    minY + (maxY - minY) * 0.48 - current.y,
    minX + (maxX - minX) * 0.52 - current.x
  );

  idleHeadingRef.current = centerHeading;

  return clampPosition(
    current.x + Math.cos(centerHeading) * minimumTravel,
    current.y + Math.sin(centerHeading) * minimumTravel
  );
}, [bounds, clampPosition, size]);

  const findPointerRecordForIntent = useCallback((intentText: string) => {
    const query = normalizeIntentText(intentText);
    const queryTokens = new Set(query.split(" ").filter((token) => token.length > 2));
    if (!queryTokens.size) return null;
    const currentRoute = routeForUrl(window.location.href);
    let best: { record: WebsiteOrbPointerRecord; score: number } | null = null;

    for (const record of pointerRecordsRef.current) {
      if (routeForUrl(record.page_route) !== currentRoute) continue;
      const candidates = [
        record.meaning || "",
        ...(record.direct_aliases || []),
        ...(record.intent_aliases || []),
        ...(record.topic_aliases || []),
      ].map(normalizeIntentText);
      const recordTokens = new Set(candidates.join(" ").split(" ").filter((token) => token.length > 2));
      const overlap = [...queryTokens].filter((token) => recordTokens.has(token)).length;
      const confidence = typeof record.confidence === "number" ? record.confidence : 0.7;
      const actionBonus = ["nav", "button", "price_card", "form_field"].includes(record.target_type)
        ? 0.14
        : 0;
      const score =
        (overlap / Math.max(1, Math.min(queryTokens.size, recordTokens.size))) * confidence +
        actionBonus;
      if (score >= 0.34 && (!best || score > best.score)) best = { record, score };
    }
    return best?.record || null;
  }, []);

  const guideToPointerTarget = useCallback(async (intentText: string) => {
    markVisitorActivity();
    const record = findPointerRecordForIntent(intentText);
    if (!record) return false;

    const movementController = movementControllerRef.current;
    if (!movementController) return false;

    const command: RobotCommand = {
      commandId: `orb-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
      actionType: "NAVIGATE_AND_ILLUMINATE",
      targetId: record.target_id,
      intent: "Guide",
      urgency: "normal",
      approachBehavior: "decelerate_on_arrive",
      endEffector: {
        type: "PING_LIGHT",
        duration: "standard",
        intensity: "medium",
      },
      reason: intentText.slice(0, 240),
      worldStateSequence: worldStateSequenceRef.current,
    };

    const movement = movementController.beginMovement({
      command,
      pointerRecord: record,
      currentWorldStateSequence: worldStateSequenceRef.current,
      onTelemetry: (event) => {
        if (process.env.NODE_ENV !== "production") {
          console.info("[orb-robotics]", event);
        }
      },
    });

    if (!movement.ok) return false;

    let activeRect = movement.targetRect;
    const targetAlreadyVisible =
      activeRect.top >= 0 &&
      activeRect.left >= 0 &&
      activeRect.bottom <= window.innerHeight &&
      activeRect.right <= window.innerWidth;

    if (!targetAlreadyVisible) {
      movement.targetElement.scrollIntoView({ behavior: "smooth", block: "center", inline: "center" });
      await wait(650);
      bumpWorldStateSequence();
      const refreshed = movement.refreshTarget();
      if (!refreshed) {
        movement.cancel("target_lost_after_scroll");
        return false;
      }
      activeRect = refreshed;
    }

    const latestGoal = movement.getLatestGoal();
    const targetCenterX = latestGoal.normalizedX * window.innerWidth;
    const targetCenterY = latestGoal.normalizedY * window.innerHeight;
    const side = targetCenterX < window.innerWidth / 2 ? 1 : -1;
    const destination = clampPosition(
      targetCenterX + side * Math.max(84, size * 0.62) - size / 2,
      targetCenterY - size / 2,
    );
    const current = positionRef.current;
    const distance = Math.hypot(destination.x - current.x, destination.y - current.y);
    avoidUntilRef.current = Date.now() + 16000;
    move.stop();
    await move.start({
      x: destination.x,
      y: destination.y,
      transition: {
        duration: Math.max(5.5, Math.min(12, distance / 75)),
        ease: [0.37, 0, 0.22, 1],
      },
    });
    positionRef.current = destination;
    if (!activeRef.current) {
      movement.cancel("orb_unmounted");
      return false;
    }

    const finalRect = movement.refreshTarget();
    if (!finalRect) {
      movement.cancel("target_lost_before_arrival");
      return false;
    }
    const finalTargetX = finalRect.left + finalRect.width / 2;
    const finalTargetY = finalRect.top + finalRect.height / 2;
    const orbCenterX = destination.x + size / 2;
    const orbCenterY = destination.y + size / 2;
    movement.complete();
    setLastGuidedTarget(record.target_id);

    setPointerBloom({
      targetId: record.target_id,
      label: (record.meaning || record.target_type || "Guided target").replace(/^[^:]+:\s*/, ""),
      left: Math.max(4, finalRect.left - 10),
      top: Math.max(4, finalRect.top - 10),
      width: finalRect.width + 20,
      height: finalRect.height + 20,
      originAngle: Math.atan2(finalTargetY - orbCenterY, finalTargetX - orbCenterX) * 180 / Math.PI,
    });
    if (pointerTimerRef.current) window.clearTimeout(pointerTimerRef.current);
    pointerTimerRef.current = window.setTimeout(() => setPointerBloom(null), 2600);
    return true;
  }, [bumpWorldStateSequence, clampPosition, findPointerRecordForIntent, markVisitorActivity, move, size]);

  const playPulse = useCallback(async (kind: PulseKind, duration: number) => {
    const visibleDuration = Math.max(duration, kind === "ripple" ? 1150 : kind === "flare" ? 1450 : 2100);

    setPulse({
      id: Date.now() + Math.floor(Math.random() * 9999),
      kind,
    });

    await wait(visibleDuration);

    if (activeRef.current) {
      setPulse(null);
    }
  }, []);

  const playLocalPresence = useCallback(async () => {
    await presence.start({
      x: [0, 3, -2, 1, 0],
      y: [0, -4, 2, -1, 0],
      rotate: [0, 1.2, -0.8, 0],
      transition: {
        duration: 5 + Math.random() * 4,
        ease: "easeInOut",
      },
    });
  }, [presence]);

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
    speechAudioRef.current = audio;
    void audio.play().catch(() => undefined);
  }, []);

  const playLatencyFiller = useCallback(() => {
    if (!audioUnlockedRef.current) return;

    const src = LATENCY_FILLER_PATHS[Math.floor(Math.random() * LATENCY_FILLER_PATHS.length)];
    if (latencyAudioRef.current) {
      latencyAudioRef.current.pause();
      latencyAudioRef.current = null;
    }

    const audio = new Audio(src);
    audio.volume = speakerBoostRef.current ? 1 : 0.72;
    latencyAudioRef.current = audio;
    audio.onended = () => {
      if (latencyAudioRef.current === audio) {
        latencyAudioRef.current = null;
      }
    };
    audio.onerror = () => {
      if (latencyAudioRef.current === audio) {
        latencyAudioRef.current = null;
      }
    };
    void audio.play().catch(() => {
      if (latencyAudioRef.current === audio) {
        latencyAudioRef.current = null;
      }
    });
  }, []);

  const playDecodedSpeech = useCallback(async (audioUrl: string) => {
    const AudioContextCtor = (window as any).AudioContext || (window as any).webkitAudioContext;
    if (!AudioContextCtor) {
      throw new Error("AudioContext unavailable");
    }

    const context: AudioContext = audioContextRef.current || new AudioContextCtor();
    audioContextRef.current = context;
    await context.resume?.();

    if (speechSourceRef.current) {
      try {
        speechSourceRef.current.stop();
      } catch {
        // Source may already have ended.
      }
      speechSourceRef.current = null;
    }

    const response = await fetch(api.orbMediaUrl(audioUrl), { cache: "force-cache" });
    if (!response.ok) {
      throw new Error("Speech audio unavailable");
    }

    const buffer = await context.decodeAudioData(await response.arrayBuffer());
    const source = context.createBufferSource();
    const gain = context.createGain();
    source.buffer = buffer;
    gain.gain.value = speakerBoostRef.current ? 1.85 : 1;
    source.connect(gain);
    gain.connect(context.destination);
    speechSourceRef.current = source;

    await new Promise<void>((resolve, reject) => {
      source.onended = () => {
        if (speechSourceRef.current === source) {
          speechSourceRef.current = null;
        }
        resolve();
      };
      try {
        source.start();
      } catch (error) {
        reject(error);
      }
    });
  }, []);

  const playStageScreech = useCallback(() => {
    const AudioContextCtor = (window as any).AudioContext || (window as any).webkitAudioContext;
    if (!AudioContextCtor) return;

    const context = audioContextRef.current || new AudioContextCtor();
    audioContextRef.current = context;
    void context.resume?.();

    const duration = 0.58;
    const sampleRate = context.sampleRate;
    const buffer = context.createBuffer(1, Math.floor(sampleRate * duration), sampleRate);
    const data = buffer.getChannelData(0);

    for (let index = 0; index < data.length; index += 1) {
      const progress = index / data.length;
      const scrape = (Math.random() * 2 - 1) * (1 - progress);
      const squeal = Math.sin(progress * progress * 2300) * 0.34;
      data[index] = (scrape * 0.42 + squeal) * Math.sin(progress * Math.PI);
    }

    const source = context.createBufferSource();
    const filter = context.createBiquadFilter();
    const gain = context.createGain();

    source.buffer = buffer;
    filter.type = "bandpass";
    filter.frequency.setValueAtTime(920, context.currentTime);
    filter.frequency.exponentialRampToValueAtTime(2400, context.currentTime + duration * 0.54);
    filter.Q.value = 6.5;
    gain.gain.setValueAtTime(0.0001, context.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.09, context.currentTime + 0.04);
    gain.gain.exponentialRampToValueAtTime(0.0001, context.currentTime + duration);

    source.connect(filter);
    filter.connect(gain);
    gain.connect(context.destination);
    source.start();
    source.stop(context.currentTime + duration);
  }, []);

  const playListeningAckTone = useCallback(() => {
    const AudioContextCtor = (window as any).AudioContext || (window as any).webkitAudioContext;
    if (!AudioContextCtor) return;

    const context = audioContextRef.current || new AudioContextCtor();
    audioContextRef.current = context;
    void context.resume?.();

    const oscillator = context.createOscillator();
    const gain = context.createGain();
    oscillator.type = "sine";
    oscillator.frequency.setValueAtTime(440, context.currentTime);
    oscillator.frequency.exponentialRampToValueAtTime(660, context.currentTime + 0.08);
    gain.gain.setValueAtTime(0.0001, context.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.06, context.currentTime + 0.025);
    gain.gain.exponentialRampToValueAtTime(0.0001, context.currentTime + 0.18);
    oscillator.connect(gain);
    gain.connect(context.destination);
    oscillator.start();
    oscillator.stop(context.currentTime + 0.2);
  }, []);

  const logVoice = useCallback((message: string, turnId: number) => {
    if (process.env.NODE_ENV !== "production") {
      console.info(`[ORB voice] ${message} ${turnId}`);
    }
  }, []);

  const stopRecordingMonitor = useCallback(() => {
    if (recordingMonitorTimerRef.current) {
      window.clearInterval(recordingMonitorTimerRef.current);
      recordingMonitorTimerRef.current = null;
    }
  }, []);

  const freezeOrbInPlace = useCallback((holdMs = 4200) => {
    avoidUntilRef.current = Date.now() + holdMs;
    move.stop();
    presence.stop();
  }, [move, presence]);

  const speak = useCallback(async (
    text: string,
    audioUrl?: string | null,
    provider?: string | null,
    options: { showTranscript?: boolean } = {},
  ) => {
    const showTranscript = options.showTranscript !== false;
    if (showTranscript) {
      showStatus();
    } else {
      setStatusVisible(false);
    }
    setStatusLine(showTranscript ? text : "Speaking.");
    setVoiceState("speaking");
    freezeOrbInPlace(4200);

    if (speechAudioRef.current) {
      speechAudioRef.current.pause();
    }
    if (latencyAudioRef.current) {
      latencyAudioRef.current.pause();
      latencyAudioRef.current = null;
    }

    if (!audioUrl) {
      setStatusTitle("Voice unavailable");
      setStatusLine(VOICE_UNAVAILABLE_MESSAGE);
      setVoiceState("idle");
      showStatus(3600);
      return;
    }

    try {
      setStatusTitle("Voice response");
      if (speakerBoostRef.current) {
        await playDecodedSpeech(audioUrl);
        setVoiceState("idle");
        showStatus(1400);
        return;
      }
      const audio = speechAudioRef.current || new Audio();
      audio.pause();
      audio.muted = false;
      audio.volume = speakerBoostRef.current ? 1 : 0.86;
      audio.src = api.orbMediaUrl(audioUrl);
      speechAudioRef.current = audio;
      await new Promise<void>((resolve, reject) => {
        audio.onended = () => {
          if (speechAudioRef.current === audio) {
            speechAudioRef.current = null;
          }
          setVoiceState("idle");
          showStatus(1400);
          resolve();
        };
        audio.onerror = () => {
          if (speechAudioRef.current === audio) {
            speechAudioRef.current = null;
          }
          setStatusTitle("Voice unavailable");
          setStatusLine(VOICE_UNAVAILABLE_MESSAGE);
          setVoiceState("idle");
          showStatus(3600);
          reject(new Error("Audio playback failed"));
        };
        audio.play().catch(reject);
      });
    } catch {
      setStatusTitle("Voice unavailable");
      setStatusLine(VOICE_UNAVAILABLE_MESSAGE);
      setVoiceState("idle");
      showStatus(3600);
    }
  }, [freezeOrbInPlace, playDecodedSpeech, showStatus]);

  const speakWithGeneratedAudio = useCallback(async (text: string, audioUrl?: string | null, provider?: string | null) => {
    setStatusTitle("Preparing voice");
    setStatusLine(text);
    setVoiceState("speaking");
    showStatus();
    freezeOrbInPlace(4200);

    if (audioUrl) {
      await speak(text, audioUrl, provider);
      return;
    }

    setStatusTitle("Voice unavailable");
    setStatusLine(VOICE_UNAVAILABLE_MESSAGE);
    setVoiceState("idle");
    showStatus(5200);
  }, [freezeOrbInPlace, showStatus, speak]);

  const speakRecovery = useCallback(async (text: string) => {
    setStatusLine(text);
    setStatusTitle("Voice unavailable");
    setVoiceState("idle");
    showStatus(3600);
  }, [showStatus]);

  const processRecordedOrbAudio = useCallback(async (audio: Blob) => {
    markVisitorActivity();
    if (voiceRequestInFlightRef.current) return;
    const turnId = voiceTurnIdRef.current;
    const controller = new AbortController();
    activeVoiceAbortControllerRef.current = controller;
    voiceRequestInFlightRef.current = true;

    if (!audio.size) {
      setStatusTitle("Voice unavailable");
      setStatusLine("I did not hear enough audio. Tap the ORB and speak after the tone.");
      setVoiceState("idle");
      showStatus(3200);
      voiceRequestInFlightRef.current = false;
      activeVoiceAbortControllerRef.current = null;
      return;
    }

    setStatusTitle("Thinking");
    setStatusLine("Preparing a response.");
    setVoiceState("speaking");
    showStatus();
    freezeOrbInPlace(4200);
    playLatencyFiller();

    try {
      logVoice("website-voice", turnId);
      const result = await api.websiteOrbVoice(audio, controller.signal, {
        target_url: window.location.href,
      });
      setStatusTitle("Voice response");
      setStatusLine(result.spoken_output);
      if (result.tts_error && !result.tts_audio_url) {
        setStatusTitle("Voice unavailable");
        setStatusLine(VOICE_UNAVAILABLE_MESSAGE);
      }
      void guideToPointerTarget(`${result.transcript} ${result.spoken_output}`);
      logVoice("playback", turnId);
      await speakWithGeneratedAudio(result.spoken_output, result.tts_audio_url, result.tts_provider);
    } catch (error) {
      if ((error as Error)?.name === "AbortError") return;
      setStatusTitle("ORB route unavailable");
      speakRecovery("I am reconnecting to my response service. Please try again in a moment.");
    } finally {
      if (activeVoiceAbortControllerRef.current === controller) {
        activeVoiceAbortControllerRef.current = null;
      }
      voiceRequestInFlightRef.current = false;
      setVoiceState("idle");
      logVoice("finalized", turnId);
    }
  }, [freezeOrbInPlace, guideToPointerTarget, logVoice, markVisitorActivity, playLatencyFiller, showStatus, speakRecovery, speakWithGeneratedAudio]);

  const stopOrbRecording = useCallback((cancel = false) => {
    if (recordingStopTimerRef.current) {
      window.clearTimeout(recordingStopTimerRef.current);
      recordingStopTimerRef.current = null;
    }
    stopRecordingMonitor();

    recordingCancelledRef.current = cancel;
    const recorder = recorderRef.current;
    if (recorder && recorder.state !== "inactive") {
      recorder.stop();
      return;
    }

    recordingStreamRef.current?.getTracks().forEach((track) => track.stop());
    recordingStreamRef.current = null;
    recorderRef.current = null;
    if (cancel) {
      audioChunksRef.current = [];
      setStatusTitle("Listening cancelled");
      setStatusLine("Tap the ORB when you want to speak.");
      setVoiceState("idle");
      showStatus(1800);
    }
  }, [showStatus, stopRecordingMonitor]);

  const monitorRecordingSilence = useCallback((stream: MediaStream, recorder: MediaRecorder) => {
    const AudioContextCtor = (window as any).AudioContext || (window as any).webkitAudioContext;
    if (!AudioContextCtor) {
      return;
    }

    const context: AudioContext = audioContextRef.current || new AudioContextCtor();
    audioContextRef.current = context;
    void context.resume?.();

    const source = context.createMediaStreamSource(stream);
    const analyser = context.createAnalyser();
    analyser.fftSize = 1024;
    source.connect(analyser);
    const samples = new Float32Array(analyser.fftSize);

    recordingStartedAtRef.current = Date.now();
    speechDetectedRef.current = false;
    silenceStartedAtRef.current = null;

    stopRecordingMonitor();
    recordingMonitorTimerRef.current = window.setInterval(() => {
      if (recorder.state === "inactive") {
        stopRecordingMonitor();
        return;
      }

      const elapsed = Date.now() - recordingStartedAtRef.current;
      analyser.getFloatTimeDomainData(samples);
      let sum = 0;
      for (let index = 0; index < samples.length; index += 1) {
        sum += samples[index] * samples[index];
      }
      const rms = Math.sqrt(sum / samples.length);

      if (rms >= SPEECH_LEVEL_THRESHOLD) {
        speechDetectedRef.current = true;
        silenceStartedAtRef.current = null;
        return;
      }

      if (elapsed >= ABSOLUTE_RECORDING_LIMIT_MS) {
        stopOrbRecording();
        return;
      }

      if (!speechDetectedRef.current || elapsed < MIN_RECORDING_MS) {
        return;
      }

      if (silenceStartedAtRef.current == null) {
        silenceStartedAtRef.current = Date.now();
        return;
      }

      if (Date.now() - silenceStartedAtRef.current >= END_SILENCE_MS) {
        stopOrbRecording();
      }
    }, 120);
  }, [stopOrbRecording, stopRecordingMonitor]);

  const startOrbRecording = useCallback(async () => {
    unlockAudio();
    if (voiceRequestInFlightRef.current || voiceState === "speaking") return;

    if (recorderRef.current) {
      stopOrbRecording(true);
      return;
    }

    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      setStatusTitle("Voice unavailable");
      setStatusLine("Microphone recording is unavailable in this browser.");
      setVoiceState("idle");
      showStatus(2600);
      return;
    }

    try {
      const turnId = voiceTurnIdRef.current + 1;
      voiceTurnIdRef.current = turnId;
      logVoice("start turn", turnId);
      activeVoiceAbortControllerRef.current?.abort();

      freezeOrbInPlace(ABSOLUTE_RECORDING_LIMIT_MS + 1800);
      setStatusTitle("Listening");
      setStatusLine("Speak now.");
      setVoiceState("listening");
      showStatus();
      void playPulse("ripple", 1150);

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      playListeningAckTone();

      recordingStreamRef.current = stream;
      audioChunksRef.current = [];
      recordingCancelledRef.current = false;

      const recorderOptions =
        MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
          ? { mimeType: "audio/webm;codecs=opus" }
          : MediaRecorder.isTypeSupported("audio/webm")
          ? { mimeType: "audio/webm" }
          : undefined;
      const recorder = new MediaRecorder(stream, recorderOptions);
      recorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      recorder.onstop = () => {
        const cancelled = recordingCancelledRef.current;
        recordingCancelledRef.current = false;
        const audio = new Blob(audioChunksRef.current, {
          type: recorder.mimeType || "audio/webm",
        });
        audioChunksRef.current = [];
        recorderRef.current = null;
        stream.getTracks().forEach((track) => track.stop());
        if (recordingStreamRef.current === stream) {
          recordingStreamRef.current = null;
        }
        if (cancelled) {
          setStatusTitle("Listening cancelled");
          setStatusLine("Tap the ORB when you want to speak.");
          setVoiceState("idle");
          showStatus(1800);
          return;
        }
        void processRecordedOrbAudio(audio);
      };

      setStatusTitle("Listening");
      setStatusLine("Speak now.");
      setVoiceState("listening");
      showStatus();
      void playPulse("ripple", 1150);
      recorder.start();
      monitorRecordingSilence(stream, recorder);
    } catch {
      setStatusTitle("Voice unavailable");
      setStatusLine("Microphone permission is needed for voice.");
      setVoiceState("idle");
      showStatus(3600);
    }
  }, [freezeOrbInPlace, logVoice, monitorRecordingSilence, playListeningAckTone, playPulse, processRecordedOrbAudio, showStatus, stopOrbRecording, unlockAudio, voiceState]);

  const interruptOrbSpeech = useCallback(() => {
    activeVoiceAbortControllerRef.current?.abort();
    activeVoiceAbortControllerRef.current = null;
    voiceRequestInFlightRef.current = false;
    if (speechAudioRef.current) {
      speechAudioRef.current.pause();
      speechAudioRef.current.currentTime = 0;
      speechAudioRef.current = null;
    }
    if (speechSourceRef.current) {
      try {
        speechSourceRef.current.stop();
      } catch {
        // Source may already have ended.
      }
      speechSourceRef.current = null;
    }
    if (latencyAudioRef.current) {
      latencyAudioRef.current.pause();
      latencyAudioRef.current = null;
    }
    setStatusTitle("Interrupted");
    setStatusLine("Tap the ORB when you want to speak.");
    setVoiceState("idle");
    showStatus(1600);
    avoidUntilRef.current = Date.now() + 900;
  }, [showStatus]);

  const requestStartupMicrophonePermission = useCallback(async () => {
    if (!navigator.mediaDevices?.getUserMedia) {
      setStatusTitle("Voice unavailable");
      setStatusLine("Microphone recording is unavailable in this browser.");
      showStatus(4200);
      return false;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      stream.getTracks().forEach((track) => track.stop());
      return true;
    } catch {
      setStatusTitle("Microphone blocked");
      setStatusLine("Allow microphone access in the browser to talk with Weaver.");
      showStatus(5200);
      return false;
    }
  }, [showStatus]);

  const runStartupVoiceSequence = useCallback(async () => {
    if (startupAutoStartedRef.current || onboardingSafeMode) return;
    startupAutoStartedRef.current = true;
    unlockAudio();
    const greeting = startupGreetingText();
    const micReadyPromise = requestStartupMicrophonePermission();
    try {
      const tts = await api.websiteOrbTts(greeting);
      await speak(greeting, tts.tts_audio_url, tts.tts_provider);
    } catch {
      speakRecovery(greeting);
    }

    const micReady = await micReadyPromise;
    if (micReady && activeRef.current) {
      window.setTimeout(() => {
        if (!activeRef.current || voiceRequestInFlightRef.current) return;
        void startOrbRecording();
      }, 420);
    }
  }, [onboardingSafeMode, requestStartupMicrophonePermission, speak, speakRecovery, startOrbRecording, unlockAudio]);

  const handleOrbClick = useCallback(() => {
    markVisitorActivity();
    if (voiceState === "speaking") {
      interruptOrbSpeech();
      return;
    }

    if (recorderRef.current) {
      stopOrbRecording(true);
      return;
    }

    void startOrbRecording();
  }, [interruptOrbSpeech, markVisitorActivity, startOrbRecording, stopOrbRecording, voiceState]);

  const toggleSpeakerBoost = useCallback(() => {
    markVisitorActivity();
    const next = !speakerBoostRef.current;
    speakerBoostRef.current = next;
    setSpeakerBoost(next);
    setStatusTitle(next ? "Speaker boost on" : "Speaker boost off");
    setStatusLine(next ? "Voice playback will be louder." : "Voice playback is back to normal.");
    showStatus(1800);
    if (speechAudioRef.current) {
      speechAudioRef.current.volume = next ? 1 : 0.86;
    }
    if (latencyAudioRef.current) {
      latencyAudioRef.current.volume = next ? 1 : 0.72;
    }
    unlockAudio();
  }, [markVisitorActivity, showStatus, unlockAudio]);

  useEffect(() => {
    movementControllerRef.current = new OrbRoboticsMovementController();
    return () => {
      movementControllerRef.current?.dispose();
      movementControllerRef.current = null;
    };
  }, []);

  useEffect(() => {
    const activityHandler = () => markVisitorActivity();
    const sequenceHandler = () => bumpWorldStateSequence();

    window.addEventListener("pointerdown", activityHandler, { passive: true });
    window.addEventListener("touchstart", activityHandler, { passive: true });
    window.addEventListener("keydown", activityHandler);
    window.addEventListener("scroll", activityHandler, { passive: true });

    window.addEventListener("resize", sequenceHandler);
    window.addEventListener("popstate", sequenceHandler);
    window.addEventListener("hashchange", sequenceHandler);

    return () => {
      window.removeEventListener("pointerdown", activityHandler);
      window.removeEventListener("touchstart", activityHandler);
      window.removeEventListener("keydown", activityHandler);
      window.removeEventListener("scroll", activityHandler);

      window.removeEventListener("resize", sequenceHandler);
      window.removeEventListener("popstate", sequenceHandler);
      window.removeEventListener("hashchange", sequenceHandler);
    };
  }, [bumpWorldStateSequence, markVisitorActivity]);

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
    const controller = new AbortController();
    const pointerDomain = ["127.0.0.1", "localhost"].includes(window.location.hostname)
      ? "orbweaver.spruked.com"
      : window.location.hostname;
    api.websiteOrbPointerMap(pointerDomain, controller.signal)
      .then((pointerMap) => {
        pointerRecordsRef.current = Array.isArray(pointerMap.records) ? pointerMap.records : [];
        bumpWorldStateSequence();
        if (process.env.NODE_ENV !== "production") {
          const demoQuery = new URLSearchParams(window.location.search).get("orbPointerDemo");
          if (demoQuery) {
            window.setTimeout(() => void guideToPointerTarget(demoQuery), 1200);
          }
        }
      })
      .catch(() => {
        pointerRecordsRef.current = [];
        bumpWorldStateSequence();
      });
    return () => controller.abort();
  }, [bumpWorldStateSequence, guideToPointerTarget]);

  useEffect(() => {
    let cancelled = false;
    let lastUrl = "";

    const preloadCapsule = () => {
      const currentUrl = window.location.href;
      if (currentUrl === lastUrl) return;
      lastUrl = currentUrl;
      api.websiteOrbPageCapsule(currentUrl)
        .then((capsule) => {
          if (cancelled) return;
          pageCapsuleRef.current = capsule;
        })
        .catch(() => {
          if (cancelled) return;
          pageCapsuleRef.current = null;
        });
    };

    preloadCapsule();
    const interval = window.setInterval(preloadCapsule, 900);
    window.addEventListener("popstate", preloadCapsule);
    window.addEventListener("hashchange", preloadCapsule);

    return () => {
      cancelled = true;
      window.clearInterval(interval);
      window.removeEventListener("popstate", preloadCapsule);
      window.removeEventListener("hashchange", preloadCapsule);
    };
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
        surge.set({ scale: 0.26, opacity: 0, x: window.innerWidth * 0.42, rotate: 10 });
        setPulse({ id: Date.now(), kind: "intro" });
        playStageScreech();

        await surge.start({
          x: [window.innerWidth * 0.42, -28, 10, 0],
          scale: [0.26, 1.78, 0.88, 1.04, 1],
          opacity: [0, 1, 1, 1, 1],
          rotate: [10, -6, 3, 0],
          transition: {
            duration: 2.65,
            ease: [0.15, 0.9, 0.18, 1],
            times: [0, 0.54, 0.74, 0.9, 1],
          },
        });

        if (!activeRef.current) return;

        window.sessionStorage.setItem("orbweaver-intro-played", "1");
        setPulse(null);
        void runStartupVoiceSequence();
      } else {
        surge.set({ scale: 1, opacity: 1, x: 0, rotate: 0 });
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
        const inactiveForMs = Date.now() - lastActivityAtRef.current;
        const shouldEnterRest =
          inactiveForMs >= REST_AFTER_INACTIVITY_MS &&
          voiceState === "idle" &&
          !recorderRef.current;

        if (shouldEnterRest) {
          if (!restModeRef.current) {
            restModeRef.current = true;
            setIsResting(true);
            const restDestination = upperRightRestDestination();
            await move.start({
              x: restDestination.x,
              y: restDestination.y,
              transition: {
                duration: 1.8,
                ease: [0.37, 0, 0.22, 1],
              },
            });
            positionRef.current = restDestination;
          }
          await wait(280);
          continue;
        }

        if (restModeRef.current) {
          restModeRef.current = false;
          setIsResting(false);
        }

        if (Date.now() < avoidUntilRef.current) {
          await wait(160);
          continue;
        }

        const destination = nextDestination();

        void playLocalPresence();

        if (!activeRef.current) break;

        await move.start({
          x: destination.x,
          y: destination.y,
          transition: {
            duration:
              (IDLE_TRAVEL_MIN_MS + Math.random() * (IDLE_TRAVEL_MAX_MS - IDLE_TRAVEL_MIN_MS)) /
              1000,
            ease: [0.37, 0, 0.22, 1],
          },
        });

        if (!activeRef.current) break;

        positionRef.current = destination;

        void playLocalPresence();

        if (!activeRef.current) break;

        await wait(IDLE_PAUSE_MIN_MS + Math.random() * (IDLE_PAUSE_MAX_MS - IDLE_PAUSE_MIN_MS));
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

    window.addEventListener("resize", handleResize);

    return () => {
      activeRef.current = false;
      restModeRef.current = false;
      if (pointerTimerRef.current) {
        window.clearTimeout(pointerTimerRef.current);
      }
      window.removeEventListener("resize", handleResize);
    };
  }, [clampPosition, glow, move, nextDestination, playLocalPresence, playStageScreech, presence, runStartupVoiceSequence, size, stopRecordingMonitor, surge, upperRightRestDestination, voiceState]);

  // Voice resources are cancelled only when this ORB component unmounts.
  useEffect(() => {
    return () => {
      speechAudioRef.current?.pause();

      if (statusTimerRef.current) {
        window.clearTimeout(statusTimerRef.current);
      }

      if (recordingStopTimerRef.current) {
        window.clearTimeout(recordingStopTimerRef.current);
      }

      stopRecordingMonitor();
      activeVoiceAbortControllerRef.current?.abort();
      activeVoiceAbortControllerRef.current = null;
      voiceRequestInFlightRef.current = false;

      if (recorderRef.current && recorderRef.current.state !== "inactive") {
        recordingCancelledRef.current = true;
        recorderRef.current.stop();
      }

      recordingStreamRef.current?.getTracks().forEach((track) => track.stop());
    };
    // Intentionally unmount-only so voice requests survive state changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
      rings: 5,
      color: "rgba(91,200,230,",
      maxScale: 9.4,
      duration: 2.05,
    };
  };

  const visual = ringStyle();

  return (
    <>
    {pointerBloom && (
      <div
        className="ow-v2-pointer-bloom"
        data-orb-pointer-target={pointerBloom.targetId}
        aria-label={`Weaver is pointing to ${pointerBloom.label}`}
        style={{
          left: pointerBloom.left,
          top: pointerBloom.top,
          width: pointerBloom.width,
          height: pointerBloom.height,
        }}
      >
        <span />
      </div>
    )}
    <motion.div
      animate={move}
      className={`ow-v2-orb-position ${pointerBloom ? "is-pointing" : ""} ${onboardingSafeMode ? "onboarding-safe-mode" : ""} ${className}`}
      data-orb-last-guided-target={lastGuidedTarget || undefined}
      style={{
        position: "fixed",
        left: 0,
        top: 0,
        width: size,
        height: size,
        zIndex: ORB_OVERLAY_Z_INDEX,
        pointerEvents: "auto",
        opacity: isResting ? REST_ORB_OPACITY : ACTIVE_ORB_OPACITY,
        "--ow-pointer-angle": `${pointerBloom?.originAngle || 0}deg`,
      } as React.CSSProperties}
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
            <Orb
              size={size}
              state={voiceState}
              onClick={handleOrbClick}
            />
            <button
              type="button"
              className={`ow-v2-orb-speaker ${speakerBoost ? "active" : ""}`}
              onClick={toggleSpeakerBoost}
              aria-label={speakerBoost ? "Turn speaker boost off" : "Turn speaker boost on"}
              aria-pressed={speakerBoost}
              title={speakerBoost ? "Speaker boost on" : "Speaker boost"}
            >
              {speakerBoost ? <Volume2 size={17} /> : <VolumeX size={17} />}
            </button>
          </motion.div>
        </motion.div>
      </motion.div>
      {statusVisible && (
        <div className="ow-v2-orb-status" aria-live="polite" aria-label={statusTitle}>
          <span>{statusLine}</span>
        </div>
      )}
    </motion.div>
    </>
  );
};

export default AutonomousOrb;
