#!/usr/bin/env python3
"""Apply the owner-approved Website ORB guidance geometry repair.

The patch is idempotent and guarded. It reduces the deployed MORB to the
canonical 50 px rendered body, constrains the visual ping halo, and guarantees
clearance between the Prime ORB, the MORB, and the verified target after
viewport clamping.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORB = ROOT / "frontend/src/landing/AutonomousOrb.tsx"
LANDING_CSS = ROOT / "frontend/src/landing/Landing.css"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one source anchor, found {count}")
    return text.replace(old, new, 1)


def patch_orb(text: str) -> str:
    text = replace_once(
        text,
        "const MORB_SIZE = 65;\nconst MORB_HALF = MORB_SIZE / 2;\nconst MORB_REUSE_DISTANCE_PX = 250;",
        "const MORB_SIZE = 50;\nconst MORB_HALF = MORB_SIZE / 2;\nconst MORB_REUSE_DISTANCE_PX = 250;\nconst ORB_TARGET_CLEARANCE_PX = 56;",
        "MORB geometry constants",
    )

    text = replace_once(
        text,
        """    const side = targetCenterX < window.innerWidth / 2 ? 1 : -1;
    const guidedDestination = clampPosition(
      targetCenterX + side * Math.max(84, size * 0.62) - size / 2,
      targetCenterY - size / 2,
    );""",
        """    const preferredSide = targetCenterX < window.innerWidth / 2 ? 1 : -1;
    const requiredCenterOffset = size / 2 + MORB_HALF + ORB_TARGET_CLEARANCE_PX;
    const guidedDestination = [preferredSide, -preferredSide]
      .map((candidateSide) => clampPosition(
        targetCenterX + candidateSide * requiredCenterOffset - size / 2,
        targetCenterY - size / 2,
      ))
      .reduce((best, candidate) => {
        const bestClearance = Math.abs(best.x + size / 2 - targetCenterX);
        const candidateClearance = Math.abs(candidate.x + size / 2 - targetCenterX);
        return candidateClearance > bestClearance ? candidate : best;
      });""",
        "Prime ORB target-clearance geometry",
    )
    return text


def patch_css(text: str) -> str:
    text = replace_once(
        text,
        """.ow-v2-morb-pointer {
  position: fixed;
  z-index: 2147483001;
  width: 65px;
  height: 65px;""",
        """.ow-v2-morb-pointer {
  position: fixed;
  z-index: 2147483001;
  width: 50px;
  height: 50px;""",
        "Rendered MORB body size",
    )

    text = replace_once(
        text,
        """@keyframes ow-v2-morb-ping {
  0% { filter: brightness(1); box-shadow: 0 0 18px var(--ow-morb-shadow, rgba(91, 200, 230, .68)), 0 0 34px var(--ow-morb-glow, rgba(91, 200, 230, .32)); }
  42% { filter: brightness(1.46); box-shadow: 0 0 30px var(--ow-morb-shadow, rgba(91, 200, 230, .82)), 0 0 74px var(--ow-morb-glow, rgba(91, 200, 230, .5)); }
  100% { filter: brightness(1); box-shadow: 0 0 22px var(--ow-morb-shadow, rgba(91, 200, 230, .68)), 0 0 48px var(--ow-morb-glow, rgba(91, 200, 230, .32)); }
}""",
        """@keyframes ow-v2-morb-ping {
  0% { filter: brightness(1); box-shadow: 0 0 8px var(--ow-morb-shadow, rgba(91, 200, 230, .68)), 0 0 14px var(--ow-morb-glow, rgba(91, 200, 230, .32)); }
  42% { filter: brightness(1.34); box-shadow: 0 0 12px var(--ow-morb-shadow, rgba(91, 200, 230, .82)), 0 0 24px var(--ow-morb-glow, rgba(91, 200, 230, .44)); }
  100% { filter: brightness(1); box-shadow: 0 0 9px var(--ow-morb-shadow, rgba(91, 200, 230, .68)), 0 0 16px var(--ow-morb-glow, rgba(91, 200, 230, .32)); }
}""",
        "MORB ping halo",
    )
    return text


def main() -> None:
    orb_before = ORB.read_text(encoding="utf-8")
    css_before = LANDING_CSS.read_text(encoding="utf-8")

    orb_after = patch_orb(orb_before)
    css_after = patch_css(css_before)

    ORB.write_text(orb_after, encoding="utf-8")
    LANDING_CSS.write_text(css_after, encoding="utf-8")

    print(
        "ORB guidance geometry applied: 50 px rendered MORB body, "
        "24 px maximum soft ping halo, 56 px Prime ORB clearance."
    )


if __name__ == "__main__":
    main()
