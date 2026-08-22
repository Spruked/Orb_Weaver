import React, { useCallback, useEffect, useRef, useState } from "react";
import { motion, useAnimationControls } from "framer-motion";
import { Volume2, VolumeX } from "lucide-react";
import { useLocation } from "react-router-dom";
import { Orb } from "./Orb";
import {
  api,
  type WebsiteOrbExperienceContext,
  type WebsiteOrbPointerRecord,
  type WebsiteOrbTtsResponse,
  type WebsiteOrbVoiceResponse,
} from "../services/api";
import {
  ACTIVE_ORB_PROJECT_CONTEXT_EVENT,
  ActiveOrbProjectContext,
  buildCustomerPageCapsuleUrl,
  getActiveOrbProjectContext,
} from "../orb/activeProjectContext";
import { OrbRoboticsMovementController } from "../orb/robotics/movementController";
import type { RobotCommand } from "../orb/robotics/robotMovement.types";
import { buildLidarGuidanceMap, Lidar2DMappingCoordinateCache } from "../orb/lidar_2d_mapping";
import {
  createPlaybackSettlement,
  type PlaybackSettlement,
  runBackendRecovery,
  shouldRearmVoice,
  shouldRunMountedStartupVoiceSequence,
} from "../orb/voiceLifecycle";

const wait = (ms: number) =>
  new Promise<void>((resolve) => window.setTimeout(resolve, ms));

const VOICE_UNAVAILABLE_MESSAGE = "Voice unavailable";
const POINTER_PING_AUDIO_PATH = "/orb/voice/pointer-ping.mp3";
const MORB_TRAVEL_AUDIO_PATH = "/orb/voice/travel-morb.mp3";
const MIN_RECORDING_MS = 700;
const END_SILENCE_MS = 2200;
const ABSOLUTE_RECORDING_LIMIT_MS = 22000;
const SPEECH_LEVEL_THRESHOLD = 0.018;
const LIDAR_DRIFT_THRESHOLD_PX = 12;
const ORB_SPEECH_PLAYBACK_RATE = 1.3;

const emitOrbRuntimeEvent = (phase: string, detail: Record<string, unknown> = {}) => {
  window.dispatchEvent(new CustomEvent("orbweaver:mounted-runtime", {
    detail: { phase, at: Date.now(), ...detail },
  }));
};

type PulseKind = "ripple" | "flare";
type FirstEncounterFlag =
  | "voice_ready"
  | "entrance_complete"
  | "communication_orientation_complete"
  | "understanding_complete"
  | "orientation_pointer_proof_complete"
  | "agency_complete"
  | "visitor_first_turn_complete"
  | "personal_relevance_complete"
  | "responsive_guidance_complete"
  | "relevant_continuation_complete"
  | "controller_handoff_complete";
type FirstEncounterState = Record<FirstEncounterFlag, boolean>;
type PointerWaltzPhase = "ACQUIRE" | "LAUNCH" | "TRAVEL" | "APPROACH" | "STANCE" | "POINT" | "PING" | "COMPLETE" | "DISSOLVE" | "RECOVERY";
type MorbWorkRole = "target" | "path" | "comparison" | "sequence" | "alternative" | "relationship";
type MorbPointerState = {
  targetId: string;
  role: MorbWorkRole;
  left: number;
  top: number;
  visible: boolean;
  pinging: boolean;
  dissolving: boolean;
  phase: PointerWaltzPhase;
};

type PulseState = {
  id: number;
  kind: PulseKind;
} | null;

type OrbVoiceState = "idle" | "listening" | "speaking";
type StartupVoicePreparation = {
  greeting: string;
  micReady: Promise<boolean>;
  tts: Promise<WebsiteOrbTtsResponse | null>;
};
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
const ACTIVE_ORB_OPACITY = 0.94;
const REST_ORB_OPACITY = 0.55;
const FIRST_ENCOUNTER_STORAGE_KEY = "orbweaver-first-encounter-state";
const STARTUP_GREETING_SESSION_KEY = "orbweaver-startup-greeting-played";
const LANDING_SPLASH_SESSION_KEY = "orbweaver-landing-splash-played";
const LANDING_SPLASH_COMPLETE_SESSION_KEY = "orbweaver-landing-splash-complete";
const STARTUP_GATE_COMPLETE_EVENT = "orbweaver:startup-gate-complete";
type StartupDiagnostics = {
  splash_state: "waiting" | "playing" | "complete" | "skipped_session_once";
  permission_state: "waiting" | "user_activated" | "requesting" | "ready" | "blocked";
  greeting_state: "waiting" | "preparing" | "playing" | "played" | "skipped_session_once" | "failed";
  audio_tts_state: "idle" | "requesting" | "ready" | "playing" | "played" | "failed";
  tts_voice: string;
  session_once_flag: boolean;
  orb_readiness_state: "mounting" | "waiting_for_gate" | "voice_ready" | "intro_playing" | "ready";
};
type RuntimeAnswerDiagnostics = NonNullable<WebsiteOrbVoiceResponse["resolution_diagnostics"]>;
const SUITE_LOGO_POINTER_RECORD: WebsiteOrbPointerRecord = {
  target_id: "orb-weaver-suite-logo",
  page_route: "/",
  target_type: "logo",
  meaning: "ORB Weaver suite logo",
  intent_aliases: ["orb weaver", "orb weaver suite", "suite logo"],
  direct_aliases: ["logo"],
  topic_aliases: ["suite"],
  content_fingerprint: "orb-weaver-suite-logo-v1",
  semantic_locator: '[data-orb-target="orb-weaver-suite-logo"]',
  confidence: 1,
  confidence_class: "VERIFIED",
  pointer_health: "OWNER_VERIFIED",
  runtime_policy: { may_point: true, requires_live_verification: true },
};
const EMPTY_FIRST_ENCOUNTER_STATE: FirstEncounterState = {
  voice_ready: false,
  entrance_complete: false,
  communication_orientation_complete: false,
  understanding_complete: false,
  orientation_pointer_proof_complete: false,
  agency_complete: false,
  visitor_first_turn_complete: false,
  personal_relevance_complete: false,
  responsive_guidance_complete: false,
  relevant_continuation_complete: false,
  controller_handoff_complete: false,
};
const MORB_SIZE = 50;
const MORB_HALF = MORB_SIZE / 2;
const MORB_REUSE_DISTANCE_PX = 250;
const ORB_TARGET_CLEARANCE_PX = 56;
const MORB_ROLE_STYLES: Record<MorbWorkRole, { primary: string; glow: string; shadow: string; skin: string }> = {
  target: {
    primary: "rgba(91, 200, 230, .96)",
    glow: "rgba(91, 200, 230, .34)",
    shadow: "rgba(91, 200, 230, .68)",
    skin: "/orb-morbs/purplemorb50px.png",
  },
  path: {
    primary: "rgba(45, 212, 255, .96)",
    glow: "rgba(45, 212, 255, .32)",
    shadow: "rgba(45, 212, 255, .68)",
    skin: "/orb-morbs/morbblackred.ico",
  },
  comparison: {
    primary: "rgba(250, 204, 21, .96)",
    glow: "rgba(250, 204, 21, .28)",
    shadow: "rgba(250, 204, 21, .62)",
    skin: "/orb-morbs/camoorb65px.png",
  },
  sequence: {
    primary: "rgba(168, 85, 247, .96)",
    glow: "rgba(168, 85, 247, .3)",
    shadow: "rgba(168, 85, 247, .62)",
    skin: "/orb-morbs/purplemorb50px.png",
  },
  alternative: {
    primary: "rgba(248, 113, 113, .96)",
    glow: "rgba(248, 113, 113, .28)",
    shadow: "rgba(248, 113, 113, .62)",
    skin: "/orb-morbs/morbblackred.ico",
  },
  relationship: {
    primary: "rgba(74, 222, 128, .96)",
    glow: "rgba(74, 222, 128, .28)",
    shadow: "rgba(74, 222, 128, .62)",
    skin: "/orb-morbs/camoorb65px.png",
  },
};
const normalizeIntentText = (value: string): string =>
  (value || "").replace(/\s+/g, " ").trim().toLowerCase();

const readFirstEncounterState = (): FirstEncounterState => {
  try {
    const stored = window.sessionStorage.getItem(FIRST_ENCOUNTER_STORAGE_KEY);
    if (!stored) return { ...EMPTY_FIRST_ENCOUNTER_STATE };
    return { ...EMPTY_FIRST_ENCOUNTER_STATE, ...JSON.parse(stored) };
  } catch {
    return { ...EMPTY_FIRST_ENCOUNTER_STATE };
  }
};

const inferMorbRole = (record: WebsiteOrbPointerRecord, intentText = ""): MorbWorkRole => {
  const targetType = normalizeIntentText(record.target_type || "");
  const combined = normalizeIntentText([
    intentText,
    record.target_id,
    record.meaning,
    targetType,
    ...(record.intent_aliases || []),
    ...(record.direct_aliases || []),
    ...(record.topic_aliases || []),
  ].filter(Boolean).join(" "));

  if (/\b(compare|comparison|versus|vs|different|difference|pricing|price|plan|package)\b/.test(combined)) return "comparison";
  if (/\b(step|sequence|first|second|third|next|then|after|before|timeline|stage)\b/.test(combined)) return "sequence";
  if (/\b(alternative|instead|also|option|either|another|otherwise)\b/.test(combined)) return "alternative";
  if (/\b(relationship|relate|connect|linked|between|depends|because|maps? to)\b/.test(combined)) return "relationship";
  if (["nav", "link", "download"].includes(targetType) || /\b(path|route|go|open|visit|navigate|journey)\b/.test(combined)) return "path";
  if (["faq_answer", "policy_line", "paragraph"].includes(targetType)) return "relationship";
  return "target";
};

const morbStyleVars = (role: MorbWorkRole): React.CSSProperties => {
  const style = MORB_ROLE_STYLES[role];
  return {
    "--ow-morb-primary": style.primary,
    "--ow-morb-glow": style.glow,
    "--ow-morb-shadow": style.shadow,
    "--ow-morb-skin": `url("${style.skin}")`,
  } as React.CSSProperties;
};

const routeForUrl = (value?: string | null): string => {
  if (!value) return "/";
  try {
    return new URL(value, window.location.origin).pathname.replace(/\/+$/, "") || "/";
  } catch {
    return "/";
  }
};

const isPublicLandingExperience = (): boolean =>
  window.location.pathname === "/" &&
  Boolean(document.getElementById("weaver-first-encounter"));

const startupGreetingText = (): string => {
  return "Hi, I'm Weaver. Welcome to ORB Weaver. I'm going to show you how I listen, understand this site, and guide with verified targets.";
};

