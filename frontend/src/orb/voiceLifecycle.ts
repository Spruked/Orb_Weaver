export type PlaybackSettlement = {
  promise: Promise<void>;
  resolve: () => void;
  reject: (error: Error) => void;
  cancel: () => void;
  isSettled: () => boolean;
};

export const abortError = (message = "Playback interrupted"): Error => {
  const error = new Error(message);
  error.name = "AbortError";
  return error;
};

export const createPlaybackSettlement = (): PlaybackSettlement => {
  let settled = false;
  let resolvePromise: () => void = () => undefined;
  let rejectPromise: (error: Error) => void = () => undefined;
  const promise = new Promise<void>((resolve, reject) => {
    resolvePromise = resolve;
    rejectPromise = reject;
  });
  return {
    promise,
    resolve: () => {
      if (settled) return;
      settled = true;
      resolvePromise();
    },
    reject: (error) => {
      if (settled) return;
      settled = true;
      rejectPromise(error);
    },
    cancel: () => {
      if (settled) return;
      settled = true;
      rejectPromise(abortError());
    },
    isSettled: () => settled,
  };
};

export type RecoveryOutcome = "played" | "cancelled" | "unavailable";

export const runBackendRecovery = async <T extends { tts_audio_url?: string | null }>(
  synthesize: (signal?: AbortSignal) => Promise<T>,
  play: (result: T) => Promise<boolean>,
  signal?: AbortSignal,
): Promise<RecoveryOutcome> => {
  if (signal?.aborted) return "cancelled";
  try {
    const result = await synthesize(signal);
    if (signal?.aborted) return "cancelled";
    if (!result.tts_audio_url) return "unavailable";
    return (await play(result)) ? "played" : "unavailable";
  } catch (error) {
    return (error as Error)?.name === "AbortError" || signal?.aborted ? "cancelled" : "unavailable";
  }
};

export const shouldRearmVoice = (state: {
  handsFree: boolean;
  voiceState: "idle" | "listening" | "thinking" | "speaking";
  onboardingSafeMode: boolean;
  requestInFlight: boolean;
  recording: boolean;
  firstEncounterRunning: boolean;
  voiceReady: boolean;
}): boolean => (
  state.handsFree &&
  state.voiceState === "idle" &&
  !state.onboardingSafeMode &&
  !state.requestInFlight &&
  !state.recording &&
  !state.firstEncounterRunning &&
  state.voiceReady
);

export const shouldRunMountedStartupVoiceSequence = (state: {
  startupAutoStarted: boolean;
  onboardingSafeMode: boolean;
  onLanding: boolean;
  greetingAlreadyPlayed: boolean;
  voiceReady: boolean;
}): boolean => (
  !state.startupAutoStarted &&
  !state.onboardingSafeMode &&
  state.onLanding
);


/** Abort an operation's wait without treating cancellation as successful completion. */
export function awaitAbortable<T>(operation: PromiseLike<T>, signal?: AbortSignal): Promise<T> {
  if (!signal) return Promise.resolve(operation);
  return new Promise<T>((resolve, reject) => {
    const abort = () => reject(abortError());
    signal.addEventListener('abort', abort, { once: true });
    Promise.resolve(operation).then(resolve, reject).finally(() => signal.removeEventListener('abort', abort));
    if (signal.aborted) {
      signal.removeEventListener('abort', abort);
      abort();
    }
  });
}
