#!/usr/bin/env python3
"""Apply the owner-approved Website ORB guidance geometry repair.

The patch is idempotent and guarded. It reduces the deployed MORB to the
canonical 50 px size and guarantees visible clearance between the Prime ORB,
the MORB, and the verified target after viewport clamping.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORB = ROOT / "frontend/src/landing/AutonomousOrb.tsx"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one source anchor, found {count}")
    return text.replace(old, new, 1)


def main() -> None:
    before = ORB.read_text(encoding="utf-8")
    after = before

    after = replace_once(
        after,
        "const MORB_SIZE = 65;\nconst MORB_HALF = MORB_SIZE / 2;\nconst MORB_REUSE_DISTANCE_PX = 250;",
        "const MORB_SIZE = 50;\nconst MORB_HALF = MORB_SIZE / 2;\nconst MORB_REUSE_DISTANCE_PX = 250;\nconst ORB_TARGET_CLEARANCE_PX = 56;",
        "MORB size and clearance constants",
    )

    after = replace_once(
        after,
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

    if after == before:
        print("ORB guidance geometry already applied.")
        return

    ORB.write_text(after, encoding="utf-8")
    print("ORB guidance geometry applied: MORB 50 px, target clearance 56 px.")


if __name__ == "__main__":
    main()
