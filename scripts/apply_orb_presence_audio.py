#!/usr/bin/env python3
"""Apply the governed ORB intro and presence-audio wiring.

Idempotent and guarded: expected source anchors must exist or the script stops
without writing a partial patch.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LANDING = ROOT / 'frontend/src/landing/LandingPage.tsx'
ORB = ROOT / 'frontend/src/landing/AutonomousOrb.tsx'


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f'{label}: expected exactly one source anchor, found {count}')
    return text.replace(old, new, 1)


def patch_landing(text: str) -> str:
    text = replace_once(
        text,
        'import OrbBurst from "./OrbBurst";\n',
        'import OrbBurst from "./OrbBurst";\nimport { orbPresenceAudio } from "../orb/audio/orbPresenceAudio";\n',
        'LandingPage audio import',
    )
    text = replace_once(
        text,
        '    if (!splashTrigger) return;\n    const timer = window.setTimeout(() => setSplashTrigger(0), LANDING_SPLASH_DURATION_MS);',
        '    if (!splashTrigger) return;\n    orbPresenceAudio.requestIntro();\n    const timer = window.setTimeout(() => setSplashTrigger(0), LANDING_SPLASH_DURATION_MS);',
        'LandingPage splash audio request',
    )
    return text


def patch_orb(text: str) -> str:
    text = replace_once(
        text,
        'import { OrbRoboticsMovementController } from "../orb/robotics/movementController";\n',
        'import { OrbRoboticsMovementController } from "../orb/robotics/movementController";\nimport { orbPresenceAudio } from "../orb/audio/orbPresenceAudio";\n',
        'AutonomousOrb audio import',
    )
    text = replace_once(
        text,
        '  const unlockAudio = useCallback(() => {\n    if (audioUnlockedRef.current) return;',
        '  const unlockAudio = useCallback(() => {\n    orbPresenceAudio.unlock();\n    if (audioUnlockedRef.current) return;',
        'AutonomousOrb audio unlock',
    )
    text = replace_once(
        text,
        '  const [pointerWaltzPhase, setPointerWaltzPhase] = useState<PointerWaltzPhase | null>(null);\n  const [greetingActive, setGreetingActive] = useState(false);\n\n  const markFirstEncounter',
        '  const [pointerWaltzPhase, setPointerWaltzPhase] = useState<PointerWaltzPhase | null>(null);\n  const [greetingActive, setGreetingActive] = useState(false);\n\n  useEffect(() => orbPresenceAudio.mount(), []);\n\n  useEffect(() => {\n    orbPresenceAudio.setVoiceState(voiceState);\n    orbPresenceAudio.setResting(isResting);\n  }, [isResting, voiceState]);\n\n  const markFirstEncounter',
        'AutonomousOrb audio lifecycle',
    )
    text = replace_once(
        text,
        '    speakerBoostRef.current = next;\n    setSpeakerBoost(next);',
        '    speakerBoostRef.current = next;\n    setSpeakerBoost(next);\n    orbPresenceAudio.setBoosted(next);',
        'AutonomousOrb speaker boost integration',
    )
    text = replace_once(
        text,
        '    <motion.div\n      animate={move}\n      className={`ow-v2-orb-position',
        '    <motion.div\n      animate={move}\n      onAnimationStart={() => orbPresenceAudio.setMoving(true)}\n      onAnimationComplete={() => orbPresenceAudio.setMoving(false)}\n      className={`ow-v2-orb-position',
        'AutonomousOrb motion integration',
    )
    return text


def main() -> None:
    landing_before = LANDING.read_text(encoding='utf-8')
    orb_before = ORB.read_text(encoding='utf-8')
    landing_after = patch_landing(landing_before)
    orb_after = patch_orb(orb_before)

    LANDING.write_text(landing_after, encoding='utf-8')
    ORB.write_text(orb_after, encoding='utf-8')
    print('ORB intro and presence audio wiring applied.')


if __name__ == '__main__':
    main()
