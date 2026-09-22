import React from "react";
import "./Landing.css";

type OrbState = "idle" | "listening" | "thinking" | "speaking";

export const Orb: React.FC<{
  size?: number;
  state?: OrbState;
  speechAmplitude?: number;
  onClick?: () => void;
  skinSrc?: string;
}> = ({
  size = 200,
  state = "idle",
  speechAmplitude = 0,
  onClick,
  skinSrc = "/orb-skins/weaver-red-eye.png",
}) => {
  const normalizedAmplitude = Math.min(1, Math.max(0, speechAmplitude));
  return (
    <button
      type="button"
      className={`ow-v2-orb-body ${state} has-image-skin has-red-eye-skin`}
      style={{
        width: size,
        height: size,
        // The center remains visually solid.  Amplitude controls its motion,
        // not a distracting fade in and out.
        "--ow-speech-core-opacity": String(0.96 + normalizedAmplitude * 0.04),
        "--ow-speech-core-scale": String(1 + normalizedAmplitude * 0.48),
        "--ow-speech-amplitude": String(normalizedAmplitude),
      } as React.CSSProperties}
      aria-label="Orb Weaver intelligence orb"
      onClick={onClick}
    >
      <img className="ow-v2-orb-skin-image" src={skinSrc} alt="Website ORB visual representation" draggable={false} />
      <div className="ow-v2-orb-eye-pulse" aria-hidden="true">
        <span className="ow-v2-orb-eye-lid" />
      </div>
    </button>
  );
};

export default Orb;
