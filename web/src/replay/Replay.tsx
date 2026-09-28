import {
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
} from "react";
import { Clock, useClock } from "./clock";
import { Controls } from "./Controls";
import { Deck2D } from "./Deck2D";
import { buildModel, originName } from "./model";
import { StateCache, eventLine, mixStrokes } from "./state";
import {
  buildTimeline,
  defaultSpeed,
  dryTicksOf,
  frameAt,
  makeFrame,
  ticksOf,
  timeOfStep,
  type Frame,
  type Timeline,
} from "./timeline";
import { DeckLoader } from "./DeckLoader";
import { importChunk } from "../lib/chunks";
import styles from "./Replay.module.css";
import type { Highlight, ReplayData } from "./types";

/* three.js and react-three-fiber load only when a replay is on the page. A chunk gone stale
   under a deploy reloads the page once (lib/chunks.ts). */
const Deck3D = lazy(() =>
  importChunk(() => import("./Deck3D")).then((m) => ({ default: m.Deck3D })),
);

export type ReplayView = "both" | "2d" | "3d";

/* The deck replay, drawn from the export the API serves, in two synchronised views, played
   as motion: a clock over the run, the pipette travelling its path between the wells the
   ledger names, the volumes moving between the states the ledger knows (timeline.ts).

   `step` is the event in motion, 0 to `data.events.length` (the run is over). The parent may
   hold it (pass `step` and `onStep`): a finding's "show in the replay" sets it to
   `stepOfFinding(data, finding)`, which lands at the start of that event's motion, and
   passes the finding's wells as `highlight`; `onStep` is called as the clock crosses each
   event. Without `step` the component keeps its own. `speed` is 0.5 to 8 (the default plays
   about 300 events a minute); `onClock` hands the parent the clock (seek in seconds, play, pause) and the timeline. */
