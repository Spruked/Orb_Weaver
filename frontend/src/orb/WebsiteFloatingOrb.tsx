import React, { useCallback, useEffect, useRef, useState } from 'react';
import { api, type WebsiteOrbPointerRecord } from '../services/api';
import { LidarCoordinateCache } from './LidarCoordinateCache';
import { validateOrbPointerTarget } from './targetValidation';
import { useOrbTelemetry } from './useOrbTelemetry';
import type { TelemetryFrame, ViewportCoordinate } from './types';
import './WebsiteFloatingOrb.css';

type OrbMode = 'idle' | 'avoiding' | 'assisting' | 'learning';
type OrbPoint = { x: number; y: number };
type BloomRect = { left: number; top: number; width: number; height: number };
type MicroOrbState = {
  left: number;
  top: number;
  visible: boolean;
  dissolving: boolean;
};

const LATENCY_FILLER_PATHS = [
  '/orb/voice/latency-fillers/ack.wav',
  '/orb/voice/latency-fillers/thinking.wav',
  '/orb/voice/latency-fillers/working.wav',
];
const VOICE_UNAVAILABLE_MESSAGE = 'Voice unavailable';
const lidar = LidarCoordinateCache.getInstance();
const MORB_TRAVEL_MS = 520;
const MORB_DISSOLVE_MS = 620;

const normalizeIntentText = (value: string): string =>
  (value || '').replace(/\s+/g, ' ').trim().toLowerCase();

const routeForUrl = (value?: string | null): string => {
  if (!value) return '/';
  try {
    return new URL(value, window.location.origin).pathname.replace(/\/+$/, '') || '/';
  } catch {
    return '/';
  }
};

const recordTextCandidates = (record: WebsiteOrbPointerRecord): string[] => {
  const meaning = (record.meaning || '').replace(/^[^:]+:\s*/, '');
  return [
    meaning,
    ...(record.direct_aliases || []),
    ...(record.intent_aliases || []),
    ...(record.topic_aliases || []),
  ]
    .map(normalizeIntentText)
    .filter((value) => value.length >= 2);
};

