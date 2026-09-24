import { createInitialJourneyState, loadJourneyState, migrateStoredJourneyState, saveJourneyState, WEBSITE_JOURNEY_STORAGE_KEY, type WebsiteJourneyStateV2 } from "../state/tourControllerStore";
import { TOUR_POINTER_TARGETS, TOUR_STOP_SOURCE_SELECTORS } from "../tour/curriculum";
import { runTourController, isTourDecisionReady } from "../tour/controller";
import { createTourAgencyRuntime } from "../tour/agencyRuntime";
import { parseChapterEvaluation } from "../tour/evaluator";
import type { TourDecisionAction, TourEngagementQuestion } from "../types/tour";
import React, { useCallback, useEffect, useRef, useState } from "react";
import { motion, useAnimationControls } from "framer-motion";
import { Volume2, VolumeX } from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";
import { Orb } from "./Orb";
import {
  api,
  ApiError,
  authStore,
  type WebsiteOrbExperienceContext,
  type WebsiteOrbPointerRecord,
  type PublicPreflightReport,
  type WebsiteOrbTtsResponse,
  type WebsiteOrbVoiceResponse,
  type WebsiteOrbPageCapsule,
} from "../services/api";
import travelMorbAsset from "../assets/sound_files/travelmorb.mp3";
import {
  ACTIVE_ORB_PROJECT_CONTEXT_EVENT,
  ActiveOrbProjectContext,
  buildCustomerPageCapsuleUrl,
  getActiveOrbProjectContext,
} from "../orb/activeProjectContext";
import { OrbRoboticsMovementController } from "../orb/robotics/movementController";
import { authorizeMovement, assertMovementAuthorization } from "../orb/robotics/movementPolicy";
import type { RobotCommand } from "../orb/robotics/robotMovement.types";
import { buildLidarGuidanceMap, Lidar2DMappingCoordinateCache } from "../orb/lidar_2d_mapping";
import {
  awaitAbortable,
  createPlaybackSettlement,
  type PlaybackSettlement,
  runBackendRecovery,
  shouldRearmVoice,
  shouldRunMountedStartupVoiceSequence,
} from "../orb/voiceLifecycle";
import { canAdvanceCaptionProgression, currentSpeechCaption } from "../orb/speechCaptions";
import { SITE_TOUR_SCRIPT, scriptedPageOrientation, type ScriptedOrientationStep } from "../orb/scriptedOrientation";
import { resolveDirectRouteNavigation, type VerifiedRouteNavigation } from "../orb/directRouteNavigation";
import { developmentFullTourOverride, developmentLlmScriptedTourOverride, emitDevelopmentStartupTrace, tourEligibleForAccount } from "./startupDevelopment";

const wait = (ms: number) =>
  new Promise<void>((resolve) => window.setTimeout(resolve, ms));

const VOICE_UNAVAILABLE_MESSAGE = "Voice unavailable";
const POINTER_PING_AUDIO_PATH = "/orb/voice/pointer-ping.mp3";
const MORB_TRAVEL_AUDIO_PATHS = [
  "/orb/voice/travel-morb.mp3",
  "/orb/voice/travel_morb2.mp3",
  travelMorbAsset,
];
const MIN_RECORDING_MS = 700;
const END_SILENCE_MS = 2200;
const ABSOLUTE_RECORDING_LIMIT_MS = 22000;
const SPEECH_LEVEL_THRESHOLD = 0.018;
const LIDAR_DRIFT_THRESHOLD_PX = 12;
const ORB_SPEECH_PLAYBACK_RATE = 0.9;
// Keep the authored site tour brisk without changing the intro or live visitor
// responses. Pitch remains preserved by the media element.
const TOUR_SPEECH_PLAYBACK_RATE = 1.08;
// Give the browser and the visitor a short, explicit boundary between the
// authored landing introduction and the first governed tour action. The
// startup gate still owns permission/readiness; this is only presentation
// settling after the intro's audio-ended proof.
const INTRO_TO_TOUR_SETTLE_MS = 650;
const SCRIPTED_STEP_MIN_DWELL_MS = 2200;
const ACCOUNT_CREATION_GUIDE_PROTOCOL = [
  "Guide the current account form one relevant question or field at a time using the server-owned Nine of Clubs policy.",
  "Preserve visitor control and keep credentials private.",
].join(" ");
const TOUR_INTERRUPTION_GUIDE_PROTOCOL = [
  "Answer the visitor's question or chosen next step using the server-owned Nine of Clubs policy.",
  "The authored tour is paused; do not resume it without their request.",
].join(" ");

