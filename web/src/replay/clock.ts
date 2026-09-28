/* The playback clock: a time in playback seconds, a speed, play and pause, driven by
   requestAnimationFrame. Listeners are told on every tick and every seek; the component
   turns a tick into one frame. Nothing is allocated per tick. */

import { useSyncExternalStore } from "react";

export class Clock {
  time = 0;
  playing = false;
  speed = 1;
  duration: number;
  version = 0;
  private listeners = new Set<() => void>();
  private raf: number | null = null;
  private last = 0;

  constructor(duration: number, speed = 1) {
    this.duration = duration;
    this.speed = speed;
  }

  subscribe(fn: () => void): () => void {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  }

  private emit(): void {
    this.version++;
    for (const fn of this.listeners) fn();
  }

  seek(t: number): void {
    this.time = Math.max(
      0,
      Math.min(this.duration, Number.isFinite(t) ? t : 0),
    );
    this.emit();
  }

  setSpeed(speed: number): void {
    this.speed = speed;
    this.emit();
  }

  play(): void {
    if (this.playing) return;
    if (this.time >= this.duration) this.time = 0;
    this.playing = true;
    this.last = now();
    this.raf = requestAnimationFrame(this.tick);
    this.emit();
  }

  pause(): void {
    if (!this.playing) return;
    this.playing = false;
    if (this.raf !== null) cancelAnimationFrame(this.raf);
    this.raf = null;
    this.emit();
  }

  toggle(): void {
    if (this.playing) this.pause();
    else this.play();
  }

  dispose(): void {
    this.pause();
    this.listeners.clear();
  }

  private tick = (): void => {
    if (!this.playing) return;
    const t = now();
    const dt = Math.min(0.1, (t - this.last) / 1000); // a tab that slept does not leap
    this.last = t;
    this.time = Math.min(this.duration, this.time + dt * this.speed);
    if (this.time >= this.duration) {
      this.playing = false;
      this.raf = null;
      this.emit();
      return;
    }
    this.raf = requestAnimationFrame(this.tick);
    this.emit();
  };
}

function now(): number {
  return typeof performance !== "undefined" ? performance.now() : Date.now();
}

/* The clock's version, so a component renders on every tick and reads the fields it needs. */
export function useClock(clock: Clock): number {
  return useSyncExternalStore(
    (fn) => clock.subscribe(fn),
    () => clock.version,
    () => clock.version,
  );
}
