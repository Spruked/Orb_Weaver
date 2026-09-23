import React from "react";
import "./Landing.css";

type OrbState = "idle" | "listening" | "thinking" | "speaking";
type OrbEyeDirection = { x: number; y: number };

export const Orb: React.FC<{
  size?: number;
  state?: OrbState;
  speechAmplitude?: number;
  eyeDirection?: OrbEyeDirection;
  onClick?: () => void;
  skinSrc?: string;
}> = ({
  size = 200,
  state = "idle",
  speechAmplitude = 0,
  eyeDirection = { x: 0, y: 0 },
  onClick,
  skinSrc = "/orb-skins/weaver-blue-eye.png",
}) => {
  const normalizedAmplitude = Math.min(1, Math.max(0, speechAmplitude));
  const eyeX = Math.min(1, Math.max(-1, eyeDirection.x));
  const eyeY = Math.min(1, Math.max(-1, eyeDirection.y));
  return (
    <button
      type="button"
      className={`weaver-root ${state}`}
      style={{
        width: size,
        height: size,
        // The center remains visually solid.  Amplitude controls its motion,
        // not a distracting fade in and out.
        "--ow-speech-core-opacity": String(0.96 + normalizedAmplitude * 0.04),
        "--ow-speech-core-scale": String(1 + normalizedAmplitude * 0.48),
        "--ow-speech-amplitude": String(normalizedAmplitude),
        "--ow-eye-x": String(eyeX),
        "--ow-eye-y": String(eyeY),
      } as React.CSSProperties}
      aria-label="Orb Weaver intelligence orb"
      onClick={onClick}
    >
      <img className="weaver-body" src={skinSrc} alt="Weaver website presence" draggable={false} />
      <div className="weaver-eye-director" aria-hidden="true">
        <span className="weaver-eye-director-pupil" />
      </div>
    </button>
  );
};

export default Orb;
