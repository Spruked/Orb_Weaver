import React, { useCallback, useEffect, useRef, useState } from "react";
import { motion, useAnimationControls } from "framer-motion";
import { Volume2, VolumeX } from "lucide-react";
import { Orb } from "./Orb";
import {
  api,
  type WebsiteOrbExperienceContext,
  type WebsiteOrbPointerRecord,
  type WebsiteOrbTtsResponse,
} from "../services/api";
import {
  ACTIVE_ORB_PROJECT_CONTEXT_EVENT,
  ActiveOrbProjectContext,
  buildCustomerPageCapsuleUrl,
  getActiveOrbProjectContext,
} from "../orb/activeProjectContext";
import { OrbRoboticsMovementController } from "../orb/robotics/movementController";
import type { RobotCommand } from "../orb/robotics/robotMovement.types";

const wait = (ms: number) =>
  new Promise<void>((resolve) => window.setTimeout(resolve, ms));

const VOICE_UNAVAILABLE_MESSAGE = "Voice unavailable";
const POINTER_PING_AUDIO_PATH = "/orb/voice/pointer-ping.mp3";
const MORB_TRAVEL_AUDIO_PATH = "/orb/voice/travel-morb.mp3";
const MIN_RECORDING_MS = 700;
const END_SILENCE_MS = 850;
const ABSOLUTE_RECORDING_LIMIT_MS = 14000;
const SPEECH_LEVEL_THRESHOLD = 0.018;

type PulseKind = "intro" | "ripple" | "flare";
type FirstEncounterFlag =
  | "splash_complete"
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
const REST_AFTER_INACTIVITY_MS = 10 * 60 * 1000;
const ACTIVE_ORB_OPACITY = 0.94;
const REST_ORB_OPACITY = 0.55;
const FIRST_ENCOUNTER_STORAGE_KEY = "orbweaver-first-encounter-state";
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
  splash_complete: false,
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
const MORB_SIZE = 65;
const MORB_HALF = MORB_SIZE / 2;
const MORB_REUSE_DISTANCE_PX = 250;
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

const startupGreetingText = (): string => {
  return "Hi, I'm Weaver. Welcome to ORB Weaver. I'm going to show you how I listen, understand this site, and guide with verified targets.";
};

