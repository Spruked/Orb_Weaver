export type OrbPoint = {
  x: number;
  y: number;
};

export type OrbKineticOptions = {
  radius?: number;
  evasionRadius?: number;
  edgePadding?: number;
  intervalMs?: number;
  glideFactor?: number;
  evasionFactor?: number;
};

const DEFAULT_OPTIONS: Required<OrbKineticOptions> = {
  radius: 96,
  evasionRadius: 180,
  edgePadding: 28,
  intervalMs: 16,
  glideFactor: 0.018,
  evasionFactor: 0.14,
};

const clamp = (value: number, min: number, max: number): number =>
  Math.max(min, Math.min(max, value));

const distance = (a: OrbPoint, b: OrbPoint): number =>
  Math.hypot(a.x - b.x, a.y - b.y);

export class OrbKineticTransit {
  private readonly element: HTMLElement;
  private readonly options: Required<OrbKineticOptions>;
  private position: OrbPoint;
  private target: OrbPoint;
  private cursor: OrbPoint | null = null;
  private timer: number | null = null;
  private halted = false;
  private lastQuadrant = -1;

  constructor(element: HTMLElement, initialPosition?: OrbPoint, options?: OrbKineticOptions) {
    this.element = element;
    this.options = { ...DEFAULT_OPTIONS, ...options };
    this.position = initialPosition ?? this.safeQuadrantTarget();
    this.target = this.safeQuadrantTarget();
    this.applyPosition();
  }

  start(): void {
    if (this.timer !== null) return;
    window.addEventListener("mousemove", this.handleMouseMove, { passive: true });
    this.timer = window.setInterval(() => this.tick(), this.options.intervalMs);
  }

  stop(): void {
    if (this.timer !== null) {
      window.clearInterval(this.timer);
      this.timer = null;
    }
    window.removeEventListener("mousemove", this.handleMouseMove);
  }

  haltToSafePosition(): void {
    this.halted = true;
    this.target = this.safeQuadrantTarget();
  }

  resume(): void {
    this.halted = false;
    this.target = this.safeQuadrantTarget();
  }

  setTarget(target: OrbPoint): void {
    this.target = this.constrain(target);
  }

  getPosition(): OrbPoint {
    return { ...this.position };
  }

  private handleMouseMove = (event: MouseEvent): void => {
    this.cursor = { x: event.clientX, y: event.clientY };
  };

  private tick(): void {
    if (!this.halted && distance(this.position, this.target) < 18) {
      this.target = this.safeQuadrantTarget();
    }

    if (this.cursor && distance(this.position, this.cursor) < this.options.evasionRadius) {
      this.target = this.evasionTarget(this.cursor);
      this.position = this.interpolate(this.position, this.target, this.options.evasionFactor);
    } else {
      this.position = this.interpolate(this.position, this.target, this.options.glideFactor);
    }

    this.position = this.constrain(this.position);
    this.applyPosition();
  }

  private evasionTarget(cursor: OrbPoint): OrbPoint {
    const dx = this.position.x - cursor.x;
    const dy = this.position.y - cursor.y;
    const magnitude = Math.max(Math.hypot(dx, dy), 1);
    const push = this.options.evasionRadius + this.options.radius;

    return this.constrain({
      x: this.position.x + (dx / magnitude) * push,
      y: this.position.y + (dy / magnitude) * push,
    });
  }

  private safeQuadrantTarget(): OrbPoint {
    const width = window.innerWidth;
    const height = window.innerHeight;
    const pad = this.options.edgePadding;
    const size = this.options.radius;
    const quadrants: OrbPoint[] = [
      { x: pad, y: pad },
      { x: width - size - pad, y: pad },
      { x: pad, y: height - size - pad },
      { x: width - size - pad, y: height - size - pad },
    ];

    let next = Math.floor(Math.random() * quadrants.length);
    if (next === this.lastQuadrant) {
      next = (next + 1) % quadrants.length;
    }
    this.lastQuadrant = next;
    return this.constrain(quadrants[next]);
  }

  private interpolate(current: OrbPoint, target: OrbPoint, factor: number): OrbPoint {
    return {
      x: current.x + (target.x - current.x) * factor,
      y: current.y + (target.y - current.y) * factor,
    };
  }

  private constrain(point: OrbPoint): OrbPoint {
    const maxX = Math.max(this.options.edgePadding, window.innerWidth - this.options.radius - this.options.edgePadding);
    const maxY = Math.max(this.options.edgePadding, window.innerHeight - this.options.radius - this.options.edgePadding);
    return {
      x: clamp(point.x, this.options.edgePadding, maxX),
      y: clamp(point.y, this.options.edgePadding, maxY),
    };
  }

  private applyPosition(): void {
    this.element.style.transform = `translate3d(${Math.round(this.position.x)}px, ${Math.round(this.position.y)}px, 0)`;
  }
}