export function Replay({
  data,
  step: stepProp,
  onStep,
  view = "both",
  highlight,
  autoFocus,
  autoPlay,
  speed: speedProp,
  onClock,
}: {
  data: ReplayData;
  step?: number;
  onStep?: (step: number) => void;
  view?: ReplayView;
  highlight?: Highlight | null;
  autoFocus?: boolean;
  autoPlay?: boolean; // play from the start on mount (not for a reader who asked for reduced motion)
  speed?: number;
  onClock?: (clock: Clock, timeline: Timeline) => void; // the clock and the run's timing, for a page that drives them (the lab, a script)
}) {
  const model = useMemo(() => buildModel(data), [data]);
  const cache = useMemo(() => new StateCache(data), [data]);
  const timeline = useMemo(() => buildTimeline(model, cache), [model, cache]);
  const count = model.count;
  const frame = useMemo<Frame>(() => makeFrame(cache), [cache]);
  const clock = useMemo(
    () => new Clock(timeline.total, speedProp ?? defaultSpeed(timeline)),
    [timeline, speedProp],
  );
  useEffect(() => () => clock.dispose(), [clock]);
  useEffect(() => onClock?.(clock, timeline), [onClock, clock, timeline]);
  const version = useClock(clock);
  // one frame per clock tick: memoised on the clock's version, so a render that runs twice
  // (Strict Mode, concurrent rendering) reads the same frame and computes nothing
  useMemo(
    () => frameAt(model, timeline, cache, clock.time, frame),
    [model, timeline, cache, clock, frame, version],
  );
  const step = frame.event;

  // The parent's step: applied when it changes, and reported as the clock crosses events.
  const applied = useRef<number | undefined>(undefined);
  useEffect(() => {
    if (stepProp === undefined || stepProp === applied.current) return;
    applied.current = stepProp;
    clock.pause();
    clock.seek(timeOfStep(timeline, stepProp));
  }, [stepProp, clock, timeline]);
  // Play from the start when the page opens on the replay, so it is seen moving at once.
  useEffect(() => {
    if (!autoPlay || prefersReducedMotion()) return;
    clock.seek(0);
    clock.play();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clock]);
  const reported = useRef(-1);
  useEffect(() => {
    if (reported.current === step) return;
    reported.current = step;
    applied.current = step; // our own report must not come back as a seek
    onStep?.(step);
  }, [step, onStep]);

  const setStep = useCallback(
    (n: number) => {
      clock.pause();
      clock.seek(timeOfStep(timeline, n));
    },
    [clock, timeline],
  );

  const event = step < count ? data.events[step] : null;
  const mixes = useMemo(() => mixStrokes(data), [data]);
  const line = event
    ? eventLine(model, event, frame.state, mixes.get(step))
    : count
      ? `end of run · ${count} events`
      : "No events: the protocol moved nothing.";
  const ticks = useMemo(() => ticksOf(data, timeline), [data, timeline]);
  const dry = useMemo(
    () => dryTicksOf(model, cache, timeline),
    [model, cache, timeline],
  );
  const marks = useMemo(
    () =>
      timeline.total > 0
        ? data.findings
            .filter((f) => f.root_event != null)
            .map((f) => timeline.start[f.root_event!] / timeline.total)
        : [],
    [data, timeline],
  );

  // The close-up follows the pipette unless a labware was pinned by clicking it.
  const [pinned, setPinned] = useState<string | null>(null);

  const onKey = (e: KeyboardEvent<HTMLDivElement>) => {
    const tag = (e.target as HTMLElement).tagName;
    if (tag === "SELECT" || tag === "INPUT" || tag === "BUTTON") return;
    if (e.key === "ArrowRight") setStep(Math.min(count, step + 1));
    else if (e.key === "ArrowLeft") setStep(Math.max(0, step - 1));
    else if (e.key === "Home") setStep(0);
    else if (e.key === "End") setStep(count);
    else if (e.key === " ") clock.toggle();
    else return;
    e.preventDefault();
  };

  const legend = data.origins;
  return (
    <div
      className={`${styles.replay} ${styles[`view_${view}`]}`}
      tabIndex={0}
      onKeyDown={onKey}
      aria-label="The deck replay"
      data-step={step}
      data-time={clock.time.toFixed(2)}
      data-phase={frame.phase}
    >
      <Controls
        time={clock.time}
        duration={timeline.total}
        step={step}
        count={count}
        playing={clock.playing}
        speed={clock.speed}
        line={line}
        ticks={ticks}
        marks={marks}
        dry={dry}
        onSeek={(t) => clock.seek(t)}
        onStep={setStep}
        onPlay={(on) => (on ? clock.play() : clock.pause())}
        onSpeed={(s) => clock.setSpeed(s)}
      />
      <div className={styles.views}>
        {view !== "3d" && (
          <div className={styles.view2d}>
            <Deck2D
              model={model}
              frame={frame}
              selected={pinned}
              onSelect={(id) => setPinned((p) => (p === id ? null : id))}
              highlight={highlight}
              playing={clock.playing}
            />
            {pinned && (
              <button
                type="button"
                className={styles.follow}
                onClick={() => setPinned(null)}
              >
                Follow the pipette again
              </button>
            )}
          </div>
        )}
        {view !== "2d" && (
          <div className={styles.view3d}>
            <Suspense fallback={<DeckLoader />}>
              <Deck3D
                model={model}
                timeline={timeline}
                frame={frame}
                version={version}
                playing={clock.playing}
                highlight={highlight}
                onSelect={(id) => setPinned(id)}
              />
            </Suspense>
          </div>
        )}
      </div>
      {legend.length > 0 && (
        <ul className={styles.legend} aria-label="Liquids">
          {legend.length <= 12 ? (
            legend.map((o, i) => (
              <li key={i}>
                <span
                  className={styles.swatch}
                  style={{ background: o.colour }}
                />
                {originName(o)}
                <span className="faint"> · {o.place}</span>
              </li>
            ))
          ) : (
            <li
              title={legend
                .map((o) => `${originName(o)} · ${o.place}`)
                .join("\n")}
            >
              <span className={styles.bar} aria-hidden="true">
                {legend.map((o, i) => (
                  <span key={i} style={{ background: o.colour }} />
                ))}
              </span>
              {legend.length} liquids
            </li>
          )}
          <li title="carry-over, no volume">
            <span className={`${styles.swatch} ${styles.swatchFilm}`} /> film
            only
          </li>
          <li title="the ledger has no state for it; hover a well for its amount">
            <span className={`${styles.swatch} ${styles.swatchUntracked}`} />{" "}
            not tracked
          </li>
        </ul>
      )}
      {autoFocus && <AutoFocus />}
    </div>
  );
}

function AutoFocus() {
  const ref = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    ref.current?.parentElement?.focus({ preventScroll: true });
  }, []);
  return <span ref={ref} hidden />;
}

function prefersReducedMotion(): boolean {
  return (
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}
