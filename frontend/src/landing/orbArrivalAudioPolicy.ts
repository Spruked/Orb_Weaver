const POLICY_KEY = '__orbWeaverWarmArrivalAudioPolicyInstalled';

type WindowWithAudioPolicy = Window & {
  [POLICY_KEY]?: boolean;
  webkitAudioContext?: typeof AudioContext;
};

/**
 * Suppresses the legacy synthesized 580ms scrape/squeal used by AutonomousOrb
 * during first arrival. Spoken TTS, listening acknowledgement tones, and normal
 * decoded speech continue to use the browser audio graph unchanged.
 */
export function installWarmArrivalAudioPolicy(): void {
  if (typeof window === 'undefined') return;
  const controlledWindow = window as WindowWithAudioPolicy;
  if (controlledWindow[POLICY_KEY]) return;

  const AudioContextCtor = window.AudioContext || controlledWindow.webkitAudioContext;
  const sourcePrototype = window.AudioBufferSourceNode?.prototype;
  if (!AudioContextCtor || !sourcePrototype) return;

  const suppressedSources = new WeakSet<AudioBufferSourceNode>();
  const originalStart = sourcePrototype.start;
  const originalStop = sourcePrototype.stop;

  sourcePrototype.start = function guardedStart(
    this: AudioBufferSourceNode,
    when?: number,
    offset?: number,
    duration?: number
  ): void {
    const buffer = this.buffer;
    const isLegacyArrivalScreech = Boolean(
      buffer &&
      buffer.numberOfChannels === 1 &&
      Math.abs(buffer.duration - 0.58) < 0.002
    );

    if (isLegacyArrivalScreech) {
      suppressedSources.add(this);
      return;
    }

    originalStart.call(this, when, offset, duration);
  };

  sourcePrototype.stop = function guardedStop(
    this: AudioBufferSourceNode,
    when?: number
  ): void {
    if (suppressedSources.has(this)) {
      suppressedSources.delete(this);
      return;
    }
    originalStop.call(this, when);
  };

  controlledWindow[POLICY_KEY] = true;
}
