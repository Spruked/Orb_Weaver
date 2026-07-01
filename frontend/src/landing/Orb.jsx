import React from "react";
import { motion } from "framer-motion";

// state: idle | listening | thinking | speaking
const PALETTE = {
  idle:      { core: "#D4AF37", glow: "rgba(212,175,55,0.45)", ring: "rgba(212,175,55,0.25)" },
  listening: { core: "#5BC8E6", glow: "rgba(91,200,230,0.55)", ring: "rgba(91,200,230,0.35)" },
  thinking:  { core: "#C77DFF", glow: "rgba(199,125,255,0.55)", ring: "rgba(199,125,255,0.35)" },
  speaking:  { core: "#F5D060", glow: "rgba(245,208,96,0.6)",  ring: "rgba(245,208,96,0.4)"  },
};

export const Orb = ({ state = "idle", size = 120, level = 0 }) => {
  const c = PALETTE[state] || PALETTE.idle;
  const pulse =
    state === "thinking"
      ? { scale: [1, 1.06, 0.97, 1.04, 1], rotate: [0, 8, -6, 0] }
      : state === "listening"
      ? { scale: [1, 1.05, 1] }
      : state === "speaking"
      ? { scale: [1, 1.04 + level * 0.12, 1] }
      : { scale: [1, 1.025, 1] };
  const dur = state === "thinking" ? 1.1 : state === "speaking" ? 0.45 : state === "listening" ? 1.6 : 4.5;

  return (
    <div
      data-testid="orb-visual"
      style={{ width: size, height: size }}
      className="relative flex items-center justify-center select-none"
      aria-label={`Orb ${state}`}
    >
      {/* outer glow */}
      <motion.div
        className="absolute rounded-full"
        style={{ width: size * 1.9, height: size * 1.9, background: `radial-gradient(circle, ${c.glow} 0%, transparent 65%)`, filter: "blur(8px)" }}
        animate={{ opacity: [0.5, 0.85, 0.5], scale: [1, 1.08, 1] }}
        transition={{ duration: dur, repeat: Infinity, ease: "easeInOut" }}
      />
      {/* expanding rings */}
      {[0, 1].map((i) => (
        <motion.div
          key={i}
          className="absolute rounded-full border"
          style={{ width: size, height: size, borderColor: c.ring }}
          animate={{ scale: [1, 1.8], opacity: [0.6, 0] }}
          transition={{ duration: dur * 1.3, repeat: Infinity, delay: i * (dur * 0.6), ease: "easeOut" }}
        />
      ))}
      {/* the sphere */}
      <motion.div
        className="relative rounded-full"
        style={{
          width: size, height: size,
          background: `radial-gradient(circle at 32% 28%, #fff8e6 0%, ${c.core} 30%, #1a1505 78%, #000 100%)`,
          boxShadow: `inset -8px -10px 24px rgba(0,0,0,0.7), inset 6px 6px 18px rgba(255,255,255,0.25), 0 0 50px ${c.glow}`,
        }}
        animate={pulse}
        transition={{ duration: dur, repeat: Infinity, ease: "easeInOut" }}
      >
        {/* inner swirl highlight */}
        <motion.div
          className="absolute rounded-full"
          style={{ inset: size * 0.16, background: `radial-gradient(circle at 60% 65%, ${c.core}66, transparent 70%)`, filter: "blur(4px)" }}
          animate={{ rotate: [0, 360] }}
          transition={{ duration: state === "thinking" ? 3 : 10, repeat: Infinity, ease: "linear" }}
        />
        {/* specular dot */}
        <div className="absolute rounded-full bg-white/80" style={{ width: size * 0.12, height: size * 0.12, top: size * 0.2, left: size * 0.26, filter: "blur(1px)" }} />
      </motion.div>
    </div>
  );
};

export default Orb;
