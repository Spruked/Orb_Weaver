import React, { useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";

const COLORS = {
  blue: "91,200,230",
  gold: "212,175,55",
  violet: "199,125,255",
};

// A reusable, pronounced "splash" shockwave for the Orb.
// Replays every time `trigger` changes. direction: "out" (arrive) | "in" (leave).
// Arrival timing is intentionally stretched without changing the visual path so
// ORB cold-start work can run underneath the splash instead of after it.
export const OrbBurst = ({ trigger = 0, size = 200, color = "blue", direction = "out", completionDelayMs = 0, onComplete }) => {
  const rgb = COLORS[color] || COLORS.blue;
  const out = direction === "out";
  const finalRingIndex = 4;
  const completionFiredRef = useRef(false);
  const completionTimerRef = useRef(null);

  useEffect(() => {
    completionFiredRef.current = false;
    if (completionTimerRef.current) window.clearTimeout(completionTimerRef.current);
  }, [trigger]);

  useEffect(() => () => {
    if (completionTimerRef.current) window.clearTimeout(completionTimerRef.current);
  }, []);

  const completeOnce = () => {
    if (completionFiredRef.current) return;
    completionFiredRef.current = true;
    if (completionDelayMs > 0) {
      completionTimerRef.current = window.setTimeout(() => onComplete?.(), completionDelayMs);
      return;
    }
    onComplete?.();
  };

  return (
    <div className="absolute inset-0 pointer-events-none" style={{ overflow: "visible", zIndex: 9 }}>
      <AnimatePresence>
        {trigger > 0 && (
          <motion.div key={trigger} className="absolute inset-0" initial={{ opacity: 1 }} exit={{ opacity: 0 }}>
            {/* central flash */}
            <Centered size={size}>
              <motion.div
                className="rounded-full bg-white"
                style={{ width: size * 0.7, height: size * 0.7, filter: "blur(10px)" }}
                initial={{ scale: out ? 0.2 : 1.6, opacity: 0 }}
                animate={{ scale: out ? [0.2, 1.8, 0.4] : [1.6, 0.2], opacity: [0, 0.95, 0] }}
                transition={{ duration: out ? 1.28 : 0.7, ease: "easeOut" }}
              />
            </Centered>

            {/* bright bloom rushing toward / away from the viewer */}
            <Centered size={size}>
              <motion.div
                className="rounded-full"
                style={{
                  width: size * 2.6, height: size * 2.6, filter: "blur(16px)",
                  background: `radial-gradient(circle, rgba(${rgb},0.9) 0%, rgba(${rgb},0.28) 36%, transparent 66%)`,
                }}
                initial={{ scale: out ? 0.1 : 3.2, opacity: 0 }}
                animate={{ scale: out ? [0.1, 1.3, 3.8] : [3.2, 0.2], opacity: out ? [0, 1, 0] : [0.9, 0] }}
                transition={{ duration: out ? 2.7 : 0.8, ease: "easeOut" }}
              />
            </Centered>

            {/* expanding/imploding rings — the 3D "coming out of the screen" effect */}
            {[0, 1, 2, 3, 4].map((i) => (
              <Centered key={i} size={size}>
                <motion.div
                  className="rounded-full"
                  style={{
                    width: size, height: size,
                    border: `${i === 0 ? 4 : i === 1 ? 3 : 2}px solid rgba(${rgb},${0.8 - i * 0.12})`,
                    boxShadow: `0 0 ${50 - i * 6}px rgba(${rgb},0.6)`,
                  }}
                  initial={{ scale: out ? 0.12 : 9.5, opacity: 0 }}
                  animate={{ scale: out ? [0.12, 9.5] : [9.5, 0.1], opacity: [0.95, 0] }}
                  transition={{ duration: out ? 2.43 : 0.9, delay: i * (out ? 0.216 : 0.06), ease: [0.22, 0.61, 0.36, 1] }}
                  onAnimationComplete={i === finalRingIndex ? completeOnce : undefined}
                />
              </Centered>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

const Centered = ({ size, children }) => (
  <div className="absolute" style={{ left: "50%", top: "50%", width: 0, height: 0 }}>
    <div style={{ position: "absolute", left: 0, top: 0, transform: "translate(-50%, -50%)" }}>
      {children}
    </div>
  </div>
);

export default OrbBurst;
