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
  skinSrc = "/orb-skins/weaver-red-blue-center.png",
}) => {
  const normalizedAmplitude = Math.min(1, Math.max(0, speechAmplitude));
  return (
    <button
      type="button"
      className={`ow-v2-orb-body ${state} has-image-skin`}
      style={{
        width: size,
        height: size,
        "--ow-speech-core-opacity": String(0.56 + normalizedAmplitude * 0.42),
        "--ow-speech-core-scale": String(0.98 + normalizedAmplitude * 0.1),
      } as React.CSSProperties}
      aria-label="Orb Weaver intelligence orb"
      onClick={onClick}
    >
      <img className="ow-v2-orb-skin-image" src={skinSrc} alt="Website ORB visual representation" draggable={false} />
      <div className="ow-v2-orb-core-pulse" aria-hidden="true">
        <span className="ow-v2-orb-core-recess" />
        <span className="ow-v2-orb-core-fold ow-v2-orb-core-fold-one" />
        <span className="ow-v2-orb-core-fold ow-v2-orb-core-fold-two" />
        <span className="ow-v2-orb-core-fold ow-v2-orb-core-fold-three" />
        <span className="ow-v2-orb-core-nucleus" />
      </div>
    </button>
  );
};

export default Orb;