const resolveTourDecisionAction = (text: string): TourDecisionAction | null => {
  const normalized = text.toLowerCase().replace(/[’']/g, "'").replace(/[^a-z0-9\s']/g, " ").replace(/\s+/g, " ").trim();
  if (/\b(preflight|scan|start|begin|let's do it|lets do it|yes)\b/.test(normalized)) return "RUN_PREFLIGHT_NOW";
  if (/\b(not now|later|continue exploring|keep exploring|skip|no thanks|no)\b/.test(normalized)) return "DEFER_PREFLIGHT";
  return null;
};

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
type MorbTrajectory = "direct" | "swirl" | "dart_orbit";
type SpeechCaptionPhase = "idle" | "speaking" | "complete" | "interrupted";
type SpeechCaptionState = {
  fullText: string;
  revealedText: string;
  phase: SpeechCaptionPhase;
  collapsed: boolean;
  expanded: boolean;
};
type MorbPointerState = {
  targetId: string;
  role: MorbWorkRole;
  left: number;
  top: number;
  visible: boolean;
  pinging: boolean;
  dissolving: boolean;
  phase: PointerWaltzPhase;
  trajectory: MorbTrajectory;
};

type PulseState = {
  id: number;
  kind: PulseKind;
} | null;

type AmbientVantagePreference = {
  route: string;
  x: number;
  y: number;
  confidence: number;
};

type OrbVoiceState = "idle" | "listening" | "thinking" | "speaking";
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
const ORB_OVERLAY_Z_INDEX = 2147483640;
const EDGE = 8;
// Keep Weaver visibly alive between guided actions without entering a target,
// speaking over the visitor, or compromising the LiDAR-safe movement path.
const AMBIENT_TRAVEL_PX_PER_SECOND = 42;
const AMBIENT_INITIAL_DWELL_MS = 5200;
// Weaver is a host, not a parked overlay. Keep its LiDAR-approved ambient
// cadence visible enough to leave reading space clear without becoming noisy.
const AMBIENT_SETTLE_MIN_MS = 2800;
const AMBIENT_SETTLE_VARIANCE_MS = 2200;
// After a page change, clear reading content promptly.  The LiDAR map chooses
// the destination; this is a short settle, not a decorative hover delay.
const AMBIENT_POST_INTERACTION_DWELL_MS = 800;
const LIDAR_SAFETY_PADDING_PX = 16;
const LIDAR_INTERACTIVE_EXCLUSION_MARGIN_PX = 20;
// Weaver is a website presence, never a corner widget. Keep every legal
// pose substantially inside the page so the visitor reads her as an active
// host rather than a chat bubble docked to an edge.
const CORNER_EXCLUSION_MARGIN_PX = 160;
const REST_AFTER_INACTIVITY_MS = 10 * 60 * 1000;
const ACTIVE_ORB_OPACITY = 0.96;
const REST_ORB_OPACITY = 0.60;
const FIRST_ENCOUNTER_STORAGE_KEY = "orbweaver-first-encounter-state";
const STARTUP_GREETING_SESSION_KEY = "orbweaver-startup-greeting-played";
const LANDING_SPLASH_SESSION_KEY = "orbweaver-landing-splash-played";
const LANDING_SPLASH_COMPLETE_SESSION_KEY = "orbweaver-landing-splash-complete";
const LANDING_STARTUP_READINESS_SESSION_KEY = "orbweaver-landing-startup-readiness";
const SCRIPTED_ORIENTATION_SESSION_KEY = "orbweaver-scripted-orientation-v1";
const AMBIENT_VANTAGE_STORAGE_KEY = "orbweaver-ambient-vantage";
const STARTUP_GATE_COMPLETE_EVENT = "orbweaver:startup-gate-complete";
const INTRO_SPEECH_STATE_DATASET_KEY = "orbWeaverIntroVoiceState";
const startupUnresolved = () => isPublicLandingExperience() && window.sessionStorage.getItem(LANDING_SPLASH_COMPLETE_SESSION_KEY) !== '1';
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
const ONBOARDING_CONTINUATION_STORAGE_KEY = "orbweaver-onboarding-continuation";
const ONBOARDING_ROUTE = "/signup";
const ONBOARDING_FIRST_TARGET_ID = "full-name-field";
type OnboardingContinuation = {
  destination: string;
  firstTargetId: string;
  approvedAt: number;
  guidedAt?: number;
};

const readOnboardingContinuation = (): OnboardingContinuation | null => {
  try {
    const raw = window.sessionStorage.getItem(ONBOARDING_CONTINUATION_STORAGE_KEY);
    if (!raw) return null;
    const value = JSON.parse(raw) as Partial<OnboardingContinuation>;
    return typeof value.destination === "string" && typeof value.firstTargetId === "string" &&
      typeof value.approvedAt === "number"
      ? { destination: value.destination, firstTargetId: value.firstTargetId, approvedAt: value.approvedAt, guidedAt: value.guidedAt }
      : null;
  } catch {
    return null;
  }
};

const saveOnboardingContinuation = (continuation: OnboardingContinuation): boolean => {
  try {
    window.sessionStorage.setItem(ONBOARDING_CONTINUATION_STORAGE_KEY, JSON.stringify(continuation));
    return true;
  } catch {
    return false;
  }
};

const onboardingFirstTargetRecord = (): WebsiteOrbPointerRecord => ({
  target_id: ONBOARDING_FIRST_TARGET_ID,
  page_route: ONBOARDING_ROUTE,
  target_type: "form_field",
  meaning: "Full name",
  direct_aliases: ["full name", "name field"],
  intent_aliases: ["start onboarding", "begin account creation"],
  content_fingerprint: "onboarding:full-name-field:live-route",
  semantic_locator: '[data-orb-target="full-name-field"]',
  confidence: 1,
  confidence_class: "VERIFIED",
  pointer_health: "OWNER_VERIFIED",
  structural_context: { tag: "input" },
  runtime_policy: { may_point: true, requires_live_verification: true },
});
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
const MORB_SIZE = 48;
const MORB_HALF = MORB_SIZE / 2;
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

const morbTrajectoryForGuidance = (guidanceSequence: number): MorbTrajectory => {
  // Keep the ordinary direct path common. The other patterns appear often
  // enough to feel alive, but are deterministic for a given guidance turn.
  const variant = guidanceSequence % 5;
  if (variant === 1) return "swirl";
  if (variant === 3) return "dart_orbit";
  return "direct";
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
  // The ORB and LandingPage are sibling mounts. Do not require a section
  // rendered by the sibling before starting the root-route showroom lifecycle.
  window.location.pathname === "/";

const readAmbientVantagePreference = (): AmbientVantagePreference | null => {
  try {
    const value = window.sessionStorage.getItem(AMBIENT_VANTAGE_STORAGE_KEY);
    if (!value) return null;
    const parsed = JSON.parse(value) as AmbientVantagePreference;
    return Number.isFinite(parsed.x) && Number.isFinite(parsed.y) && typeof parsed.route === "string"
      ? parsed
      : null;
  } catch {
    return null;
  }
};

const startupGreetingText = (): string => {
  // The splash is a neutral entry point. The governed ORIENT turn provides
  // the contextual, naturally worded product orientation that follows.
  return "Welcome. I am Weaver. Let’s begin together.";
};

const normalizeOrbDialogue = (text: string): string => text
  .replace(/\*/g, "")
  .replace(/\bI am Weaver(?:,? the)? (?:male )?(?:Orb Weaver )?Website Assistant\.?/gi, "I am Weaver.")
  .replace(/\s+([,.!?])/g, "$1")
  .replace(/\s{2,}/g, " ")
  .trim();

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
  const orbSpin = useAnimationControls();
  const glow = useAnimationControls();
  const presence = useAnimationControls();
  const activeRef = useRef(true);
  const reducedMotionRef = useRef(false);
  const positionRef = useRef({ x: 0, y: 0 });
  const orbRotationRef = useRef(0);
  const orbElementRef = useRef<HTMLDivElement | null>(null);
  const motionInterruptionSequenceRef = useRef(0);
  const idleHeadingRef = useRef(-Math.PI / 2);
  const lastAutonomousDestinationRef = useRef<{ x: number; y: number } | null>(null);
  const ambientPoseHistoryRef = useRef<{ x: number; y: number }[]>([]);
  const ambientVantageRef = useRef<AmbientVantagePreference | null>(readAmbientVantagePreference());
  const movementControllerRef = useRef<OrbRoboticsMovementController | null>(null);
  const nudgePointerRef = useRef<{ pointerId: number; start: { x: number; y: number }; origin: { x: number; y: number } } | null>(null);
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
  // Route-local records are locators for freshly rendered first-party UI. They
  // never modify the canonical crawl pointer map and remain non-authoritative
  // until the existing movement controller verifies their live DOM target.
  const onboardingLiveRecordRef = useRef<WebsiteOrbPointerRecord | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<BlobPart[]>([]);
  const recordingStreamRef = useRef<MediaStream | null>(null);
  const recordingStopTimerRef = useRef<number | null>(null);
  const recordingCancelledRef = useRef(false);
  const speechAudioRef = useRef<HTMLAudioElement | null>(null);
  const latencyAudioRef = useRef<HTMLAudioElement | null>(null);
  const pointerPingAudioRef = useRef<HTMLAudioElement | null>(null);
  const morbTravelAudioRef = useRef<HTMLAudioElement | null>(null);
  const morbTravelAudioIndexRef = useRef(0);
  const audioContextRef = useRef<AudioContext | null>(null);
  const speechSourceRef = useRef<AudioBufferSourceNode | null>(null);
  const speechAnalyserRef = useRef<AnalyserNode | null>(null);
  const speechVisualizerFrameRef = useRef<number | null>(null);
  const speechVisualizerActiveRef = useRef(false);
  const mediaSpeechSourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const mediaSpeechElementRef = useRef<HTMLAudioElement | null>(null);
  const speechPlaybackSettlementRef = useRef<PlaybackSettlement | null>(null);
  const speechPlaybackRef = useRef(false);
  const captionFrameRef = useRef<number | null>(null);
  const captionCollapseTimerRef = useRef<number | null>(null);
  const captionPlaybackCancelledRef = useRef(false);
  const audioUnlockedRef = useRef(false);
  const statusTimerRef = useRef<number | null>(null);
  const avoidUntilRef = useRef(0);
  const voiceRequestInFlightRef = useRef(false);
  // A governed 503 is a pause, not a transient microphone failure. It must
  // suppress hands-free rearming until the visitor explicitly retries.
  const cognitionUnavailableRef = useRef(false);
  const activeVoiceAbortControllerRef = useRef<AbortController | null>(null);
  const voiceTurnIdRef = useRef(0);
  const recordingMonitorTimerRef = useRef<number | null>(null);
  const recordingStartedAtRef = useRef(0);
  const speechDetectedRef = useRef(false);
  const silenceStartedAtRef = useRef<number | null>(null);
  const speechRecognitionRef = useRef<any>(null);
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
  const navigate = useNavigate();
  // The documented dev reset must reset the journey as well as the splash.
  // Otherwise a prior pending question or paused state survives the visual
  // reset and blocks the fresh ORIENT -> DISCOVER handoff.
  const startupResetRequestedRef = useRef(new URLSearchParams(window.location.search).get('orbStartupReset') === '1');
  const [journeyBoot] = useState(() => startupResetRequestedRef.current
    ? { status: 'initial' as const, state: createInitialJourneyState() }
    : loadJourneyState());
  const websiteJourneyRef = useRef<WebsiteJourneyStateV2 | null>(journeyBoot.state);
  const [, setTourState] = useState<WebsiteJourneyStateV2 | null>(journeyBoot.state);
  // This is visitor-facing operational state. It must not be silently dropped
  // when a governed dependency pauses the tour.
  const [tourNotice, setTourNotice] = useState('');
  // loadJourneyState() has already validated the initial in-memory snapshot.
  // Mark it ready immediately so the startup intro cannot request the tour
  // before the migration effect gets a chance to run.
  const journeyReadyRef = useRef(Boolean(journeyBoot.state));
  const landingTourRunningRef = useRef(false);
  const landingTourSettledRef = useRef<Promise<void>>(Promise.resolve());
  const landingTourAbortControllerRef = useRef<AbortController | null>(null);
  const scriptedOrientationRunningRef = useRef(false);
  const scriptedOrientationInterruptedRef = useRef(false);
  const scriptedLandingOpeningCompleteRef = useRef(false);
  const liveTourReadyRef = useRef(window.sessionStorage.getItem(LANDING_STARTUP_READINESS_SESSION_KEY) === "READY");
  const routeArrivalInFlightRef = useRef<string | null>(null);
  const pendingDirectRouteGuidanceRef = useRef<VerifiedRouteNavigation | null>(null);
  const agencyRuntimeRef = useRef<ReturnType<typeof createTourAgencyRuntime> | null>(null);
  const handsFreeEnabledRef = useRef(false);
  const [pulse, setPulse] = useState<PulseState>(null);
  const [voiceState, setVoiceState] = useState<OrbVoiceState>("idle");
  const [speechAmplitude, setSpeechAmplitude] = useState(0);
  const [orbEyeDirection, setOrbEyeDirection] = useState({ x: 0, y: 0 });
  const [voiceRearmSequence, setVoiceRearmSequence] = useState(0);
  const [statusVisible, setStatusVisible] = useState(false);
  const [statusTitle, setStatusTitle] = useState("ORB online");
  const [statusLine, setStatusLine] = useState("Weaver is preparing voice.");
  const [speechCaption, setSpeechCaption] = useState<SpeechCaptionState>({
    fullText: "",
    revealedText: "",
    phase: "idle",
    collapsed: false,
    expanded: false,
  });
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
  // Guidance is an async operation. Keep the currently rendered MORB in a ref
  // so a cosmetic MORB state update cannot recreate the guidance callback and
  // abort a route-continuation effect midway through a verified arrival.
  const morbPointerRef = useRef<MorbPointerState | null>(null);
  const [pointerWaltzPhase, setPointerWaltzPhase] = useState<PointerWaltzPhase | null>(null);
  const [greetingActive, setGreetingActive] = useState(false);
  const [showStartupDiagnosticsPanel] = useState(() => startupDiagnosticsPanelEnabled());
  const [startupDiagnostics, setStartupDiagnostics] = useState<StartupDiagnostics>(() => initialStartupDiagnostics());
  const [runtimeAnswerDiagnostics, setRuntimeAnswerDiagnostics] = useState<RuntimeAnswerDiagnostics | null>(null);
  const preflightNarratedReportRef = useRef<string | null>(null);
  const preflightWalkthroughAbortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    morbPointerRef.current = morbPointer;
  }, [morbPointer]);

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

  const saveWebsiteJourney = useCallback((next: WebsiteJourneyStateV2) => {
    if (!saveJourneyState(next)) throw new Error("Your tour progress could not be saved. Please enable session storage to continue.");
    websiteJourneyRef.current = next;
    agencyRuntimeRef.current?.invalidatePosition();
    setTourState(next);
    emitOrbRuntimeEvent("website_journey_state", next as unknown as Record<string, unknown>);
    return next;
  }, []);

  useEffect(() => {
    // The V1 reader/writer has now been retired. Only known mappings are promoted.
    if (startupResetRequestedRef.current) {
      try {
        saveWebsiteJourney(createInitialJourneyState());
        journeyReadyRef.current = true;
      } catch (error) {
        setTourNotice(error instanceof Error ? error.message : "Tour storage is unavailable.");
      }
      return;
    }
    const loaded = migrateStoredJourneyState();
    if (!loaded.state) {
      setTourNotice("Your saved tour position is preserved, but cannot be resumed yet.");
      return;
    }
    try {
      saveWebsiteJourney(loaded.state);
      journeyReadyRef.current = true;
    } catch (error) {
      setTourNotice(error instanceof Error ? error.message : "Tour storage is unavailable.");
    }
  }, [saveWebsiteJourney]);

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
  const interiorX = Math.min(CORNER_EXCLUSION_MARGIN_PX, Math.max(EDGE, Math.floor((window.innerWidth - size) / 2) - EDGE));
  const interiorY = Math.min(CORNER_EXCLUSION_MARGIN_PX, Math.max(EDGE, Math.floor((window.innerHeight - size) / 2) - EDGE));
  const boundedMinX = Math.max(minX, interiorX);
  const boundedMinY = Math.max(minY, interiorY);
  const boundedMaxX = Math.max(boundedMinX, window.innerWidth - size - interiorX);
  const boundedMaxY = Math.max(boundedMinY, window.innerHeight - size - interiorY);

  return {
    minX: boundedMinX,
    minY: boundedMinY,
    maxX: boundedMaxX,
    maxY: boundedMaxY,
  };
}, [size]);
  const clampPosition = useCallback((x: number, y: number) => {
    const { minX, minY, maxX, maxY } = bounds();

    return {
      x: Math.max(minX, Math.min(x, maxX)),
      y: Math.max(minY, Math.min(y, maxY)),
    };
  }, [bounds]);

  const travelOrbAlongCurve = useCallback(async (
    destination: { x: number; y: number },
    mode: "glide" | "swirl",
    signal?: AbortSignal,
    safeControlPoint?: { x: number; y: number } | null,
  ) => {
    const current = positionRef.current;
    const dx = destination.x - current.x;
    const dy = destination.y - current.y;
    const distance = Math.hypot(dx, dy);
    const duration = mode === "swirl"
      ? Math.max(1.8, Math.min(5.8, distance / 118))
      : Math.max(2.4, Math.min(7.2, distance / 92));
    const pathLength = Math.max(1, distance);
    const normalX = -dy / pathLength;
    const normalY = dx / pathLength;
    const bend = mode === "swirl"
      ? Math.min(180, Math.max(72, distance * 0.24))
      : Math.min(112, Math.max(42, distance * 0.18));
    const direction = ((Math.round(current.x + current.y) + guidanceSequenceRef.current) % 2 === 0) ? 1 : -1;
    const midpoint = {
      x: (current.x + destination.x) / 2 + normalX * bend * direction,
      y: (current.y + destination.y) / 2 + normalY * bend * direction,
    };
    const control = safeControlPoint || clampPosition(midpoint.x, midpoint.y);
    const restingRotation = orbRotationRef.current;
    const spinTransit = mode === "swirl" && guidanceSequenceRef.current % 3 === 0;
    const spiralTransit = mode === "swirl" && !spinTransit;
    const spinPeak = restingRotation + direction * (spinTransit ? 2880 : 0);
    const useCurve = distance >= 80 && Boolean(safeControlPoint);
    const lateralX = control.x - ((current.x + destination.x) / 2);
    const lateralY = control.y - ((current.y + destination.y) / 2);
    // A multi-point S path makes the transit read as deliberate body movement
    // instead of a translated DOM node. The control point is still chosen by
    // the caller's live LiDAR pass; the extra points stay inside that corridor.
    const transitPoints = useCurve
      ? spiralTransit
        ? [
          current,
          { x: current.x + dx * 0.14 + lateralX * 0.24, y: current.y + dy * 0.14 + lateralY * 0.24 },
          { x: current.x + dx * 0.3 + lateralX * 0.72, y: current.y + dy * 0.3 + lateralY * 0.72 },
          { x: current.x + dx * 0.46 - lateralX * 0.7, y: current.y + dy * 0.46 - lateralY * 0.7 },
          { x: current.x + dx * 0.63 + lateralX * 0.58, y: current.y + dy * 0.63 + lateralY * 0.58 },
          { x: current.x + dx * 0.8 - lateralX * 0.34, y: current.y + dy * 0.8 - lateralY * 0.34 },
          destination,
        ].map((point) => clampPosition(point.x, point.y))
        : [
          current,
          { x: current.x + dx * 0.24 + lateralX * 0.52, y: current.y + dy * 0.24 + lateralY * 0.52 },
          { x: current.x + dx * 0.5 - lateralX * 0.38, y: current.y + dy * 0.5 - lateralY * 0.38 },
          { x: current.x + dx * 0.76 + lateralX * 0.22, y: current.y + dy * 0.76 + lateralY * 0.22 },
          destination,
        ].map((point) => clampPosition(point.x, point.y))
      : [current, destination];
    const xFrames = transitPoints.map((point) => point.x);
    const yFrames = transitPoints.map((point) => point.y);
    const times = transitPoints.length === 7
      ? [0, 0.14, 0.3, 0.46, 0.63, 0.8, 1]
      : transitPoints.length === 5 ? [0, 0.2, 0.48, 0.76, 1] : [0, 1];

    emitOrbRuntimeEvent("orb_transit_started", {
      mode,
      distance,
      duration,
      control,
      path: useCurve ? (spiralTransit ? "spiral" : "serpentine") : "short_glide",
      rotation: spinTransit ? spinPeak : restingRotation,
    });
    if (spinTransit) {
      emitOrbRuntimeEvent("orb_spin_up_started", { restingRotation, spinPeak });
      await awaitAbortable(orbSpin.start({
        rotateY: spinPeak,
        transition: { duration: 0.52, ease: "easeIn" },
      }), signal);
      emitOrbRuntimeEvent("orb_spin_up_completed", { spinPeak });
    }
    await awaitAbortable(move.start({
      x: xFrames,
      y: yFrames,
      transition: { duration, ease: "easeInOut", times },
    }), signal);
    if (spinTransit) {
      emitOrbRuntimeEvent("orb_spin_down_started", { restingRotation });
      await awaitAbortable(orbSpin.start({
        rotateY: restingRotation,
        transition: { duration: 0.42, ease: "easeOut" },
      }), signal);
      emitOrbRuntimeEvent("orb_spin_down_completed", { restingRotation });
    }
    orbRotationRef.current = restingRotation;
    emitOrbRuntimeEvent("orb_transit_arrived", { mode, distance, restingRotation });
  }, [clampPosition, move, orbSpin]);

  const splashAlignedPosition = useCallback(() => (
    clampPosition(
      window.innerWidth * 0.66 - size / 2,
      window.innerHeight * 0.37 - size / 2,
    )
  ), [clampPosition, size]);

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

  // A completed response, guided action, or TAMP Out is a handoff back to
  // ambient presence. Record the current resting pose as recently used and
  // discard the soft vantage preference so the next LiDAR pass must acquire a
  // meaningfully different live pose.
  const invalidateAmbientPose = useCallback((reason: string) => {
    const rect = orbElementRef.current?.getBoundingClientRect();
    const current = rect ? { x: rect.left, y: rect.top } : positionRef.current;
    positionRef.current = current;
    ambientPoseHistoryRef.current = [
      ...ambientPoseHistoryRef.current.filter((pose) => Math.hypot(pose.x - current.x, pose.y - current.y) > 1),
      current,
    ].slice(-4);
    ambientVantageRef.current = null;
    lastAutonomousDestinationRef.current = null;
    window.sessionStorage.removeItem(AMBIENT_VANTAGE_STORAGE_KEY);
    emitOrbRuntimeEvent("lidar_pose_invalidated", { reason, current });
  }, []);

  const authorizeMotion = useCallback((destination: { x: number; y: number }, intent: string) => {
    const result = authorizeMovement({
      destination,
      current: positionRef.current,
      viewport: { width: window.innerWidth, height: window.innerHeight },
      orbSize: size,
      speechActive: speechPlaybackRef.current,
      dormant: restModeRef.current,
      worldStateSequence: worldStateSequenceRef.current,
      intent,
    });
    if (!result.ok) {
      emitOrbRuntimeEvent("movement_policy_blocked", { reason: result.reason, intent });
      return null;
    }
    emitOrbRuntimeEvent("movement_policy_authorized", {
      intent,
      movement_doctrine_version: result.authorization.movementDoctrineVersion,
      movement_policy_version: result.authorization.movementPolicyVersion,
      governance_trace_id: result.authorization.governanceTraceId,
      world_state_sequence: worldStateSequenceRef.current,
    });
    return result.authorization;
  }, [size]);

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
    const path = MORB_TRAVEL_AUDIO_PATHS[morbTravelAudioIndexRef.current % MORB_TRAVEL_AUDIO_PATHS.length];
    morbTravelAudioIndexRef.current += 1;
    const audio = morbTravelAudioRef.current || new Audio(path);
    if (audio.src !== new URL(path, window.location.href).href) audio.src = path;
    audio.pause();
    audio.currentTime = 0;
    audio.loop = true;
    audio.volume = speakerBoostRef.current ? 0.34 : 0.24;
    morbTravelAudioRef.current = audio;
    void audio.play().catch(() => undefined);
  }, []);

  const stopMorbTravelSound = useCallback(() => {
    const audio = morbTravelAudioRef.current;
    if (!audio) return;
    audio.pause();
    audio.currentTime = 0;
  }, []);

  const nextDestination = useCallback(() => {
    const current = positionRef.current;
    const minimumTravel = Math.max(56, Math.min(92, size * 0.45));
    // A route can place the ORB directly over a paragraph.  Permit one
    // deliberate relocation to a clear edge instead of trapping it in copy.
    const maximumTravel = Math.hypot(window.innerWidth, window.innerHeight);
    const lidarMap = buildLidarGuidanceMap({
      orbPosition: { x: current.x + size / 2, y: current.y + size / 2 },
    });
    const { minX, minY, maxX, maxY } = bounds();
    const preference = ambientVantageRef.current?.route === lidarMap.route
      ? ambientVantageRef.current
      : null;
    const relevantFeatures = lidarMap.features.filter((feature) => (
      feature.visible &&
      feature.pointerEvents !== "none" &&
      (feature.hardExclusion || (!feature.occluded && ["interactive", "text_block", "image"].includes(feature.kind)))
    ));
    const intersects = (a: { left: number; top: number; right: number; bottom: number }, b: { x: number; y: number; width: number; height: number }) =>
      Math.max(0, Math.min(a.right, b.x + b.width) - Math.max(a.left, b.x)) *
      Math.max(0, Math.min(a.bottom, b.y + b.height) - Math.max(a.top, b.y));
    const currentOrbRect = orbElementRef.current?.getBoundingClientRect();
    const captionElement = document.querySelector<HTMLElement>('[data-orb-caption-state]');
    const captionRect = captionElement?.getBoundingClientRect();
    const captionOffset = currentOrbRect && captionRect
      ? {
        x: captionRect.left - currentOrbRect.left,
        y: captionRect.top - currentOrbRect.top,
        width: captionRect.width,
        height: captionRect.height,
      }
      : null;
    const renderedFootprint = (candidate: { x: number; y: number }) => {
      const body = {
        left: candidate.x,
        top: candidate.y,
        right: candidate.x + size,
        bottom: candidate.y + size,
      };
      const footprint = captionOffset
        ? {
          left: Math.min(body.left, candidate.x + captionOffset.x),
          top: Math.min(body.top, candidate.y + captionOffset.y),
          right: Math.max(body.right, candidate.x + captionOffset.x + captionOffset.width),
          bottom: Math.max(body.bottom, candidate.y + captionOffset.y + captionOffset.height),
        }
        : body;
      return {
        left: footprint.left - LIDAR_SAFETY_PADDING_PX,
        top: footprint.top - LIDAR_SAFETY_PADDING_PX,
        right: footprint.right + LIDAR_SAFETY_PADDING_PX,
        bottom: footprint.bottom + LIDAR_SAFETY_PADDING_PX,
      };
    };

    const candidates: Array<{
      point: { x: number; y: number };
      score: number;
      collisions: number;
      textCollisions: number;
      interactiveCollisions: number;
    }> = [];
    for (let row = 0; row < 7; row += 1) {
      for (let column = 0; column < 9; column += 1) {
        const candidate = clampPosition(
          minX + (maxX - minX) * (column / 8),
          minY + (maxY - minY) * (row / 6),
        );
        const actualTravel = Math.hypot(candidate.x - current.x, candidate.y - current.y);
        const candidateCenter = { x: candidate.x + size / 2, y: candidate.y + size / 2 };
        const rect = renderedFootprint(candidate);
        const collisions = relevantFeatures.reduce((total, feature) => total + intersects(rect, feature.rect), 0);
        const textCollisions = relevantFeatures
          .filter((feature) => feature.kind === "text_block")
          .reduce((total, feature) => total + intersects(rect, feature.rect), 0);
        const interactiveCollisions = relevantFeatures
          .filter((feature) => feature.hardExclusion || feature.kind === "interactive")
          .reduce((total, feature) => total + intersects(
            rect,
            feature.hardExclusion
              ? {
                x: feature.rect.x - LIDAR_INTERACTIVE_EXCLUSION_MARGIN_PX,
                y: feature.rect.y - LIDAR_INTERACTIVE_EXCLUSION_MARGIN_PX,
                width: feature.rect.width + LIDAR_INTERACTIVE_EXCLUSION_MARGIN_PX * 2,
                height: feature.rect.height + LIDAR_INTERACTIVE_EXCLUSION_MARGIN_PX * 2,
              }
              : feature.rect,
          ), 0);
        const hardExclusionCollision = relevantFeatures.some((feature) => (
          feature.hardExclusion && intersects(rect, {
            x: feature.rect.x - LIDAR_INTERACTIVE_EXCLUSION_MARGIN_PX,
            y: feature.rect.y - LIDAR_INTERACTIVE_EXCLUSION_MARGIN_PX,
            width: feature.rect.width + LIDAR_INTERACTIVE_EXCLUSION_MARGIN_PX * 2,
            height: feature.rect.height + LIDAR_INTERACTIVE_EXCLUSION_MARGIN_PX * 2,
          }) > 0
        ));
        const recentDistance = ambientPoseHistoryRef.current.length
          ? Math.min(...ambientPoseHistoryRef.current.map((pose) => Math.hypot(candidate.x - pose.x, candidate.y - pose.y)))
          : minimumTravel;
        if (actualTravel < minimumTravel * 0.72 || actualTravel > maximumTravel || recentDistance < Math.max(72, size * 0.46) || hardExclusionCollision) continue;
        const normalized = { x: candidateCenter.x / window.innerWidth, y: candidateCenter.y / window.innerHeight };
        const preferenceScore = preference
          ? Math.max(0, 150 - Math.hypot(normalized.x - preference.x, normalized.y - preference.y) * 360) * preference.confidence
          : 0;
        const edgeVantage = Math.min(candidateCenter.x, window.innerWidth - candidateCenter.x, candidateCenter.y, window.innerHeight - candidateCenter.y);
        candidates.push({
          point: candidate,
          collisions,
          textCollisions,
          interactiveCollisions,
          // Text and controls are exclusion zones. The small edge preference
          // deliberately gives Weaver a readable margin when several clear
          // places are available.
          score: preferenceScore + recentDistance * .35 - textCollisions * 90 - interactiveCollisions * 65 - collisions * 12 - actualTravel * .04 - edgeVantage * .10,
        });
      }
    }

    // Prefer the readable edge of the paragraph Weaver is hosting around.
    // These are evidence-derived stances, not screen-edge docks: the live
    // footprint and hard interactive exclusions still decide legality.
    relevantFeatures
      .filter((feature) => feature.kind === "text_block")
      .slice(0, 10)
      .forEach((feature) => {
        const gap = 24;
        const paragraphEdgeCandidates = [
          { x: feature.rect.x - size - gap, y: feature.rect.y + feature.rect.height / 2 - size / 2 },
          { x: feature.rect.x + feature.rect.width + gap, y: feature.rect.y + feature.rect.height / 2 - size / 2 },
          { x: feature.rect.x + feature.rect.width / 2 - size / 2, y: feature.rect.y - size - gap },
          { x: feature.rect.x + feature.rect.width / 2 - size / 2, y: feature.rect.y + feature.rect.height + gap },
        ].map((candidate) => clampPosition(candidate.x, candidate.y));
        paragraphEdgeCandidates.forEach((candidate) => {
          const actualTravel = Math.hypot(candidate.x - current.x, candidate.y - current.y);
          const rect = renderedFootprint(candidate);
          const collisions = relevantFeatures.reduce((total, item) => total + intersects(rect, item.rect), 0);
          const textCollisions = relevantFeatures
            .filter((item) => item.kind === "text_block")
            .reduce((total, item) => total + intersects(rect, item.rect), 0);
          const interactiveCollisions = relevantFeatures
            .filter((item) => item.hardExclusion || item.kind === "interactive")
            .reduce((total, item) => total + intersects(rect, item.rect), 0);
          const hardExclusionCollision = relevantFeatures.some((item) => item.hardExclusion && intersects(rect, {
            x: item.rect.x - LIDAR_INTERACTIVE_EXCLUSION_MARGIN_PX,
            y: item.rect.y - LIDAR_INTERACTIVE_EXCLUSION_MARGIN_PX,
            width: item.rect.width + LIDAR_INTERACTIVE_EXCLUSION_MARGIN_PX * 2,
            height: item.rect.height + LIDAR_INTERACTIVE_EXCLUSION_MARGIN_PX * 2,
          }) > 0);
          const recentDistance = ambientPoseHistoryRef.current.length
            ? Math.min(...ambientPoseHistoryRef.current.map((pose) => Math.hypot(candidate.x - pose.x, candidate.y - pose.y)))
            : minimumTravel;
          if (actualTravel < minimumTravel * 0.72 || recentDistance < Math.max(72, size * 0.46) || hardExclusionCollision) return;
          candidates.push({
            point: candidate,
            collisions,
            textCollisions,
            interactiveCollisions,
            score: 320 + recentDistance * .35 - textCollisions * 90 - interactiveCollisions * 65 - collisions * 12 - actualTravel * .04,
          });
        });
      });

    // Never trade readable copy for an old ambient preference. If a truly
    // clear pose exists, only clear poses may be chosen; otherwise select the
    // least-overlapping pose and keep moving rather than parking on a word.
    const lowestTextCollision = candidates.length
      ? Math.min(...candidates.map((candidate) => candidate.textCollisions))
      : 0;
    const viableCandidates = candidates.filter((candidate) => (
      candidate.textCollisions <= lowestTextCollision + 0.5
    ));
    const best = viableCandidates.reduce<typeof candidates[number] | null>(
      (selected, candidate) => !selected || candidate.score > selected.score ? candidate : selected,
      null,
    );

    if (best) {
      lastAutonomousDestinationRef.current = best.point;
      ambientPoseHistoryRef.current = [...ambientPoseHistoryRef.current, best.point].slice(-4);
      const nextPreference: AmbientVantagePreference = {
        route: lidarMap.route,
        x: (best.point.x + size / 2) / window.innerWidth,
        y: (best.point.y + size / 2) / window.innerHeight,
        confidence: Math.min(0.85, (preference?.confidence || 0.25) + 0.12),
      };
      ambientVantageRef.current = nextPreference;
      window.sessionStorage.setItem(AMBIENT_VANTAGE_STORAGE_KEY, JSON.stringify(nextPreference));
      emitOrbRuntimeEvent("lidar_ambient_pose_selected", {
        route: lidarMap.route,
        featureCount: lidarMap.features.length,
        dynamicObstacleCount: lidarMap.dynamicObstacleCount,
        collisions: Math.round(best.collisions),
        textCollisions: Math.round(best.textCollisions),
        interactiveCollisions: Math.round(best.interactiveCollisions),
        captionFootprint: captionOffset ? {
          width: captionOffset.width,
          height: captionOffset.height,
          offsetX: captionOffset.x,
          offsetY: captionOffset.y,
        } : null,
        ambientVelocity: AMBIENT_TRAVEL_PX_PER_SECOND,
        destination: best.point,
      });
      return best.point;
    }

    emitOrbRuntimeEvent("lidar_ambient_pose_blocked", {
      route: lidarMap.route,
      featureCount: lidarMap.features.length,
      reason: "no_clear_novel_pose",
    });
    // A blocked LiDAR pass must not silently dock the Website ORB at an edge
    // or corner. Hold the last witnessed pose and report the condition so a
    // later live geometry pass can recover deliberately.
    return current;
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
    // Conversation and guidance resolve into a visible, attentive dwell before
    // Weaver resumes ambient motion. This is never guidance travel.
    await wait(AMBIENT_POST_INTERACTION_DWELL_MS);
    if (speechPlaybackRef.current || guidanceActiveRef.current || controlMotionActiveRef.current || manualHoldRef.current || restModeRef.current) {
      autonomousResumeActiveRef.current = false;
      return;
    }
    const sequence = motionInterruptionSequenceRef.current + 1;
    motionInterruptionSequenceRef.current = sequence;
    const destination = nextDestination();
    const relocationDistance = Math.hypot(destination.x - positionRef.current.x, destination.y - positionRef.current.y);
    if (relocationDistance < 1) {
      autonomousResumeActiveRef.current = false;
      emitOrbRuntimeEvent("autonomous_resume_blocked", { reason: "no_legal_fresh_pose" });
      return;
    }
    const authorization = authorizeMotion(destination, "Ambient");
    if (!authorization) {
      autonomousResumeActiveRef.current = false;
      return;
    }
    emitOrbRuntimeEvent("autonomous_resume_started", { destination });
    try {
      assertMovementAuthorization(authorization);
      await travelOrbAlongCurve(destination, "glide");
      if (sequence === motionInterruptionSequenceRef.current) positionRef.current = destination;
    } finally {
      if (sequence === motionInterruptionSequenceRef.current) {
        autonomousResumeActiveRef.current = false;
        emitOrbRuntimeEvent("autonomous_resume_complete", { destination });
      }
    }
  }, [authorizeMotion, nextDestination, travelOrbAlongCurve]);
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
    const authorization = authorizeMotion(destination, command);
    if (!authorization) {
      controlMotionActiveRef.current = false;
      return false;
    }
    emitOrbRuntimeEvent("control_motion_started", { command, current, destination, distance: distanceToMove });
    try {
      assertMovementAuthorization(authorization);
      await travelOrbAlongCurve(destination, distanceToMove > 520 ? "swirl" : "glide");
      positionRef.current = destination;
      invalidateAmbientPose("control_action_complete");
      emitOrbRuntimeEvent("control_motion_complete", { command, moved: distanceToMove > 1, destination });
    } finally {
      controlMotionActiveRef.current = false;
    }
    window.setTimeout(() => void resumeAutonomousPresence(), 180);
    return true;
  }, [authorizeMotion, clampPosition, invalidateAmbientPose, localMoveOutDestination, markVisitorActivity, move, resumeAutonomousPresence, size, travelOrbAlongCurve]);

  const findPointerRecordForIntent = useCallback((intentText: string) => {
    const query = normalizeIntentText(intentText);
    const queryTokens = new Set(query.split(" ").filter((token) => token.length > 2));
    if (!queryTokens.size) return null;
    const currentRoute = routeForUrl(window.location.href);
    let best: { record: WebsiteOrbPointerRecord; score: number } | null = null;

    const routeRecords = onboardingLiveRecordRef.current
      ? [...pointerRecordsRef.current, onboardingLiveRecordRef.current]
      : pointerRecordsRef.current;
    for (const record of routeRecords) {
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
    options: { launchMorbOnly?: boolean; signal?: AbortSignal } = {},
  ) => {
    if (options.signal?.aborted) return false;
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
      if (result) {
        invalidateAmbientPose("tamp_out");
        window.setTimeout(() => void resumeAutonomousPresence(), 120);
      }
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

    const cancelGuidance = () => {
      movement.cancel("tour_interrupted");
      move.stop();
      stopMorbTravelSound();
      pointerPingAudioRef.current?.pause();
      setPointerBloom(null);
      setMorbPointer(null);
      guidanceActiveRef.current = false;
    };
    options.signal?.addEventListener('abort', cancelGuidance, { once: true });
    try {
    if (options.signal?.aborted) { cancelGuidance(); return finishGuidance(false, 'tour_interrupted'); }
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
      await awaitAbortable(wait(650), options.signal);
    if (options.signal?.aborted) return finishGuidance(false, 'tour_interrupted');
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
    const guidanceMap = buildLidarGuidanceMap({
      orbPosition: { x: positionRef.current.x + size / 2, y: positionRef.current.y + size / 2 },
    });
    const currentOrbRect = orbElementRef.current?.getBoundingClientRect();
    const captionRect = document.querySelector<HTMLElement>('[data-orb-caption-state]')?.getBoundingClientRect();
    const captionOffset = currentOrbRect && captionRect
      ? { x: captionRect.left - currentOrbRect.left, y: captionRect.top - currentOrbRect.top, width: captionRect.width, height: captionRect.height }
      : null;
    const intersects = (a: { left: number; top: number; right: number; bottom: number }, b: { x: number; y: number; width: number; height: number }) =>
      Math.max(0, Math.min(a.right, b.x + b.width) - Math.max(a.left, b.x)) *
      Math.max(0, Math.min(a.bottom, b.y + b.height) - Math.max(a.top, b.y));
    const footprintFor = (candidate: { x: number; y: number }) => {
      const body = { left: candidate.x, top: candidate.y, right: candidate.x + size, bottom: candidate.y + size };
      const footprint = captionOffset ? {
        left: Math.min(body.left, candidate.x + captionOffset.x),
        top: Math.min(body.top, candidate.y + captionOffset.y),
        right: Math.max(body.right, candidate.x + captionOffset.x + captionOffset.width),
        bottom: Math.max(body.bottom, candidate.y + captionOffset.y + captionOffset.height),
      } : body;
      return {
        left: footprint.left - LIDAR_SAFETY_PADDING_PX,
        top: footprint.top - LIDAR_SAFETY_PADDING_PX,
        right: footprint.right + LIDAR_SAFETY_PADDING_PX,
        bottom: footprint.bottom + LIDAR_SAFETY_PADDING_PX,
      };
    };
    const protectedFeatures = guidanceMap.features.filter((feature) => (
      feature.visible && feature.pointerEvents !== "none" &&
      (feature.hardExclusion || (!feature.occluded && ["interactive", "text_block", "image"].includes(feature.kind)))
    ));
    const isSafeStance = (candidate: { x: number; y: number }) => {
      const footprint = footprintFor(candidate);
      return !protectedFeatures.some((feature) => {
        const margin = feature.hardExclusion ? LIDAR_INTERACTIVE_EXCLUSION_MARGIN_PX : 0;
        return intersects(footprint, {
          x: feature.rect.x - margin,
          y: feature.rect.y - margin,
          width: feature.rect.width + margin * 2,
          height: feature.rect.height + margin * 2,
        }) > 0;
      });
    };
    // Search around the same verified target first. Expand the radius only
    // when the nearest cardinal/diagonal stance is occupied; never abandon
    // the target for a generic edge or corner fallback.
    const targetHalfWidth = activeRect.width / 2 + size / 2 + ORB_TARGET_CLEARANCE_PX;
    const targetHalfHeight = activeRect.height / 2 + size / 2 + ORB_TARGET_CLEARANCE_PX;
    const stanceCandidates = [1, 1.5, 2.2].flatMap((radius) => [
      { x: targetCenterX - targetHalfWidth * radius - size / 2, y: targetCenterY - size / 2 },
      { x: targetCenterX + targetHalfWidth * radius - size / 2, y: targetCenterY - size / 2 },
      { x: targetCenterX - size / 2, y: targetCenterY - targetHalfHeight * radius - size / 2 },
      { x: targetCenterX - size / 2, y: targetCenterY + targetHalfHeight * radius - size / 2 },
      { x: targetCenterX - targetHalfWidth * radius - size / 2, y: targetCenterY - targetHalfHeight * radius - size / 2 },
      { x: targetCenterX + targetHalfWidth * radius - size / 2, y: targetCenterY - targetHalfHeight * radius - size / 2 },
      { x: targetCenterX - targetHalfWidth * radius - size / 2, y: targetCenterY + targetHalfHeight * radius - size / 2 },
      { x: targetCenterX + targetHalfWidth * radius - size / 2, y: targetCenterY + targetHalfHeight * radius - size / 2 },
    ].map((candidate) => clampPosition(candidate.x, candidate.y)));
    const guidedDestination = stanceCandidates.find((candidate) => isSafeStance(candidate));
    if (!guidedDestination) {
      movement.cancel("no_phase_zero_adjacent_stance");
      return finishGuidance(false, "no_phase_zero_adjacent_stance");
    }
    if (!options.launchMorbOnly) {
      const rect = orbElementRef.current?.getBoundingClientRect();
      if (rect) positionRef.current = { x: rect.left, y: rect.top };
    }
    const current = positionRef.current;
    const destination = options.launchMorbOnly ? current : guidedDestination;
    const distance = Math.hypot(destination.x - current.x, destination.y - current.y);
    avoidUntilRef.current = Date.now() + 900;
    if (!options.launchMorbOnly) {
      motionInterruptionSequenceRef.current += 1;
      autonomousResumeActiveRef.current = false;
      move.stop();
      const authorization = authorizeMotion(destination, "Guide");
      if (!authorization) {
        movement.cancel("movement_policy_blocked");
        return finishGuidance(false, "movement_policy_blocked");
      }
      setPointerWaltzPhase("APPROACH");
      assertMovementAuthorization(authorization);
      const travelMode = distance > 520 ? "swirl" : "glide";
      const dx = destination.x - current.x;
      const dy = destination.y - current.y;
      const pathLength = Math.max(1, Math.hypot(dx, dy));
      const normalX = -dy / pathLength;
      const normalY = dx / pathLength;
      const bend = travelMode === "swirl" ? Math.min(180, Math.max(72, distance * 0.24)) : Math.min(112, Math.max(42, distance * 0.18));
      const corridorControls = [0.24, 0.42, 0.66, 1].flatMap((scale) => [1, -1].map((side) => clampPosition(
        (current.x + destination.x) / 2 + normalX * bend * scale * side,
        (current.y + destination.y) / 2 + normalY * bend * scale * side,
      )));
      const safeControlPoint = distance < 80
        ? null
        : corridorControls.find((candidate) => isSafeStance(candidate)) || null;
      emitOrbRuntimeEvent("lidar_transit_corridor_selected", {
        targetId: record.target_id,
        mode: travelMode,
        safeControlPoint,
        corridorCandidates: corridorControls,
      });
      await travelOrbAlongCurve(destination, travelMode, options.signal, safeControlPoint);
    }
    if (options.signal?.aborted) return finishGuidance(false, 'tour_interrupted');
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
    const eyeDirectionLength = Math.max(1, Math.hypot(finalTargetX - orbCenterX, finalTargetY - orbCenterY));
    setOrbEyeDirection({
      x: Math.max(-1, Math.min(1, (finalTargetX - orbCenterX) / eyeDirectionLength)),
      y: Math.max(-1, Math.min(1, (finalTargetY - orbCenterY) / eyeDirectionLength)),
    });

    if (morbPointerRef.current) {
      setPointerWaltzPhase("DISSOLVE");
      setMorbPointer((currentMorb) => currentMorb ? { ...currentMorb, phase: "DISSOLVE", dissolving: true } : null);
      await awaitAbortable(wait(420), options.signal);
    if (options.signal?.aborted) return finishGuidance(false, 'tour_interrupted');
      setMorbPointer(null);
    }

    setPointerWaltzPhase("LAUNCH");
    playMorbLaunchSound();
    const morbTrajectory = morbTrajectoryForGuidance(guidanceSequence);
    setMorbPointer({
      targetId: record.target_id,
      role,
      left: orbCenterX - MORB_HALF,
      top: orbCenterY - MORB_HALF,
      visible: false,
      pinging: false,
      dissolving: false,
      phase: "LAUNCH",
      trajectory: morbTrajectory,
    });
    await awaitAbortable(wait(60), options.signal);
    if (options.signal?.aborted) return finishGuidance(false, 'tour_interrupted');
    setPointerWaltzPhase("TRAVEL");
    startMorbTravelSound();
    const morbTravelDuration = Math.max(760, Math.min(1500,
      Math.round(Math.hypot(finalTargetX - orbCenterX, finalTargetY - orbCenterY) * 1.25),
    ));
    const moveMorbAlongLivePath = (x: number, y: number) => {
      setMorbPointer((currentMorb) => currentMorb ? {
        ...currentMorb,
        left: x - MORB_HALF,
        top: y - MORB_HALF,
        visible: true,
        phase: "TRAVEL",
      } : null);
    };
    const pathX = finalTargetX - orbCenterX;
    const pathY = finalTargetY - orbCenterY;
    const pathLength = Math.max(1, Math.hypot(pathX, pathY));
    const normalX = -pathY / pathLength;
    const normalY = pathX / pathLength;

    if (morbTrajectory === "swirl") {
      // A broad S-curve reads as a purposeful scouting pass before the MORB
      // settles on the target. The live target is still rechecked below.
      moveMorbAlongLivePath(
        orbCenterX + pathX * .42 + normalX * Math.min(118, pathLength * .25),
        orbCenterY + pathY * .42 + normalY * Math.min(118, pathLength * .25),
      );
      await awaitAbortable(wait(Math.round(morbTravelDuration * .34)), options.signal);
      if (options.signal?.aborted) return finishGuidance(false, 'tour_interrupted');
      moveMorbAlongLivePath(
        orbCenterX + pathX * .78 - normalX * Math.min(76, pathLength * .16),
        orbCenterY + pathY * .78 - normalY * Math.min(76, pathLength * .16),
      );
      await awaitAbortable(wait(Math.round(morbTravelDuration * .34)), options.signal);
      if (options.signal?.aborted) return finishGuidance(false, 'tour_interrupted');
      moveMorbAlongLivePath(finalTargetX, finalTargetY);
      await awaitAbortable(wait(Math.round(morbTravelDuration * .32)), options.signal);
    } else if (morbTrajectory === "dart_orbit") {
      // A fast line followed by two tight target-relative passes gives the
      // MORB a dart-and-circle arrival without ever using cached authority.
      moveMorbAlongLivePath(orbCenterX + pathX * .78, orbCenterY + pathY * .78);
      await awaitAbortable(wait(Math.round(morbTravelDuration * .42)), options.signal);
      if (options.signal?.aborted) return finishGuidance(false, 'tour_interrupted');
      moveMorbAlongLivePath(finalTargetX + normalX * 32, finalTargetY + normalY * 32);
      await awaitAbortable(wait(Math.round(morbTravelDuration * .22)), options.signal);
      if (options.signal?.aborted) return finishGuidance(false, 'tour_interrupted');
      moveMorbAlongLivePath(finalTargetX - normalX * 26, finalTargetY - normalY * 26);
      await awaitAbortable(wait(Math.round(morbTravelDuration * .18)), options.signal);
      if (options.signal?.aborted) return finishGuidance(false, 'tour_interrupted');
      moveMorbAlongLivePath(finalTargetX, finalTargetY);
      await awaitAbortable(wait(Math.round(morbTravelDuration * .18)), options.signal);
    } else {
      moveMorbAlongLivePath(finalTargetX, finalTargetY);
      await awaitAbortable(wait(morbTravelDuration), options.signal);
    }
    if (options.signal?.aborted) return finishGuidance(false, 'tour_interrupted');
    stopMorbTravelSound();
    setPointerWaltzPhase("STANCE");
    setMorbPointer((currentMorb) => currentMorb ? { ...currentMorb, phase: "STANCE" } : null);
    await awaitAbortable(wait(180), options.signal);
    if (options.signal?.aborted) return finishGuidance(false, 'tour_interrupted');

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
    emitOrbRuntimeEvent("guidance_point_ping", {
      targetId: record.target_id,
      geometrySource: "live_refresh",
    });

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
    await awaitAbortable(wait(1200), options.signal);
    if (options.signal?.aborted) return finishGuidance(false, 'tour_interrupted');
    setPointerWaltzPhase("DISSOLVE");
    setMorbPointer((currentMorb) => currentMorb ? { ...currentMorb, phase: "DISSOLVE", dissolving: true } : null);
    await awaitAbortable(wait(420), options.signal);
    if (options.signal?.aborted) return finishGuidance(false, 'tour_interrupted');
    setMorbPointer(null);
    setPointerWaltzPhase("COMPLETE");
    return finishGuidance(true);
    } finally { options.signal?.removeEventListener('abort', cancelGuidance); }
  }, [authorizeMotion, bumpWorldStateSequence, clampPosition, invalidateAmbientPose, markVisitorActivity, move, playMorbLaunchSound, playPointerPing, resumeAutonomousPresence, size, startMorbTravelSound, stopMorbTravelSound, travelOrbAlongCurve]);

  const guideToPointerTarget = useCallback(async (intentText: string) => {
    const record = findPointerRecordForIntent(intentText);
    if (!record) return false;
    return guideToPointerRecord(record, intentText);
  }, [findPointerRecordForIntent, guideToPointerRecord]);

  const findPointerRecordById = useCallback((targetId: string) => {
    const currentRoute = routeForUrl(window.location.href);
    const routeRecords = onboardingLiveRecordRef.current
      ? [...pointerRecordsRef.current, onboardingLiveRecordRef.current]
      : pointerRecordsRef.current;
    return routeRecords.find((record) => (
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

  const waitForPointerRecord = useCallback(async (targetId: string) => {
    const startedAt = Date.now();
    while (activeRef.current && Date.now() - startedAt < 8000) {
      const target = findPointerRecordById(targetId);
      if (target) return target;
      await wait(160);
    }
    return findPointerRecordById(targetId);
  }, [findPointerRecordById]);

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
    // The outer body is intentionally still; speech belongs to the center eye.
    presence.stop();
  }, [presence]);

  useEffect(() => {
    presence.stop();
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

  const executeVerifiedDirectRouteNavigation = useCallback((request: VerifiedRouteNavigation): boolean => {
    if (window.location.pathname === request.route) return false;
    // An explicit visitor imperative is the required approval for a known,
    // first-party route. Arrival still revalidates the target before pointing.
    pendingDirectRouteGuidanceRef.current = request;
    markVisitorActivity();
    setStatusTitle(`Opening ${request.label}`);
    setStatusLine(`Taking you to ${request.label}.`);
    showStatus(4200);
    emitOrbRuntimeEvent("visitor_route_navigation_authorized", {
      route: request.route,
      pointerTargetId: request.pointerTargetId,
      source: "explicit_visitor_voice_request",
    });
    navigate(request.route);
    return true;
  }, [markVisitorActivity, navigate, showStatus]);

  const stopSpeechCaptions = useCallback((completed: boolean) => {
    if (!completed) captionPlaybackCancelledRef.current = true;
    if (captionFrameRef.current) {
      window.cancelAnimationFrame(captionFrameRef.current);
      captionFrameRef.current = null;
    }
    if (captionCollapseTimerRef.current) {
      window.clearTimeout(captionCollapseTimerRef.current);
      captionCollapseTimerRef.current = null;
    }
    setSpeechCaption({ fullText: '', revealedText: '', phase: 'idle', collapsed: false, expanded: false });
    emitOrbRuntimeEvent(completed ? 'caption_completed' : 'caption_stopped');
  }, []);

  const startSpeechCaptions = useCallback((text: string, playback: () => { currentTime: number; duration: number; paused: boolean }) => {
    captionPlaybackCancelledRef.current = false;
    if (captionFrameRef.current) window.cancelAnimationFrame(captionFrameRef.current);
    if (captionCollapseTimerRef.current) window.clearTimeout(captionCollapseTimerRef.current);
    captionFrameRef.current = null;
    captionCollapseTimerRef.current = null;
    setSpeechCaption({ fullText: text, revealedText: "", phase: "speaking", collapsed: false, expanded: false });
    emitOrbRuntimeEvent("caption_started", { fullCharacters: text.length });

    let lastRevealed = "";
    const advance = () => {
      const progress = playback();
      if (!canAdvanceCaptionProgression({ paused: progress.paused, cancelled: captionPlaybackCancelledRef.current })) return;
      const next = currentSpeechCaption(text, progress.currentTime, progress.duration);
      if (next !== lastRevealed) {
        lastRevealed = next;
        setSpeechCaption((current) => current.phase === "speaking" ? { ...current, revealedText: next } : current);
        emitOrbRuntimeEvent("caption_progressed", {
          revealedCharacters: next.length,
          audioCurrentTime: progress.currentTime,
          audioDuration: progress.duration,
        });
      }
      captionFrameRef.current = window.requestAnimationFrame(advance);
    };
    captionFrameRef.current = window.requestAnimationFrame(advance);
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

  const stopSpeechVisualizer = useCallback(() => {
    if (speechVisualizerFrameRef.current !== null) {
      window.cancelAnimationFrame(speechVisualizerFrameRef.current);
      speechVisualizerFrameRef.current = null;
    }
    const wasActive = speechVisualizerActiveRef.current;
    speechVisualizerActiveRef.current = false;
    speechAnalyserRef.current = null;
    setSpeechAmplitude(0);
    if (wasActive) emitOrbRuntimeEvent("SPEECH_VISUAL_ENDED");
  }, []);

  const startSpeechVisualizer = useCallback((analyser: AnalyserNode) => {
    stopSpeechVisualizer();
    analyser.fftSize = 512;
    analyser.smoothingTimeConstant = 0.72;
    const samples = new Uint8Array(analyser.fftSize);
    speechAnalyserRef.current = analyser;
    speechVisualizerActiveRef.current = true;
    emitOrbRuntimeEvent("SPEECH_VISUAL_ACTIVE");

    const update = () => {
      if (speechAnalyserRef.current !== analyser) return;
      analyser.getByteTimeDomainData(samples);
      let sum = 0;
      for (const sample of samples) {
        const centered = (sample - 128) / 128;
        sum += centered * centered;
      }
      const rms = Math.sqrt(sum / samples.length);
      // Normal conversational TTS sits close to the noise floor of an
      // analyser. Lift it into a visible, but bounded, center-eye response.
      const amplitude = Math.min(1, Math.max(0, (rms - 0.004) * 30));
      setSpeechAmplitude((current) => Math.abs(current - amplitude) > 0.006 ? amplitude : current);
      speechVisualizerFrameRef.current = window.requestAnimationFrame(update);
    };

    update();
  }, [stopSpeechVisualizer]);

  const startFallbackSpeechVisualizer = useCallback(() => {
    stopSpeechVisualizer();
    speechVisualizerActiveRef.current = true;
    emitOrbRuntimeEvent("SPEECH_VISUAL_ACTIVE", { source: "speech-cadence-fallback" });
    const startedAt = performance.now();
    const update = () => {
      if (!speechVisualizerActiveRef.current) return;
      // Some Chromium builds do not expose a capturable track for a directly
      // played media element. Keep the eye responsive to active speech in that
      // case, without animating the shell or rings.
      const elapsed = (performance.now() - startedAt) / 1000;
      const cadence = 0.18 + Math.max(0, Math.sin(elapsed * 8.6)) * 0.38 + Math.max(0, Math.sin(elapsed * 3.1 + 0.8)) * 0.16;
      setSpeechAmplitude(cadence);
      speechVisualizerFrameRef.current = window.requestAnimationFrame(update);
    };
    update();
  }, [stopSpeechVisualizer]);

  const connectSpeechMediaVisualizer = useCallback(async (audio: HTMLAudioElement): Promise<AnalyserNode | null> => {
    const AudioContextCtor = (window as any).AudioContext || (window as any).webkitAudioContext;
    if (!AudioContextCtor) return null;
    const context: AudioContext = audioContextRef.current || new AudioContextCtor();
    audioContextRef.current = context;
    await context.resume?.();
    if (context.state !== "running") return null;

    // Observe a captured copy. createMediaElementSource() takes over the
    // element's audible output and can make real speech silent when the Web
    // Audio graph is suspended even though HTMLMediaElement.play() succeeds.
    const captureStream = (audio as HTMLAudioElement & {
      captureStream?: () => MediaStream;
      mozCaptureStream?: () => MediaStream;
    }).captureStream || (audio as HTMLAudioElement & { mozCaptureStream?: () => MediaStream }).mozCaptureStream;
    if (!captureStream) return null;
    const stream = captureStream.call(audio);
    if (!stream.getAudioTracks().some(track => track.readyState === "live")) return null;

    const source = mediaSpeechElementRef.current === audio && mediaSpeechSourceRef.current
      ? mediaSpeechSourceRef.current
      : context.createMediaStreamSource(stream);
    mediaSpeechElementRef.current = audio;
    mediaSpeechSourceRef.current = source;

    const analyser = context.createAnalyser();
    source.disconnect();
    source.connect(analyser);
    const silentSink = context.createGain();
    silentSink.gain.value = 0;
    analyser.connect(silentSink);
    silentSink.connect(context.destination);
    return analyser;
  }, []);

  const playDecodedSpeech = useCallback(async (audioUrl: string, captionText?: string, onPlaybackStarted?: () => void, playbackRate = ORB_SPEECH_PLAYBACK_RATE) => {
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

    const audio = new Audio(api.orbMediaUrl(audioUrl));
    audio.crossOrigin = 'anonymous';
    audio.playbackRate = playbackRate;
    audio.defaultPlaybackRate = playbackRate;
    audio.preservesPitch = true;
    speechAudioRef.current = audio;
    const source = context.createMediaElementSource(audio);
    const gain = context.createGain();
    gain.gain.value = speakerBoostRef.current ? 1.85 : 1;
    const analyser = context.createAnalyser();
    source.connect(gain);
    gain.connect(analyser);
    analyser.connect(context.destination);

    const settlement = createPlaybackSettlement();
    speechPlaybackSettlementRef.current = settlement;
    audio.onended = () => {
      if (speechAudioRef.current === audio) speechAudioRef.current = null;
      stopSpeechVisualizer();
      stopSpeechCaptions(!captionPlaybackCancelledRef.current);
      invalidateAmbientPose("response_complete");
      settlement.resolve();
    };
    try {
      audio.onerror = () => settlement.reject(new Error('Speech audio unavailable'));
      await audio.play();
      onPlaybackStarted?.();
      if (captionText) {
        startSpeechCaptions(captionText, () => ({
          currentTime: audio.currentTime,
          duration: audio.duration,
          paused: audio.paused,
        }));
      }
      startSpeechVisualizer(analyser);
    } catch (error) {
      settlement.reject(error as Error);
    }
    try {
      await settlement.promise;
    } finally {
      if (speechPlaybackSettlementRef.current === settlement) speechPlaybackSettlementRef.current = null;
    }
  }, [invalidateAmbientPose, startSpeechCaptions, startSpeechVisualizer, stopSpeechCaptions, stopSpeechVisualizer]);

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
    // A conversation is attentive, not another ambient travel state. Hold
    // position while listening, thinking, or speaking; inner animation keeps
    // Weaver visibly alive without positional restlessness.
    const rect = orbElementRef.current?.getBoundingClientRect();
    if (rect) positionRef.current = { x: rect.left, y: rect.top };
    motionInterruptionSequenceRef.current += 1;
    autonomousResumeActiveRef.current = false;
    move.stop();
  }, [move]);

  const speak = useCallback(async (
    text: string,
    audioUrl?: string | null,
    provider?: string | null,
    options: { showTranscript?: boolean; onPlaybackStarted?: () => void; playbackRate?: number } = {},
  ): Promise<boolean> => {
    // Narration is active hosting, never visitor inactivity.
    markVisitorActivity();
    const showTranscript = options.showTranscript !== false;
    if (showTranscript) {
      showStatus();
    } else {
      stopSpeechCaptions(false);
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
        stopSpeechCaptions(false);
        setVoiceState("idle");
        setStatusTitle("Voice unavailable");
        setStatusLine(VOICE_UNAVAILABLE_MESSAGE);
        showStatus(3600);
        return false;
      }
      if (speakerBoostRef.current) {
        await playDecodedSpeech(audioUrl, showTranscript ? text : undefined, options.onPlaybackStarted, options.playbackRate);
        speechPlaybackRef.current = false;
        setVoiceState("idle");
        showStatus(1400);
        return true;
      }
      // Always use a fresh media element. A previous element may have been
      // routed through an older Web Audio graph before hot reload or browser
      // suspension; reusing it can resolve play() while producing no sound.
      speechAudioRef.current?.pause();
      const audio = new Audio();
      audio.muted = false;
      audio.volume = speakerBoostRef.current ? 1 : 0.86;
      audio.playbackRate = options.playbackRate || ORB_SPEECH_PLAYBACK_RATE;
      audio.defaultPlaybackRate = options.playbackRate || ORB_SPEECH_PLAYBACK_RATE;
      audio.preservesPitch = true;
      audio.src = api.orbMediaUrl(audioUrl);
      speechAudioRef.current = audio;
      const settlement = createPlaybackSettlement();
      speechPlaybackSettlementRef.current = settlement;
      audio.onended = () => {
        stopSpeechCaptions(!captionPlaybackCancelledRef.current);
        if (speechAudioRef.current === audio) speechAudioRef.current = null;
        speechPlaybackRef.current = false;
        stopSpeechVisualizer();
        setVoiceState("idle");
        showStatus(1400);
        invalidateAmbientPose("response_complete");
        emitOrbRuntimeEvent("playback_ended", { provider: provider || null });
        settlement.resolve();
      };
      audio.onpause = () => {
        if (speechAudioRef.current === audio && !audio.ended) stopSpeechCaptions(false);
      };
      audio.onerror = () => {
        stopSpeechCaptions(false);
        if (speechAudioRef.current === audio) speechAudioRef.current = null;
        settlement.reject(new Error("Audio playback failed"));
      };
      try {
        try {
          await audio.play();
          options.onPlaybackStarted?.();
          if (showTranscript) {
            startSpeechCaptions(text, () => ({
              currentTime: audio.currentTime,
              duration: audio.duration,
              paused: audio.paused,
            }));
          }
          // Connect only after direct media playback begins. The captured copy
          // drives visuals without owning or muting the audible output.
          let speechAnalyser: AnalyserNode | null = null;
          try {
            speechAnalyser = await connectSpeechMediaVisualizer(audio);
          } catch {
            speechAnalyser = null;
          }
          if (speechAnalyser) startSpeechVisualizer(speechAnalyser);
          else startFallbackSpeechVisualizer();
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
      stopSpeechVisualizer();
      stopSpeechCaptions(false);
      emitOrbRuntimeEvent("playback_failed", {
        provider: provider || null,
        error: error instanceof Error ? error.message : "unknown_playback_error",
        audioContextState: audioContextRef.current?.state || null,
      });
      if ((error as Error)?.name === "AbortError") throw error;
      setStatusTitle("Voice unavailable");
      setStatusLine(VOICE_UNAVAILABLE_MESSAGE);
      setVoiceState("idle");
      showStatus(3600);
      return false;
    }
  }, [connectSpeechMediaVisualizer, freezeOrbInPlace, invalidateAmbientPose, markVisitorActivity, playDecodedSpeech, showStatus, startFallbackSpeechVisualizer, startSpeechCaptions, startSpeechVisualizer, stopSpeechCaptions, stopSpeechVisualizer]);

  const speakWithGeneratedAudio = useCallback(async (
    text: string,
    audioUrl?: string | null,
    provider?: string | null,
    options: { onPlaybackStarted?: () => void; playbackRate?: number } = {},
  ) => {
    const normalizedText = normalizeOrbDialogue(text);
    setStatusTitle("Preparing voice");
    setStatusLine(normalizedText);
    setVoiceState("thinking");
    showStatus();
    freezeOrbInPlace(4200);

    return speak(normalizedText, audioUrl, provider, options);
  }, [freezeOrbInPlace, showStatus, speak]);

  const runMorbWorkSimulation = useCallback(async (
    work: "product_price_research" | "desktop_diagnostics",
    auditTaskCount: 3 | 5 | 7 | 11 = 3,
  ): Promise<void> => {
    // This is intentionally separate from pointer guidance: a MORB scouts a
    // bounded task area, does not acquire a clickable DOM target, and cannot
    // navigate, purchase, or change external state.
    const rect = orbElementRef.current?.getBoundingClientRect();
    const originX = rect ? rect.left + rect.width / 2 : window.innerWidth / 2;
    const originY = rect ? rect.top + rect.height / 2 : window.innerHeight / 2;
    const destinationX = Math.min(window.innerWidth - MORB_HALF - 24, Math.max(MORB_HALF + 24, window.innerWidth * .69));
    const destinationY = Math.min(window.innerHeight - MORB_HALF - 24, Math.max(MORB_HALF + 24, window.innerHeight * .56));
    const role: MorbWorkRole = work === "product_price_research" ? "comparison" : "sequence";
    const targetId = `morb-${work}-audit-${auditTaskCount}`;

    emitOrbRuntimeEvent("morb_single_function_deployment_started", {
      work,
      audit_task_count: auditTaskCount,
      audit_task_count_is_prime: true,
      pointer_guidance: false,
      external_navigation: false,
      purchase_authority: false,
      mutation_authority: false,
    });
    playMorbLaunchSound();
    setMorbPointer({
      targetId,
      role,
      left: originX - MORB_HALF,
      top: originY - MORB_HALF,
      visible: true,
      pinging: false,
      dissolving: false,
      phase: "LAUNCH",
      trajectory: "swirl",
    });
    await wait(160);
    startMorbTravelSound();
    setMorbPointer((current) => current ? {
      ...current,
      left: destinationX - MORB_HALF,
      top: destinationY - MORB_HALF,
      phase: "TRAVEL",
    } : null);
    await wait(900);
    stopMorbTravelSound();
    setMorbPointer((current) => current ? { ...current, phase: "COMPLETE" } : null);
    emitOrbRuntimeEvent("morb_single_function_deployment_completed", {
      work,
      audit_task_count: auditTaskCount,
      audit_task_count_is_prime: true,
      result: "mock_complete",
    });
    await wait(480);
    setMorbPointer((current) => current ? { ...current, phase: "DISSOLVE", dissolving: true } : null);
    await wait(320);
    setMorbPointer(null);
  }, [playMorbLaunchSound, startMorbTravelSound, stopMorbTravelSound]);

  const runScriptedOrientation = useCallback(async (
    orientationId: string,
    steps: readonly ScriptedOrientationStep[],
  ): Promise<boolean> => {
    if (scriptedOrientationRunningRef.current) return false;
    if (window.sessionStorage.getItem(SCRIPTED_ORIENTATION_SESSION_KEY) === orientationId) return true;
    scriptedOrientationRunningRef.current = true;
    scriptedOrientationInterruptedRef.current = false;
    handsFreeEnabledRef.current = false;
    const llmScriptedTourEvaluation = developmentLlmScriptedTourOverride();
    emitOrbRuntimeEvent("scripted_orientation_started", { orientationId, stepCount: steps.length });
    try {
      for (const [index, step] of steps.entries()) {
        const stepStartedAt = Date.now();
        if (scriptedOrientationInterruptedRef.current) {
          emitOrbRuntimeEvent("scripted_orientation_interrupted_by_visitor", { orientationId, index });
          setStatusTitle("Tour paused for your question");
          setStatusLine("Weaver is listening. Ask a question, join the Founding Beta, or start an investor conversation.");
          showStatus(6200);
          return false;
        }
        if (step.route && window.location.pathname !== step.route) {
          emitOrbRuntimeEvent("scripted_tour_navigation_started", { orientationId, index, route: step.route });
          navigate(step.route);
          // RouteScrollReset and the destination page need one render before
          // the host narrates its page-level orientation.
          await wait(1400);
          emitOrbRuntimeEvent("scripted_tour_navigation_completed", { orientationId, index, route: step.route });
        }
        const section = step.selector ? document.querySelector<HTMLElement>(step.selector) : null;
        if (section) {
          section.scrollIntoView({ behavior: "smooth", block: "center" });
          await wait(700);
        }
        if (step.handoffToLiveConversation) {
          const ready = liveTourReadyRef.current;
          const preflightReady = Boolean(preflightNarratedReportRef.current);
          setStatusTitle(ready ? "Weaver is ready" : "Weaver is preparing");
          setStatusLine(ready
            ? (preflightReady
              ? "Create your account, then we can optionally review your ready Preflight before a full-site scan."
              : "The guided tour ends here. Tap Weaver to create your account or ask a question.")
            : "The guided tour ends here. Account creation is ready while Weaver completes question readiness.");
          showStatus(6200);
          emitOrbRuntimeEvent("scripted_orientation_account_handoff", {
            orientationId,
            index,
            route: step.route || window.location.pathname,
            readiness: ready ? "ready" : "warming",
            preflight_ready_for_optional_post_account_review: preflightReady,
          });
          continue;
        }
        if (!step.text) {
          emitOrbRuntimeEvent("scripted_orientation_paused", { orientationId, index, reason: "missing_script_text" });
          return false;
        }
        // Every authored stop demonstrates the verified target before its
        // explanation. The movement controller performs a live DOM refresh,
        // launches the pointer, and pings without ever clicking the target.
        for (const targetId of step.pointerTargetIds || []) {
          if (scriptedOrientationInterruptedRef.current) break;
          const target = await waitForPointerRecord(targetId);
          if (!target) {
            emitOrbRuntimeEvent("scripted_tour_pointer_unavailable", { orientationId, index, targetId });
            const message = `Weaver is holding this page until its live target can be verified: ${targetId}.`;
            if (process.env.NODE_ENV !== "production") console.error(`[ORB scripted tour] ${message}`);
            setTourNotice(message);
            setStatusTitle("Tour paused safely");
            setStatusLine(message);
            showStatus(6200);
            emitOrbRuntimeEvent("scripted_orientation_paused", { orientationId, index, targetId, reason: "target_not_live_on_route" });
            return false;
          }
          const guided = await guideToPointerRecord(
            target,
            "Demonstrate verified visual navigation without activating the target",
          );
          emitOrbRuntimeEvent(guided ? "scripted_tour_pointer_demonstrated" : "scripted_tour_pointer_unavailable", {
            orientationId,
            index,
            targetId,
          });
          if (!guided) {
            const message = `Weaver is holding until a safe stance is available for ${targetId}.`;
            if (process.env.NODE_ENV !== "production") console.error(`[ORB scripted tour] ${message}`);
            setTourNotice(message);
            setStatusTitle("Tour target waiting");
            setStatusLine(message);
            showStatus(4200);
            return false;
          }
        }
        if (scriptedOrientationInterruptedRef.current) continue;
        let spokenText = step.text;
        let suppliedAudioUrl: string | null | undefined;
        let suppliedAudioProvider: string | null | undefined;
        if (llmScriptedTourEvaluation) {
          const nearbyScript = steps
            .slice(Math.max(0, index - 1), Math.min(steps.length, index + 2))
            .map((candidate, candidateIndex) => {
              const absoluteIndex = Math.max(0, index - 1) + candidateIndex + 1;
              return `Stop ${absoluteIndex}${candidate.route ? ` (${candidate.route})` : ""}: ${candidate.text || "[silent handoff]"}`;
            })
            .join("\n\n");
          try {
            const generated = await api.websiteOrbText(
              "Deliver only the current authored tour stop in first person, using the supplied tour context. Preserve its meaning; do not ask a question or initiate actions.",
              true,
              undefined,
              {
                target_url: contextTargetUrl(),
                experience: {
                  phase: "understanding",
                  objective: "Faithfully articulate one authored tour stop using only the supplied scripted context.",
                  verification_state: "verified",
                  tour: {
                    chapter_id: "scripted-tour-llm-evaluation",
                    stop_id: `${orientationId}-${index + 1}`,
                    purpose: "Evaluate whether the local model can faithfully deliver the authored tour stop.",
                    required_concepts: [{ id: "authored-script", description: step.text.slice(0, 1000) }],
                    avoid: ["Do not invent facts or capabilities.", "Do not take or promise actions.", "Do not ask the visitor a question."],
                    presentation_guidance: ["Speak only the current authored stop in first person."],
                    visible_section_text: `Current authored stop: ${step.text}\n\nNearby context:\n${nearbyScript}`.slice(0, 8000),
                    evidence_attempt: 1,
                  },
                },
              },
            );
            const candidate = generated.spoken_output?.replace(/\s+/g, " ").trim();
            // A missing evaluation or implausibly short response is not a
            // successful test. Keep the visitor on the exact authored copy.
            if (generated.chapter_evaluation && candidate && candidate.length >= 48) {
              spokenText = candidate;
              suppliedAudioUrl = generated.tts_audio_url;
              suppliedAudioProvider = generated.tts_provider;
              emitOrbRuntimeEvent("scripted_orientation_llm_context_accepted", {
                orientationId,
                index,
                llmSource: generated.llm_source,
                authoredLength: step.text.length,
                generatedLength: candidate.length,
              });
            } else {
              emitOrbRuntimeEvent("scripted_orientation_llm_context_rejected", { orientationId, index, reason: "incomplete_or_empty_evaluation" });
            }
          } catch (error) {
            emitOrbRuntimeEvent("scripted_orientation_llm_context_fallback", {
              orientationId,
              index,
              error: error instanceof Error ? error.message : "unknown_llm_error",
            });
          }
        }
        let played = false;
        for (let attempt = 1; attempt <= 2 && !played; attempt += 1) {
          if (scriptedOrientationInterruptedRef.current) break;
          try {
            const tts = suppliedAudioUrl
              ? { tts_audio_url: suppliedAudioUrl, tts_provider: suppliedAudioProvider }
              : await api.websiteOrbTts(spokenText);
            played = await speakWithGeneratedAudio(spokenText, tts.tts_audio_url, tts.tts_provider, {
              playbackRate: TOUR_SPEECH_PLAYBACK_RATE,
              onPlaybackStarted: () => {
                emitOrbRuntimeEvent("scripted_orientation_step_started", { orientationId, index, attempt });
                if (!step.scrollToEndDuringSpeech) return;
                window.requestAnimationFrame(() => {
                  window.scrollTo({ top: document.documentElement.scrollHeight, behavior: "smooth" });
                  emitOrbRuntimeEvent("scripted_orientation_scroll_to_end_started", { orientationId, index });
                });
              },
            });
          } catch (error) {
            if (scriptedOrientationInterruptedRef.current) break;
            emitOrbRuntimeEvent("scripted_orientation_tts_attempt_failed", {
              orientationId,
              index,
              attempt,
              error: error instanceof Error ? error.message : "unknown",
            });
          }
        }
        if (scriptedOrientationInterruptedRef.current) continue;
        if (!played) {
          // A spoken step can be retried, but it must never strand the visitor
          // on the current page. Record a visible controlled skip and advance.
          emitOrbRuntimeEvent("scripted_orientation_step_skipped", { orientationId, index, reason: "tts_or_playback_unavailable" });
          setTourNotice(`Tour voice was unavailable for this stop; continuing to the next verified page.`);
          setStatusTitle("Continuing guided tour");
          setStatusLine("Voice is reconnecting. Weaver is continuing to the next tour stop.");
          showStatus(4200);
          await wait(Math.max(0, SCRIPTED_STEP_MIN_DWELL_MS - (Date.now() - stepStartedAt)));
          continue;
        }
        if (scriptedOrientationInterruptedRef.current) continue;
        if (step.simulation) {
          const auditTaskCount = step.auditTaskCount || (step.simulation === "product_price_research" ? 3 : 5);
          await runMorbWorkSimulation(step.simulation, auditTaskCount);
          emitOrbRuntimeEvent(`scripted_morb_${step.simulation}_simulation`, {
            orientationId,
            index,
            mode: "mock",
            audit_task_count: auditTaskCount,
            audit_task_count_is_prime: true,
            external_navigation: false,
            purchase_authority: false,
          });
        }
        // A completed authored stop is the same TAMP handoff as any other
        // completed response: acquire a new Phase Zero-approved ambient pose
        // before the next stop can begin.
        invalidateAmbientPose("tour_step_complete");
        await resumeAutonomousPresence();
        const remainingDwellMs = Math.max(0, SCRIPTED_STEP_MIN_DWELL_MS - (Date.now() - stepStartedAt));
        if (remainingDwellMs > 0) {
          emitOrbRuntimeEvent("scripted_orientation_step_settle_started", {
            orientationId,
            index,
            remainingDwellMs,
          });
          await wait(remainingDwellMs);
          emitOrbRuntimeEvent("scripted_orientation_step_settle_completed", { orientationId, index });
        }
      }
      window.sessionStorage.setItem(SCRIPTED_ORIENTATION_SESSION_KEY, orientationId);
      emitOrbRuntimeEvent("scripted_orientation_completed", { orientationId });
      return true;
    } finally {
      scriptedOrientationRunningRef.current = false;
    }
  }, [findPointerRecordById, guideToPointerRecord, invalidateAmbientPose, navigate, resumeAutonomousPresence, runMorbWorkSimulation, showStatus, speakWithGeneratedAudio, waitForPointerRecord, waitForPointerRecords]);

  const diagnosticNarrationText = useCallback(() => {
    return [
      "Startup diagnostics.",
      `Splash is ${startupDiagnostics.splash_state}.`,
      `Permission is ${startupDiagnostics.permission_state}.`,
      `Greeting is ${startupDiagnostics.greeting_state}.`,
      `Audio is ${startupDiagnostics.audio_tts_state}.`,
      `The selected Kokoro voice is ${startupDiagnostics.tts_voice}.`,
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
    setVoiceState("thinking");
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

  const scrollToLandingTourSection = useCallback(async (sectionId: string, signal?: AbortSignal) => {
    const section = document.getElementById(sectionId);
    if (!section) {
      emitOrbRuntimeEvent("LANDING_TOUR_BLOCKED", { reason: "section_missing", sectionId });
      return false;
    }
    section.scrollIntoView({ behavior: "smooth", block: "center" });
    await awaitAbortable(wait(720), signal);
    const rect = section.getBoundingClientRect();
    const visible = rect.bottom > HEADER_SAFE && rect.top < window.innerHeight - 24;
    if (!visible) {
      // `behavior: auto` inherits the page's smooth-scroll CSS. On distant
      // sections that leaves the target thousands of pixels away when the
      // verifier runs. Temporarily disable it and land on measured geometry.
      const root = document.documentElement;
      const previousScrollBehavior = root.style.scrollBehavior;
      root.style.scrollBehavior = "auto";
      const currentRect = section.getBoundingClientRect();
      window.scrollTo(0, Math.max(0, window.scrollY + currentRect.top - HEADER_SAFE - 24));
      root.style.scrollBehavior = previousScrollBehavior;
      await awaitAbortable(wait(90), signal);
    }
    const verifiedRect = section.getBoundingClientRect();
    const verified = verifiedRect.bottom > HEADER_SAFE && verifiedRect.top < window.innerHeight - 24;
    emitOrbRuntimeEvent(verified ? "landing_tour_section_verified" : "LANDING_TOUR_BLOCKED", {
      sectionId,
      reason: verified ? undefined : "section_not_visible_after_scroll",
    });
    if (verified) bumpWorldStateSequence();
    return verified;
  }, [bumpWorldStateSequence]);

  const getAgencyRuntime = useCallback(() => {
    if (!agencyRuntimeRef.current) agencyRuntimeRef.current = createTourAgencyRuntime({
      read: () => websiteJourneyRef.current,
      save: saveWebsiteJourney,
      pointers: () => pointerRecordsRef.current,
      capsule: () => pageCapsuleRef.current as WebsiteOrbPageCapsule | null,
      targetUrl: contextTargetUrl,
      worldRevision: () => worldStateSequenceRef.current,
      speak: (text, audio, provider) => speakWithGeneratedAudio(text, audio, provider),
      guide: (record, signal) => guideToPointerRecord(record, 'Demonstrate the authorized semantic target without activating it', { signal }),
      navigate,
      telemetry: emitOrbRuntimeEvent,
    });
    return agencyRuntimeRef.current;
  }, [contextTargetUrl, guideToPointerRecord, navigate, saveWebsiteJourney, speakWithGeneratedAudio]);

  useEffect(() => {
    const observer = new MutationObserver(records => {
      // Ignore Weaver's own animation/caption tree. Page content and controls
      // invalidate agency on mutation; no millisecond polling is introduced.
      if (records.some(record => {
        const element = record.target instanceof Element ? record.target : record.target.parentElement;
        return Boolean(element?.closest('main'));
      })) agencyRuntimeRef.current?.invalidateDOM();
    });
    observer.observe(document.body, { subtree: true, childList: true, characterData: true, attributes: true,
      attributeFilter: ['href', 'hidden', 'disabled', 'aria-hidden', 'class', 'style'] });
    return () => observer.disconnect();
  }, []);

  const runLandingTour = useCallback(async () => {
    const authenticated = Boolean(authStore.getToken());
    const developmentOverride = developmentFullTourOverride();
    const accountEligible = tourEligibleForAccount(authenticated, developmentOverride);
    emitDevelopmentStartupTrace("tour_eligibility_result", { authenticated, development_full_tour_override: developmentOverride, eligible: accountEligible });
    if (!accountEligible) {
      emitOrbRuntimeEvent('landing_tour_skipped_authenticated');
      return;
    }
    const journey = websiteJourneyRef.current;
    const blockedReason = !journeyReadyRef.current ? 'journey_not_ready'
      : !journey ? 'journey_missing'
      : !isPublicLandingExperience() ? 'not_public_landing'
      : landingTourRunningRef.current ? 'already_running'
      : voiceRequestInFlightRef.current ? 'voice_turn_active'
      : recorderRef.current ? 'recorder_active'
      : onboardingSafeMode ? 'onboarding_safe_mode'
      : journey.stage !== 'LANDING_TOUR' ? 'stage_not_landing_tour'
      : null;
    if (blockedReason || !journey) {
      emitOrbRuntimeEvent('target_one_tour_start_blocked', { blockedReason, stage: journey?.stage || null, stopId: journey?.currentStopId || null });
      return;
    }
    if (journey.interruptionState.isInterrupted || journey.preflightStatus === "DEFERRED") {
      emitOrbRuntimeEvent('target_one_tour_start_blocked', { blockedReason: journey.interruptionState.isInterrupted ? 'interrupted' : 'preflight_deferred', stage: journey.stage, stopId: journey.currentStopId });
      return;
    }
    if (journey.interaction.pendingQuestionId || journey.interaction.activeDestinationRoute) {
      emitOrbRuntimeEvent('target_one_tour_start_blocked', { blockedReason: 'awaiting_governed_interaction', stage: journey.stage, stopId: journey.currentStopId, pendingQuestionId: journey.interaction.pendingQuestionId, activeDestinationRoute: journey.interaction.activeDestinationRoute });
      return;
    }
    emitOrbRuntimeEvent('target_one_tour_controller_initialized', {
      stage: journey.stage,
      chapterId: journey.currentChapterId,
      stopId: journey.currentStopId,
      modelEndpoint: 'http://127.0.0.1:16520/api/generate',
      apiEndpoint: 'http://127.0.0.1:16666/api/orb/website-text',
    });
    emitDevelopmentStartupTrace("tour_initialization", { stop_id: journey.currentStopId });
    landingTourRunningRef.current = true;
    let settleTour: () => void = () => undefined;
    landingTourSettledRef.current = new Promise<void>(resolve => { settleTour = resolve; });
    const controller = new AbortController();
    landingTourAbortControllerRef.current = controller;
    setTourNotice('');
    try {
      if (journey.salesPhase === 'ORIENT' || journey.salesPhase === 'DISCOVER') {
        // The public Track A path is purpose-governed by sales phase, not by
        // legacy technical curriculum coverage. Agency retains its existing
        // bounded candidate authorization and execution revalidation.
        const result = await getAgencyRuntime().beginSalesJourney(controller.signal);
        if (result !== 'awaiting_visitor') {
          throw new Error('Weaver could not prepare a governed discovery question. Your place is saved.');
        }
        return;
      }
      await runTourController({
        read: () => websiteJourneyRef.current,
        save: saveWebsiteJourney,
        agency: (_chapter, _stop, signal) => getAgencyRuntime().turn(signal),
        verifySection: async (stop, signal) => {
          if (signal.aborted) return false;
          emitOrbRuntimeEvent('target_one_governed_stop_activated', { stage: journey.stage, chapterId: websiteJourneyRef.current?.currentChapterId || null, stopId: stop.id });
          const section = document.querySelector<HTMLElement>(stop.sectionDomSelector);
          if (!section?.id) return false;
          if (stop.id === 'stop-hero-meet') {
            // The opening anchors the hero without initiating a scroll.
            const rect = section.getBoundingClientRect();
            return rect.width > 0 && rect.height > 0 && rect.bottom > HEADER_SAFE && rect.top < window.innerHeight - 24;
          }
          const visible = await scrollToLandingTourSection(section.id, signal);
          return visible && !signal.aborted;
        },
        demonstrate: async (chapter, stop, signal) => {
          const targetId = TOUR_POINTER_TARGETS[`${chapter.id}/${stop.id}`];
          if (!targetId) return true;
          const ready = await awaitAbortable(waitForPointerRecords(), signal);
          if (signal.aborted) return false;
          const target = ready ? findPointerRecordById(targetId) : null;
          if (!target) return false;
          // Existing Pointer/LiDAR/HAL verification and movement path.
          const guided = await guideToPointerRecord(target, "Demonstrate verified visual guidance without activating the target", { signal });
          return Boolean(guided) && !signal.aborted;
        },
        converse: async (chapter, stop, missing, engagement: TourEngagementQuestion | null, signal, attempt) => {
          const section = document.querySelector<HTMLElement>(stop.sectionDomSelector);
          if (!section || signal.aborted) throw new DOMException("Tour interrupted", "AbortError");
          const sourceSelectors = TOUR_STOP_SOURCE_SELECTORS[stop.id] || [stop.sectionDomSelector];
          const sourceText = sourceSelectors.map(selector => {
            const element = document.querySelector<HTMLElement>(selector);
            return element ? `[Page source ${selector}]\n${element.innerText}` : '';
          }).filter(Boolean).join('\n\n');
          setStatusTitle("Preparing voice");
          setStatusLine("Weaver is preparing this tour stop.");
          showStatus();
          emitOrbRuntimeEvent('tour_converse_started', { stopId: stop.id, evidenceAttempt: attempt, apiEndpoint: 'http://127.0.0.1:16666/api/orb/website-text' });
          emitDevelopmentStartupTrace("first_governed_tour_request", { stop_id: stop.id, evidence_attempt: attempt });
          const interaction = websiteJourneyRef.current?.interaction || journey.interaction;
          const result = await api.websiteOrbText(`Explain the current landing tour stop: ${stop.id}.`, true, signal, {
            project_id: activeOrbContext?.project_id,
            target_url: contextTargetUrl(),
            experience: {
              phase: "understanding",
              objective: "Explain the current curriculum concepts and provide supporting excerpts. The controller owns progression.",
              verification_state: "verified",
              tour: {
                chapter_id: chapter.id, stop_id: stop.id, purpose: stop.purpose,
                required_concepts: missing, avoid: [...chapter.avoid, ...(stop.avoid || [])],
                presentation_guidance: [...(chapter.presentationGuidance || []), ...(stop.presentationGuidance ? [stop.presentationGuidance] : [])],
                visible_section_text: sourceText.slice(0, 8000),
                evidence_attempt: attempt,
                // A failed articulation did not ask the visitor anything, so
                // retain this governed question for the final evidence attempt.
                engagement_question: engagement ? { id: engagement.id, prompt: engagement.prompt, intent: engagement.intent } : null,
                interaction_context: {
                  recent_weaver_statements: interaction.recentWeaverStatements,
                  covered_concept_ids: websiteJourneyRef.current?.completedTourConceptIds || journey.completedTourConceptIds,
                  asked_question_ids: interaction.askedQuestionIds,
                  visited_routes: interaction.visitedRoutes,
                  answer_signals: interaction.answerSignals,
                },
              },
            },
          });
          if (signal.aborted) throw new DOMException("Tour interrupted", "AbortError");
          emitOrbRuntimeEvent('tour_converse_received', { stopId: stop.id, hasAudio: Boolean(result.tts_audio_url), hasEvidence: Boolean(result.chapter_evaluation), llmSource: result.llm_source });
          if (result.tts_audio_url) emitDevelopmentStartupTrace("first_tour_audio_ready", { stop_id: stop.id });
          emitOrbRuntimeEvent('tour_articulation_received', {
            stopId: stop.id,
            source_facts: sourceText.slice(0, 2500),
            prompt_context: {
              purpose: stop.purpose,
              required_concepts: missing.map((concept) => ({ id: concept.id, description: concept.description })),
            },
            raw_spoken_output: result.tour_articulation_trace?.raw_model_output || result.tour_articulation_trace?.generated_output || result.spoken_output,
            evidence_model_output: result.tour_articulation_trace?.evidence_model_output || null,
            sanitized_output: result.tour_articulation_trace?.sanitized_output || result.spoken_output,
            final_spoken_text: result.tour_articulation_trace?.delivered_output || result.spoken_output,
            llm_source: result.llm_source,
            tts_provider: result.tts_provider || null,
            site_world_slice: result.tour_articulation_trace?.site_world_slice || null,
          });
          const evaluation = parseChapterEvaluation(result.chapter_evaluation, result.spoken_output);
          const cancelPlayback = () => {
            speechPlaybackSettlementRef.current?.cancel();
            speechAudioRef.current?.pause();
            try { speechSourceRef.current?.stop(); } catch { /* Already stopped. */ }
            speechPlaybackRef.current = false;
          };
          signal.addEventListener('abort', cancelPlayback, { once: true });
          try {
            const played = await speakWithGeneratedAudio(
              result.spoken_output,
              result.tts_audio_url,
              result.tts_provider,
              { onPlaybackStarted: () => emitDevelopmentStartupTrace("first_tour_speech_started", { stop_id: stop.id }) },
            );
            if (played) emitDevelopmentStartupTrace("first_tour_speech_completed", { stop_id: stop.id });
            if (signal.aborted) throw new DOMException("Tour interrupted", "AbortError");
            if (!played) throw new Error("Voice playback did not finish. Your tour position is saved.");
            const currentJourney = websiteJourneyRef.current;
            if (currentJourney) {
              saveWebsiteJourney({
                ...currentJourney,
                interaction: {
                  ...currentJourney.interaction,
                  recentWeaverStatements: [...currentJourney.interaction.recentWeaverStatements, result.spoken_output].slice(-4),
                },
              });
            }
            return evaluation;
          } finally { signal.removeEventListener('abort', cancelPlayback); }
        },
      }, controller.signal);
    } catch (error) {
      if (controller.signal.aborted || (error as Error)?.name === "AbortError") return;
      const message = error instanceof Error ? error.message : "The tour is paused. Your position is saved.";
      const status = error instanceof ApiError ? error.status : null;
      const cognitionUnavailable = status === 503 && /dynamic tour cognition/i.test(message);
      emitOrbRuntimeEvent('target_one_tour_execution_blocked', {
        stage: websiteJourneyRef.current?.stage || null,
        chapterId: websiteJourneyRef.current?.currentChapterId || null,
        stopId: websiteJourneyRef.current?.currentStopId || null,
        httpStatus: status,
        reason: message,
        cognitionUnavailable,
      });
      if (cognitionUnavailable) {
        cognitionUnavailableRef.current = true;
        handsFreeEnabledRef.current = false;
        setTourNotice('Weaver’s guided tour is paused because live cognition is unavailable. Your place is saved.');
        setStatusTitle('Tour waiting for live cognition');
        setStatusLine('Weaver cannot begin this guided stop until the live reasoning service returns.');
        showStatus(7200);
      } else {
        setTourNotice(message);
      }
    } finally {
      if (landingTourAbortControllerRef.current === controller) landingTourAbortControllerRef.current = null;
      landingTourRunningRef.current = false;
      settleTour();
    }
  }, [activeOrbContext?.project_id, contextTargetUrl, findPointerRecordById, getAgencyRuntime, guideToPointerRecord, onboardingSafeMode, saveWebsiteJourney, scrollToLandingTourSection, showStatus, speakWithGeneratedAudio, waitForPointerRecords]);

  useEffect(() => {
    const receiveReadiness = (event: Event) => {
      const detail = (event as CustomEvent).detail || {};
      if (detail.phase !== "STARTUP_WARMUP_READY") return;
      liveTourReadyRef.current = true;
      emitOrbRuntimeEvent("scripted_orientation_live_handoff_ready");
      if (scriptedLandingOpeningCompleteRef.current) {
        setStatusTitle("Weaver is ready for questions");
        setStatusLine("The guided tour is complete. Ask Weaver anything about this site.");
        showStatus(5200);
        emitOrbRuntimeEvent("scripted_landing_tour_questions_ready");
      }
    };
    window.addEventListener("orbweaver:startup-intro", receiveReadiness);
    return () => window.removeEventListener("orbweaver:startup-intro", receiveReadiness);
  }, [showStatus]);

  const resumeLandingTour = useCallback(async () => {
    await landingTourSettledRef.current;
    const state = websiteJourneyRef.current;
    if (!state || state.stage !== 'LANDING_TOUR' || state.preflightStatus === 'DEFERRED') return;
    if (voiceRequestInFlightRef.current || recorderRef.current) {
      setTourNotice('Finish speaking to continue the tour.');
      return;
    }
    try {
      saveWebsiteJourney({ ...state,
        interruptionState: { isInterrupted: false, interruptedAtChapterId: null, interruptedAtStopId: null } });
      void runLandingTour();
    } catch (error) { setTourNotice((error as Error).message); }
  }, [runLandingTour, saveWebsiteJourney]);

  const retryPausedTour = useCallback(() => {
    cognitionUnavailableRef.current = false;
    setTourNotice('');
    emitOrbRuntimeEvent('target_one_tour_retry_requested', {
      stage: websiteJourneyRef.current?.stage || null,
      chapterId: websiteJourneyRef.current?.currentChapterId || null,
      stopId: websiteJourneyRef.current?.currentStopId || null,
    });
    void resumeLandingTour();
  }, [resumeLandingTour]);

  const chooseTourDecision = useCallback((action: TourDecisionAction) => {
    const state = websiteJourneyRef.current;
    if (!state || !isTourDecisionReady(state)) return false;
    try {
      if (action === 'DEFER_PREFLIGHT') {
        saveWebsiteJourney({ ...state, preflightStatus: 'DEFERRED' });
        setTourNotice('Weaver will leave Preflight for later and keep the visitor on the current page.');
      } else if (action === 'RUN_PREFLIGHT_NOW') {
        // A spoken visitor choice authorizes routing, never scan completion.
        navigate('/preflight');
      }
      return true;
    } catch (error) {
      setTourNotice((error as Error).message);
      return false;
    }
  }, [navigate, saveWebsiteJourney]);

  const applyEngagementAnswer = useCallback(async (transcript: string, signal: AbortSignal): Promise<boolean> => {
    if (websiteJourneyRef.current?.stage !== 'LANDING_TOUR') return false;
    const handled = await getAgencyRuntime().answer(transcript, signal);
    if (handled && !websiteJourneyRef.current?.interaction.pendingQuestionId &&
      !websiteJourneyRef.current?.interaction.activeDestinationRoute) {
      window.setTimeout(() => void resumeLandingTour(), 360);
    }
    return handled;
  }, [getAgencyRuntime, resumeLandingTour]);

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
    setVoiceState("thinking");
    showStatus();
    freezeOrbInPlace(4200);
    try {
      logVoice("website-voice", turnId);
      const targetUrl = contextTargetUrl();
      const visitorTurn = Math.min(20, firstEncounterVisitorTurnRef.current + 1);
      firstEncounterVisitorTurnRef.current = visitorTurn;
      const inFirstEncounter = isPublicLandingExperience() && !firstEncounterComplete();
      const guidedConversation = scriptedOrientationInterruptedRef.current || window.location.pathname === ONBOARDING_ROUTE;
      const experience: WebsiteOrbExperienceContext | null = scriptedOrientationInterruptedRef.current
        ? {
            phase: "agency",
            guidance_mode: "tour_question",
            objective: TOUR_INTERRUPTION_GUIDE_PROTOCOL,
            visitor_turn: visitorTurn,
            verification_state: "verified",
            demonstrated_capabilities: ["verified tour context", "visitor-directed navigation", "Founding Beta and investor routing"],
          }
        : inFirstEncounter
        ? visitorTurn === 1
          ? {
              phase: "make_it_personal",
              objective: "Respond to the visitor's actual first request, show that it was understood in context, and guide to a verified relevant target when one exists.",
              visitor_turn: visitorTurn,
              verification_state: "pending",
              demonstrated_capabilities: ["Faster Whisper transcription", "Site World reasoning", "Kokoro voice"],
            }
          : {
              phase: "relevant_continuation",
              objective: "Continue from the visitor's words and prior demonstrated capability with a relevant next step, preserving their progress and transitioning into normal consultation.",
              visitor_turn: visitorTurn,
              verification_state: "pending",
              demonstrated_capabilities: ["voice turn-taking", "contextual reasoning", "verified visual guidance"],
            }
        : window.location.pathname === ONBOARDING_ROUTE
          ? {
              phase: "agency",
              guidance_mode: "account_setup",
              objective: ACCOUNT_CREATION_GUIDE_PROTOCOL,
              visitor_turn: visitorTurn,
              verification_state: "verified",
              verified_target_id: onboardingLiveRecordRef.current?.target_id || null,
              verified_target_label: onboardingLiveRecordRef.current?.meaning || null,
              demonstrated_capabilities: ["verified visual guidance", "visitor-controlled account setup", "optional Preflight review"],
            }
          : null;
      const result = await api.websiteOrbVoice(audio, controller.signal, {
        project_id: activeOrbContext?.project_id,
        target_url: targetUrl,
        experience,
        transcribe_only: !guidedConversation && websiteJourneyRef.current?.stage === 'LANDING_TOUR',
      });
      if (!guidedConversation && await applyEngagementAnswer(result.transcript || "", controller.signal)) return;
      const decisionAction = resolveTourDecisionAction(result.transcript || "");
      if (!guidedConversation && decisionAction && chooseTourDecision(decisionAction)) return;
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
      const responsePlayed = await speakWithGeneratedAudio(spokenOutput, result.tts_audio_url, result.tts_provider);
      if (!responsePlayed) return;
      if (controller.signal.aborted) return;
      const requestedRoute = resolveDirectRouteNavigation(result.transcript || "");
      if (requestedRoute && executeVerifiedDirectRouteNavigation(requestedRoute)) return;
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
      if (websiteJourneyRef.current?.stage === "LANDING_TOUR") {
        window.setTimeout(resumeLandingTour, 360);
      }
    } catch (error) {
      if ((error as Error)?.name === "AbortError") return;
      const message = error instanceof Error ? error.message : "Voice temporarily unavailable";
      const status = error instanceof ApiError ? error.status : null;
      const cognitionUnavailable = status === 503 && /cognition.*unavailable|act was not advanced/i.test(message);
      if (cognitionUnavailable) {
        cognitionUnavailableRef.current = true;
        handsFreeEnabledRef.current = false;
        setTourNotice('Weaver is holding here until live cognition returns. Your tour place is saved.');
        setStatusTitle('Voice waiting for live cognition');
        setStatusLine('Automatic listening is paused to avoid retrying an unavailable reasoning service.');
        emitOrbRuntimeEvent('voice_turn_cognition_blocked', { turnId, httpStatus: status, reason: message });
      } else {
        setStatusTitle("Voice reconnecting");
        setStatusLine("Voice temporarily unavailable");
      }
      setVoiceState("idle");
      showStatus(cognitionUnavailable ? 7200 : 3600);
    } finally {
      if (activeVoiceAbortControllerRef.current === controller) {
        activeVoiceAbortControllerRef.current = null;
        voiceRequestInFlightRef.current = false;
        setVoiceState("idle");
        setVoiceRearmSequence((value) => value + 1);
      }
      logVoice("finalized", turnId);
    }
  }, [activeOrbContext?.project_id, applyEngagementAnswer, chooseTourDecision, contextTargetUrl, executeOrbControlAction, executeVerifiedDirectRouteNavigation, firstEncounterComplete, freezeOrbInPlace, guideFromRuntimeResult, logVoice, markFirstEncounter, markVisitorActivity, resumeLandingTour, showStatus, speakWithGeneratedAudio]);

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

  const startOrbRecording = useCallback(async () => {
    if (landingTourRunningRef.current) return;
    unlockAudio();
    if (voiceRequestInFlightRef.current || voiceState === "speaking") return;

    // Website ORB voice is a single verifiable path: browser MediaRecorder →
    // Faster Whisper → governed response → Kokoro WAV.  Browser speech
    // recognition would bypass the recorded-audio proof and must not win the
    // microphone turn merely because a browser exposes that API.
    emitOrbRuntimeEvent("recorded_audio_stt_selected", { engine: "faster_whisper" });

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
  }, [freezeOrbInPlace, logVoice, monitorRecordingSilence, playPulse, processRecordedOrbAudio, showStatus, stopOrbRecording, unlockAudio, voiceState]);

  const interruptOrbSpeech = useCallback(() => {
    handsFreeEnabledRef.current = false;
    const journey = websiteJourneyRef.current;
    if (journey?.stage === 'LANDING_TOUR' && !journey.interruptionState.isInterrupted) {
      try {
        saveWebsiteJourney({ ...journey, interruptionState: {
          isInterrupted: true, interruptedAtChapterId: journey.currentChapterId, interruptedAtStopId: journey.currentStopId,
        } });
      } catch (error) { setTourNotice((error as Error).message); }
    }
    // Keep the exact tour position in session state while the visitor takes
    // the floor. The recorded-audio answer resumes it after this turn.
    landingTourAbortControllerRef.current?.abort();
    activeVoiceAbortControllerRef.current?.abort();
    activeVoiceAbortControllerRef.current = null;
    voiceRequestInFlightRef.current = false;
    speechPlaybackSettlementRef.current?.cancel();
    speechPlaybackSettlementRef.current = null;
    stopSpeechCaptions(false);
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
    stopSpeechVisualizer();
    if (latencyAudioRef.current) {
      latencyAudioRef.current.pause();
      latencyAudioRef.current = null;
    }
    setStatusTitle("Interrupted");
    setStatusLine("I’ve paused here. Tap Weaver, then tell me where you want to go next.");
    setVoiceState("idle");
    showStatus(1600);
    avoidUntilRef.current = Date.now() + 900;
    emitOrbRuntimeEvent("playback_interrupted", { turnId: voiceTurnIdRef.current });
    window.setTimeout(() => void resumeAutonomousPresence(), 120);
  }, [resumeAutonomousPresence, saveWebsiteJourney, showStatus, stopSpeechCaptions, stopSpeechVisualizer]);

  const handleOrbPointerDown = useCallback((event: React.PointerEvent<HTMLDivElement>) => {
    if ((event.target as HTMLElement).closest("button")) return;
    if (speechPlaybackRef.current) interruptOrbSpeech();
    markVisitorActivity();
    move.stop();
    manualHoldRef.current = true;
    nudgePointerRef.current = {
      pointerId: event.pointerId,
      start: { x: event.clientX, y: event.clientY },
      origin: { ...positionRef.current },
    };
    event.currentTarget.setPointerCapture(event.pointerId);
  }, [interruptOrbSpeech, markVisitorActivity, move]);

  const handleOrbPointerMove = useCallback((event: React.PointerEvent<HTMLDivElement>) => {
    const drag = nudgePointerRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    const destination = clampPosition(
      drag.origin.x + event.clientX - drag.start.x,
      drag.origin.y + event.clientY - drag.start.y,
    );
    const authorization = authorizeMotion(destination, "Summon");
    if (!authorization) return;
    assertMovementAuthorization(authorization);
    move.set(destination);
    positionRef.current = destination;
    markVisitorActivity();
    emitOrbRuntimeEvent("orb_nudged", { destination, governance_trace_id: authorization.governanceTraceId });
  }, [authorizeMotion, clampPosition, markVisitorActivity, move]);

  const handleOrbPointerUp = useCallback((event: React.PointerEvent<HTMLDivElement>) => {
    if (!nudgePointerRef.current || nudgePointerRef.current.pointerId !== event.pointerId) return;
    nudgePointerRef.current = null;
    manualHoldRef.current = false;
    event.currentTarget.releasePointerCapture?.(event.pointerId);
    window.setTimeout(() => void resumeAutonomousPresenceRef.current(), 650);
  }, []);

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

  const waitForStartupGate = useCallback(async (): Promise<"READY" | "BLOCKED"> => {
    if (!isPublicLandingExperience()) return "READY";
    if (window.sessionStorage.getItem(LANDING_SPLASH_COMPLETE_SESSION_KEY) === "1") {
      updateStartupDiagnostics({ splash_state: "skipped_session_once" });
      return window.sessionStorage.getItem(LANDING_STARTUP_READINESS_SESSION_KEY) === "BLOCKED"
        ? "BLOCKED"
        : "READY";
    }

    updateStartupDiagnostics({ splash_state: "playing", orb_readiness_state: "waiting_for_gate" });
    return new Promise<"READY" | "BLOCKED">((resolve) => {
      let settled = false;
      const settle = (readiness: "READY" | "BLOCKED") => {
        if (settled) return;
        settled = true;
        window.clearTimeout(timeout);
        window.removeEventListener(STARTUP_GATE_COMPLETE_EVENT, handler);
        resolve(readiness);
      };
      const timeout = window.setTimeout(() => {
        emitOrbRuntimeEvent("startup_gate_failed_closed", { reason: "startup_gate_timeout" });
        settle("BLOCKED");
      }, 30000);
      const handler = (event: Event) => {
        const detail = (event as CustomEvent).detail || {};
        unlockAudio();
        updateStartupDiagnostics({
          splash_state: detail.splash_state === "skipped_session_once" ? "skipped_session_once" : "complete",
          permission_state: detail.permission_state === "user_activated" ? "user_activated" : "waiting",
        });
        settle(detail.readiness_state === "BLOCKED" ? "BLOCKED" : "READY");
      };
      window.addEventListener(STARTUP_GATE_COMPLETE_EVENT, handler, { once: true });
      // LandingPage can complete its non-blocking opening before this mount
      // effect subscribes. Session state is the durable handoff; the event is
      // only the fast path.
      if (window.sessionStorage.getItem(LANDING_SPLASH_COMPLETE_SESSION_KEY) === "1") {
        settle(window.sessionStorage.getItem(LANDING_STARTUP_READINESS_SESSION_KEY) === "BLOCKED" ? "BLOCKED" : "READY");
      }
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
      // Mobile browsers require microphone permission to follow a user
      // gesture. The Pause/Continue control is the explicit permission gate;
      // never prompt during automatic landing startup.
      micReady: Promise.resolve(false),
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
  }, [showStatus, unlockAudio, updateStartupDiagnostics]);

  const runStartupVoiceSequence = useCallback(async () => {
    const onLanding = isPublicLandingExperience();
    const authenticatedExistingAccount = Boolean(authStore.getToken());
    const fullTourDevelopmentOverride = developmentFullTourOverride();
    const accountTourEligible = tourEligibleForAccount(authenticatedExistingAccount, fullTourDevelopmentOverride);
    emitDevelopmentStartupTrace("authenticated_account_detected", { authenticated: authenticatedExistingAccount });
    emitDevelopmentStartupTrace("full_tour_development_override", { active: fullTourDevelopmentOverride });
    const greetingAlreadyPlayed =
      window.sessionStorage.getItem(STARTUP_GREETING_SESSION_KEY) === "1";

    if (!shouldRunMountedStartupVoiceSequence({
      startupAutoStarted: startupAutoStartedRef.current,
      onboardingSafeMode,
      onLanding,
      greetingAlreadyPlayed,
      voiceReady: firstEncounterStateRef.current.voice_ready,
    })) return;

    startupAutoStartedRef.current = true;
    let micReady = false;
    const startupPreparation =
      onLanding && !greetingAlreadyPlayed
        ? prepareStartupVoice()
        : null;

    emitOrbRuntimeEvent("orb_mount_confirmed", { onLanding });
    updateStartupDiagnostics({ orb_readiness_state: onLanding ? "waiting_for_gate" : "mounting" });
    const startupReadiness = await waitForStartupGate();
    const liveTourReady = startupReadiness === "READY";
    if (!liveTourReady) {
      emitOrbRuntimeEvent("startup_readiness_blocked", {
        reason: "cognition_not_ready",
      });
    }

    // LandingPage owns the scripted splash introduction. Re-check after the
    // gate because it may have completed while this component was waiting.
    const splashHandledGreeting =
      window.sessionStorage.getItem(STARTUP_GREETING_SESSION_KEY) === "1";

    if (onLanding && !greetingAlreadyPlayed && !splashHandledGreeting) {
      const preparation = startupPreparation ?? prepareStartupVoice();
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
        introAudioPlayed = await spokenGreeting;
        if (!introAudioPlayed) throw new Error("Startup voice playback failed");
        updateStartupDiagnostics({ audio_tts_state: "played", greeting_state: "played" });
        markFirstEncounter("entrance_complete");
      } catch {
        updateStartupDiagnostics({ audio_tts_state: "failed", greeting_state: "failed" });
        // Recovery is still a valid spoken introduction. Preserve its result
        // so a transient primary-playback failure cannot strand the visitor
        // between the splash and Target One.
        const recoveryOutcome = await speakRecovery(preparation.greeting);
        introAudioPlayed = recoveryOutcome === "played";
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

      if (!introAudioPlayed) {
        // A cancelled or unavailable voice path must not dead-end the host.
        // The tour will surface its own governed evidence/voice status.
        emitOrbRuntimeEvent("intro_continuing_without_audio");
      }

      // The intro is complete only after its playback promise settles. Keep a
      // small deterministic boundary before the first tour pointer/navigation
      // action so the two experiences cannot visually overlap.
      emitOrbRuntimeEvent("intro_to_tour_settle_started", { delayMs: INTRO_TO_TOUR_SETTLE_MS });
      await wait(INTRO_TO_TOUR_SETTLE_MS);
      emitOrbRuntimeEvent("intro_to_tour_settle_completed");
      const scriptedOpeningComplete = await runScriptedOrientation("site:full-tour", SITE_TOUR_SCRIPT);
      scriptedLandingOpeningCompleteRef.current = scriptedOpeningComplete;
      if (scriptedOpeningComplete && (liveTourReady || liveTourReadyRef.current)) {
        setStatusTitle("Weaver is ready for questions");
        setStatusLine("The guided tour is complete. Ask Weaver anything about this site.");
        showStatus(5200);
        emitOrbRuntimeEvent("scripted_landing_tour_questions_ready");
      } else emitOrbRuntimeEvent("scripted_landing_tour_waiting_for_readiness");
    } else {
      updateStartupDiagnostics({ greeting_state: splashHandledGreeting || greetingAlreadyPlayed ? "skipped_session_once" : "waiting" });
      if (onLanding && splashHandledGreeting) {
        // LandingPage owns the authored splash audio. Its durable completion
        // marker proves playback ended, but the first governed tour action
        // still gets the same short visual/audio settle boundary.
        emitOrbRuntimeEvent("intro_to_tour_settle_started", { delayMs: INTRO_TO_TOUR_SETTLE_MS });
        await wait(INTRO_TO_TOUR_SETTLE_MS);
        emitOrbRuntimeEvent("intro_to_tour_settle_completed");
        const scriptedOpeningComplete = await runScriptedOrientation("site:full-tour", SITE_TOUR_SCRIPT);
        scriptedLandingOpeningCompleteRef.current = scriptedOpeningComplete;
        emitOrbRuntimeEvent("intro_handoff_to_scripted_landing_tour");
        if (scriptedOpeningComplete && (liveTourReady || liveTourReadyRef.current)) {
          setStatusTitle("Weaver is ready for questions");
          setStatusLine("The guided tour is complete. Ask Weaver anything about this site.");
          showStatus(5200);
          emitOrbRuntimeEvent("scripted_landing_tour_questions_ready");
        } else emitOrbRuntimeEvent("scripted_landing_tour_waiting_for_readiness", { scriptedOpeningComplete, liveTourReady: liveTourReady || liveTourReadyRef.current, accountTourEligible });
      } else if (onLanding && authenticatedExistingAccount && !accountTourEligible) {
        emitOrbRuntimeEvent("landing_tour_skipped_authenticated");
      }
      // Scripted orientation is the only automatic speech. Microphone access
      // remains an explicit visitor action after that first explanation.
      updateStartupDiagnostics({ orb_readiness_state: "ready" });
      emitOrbRuntimeEvent("orb_ready");
    }

    if (micReady && activeRef.current) {
      handsFreeEnabledRef.current = true;
      window.setTimeout(() => {
        if (!activeRef.current || landingTourRunningRef.current || voiceRequestInFlightRef.current || recorderRef.current) return;
        void startOrbRecording();
      }, 420);
    }
  }, [guideToPointerRecord, markFirstEncounter, onboardingSafeMode, prepareStartupVoice, runScriptedOrientation, setGreetingActive, showStatus, speak, speakRecovery, startOrbRecording, updateStartupDiagnostics, waitForStartupGate]);

  // Keep the mounted startup path pointed at the live sequence before mount
  // effects can call it.
  prepareStartupVoiceRef.current = prepareStartupVoice;
  runStartupVoiceSequenceRef.current = runStartupVoiceSequence;

  useEffect(() => {
    if (location.pathname === "/" || onboardingSafeMode) return;
    const orientation = scriptedPageOrientation(location.pathname);
    if (!orientation) return;
    void runScriptedOrientation(`page:${location.pathname}`, [orientation])
      .finally(() => {
        updateStartupDiagnostics({ orb_readiness_state: "ready" });
        emitOrbRuntimeEvent("orb_ready");
      });
  }, [location.pathname, onboardingSafeMode, runScriptedOrientation, updateStartupDiagnostics]);

  const handleOrbClick = useCallback(() => {
    markVisitorActivity();
    if (scriptedOrientationRunningRef.current) {
      // A tour is guided, never locked. The visitor may pause it to ask a
      // question or request a verified alternate destination at any moment.
      scriptedOrientationInterruptedRef.current = true;
      interruptOrbSpeech();
      setStatusTitle("Tour paused");
      setStatusLine("Ask Weaver a question, ask about the Founding Beta, or request an investor conversation.");
      showStatus(6200);
      emitOrbRuntimeEvent("scripted_orientation_pause_requested", { route: location.pathname });
      window.setTimeout(() => {
        if (!voiceRequestInFlightRef.current && !recorderRef.current) void startOrbRecording();
      }, 180);
      return;
    }
    if (voiceState === "speaking" || landingTourRunningRef.current) {
      interruptOrbSpeech();
      return;
    }

    if (recorderRef.current) {
      stopOrbRecording(true);
      return;
    }

    void startOrbRecording();
  }, [interruptOrbSpeech, location.pathname, markVisitorActivity, showStatus, startOrbRecording, stopOrbRecording, voiceState]);

  const resetStartupSequence = useCallback(() => {
    window.sessionStorage.removeItem(LANDING_SPLASH_SESSION_KEY);
    window.sessionStorage.removeItem(LANDING_SPLASH_COMPLETE_SESSION_KEY);
    window.sessionStorage.removeItem(LANDING_STARTUP_READINESS_SESSION_KEY);
    window.sessionStorage.removeItem(SCRIPTED_ORIENTATION_SESSION_KEY);
    window.sessionStorage.removeItem(STARTUP_GREETING_SESSION_KEY);
    window.sessionStorage.removeItem(FIRST_ENCOUNTER_STORAGE_KEY);
    window.sessionStorage.removeItem(WEBSITE_JOURNEY_STORAGE_KEY);
    firstEncounterStateRef.current = { ...EMPTY_FIRST_ENCOUNTER_STATE };
    websiteJourneyRef.current = createInitialJourneyState();
    setTourState(websiteJourneyRef.current);
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
    // The one existing audio control is also the permitted user gesture for a
    // browser-blocked landing introduction; no startup card/button is needed.
    window.dispatchEvent(new CustomEvent("orbweaver:startup-audio-permission"));
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
    const syncStoredIntroPresence = () => {
      if (document.documentElement.dataset[INTRO_SPEECH_STATE_DATASET_KEY] !== "speaking") return;
      markVisitorActivity();
      setGreetingActive(true);
      setVoiceState("speaking");
      startFallbackSpeechVisualizer();
    };
    const syncIntroPresence = (event: Event) => {
      const detail = (event as CustomEvent<{ phase?: string; text?: string | null }>).detail;
      const phase = detail?.phase;
      if (phase === "INTRO_AUDIO_PLAYING") {
        markVisitorActivity();
        setGreetingActive(true);
        setVoiceState("speaking");
        // The intro is played by LandingPage rather than the normal ORB TTS
        // path. Give that audio the same centre-only speech response.
        startFallbackSpeechVisualizer();
      } else if (phase === "INTRO_CAPTION") {
        const text = detail?.text?.trim() || "";
        setSpeechCaption({ fullText: text, revealedText: text, phase: text ? "speaking" : "idle", collapsed: false, expanded: false });
      } else if (phase === "INTRO_AUDIO_ENDED" || phase === "INTRO_AUDIO_ERROR") {
        setGreetingActive(false);
        setSpeechCaption({ fullText: "", revealedText: "", phase: "idle", collapsed: false, expanded: false });
        if (!speechPlaybackRef.current) {
          stopSpeechVisualizer();
          setVoiceState("idle");
        }
      }
    };
    // The LandingPage value is set only after audio.play() resolves. Reading it
    // closes an event-subscription race without inventing a splash-only pulse.
    syncStoredIntroPresence();
    window.addEventListener("orbweaver:startup-intro", syncIntroPresence);
    return () => window.removeEventListener("orbweaver:startup-intro", syncIntroPresence);
  }, [markVisitorActivity, startFallbackSpeechVisualizer, stopSpeechVisualizer]);

  useEffect(() => {
    if (!isPublicLandingExperience() || landingTourRunningRef.current) return;
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
      if (!activeRef.current || landingTourRunningRef.current || voiceRequestInFlightRef.current || recorderRef.current) return;
      void startOrbRecording();
    }, 720);

    return () => window.clearTimeout(rearmTimer);
  }, [onboardingSafeMode, startOrbRecording, voiceRearmSequence, voiceState]);

  useEffect(() => {
    const activityHandler = () => markVisitorActivity();
    const sequenceHandler = () => bumpWorldStateSequence();

    window.addEventListener("pointerdown", activityHandler, { passive: true });
    window.addEventListener("touchstart", activityHandler, { passive: true });
    window.addEventListener("click", activityHandler, { passive: true });
    window.addEventListener("input", activityHandler, { passive: true });
    window.addEventListener("keydown", activityHandler);
    window.addEventListener("scroll", activityHandler, { passive: true });

    window.addEventListener("resize", sequenceHandler);
    window.addEventListener("popstate", sequenceHandler);
    window.addEventListener("hashchange", sequenceHandler);

    return () => {
      window.removeEventListener("pointerdown", activityHandler);
      window.removeEventListener("touchstart", activityHandler);
      window.removeEventListener("click", activityHandler);
      window.removeEventListener("input", activityHandler);
      window.removeEventListener("keydown", activityHandler);
      window.removeEventListener("scroll", activityHandler);

      window.removeEventListener("resize", sequenceHandler);
      window.removeEventListener("popstate", sequenceHandler);
      window.removeEventListener("hashchange", sequenceHandler);
    };
  }, [bumpWorldStateSequence, markVisitorActivity]);

  useEffect(() => {
    const handlePreflightComplete = (event: Event) => {
      const detail = (event as CustomEvent<PublicPreflightReport>).detail;
      if (!detail?.generated_at || preflightNarratedReportRef.current === detail.generated_at) return;
      preflightNarratedReportRef.current = detail.generated_at;
      // During the authored tour, a scan is the visitor's explicit action but
      // its explanation belongs after account creation.  Do not interrupt the
      // tour or make the account handoff compete with result narration.
      if (scriptedOrientationRunningRef.current) {
        setStatusTitle('Preflight result ready');
        setStatusLine('Your result is ready. We can optionally review it after account creation, before a full-site scan.');
        showStatus(7000);
        emitOrbRuntimeEvent('preflight_review_deferred_until_post_account', {
          generated_at: detail.generated_at,
          site_url: detail.site_url || null,
        });
        return;
      }
      preflightWalkthroughAbortRef.current?.abort();
      const walkthroughController = new AbortController();
      preflightWalkthroughAbortRef.current = walkthroughController;

      if (!detail.outcome || !detail.site_url) return;

      const findingSequence = ['overview', 'reasons', 'boundaries', 'offers']
        .map((kind) => document.querySelector<HTMLElement>(`[data-preflight-finding="${kind}"]`))
        .filter((element): element is HTMLElement => Boolean(element));
      const resultRecord = (element: HTMLElement, index: number): WebsiteOrbPointerRecord => {
        const findingKey = element.dataset.preflightFinding || `unclassified-${index}`;
        const targetId = `preflight-result-${detail.generated_at}-${findingKey}`;
        // The report is factual authority and this exact rendered card is its
        // presentation surface. Bind a per-report identity before validation;
        // a stale cache coordinate alone can never pass the later live check.
        element.setAttribute('data-orb-target', targetId);
        const rect = element.getBoundingClientRect();
        lidarCacheRef.current.injectFrame({
          event_type: 'pointer_target_lock',
          target_id: targetId,
          absolute_top: rect.top + window.scrollY,
          absolute_left: rect.left + window.scrollX,
          width: rect.width,
          height: rect.height,
          semantic_intent: 'rendered_preflight_finding',
          movement_vector: 'glide',
          confidence: 1,
          metadata: { report_generated_at: detail.generated_at, finding: findingKey },
          timestamp_iso: new Date().toISOString(),
        });
        emitOrbRuntimeEvent('preflight_lidar_target_mapped', {
          targetId,
          finding: findingKey,
          source: 'rendered_preflight_dom',
        });
        return {
          target_id: targetId,
          page_route: window.location.pathname,
          target_type: 'preflight_result',
          content_fingerprint: `preflight:${detail.generated_at}:${findingKey}`,
          semantic_locator: `[data-orb-target="${targetId}"]`,
          confidence: 1,
          confidence_class: 'VERIFIED',
          finding_class: 'CONFIRMED',
          pointer_health: 'OWNER_VERIFIED',
          runtime_policy: { may_point: true, requires_live_verification: true },
        };
      };

      const walkRenderedResults = async () => {
        if (findingSequence.length === 0) {
          setStatusTitle('Preflight result ready');
          setStatusLine('I have the result, but I cannot prepare the explanation right now.');
          showStatus(7000);
          return;
        }
        for (const [index, element] of findingSequence.entries()) {
          if (walkthroughController.signal.aborted || window.location.pathname !== '/preflight') return;
          const liveText = element.innerText.replace(/\s+/g, ' ').trim();
          if (!liveText) continue;
          const record = resultRecord(element, index);
          const guided = await guideToPointerRecord(record, `Explain this Preflight result: ${liveText.slice(0, 220)}`, { signal: walkthroughController.signal });
          if (!guided) continue;
          if (walkthroughController.signal.aborted || window.location.pathname !== '/preflight') return;
          const findingFacts = index === 0
            ? [detail.outcome_title, detail.summary, `Fit score: ${detail.fit_score}/100`, `Pages read: ${detail.basic_checks?.pages_read ?? detail.basic_checks?.sample_pages_read ?? 0}`]
            : index === 1
              ? detail.reasons
              : index === 2
                ? [detail.notice, detail.install_path, detail.premium_status]
                : [
                    'Offer 1: Continue to onboarding.',
                    'Offer 2: Purchase complete full-site scans and data for $49.95.',
                    'Offer 3: Proceed toward ORB production.',
                    'The visitor must choose; do not initiate an offer automatically.',
                  ];
          const result = await api.websiteOrbText(
            'Interpret this verified Preflight finding for the visitor in natural speech. Explain what it means and why it matters, then connect it to the next useful choice when appropriate.',
            true,
            undefined,
            {
              target_url: detail.site_url,
              experience: {
                phase: 'understanding',
                objective: 'Explain one actual Preflight finding without reading the card mechanically.',
                verification_state: 'verified',
                tour: {
                  chapter_id: 'preflight-results',
                  stop_id: `finding-${index}`,
                  purpose: 'Explain the current verified Preflight finding.',
                  required_concepts: [{
                    id: `preflight-finding-${index}`,
                    description: findingFacts.filter(Boolean).join(' '),
                  }],
                  avoid: ['Do not invent findings.', 'Do not imply unknown or unevaluated items are absent.', 'Do not choose an offer for the visitor.'],
                  presentation_guidance: ['Use the live DOM only to locate what the visitor is seeing; the persisted report is factual authority.'],
                  visible_section_text: liveText.slice(0, 2500),
                  evidence_attempt: 1,
                },
              },
            },
          );
          emitOrbRuntimeEvent('preflight_articulation_received', {
            finding_index: index,
            source_facts: findingFacts,
            raw_spoken_output: result.spoken_output,
            final_spoken_text: result.spoken_output,
            llm_source: result.llm_source,
            tts_provider: result.tts_provider || null,
          });
          if (!result.chapter_evaluation || !result.spoken_output.trim()) {
            setStatusTitle('Preflight explanation unavailable');
            setStatusLine('I have your result, but I cannot prepare the explanation right now.');
            showStatus(7000);
            continue;
          }
          if (walkthroughController.signal.aborted || window.location.pathname !== '/preflight') return;
          await speakWithGeneratedAudio(result.spoken_output, result.tts_audio_url, result.tts_provider);
        }
      };

      void walkRenderedResults()
        .catch(() => {
          setStatusTitle('Preflight explanation unavailable');
          setStatusLine('I have your result, but I cannot prepare the explanation right now.');
          showStatus(7000);
        });
    };

    window.addEventListener('orbweaver:preflight-complete', handlePreflightComplete);
    return () => window.removeEventListener('orbweaver:preflight-complete', handlePreflightComplete);
  }, [guideToPointerRecord, showStatus, speakWithGeneratedAudio]);

  useEffect(() => {
    const recordApprovedOnboarding = (event: Event) => {
      const detail = (event as CustomEvent<{ destination?: unknown; first_target_id?: unknown }>).detail || {};
      const destination = typeof detail.destination === "string" ? detail.destination : `${ONBOARDING_ROUTE}?intent=site_onboarding`;
      const firstTargetId = typeof detail.first_target_id === "string" ? detail.first_target_id : ONBOARDING_FIRST_TARGET_ID;
      const journey = websiteJourneyRef.current;
      if (!journey || !journeyReadyRef.current) return;

      saveWebsiteJourney({
        ...journey,
        stage: "ONBOARDING",
        currentChapterId: null,
        currentStopId: null,
        currentStopCoveredConceptIds: [],
        interruptionState: { isInterrupted: false, interruptedAtChapterId: null, interruptedAtStopId: null },
      });
      const continuation = { destination, firstTargetId, approvedAt: Date.now() };
      preflightWalkthroughAbortRef.current?.abort();
      if (!saveOnboardingContinuation(continuation)) {
        setTourNotice("Your onboarding handoff could not be saved. Please enable session storage to continue.");
        return;
      }
      emitOrbRuntimeEvent("onboarding_continuation_recorded", {
        destination,
        firstTargetId,
        journey_stage: "ONBOARDING",
      });
    };

    window.addEventListener("orbweaver:onboarding-approved", recordApprovedOnboarding);
    return () => window.removeEventListener("orbweaver:onboarding-approved", recordApprovedOnboarding);
  }, [saveWebsiteJourney]);

  useEffect(() => {
    if (location.pathname !== ONBOARDING_ROUTE) {
      onboardingLiveRecordRef.current = null;
      return;
    }

    const continuation = readOnboardingContinuation();
    const journey = websiteJourneyRef.current;
    if (!continuation || !journey || journey.stage !== "ONBOARDING" ||
      routeForUrl(continuation.destination) !== ONBOARDING_ROUTE ||
      continuation.firstTargetId !== ONBOARDING_FIRST_TARGET_ID) return;

    let cancelled = false;
    const controller = new AbortController();
    const attachLiveTarget = async () => {
      // Wait for the actual signup page to hydrate. This is a locator only;
      // `guideToPointerRecord` must still prove connection, visibility,
      // identity, current geometry, and final-arrival geometry before Ping.
      await awaitAbortable(wait(160), controller.signal).catch(() => undefined);
      if (cancelled || controller.signal.aborted) return;
      for (let attempt = 0; !cancelled && attempt < 20; attempt += 1) {
        const target = document.querySelector<HTMLElement>('[data-orb-target="full-name-field"]');
        if (target && document.body.contains(target)) {
          const record = onboardingFirstTargetRecord();
          onboardingLiveRecordRef.current = record;
          const rect = target.getBoundingClientRect();
          lidarCacheRef.current.load([...pointerRecordsRef.current, record]);
          lidarCacheRef.current.injectFrame({
            event_type: "pointer_target_lock",
            target_id: record.target_id,
            absolute_top: rect.top + window.scrollY,
            absolute_left: rect.left + window.scrollX,
            width: rect.width,
            height: rect.height,
            semantic_intent: "onboarding_continuation",
            movement_vector: "glide",
            confidence: 1,
            metadata: { route: location.pathname, continuation_approved_at: continuation.approvedAt },
            timestamp_iso: new Date().toISOString(),
          });
          emitOrbRuntimeEvent("onboarding_lidar_target_mapped", {
            targetId: record.target_id,
            route: location.pathname,
            source: "live_onboarding_dom",
          });
          emitOrbRuntimeEvent("onboarding_route_ready", {
            route: location.pathname,
            targetId: record.target_id,
            resumed_session: true,
          });

          if (!continuation.guidedAt) {
            const guided = await guideToPointerRecord(record, "Continue onboarding with your full name", { signal: controller.signal });
            if (!cancelled && guided) {
              saveOnboardingContinuation({ ...continuation, guidedAt: Date.now() });
              emitOrbRuntimeEvent("onboarding_first_target_guided", { targetId: record.target_id });
            }
          }
          return;
        }
        await awaitAbortable(wait(80), controller.signal).catch(() => undefined);
      }
      if (!cancelled) emitOrbRuntimeEvent("onboarding_route_blocked", { reason: "first_target_not_rendered" });
    };

    void attachLiveTarget();
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [guideToPointerRecord, location.pathname]);

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
        const liveOnboardingRecord = onboardingLiveRecordRef.current;
        const recordsForCurrentRoute = liveOnboardingRecord && routeForUrl(liveOnboardingRecord.page_route) === location.pathname
          ? [...pointerRecordsRef.current, liveOnboardingRecord]
          : pointerRecordsRef.current;
        lidarCacheRef.current.load(recordsForCurrentRoute);
        lidarCacheRef.current.startDriftAudit();
        emitOrbRuntimeEvent("pointer_map_ready", { count: pointerRecordsRef.current.length, route: location.pathname });
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
  }, [activeOrbContext?.canonical_domain, bumpWorldStateSequence, guideToPointerTarget, location.pathname]);

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
      const liveOnboardingRecord = onboardingLiveRecordRef.current;
      lidarCacheRef.current.load(liveOnboardingRecord && routeForUrl(liveOnboardingRecord.page_route) === location.pathname
        ? [...pointerRecordsRef.current, liveOnboardingRecord]
        : pointerRecordsRef.current);
      emitOrbRuntimeEvent("route_spatial_state_ready", { route: location.pathname });
      const continuation = location.pathname === ONBOARDING_ROUTE ? readOnboardingContinuation() : null;
      const pendingOnboardingGuidance = Boolean(
        continuation &&
        continuation.firstTargetId === ONBOARDING_FIRST_TARGET_ID &&
        !continuation.guidedAt &&
        websiteJourneyRef.current?.stage === "ONBOARDING",
      );
      if (!pendingOnboardingGuidance && !guidanceActiveRef.current) {
        void resumeAutonomousPresenceRef.current();
      }
    }, 120);
    return () => window.clearTimeout(rebuild);
  }, [bumpWorldStateSequence, location.pathname]);

  useEffect(() => {
    const journey = websiteJourneyRef.current;
    if (!journeyReadyRef.current || !journey) return;
    // Route arrival is observable evidence; it is not evidence of a scan running.
    if (location.pathname === "/preflight" && journey.stage === "LANDING_TOUR" && !journey.interaction.activeDestinationRoute) {
      try {
        saveWebsiteJourney({ ...journey, stage: "PREFLIGHT", currentChapterId: null, currentStopId: null,
          currentStopCoveredConceptIds: [],
          preflightStatus: journey.preflightStatus === 'DEFERRED' ? 'NOT_STARTED' : journey.preflightStatus,
          interruptionState: { isInterrupted: false, interruptedAtChapterId: null, interruptedAtStopId: null } });
      } catch (error) { setTourNotice((error as Error).message); }
      return;
    }
  }, [location.pathname, saveWebsiteJourney]);

  useEffect(() => {
    const pending = pendingDirectRouteGuidanceRef.current;
    if (!pending || pending.route !== location.pathname) return;
    let cancelled = false;
    const arriveAndPresent = async () => {
      // Wait for the route's new pointer registry and LiDAR geometry. Never
      // carry a coordinate from the source page into a destination page.
      const recordsReady = await waitForPointerRecords();
      if (cancelled) return;
      const target = recordsReady ? findPointerRecordById(pending.pointerTargetId) : null;
      if (!target) {
        pendingDirectRouteGuidanceRef.current = null;
        emitOrbRuntimeEvent("visitor_route_navigation_target_unavailable", {
          route: pending.route,
          pointerTargetId: pending.pointerTargetId,
        });
        setStatusTitle("Page opened");
        setStatusLine(`${pending.label} is open, but its live pointer target is not ready yet.`);
        showStatus(5200);
        return;
      }
      const guided = await guideToPointerRecord(target, `Visitor requested ${pending.label}`);
      if (cancelled) return;
      pendingDirectRouteGuidanceRef.current = null;
      emitOrbRuntimeEvent(guided ? "visitor_route_navigation_presented" : "visitor_route_navigation_target_unavailable", {
        route: pending.route,
        pointerTargetId: pending.pointerTargetId,
      });
      if (!guided) {
        setStatusTitle("Page opened");
        setStatusLine(`${pending.label} is open, but I could not verify its live target to point safely.`);
        showStatus(5200);
      }
    };
    const timer = window.setTimeout(() => void arriveAndPresent(), 700);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [findPointerRecordById, guideToPointerRecord, location.pathname, showStatus, waitForPointerRecords]);

  useEffect(() => {
    const journey = websiteJourneyRef.current;
    const destination = journey?.interaction.activeDestinationRoute;
    if (!journey || !destination || destination !== location.pathname || routeArrivalInFlightRef.current === destination) return;
    routeArrivalInFlightRef.current = destination;
    const controller = new AbortController();
    const arrivalObjective = "Continue the governed visitor conversation on this selected page. Explain how this page answers the visitor's stated direction, without claiming completion or choosing a further destination.";
    void api.websiteOrbText("Continue from the visitor's selected direction on the current page.", true, controller.signal, {
      project_id: activeOrbContext?.project_id,
      target_url: contextTargetUrl(),
      experience: {
        phase: "understanding",
        objective: arrivalObjective,
        verification_state: "verified",
        demonstrated_capabilities: ["governed cross-page continuity", "current-page explanation"],
      },
    }).then(async (result) => {
      if (controller.signal.aborted) return;
      emitOrbRuntimeEvent("tour_engagement_destination_arrived", {
        route: destination,
        sourceLane: result.source_lane || result.llm_source,
        llmSource: result.llm_source,
      });
      void api.websiteOrbAgency('observe', { source: 'LIVE_BEHAVIOR', outcome: 'route_arrived', route: destination }, contextTargetUrl());
      const played = await speakWithGeneratedAudio(result.spoken_output, result.tts_audio_url, result.tts_provider);
      if (!played || controller.signal.aborted) return;
      const current = websiteJourneyRef.current;
      if (current?.interaction.activeDestinationRoute === destination) {
        saveWebsiteJourney({
          ...current,
          interaction: {
            ...current.interaction,
            activeDestinationRoute: null,
            recentWeaverStatements: [...current.interaction.recentWeaverStatements, result.spoken_output].slice(-4),
          },
        });
        await getAgencyRuntime().turn(controller.signal);
      }
    }).catch(() => {
      if (!controller.signal.aborted) setTourNotice("Your selected page is open. My conversational response is temporarily unavailable, and your place is saved.");
    }).finally(() => {
      if (routeArrivalInFlightRef.current === destination) routeArrivalInFlightRef.current = null;
    });
    return () => controller.abort();
  }, [activeOrbContext?.project_id, contextTargetUrl, getAgencyRuntime, location.pathname, saveWebsiteJourney, speakWithGeneratedAudio]);

  useEffect(() => () => {
    landingTourAbortControllerRef.current?.abort();
  }, [location.pathname]);

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

    const start = isPublicLandingExperience() ? splashAlignedPosition() : nextDestination();
    const ambientStartupReleaseAt = Date.now() + 12_000;

    positionRef.current = start;
    move.set(start);

    const run = async () => {
      emitDevelopmentStartupTrace("orb_mounted");
      void runStartupVoiceSequenceRef.current();

      // This wrapper contains the entire orb. It must never animate opacity
      // or scale; the center eye alone represents speech.
      glow.set({ opacity: 1, scale: 1 });

      await wait(AMBIENT_INITIAL_DWELL_MS);

      while (activeRef.current) {
        // A warming or degraded model must never turn Weaver into a static
        // obstruction. Preserve the opening composition briefly, then let
        // LiDAR keep the host out of the visitor's reading path.
        if (startupUnresolved() && Date.now() < ambientStartupReleaseAt) {
          await wait(160);
          continue;
        }
        const inactiveForMs = Date.now() - lastActivityAtRef.current;
        const shouldEnterRest =
          inactiveForMs >= REST_AFTER_INACTIVITY_MS &&
          !speechPlaybackRef.current &&
          !recorderRef.current &&
          !speechRecognitionRef.current &&
          !voiceRequestInFlightRef.current &&
          !guidanceActiveRef.current &&
          !controlMotionActiveRef.current;

        if (shouldEnterRest) {
          if (!restModeRef.current) {
            restModeRef.current = true;
            setIsResting(true);
            motionInterruptionSequenceRef.current += 1;
            move.stop();
            emitOrbRuntimeEvent("dormant_started", { inactivityMs: inactiveForMs });
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
        const travelDistance = Math.hypot(destination.x - positionRef.current.x, destination.y - positionRef.current.y);
        const authorization = authorizeMotion(destination, "Ambient");
        if (!authorization) {
          await wait(160);
          continue;
        }
        assertMovementAuthorization(authorization);
        await travelOrbAlongCurve(destination, travelDistance > 520 ? "swirl" : "glide");

        if (!activeRef.current) break;
        if (movementSequence !== motionInterruptionSequenceRef.current) continue;

        positionRef.current = destination;

        void playLocalPresence();

        if (!activeRef.current) break;

        await wait(AMBIENT_SETTLE_MIN_MS + Math.round(Math.random() * AMBIENT_SETTLE_VARIANCE_MS));
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
    authorizeMotion,
    clampPosition,
    glow,
    splashAlignedPosition,
    move,
    travelOrbAlongCurve,
    nextDestination,
    playLocalPresence,
    presence,
    size,
  ]);

  useEffect(() => {
    const monitor = window.setInterval(() => {
      const shouldRest =
        Date.now() - lastActivityAtRef.current >= REST_AFTER_INACTIVITY_MS &&
        !speechPlaybackRef.current && !recorderRef.current && !speechRecognitionRef.current && !guidanceActiveRef.current &&
        !controlMotionActiveRef.current && !voiceRequestInFlightRef.current &&
        !restModeRef.current && !restTransitionActiveRef.current;
      if (!shouldRest) return;
      restTransitionActiveRef.current = true;
      restModeRef.current = true;
      setIsResting(true);
      motionInterruptionSequenceRef.current += 1;
      autonomousResumeActiveRef.current = false;
      move.stop();
      emitOrbRuntimeEvent("dormant_started", { inactivityMs: Date.now() - lastActivityAtRef.current });
      restTransitionActiveRef.current = false;
    }, 240);
    return () => window.clearInterval(monitor);
  }, [move]);

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
      if (captionFrameRef.current) window.cancelAnimationFrame(captionFrameRef.current);
      if (captionCollapseTimerRef.current) window.clearTimeout(captionCollapseTimerRef.current);

      if (recorderRef.current && recorderRef.current.state !== "inactive") {
        recordingCancelledRef.current = true;
        recorderRef.current.stop();
      }

      recordingStreamRef.current?.getTracks().forEach((track) => track.stop());
    };
    // Intentionally unmount-only so voice requests survive state changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
      ref={orbElementRef}
      animate={move}
      onPointerDown={handleOrbPointerDown}
      onPointerMove={handleOrbPointerMove}
      onPointerUp={handleOrbPointerUp}
      onPointerCancel={handleOrbPointerUp}
      className={`ow-v2-orb-position ${pointerBloom ? "is-pointing" : ""} ${greetingActive ? "is-greeting" : ""} ${morbPointer ? "has-deployed-morb" : ""} ${className}`}
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
        <motion.div animate={presence} style={{ transformOrigin: "center" }}>
          <motion.div animate={glow}>
            <motion.div
              animate={orbSpin}
              style={{ width: size, height: size, transformOrigin: "center", perspective: 900 }}
            >
              <Orb
                size={size}
                state={voiceState}
                speechAmplitude={speechAmplitude}
                eyeDirection={orbEyeDirection}
                onClick={handleOrbClick}
              />
            </motion.div>
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
      {speechCaption.fullText && (speechCaption.phase !== "speaking" || speechCaption.revealedText) && (
        <aside
          className="ow-v2-orb-speech"
          data-orb-caption-state={speechCaption.phase}
          aria-live={speechCaption.phase === "speaking" ? "polite" : undefined}
          aria-label="Weaver speech"
        >
          <span>{speechCaption.revealedText || speechCaption.fullText}</span>
        </aside>
      )}
    </motion.div>
    </>
  );
};

export default AutonomousOrb;