const initialStartupDiagnostics = (): StartupDiagnostics => ({
  splash_state: window.sessionStorage.getItem(LANDING_SPLASH_COMPLETE_SESSION_KEY) === "1" ? "skipped_session_once" : "waiting",
  permission_state: "waiting",
  greeting_state: window.sessionStorage.getItem(STARTUP_GREETING_SESSION_KEY) === "1" ? "skipped_session_once" : "waiting",
  audio_tts_state: "idle",
  tts_voice: "OrbWeaver",
  session_once_flag: window.sessionStorage.getItem(STARTUP_GREETING_SESSION_KEY) === "1",
  orb_readiness_state: "mounting",
});

const startupDiagnosticsPanelEnabled = (): boolean => {
  if (process.env.NODE_ENV === "production" || !isPublicLandingExperience()) return false;
  const params = new URLSearchParams(window.location.search);
  return params.get("orbStartupDiagnostics") === "1";
};

export const AutonomousOrb: React.FC<Props> = ({
  size = 190,
  className = "",
}) => {
  const location = useLocation();
  const onboardingSafeMode = ['/signup', '/login'].includes(location.pathname);
  const move = useAnimationControls();
  const glow = useAnimationControls();
  const presence = useAnimationControls();
  const activeRef = useRef(true);
  const reducedMotionRef = useRef(false);
  const positionRef = useRef({ x: 0, y: 0 });
  const orbElementRef = useRef<HTMLDivElement | null>(null);
  const motionInterruptionSequenceRef = useRef(0);
  const idleHeadingRef = useRef(Math.random() * Math.PI * 2);
  const lastAutonomousDestinationRef = useRef<{ x: number; y: number } | null>(null);
  const lastAutonomousHeadingRef = useRef<number | null>(null);
  const movementControllerRef = useRef<OrbRoboticsMovementController | null>(null);
  const lidarCacheRef = useRef(Lidar2DMappingCoordinateCache.getInstance());
  const guidanceActiveRef = useRef(false);
  const controlMotionActiveRef = useRef(false);
  const autonomousResumeActiveRef = useRef(false);
  const manualHoldRef = useRef(false);
  const previousCommandPositionRef = useRef<{ x: number; y: number } | null>(null);
  const guidanceSequenceRef = useRef(0);
  const worldStateSequenceRef = useRef(1);
  const lastActivityAtRef = useRef(Date.now());
  const restModeRef = useRef(false);
  const restTransitionActiveRef = useRef(false);
  const resumeAutonomousPresenceRef = useRef<() => Promise<void>>(async () => undefined);
  const pointerRecordsRef = useRef<WebsiteOrbPointerRecord[]>([]);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<BlobPart[]>([]);
  const recordingStreamRef = useRef<MediaStream | null>(null);
  const recordingStopTimerRef = useRef<number | null>(null);
  const recordingCancelledRef = useRef(false);
  const speechAudioRef = useRef<HTMLAudioElement | null>(null);
  const latencyAudioRef = useRef<HTMLAudioElement | null>(null);
  const pointerPingAudioRef = useRef<HTMLAudioElement | null>(null);
  const morbTravelAudioRef = useRef<HTMLAudioElement | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const speechSourceRef = useRef<AudioBufferSourceNode | null>(null);
  const speechPlaybackSettlementRef = useRef<PlaybackSettlement | null>(null);
  const speechPlaybackRef = useRef(false);
  const audioUnlockedRef = useRef(false);
  const statusTimerRef = useRef<number | null>(null);
  const visitorSpeechTimerRef = useRef<number | null>(null);
  const avoidUntilRef = useRef(0);
  const voiceRequestInFlightRef = useRef(false);
  const activeVoiceAbortControllerRef = useRef<AbortController | null>(null);
  const voiceTurnIdRef = useRef(0);
  const recordingMonitorTimerRef = useRef<number | null>(null);
  const recordingStartedAtRef = useRef(0);
  const speechDetectedRef = useRef(false);
  const silenceStartedAtRef = useRef<number | null>(null);
  const speechRecognitionRef = useRef<any>(null);
  const speechRecognitionTranscriptRef = useRef("");
  const speechRecognitionDisabledRef = useRef(false);
  const speechRecognitionStopTimerRef = useRef<number | null>(null);
  const speechRecognitionAbsoluteTimerRef = useRef<number | null>(null);
  const speakerBoostRef = useRef(false);
  const startupAutoStartedRef = useRef(false);
  const startupVoicePreparationRef = useRef<StartupVoicePreparation | null>(null);
  const prepareStartupVoiceRef = useRef<() => StartupVoicePreparation>(() => {
    throw new Error("Startup voice is not ready");
  });
  const runStartupVoiceSequenceRef = useRef<() => Promise<void>>(async () => undefined);
  const pageCapsuleRef = useRef<unknown>(null);
  const pointerTimerRef = useRef<number | null>(null);
  const firstEncounterStateRef = useRef<FirstEncounterState>(readFirstEncounterState());
  const firstEncounterVisitorTurnRef = useRef(0);
  const firstEncounterRunningRef = useRef(false);
  const handsFreeEnabledRef = useRef(false);
  const [pulse, setPulse] = useState<PulseState>(null);
  const [voiceState, setVoiceState] = useState<OrbVoiceState>("idle");
  const [voiceRearmSequence, setVoiceRearmSequence] = useState(0);
  const [statusVisible, setStatusVisible] = useState(false);
  const [statusTitle, setStatusTitle] = useState("ORB online");
  const [statusLine, setStatusLine] = useState("Weaver is preparing voice.");
  const [visitorUtterance, setVisitorUtterance] = useState("");
  const [diagnosticUtterance, setDiagnosticUtterance] = useState("");
  const [activeOrbContext, setActiveOrbContext] = useState<ActiveOrbProjectContext | null>(() => getActiveOrbProjectContext());
  const [speakerBoost, setSpeakerBoost] = useState(false);
  const [lastGuidedTarget, setLastGuidedTarget] = useState<string | null>(null);
  const [guidanceGeometrySource, setGuidanceGeometrySource] = useState<"lidar_cache" | "live_dom" | null>(null);
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
  const [morbPointer, setMorbPointer] = useState<MorbPointerState | null>(null);
  const [pointerWaltzPhase, setPointerWaltzPhase] = useState<PointerWaltzPhase | null>(null);
  const [greetingActive, setGreetingActive] = useState(false);
  const [showStartupDiagnosticsPanel] = useState(() => startupDiagnosticsPanelEnabled());
  const [startupDiagnostics, setStartupDiagnostics] = useState<StartupDiagnostics>(() => initialStartupDiagnostics());
  const [runtimeAnswerDiagnostics, setRuntimeAnswerDiagnostics] = useState<RuntimeAnswerDiagnostics | null>(null);

  const updateStartupDiagnostics = useCallback((patch: Partial<StartupDiagnostics>) => {
    setStartupDiagnostics((current) => {
      const next = {
        ...current,
        ...patch,
        session_once_flag: window.sessionStorage.getItem(STARTUP_GREETING_SESSION_KEY) === "1",
      };
      (window as any).__ORB_WEAVER_STARTUP_DIAGNOSTICS__ = next;
      emitOrbRuntimeEvent("startup_diagnostics", next);
      return next;
    });
  }, []);

  const markFirstEncounter = useCallback((flag: FirstEncounterFlag) => {
    const next = { ...firstEncounterStateRef.current, [flag]: true };
    firstEncounterStateRef.current = next;
    window.sessionStorage.setItem(FIRST_ENCOUNTER_STORAGE_KEY, JSON.stringify(next));
  }, []);

  const firstEncounterComplete = useCallback(() => {
    const state = firstEncounterStateRef.current;
    return (
      state.voice_ready &&
      state.entrance_complete &&
      state.communication_orientation_complete &&
      state.understanding_complete &&
      state.orientation_pointer_proof_complete &&
      state.agency_complete &&
      state.visitor_first_turn_complete &&
      state.personal_relevance_complete &&
      state.responsive_guidance_complete &&
      state.relevant_continuation_complete &&
      state.controller_handoff_complete
    );
  }, []);

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
      window.setTimeout(() => void resumeAutonomousPresenceRef.current(), 120);
    }
  }, []);

  const playPointerPing = useCallback(() => {
    if (!audioUnlockedRef.current) return;
    const audio = pointerPingAudioRef.current || new Audio(POINTER_PING_AUDIO_PATH);
    audio.pause();
    audio.currentTime = 0;
    audio.volume = speakerBoostRef.current ? 1 : 0.86;
    pointerPingAudioRef.current = audio;
    void audio.play().catch(() => undefined);
  }, []);

  const playMorbLaunchSound = useCallback(() => {
    const AudioContextCtor = (window as any).AudioContext || (window as any).webkitAudioContext;
    if (!audioUnlockedRef.current || !AudioContextCtor) return;

    const context: AudioContext = audioContextRef.current || new AudioContextCtor();
    audioContextRef.current = context;
    void context.resume?.();
    const startTime = context.currentTime;
    const oscillator = context.createOscillator();
    const filter = context.createBiquadFilter();
    const gain = context.createGain();
    oscillator.type = "triangle";
    oscillator.frequency.setValueAtTime(340, startTime);
    oscillator.frequency.exponentialRampToValueAtTime(500, startTime + 0.11);
    filter.type = "highpass";
    filter.frequency.value = 200;
    gain.gain.setValueAtTime(0.0001, startTime);
    gain.gain.linearRampToValueAtTime(speakerBoostRef.current ? 0.3 : 0.22, startTime + 0.015);
    gain.gain.exponentialRampToValueAtTime(0.0001, startTime + 0.16);
    oscillator.connect(filter).connect(gain).connect(context.destination);
    oscillator.start(startTime);
    oscillator.stop(startTime + 0.17);
  }, []);

  const startMorbTravelSound = useCallback(() => {
    if (!audioUnlockedRef.current) return;
    const audio = morbTravelAudioRef.current || new Audio(MORB_TRAVEL_AUDIO_PATH);
    audio.pause();
    audio.currentTime = 0;
    audio.loop = true;
    audio.volume = speakerBoostRef.current ? 0.72 : 0.54;
    morbTravelAudioRef.current = audio;
    void audio.play().catch(() => undefined);
  }, []);

  const stopMorbTravelSound = useCallback(() => {
    const audio = morbTravelAudioRef.current;
    if (!audio) return;
    audio.pause();
    audio.currentTime = 0;
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
    Math.min(320, window.innerWidth * 0.24)
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
      const lastDestination = lastAutonomousDestinationRef.current;
      const lastHeading = lastAutonomousHeadingRef.current;
      const headingDelta = lastHeading == null
        ? Math.PI
        : Math.abs(Math.atan2(Math.sin(heading - lastHeading), Math.cos(heading - lastHeading)));
      if (lastDestination && Math.hypot(candidate.x - lastDestination.x, candidate.y - lastDestination.y) < Math.max(90, size * 0.65)) continue;
      if (lastHeading != null && headingDelta < 0.24) continue;
      idleHeadingRef.current = heading;
      lastAutonomousHeadingRef.current = heading;
      lastAutonomousDestinationRef.current = candidate;
      return candidate;
    }
  }

  const centerHeading = Math.atan2(
    minY + (maxY - minY) * 0.48 - current.y,
    minX + (maxX - minX) * 0.52 - current.x
  );

  idleHeadingRef.current = centerHeading;

  const fallback = clampPosition(
    current.x + Math.cos(centerHeading + (Math.random() > 0.5 ? 0.72 : -0.72)) * Math.max(minimumTravel, 110),
    current.y + Math.sin(centerHeading + (Math.random() > 0.5 ? 0.72 : -0.72)) * Math.max(minimumTravel, 110)
  );
  lastAutonomousDestinationRef.current = fallback;
  lastAutonomousHeadingRef.current = centerHeading;
  return fallback;
}, [bounds, clampPosition, size]);

  const resumeAutonomousPresence = useCallback(async () => {
    const blockers = {
      inactive: !activeRef.current,
      speech: speechPlaybackRef.current,
      guidance: guidanceActiveRef.current,
      control: controlMotionActiveRef.current,
      hold: manualHoldRef.current,
      rest: restModeRef.current,
      alreadyResuming: autonomousResumeActiveRef.current,
    };
    if (Object.values(blockers).some(Boolean)) {
      emitOrbRuntimeEvent("autonomous_resume_blocked", blockers);
      return;
    }
    autonomousResumeActiveRef.current = true;
    const sequence = motionInterruptionSequenceRef.current + 1;
    motionInterruptionSequenceRef.current = sequence;
    const destination = nextDestination();
    emitOrbRuntimeEvent("autonomous_resume_started", { destination });
    try {
      await move.start({
        x: destination.x,
        y: destination.y,
        transition: { duration: 5.2, ease: [0.37, 0, 0.22, 1] },
      });
      if (sequence === motionInterruptionSequenceRef.current) positionRef.current = destination;
    } finally {
      if (sequence === motionInterruptionSequenceRef.current) {
        autonomousResumeActiveRef.current = false;
        emitOrbRuntimeEvent("autonomous_resume_complete", { destination });
      }
    }
  }, [move, nextDestination]);
  resumeAutonomousPresenceRef.current = resumeAutonomousPresence;

  const localMoveOutDestination = useCallback(() => {
    const currentRect = orbElementRef.current?.getBoundingClientRect();
    const current = currentRect ? { x: currentRect.left, y: currentRect.top } : positionRef.current;
    const center = { x: current.x + size / 2, y: current.y + size / 2 };
    const nearby = document.elementsFromPoint(center.x, center.y).find((element) => (
      !orbElementRef.current?.contains(element) &&
      !element.closest('.ow-v2-orb-position') &&
      element !== document.body && element !== document.documentElement
    ));
    const guidanceMap = buildLidarGuidanceMap({ orbPosition: center });
    let heading = idleHeadingRef.current + (Math.random() > 0.5 ? 0.7 : -0.7);
    if (nearby) {
      const rect = nearby.getBoundingClientRect();
      heading = Math.atan2(center.y - (rect.top + rect.height / 2), center.x - (rect.left + rect.width / 2));
      heading += (Math.random() - 0.5) * 0.5;
    }
    const displacement = Math.max(88, Math.min(148, size * (0.62 + Math.random() * 0.18)));
    const destination = clampPosition(
      current.x + Math.cos(heading) * displacement,
      current.y + Math.sin(heading) * displacement,
    );
    emitOrbRuntimeEvent("control_spatial_sample", {
      nearbyTag: nearby?.tagName.toLowerCase() || null,
      lidarFeatures: guidanceMap.features.length,
      displacement: Math.hypot(destination.x - current.x, destination.y - current.y),
    });
    return destination;
  }, [clampPosition, size]);

  const executeOrbControlAction = useCallback(async (action?: { type: string; command: string } | null) => {
    if (!action || action.type !== "orb_motion") return false;
    const command = action.command;
    manualHoldRef.current = command === "hold_position";
    if (command === "listen") {
      manualHoldRef.current = false;
      emitOrbRuntimeEvent("control_motion_complete", { command, moved: false });
      return true;
    }
    if (command === "wake") {
      manualHoldRef.current = false;
      markVisitorActivity();
      emitOrbRuntimeEvent("control_motion_complete", { command, moved: false });
      return true;
    }
    const rect = orbElementRef.current?.getBoundingClientRect();
    const current = rect ? { x: rect.left, y: rect.top } : positionRef.current;
    const previousCommandPosition = previousCommandPositionRef.current;
    motionInterruptionSequenceRef.current += 1;
    autonomousResumeActiveRef.current = false;
    move.stop();
    if (command === "hold_position") {
      positionRef.current = current;
      emitOrbRuntimeEvent("control_motion_complete", { command, moved: false });
      return true;
    }
    const step = Math.max(92, size * 0.68);
    let destination = current;
    if (command === "move_out_of_way" || command === "move_to_side") destination = localMoveOutDestination();
    if (command === "move_up") destination = clampPosition(current.x, current.y - step);
    if (command === "move_down") destination = clampPosition(current.x, current.y + step);
    if (command === "move_left") destination = clampPosition(current.x - step, current.y);
    if (command === "move_right") destination = clampPosition(current.x + step, current.y);
    if (command === "come_here") destination = clampPosition(window.innerWidth / 2 - size / 2, window.innerHeight / 2 - size / 2);
    if (command === "come_back" && previousCommandPosition) destination = clampPosition(previousCommandPosition.x, previousCommandPosition.y);
    previousCommandPositionRef.current = current;
    const distanceToMove = Math.hypot(destination.x - current.x, destination.y - current.y);
    controlMotionActiveRef.current = true;
    emitOrbRuntimeEvent("control_motion_started", { command, current, destination, distance: distanceToMove });
    try {
      await move.start({
        x: destination.x,
        y: destination.y,
        transition: { duration: Math.max(1.15, Math.min(2.2, distanceToMove / 78)), ease: [0.37, 0, 0.22, 1] },
      });
      positionRef.current = destination;
      emitOrbRuntimeEvent("control_motion_complete", { command, moved: distanceToMove > 1, destination });
    } finally {
      controlMotionActiveRef.current = false;
    }
    window.setTimeout(() => void resumeAutonomousPresence(), 180);
    return true;
  }, [clampPosition, localMoveOutDestination, markVisitorActivity, move, resumeAutonomousPresence, size]);

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

  const guideToPointerRecord = useCallback(async (
    record: WebsiteOrbPointerRecord,
    intentText: string,
    options: { launchMorbOnly?: boolean } = {},
  ) => {
    markVisitorActivity();
    const movementController = movementControllerRef.current;
    if (!movementController) return false;
    if (record.runtime_policy?.may_point !== true) {
      emitOrbRuntimeEvent("guidance_blocked", { targetId: record.target_id, reason: "may_point_false" });
      return false;
    }
    const guidanceSequence = guidanceSequenceRef.current + 1;
    guidanceSequenceRef.current = guidanceSequence;
    guidanceActiveRef.current = true;
    const finishGuidance = (result: boolean, reason?: string) => {
      if (guidanceSequenceRef.current === guidanceSequence) guidanceActiveRef.current = false;
      emitOrbRuntimeEvent(result ? "guidance_complete" : "guidance_recovery", {
        targetId: record.target_id,
        reason,
      });
      if (result) window.setTimeout(() => void resumeAutonomousPresence(), 120);
      return result;
    };
    const role = inferMorbRole(record, intentText);

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

    setPointerWaltzPhase("ACQUIRE");
    emitOrbRuntimeEvent("guidance_acquire", {
      targetId: record.target_id,
      mayPoint: record.runtime_policy?.may_point === true,
      mayClick: record.runtime_policy?.may_click === true,
    });
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

    if (!movement.ok) {
      setPointerWaltzPhase("RECOVERY");
      return finishGuidance(false, movement.reason);
    }

    let activeRect = movement.targetRect;
    const cachedCoordinate = lidarCacheRef.current.get(record.target_id);
    if (cachedCoordinate) {
      const drift = Math.hypot(
        cachedCoordinate.left - activeRect.left,
        cachedCoordinate.top - activeRect.top,
      );
      if (drift <= LIDAR_DRIFT_THRESHOLD_PX) {
        setGuidanceGeometrySource("lidar_cache");
        emitOrbRuntimeEvent("lidar_cache_hit", { targetId: record.target_id, drift });
      } else {
        lidarCacheRef.current.load(pointerRecordsRef.current);
        setGuidanceGeometrySource("live_dom");
        emitOrbRuntimeEvent("lidar_drift_relocalized", { targetId: record.target_id, drift });
      }
    } else {
      setGuidanceGeometrySource("live_dom");
      emitOrbRuntimeEvent("lidar_cache_miss", { targetId: record.target_id });
    }
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
        setPointerWaltzPhase("RECOVERY");
        movement.cancel("target_lost_after_scroll");
        return finishGuidance(false, "target_lost_after_scroll");
      }
      activeRect = refreshed;
    }

    const latestGoal = movement.getLatestGoal();
    const targetCenterX = latestGoal.normalizedX * window.innerWidth;
    const targetCenterY = latestGoal.normalizedY * window.innerHeight;
    const preferredSide = targetCenterX < window.innerWidth / 2 ? 1 : -1;
    const requiredCenterOffset = size / 2 + MORB_HALF + ORB_TARGET_CLEARANCE_PX;
    const guidedDestination = [preferredSide, -preferredSide]
      .map((candidateSide) => clampPosition(
        targetCenterX + candidateSide * requiredCenterOffset - size / 2,
        targetCenterY - size / 2,
      ))
      .reduce((best, candidate) => {
        const bestClearance = Math.abs(best.x + size / 2 - targetCenterX);
        const candidateClearance = Math.abs(candidate.x + size / 2 - targetCenterX);
        return candidateClearance > bestClearance ? candidate : best;
      });
    const current = positionRef.current;
    const destination = options.launchMorbOnly ? current : guidedDestination;
    const distance = Math.hypot(destination.x - current.x, destination.y - current.y);
    avoidUntilRef.current = Date.now() + 900;
    if (!options.launchMorbOnly) {
      const rect = orbElementRef.current?.getBoundingClientRect();
      if (rect) positionRef.current = { x: rect.left, y: rect.top };
      motionInterruptionSequenceRef.current += 1;
      autonomousResumeActiveRef.current = false;
      move.stop();
      setPointerWaltzPhase("APPROACH");
      await move.start({
        x: destination.x,
        y: destination.y,
        transition: {
          duration: Math.max(5.5, Math.min(12, distance / 75)),
          ease: [0.37, 0, 0.22, 1],
        },
      });
    }
    positionRef.current = destination;
    if (!activeRef.current) {
      setPointerWaltzPhase("RECOVERY");
      movement.cancel("orb_unmounted");
      return finishGuidance(false, "orb_unmounted");
    }

    const finalRect = movement.refreshTarget();
    if (!finalRect) {
      setPointerWaltzPhase("RECOVERY");
      movement.cancel("target_lost_before_arrival");
      return finishGuidance(false, "target_lost_before_arrival");
    }
    const finalTargetX = finalRect.left + finalRect.width / 2;
    const finalTargetY = finalRect.top + finalRect.height / 2;
    const orbCenterX = destination.x + size / 2;
    const orbCenterY = destination.y + size / 2;

    const existingMorbCenter = morbPointer
      ? { x: morbPointer.left + MORB_HALF, y: morbPointer.top + MORB_HALF }
      : null;
    const morbDistance = existingMorbCenter
      ? Math.hypot(finalTargetX - existingMorbCenter.x, finalTargetY - existingMorbCenter.y)
      : Number.POSITIVE_INFINITY;
    const reuseMorb = Boolean(existingMorbCenter && !morbPointer?.dissolving && morbDistance < MORB_REUSE_DISTANCE_PX);

    if (!reuseMorb && morbPointer) {
      setPointerWaltzPhase("DISSOLVE");
      setMorbPointer((currentMorb) => currentMorb ? { ...currentMorb, phase: "DISSOLVE", dissolving: true } : null);
      await wait(420);
      setMorbPointer(null);
    }

    if (reuseMorb) {
      setPointerWaltzPhase("TRAVEL");
      startMorbTravelSound();
      setMorbPointer((currentMorb) => currentMorb ? {
        ...currentMorb,
        targetId: record.target_id,
        role,
        left: finalTargetX - MORB_HALF,
        top: finalTargetY - MORB_HALF,
        phase: "TRAVEL",
        pinging: false,
        dissolving: false,
      } : null);
    } else {
      setPointerWaltzPhase("LAUNCH");
      playMorbLaunchSound();
      setMorbPointer({
        targetId: record.target_id,
        role,
        left: orbCenterX - MORB_HALF,
        top: orbCenterY - MORB_HALF,
        visible: false,
        pinging: false,
        dissolving: false,
        phase: "LAUNCH",
      });
      await wait(60);
      setPointerWaltzPhase("TRAVEL");
      startMorbTravelSound();
      setMorbPointer((currentMorb) => currentMorb ? {
        ...currentMorb,
        left: finalTargetX - MORB_HALF,
        top: finalTargetY - MORB_HALF,
        visible: true,
        phase: "TRAVEL",
      } : null);
    }

    await wait(640);
    stopMorbTravelSound();
    setPointerWaltzPhase("STANCE");
    setMorbPointer((currentMorb) => currentMorb ? { ...currentMorb, phase: "STANCE" } : null);
    await wait(180);

    const pingRect = movement.refreshTarget();
    if (!pingRect) {
      setPointerWaltzPhase("RECOVERY");
      setMorbPointer((currentMorb) => currentMorb ? { ...currentMorb, dissolving: true } : null);
      movement.cancel("target_lost_before_ping");
      return finishGuidance(false, "target_lost_before_ping");
    }

    setPointerWaltzPhase("POINT");
    setMorbPointer((currentMorb) => currentMorb ? { ...currentMorb, phase: "POINT" } : null);
    movement.complete();
    setPointerWaltzPhase("PING");
    playPointerPing();
    setLastGuidedTarget(record.target_id);

    setPointerBloom({
      targetId: record.target_id,
      label: (record.meaning || record.target_type || "Guided target").replace(/^[^:]+:\s*/, ""),
      left: Math.max(4, pingRect.left - 10),
      top: Math.max(4, pingRect.top - 10),
      width: pingRect.width + 20,
      height: pingRect.height + 20,
      originAngle: Math.atan2(finalTargetY - orbCenterY, finalTargetX - orbCenterX) * 180 / Math.PI,
    });
    setMorbPointer((currentMorb) => currentMorb ? { ...currentMorb, phase: "PING", pinging: true } : null);
    if (pointerTimerRef.current) window.clearTimeout(pointerTimerRef.current);
    pointerTimerRef.current = window.setTimeout(() => {
      setPointerBloom(null);
      setPointerWaltzPhase("COMPLETE");
    }, 2600);
    await wait(1200);
    setPointerWaltzPhase("DISSOLVE");
    setMorbPointer((currentMorb) => currentMorb ? { ...currentMorb, phase: "DISSOLVE", dissolving: true } : null);
    await wait(420);
    setMorbPointer(null);
    setPointerWaltzPhase("COMPLETE");
    return finishGuidance(true);
  }, [bumpWorldStateSequence, clampPosition, markVisitorActivity, morbPointer, move, playMorbLaunchSound, playPointerPing, resumeAutonomousPresence, size, startMorbTravelSound, stopMorbTravelSound]);

  const guideToPointerTarget = useCallback(async (intentText: string) => {
    const record = findPointerRecordForIntent(intentText);
    if (!record) return false;
    return guideToPointerRecord(record, intentText);
  }, [findPointerRecordForIntent, guideToPointerRecord]);

  const findPointerRecordById = useCallback((targetId: string) => {
    const currentRoute = routeForUrl(window.location.href);
    return pointerRecordsRef.current.find((record) => (
      record.target_id === targetId && routeForUrl(record.page_route) === currentRoute
    )) || null;
  }, []);

  const guideFromRuntimeResult = useCallback(async (
    result: { transcript: string; spoken_output: string; guidance?: Record<string, unknown> | null; cognitive_pulse?: Record<string, unknown> | null },
  ) => {
    const directTargetId = typeof result.guidance?.target_id === "string" ? result.guidance.target_id : null;
    const pulsePointerMatches = result.cognitive_pulse?.pointer_matches;
    const pulseMatches = Array.isArray(pulsePointerMatches)
      ? pulsePointerMatches as Array<Record<string, unknown>>
      : [];
    const pulseTargetId = typeof pulseMatches[0]?.target_id === "string" ? pulseMatches[0].target_id as string : null;
    const targetId = directTargetId || pulseTargetId;
    if (targetId) {
      const record = findPointerRecordById(targetId);
      if (!record) {
        emitOrbRuntimeEvent("guidance_recovery", { targetId, reason: "runtime_target_not_live_on_route" });
        return false;
      }
      return guideToPointerRecord(record, result.transcript);
    }
    return guideToPointerTarget(`${result.transcript} ${result.spoken_output}`);
  }, [findPointerRecordById, guideToPointerRecord, guideToPointerTarget]);

  const waitForPointerRecords = useCallback(async () => {
    const startedAt = Date.now();
    while (activeRef.current && Date.now() - startedAt < 3200) {
      if (pointerRecordsRef.current.length > 0) return true;
      await wait(160);
    }
    return pointerRecordsRef.current.length > 0;
  }, []);

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

  const showVisitorUtterance = useCallback((text: string, hideAfterMs?: number) => {
    setVisitorUtterance(text);
    if (visitorSpeechTimerRef.current) {
      window.clearTimeout(visitorSpeechTimerRef.current);
      visitorSpeechTimerRef.current = null;
    }
    if (hideAfterMs) {
      visitorSpeechTimerRef.current = window.setTimeout(() => {
        setVisitorUtterance("");
        visitorSpeechTimerRef.current = null;
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
    source.playbackRate.value = ORB_SPEECH_PLAYBACK_RATE;
    source.detune.value = -1200 * Math.log2(ORB_SPEECH_PLAYBACK_RATE);
    gain.gain.value = speakerBoostRef.current ? 1.85 : 1;
    source.connect(gain);
    gain.connect(context.destination);
    speechSourceRef.current = source;

    const settlement = createPlaybackSettlement();
    speechPlaybackSettlementRef.current = settlement;
    source.onended = () => {
      if (speechSourceRef.current === source) speechSourceRef.current = null;
      settlement.resolve();
    };
    try {
      source.start();
    } catch (error) {
      settlement.reject(error as Error);
    }
    try {
      await settlement.promise;
    } finally {
      if (speechPlaybackSettlementRef.current === settlement) speechPlaybackSettlementRef.current = null;
    }
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

  const freezeOrbInPlace = useCallback((_holdMs = 4200) => {
    // Listening and thinking may continue to drift. Only audible speech holds Weaver still.
    if (!speechPlaybackRef.current) return;
    const rect = orbElementRef.current?.getBoundingClientRect();
    if (rect) positionRef.current = { x: rect.left, y: rect.top };
    motionInterruptionSequenceRef.current += 1;
    autonomousResumeActiveRef.current = false;
    move.stop();
    presence.stop();
  }, [move, presence]);

  const speak = useCallback(async (
    text: string,
    audioUrl?: string | null,
    provider?: string | null,
    options: { showTranscript?: boolean } = {},
  ): Promise<boolean> => {
    const showTranscript = options.showTranscript !== false;
    if (showTranscript) {
      showStatus();
      showVisitorUtterance(text);
    } else {
      showVisitorUtterance("");
    }
    setStatusLine("Speaking through Website ORB voice.");
    setVoiceState("speaking");
    speechPlaybackRef.current = true;
    freezeOrbInPlace(4200);
    emitOrbRuntimeEvent("playback_started", { provider: provider || null });

    if (speechAudioRef.current) {
      speechAudioRef.current.pause();
    }
    if (latencyAudioRef.current) {
      latencyAudioRef.current.pause();
      latencyAudioRef.current = null;
    }

    try {
      setStatusTitle("Voice response");
      if (!audioUrl) {
        speechPlaybackRef.current = false;
        setVoiceState("idle");
        setStatusTitle("Voice unavailable");
        setStatusLine(VOICE_UNAVAILABLE_MESSAGE);
        showStatus(3600);
        return false;
      }
      if (speakerBoostRef.current) {
        await playDecodedSpeech(audioUrl);
        speechPlaybackRef.current = false;
        setVoiceState("idle");
        showStatus(1400);
        showVisitorUtterance("", 1);
        return true;
      }
      const audio = speechAudioRef.current || new Audio();
      audio.pause();
      audio.muted = false;
      audio.volume = speakerBoostRef.current ? 1 : 0.86;
      audio.playbackRate = ORB_SPEECH_PLAYBACK_RATE;
      audio.preservesPitch = true;
      audio.src = api.orbMediaUrl(audioUrl);
      speechAudioRef.current = audio;
      const settlement = createPlaybackSettlement();
      speechPlaybackSettlementRef.current = settlement;
      audio.onended = () => {
        if (speechAudioRef.current === audio) speechAudioRef.current = null;
        speechPlaybackRef.current = false;
        setVoiceState("idle");
        showStatus(1400);
        emitOrbRuntimeEvent("playback_ended", { provider: provider || null });
        showVisitorUtterance("", 1);
        settlement.resolve();
      };
      audio.onerror = () => {
        if (speechAudioRef.current === audio) speechAudioRef.current = null;
        settlement.reject(new Error("Audio playback failed"));
      };
      try {
        try {
          await audio.play();
        } catch (error) {
          settlement.reject(error as Error);
        }
        await settlement.promise;
      } finally {
        if (speechPlaybackSettlementRef.current === settlement) speechPlaybackSettlementRef.current = null;
      }
      return true;
    } catch (error) {
      speechPlaybackRef.current = false;
      if ((error as Error)?.name === "AbortError") throw error;
      setStatusTitle("Voice unavailable");
      setStatusLine(VOICE_UNAVAILABLE_MESSAGE);
      setVoiceState("idle");
      showVisitorUtterance("", 1);
      showStatus(3600);
      return false;
    }
  }, [freezeOrbInPlace, playDecodedSpeech, showStatus, showVisitorUtterance]);

  const speakWithGeneratedAudio = useCallback(async (text: string, audioUrl?: string | null, provider?: string | null) => {
    setStatusTitle("Preparing voice");
    setStatusLine(text);
    setVoiceState("speaking");
    showStatus();
    freezeOrbInPlace(4200);

    return speak(text, audioUrl, provider);
  }, [freezeOrbInPlace, showStatus, speak]);

  const diagnosticNarrationText = useCallback(() => {
    return [
      "Startup diagnostics.",
      `Splash is ${startupDiagnostics.splash_state}.`,
      `Permission is ${startupDiagnostics.permission_state}.`,
      `Greeting is ${startupDiagnostics.greeting_state}.`,
      `Audio is ${startupDiagnostics.audio_tts_state}.`,
      `The selected Qwen TTS voice is ${startupDiagnostics.tts_voice}.`,
      `Session flag is ${startupDiagnostics.session_once_flag ? "played once" : "not played"}.`,
      `ORB readiness is ${startupDiagnostics.orb_readiness_state}.`,
      runtimeAnswerDiagnostics?.resolution_source
        ? `The latest answer source is ${runtimeAnswerDiagnostics.resolution_source}.`
        : "No visitor answer has been resolved yet.",
      runtimeAnswerDiagnostics?.qwen_bypassed === true ? "Qwen cognition was bypassed." : "Qwen cognition was used or not yet measured.",
      runtimeAnswerDiagnostics?.cached_speech === true ? "Cached Qwen speech was used." : "Cached speech was not used or not yet measured.",
      runtimeAnswerDiagnostics?.learning_candidate_state
        ? `The learning candidate state is ${runtimeAnswerDiagnostics.learning_candidate_state}.`
        : "There is no learning candidate state yet.",
    ].join(" ");
  }, [runtimeAnswerDiagnostics, startupDiagnostics]);

  const speakDiagnostics = useCallback(async () => {
    const text = diagnosticNarrationText();
    setDiagnosticUtterance(text);
    setStatusTitle("Speaking diagnostics");
    setStatusLine("Diagnostic narration is separate from visitor speech.");
    showStatus();
    try {
      const tts = await api.websiteOrbTts(text);
      if (!tts.tts_audio_url) throw new Error(tts.tts_error || "Diagnostic TTS unavailable");
      await speak(text, tts.tts_audio_url, tts.tts_provider, { showTranscript: false });
    } catch (error) {
      setStatusTitle("Diagnostic voice unavailable");
      setStatusLine(error instanceof Error ? error.message : VOICE_UNAVAILABLE_MESSAGE);
      showStatus(3600);
    }
  }, [diagnosticNarrationText, showStatus, speak]);

  const speakRecovery = useCallback(async (text: string, signal?: AbortSignal) => {
    setStatusLine(text);
    setStatusTitle("Recovering voice");
    setVoiceState("speaking");
    showStatus();

    const outcome = await runBackendRecovery<WebsiteOrbTtsResponse>(
      (recoverySignal) => api.websiteOrbTts(text, recoverySignal),
      (tts) => speak(text, tts.tts_audio_url, tts.tts_provider),
      signal,
    );
    if (outcome === "unavailable") {
      setStatusTitle("Voice unavailable");
      setStatusLine(VOICE_UNAVAILABLE_MESSAGE);
      setVoiceState("idle");
      showStatus(3600);
    }
    return outcome;
  }, [showStatus, speak]);

  const contextTargetUrl = useCallback(() => {
    if (activeOrbContext) return buildCustomerPageCapsuleUrl(activeOrbContext);
    if (["127.0.0.1", "localhost"].includes(window.location.hostname)) {
      return new URL(`${window.location.pathname}${window.location.search}`, "https://orbweaver.spruked.com").toString();
    }
    return window.location.href;
  }, [activeOrbContext]);

  const runGeneratedAct = useCallback(async (
    transcript: string,
    experience: WebsiteOrbExperienceContext,
    controller?: AbortController,
  ) => {
    const result = await api.websiteOrbText(transcript, true, controller?.signal, {
      project_id: activeOrbContext?.project_id,
      target_url: contextTargetUrl(),
      experience,
    });
    await speakWithGeneratedAudio(result.spoken_output, result.tts_audio_url, result.tts_provider);
    return result;
  }, [activeOrbContext?.project_id, contextTargetUrl, speakWithGeneratedAudio]);

  const runFirstEncounterChoreography = useCallback(async () => {
    if (
      !isPublicLandingExperience() ||
      firstEncounterRunningRef.current ||
      firstEncounterComplete() ||
      onboardingSafeMode
    ) {
      return;
    }
    firstEncounterRunningRef.current = true;
    try {
      const encounterSection = document.getElementById("weaver-first-encounter");
      if (encounterSection) {
        encounterSection.scrollIntoView({ behavior: "smooth", block: "center" });
        await wait(900);
        bumpWorldStateSequence();
      }

      await runGeneratedAct(
        "A first-time visitor has arrived and has not spoken yet.",
        {
          phase: "orientation",
          objective: "Orient the visitor to natural voice turn-taking: they can speak normally, finish the thought, and pause so Weaver can respond.",
          verification_state: "not_applicable",
          demonstrated_capabilities: ["Qwen TTS voice is playing", "Faster Whisper microphone path is ready"],
        },
      );
      markFirstEncounter("communication_orientation_complete");
      await runGeneratedAct(
        "The visitor is viewing the Orb Weaver home page before their first voice turn.",
        {
          phase: "understanding",
          objective: "Demonstrate that Weaver understands this specific page and its useful visitor paths using live Site World and page context.",
          verification_state: "not_applicable",
          demonstrated_capabilities: ["current page context loaded", "Site World available"],
        },
      );
      markFirstEncounter("understanding_complete");

      const hasPointerMap = await waitForPointerRecords();
      const proofTarget = hasPointerMap ? findPointerRecordById("watch_weaver_guide") : null;
      if (proofTarget) {
        const guided = await guideToPointerRecord(proofTarget, "Demonstrate verified visual guidance");
        if (guided) {
          markFirstEncounter("orientation_pointer_proof_complete");
        } else {
          emitOrbRuntimeEvent("startup_pointer_demo_skipped", {
            targetId: "watch_weaver_guide",
            reason: "live_target_verification_failed",
          });
          markFirstEncounter("orientation_pointer_proof_complete");
        }
      } else {
        emitOrbRuntimeEvent("startup_pointer_demo_skipped", {
          targetId: "watch_weaver_guide",
          reason: hasPointerMap ? "target_missing_on_route" : "pointer_map_unavailable",
        });
        markFirstEncounter("orientation_pointer_proof_complete");
      }

      await runGeneratedAct(
        proofTarget
          ? "The visual-guidance demo was attempted after the greeting without blocking startup readiness."
          : "The visual-guidance demo target was unavailable, so the greeting continues and Weaver remains ready.",
        {
          phase: "agency",
          objective: "Establish agency after the startup introduction and invite a useful next action without making pointer readiness a prerequisite.",
          verified_target_id: proofTarget?.target_id,
          verified_target_label: proofTarget?.meaning,
          verification_state: proofTarget ? "verified" : "not_applicable",
          demonstrated_capabilities: proofTarget
            ? ["optional live DOM target verification", "movement", "point", "ping", "neural voice"]
            : ["neural voice", "startup readiness", "Site World explanation"],
        },
      );
      markFirstEncounter("agency_complete");
      setStatusTitle("Listening");
      setStatusLine("Speak naturally, then pause.");
      showStatus();
    } catch (error) {
      setStatusTitle("First encounter paused");
      setStatusLine(error instanceof Error ? error.message : "A required live proof is unavailable.");
      showStatus(5200);
      throw error;
    } finally {
      firstEncounterRunningRef.current = false;
    }
  }, [bumpWorldStateSequence, findPointerRecordById, firstEncounterComplete, guideToPointerRecord, markFirstEncounter, onboardingSafeMode, runGeneratedAct, showStatus, waitForPointerRecords]);

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
    try {
      logVoice("website-voice", turnId);
      const targetUrl = contextTargetUrl();
      const visitorTurn = firstEncounterVisitorTurnRef.current + 1;
      firstEncounterVisitorTurnRef.current = visitorTurn;
      const inFirstEncounter = isPublicLandingExperience() && !firstEncounterComplete();
      const experience: WebsiteOrbExperienceContext | null = inFirstEncounter
        ? visitorTurn === 1
          ? {
              phase: "make_it_personal",
              objective: "Respond to the visitor's actual first request, show that it was understood in context, and guide to a verified relevant target when one exists.",
              visitor_turn: visitorTurn,
              verification_state: "pending",
              demonstrated_capabilities: ["Faster Whisper transcription", "Site World reasoning", "Qwen TTS voice"],
            }
          : {
              phase: "relevant_continuation",
              objective: "Continue from the visitor's words and prior demonstrated capability with a relevant next step, preserving their progress and transitioning into normal consultation.",
              visitor_turn: visitorTurn,
              verification_state: "pending",
              demonstrated_capabilities: ["voice turn-taking", "contextual reasoning", "verified visual guidance"],
            }
        : null;
      const result = await api.websiteOrbVoice(audio, controller.signal, {
        project_id: activeOrbContext?.project_id,
        target_url: targetUrl,
        experience,
      });
      const spokenOutput = result.spoken_output;
      setRuntimeAnswerDiagnostics(result.resolution_diagnostics || null);
      setStatusTitle("Voice response");
      setStatusLine(spokenOutput);
      if (result.tts_error && !result.tts_audio_url) {
        setStatusTitle("Voice unavailable");
        setStatusLine(VOICE_UNAVAILABLE_MESSAGE);
      }
      emitOrbRuntimeEvent("canonical_response", {
        turnId,
        transcript: result.transcript,
        sourceLane: result.source_lane || result.llm_source,
        ttsProvider: result.tts_provider || null,
        controlCommand: result.control_action?.command || null,
      });
      logVoice("playback", turnId);
      await speakWithGeneratedAudio(spokenOutput, result.tts_audio_url, result.tts_provider);
      if (controller.signal.aborted) return;
      const controlHandled = await executeOrbControlAction(result.control_action);
      const guided = controlHandled ? false : await guideFromRuntimeResult(result);
      if (controller.signal.aborted) return;
      if (guided) markFirstEncounter("responsive_guidance_complete");
      if (experience?.phase === "make_it_personal") {
        markFirstEncounter("visitor_first_turn_complete");
        markFirstEncounter("personal_relevance_complete");
      } else if (experience?.phase === "relevant_continuation") {
        markFirstEncounter("relevant_continuation_complete");
        if (guided || firstEncounterStateRef.current.responsive_guidance_complete) {
          markFirstEncounter("controller_handoff_complete");
        }
      }
    } catch (error) {
      if ((error as Error)?.name === "AbortError") return;
      setStatusTitle("ORB route unavailable");
      await speakRecovery("I am reconnecting to my response service. Please try again in a moment.", controller.signal);
    } finally {
      if (activeVoiceAbortControllerRef.current === controller) {
        activeVoiceAbortControllerRef.current = null;
        voiceRequestInFlightRef.current = false;
        setVoiceState("idle");
        setVoiceRearmSequence((value) => value + 1);
      }
      logVoice("finalized", turnId);
    }
  }, [activeOrbContext?.project_id, contextTargetUrl, executeOrbControlAction, firstEncounterComplete, freezeOrbInPlace, guideFromRuntimeResult, logVoice, markFirstEncounter, markVisitorActivity, showStatus, speakRecovery, speakWithGeneratedAudio]);

  const processRecognizedOrbText = useCallback(async (transcript: string) => {
    markVisitorActivity();
    const cleanTranscript = transcript.replace(/\s+/g, " ").trim();
    if (!cleanTranscript || voiceRequestInFlightRef.current) return;
    const turnId = voiceTurnIdRef.current;
    const controller = new AbortController();
    activeVoiceAbortControllerRef.current = controller;
    voiceRequestInFlightRef.current = true;

    setStatusTitle("Thinking");
    setStatusLine(cleanTranscript);
    setVoiceState("speaking");
    showStatus();
    freezeOrbInPlace(4200);
    try {
      logVoice("browser-speech-recognition", turnId);
      const targetUrl = contextTargetUrl();
      const visitorTurn = firstEncounterVisitorTurnRef.current + 1;
      firstEncounterVisitorTurnRef.current = visitorTurn;
      const inFirstEncounter = isPublicLandingExperience() && !firstEncounterComplete();
      const experience: WebsiteOrbExperienceContext | null = inFirstEncounter
        ? visitorTurn === 1
          ? {
              phase: "make_it_personal",
              objective: "Respond to the visitor's actual first request, show that it was understood in context, and guide to a verified relevant target when one exists.",
              visitor_turn: visitorTurn,
              verification_state: "pending",
              demonstrated_capabilities: ["browser speech recognition", "Site World reasoning", "Qwen TTS voice"],
            }
          : {
              phase: "relevant_continuation",
              objective: "Continue from the visitor's words and prior demonstrated capability with a relevant next step, preserving their progress and transitioning into normal consultation.",
              visitor_turn: visitorTurn,
              verification_state: "pending",
              demonstrated_capabilities: ["voice turn-taking", "contextual reasoning", "verified visual guidance"],
            }
        : null;
      const result = await api.websiteOrbText(cleanTranscript, true, controller.signal, {
        project_id: activeOrbContext?.project_id,
        target_url: targetUrl,
        experience,
      });
      const spokenOutput = result.spoken_output;
      setRuntimeAnswerDiagnostics(result.resolution_diagnostics || null);
      setStatusTitle("Voice response");
      setStatusLine(spokenOutput);
      emitOrbRuntimeEvent("canonical_response", {
        turnId,
        transcript: result.transcript,
        sourceLane: result.source_lane || result.llm_source,
        ttsProvider: result.tts_provider || null,
        controlCommand: result.control_action?.command || null,
      });
      await speakWithGeneratedAudio(spokenOutput, result.tts_audio_url, result.tts_provider);
      if (controller.signal.aborted) return;
      const controlHandled = await executeOrbControlAction(result.control_action);
      const guided = controlHandled ? false : await guideFromRuntimeResult(result);
      if (guided) markFirstEncounter("responsive_guidance_complete");
      if (experience?.phase === "make_it_personal") {
        markFirstEncounter("visitor_first_turn_complete");
        markFirstEncounter("personal_relevance_complete");
      } else if (experience?.phase === "relevant_continuation") {
        markFirstEncounter("relevant_continuation_complete");
        if (guided || firstEncounterStateRef.current.responsive_guidance_complete) {
          markFirstEncounter("controller_handoff_complete");
        }
      }
    } catch (error) {
      if ((error as Error)?.name === "AbortError") return;
      setStatusTitle("ORB route unavailable");
      await speakRecovery("I am reconnecting to my response service. Please try again in a moment.", controller.signal);
    } finally {
      if (activeVoiceAbortControllerRef.current === controller) {
        activeVoiceAbortControllerRef.current = null;
        voiceRequestInFlightRef.current = false;
        setVoiceState("idle");
        setVoiceRearmSequence((value) => value + 1);
      }
      logVoice("finalized", turnId);
    }
  }, [activeOrbContext?.project_id, contextTargetUrl, executeOrbControlAction, firstEncounterComplete, freezeOrbInPlace, guideFromRuntimeResult, logVoice, markFirstEncounter, markVisitorActivity, showStatus, speakRecovery, speakWithGeneratedAudio]);

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

  const stopBrowserSpeechRecognition = useCallback((cancel = false) => {
    if (speechRecognitionStopTimerRef.current) {
      window.clearTimeout(speechRecognitionStopTimerRef.current);
      speechRecognitionStopTimerRef.current = null;
    }
    if (speechRecognitionAbsoluteTimerRef.current) {
      window.clearTimeout(speechRecognitionAbsoluteTimerRef.current);
      speechRecognitionAbsoluteTimerRef.current = null;
    }
    const recognition = speechRecognitionRef.current;
    if (!recognition) return;
    recognition.__orbCancelled = cancel;
    try {
      recognition.stop();
    } catch {
      speechRecognitionRef.current = null;
    }
  }, []);

  const startBrowserSpeechRecognition = useCallback(() => {
    if (speechRecognitionDisabledRef.current) return false;
    const SpeechRecognitionCtor = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognitionCtor) return false;
    if (speechRecognitionRef.current) {
      stopBrowserSpeechRecognition(true);
      return true;
    }

    const turnId = voiceTurnIdRef.current + 1;
    voiceTurnIdRef.current = turnId;
    const recognition = new SpeechRecognitionCtor();
    speechRecognitionRef.current = recognition;
    speechRecognitionTranscriptRef.current = "";
    recognition.lang = "en-US";
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;

    const armPauseTimer = () => {
      if (speechRecognitionStopTimerRef.current) window.clearTimeout(speechRecognitionStopTimerRef.current);
      speechRecognitionStopTimerRef.current = window.setTimeout(() => stopBrowserSpeechRecognition(false), END_SILENCE_MS);
    };

    recognition.onresult = (event: any) => {
      let interim = "";
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const result = event.results[index];
        const text = String(result?.[0]?.transcript || "");
        if (result.isFinal) {
          speechRecognitionTranscriptRef.current = `${speechRecognitionTranscriptRef.current} ${text}`.trim();
        } else {
          interim = `${interim} ${text}`.trim();
        }
      }
      const preview = `${speechRecognitionTranscriptRef.current} ${interim}`.replace(/\s+/g, " ").trim();
      if (preview) {
        setStatusTitle("Listening");
        setStatusLine(preview);
        armPauseTimer();
      }
    };
    recognition.onerror = () => {
      speechRecognitionDisabledRef.current = true;
      speechRecognitionRef.current = null;
      setStatusTitle("Speech recognition unavailable");
      setStatusLine("Tap the ORB again to use microphone recording.");
      setVoiceState("idle");
      showStatus(1800);
    };
    recognition.onend = () => {
      const cancelled = Boolean(recognition.__orbCancelled);
      speechRecognitionRef.current = null;
      if (speechRecognitionStopTimerRef.current) window.clearTimeout(speechRecognitionStopTimerRef.current);
      if (speechRecognitionAbsoluteTimerRef.current) window.clearTimeout(speechRecognitionAbsoluteTimerRef.current);
      speechRecognitionStopTimerRef.current = null;
      speechRecognitionAbsoluteTimerRef.current = null;
      const transcript = speechRecognitionTranscriptRef.current.replace(/\s+/g, " ").trim();
      speechRecognitionTranscriptRef.current = "";
      if (cancelled) {
        setStatusTitle("Listening cancelled");
        setStatusLine("Tap the ORB when you want to speak.");
        setVoiceState("idle");
        showStatus(1800);
        return;
      }
      if (!transcript) {
        handsFreeEnabledRef.current = false;
        setStatusTitle("Still listening");
        setStatusLine("I did not hear speech. Tap the ORB when you are ready.");
        setVoiceState("idle");
        showStatus(2600);
        return;
      }
      handsFreeEnabledRef.current = isPublicLandingExperience();
      void processRecognizedOrbText(transcript);
    };

    try {
      setStatusTitle("Listening");
      setStatusLine("Speak your full question. Pause when you are done.");
      setVoiceState("listening");
      showStatus();
      recognition.start();
      speechRecognitionAbsoluteTimerRef.current = window.setTimeout(() => stopBrowserSpeechRecognition(false), ABSOLUTE_RECORDING_LIMIT_MS);
      return true;
    } catch {
      speechRecognitionRef.current = null;
      return false;
    }
  }, [processRecognizedOrbText, showStatus, stopBrowserSpeechRecognition]);

  const startOrbRecording = useCallback(async () => {
    unlockAudio();
    if (voiceRequestInFlightRef.current || voiceState === "speaking") return;

    if (startBrowserSpeechRecognition()) return;

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

      const retainedStream = recordingStreamRef.current;
      const retainedTrack = retainedStream?.getAudioTracks().find((track) => track.readyState === "live");
      const stream = retainedStream && retainedTrack
        ? retainedStream
        : await navigator.mediaDevices.getUserMedia({
            audio: {
              echoCancellation: true,
              noiseSuppression: true,
              autoGainControl: true,
            },
          });
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
      emitOrbRuntimeEvent("recording_started", { turnId, mimeType: recorder.mimeType });

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      recorder.onstop = () => {
        const cancelled = recordingCancelledRef.current;
        const speechDetected = speechDetectedRef.current;
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
          emitOrbRuntimeEvent("recording_cancelled", { turnId });
          setStatusTitle("Listening cancelled");
          setStatusLine("Tap the ORB when you want to speak.");
          setVoiceState("idle");
          showStatus(1800);
          return;
        }
        if (!speechDetected) {
          handsFreeEnabledRef.current = false;
          emitOrbRuntimeEvent("recording_discarded", { turnId, reason: "no_speech_detected", bytes: audio.size });
          setStatusTitle("Still listening");
          setStatusLine("I did not hear speech. Tap the ORB when you are ready.");
          setVoiceState("idle");
          showStatus(2600);
          return;
        }
        handsFreeEnabledRef.current = isPublicLandingExperience();
        emitOrbRuntimeEvent("recording_stopped", { turnId, bytes: audio.size });
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
  }, [freezeOrbInPlace, logVoice, monitorRecordingSilence, playPulse, processRecordedOrbAudio, showStatus, startBrowserSpeechRecognition, stopOrbRecording, unlockAudio, voiceState]);

  const interruptOrbSpeech = useCallback(() => {
    activeVoiceAbortControllerRef.current?.abort();
    activeVoiceAbortControllerRef.current = null;
    voiceRequestInFlightRef.current = false;
    speechPlaybackSettlementRef.current?.cancel();
    speechPlaybackSettlementRef.current = null;
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
    emitOrbRuntimeEvent("playback_interrupted", { turnId: voiceTurnIdRef.current });
    window.setTimeout(() => void resumeAutonomousPresence(), 120);
  }, [resumeAutonomousPresence, showStatus]);

  const requestStartupMicrophonePermission = useCallback(async () => {
    updateStartupDiagnostics({ permission_state: "requesting" });
    if (!navigator.mediaDevices?.getUserMedia) {
      setStatusTitle("Voice unavailable");
      setStatusLine("Microphone recording is unavailable in this browser.");
      showStatus(4200);
      updateStartupDiagnostics({ permission_state: "blocked" });
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
      recordingStreamRef.current = stream;
      markFirstEncounter("voice_ready");
      updateStartupDiagnostics({ permission_state: "ready", orb_readiness_state: "voice_ready" });
      return true;
    } catch {
      setStatusTitle("Microphone blocked");
      setStatusLine("Allow microphone access in the browser to talk with Weaver.");
      showStatus(5200);
      updateStartupDiagnostics({ permission_state: "blocked" });
      return false;
    }
  }, [markFirstEncounter, showStatus, updateStartupDiagnostics]);

  const waitForStartupGate = useCallback(async () => {
    if (!isPublicLandingExperience()) return;
    if (window.sessionStorage.getItem(LANDING_SPLASH_COMPLETE_SESSION_KEY) === "1") {
      updateStartupDiagnostics({ splash_state: "skipped_session_once" });
      return;
    }

    updateStartupDiagnostics({ splash_state: "playing", orb_readiness_state: "waiting_for_gate" });
    await new Promise<void>((resolve) => {
      const handler = (event: Event) => {
        const detail = (event as CustomEvent).detail || {};
        unlockAudio();
        updateStartupDiagnostics({
          splash_state: detail.splash_state === "skipped_session_once" ? "skipped_session_once" : "complete",
          permission_state: detail.permission_state === "user_activated" ? "user_activated" : "waiting",
        });
        window.removeEventListener(STARTUP_GATE_COMPLETE_EVENT, handler);
        resolve();
      };
      window.addEventListener(STARTUP_GATE_COMPLETE_EVENT, handler, { once: true });
    });
  }, [unlockAudio, updateStartupDiagnostics]);

  const prepareStartupVoice = useCallback((): StartupVoicePreparation => {
    if (startupVoicePreparationRef.current) return startupVoicePreparationRef.current;

    unlockAudio();
    updateStartupDiagnostics({ greeting_state: "preparing", audio_tts_state: "requesting" });
    setStatusTitle("Opening the ORB Weaver suite");
    setStatusLine("Preparing voice permission and guidance.");
    showStatus();

    const greeting = startupGreetingText();
    const preparation: StartupVoicePreparation = {
      greeting,
      micReady: requestStartupMicrophonePermission(),
      tts: api.websiteOrbTts(greeting)
        .then((tts) => {
          updateStartupDiagnostics({ audio_tts_state: tts.tts_audio_url ? "ready" : "failed" });
          if (tts.tts_voice) updateStartupDiagnostics({ tts_voice: tts.tts_voice });
          return tts;
        })
        .catch(() => {
          updateStartupDiagnostics({ audio_tts_state: "failed" });
          return null;
        }),
    };
    startupVoicePreparationRef.current = preparation;
    return preparation;
  }, [requestStartupMicrophonePermission, showStatus, unlockAudio, updateStartupDiagnostics]);

  const runStartupVoiceSequence = useCallback(async () => {
    const onLanding = isPublicLandingExperience();
    const greetingAlreadyPlayed =
      window.sessionStorage.getItem(STARTUP_GREETING_SESSION_KEY) === "1";

    // A first-time visitor who lands deep in the site should not get a surprise
    // microphone prompt. Once voice has been established, page reloads resume
    // hands-free listening without replaying the landing greeting.
    if (!shouldRunMountedStartupVoiceSequence({
      startupAutoStarted: startupAutoStartedRef.current,
      onboardingSafeMode,
      onLanding,
      greetingAlreadyPlayed,
      voiceReady: firstEncounterStateRef.current.voice_ready,
    })) return;

    startupAutoStartedRef.current = true;
    let micReady = false;
    emitOrbRuntimeEvent("orb_mount_confirmed", { onLanding });
    updateStartupDiagnostics({ orb_readiness_state: onLanding ? "waiting_for_gate" : "mounting" });
    await waitForStartupGate();

    if (onLanding && !greetingAlreadyPlayed) {
      const preparation = prepareStartupVoice();
      micReady = await preparation.micReady;
      emitOrbRuntimeEvent("permission_handoff_complete", { micReady });
      setGreetingActive(true);
      updateStartupDiagnostics({ greeting_state: "playing", orb_readiness_state: "intro_playing" });
      emitOrbRuntimeEvent("intro_started", { provider: "website_orb_tts" });
      let introAudioPlayed = false;
      try {
        const tts = await preparation.tts;
        if (!tts?.tts_audio_url) throw new Error("Startup voice synthesis failed");
        updateStartupDiagnostics({ audio_tts_state: "playing" });
        emitOrbRuntimeEvent("intro_audio_started", { provider: tts.tts_provider || null, voice: tts.tts_voice || null });
        const spokenGreeting = speak(preparation.greeting, tts.tts_audio_url, tts.tts_provider);
        void guideToPointerRecord(SUITE_LOGO_POINTER_RECORD, "ORB Weaver suite", { launchMorbOnly: true });
        introAudioPlayed = await spokenGreeting;
        if (!introAudioPlayed) throw new Error("Startup voice playback failed");
        updateStartupDiagnostics({ audio_tts_state: "played", greeting_state: "played" });
        markFirstEncounter("entrance_complete");
      } catch {
        updateStartupDiagnostics({ audio_tts_state: "failed", greeting_state: "failed" });
        await speakRecovery(preparation.greeting);
      } finally {
        setGreetingActive(false);
        if (introAudioPlayed) {
          window.sessionStorage.setItem(STARTUP_GREETING_SESSION_KEY, "1");
          updateStartupDiagnostics({ greeting_state: "played", orb_readiness_state: "ready" });
          emitOrbRuntimeEvent("intro_complete");
          emitOrbRuntimeEvent("orb_ready");
        } else {
          updateStartupDiagnostics({ greeting_state: "failed", orb_readiness_state: "voice_ready" });
        }
      }

      if (!introAudioPlayed) return;

      // Choreography is enrichment, never a gate on conversation.
      try {
        await runFirstEncounterChoreography();
      } catch {
        // The choreography reports its own status. Weaver must still listen.
      }
    } else {
      updateStartupDiagnostics({ greeting_state: "skipped_session_once" });
      micReady = await requestStartupMicrophonePermission();
      emitOrbRuntimeEvent("permission_handoff_complete", { micReady });
      updateStartupDiagnostics({ orb_readiness_state: "ready" });
      emitOrbRuntimeEvent("orb_ready");
    }

    if (micReady && activeRef.current) {
      handsFreeEnabledRef.current = true;
      window.setTimeout(() => {
        if (!activeRef.current || voiceRequestInFlightRef.current || recorderRef.current) return;
        void startOrbRecording();
      }, 420);
    }
  }, [guideToPointerRecord, markFirstEncounter, onboardingSafeMode, prepareStartupVoice, requestStartupMicrophonePermission, runFirstEncounterChoreography, setGreetingActive, speak, speakRecovery, startOrbRecording, updateStartupDiagnostics, waitForStartupGate]);

  // Keep the mounted startup path pointed at the live sequence before mount
  // effects can call it.
  prepareStartupVoiceRef.current = prepareStartupVoice;
  runStartupVoiceSequenceRef.current = runStartupVoiceSequence;

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

  const resetStartupSequence = useCallback(() => {
    window.sessionStorage.removeItem(LANDING_SPLASH_SESSION_KEY);
    window.sessionStorage.removeItem(LANDING_SPLASH_COMPLETE_SESSION_KEY);
    window.sessionStorage.removeItem(STARTUP_GREETING_SESSION_KEY);
    window.sessionStorage.removeItem(FIRST_ENCOUNTER_STORAGE_KEY);
    firstEncounterStateRef.current = { ...EMPTY_FIRST_ENCOUNTER_STATE };
    startupVoicePreparationRef.current = null;
    startupAutoStartedRef.current = false;
    updateStartupDiagnostics(initialStartupDiagnostics());
    emitOrbRuntimeEvent("startup_reset");
    const url = new URL(window.location.href);
    url.searchParams.set("orbStartupReset", "1");
    window.location.assign(url.toString());
  }, [updateStartupDiagnostics]);

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
    if (pointerPingAudioRef.current) {
      pointerPingAudioRef.current.volume = next ? 1 : 0.86;
    }
    if (morbTravelAudioRef.current) {
      morbTravelAudioRef.current.volume = next ? 0.72 : 0.54;
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
    if (onboardingSafeMode) return;
    if (isPublicLandingExperience() && firstEncounterStateRef.current.voice_ready) {
      handsFreeEnabledRef.current = true;
    }
  }, [onboardingSafeMode]);

  useEffect(() => {
    if (!isPublicLandingExperience()) return;
    if (!shouldRearmVoice({
      handsFree: handsFreeEnabledRef.current,
      voiceState,
      onboardingSafeMode,
      requestInFlight: voiceRequestInFlightRef.current,
      recording: Boolean(recorderRef.current),
      firstEncounterRunning: firstEncounterRunningRef.current,
      voiceReady: firstEncounterStateRef.current.voice_ready,
    })) return;

    const rearmTimer = window.setTimeout(() => {
      if (!activeRef.current || voiceRequestInFlightRef.current || recorderRef.current) return;
      void startOrbRecording();
    }, 720);

    return () => window.clearTimeout(rearmTimer);
  }, [onboardingSafeMode, startOrbRecording, voiceRearmSequence, voiceState]);

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
    const updateContext = () => setActiveOrbContext(getActiveOrbProjectContext());
    window.addEventListener(ACTIVE_ORB_PROJECT_CONTEXT_EVENT, updateContext);
    window.addEventListener("storage", updateContext);
    return () => {
      window.removeEventListener(ACTIVE_ORB_PROJECT_CONTEXT_EVENT, updateContext);
      window.removeEventListener("storage", updateContext);
    };
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    const pointerDomain = activeOrbContext?.canonical_domain
      || (["127.0.0.1", "localhost"].includes(window.location.hostname) ? "orbweaver.spruked.com" : window.location.hostname);
    api.websiteOrbPointerMap(pointerDomain, controller.signal)
      .then((pointerMap) => {
        pointerRecordsRef.current = Array.isArray(pointerMap.records) ? pointerMap.records : [];
        lidarCacheRef.current.load(pointerRecordsRef.current);
        lidarCacheRef.current.startDriftAudit();
        emitOrbRuntimeEvent("pointer_map_ready", { count: pointerRecordsRef.current.length });
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
        lidarCacheRef.current.clear();
        bumpWorldStateSequence();
      });
    return () => controller.abort();
  }, [activeOrbContext?.canonical_domain, bumpWorldStateSequence, guideToPointerTarget]);

  useEffect(() => {
    guidanceSequenceRef.current += 1;
    motionInterruptionSequenceRef.current += 1;
    autonomousResumeActiveRef.current = false;
    guidanceActiveRef.current = false;
    movementControllerRef.current?.dispose();
    setPointerBloom(null);
    setMorbPointer(null);
    setPointerWaltzPhase(null);
    setGuidanceGeometrySource(null);
    bumpWorldStateSequence();
    const rebuild = window.setTimeout(() => {
      lidarCacheRef.current.load(pointerRecordsRef.current);
      emitOrbRuntimeEvent("route_spatial_state_ready", { route: location.pathname });
      void resumeAutonomousPresenceRef.current();
    }, 120);
    return () => window.clearTimeout(rebuild);
  }, [bumpWorldStateSequence, location.pathname]);

  useEffect(() => {
    let cancelled = false;
    let lastUrl = "";

    const preloadCapsule = () => {
      const currentUrl = contextTargetUrl();
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
  }, [contextTargetUrl]);

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
      void runStartupVoiceSequenceRef.current();

      if (!reducedMotionRef.current) {
        glow.start({
          opacity: [0.62, 0.96, 0.58, 0.88, 0.62],
          scale: [1, 1.1, 0.97, 1.06, 1],
          transition: {
            duration: 15,
            repeat: Infinity,
            ease: "easeInOut",
          },
        });
      }

      await wait(700);

      while (activeRef.current) {
        const inactiveForMs = Date.now() - lastActivityAtRef.current;
        const shouldEnterRest =
          inactiveForMs >= REST_AFTER_INACTIVITY_MS &&
          !speechPlaybackRef.current &&
          !recorderRef.current &&
          !speechRecognitionRef.current;

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

        if (
          speechPlaybackRef.current || guidanceActiveRef.current || controlMotionActiveRef.current ||
          autonomousResumeActiveRef.current || manualHoldRef.current
        ) {
          await wait(160);
          continue;
        }

        if (Date.now() < avoidUntilRef.current) {
          await wait(160);
          continue;
        }

        const destination = nextDestination();

        void playLocalPresence();

        if (!activeRef.current) break;

        const movementSequence = motionInterruptionSequenceRef.current;
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
        if (movementSequence !== motionInterruptionSequenceRef.current) continue;

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
  }, [
    clampPosition,
    glow,
    move,
    nextDestination,
    playLocalPresence,
    presence,
    size,
    upperRightRestDestination,
  ]);

  useEffect(() => {
    const monitor = window.setInterval(() => {
      const shouldRest =
        Date.now() - lastActivityAtRef.current >= REST_AFTER_INACTIVITY_MS &&
        !speechPlaybackRef.current && !recorderRef.current && !speechRecognitionRef.current && !guidanceActiveRef.current &&
        !controlMotionActiveRef.current && !restModeRef.current && !restTransitionActiveRef.current;
      if (!shouldRest) return;
      restTransitionActiveRef.current = true;
      restModeRef.current = true;
      setIsResting(true);
      motionInterruptionSequenceRef.current += 1;
      autonomousResumeActiveRef.current = false;
      move.stop();
      const destination = upperRightRestDestination();
      emitOrbRuntimeEvent("rest_started", { destination });
      void move.start({
        x: destination.x,
        y: destination.y,
        transition: { duration: 1.8, ease: [0.37, 0, 0.22, 1] },
      }).then(() => {
        positionRef.current = destination;
        emitOrbRuntimeEvent("rest_complete", { destination });
      }).finally(() => {
        restTransitionActiveRef.current = false;
      });
    }, 240);
    return () => window.clearInterval(monitor);
  }, [move, upperRightRestDestination]);

  // Voice resources are cancelled only when this ORB component unmounts.
  useEffect(() => {
    return () => {
      speechAudioRef.current?.pause();
      pointerPingAudioRef.current?.pause();
      stopMorbTravelSound();

      if (statusTimerRef.current) {
        window.clearTimeout(statusTimerRef.current);
      }

      if (recordingStopTimerRef.current) {
        window.clearTimeout(recordingStopTimerRef.current);
      }

      stopRecordingMonitor();
      stopBrowserSpeechRecognition(true);
      activeVoiceAbortControllerRef.current?.abort();
      activeVoiceAbortControllerRef.current = null;
      voiceRequestInFlightRef.current = false;
      speechPlaybackSettlementRef.current?.cancel();
      speechPlaybackSettlementRef.current = null;

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
    {morbPointer && (
      <div
        className={`ow-v2-morb-pointer ${morbPointer.visible ? "visible" : ""} ${morbPointer.pinging ? "pinging" : ""} ${morbPointer.dissolving ? "dissolving" : ""}`}
        data-orb-morb-target={morbPointer.targetId}
        data-orb-morb-role={morbPointer.role}
        data-orb-pointer-state={pointerWaltzPhase || undefined}
        aria-hidden="true"
        style={{
          left: morbPointer.left,
          top: morbPointer.top,
          ...morbStyleVars(morbPointer.role),
        }}
        data-orb-pointer-phase={morbPointer.phase}
      />
    )}
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
      ref={orbElementRef}
      animate={move}
      className={`ow-v2-orb-position ${pointerBloom ? "is-pointing" : ""} ${greetingActive ? "is-greeting" : ""} ${morbPointer ? "has-deployed-morb" : ""} ${onboardingSafeMode ? "onboarding-safe-mode" : ""} ${className}`}
      data-orb-last-guided-target={lastGuidedTarget || undefined}
      data-orb-voice-state={voiceState}
      data-orb-resting={isResting ? "true" : "false"}
      data-orb-guidance-source={guidanceGeometrySource || undefined}
      data-orb-route={location.pathname}
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
      <div className="ow-v2-morb-orbit" aria-hidden="true">
        <span className="ow-v2-morb-orbit-dot ow-v2-morb-orbit-dot-one" />
        <span className="ow-v2-morb-orbit-dot ow-v2-morb-orbit-dot-two" />
        <span className="ow-v2-morb-orbit-dot ow-v2-morb-orbit-dot-three" />
      </div>
      {pulse && (
        <div className="ow-v2-local-pulse" key={pulse.id}>
          <motion.div
            className="ow-v2-local-bloom"
            initial={{ scale: 0.1, opacity: 0 }}
            animate={{
              scale: pulse.kind === "flare" ? [0.12, 2.05] : [0.12, 1.12],
              opacity: [0, 0.88, 0],
            }}
            transition={{
              duration: visual.duration,
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
                delay: index * 0.13,
                ease: [0.22, 0.61, 0.36, 1],
              }}
            />
          ))}

   
        </div>
      )}

      <motion.div animate={presence} style={{ transformOrigin: "center" }}>
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
      {visitorUtterance && (
        <div className="ow-v2-orb-speech" aria-live="polite" aria-label="Weaver says">
          <span>{visitorUtterance}</span>
        </div>
      )}
    </motion.div>
    {showStartupDiagnosticsPanel && statusVisible && (
      <aside className="ow-v2-startup-panel" aria-label="Startup diagnostics">
        <strong>{statusTitle}</strong>
        <p>{statusLine}</p>
        <dl className="ow-v2-startup-diagnostics">
          <div><dt>Splash</dt><dd>{startupDiagnostics.splash_state}</dd></div>
          <div><dt>Permission</dt><dd>{startupDiagnostics.permission_state}</dd></div>
          <div><dt>Greeting</dt><dd>{startupDiagnostics.greeting_state}</dd></div>
          <div><dt>Audio</dt><dd>{startupDiagnostics.audio_tts_state}</dd></div>
          <div><dt>Voice</dt><dd>{startupDiagnostics.tts_voice}</dd></div>
          <div><dt>Session</dt><dd>{startupDiagnostics.session_once_flag ? "once played" : "not played"}</dd></div>
          <div><dt>Ready</dt><dd>{startupDiagnostics.orb_readiness_state}</dd></div>
          <div><dt>Answer</dt><dd>{runtimeAnswerDiagnostics?.resolution_source || "not resolved"}</dd></div>
          <div><dt>Record</dt><dd>{runtimeAnswerDiagnostics?.fact_record_id || "none"}</dd></div>
          <div><dt>Confidence</dt><dd>{runtimeAnswerDiagnostics?.confidence?.toFixed(2) || "n/a"}</dd></div>
          <div><dt>Qwen</dt><dd>{runtimeAnswerDiagnostics?.qwen_bypassed ? "bypassed" : "used / n/a"}</dd></div>
          <div><dt>Speech</dt><dd>{runtimeAnswerDiagnostics?.cached_speech ? "cached" : "live / n/a"}</dd></div>
          <div><dt>Learning</dt><dd>{runtimeAnswerDiagnostics?.learning_candidate_state || "none"}</dd></div>
        </dl>
        {diagnosticUtterance && (
          <p className="ow-v2-diagnostic-utterance">{diagnosticUtterance}</p>
        )}
        <button
          type="button"
          className="ow-v2-startup-reset"
          onClick={speakDiagnostics}
        >
          Speak diagnostics
        </button>
        <button
          type="button"
          className="ow-v2-startup-reset"
          onClick={resetStartupSequence}
        >
          Reset first encounter
        </button>
      </aside>
    )}
    </>
  );
};

export default AutonomousOrb;
