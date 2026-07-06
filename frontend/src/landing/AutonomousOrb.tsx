import React, { useCallback, useEffect, useRef, useState } from "react";
import { motion, useAnimationControls } from "framer-motion";
import { Orb } from "./Orb";
import { api } from "../services/api";

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
  const lastAvoidRef = useRef(0);
  const voiceRequestInFlightRef = useRef(false);
  const activeVoiceAbortControllerRef = useRef<AbortController | null>(null);
  const voiceTurnIdRef = useRef(0);
  const recordingMonitorTimerRef = useRef<number | null>(null);
  const recordingStartedAtRef = useRef(0);
  const speechDetectedRef = useRef(false);
  const silenceStartedAtRef = useRef<number | null>(null);

  const [pulse, setPulse] = useState<PulseState>(null);
  const [voiceState, setVoiceState] = useState<OrbVoiceState>("idle");
  const [statusVisible, setStatusVisible] = useState(false);
  const [statusTitle, setStatusTitle] = useState("ORB online");
  const [statusLine, setStatusLine] = useState("Tap the ORB to speak.");

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

  const speak = useCallback(async (text: string, audioUrl?: string | null, provider?: string | null) => {
    showStatus();
    setStatusLine(text);
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
      const audio = speechAudioRef.current || new Audio();
      audio.pause();
      audio.muted = false;
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
  }, [freezeOrbInPlace, showStatus]);

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
      const result = await api.websiteOrbVoice(audio, controller.signal);
      setStatusTitle("Voice response");
      setStatusLine(result.spoken_output);
      if (result.tts_error && !result.tts_audio_url) {
        setStatusTitle("Voice unavailable");
        setStatusLine(VOICE_UNAVAILABLE_MESSAGE);
      }
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
  }, [freezeOrbInPlace, logVoice, playLatencyFiller, showStatus, speakRecovery, speakWithGeneratedAudio]);

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

  const handleOrbClick = useCallback(() => {
    if (voiceState === "speaking") {
      interruptOrbSpeech();
      return;
    }

    if (recorderRef.current) {
      stopOrbRecording(true);
      return;
    }

    void startOrbRecording();
  }, [interruptOrbSpeech, startOrbRecording, stopOrbRecording, voiceState]);

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
      rings: 5,
      color: "rgba(91,200,230,",
      maxScale: 9.4,
      duration: 2.05,
    };
  };

  const visual = ringStyle();

  return (
    <>
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
            <Orb
              size={size}
              state={voiceState}
              onClick={handleOrbClick}
            />
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