const WebsiteFloatingOrb: React.FC = () => {
  const [position, setPosition] = useState({ x: window.innerWidth - 180, y: 190 });
  const [targetPos, setTargetPos] = useState({ x: window.innerWidth - 180, y: 190 });
  const [mode, setMode] = useState<OrbMode>('idle');
  const [isMoving, setIsMoving] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [statusLine, setStatusLine] = useState('Greeting visitor');
  const [spokenOutput, setSpokenOutput] = useState('Weaver is present.');
  const [dockStatus, setDockStatus] = useState<'searching' | 'linked' | 'offline'>('searching');
  const [mood, setMood] = useState(0.86);
  const [pointingTargetId, setPointingTargetId] = useState<string | null>(null);
  const [bloomRect, setBloomRect] = useState<BloomRect | null>(null);
  const [microOrb, setMicroOrb] = useState<MicroOrbState | null>(null);

  const positionRef = useRef(position);
  const targetRef = useRef(targetPos);
  const modeRef = useRef<OrbMode>(mode);
  const pointerRecordsRef = useRef<WebsiteOrbPointerRecord[]>([]);
  const dockRef = useRef<WebSocket | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<BlobPart[]>([]);
  const speechAudioRef = useRef<HTMLAudioElement | null>(null);
  const latencyAudioRef = useRef<HTMLAudioElement | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const speechSourceRef = useRef<AudioBufferSourceNode | null>(null);
  const bubbleTimerRef = useRef<number | null>(null);
  const bloomTimerRef = useRef<number | null>(null);
  const microOrbTravelRef = useRef<number | null>(null);
  const microOrbDissolveRef = useRef<number | null>(null);
  const microOrbCleanupRef = useRef<number | null>(null);
  const lastActivityRef = useRef(Date.now());

  useEffect(() => {
    positionRef.current = position;
  }, [position]);

  useEffect(() => {
    targetRef.current = targetPos;
  }, [targetPos]);

  useEffect(() => {
    modeRef.current = mode;
  }, [mode]);

  const orbColor = mood >= 0.8 ? 'rgba(45, 212, 255, 0.9)' : mood >= 0.6 ? 'rgba(250, 204, 21, 0.9)' : 'rgba(248, 113, 113, 0.9)';

  const pointNearRect = useCallback((rect: DOMRect): OrbPoint => {
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;
    const side = centerX < window.innerWidth / 2 ? 1 : -1;
    return {
      x: Math.max(80, Math.min(window.innerWidth - 80, centerX + side * 132)),
      y: Math.max(100, Math.min(window.innerHeight - 100, centerY)),
    };
  }, []);

  const clearMicroOrbSequence = useCallback(() => {
    if (microOrbTravelRef.current) {
      window.cancelAnimationFrame(microOrbTravelRef.current);
      microOrbTravelRef.current = null;
    }
    if (microOrbDissolveRef.current) {
      window.clearTimeout(microOrbDissolveRef.current);
      microOrbDissolveRef.current = null;
    }
    if (microOrbCleanupRef.current) {
      window.clearTimeout(microOrbCleanupRef.current);
      microOrbCleanupRef.current = null;
    }
    setMicroOrb(null);
  }, []);

  const deployMicroOrb = useCallback((viewportCoord: ViewportCoordinate) => {
    clearMicroOrbSequence();

    const originLeft = positionRef.current.x - 11;
    const originTop = positionRef.current.y - 11;
    const targetLeft = viewportCoord.left + viewportCoord.width / 2 - 11;
    const targetTop = viewportCoord.top + viewportCoord.height / 2 - 11;

    setMicroOrb({
      left: originLeft,
      top: originTop,
      visible: false,
      dissolving: false,
    });

    microOrbTravelRef.current = window.requestAnimationFrame(() => {
      setMicroOrb({
        left: targetLeft,
        top: targetTop,
        visible: true,
        dissolving: false,
      });
      microOrbTravelRef.current = null;
    });

    microOrbDissolveRef.current = window.setTimeout(() => {
      setMicroOrb((current) => current ? { ...current, dissolving: true } : null);
      microOrbDissolveRef.current = null;
    }, MORB_TRAVEL_MS + 120);

    microOrbCleanupRef.current = window.setTimeout(() => {
      setMicroOrb(null);
      microOrbCleanupRef.current = null;
    }, MORB_TRAVEL_MS + MORB_DISSOLVE_MS);
  }, [clearMicroOrbSequence]);

  const applyTargetLock = useCallback((viewportCoord: ViewportCoordinate, label: string, targetId: string) => {
    const rect = {
      left: viewportCoord.left,
      top: viewportCoord.top,
      width: viewportCoord.width,
      height: viewportCoord.height,
      right: viewportCoord.left + viewportCoord.width,
      bottom: viewportCoord.top + viewportCoord.height,
      x: viewportCoord.left,
      y: viewportCoord.top,
      toJSON: () => '',
    } as DOMRect;

    const nextTarget = pointNearRect(rect);
    setTargetPos(nextTarget);
    setMode('assisting');
    setIsMoving(true);
    setPointingTargetId(targetId);
    setStatusLine(`Pointing: ${label.slice(0, 54)}`);
    deployMicroOrb(viewportCoord);
    setBloomRect({
      left: Math.max(0, viewportCoord.left - 8),
      top: Math.max(0, viewportCoord.top - 8),
      width: viewportCoord.width + 16,
      height: viewportCoord.height + 16,
    });

    if (bloomTimerRef.current) {
      window.clearTimeout(bloomTimerRef.current);
    }
    bloomTimerRef.current = window.setTimeout(() => {
      setBloomRect(null);
      setPointingTargetId(null);
    }, 1800);
  }, [deployMicroOrb, pointNearRect]);

  const telemetryUrl = 'ws://localhost:8000/ws/orb-pointer';
  const handleTelemetryTargetLock = useCallback((viewportCoord: ViewportCoordinate, frame: TelemetryFrame) => {
    applyTargetLock(viewportCoord, frame.semantic_intent || frame.target_id, frame.target_id);
  }, [applyTargetLock]);

  const handleTelemetryStatusChange = useCallback((status: string) => {
    if (status === 'connected') {
      setStatusLine((current) => current === 'Greeting visitor' ? 'Telemetry linked' : current);
    }
  }, []);

  const { reportDrift } = useOrbTelemetry({
    wsUrl: telemetryUrl,
    onTargetLock: handleTelemetryTargetLock,
    onStatusChange: handleTelemetryStatusChange,
  });

  const findPointerRecordForIntent = useCallback((intentText: string): WebsiteOrbPointerRecord | null => {
    const query = normalizeIntentText(intentText);
    if (!query) return null;

    const currentRoute = routeForUrl(window.location.href);
    let best: { record: WebsiteOrbPointerRecord; score: number } | null = null;

    for (const record of pointerRecordsRef.current) {
      const recordRoute = routeForUrl(record.page_route);
      if (recordRoute !== currentRoute) continue;

      let score = 0;
      for (const candidate of recordTextCandidates(record)) {
        if (candidate.length < 2) continue;
        if (query === candidate) score = Math.max(score, 1);
        else if (query.includes(candidate)) score = Math.max(score, Math.min(0.92, candidate.length / Math.max(query.length, 1)));
        else if (candidate.includes(query) && query.length >= 4) score = Math.max(score, Math.min(0.84, query.length / candidate.length));
      }

      const confidence = typeof record.confidence === 'number' ? record.confidence : 0.7;
      score *= Math.max(0.55, Math.min(1, confidence));
      if (score >= 0.42 && (!best || score > best.score)) {
        best = { record, score };
      }
    }

    return best?.record || null;
  }, []);

  const guideToPointerTarget = useCallback(async (intentText: string) => {
    const record = findPointerRecordForIntent(intentText);
    if (!record) return;

    const firstPass = validateOrbPointerTarget(record, { logger: console });
    if (!firstPass.ok) return;

    const viewportCoord = await lidar.prepareForMovement(record.target_id);
    if (!viewportCoord) {
      reportDrift(record.target_id);
      return;
    }

    applyTargetLock(
      viewportCoord,
      (record.meaning || record.target_type || 'target').replace(/^[^:]+:\s*/, ''),
      record.target_id,
    );
  }, [applyTargetLock, findPointerRecordForIntent, reportDrift]);

  const playLatencyFiller = useCallback(() => {
    const src = LATENCY_FILLER_PATHS[Math.floor(Math.random() * LATENCY_FILLER_PATHS.length)];
    if (latencyAudioRef.current) {
      latencyAudioRef.current.pause();
      latencyAudioRef.current = null;
    }

    const audio = new Audio(src);
    audio.volume = 0.72;
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

  const unlockAudio = useCallback(() => {
    const AudioContextCtor = (window as any).AudioContext || (window as any).webkitAudioContext;
    if (AudioContextCtor && !audioContextRef.current) {
      audioContextRef.current = new AudioContextCtor();
    }
    void audioContextRef.current?.resume?.();

    if (!speechAudioRef.current) {
      const audio = new Audio('data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAESsAACJWAAACABAAZGF0YQAAAAA=');
      audio.muted = true;
      speechAudioRef.current = audio;
      void audio.play().catch(() => undefined);
    }
  }, []);

  const playDecodedSpeech = useCallback(async (audioUrl: string) => {
    const AudioContextCtor = (window as any).AudioContext || (window as any).webkitAudioContext;
    if (!AudioContextCtor) {
      throw new Error('AudioContext unavailable');
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

    const response = await fetch(api.orbMediaUrl(audioUrl), { cache: 'force-cache' });
    if (!response.ok) {
      throw new Error('Speech audio unavailable');
    }

    const buffer = await context.decodeAudioData(await response.arrayBuffer());
    const source = context.createBufferSource();
    const gain = context.createGain();
    source.buffer = buffer;
    gain.gain.value = 1;
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

  const speakOutput = useCallback(async (text: string, audioUrl?: string | null, provider?: string | null) => {
    setSpokenOutput(text);
    setIsSpeaking(true);
    setMode('assisting');
    setStatusLine(text);

    if (bubbleTimerRef.current) {
      window.clearTimeout(bubbleTimerRef.current);
    }
    bubbleTimerRef.current = window.setTimeout(() => {
      setIsSpeaking(false);
      setMode('idle');
    }, 4200);

    if (speechAudioRef.current) {
      speechAudioRef.current.pause();
    }
    if (latencyAudioRef.current) {
      latencyAudioRef.current.pause();
      latencyAudioRef.current = null;
    }

    if (!audioUrl) {
      setStatusLine(VOICE_UNAVAILABLE_MESSAGE);
      return;
    }

    try {
      const audio = speechAudioRef.current || new Audio();
      audio.pause();
      audio.muted = false;
      audio.src = api.orbMediaUrl(audioUrl);
      speechAudioRef.current = audio;
      audio.onended = () => {
        if (speechAudioRef.current === audio) {
          speechAudioRef.current = null;
        }
        setIsSpeaking(false);
      };
      audio.onerror = () => {
        if (speechAudioRef.current === audio) {
          speechAudioRef.current = null;
        }
        setStatusLine(VOICE_UNAVAILABLE_MESSAGE);
        setIsSpeaking(false);
      };
      await audio.play();
    } catch {
      try {
        await playDecodedSpeech(audioUrl);
        setIsSpeaking(false);
      } catch {
        setStatusLine(VOICE_UNAVAILABLE_MESSAGE);
        setIsSpeaking(false);
      }
    }
  }, [playDecodedSpeech]);

  const speakRecovery = useCallback(async (text: string) => {
    try {
      playLatencyFiller();
      const result = await api.websiteOrbTts(text);
      await speakOutput(text, result.tts_audio_url, result.tts_provider);
    } catch {
      setSpokenOutput(text);
      setStatusLine(VOICE_UNAVAILABLE_MESSAGE);
      setIsSpeaking(false);
      setMode('idle');
    }
  }, [playLatencyFiller, speakOutput]);

  const stopVoiceInput = useCallback(() => {
    if (recorderRef.current && recorderRef.current.state !== 'inactive') {
      recorderRef.current.stop();
    }
  }, []);

  const startVoiceInput = useCallback(async () => {
    lastActivityRef.current = Date.now();
    unlockAudio();

    if (isListening) {
      stopVoiceInput();
      return;
    }

    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
      setStatusLine('Mic unavailable');
      void speakRecovery('Microphone recording is not available in this browser.');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];
      const recorderOptions = MediaRecorder.isTypeSupported('audio/webm') ? { mimeType: 'audio/webm' } : undefined;
      const recorder = new MediaRecorder(stream, recorderOptions);
      recorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      recorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        setIsListening(false);
        setStatusLine('Thinking');
        setMode('assisting');

        const audio = new Blob(audioChunksRef.current, { type: recorder.mimeType || 'audio/webm' });
        audioChunksRef.current = [];

        try {
          const result = await api.websiteOrbVoice(audio, undefined, {
            target_url: window.location.href,
          });
          setStatusLine(result.llm_source === 'local-llm' ? 'ORB cognition + LLM' : 'ORB cognition');
          const glowIntensity = result.cognitive_pulse?.glow_intensity;
          if (typeof glowIntensity === 'number') {
            setMood(Math.max(0.1, Math.min(1, glowIntensity)));
          }
          if (dockRef.current?.readyState === WebSocket.OPEN) {
            dockRef.current.send(JSON.stringify({
              action: 'voice_input',
              type: 'website_orb_voice',
              transcript: result.transcript,
              cognitive_pulse: result.cognitive_pulse,
              timestamp: Date.now(),
            }));
          }
          if (result.tts_error && !result.tts_audio_url) {
            setStatusLine(VOICE_UNAVAILABLE_MESSAGE);
          }
          void guideToPointerTarget(`${result.transcript} ${result.spoken_output}`);
          await speakOutput(result.spoken_output, result.tts_audio_url, result.tts_provider);
        } catch (error) {
          setStatusLine('Voice pipeline failed');
          void speakRecovery(error instanceof Error ? error.message : 'The ORB voice pipeline could not complete.');
        }
      };

      setIsListening(true);
      setStatusLine('Listening');
      setMode('learning');
      setSpokenOutput('Listening...');
      recorder.start();
      window.setTimeout(() => {
        if (recorder.state !== 'inactive') recorder.stop();
      }, 6500);
    } catch (error) {
      setIsListening(false);
      setStatusLine('Mic permission needed');
      void speakRecovery(error instanceof Error ? error.message : 'Microphone permission is needed for voice input.');
    }
  }, [guideToPointerTarget, isListening, speakOutput, speakRecovery, stopVoiceInput, unlockAudio]);

  useEffect(() => {
    const controller = new AbortController();
    api.websiteOrbPointerMap(window.location.hostname, controller.signal)
      .then((pointerMap) => {
        pointerRecordsRef.current = Array.isArray(pointerMap.records) ? pointerMap.records : [];
        if (pointerRecordsRef.current.length > 0) {
          lidar.load(pointerRecordsRef.current);
          setStatusLine('LiDAR grid locked. Telemetry ready.');
        }
      })
      .catch(() => {
        pointerRecordsRef.current = [];
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const notifyRouteChange = () => {
      lidar.rebuild();
      setPointingTargetId(null);
      setBloomRect(null);
      clearMicroOrbSequence();
    };

    const originalPushState = window.history.pushState;
    const originalReplaceState = window.history.replaceState;

    window.history.pushState = function pushState(...args) {
      const result = originalPushState.apply(this, args);
      window.dispatchEvent(new Event('orb-routechange'));
      return result;
    };
    window.history.replaceState = function replaceState(...args) {
      const result = originalReplaceState.apply(this, args);
      window.dispatchEvent(new Event('orb-routechange'));
      return result;
    };

    window.addEventListener('popstate', notifyRouteChange);
    window.addEventListener('hashchange', notifyRouteChange);
    window.addEventListener('orb-routechange', notifyRouteChange);

    return () => {
      window.history.pushState = originalPushState;
      window.history.replaceState = originalReplaceState;
      window.removeEventListener('popstate', notifyRouteChange);
      window.removeEventListener('hashchange', notifyRouteChange);
      window.removeEventListener('orb-routechange', notifyRouteChange);
    };
  }, [clearMicroOrbSequence]);

  useEffect(() => {
    let reconnectTimer = 0;
    let closedByComponent = false;

    const connectDockstation = () => {
      try {
        const socket = new WebSocket('ws://localhost:8000/ws/orb_assistant');
        dockRef.current = socket;

        socket.onopen = () => {
          setDockStatus('linked');
          setStatusLine('Dockstation linked');
          socket.send(JSON.stringify({
            type: 'ORB_HANDSHAKE',
            orb_id: 'ORB_WEAVER_PUBLIC_WEBSITE_ORB_V1',
            role: 'website_orb',
            capabilities: ['presence', 'mediation', 'ui', 'public_preflight', 'marketplace_guidance', 'dockstation_handoff'],
            source: 'orb_weaver_website',
          }));
        };

        socket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.type === 'cognitive_pulse' || data.type === 'speech_pulse') {
              const pulse = data.data || data;
              if (typeof pulse.glow_intensity === 'number') {
                setMood(Math.max(0.1, Math.min(1, pulse.glow_intensity)));
              }
              if (pulse.cognitive_mode) {
                setStatusLine(`Dock mode: ${pulse.cognitive_mode}`);
              }
              if (typeof data.transcription === 'string') {
                void speakRecovery(data.transcription);
              }
              if (typeof pulse.spoken_output === 'string') {
                void speakRecovery(pulse.spoken_output);
              }
            }
            if (data.type === 'lerp_optimization') {
              setStatusLine('Dockstation tuned movement');
            }
            if (data.type === 'drift_preference') {
              setStatusLine('Dockstation drift preference');
            }
          } catch {
            // Desktop bridge can emit diagnostics; the website ORB ignores them.
          }
        };

        socket.onclose = () => {
          dockRef.current = null;
          if (closedByComponent) return;
          setDockStatus('offline');
          setStatusLine('Website ORB online');
          reconnectTimer = window.setTimeout(connectDockstation, 5000);
        };

        socket.onerror = () => {
          setDockStatus('offline');
        };
      } catch {
        setDockStatus('offline');
        reconnectTimer = window.setTimeout(connectDockstation, 5000);
      }
    };

    connectDockstation();
    return () => {
      closedByComponent = true;
      window.clearTimeout(reconnectTimer);
      dockRef.current?.close();
      stopVoiceInput();
      if (bubbleTimerRef.current) {
        window.clearTimeout(bubbleTimerRef.current);
      }
      if (bloomTimerRef.current) {
        window.clearTimeout(bloomTimerRef.current);
      }
      if (speechAudioRef.current) {
        speechAudioRef.current.pause();
      }
      if (speechSourceRef.current) {
        try {
          speechSourceRef.current.stop();
        } catch {
          // Source may already have ended.
        }
        speechSourceRef.current = null;
      }
      clearMicroOrbSequence();
    };
  }, [clearMicroOrbSequence, speakRecovery, stopVoiceInput]);

  useEffect(() => {
    const greetingTimer = window.setTimeout(() => {
      setStatusLine(dockStatus === 'linked' ? 'Dockstation linked' : 'Website ORB online');
    }, 2200);
    return () => window.clearTimeout(greetingTimer);
  }, [dockStatus]);

  useEffect(() => {
    const interval = window.setInterval(() => {
      let nextMood = 0.78;
      if (modeRef.current === 'assisting') nextMood += 0.16;
      if (modeRef.current === 'avoiding') nextMood -= 0.08;
      if (Date.now() - lastActivityRef.current > 15000) nextMood += 0.08;
      setMood(Math.max(0.1, Math.min(1, nextMood)));
    }, 1000);
    return () => window.clearInterval(interval);
  }, []);

  useEffect(() => {
    const handleMouseMove = (event: MouseEvent) => {
      lastActivityRef.current = Date.now();
      const current = positionRef.current;
      const dx = event.clientX - current.x;
      const dy = event.clientY - current.y;
      const distance = Math.sqrt(dx * dx + dy * dy);
      const avoidanceDistance = 260;

      if (distance < avoidanceDistance) {
        const angle = Math.atan2(dy, dx);
        const avoidDistance = avoidanceDistance * 1.25;
        const nextTarget = {
          x: Math.max(80, Math.min(window.innerWidth - 80, event.clientX + Math.cos(angle) * avoidDistance)),
          y: Math.max(100, Math.min(window.innerHeight - 100, event.clientY + Math.sin(angle) * avoidDistance)),
        };
        setTargetPos(nextTarget);
        setMode('avoiding');
        if (dockRef.current?.readyState === WebSocket.OPEN) {
          dockRef.current.send(JSON.stringify({
            action: 'learn_movement',
            pattern: {
              from: positionRef.current,
              to: nextTarget,
              cursor_distance: distance,
              velocity: 0.14,
              timestamp: Date.now(),
            },
          }));
        }
        setIsMoving(true);
      }
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  useEffect(() => {
    let frame = 0;
    let rafId = 0;

    const animate = () => {
      const current = positionRef.current;
      let target = targetRef.current;

      if (modeRef.current === 'idle') {
        const time = Date.now() * 0.001;
        target = {
          x: window.innerWidth - 185 + Math.sin(time * 0.5) * 28,
          y: 185 + Math.cos(time * 0.32) * 18,
        };
        targetRef.current = target;
      }

      const factor = modeRef.current === 'avoiding' ? 0.14 : modeRef.current === 'assisting' ? 0.08 : 0.045;
      const next = {
        x: current.x + (target.x - current.x) * factor,
        y: current.y + (target.y - current.y) * factor,
      };
      const distance = Math.sqrt((target.x - next.x) ** 2 + (target.y - next.y) ** 2);

      if (distance < 5 && modeRef.current === 'avoiding') {
        setMode('idle');
        setIsMoving(false);
      } else if (frame % 2 === 0) {
        setIsMoving(distance > 2);
      }

      positionRef.current = next;
      setPosition(next);
      frame += 1;
      rafId = requestAnimationFrame(animate);
    };

    rafId = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(rafId);
  }, []);

  return (
    <>
    <div
      className={`ow-website-orb-shell ${mode} ${dockStatus}`}
      style={{
        left: `${position.x - 70}px`,
        top: `${position.y - 70}px`,
      }}
    >
      <button
        type="button"
        className={`ow-website-orb-core ${isMoving ? 'moving' : ''} ${isSpeaking ? 'speaking' : ''} ${isListening ? 'listening' : ''} ${pointingTargetId ? 'pointing' : ''}`}
        style={{
          background: `radial-gradient(circle at 32% 28%, rgba(255,255,255,0.92), ${orbColor} 24%, #111827 72%)`,
          boxShadow: `0 0 34px ${orbColor}, inset 0 0 22px rgba(255,255,255,0.24)`,
        }}
        onClick={startVoiceInput}
        aria-label="Speak to Weaver ORB"
      >
        <span className="ow-website-orb-aura" style={{ background: `radial-gradient(circle, ${orbColor}, transparent 68%)` }} />
        <span className="ow-website-orb-ring" />
        <span className="ow-website-orb-ring second" />
        <span className="ow-website-orb-shine" />
      </button>

      <div className="ow-website-orb-label">
        <strong>Weaver</strong>
        <span>{statusLine}</span>
      </div>

      <div className={`ow-website-orb-speech ${isSpeaking || isListening ? 'visible' : ''}`} aria-live="polite">
        {spokenOutput}
      </div>
    </div>
    {bloomRect && (
      <>
        <div
          className="ow-website-orb-target-bloom"
          style={{
            left: `${bloomRect.left}px`,
            top: `${bloomRect.top}px`,
            width: `${bloomRect.width}px`,
            height: `${bloomRect.height}px`,
          }}
        />
      </>
    )}
    {microOrb && (
      <div
        className={`ow-website-orb-micro-pointer ${microOrb.visible ? 'visible' : ''} ${microOrb.dissolving ? 'dissolving' : ''}`}
        style={{
          left: `${microOrb.left}px`,
          top: `${microOrb.top}px`,
        }}
        aria-hidden="true"
      />
    )}
    </>
  );
};

export default WebsiteFloatingOrb;
