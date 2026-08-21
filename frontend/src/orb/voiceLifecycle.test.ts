import {
  createPlaybackSettlement,
  runBackendRecovery,
  shouldRearmVoice,
  shouldRunMountedStartupVoiceSequence,
} from './voiceLifecycle';

declare const describe: (name: string, suite: () => void) => void;
declare const test: (name: string, run: () => void | Promise<void>) => void;
declare const expect: any;

describe('Website ORB voice lifecycle', () => {
  test('interrupt settles the active playback promise exactly once', async () => {
    const playback = createPlaybackSettlement();
    playback.cancel();
    playback.resolve();
    await expect(playback.promise).rejects.toMatchObject({ name: 'AbortError' });
    expect(playback.isSettled()).toBe(true);
  });

  test('an interrupted turn cannot settle the next turn playback', async () => {
    const interrupted = createPlaybackSettlement();
    const next = createPlaybackSettlement();
    interrupted.cancel();
    interrupted.resolve();
    expect(next.isSettled()).toBe(false);
    next.resolve();
    await expect(interrupted.promise).rejects.toMatchObject({ name: 'AbortError' });
    await expect(next.promise).resolves.toBeUndefined();
  });

  test('backend recovery waits for synthesis and playback', async () => {
    const events: string[] = [];
    const outcome = await runBackendRecovery(
      async () => {
        events.push('synthesized');
        return { tts_audio_url: '/voice/recovery.wav' };
      },
      async () => {
        events.push('played');
        return true;
      },
    );
    expect(outcome).toBe('played');
    expect(events).toEqual(['synthesized', 'played']);
  });

  test('recovery cancellation does not begin playback', async () => {
    const controller = new AbortController();
    controller.abort();
    let playCalls = 0;
    const play = async () => { playCalls += 1; return true; };
    const outcome = await runBackendRecovery(
      async () => ({ tts_audio_url: '/voice/recovery.wav' }),
      play,
      controller.signal,
    );
    expect(outcome).toBe('cancelled');
    expect(playCalls).toBe(0);
  });

  test('recovery reports unavailable without switching voice providers', async () => {
    let playCalls = 0;
    const play = async () => { playCalls += 1; return true; };
    const outcome = await runBackendRecovery(
      async () => ({ tts_audio_url: null }),
      play,
    );
    expect(outcome).toBe('unavailable');
    expect(playCalls).toBe(0);
  });

  test('hands-free rearm waits for completed recovery and clear locks', () => {
    const ready = {
      handsFree: true,
      voiceState: 'idle' as const,
      onboardingSafeMode: false,
      requestInFlight: false,
      recording: false,
      firstEncounterRunning: false,
      voiceReady: true,
    };
    expect(shouldRearmVoice({ ...ready, voiceState: 'speaking' })).toBe(false);
    expect(shouldRearmVoice({ ...ready, requestInFlight: true })).toBe(false);
    expect(shouldRearmVoice({ ...ready, recording: true })).toBe(false);
    expect(shouldRearmVoice(ready)).toBe(true);
  });

  test('mounted startup runs on a true first-encounter landing', () => {
    expect(shouldRunMountedStartupVoiceSequence({
      startupAutoStarted: false,
      onboardingSafeMode: false,
      onLanding: true,
      greetingAlreadyPlayed: false,
      voiceReady: false,
    })).toBe(true);
  });

  test('mounted startup avoids surprise mic prompts away from landing even after voice was established', () => {
    expect(shouldRunMountedStartupVoiceSequence({
      startupAutoStarted: false,
      onboardingSafeMode: false,
      onLanding: false,
      greetingAlreadyPlayed: true,
      voiceReady: true,
    })).toBe(false);
  });
});
