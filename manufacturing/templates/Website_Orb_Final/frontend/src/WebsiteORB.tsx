import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Orb } from "./OrbVisual";
import { WebsiteOrbApi, type AnswerResponse, type RouteContextResponse } from "./api";
import type { PlotRecord } from "./pointer/pointerPlotTypes";
import { resolveTarget } from "./pointer/pointerResolution";
import "./WebsiteORB.css";

type Props = {
  apiBase?: string;
  size?: number;
};

type Position = {
  x: number;
  y: number;
};

const EDGE = 8;
const CURSOR_SAFE_RADIUS = 180;
const RECORDING_MAX_MS = 14000;
const RECORDING_MIN_MS = 650;
const SILENCE_AFTER_SPEECH_MS = 850;
const SILENCE_SAMPLE_MS = 120;
const SPEECH_RMS_THRESHOLD = 0.025;
const SILENCE_RMS_THRESHOLD = 0.018;

export const WebsiteORB: React.FC<Props> = ({ apiBase = "", size = 164 }) => {
  const api = useMemo(() => new WebsiteOrbApi(apiBase), [apiBase]);
  const orbRef = useRef<HTMLDivElement | null>(null);
  const cursorRef = useRef<Position | null>(null);
  const posRef = useRef<Position>({ x: EDGE, y: EDGE });
  const targetRef = useRef<Position>({ x: EDGE, y: EDGE });
  const routeRef = useRef(window.location.pathname || "/");
  const [position, setPosition] = useState<Position>({ x: EDGE, y: EDGE });
  const [routeContext, setRouteContext] = useState<RouteContextResponse | null>(null);
  const [message, setMessage] = useState("");
  const [answer, setAnswer] = useState("Tap or ask. I know where I am on Orb Weaver.");
  const [state, setState] = useState<"idle" | "listening" | "speaking">("idle");
  const [resolvedTarget, setResolvedTarget] = useState<Element | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const monitorRef = useRef<number>(0);

  const clamp = useCallback(
    (next: Position): Position => ({
      x: Math.max(EDGE, Math.min(next.x, window.innerWidth - size - EDGE)),
      y: Math.max(EDGE, Math.min(next.y, window.innerHeight - size - EDGE)),
    }),
    [size],
  );

  const chooseDestination = useCallback(() => {
    const current = posRef.current;
    let candidate = current;
    for (let i = 0; i < 35; i += 1) {
      const next = clamp({
        x: EDGE + Math.random() * Math.max(1, window.innerWidth - size - EDGE * 2),
        y: EDGE + Math.random() * Math.max(1, window.innerHeight - size - EDGE * 2),
      });
      const cursor = cursorRef.current;
      const cursorDistance = cursor
        ? Math.hypot(next.x + size / 2 - cursor.x, next.y + size / 2 - cursor.y)
        : Number.POSITIVE_INFINITY;
      const travel = Math.hypot(next.x - current.x, next.y - current.y);
      if (cursorDistance > CURSOR_SAFE_RADIUS && travel > Math.min(420, window.innerWidth * 0.3)) {
        candidate = next;
        break;
      }
    }
    targetRef.current = candidate;
  }, [clamp, size]);

  useEffect(() => {
    chooseDestination();
    let frame = 0;
    let lastDestinationAt = performance.now();

    const tick = (now: number) => {
      const cursor = cursorRef.current;
      let target = targetRef.current;
      if (cursor) {
        const distance = Math.hypot(posRef.current.x + size / 2 - cursor.x, posRef.current.y + size / 2 - cursor.y);
        if (distance < CURSOR_SAFE_RADIUS) {
          target = clamp({
            x: posRef.current.x + (posRef.current.x + size / 2 - cursor.x) * 0.9,
            y: posRef.current.y + (posRef.current.y + size / 2 - cursor.y) * 0.9,
          });
          targetRef.current = target;
        }
      }

      if (now - lastDestinationAt > 2200 + Math.random() * 2800) {
        chooseDestination();
        lastDestinationAt = now;
      }

      const current = posRef.current;
      const next = clamp({
        x: current.x + (target.x - current.x) * 0.022,
        y: current.y + (target.y - current.y) * 0.022,
      });
      posRef.current = next;
      setPosition(next);
      frame = requestAnimationFrame(tick);
    };

    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [chooseDestination, clamp, size]);

  useEffect(() => {
    const onPointer = (event: PointerEvent) => {
      cursorRef.current = { x: event.clientX, y: event.clientY };
    };
    window.addEventListener("pointermove", onPointer, { passive: true });
    return () => window.removeEventListener("pointermove", onPointer);
  }, []);

  const refreshRoute = useCallback(async () => {
    const route = window.location.pathname || "/";
    if (route === routeRef.current && routeContext) return;
    routeRef.current = route;
    const context = await api.routeContext(route);
    setRouteContext(context);
  }, [api, routeContext]);

  useEffect(() => {
    void refreshRoute().catch(() => undefined);
    const timer = window.setInterval(() => void refreshRoute().catch(() => undefined), 1200);
    return () => window.clearInterval(timer);
  }, [refreshRoute]);

  const submit = useCallback(async () => {
    const trimmed = message.trim();
    if (!trimmed) return;
    setState("speaking");
    setResolvedTarget(null);
    try {
      const response = await api.answerText(trimmed, routeRef.current);
      setAnswer(response.answer);
      await resolveBestPointer(response);
    } catch {
      setAnswer("I am here, but the Website ORB runtime is unavailable.");
    } finally {
      setMessage("");
      window.setTimeout(() => setState("idle"), 1200);
    }
  }, [api, message]);

  const startVoice = useCallback(async () => {
    if (recorderRef.current?.state === "recording") { recorderRef.current.stop(); return; }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const context = new AudioContext();
      const analyser = context.createAnalyser();
      analyser.fftSize = 1024;
      context.createMediaStreamSource(stream).connect(analyser);
      const types = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4;codecs=mp4a.40.2", "audio/mp4", "audio/ogg;codecs=opus", "audio/ogg"];
      const mimeType = types.find((type) => MediaRecorder.isTypeSupported(type)) || "";
      const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
      recorderRef.current = recorder;
      const chunks: BlobPart[] = [];
      let speechDetected = false;
      let silenceAt: number | null = null;
      const startedAt = Date.now();
      const release = () => {
        window.clearTimeout(monitorRef.current);
        stream.getTracks().forEach((track) => track.stop());
        void context.close().catch(() => undefined);
        recorderRef.current = null;
      };
      const monitor = () => {
        if (recorder.state !== "recording") return;
        const samples = new Uint8Array(analyser.fftSize);
        analyser.getByteTimeDomainData(samples);
        const rms = Math.sqrt(samples.reduce((sum, value) => sum + (((value - 128) / 128) ** 2), 0) / samples.length);
        const now = Date.now();
        if (rms >= SPEECH_RMS_THRESHOLD) { speechDetected = true; silenceAt = null; }
        else if (speechDetected && rms <= SILENCE_RMS_THRESHOLD) {
          silenceAt ??= now;
          if (now - startedAt >= RECORDING_MIN_MS && now - silenceAt >= SILENCE_AFTER_SPEECH_MS) { recorder.stop(); return; }
        } else silenceAt = null;
        if (now - startedAt >= RECORDING_MAX_MS) { recorder.stop(); return; }
        monitorRef.current = window.setTimeout(monitor, SILENCE_SAMPLE_MS);
      };
      recorder.ondataavailable = (event) => { if (event.data.size) chunks.push(event.data); };
      recorder.onstop = async () => {
        const recordedType = recorder.mimeType || "audio/webm";
        release();
        setState("speaking");
        try {
          const extension = recordedType.includes("mp4") ? "m4a" : recordedType.includes("ogg") ? "ogg" : "webm";
          const response = await api.answerVoice(new Blob(chunks, { type: recordedType }), routeRef.current, `website-orb.${extension}`);
          setAnswer(response.spoken_output);
          if (response.tts_audio_url) void new Audio(`${apiBase}${response.tts_audio_url}`).play().catch(() => undefined);
          await resolveBestPointer(response);
        } catch { setAnswer("I could not complete that voice request."); }
        finally { window.setTimeout(() => setState("idle"), 1200); }
      };
      recorder.start();
      setState("listening");
      setAnswer("I am listening.");
      monitor();
    } catch { setAnswer("Microphone permission was not granted."); }
  }, [api, apiBase]);

  const resolveBestPointer = async (response: AnswerResponse) => {
    const record = response.pointer_targets[0] as unknown as PlotRecord | undefined;
    if (!record) return;
    const result = await resolveTarget(record);
    if (result.status === "resolved" && result.target?.element && result.target.onScreen) {
      setResolvedTarget(result.target.element);
      result.target.element.scrollIntoView({ behavior: "smooth", block: "center", inline: "center" });
      window.setTimeout(() => setResolvedTarget(null), 1800);
    }
  };

  useEffect(() => {
    if (!resolvedTarget) return;
    resolvedTarget.classList.add("website-orb-pointer-ping");
    return () => resolvedTarget.classList.remove("website-orb-pointer-ping");
  }, [resolvedTarget]);

  return (
    <div
      ref={orbRef}
      className="website-orb-root"
      style={{ transform: `translate3d(${position.x}px, ${position.y}px, 0)` }}
    >
      <Orb size={size} state={state} onClick={() => setState((current) => (current === "listening" ? "idle" : "listening"))} />
      <form
        className="website-orb-panel"
        onSubmit={(event) => {
          event.preventDefault();
          void submit();
        }}
      >
        <div className="website-orb-answer">{answer}</div>
        <div className="website-orb-route">{routeContext?.matched_route || routeRef.current}</div>
        <div className="website-orb-row">
          <input
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            placeholder="Ask Weaver"
            aria-label="Ask Weaver"
          />
          <button type="submit">Ask</button>
          <button type="button" onClick={() => void startVoice()}>{state === "listening" ? "Stop" : "Voice"}</button>
        </div>
      </form>
    </div>
  );
};

export default WebsiteORB;
