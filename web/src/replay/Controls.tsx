import { SPEEDS } from "./timeline";
import { memo } from "react";
import styles from "./Controls.module.css";

/* The scrubber both views share: play and pause at a speed, one event back or forward, first
   and last, a slider over the run's time with a tick at every event outside a mix and a mark
   at every finding, a film button, and the current event in words. */
export function Controls({
  time,
  duration,
  step,
  count,
  playing,
  speed,
  line,
  ticks,
  marks,
  dry,
  onSeek,
  onStep,
  onPlay,
  onSpeed,
}: {
  time: number; // playback seconds
  duration: number;
  step: number; // the event in motion; count at the end
  count: number;
  playing: boolean;
  speed: number;
  line: string; // "line 34 · aspirate 5 µl of sample 1 from tube A3 in slot 2, tip A1"
  ticks: number[]; // fractions of the run
  marks: number[]; // fractions of the run: the findings
  dry?: number[]; // fractions of the run: the dry draws, in the warning tone
  onSeek: (t: number) => void;
  onStep: (step: number) => void;
  onPlay: (playing: boolean) => void;
  onSpeed: (speed: number) => void;
}) {
  const clamp = (n: number) => Math.max(0, Math.min(count, n));
  const at = duration > 0 ? time / duration : 0;
  return (
    <div className={styles.controls}>
      <div className={styles.buttons}>
        <button
          type="button"
          onClick={() => onStep(0)}
          title="The deck before the run starts (Home)"
          aria-label="First step"
        >
          ⇤
        </button>
        <button
          type="button"
          onClick={() => onStep(clamp(step - 1))}
          title="One event back (←)"
          aria-label="Step back"
        >
          ‹
        </button>
        <button
          type="button"
          className={styles.play}
          onClick={() => onPlay(!playing)}
          title={playing ? "Pause (space)" : "Play (space)"}
          aria-pressed={playing}
        >
          {playing ? "Pause" : "Play"}
        </button>
        <button
          type="button"
          onClick={() => onStep(clamp(step + 1))}
          title="One event forward (→)"
          aria-label="Step forward"
        >
          ›
        </button>
        <button
          type="button"
          onClick={() => onStep(count)}
          title="The end of the run (End)"
          aria-label="Last step"
        >
          ⇥
        </button>
        <label className={styles.speed}>
          <span className="sr-only">Speed</span>
          <select
            value={speed}
            onChange={(e) => onSpeed(Number(e.target.value))}
            aria-label="Speed"
          >
            {SPEEDS.map((s) => (
              <option key={s} value={s}>
                {s}×
              </option>
            ))}
          </select>
        </label>
        <span className={styles.count}>
          event <strong>{Math.min(step + 1, count)}</strong> of {count} ·
          playback {clock(time)} / {clock(duration)}
        </span>
      </div>
      <div className={styles.track}>
        <Ticks ticks={ticks} marks={marks} dry={dry ?? []} />
        <svg
          className={styles.ticks}
          viewBox="0 0 1000 8"
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          <line
            x1={at * 1000}
            x2={at * 1000}
            y1="0"
            y2="8"
            className={styles.now}
          />
        </svg>
        <input
          type="range"
          min={0}
          max={1000}
          value={Math.round(at * 1000)}
          onChange={(e) => onSeek((Number(e.target.value) / 1000) * duration)}
          className={styles.slider}
          aria-label="Time"
          aria-valuetext={`${clock(time)} of ${clock(duration)}, event ${Math.min(step + 1, count)} of ${count}`}
        />
      </div>
      <div
        className={styles.line}
        aria-live={playing ? "off" : "polite"}
        title={line}
      >
        {line}
      </div>
    </div>
  );
}

function clock(s: number): string {
  const m = Math.floor(s / 60);
  const r = Math.floor(s - m * 60);
  return `${m}:${r < 10 ? "0" : ""}${r}`;
}

/* The ticks and the findings' marks: drawn once per run, not once per clock tick. */
const Ticks = memo(function Ticks({
  ticks,
  marks,
  dry,
}: {
  ticks: number[];
  marks: number[];
  dry: number[];
}) {
  return (
    <svg
      className={styles.ticks}
      viewBox="0 0 1000 8"
      preserveAspectRatio="none"
      aria-hidden="true"
      data-dry={dry.length}
    >
      {ticks.map((f, i) => (
        <line
          key={i}
          x1={f * 1000}
          x2={f * 1000}
          y1="0"
          y2="8"
          className={styles.tick}
        />
      ))}
      {dry.map((f, i) => (
        <line
          key={`d${i}`}
          x1={f * 1000}
          x2={f * 1000}
          y1="0"
          y2="8"
          className={styles.tickDry}
        />
      ))}
      {marks.map((f, i) => (
        <line
          key={`m${i}`}
          x1={f * 1000}
          x2={f * 1000}
          y1="0"
          y2="8"
          className={styles.mark}
        />
      ))}
    </svg>
  );
});
