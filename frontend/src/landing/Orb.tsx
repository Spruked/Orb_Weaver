import React from "react";
import "./Landing.css";

type OrbState = "idle" | "listening" | "speaking";

export const Orb: React.FC<{ size?: number; state?: OrbState; onClick?: () => void }> = ({
  size = 200,
  state = "idle",
  onClick,
}) => {
  return (
    <button
      type="button"
      className={`ow-v2-orb-body ${state}`}
      style={{ width: size, height: size }}
      aria-label="Orb Weaver intelligence orb"
      onClick={onClick}
    >
      <div className="ow-v2-orb-halo" />
      <div className="ow-v2-orb-surface" />
      <div className="ow-v2-orb-core-light" />
      <div className="ow-v2-orb-specular" />
      <div className="ow-v2-orb-lower-shadow" />
    </button>
  );
};

export default Orb;
