const INTRO_AUDIO_PATH = '/orb/voice/orb-intro-presence.mp3';
const HUM_AUDIO_PATH = '/orb/voice/orb-presence-hum.mp3';

const INTRO_VOLUME = 0.82;
const HUM_IDLE_VOLUME = 0.026;
const HUM_MOVING_VOLUME = 0.052;
const HUM_RESTING_VOLUME = 0.012;
const HUM_BOOST_MULTIPLIER = 1.2;
const HUM_MAX_VOLUME = 0.064;
const VOLUME_RAMP_MS = 420;

type OrbVoiceState = 'idle' | 'listening' | 'speaking';

class OrbPresenceAudioController {
  private introAudio: HTMLAudioElement | null = null;
  private humAudio: HTMLAudioElement | null = null;
  private mountedCount = 0;
  private unlocked = false;
  private introRequested = false;
  private introPlayed = false;
  private introPlaying = false;
  private moving = false;
  private resting = false;
  private voiceState: OrbVoiceState = 'idle';
  private boosted = false;
  private rampFrame: number | null = null;
  private gestureListenersInstalled = false;

  private readonly handleGesture = () => {
    this.unlock();
  };

  private readonly handleVisibility = () => {
    this.syncHum();
  };

  mount(): () => void {
    this.mountedCount += 1;
    this.ensureAudio();
    this.installGestureListeners();
    document.addEventListener('visibilitychange', this.handleVisibility);
    this.tryPlayIntro();
    this.syncHum();

    return () => {
      this.mountedCount = Math.max(0, this.mountedCount - 1);
      document.removeEventListener('visibilitychange', this.handleVisibility);
      if (this.mountedCount === 0) {
        this.cancelRamp();
        this.humAudio?.pause();
        if (this.humAudio) this.humAudio.volume = 0;
      }
    };
  }

  requestIntro(): void {
    this.introRequested = true;
    this.ensureAudio();
    this.installGestureListeners();
    this.tryPlayIntro();
  }

  unlock(): void {
    this.unlocked = true;
    this.removeGestureListeners();
    this.tryPlayIntro();
    this.syncHum();
  }

  setMoving(moving: boolean): void {
    this.moving = moving;
    this.syncHum();
  }

  setResting(resting: boolean): void {
    this.resting = resting;
    this.syncHum();
  }

  setVoiceState(state: OrbVoiceState): void {
    this.voiceState = state;
    this.syncHum();
  }

  setBoosted(boosted: boolean): void {
    this.boosted = boosted;
    if (this.introAudio && this.introPlaying) {
      this.introAudio.volume = boosted ? 1 : INTRO_VOLUME;
    }
    this.syncHum();
  }

  private ensureAudio(): void {
    if (!this.introAudio) {
      const intro = new Audio(INTRO_AUDIO_PATH);
      intro.preload = 'auto';
      intro.volume = INTRO_VOLUME;
      intro.addEventListener('ended', () => {
        this.introPlaying = false;
        this.syncHum();
      });
      intro.addEventListener('error', () => {
        this.introPlaying = false;
        this.syncHum();
      });
      this.introAudio = intro;
    }

    if (!this.humAudio) {
      const hum = new Audio(HUM_AUDIO_PATH);
      hum.preload = 'auto';
      hum.loop = true;
      hum.volume = 0;
      this.humAudio = hum;
    }
  }

  private installGestureListeners(): void {
    if (this.gestureListenersInstalled || this.unlocked) return;
    this.gestureListenersInstalled = true;
    window.addEventListener('pointerdown', this.handleGesture, { passive: true });
    window.addEventListener('touchstart', this.handleGesture, { passive: true });
    window.addEventListener('keydown', this.handleGesture);
  }

  private removeGestureListeners(): void {
    if (!this.gestureListenersInstalled) return;
    this.gestureListenersInstalled = false;
    window.removeEventListener('pointerdown', this.handleGesture);
    window.removeEventListener('touchstart', this.handleGesture);
    window.removeEventListener('keydown', this.handleGesture);
  }

  private tryPlayIntro(): void {
    if (!this.introRequested || this.introPlayed || this.introPlaying) return;
    this.ensureAudio();
    const intro = this.introAudio;
    if (!intro) return;

    this.introPlaying = true;
    this.rampHumTo(0);
    intro.currentTime = 0;
    intro.volume = this.boosted ? 1 : INTRO_VOLUME;
    void intro.play()
      .then(() => {
        this.unlocked = true;
        this.introPlayed = true;
        this.removeGestureListeners();
      })
      .catch(() => {
        this.introPlaying = false;
        this.installGestureListeners();
      });
  }

  private desiredHumVolume(): number {
    if (
      this.mountedCount <= 0 ||
      !this.unlocked ||
      document.hidden ||
      this.introPlaying ||
      this.voiceState !== 'idle'
    ) {
      return 0;
    }

    const base = this.resting
      ? HUM_RESTING_VOLUME
      : this.moving
        ? HUM_MOVING_VOLUME
        : HUM_IDLE_VOLUME;
    const adjusted = this.boosted ? base * HUM_BOOST_MULTIPLIER : base;
    return Math.min(HUM_MAX_VOLUME, adjusted);
  }

  private syncHum(): void {
    this.ensureAudio();
    const hum = this.humAudio;
    if (!hum) return;

    const target = this.desiredHumVolume();
    if (target > 0) {
      void hum.play().catch(() => {
        this.installGestureListeners();
      });
    }
    this.rampHumTo(target);
  }

  private rampHumTo(target: number): void {
    const hum = this.humAudio;
    if (!hum) return;
    this.cancelRamp();

    const initial = hum.volume;
    const startedAt = performance.now();
    const animate = (now: number) => {
      const progress = Math.min(1, (now - startedAt) / VOLUME_RAMP_MS);
      hum.volume = initial + (target - initial) * progress;
      if (progress < 1) {
        this.rampFrame = window.requestAnimationFrame(animate);
        return;
      }
      this.rampFrame = null;
      if (target === 0) hum.pause();
    };
    this.rampFrame = window.requestAnimationFrame(animate);
  }

  private cancelRamp(): void {
    if (this.rampFrame == null) return;
    window.cancelAnimationFrame(this.rampFrame);
    this.rampFrame = null;
  }
}

export const orbPresenceAudio = new OrbPresenceAudioController();
