import React, { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../services/api';
import './WebsiteFloatingOrb.css';

type OrbMode = 'idle' | 'avoiding' | 'assisting' | 'learning';

const LATENCY_FILLER_PATHS = [
  '/orb/voice/latency-fillers/ack.wav',
  '/orb/voice/latency-fillers/thinking.wav',
  '/orb/voice/latency-fillers/working.wav',
];
const VOICE_UNAVAILABLE_MESSAGE = 'Voice unavailable';

const WebsiteFloatingOrb: React.FC = () => {
  const [position, setPosition] = useState({ x: window.innerWidth - 180, y: 190 });
  const [targetPos, setTargetPos] = useState({ x: window.innerWidth - 180, y: 190 });
  const [mode, setMode] = useState<OrbMode>('idle');
  const [isMoving, setIsMoving] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [statusLine, setStatusLine] = useState('Greeting visitor');
  const [spokenOutput, setSpokenOutput] = useState('Caleon is present.');
  const [dockStatus, setDockStatus] = useState<'searching' | 'linked' | 'offline'>('searching');
  const [mood, setMood] = useState(0.86);

  const positionRef = useRef(position);
  const targetRef = useRef(targetPos);
  const modeRef = useRef<OrbMode>(mode);
  const dockRef = useRef<WebSocket | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<BlobPart[]>([]);
  const speechAudioRef = useRef<HTMLAudioElement | null>(null);
  const latencyAudioRef = useRef<HTMLAudioElement | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const speechSourceRef = useRef<AudioBufferSourceNode | null>(null);
  const bubbleTimerRef = useRef<number | null>(null);
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
          const result = await api.websiteOrbVoice(audio);
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
  }, [isListening, speakOutput, speakRecovery, stopVoiceInput, unlockAudio]);

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
    };
  }, [speakRecovery, stopVoiceInput]);

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
    <div
      className={`ow-website-orb-shell ${mode} ${dockStatus}`}
      style={{
        left: `${position.x - 70}px`,
        top: `${position.y - 70}px`,
      }}
    >
      <button
        type="button"
        className={`ow-website-orb-core ${isMoving ? 'moving' : ''} ${isSpeaking ? 'speaking' : ''} ${isListening ? 'listening' : ''}`}
        style={{
          background: `radial-gradient(circle at 32% 28%, rgba(255,255,255,0.92), ${orbColor} 24%, #111827 72%)`,
          boxShadow: `0 0 34px ${orbColor}, inset 0 0 22px rgba(255,255,255,0.24)`,
        }}
        onClick={startVoiceInput}
        aria-label="Speak to Caleon ORB"
      >
        <span className="ow-website-orb-aura" style={{ background: `radial-gradient(circle, ${orbColor}, transparent 68%)` }} />
        <span className="ow-website-orb-ring" />
        <span className="ow-website-orb-ring second" />
        <span className="ow-website-orb-shine" />
      </button>

      <div className="ow-website-orb-label">
        <strong>Caleon (CALI)</strong>
        <span>{statusLine}</span>
      </div>

      <div className={`ow-website-orb-speech ${isSpeaking || isListening ? 'visible' : ''}`} aria-live="polite">
        {spokenOutput}
      </div>
    </div>
  );
};

export default WebsiteFloatingOrb;