export const AutonomousOrb: React.FC<Props> = ({
  size = 190,
  className = "",
}) => {
  const onboardingSafeMode = ['/signup', '/login'].includes(window.location.pathname);
  const move = useAnimationControls();
  const surge = useAnimationControls();
  const glow = useAnimationControls();
  const presence = useAnimationControls();
  const activeRef = useRef(true);
  const reducedMotionRef = useRef(false);
  const positionRef = useRef({ x: 0, y: 0 });
  const idleHeadingRef = useRef(Math.random() * Math.PI * 2);
  const lastAutonomousDestinationRef = useRef<{ x: number; y: number } | null>(null);
  const lastAutonomousHeadingRef = useRef<number | null>(null);
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
  const pointerPingAudioRef = useRef<HTMLAudioElement | null>(null);
  const morbTravelAudioRef = useRef<HTMLAudioElement | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const speechSourceRef = useRef<AudioBufferSourceNode | null>(null);
  const speechPlaybackRef = useRef(false);
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
  const [statusVisible, setStatusVisible] = useState(false);
  const [statusTitle, setStatusTitle] = useState("ORB online");
  const [statusLine, setStatusLine] = useState("Weaver is preparing voice.");
  const [activeOrbContext, setActiveOrbContext] = useState<ActiveOrbProjectContext | null>(() => getActiveOrbProjectContext());
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
  const [morbPointer, setMorbPointer] = useState<MorbPointerState | null>(null);
  const [pointerWaltzPhase, setPointerWaltzPhase] = useState<PointerWaltzPhase | null>(null);
  const [greetingActive, setGreetingActive] = useState(false);

  const markFirstEncounter = useCallback((flag: FirstEncounterFlag) => {
    const next = { ...firstEncounterStateRef.current, [flag]: true };
    firstEncounterStateRef.current = next;
    window.sessionStorage.setItem(FIRST_ENCOUNTER_STORAGE_KEY, JSON.stringify(next));
  }, []);

  const firstEncounterComplete = useCallback(() => {
    const state = firstEncounterStateRef.current;
    return (
      state.splash_complete &&
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
      return false;
    }

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
        setPointerWaltzPhase("RECOVERY");
        movement.cancel("target_lost_after_scroll");
        return false;
      }
      activeRect = refreshed;
    }

    const latestGoal = movement.getLatestGoal();
    const targetCenterX = latestGoal.normalizedX * window.innerWidth;
    const targetCenterY = latestGoal.normalizedY * window.innerHeight;
    const side = targetCenterX < window.innerWidth / 2 ? 1 : -1;
    const guidedDestination = clampPosition(
      targetCenterX + side * Math.max(84, size * 0.62) - size / 2,
      targetCenterY - size / 2,
    );
    const current = positionRef.current;
    const destination = options.launchMorbOnly ? current : guidedDestination;
    const distance = Math.hypot(destination.x - current.x, destination.y - current.y);
    avoidUntilRef.current = Date.now() + 900;
    if (!options.launchMorbOnly) {
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
      return false;
    }

    const finalRect = movement.refreshTarget();
    if (!finalRect) {
      setPointerWaltzPhase("RECOVERY");
      movement.cancel("target_lost_before_arrival");
      return false;
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
      return false;
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
    return true;
  }, [bumpWorldStateSequence, clampPosition, markVisitorActivity, morbPointer, move, playMorbLaunchSound, playPointerPing, size, startMorbTravelSound, stopMorbTravelSound]);

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
    speechPlaybackRef.current = true;
    freezeOrbInPlace(4200);

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
        setStatusTitle("Voice unavailable");
        setStatusLine(VOICE_UNAVAILABLE_MESSAGE);
        setVoiceState("idle");
        showStatus(3600);
        return;
      }
      if (speakerBoostRef.current) {
        await playDecodedSpeech(audioUrl);
        speechPlaybackRef.current = false;
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
          speechPlaybackRef.current = false;
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
      speechPlaybackRef.current = false;
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

    await speak(text, audioUrl, provider);
  }, [freezeOrbInPlace, showStatus, speak]);

  const speakRecovery = useCallback(async (text: string) => {
    setStatusLine(text);
    setStatusTitle("Voice unavailable");
    setVoiceState("idle");
    showStatus(3600);
  }, [showStatus]);

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
    if (firstEncounterRunningRef.current || firstEncounterComplete() || onboardingSafeMode) return;
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
          demonstrated_capabilities: ["Kokoro neural voice is playing", "Faster Whisper microphone path is ready"],
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
      if (!proofTarget) throw new Error("Owner-approved orientation target is unavailable");
      const guided = await guideToPointerRecord(proofTarget, "Demonstrate verified visual guidance");
      if (!guided) throw new Error("Live target verification did not complete");
      markFirstEncounter("orientation_pointer_proof_complete");

      await runGeneratedAct(
        "The verified visual-guidance target was acquired, approached, pointed to, and pinged successfully.",
        {
          phase: "agency",
          objective: "Establish agency by connecting the completed visual proof to useful next actions and invite an open, meaningful first request without asking a generic help question.",
          verified_target_id: proofTarget.target_id,
          verified_target_label: proofTarget.meaning,
          verification_state: "verified",
          demonstrated_capabilities: ["live DOM target verification", "movement", "point", "ping", "neural voice"],
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
      const inFirstEncounter = !firstEncounterComplete();
      const experience: WebsiteOrbExperienceContext | null = inFirstEncounter
        ? visitorTurn === 1
          ? {
              phase: "make_it_personal",
              objective: "Respond to the visitor's actual first request, show that it was understood in context, and guide to a verified relevant target when one exists.",
              visitor_turn: visitorTurn,
              verification_state: "pending",
              demonstrated_capabilities: ["Faster Whisper transcription", "Site World reasoning", "Kokoro neural voice"],
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
      setStatusTitle("Voice response");
      setStatusLine(spokenOutput);
      if (result.tts_error && !result.tts_audio_url) {
        setStatusTitle("Voice unavailable");
        setStatusLine(VOICE_UNAVAILABLE_MESSAGE);
      }
      const guidance = guideToPointerTarget(`${result.transcript} ${result.spoken_output}`);
      logVoice("playback", turnId);
      await speakWithGeneratedAudio(spokenOutput, result.tts_audio_url, result.tts_provider);
      const guided = await guidance;
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
      speakRecovery("I am reconnecting to my response service. Please try again in a moment.");
    } finally {
      if (activeVoiceAbortControllerRef.current === controller) {
        activeVoiceAbortControllerRef.current = null;
      }
      voiceRequestInFlightRef.current = false;
      setVoiceState("idle");
      logVoice("finalized", turnId);
    }
  }, [activeOrbContext?.project_id, contextTargetUrl, firstEncounterComplete, freezeOrbInPlace, guideToPointerTarget, logVoice, markFirstEncounter, markVisitorActivity, showStatus, speakRecovery, speakWithGeneratedAudio]);

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
  }, [freezeOrbInPlace, logVoice, monitorRecordingSilence, playPulse, processRecordedOrbAudio, showStatus, stopOrbRecording, unlockAudio, voiceState]);

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
      recordingStreamRef.current = stream;
      markFirstEncounter("voice_ready");
      return true;
    } catch {
      setStatusTitle("Microphone blocked");
      setStatusLine("Allow microphone access in the browser to talk with Weaver.");
      showStatus(5200);
      return false;
    }
  }, [markFirstEncounter, showStatus]);

  const prepareStartupVoice = useCallback((): StartupVoicePreparation => {
    if (startupVoicePreparationRef.current) return startupVoicePreparationRef.current;

    unlockAudio();
    markFirstEncounter("splash_complete");
    setStatusTitle("Opening the ORB Weaver suite");
    setStatusLine("Preparing voice permission and guidance.");
    showStatus();

    const greeting = startupGreetingText();
    const preparation: StartupVoicePreparation = {
      greeting,
      micReady: requestStartupMicrophonePermission(),
      tts: api.websiteOrbTts(greeting).catch(() => null),
    };
    startupVoicePreparationRef.current = preparation;
    return preparation;
  }, [markFirstEncounter, requestStartupMicrophonePermission, showStatus, unlockAudio]);

  const runStartupVoiceSequence = useCallback(async () => {
    if (startupAutoStartedRef.current || onboardingSafeMode) return;
    startupAutoStartedRef.current = true;
    const preparation = prepareStartupVoice();
    const micReady = await preparation.micReady;
    setGreetingActive(true);
    try {
      const tts = await preparation.tts;
      if (!tts?.tts_audio_url) throw new Error("Startup voice synthesis failed");
      const spokenGreeting = speak(preparation.greeting, tts.tts_audio_url, tts.tts_provider);
      void guideToPointerRecord(SUITE_LOGO_POINTER_RECORD, "ORB Weaver suite", { launchMorbOnly: true });
      await spokenGreeting;
      markFirstEncounter("entrance_complete");
    } catch {
      await speakRecovery(preparation.greeting);
      markFirstEncounter("entrance_complete");
    } finally {
      setGreetingActive(false);
    }

    await runFirstEncounterChoreography();
    if (micReady && activeRef.current) {
      handsFreeEnabledRef.current = true;
      window.setTimeout(() => {
        if (!activeRef.current || voiceRequestInFlightRef.current) return;
        void startOrbRecording();
      }, 420);
    }
  }, [guideToPointerRecord, markFirstEncounter, onboardingSafeMode, prepareStartupVoice, runFirstEncounterChoreography, setGreetingActive, speak, speakRecovery, startOrbRecording]);

  // Keep the autonomous loop mounted. Voice state changes are frequent and must not replay
  // the entrance sequence or reset Weaver's position.
  useEffect(() => {
    prepareStartupVoiceRef.current = prepareStartupVoice;
    runStartupVoiceSequenceRef.current = runStartupVoiceSequence;
  }, [prepareStartupVoice, runStartupVoiceSequence]);

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
    if (!handsFreeEnabledRef.current || voiceState !== "idle" || onboardingSafeMode) return;
    if (voiceRequestInFlightRef.current || recorderRef.current || firstEncounterRunningRef.current) return;
    if (!firstEncounterStateRef.current.voice_ready) return;

    const rearmTimer = window.setTimeout(() => {
      if (!activeRef.current || voiceRequestInFlightRef.current || recorderRef.current) return;
      void startOrbRecording();
    }, 720);

    return () => window.clearTimeout(rearmTimer);
  }, [onboardingSafeMode, startOrbRecording, voiceState]);

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
  }, [activeOrbContext?.canonical_domain, bumpWorldStateSequence, guideToPointerTarget]);

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
      prepareStartupVoiceRef.current();

      if (reducedMotionRef.current) {
        surge.set({ scale: 1, opacity: 1 });
        setPulse({ id: Date.now(), kind: "intro" });
        void runStartupVoiceSequenceRef.current();
        return;
      }

      surge.set({ scale: 0.26, opacity: 0, x: window.innerWidth * 0.42, rotate: 10 });
      setPulse({ id: Date.now(), kind: "intro" });
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

      setPulse(null);
      void runStartupVoiceSequenceRef.current();

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
          !speechPlaybackRef.current &&
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

        if (speechPlaybackRef.current) {
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
  }, [clampPosition, glow, move, nextDestination, playLocalPresence, presence, size, stopRecordingMonitor, surge, upperRightRestDestination]);

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
      animate={move}
      className={`ow-v2-orb-position ${pointerBloom ? "is-pointing" : ""} ${greetingActive ? "is-greeting" : ""} ${morbPointer ? "has-deployed-morb" : ""} ${onboardingSafeMode ? "onboarding-safe-mode" : ""} ${className}`}
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
