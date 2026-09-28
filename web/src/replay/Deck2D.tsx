import { memo, useId, useMemo, useState } from "react";
import { ul } from "../lib/format";
import { labwareTitle, pipetteMaxOf, wellSize } from "./model";
import {
  mixHex,
  shapeOf,
  tipWords,
  wellFill,
  wellText,
  type ReplayState,
  type WellShape,
} from "./state";
import { binSpot, type LabwarePlacement } from "./scene";
import {
  drawnChannels,
  easeInOut,
  isMixStroke,
  racksAt,
  rowAt,
  type Frame,
} from "./timeline";
import styles from "./Deck2D.module.css";
import type {
  Highlight,
  LabwareModel,
  ReplayEvent,
  ReplayModel,
  TipStatus,
  WellFill,
  WellRow,
} from "./types";

/* The 2D view: the deck seen from above as its grid of slots with the gantry over it, and a
   close-up of one labware drawn to proportion from its definition, every well filled with
   what it holds at this moment, the pipette moving over it along its path. The wells use the
   plate map's language (PlateGrid): a white well, a ring, stacked bands of the liquids'
   colours that grow and shrink as the tip works, a dashed orange ring for carry-over. Hover
   a well to read it in words. */
export function Deck2D({
  model,
  frame,
  selected,
  onSelect,
  highlight,
  playing = false,
}: {
  model: ReplayModel;
  frame: Frame;
  selected: string | null; // a pinned labware's id; null follows the pipette
  onSelect: (id: string) => void;
  highlight?: Highlight | null;
  playing?: boolean; // the readout is read aloud only when the clock is still
}) {
  const [hover, setHover] = useState<number | null>(null);
  const event: ReplayEvent | null =
    frame.event < model.count ? model.data.events[frame.event] : null;
  const state = frame.state;
  // The close-up shows the pinned labware, else the bin while a tip drops or a tip empties
  // into it, else the labware the pipette is going to (the last one with wells, so the plate
  // comes back after the drop), else the first.
  const labware =
    (selected && model.byId.get(selected)) ||
    binTarget(model, event) ||
    followed(model, frame.event) ||
    model.labware.find((l) => !l.row.is_trash) ||
    null;
  const acted = useMemo(
    () =>
      new Set(
        event && frame.phase === "action" ? event.targets.map((t) => t[1]) : [],
      ),
    [event, frame.phase],
  );
  const marked = useMemo(() => new Set(highlight?.wells ?? []), [highlight]);
  const reached = useMemo(
    () => new Set(highlight?.downstream ?? []),
    [highlight],
  );
  const readout =
    hover !== null
      ? wellText(model, state, hover)
      : event
        ? tipWords(
            model,
            event,
            frame.phase === "action" && frame.progress >= 0.5
              ? frame.after
              : state,
            state,
          )
        : "";
  return (
    <div className={styles.wrap}>
      <DeckOverview
        model={model}
        frame={frame}
        selected={labware?.row.id ?? null}
        onSelect={onSelect}
      />
      <div className={styles.closeup}>
        {labware && (
          <>
            <div
              className={styles.title}
              title={`slot ${labware.row.slot} ${labwareTitle(labware)}`}
            >
              <span className={styles.slot}>slot {labware.row.slot}</span>{" "}
              {labwareTitle(labware)}
              {!labware.row.measured && !labware.row.is_trash && (
                <span className={styles.note}>
                  {" "}
                  · well positions are a guess: no definition matched
                </span>
              )}
            </div>
            <div className={styles.stage}>
              <LabwareCloseup
                model={model}
                labware={labware}
                state={state}
                event={event}
                frame={frame}
                acted={acted}
                marked={marked}
                reached={reached}
                onHover={setHover}
              />
            </div>
          </>
        )}
        <div
          className={styles.readout}
          aria-live={playing ? "off" : "polite"}
          title={readout || undefined}
        >
          {readout}
        </div>
      </div>
    </div>
  );
}

/* The trash, when the event drops a tip into it or empties a tip into it; else null. */
function binTarget(
  model: ReplayModel,
  event: ReplayEvent | null,
): LabwareModel | null {
  if (!event || !event.targets.length) return null;
  if (
    event.op !== "drop_tip" &&
    event.op !== "dispense" &&
    event.op !== "blow_out"
  )
    return null;
  const lw = model.wells[event.targets[0][1]]?.labware;
  return lw && lw.row.is_trash ? lw : null;
}

function followed(model: ReplayModel, event: number): LabwareModel | null {
  for (let i = Math.min(event, model.count - 1); i >= 0; i--) {
    const e = model.data.events[i];
    const lw = e.targets.length ? model.wells[e.targets[0][1]]?.labware : null;
    if (lw && !lw.row.is_trash) return lw;
  }
  return null;
}

/* A row's fill, kept per row object: the state's rows never change, so the close-up's wells
   keep their props and skip their render; a live row (interpolated) is read afresh. */
const fills = new WeakMap<WellRow, WellFill>();
function fillOf(
  model: ReplayModel,
  row: WellRow | undefined,
  max: number | null,
  live: boolean,
  shape: WellShape | null = null,
): WellFill | null {
  if (!row) return null;
  if (live) return wellFill(model.data, row, max, shape);
  let f = fills.get(row);
  if (!f) {
    f = wellFill(model.data, row, max, shape)!;
    fills.set(row, f);
  }
  return f;
}

/* Every labware's hatch pattern and band gradient per liquid, once per SVG. A band is its
   liquid's colour at the top and a shade darker (SHADE) at its bottom, whatever its height
   (the gradient spans the band it fills): a drawing convention that makes a stack of bands
   read as liquid, not a claim about it. */
export const SHADE = 0.12;
export const SURFACE_LIGHT = 0.3;
export const SURFACE_LINE = 0.35; // mm of the drawing: the ring's stroke width
function Hatches({
  model,
  prefix,
  unit,
}: {
  model: ReplayModel;
  prefix: string;
  unit: number;
}) {
  return (
    <defs>
      {model.data.origins.map((o, i) => (
        <pattern
          key={i}
          id={`${prefix}-hatch-${i}`}
          width={unit}
          height={unit}
          patternUnits="userSpaceOnUse"
          patternTransform="rotate(45)"
        >
          <rect x="0" y="0" width={unit * 0.45} height={unit} fill={o.colour} />
        </pattern>
      ))}
      {model.data.origins.map((o, i) => (
        <linearGradient
          key={`g${i}`}
          id={`${prefix}-band-${i}`}
          x1="0"
          y1="0"
          x2="0"
          y2="1"
        >
          <stop offset="0" stopColor={o.colour} />
          <stop offset="1" stopColor={mixHex(o.colour, "#000000", SHADE)} />
        </linearGradient>
      ))}
      <pattern
        id={`${prefix}-parked`}
        width={unit}
        height={unit}
        patternUnits="userSpaceOnUse"
        patternTransform="rotate(45)"
      >
        <rect
          x="0"
          y="0"
          width={unit * 0.45}
          height={unit}
          className={styles.parkedStripe}
        />
      </pattern>
    </defs>
  );
}

/* The deck: twelve slots in their real layout, each labware as its footprint with its wells as
   dots in the colour of what they hold, the trash as a bin with the tips dropped in it, the
   gantry as a beam across the deck at the pipette's y with the pipette on it. Click a labware
   to open it in the close-up. */
function DeckOverview({
  model,
  frame,
  selected,
  onSelect,
}: {
  model: ReplayModel;
  frame: Frame;
  selected: string | null;
  onSelect: (id: string) => void;
}) {
  const { width: W, height: H, slots } = model.data.deck;
  const prefix = useId().replace(/:/g, "");
  const M = 3;
  const racks = racksAt(frame);
  const px = frame.x;
  const py = H - frame.y;
  const lift = 1 + 0.5 * Math.max(0, Math.min(1, frame.h / 80)); // raised: drawn larger, nearer the eye
  return (
    <svg
      viewBox={`${-M} ${-M} ${W + 2 * M} ${H + 2 * M}`}
      className={styles.deck}
      role="img"
      aria-label="The deck, seen from above"
    >
      <Hatches model={model} prefix={prefix} unit={1.4} />
      {slots.map((s) => (
        <g key={s.id} transform={`translate(${s.x},${H - s.y - s.height})`}>
          <rect
            x="0"
            y="0"
            width={s.width}
            height={s.height}
            rx="1.5"
            className={styles.slotBox}
          />
          <text
            x={s.width / 2}
            y={s.height / 2 + 6}
            textAnchor="middle"
            className={styles.slotNumber}
          >
            {s.id}
          </text>
        </g>
      ))}
      {model.labware.map((lw) => (
        <MiniLabware
          key={lw.row.id}
          model={model}
          lw={lw}
          state={frame.state}
          frame={frame}
          racks={racks}
          live={liveOf(frame, lw)}
          drops={lw.row.is_trash ? frame.drops : 0}
          waste={lw.row.is_trash ? frame.waste : 0}
          H={H}
          prefix={prefix}
          selected={lw.row.id === selected}
          onSelect={onSelect}
        />
      ))}
      <g className={styles.gantry} aria-hidden="true">
        <line x1={-M} x2={W + M} y1={py} y2={py} className={styles.beam} />
        {drawnChannels(frame).map((k) => (
          <circle
            key={k}
            cx={px + frame.ox[k]}
            cy={py - frame.oy[k]}
            r={2.2 * lift}
            className={
              frame.tipOn[k] ? styles.pipetteMarkTip : styles.pipetteMark
            }
          />
        ))}
      </g>
    </svg>
  );
}

/* The version to hand a labware: the frame's when one of its wells is live, else 0, so a
   labware the event does not touch keeps its props. */
function liveOf(frame: Frame, lw: LabwareModel): number {
  if (frame.live.size === 0) return 0;
  for (const w of lw.wells) if (frame.live.has(w.index)) return frame.version;
  return 0;
}

const MiniLabware = memo(function MiniLabware({
  model,
  lw,
  state,
  frame,
  racks,
  live,
  drops,
  waste,
  H,
  prefix,
  selected,
  onSelect,
}: {
  model: ReplayModel;
  lw: LabwareModel;
  state: ReplayState;
  frame: Frame; // the same object throughout: `live` is the version that says it changed here
  racks: ReplayState["racks"];
  live: number;
  drops: number;
  waste: number; // µl in the bin, for the trash slot
  H: number;
  prefix: string;
  selected: boolean;
  onSelect: (id: string) => void;
}) {
  const { w, h } = lw.row;
  // At overview size a labware's name is a few pixels high: the slot number is what reads, the
  // name is the hover and the close-up's title.
  const label = `${lw.row.slot}  ${labwareTitle(lw)}`;
  const size = 15;
  return (
    <g
      transform={`translate(${lw.x},${H - lw.y - h})`}
      className={`${styles.mini} ${selected ? styles.miniSelected : ""} ${lw.row.is_trash ? styles.trash : ""}`}
      onClick={() => onSelect(lw.row.id)}
      onKeyDown={(e) =>
        (e.key === "Enter" || e.key === " ") && onSelect(lw.row.id)
      }
      role="button"
      tabIndex={0}
      aria-label={`Slot ${lw.row.slot}: ${labwareTitle(lw)}`}
      data-live={live || undefined}
    >
      <rect
        x="0"
        y="0"
        width={w}
        height={h}
        rx="1.5"
        className={styles.miniBody}
      />
      {lw.wells.map((well) => {
        const g = well.geometry;
        const s = wellSize(g);
        const cx = g.x;
        const cy = h - g.y;
        if (lw.row.is_tiprack) {
          const st: TipStatus = racks.get(well.index) ?? "fresh";
          return (
            <circle
              key={well.name}
              cx={cx}
              cy={cy}
              r={s.w / 2}
              className={`${styles.miniTip} ${styles[`tip_${st}`]}`}
              fill={st === "parked" ? `url(#${prefix}-parked)` : undefined}
            />
          );
        }
        const fill = fillOf(
          model,
          live ? rowAt(frame, well.index) : state.wells.get(well.index),
          g.max,
          live > 0 && frame.live.has(well.index),
          shapeOf(g),
        );
        const colour =
          fill && fill.bands.length && fill.fraction > 0
            ? fill.blended
            : fill && fill.films.length
              ? `url(#${prefix}-hatch-${fill.films[0].origin})`
              : undefined;
        return s.round ? (
          <circle
            key={well.name}
            cx={cx}
            cy={cy}
            r={s.w / 2}
            className={styles.miniWell}
            fill={colour}
            opacity={
              fill && fill.bands.length && !fill.bands[0].certain
                ? 0.5
                : undefined
            }
          />
        ) : (
          <rect
            key={well.name}
            x={cx - s.w / 2}
            y={cy - s.h / 2}
            width={s.w}
            height={s.h}
            rx="0.6"
            className={styles.miniWell}
            fill={colour}
          />
        );
      })}
      {lw.row.is_trash && (drops > 0 || waste > 0) && (
        <text
          x={w / 2}
          y={h / 2 + 2}
          textAnchor="middle"
          className={styles.binCount}
          fontSize={6}
        >
          {drops} tip{drops === 1 ? "" : "s"}
          {waste > 0 ? ` · ${ul(waste)}` : ""}
        </text>
      )}
      <title>{label}</title>
      <text x="3" y={size + 1} className={styles.miniLabel} fontSize={size}>
        {lw.row.slot}
      </text>
    </g>
  );
});

/* One labware, large, to proportion: the wells at the positions in its definition, the
   pipette over it. Exported for the plate-map approval, which draws the map she is approving
   with this same close-up (components/PlateGrid.tsx, `asReplay`) without a frame; `proposed`
   marks wells a free group could go in. */
export function LabwareCloseup({
  model,
  labware,
  state,
  event: _event,
  frame,
  acted,
  marked,
  reached,
  proposed,
  onHover,
}: {
  model: ReplayModel;
  labware: LabwareModel;
  state: ReplayState;
  event: ReplayEvent | null; // kept for callers without a frame (the plate-map approval)
  frame?: Frame;
  acted: Set<number>;
  marked: Set<number>;
  reached: Set<number>;
  proposed?: Set<number>;
  onHover: (i: number | null) => void;
}) {
  const prefix = useId().replace(/:/g, "");
  const { w, h } = labware.row;
  const axes = useMemo(() => axesOf(labware), [labware]);
  // one tab stop per plate: the focused well, else the first named one; arrows move between wells
  const named = useMemo(
    () => labware.wells.filter((wl) => wl.index >= 0),
    [labware],
  );
  const [focusedWell, setFocusedWell] = useState<number>(-1);
  const stop = named.some((wl) => wl.index === focusedWell)
    ? focusedWell
    : (named[0]?.index ?? -1);
  const onArrow = (e: React.KeyboardEvent<SVGSVGElement>) => {
    if (
      !["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(e.key) ||
      named.length === 0
    )
      return;
    const at = Math.max(
      0,
      named.findIndex((wl) => wl.index === stop),
    );
    const cur = named[at];
    const step = (dx: number, dy: number) => {
      // the nearest well in that direction, by the definition's positions (y grows to the back)
      let best: { wl: (typeof named)[number]; d: number } | null = null;
      for (const wl of named) {
        const ddx = wl.geometry.x - cur.geometry.x;
        const ddy = wl.geometry.y - cur.geometry.y;
        if (
          (dx && Math.sign(ddx) !== dx) ||
          (dy && Math.sign(ddy) !== dy) ||
          (dx && Math.abs(ddy) > 1) ||
          (dy && Math.abs(ddx) > 1)
        )
          continue;
        const d = Math.hypot(ddx, ddy);
        if (d > 0 && (!best || d < best.d)) best = { wl, d };
      }
      return best?.wl ?? cur;
    };
    const next =
      e.key === "ArrowRight"
        ? step(1, 0)
        : e.key === "ArrowLeft"
          ? step(-1, 0)
          : e.key === "ArrowUp"
            ? step(0, 1)
            : step(0, -1);
    setFocusedWell(next.index);
    onHover(next.index);
    (
      e.currentTarget.querySelector(
        `[data-index="${next.index}"]`,
      ) as SVGElement | null
    )?.focus();
    e.preventDefault();
  };
  const PAD_L = axes ? 7 : 1;
  const PAD_T = axes ? 6 : 1;
  const racks = frame ? racksAt(frame) : state.racks;
  // the pipette, when it is over this labware (or within 12 mm of it): one tip per channel
  // with a point of its own (channels collapsed on one short well draw as one tip)
  const pipette: { x: number; y: number; k: number }[] = [];
  if (frame && frame.event >= 0) {
    for (const k of drawnChannels(frame)) {
      const x = frame.x + frame.ox[k] - labware.x;
      const y = frame.y + frame.oy[k] - labware.y;
      if (x > -12 && x < w + 12 && y > -12 && y < h + 12)
        pipette.push({ x, y: h - y, k });
    }
  }
  const lift = frame
    ? 1 + 0.6 * Math.max(0, Math.min(1, (frame.h - labware.depth) / 60))
    : 1;
  // a mix: the well being pumped gets a swirl, so three strokes read as mixing, not a mistake
  const mixing =
    _event && isMixStroke(_event) && frame && frame.phase === "action"
      ? new Set(_event.targets.map((t) => t[1]))
      : null;
  return (
    <svg
      viewBox={`${-PAD_L} ${-PAD_T} ${w + PAD_L + 1} ${h + PAD_T + 1}`}
      className={styles.svg}
      role="img"
      aria-label={`Close-up of slot ${labware.row.slot}: ${labwareTitle(labware)}`}
      onMouseLeave={() => onHover(null)}
      onKeyDown={onArrow}
    >
      <Hatches model={model} prefix={prefix} unit={1} />
      <rect x="0" y="0" width={w} height={h} rx="2" className={styles.body} />
      {axes?.cols.map((c) => (
        <text
          key={`c${c.label}`}
          x={c.x}
          y={-2}
          textAnchor="middle"
          className={styles.axis}
        >
          {c.label}
        </text>
      ))}
      {axes?.rows.map((r) => (
        <text
          key={`r${r.label}`}
          x={-3}
          y={h - r.y + 1.2}
          textAnchor="middle"
          className={styles.axis}
        >
          {r.label}
        </text>
      ))}
      {labware.wells.map((well) => {
        const live = frame ? frame.live.has(well.index) : false;
        const row = frame
          ? rowAt(frame, well.index)
          : state.wells.get(well.index);
        return (
          <Well2D
            key={well.name}
            prefix={prefix}
            model={model}
            index={well.index}
            name={well.name}
            geometry={well.geometry}
            cx={well.geometry.x}
            cy={h - well.geometry.y}
            tiprack={labware.row.is_tiprack}
            status={racks.get(well.index) ?? "fresh"}
            fill={
              labware.row.is_tiprack
                ? null
                : fillOf(
                    model,
                    row,
                    well.geometry.max,
                    live,
                    shapeOf(well.geometry),
                  )
            }
            acted={acted.has(well.index)}
            marked={marked.has(well.index)}
            reached={reached.has(well.index)}
            proposed={proposed?.has(well.index) ?? false}
            tabStop={well.index === stop}
            onHover={(i) => {
              if (i != null) setFocusedWell(i);
              onHover(i);
            }}
          />
        );
      })}
      {mixing &&
        labware.wells
          .filter((well) => mixing.has(well.index))
          .map((well) => {
            const s = wellSize(well.geometry);
            return (
              <MixMark
                key={`mix-${well.name}`}
                cx={well.geometry.x}
                cy={h - well.geometry.y}
                r={s.w / 2}
              />
            );
          })}
      {labware.row.is_trash && frame && (
        <BinContents
          w={w}
          h={h}
          frame={frame}
          event={_event}
          pipette={pipette}
        />
      )}
      {frame &&
        pipette.map(({ x, y, k }, j) => (
          <PipetteTip
            key={k}
            frame={frame}
            channel={k}
            x={x}
            y={y}
            scale={(pipette.length > 1 ? 0.55 : 1) * lift}
            label={pipette.length === 1 || j === 0 || j === pipette.length - 1}
            pipetteMax={pipetteMaxOf(model)}
          />
        ))}
    </svg>
  );
}

/* Row letters down the side and column numbers across the top, from the wells' names and
   positions, when the names are of the A1 kind. */
function axesOf(lw: LabwareModel): {
  rows: { label: string; y: number }[];
  cols: { label: string; x: number }[];
} | null {
  const rows = new Map<string, number>();
  const cols = new Map<string, number>();
  for (const w of lw.wells) {
    const m = /^([A-Z]+)(\d+)$/.exec(w.name);
    if (!m) return null;
    if (!rows.has(m[1])) rows.set(m[1], w.geometry.y);
    if (!cols.has(m[2])) cols.set(m[2], w.geometry.x);
  }
  if (rows.size === 0) return null;
  return {
    rows: [...rows].map(([label, y]) => ({ label, y })),
    cols: [...cols].map(([label, x]) => ({ label, x })),
  };
}

const Well2D = memo(function Well2D({
  prefix,
  model,
  index,
  name,
  geometry,
  cx,
  cy,
  tiprack,
  status,
  fill,
  acted,
  marked,
  reached,
  proposed = false,
  tabStop = false,
  onHover,
}: {
  prefix: string;
  model: ReplayModel;
  index: number;
  name: string;
  geometry: LabwareModel["wells"][number]["geometry"];
  cx: number;
  cy: number;
  tiprack: boolean;
  status: TipStatus;
  fill: WellFill | null;
  acted: boolean;
  marked: boolean;
  reached: boolean;
  proposed?: boolean;
  tabStop?: boolean; // the plate's one tab stop (roving); the others are reached with the arrows
  onHover: (i: number | null) => void;
}) {
  const s = wellSize(geometry);
  const x0 = cx - s.w / 2;
  const y0 = cy - s.h / 2;
  const clipId = `${prefix}-clip-${name}`;
  const shape = s.round ? (
    <circle cx={cx} cy={cy} r={s.w / 2} />
  ) : (
    <rect x={x0} y={y0} width={s.w} height={s.h} rx="0.6" />
  );
  const fillH = fill ? s.h * fill.fraction : 0;
  // A well with any liquid gets a ring in its liquid's colour, so a full plate reads as full
  // from across the room; the band inside says how much.
  const held = Boolean(
    fill &&
    fill.bands.length &&
    fillH > 0 &&
    !acted &&
    !marked &&
    !reached &&
    !proposed,
  );
  const classes = [
    styles.well,
    acted ? styles.acted : "",
    marked ? styles.marked : "",
    reached ? styles.reached : "",
    proposed ? styles.proposed : "",
    held ? styles.held : "",
  ].join(" ");
  // the bands, stacked from the bottom: each one's top edge
  const tops: number[] = [];
  if (fill) {
    let y = y0 + s.h;
    for (const b of fill.bands) {
      y -= fillH * b.share;
      tops.push(y);
    }
  }
  return (
    <g
      className={classes}
      onMouseEnter={() => index >= 0 && onHover(index)}
      onFocus={() => index >= 0 && onHover(index)}
      onClick={() => index >= 0 && onHover(index)}
      tabIndex={index >= 0 ? (tabStop ? 0 : -1) : undefined}
      role={index >= 0 ? "button" : undefined}
      aria-label={`${tiprack ? "Tip" : "Well"} ${name}`}
      data-well={name}
      data-index={index >= 0 ? index : undefined}
      data-acted={acted || undefined}
      data-volume={
        fill && fill.volume != null
          ? Math.round(fill.volume * 100) / 100
          : undefined
      }
    >
      <clipPath id={clipId}>{shape}</clipPath>
      {s.round ? (
        <circle cx={cx} cy={cy} r={s.w / 2} className={styles.wellBg} />
      ) : (
        <rect
          x={x0}
          y={y0}
          width={s.w}
          height={s.h}
          rx="0.6"
          className={styles.wellBg}
        />
      )}
      {tiprack && (status === "fresh" || status === "parked") && (
        <rect
          x={x0}
          y={y0}
          width={s.w}
          height={s.h}
          className={styles[`tip_${status}`]}
          fill={status === "parked" ? `url(#${prefix}-parked)` : undefined}
          clipPath={`url(#${clipId})`}
        />
      )}
      {fill && fillH > 0 && (
        <g clipPath={`url(#${clipId})`}>
          {fill.bands.map((b, i) => (
            <rect
              key={i}
              x={x0}
              y={tops[i]}
              width={s.w}
              height={fillH * b.share}
              fill={`url(#${prefix}-band-${b.origin})`}
              opacity={b.certain ? 1 : 0.45}
              data-band={model.data.origins[b.origin]?.name}
            />
          ))}
          {fill.bands.length > 0 && (
            // the surface: a thin lighter line along the top band's top edge
            <rect
              x={x0}
              y={tops[tops.length - 1]}
              width={s.w}
              height={SURFACE_LINE}
              fill={mixHex(
                fill.bands[fill.bands.length - 1].colour,
                "#ffffff",
                SURFACE_LIGHT,
              )}
              opacity={fill.bands[fill.bands.length - 1].certain ? 1 : 0.45}
              data-surface=""
            />
          )}
          {fill.films.map((f, i) => {
            const top = Math.max(fillH, s.h * 0.3);
            const sw = s.w / fill.films.length;
            return (
              <rect
                key={`f${i}`}
                x={x0 + i * sw}
                y={y0 + s.h - top}
                width={sw}
                height={top}
                fill={`url(#${prefix}-hatch-${f.origin})`}
                opacity={f.certain ? 1 : 0.5}
              />
            );
          })}
        </g>
      )}
      {fill &&
        fill.volume === null &&
        (s.round ? (
          <circle
            cx={cx}
            cy={cy}
            r={s.w / 2 - 0.3}
            className={styles.unknownVolume}
          />
        ) : (
          <rect
            x={x0 + 0.3}
            y={y0 + 0.3}
            width={s.w - 0.6}
            height={s.h - 0.6}
            className={styles.unknownVolume}
          />
        ))}
      {fill &&
        fill.films.length > 0 &&
        fill.bands.length > 0 &&
        (s.round ? (
          <circle cx={cx} cy={cy} r={s.w / 2 - 0.7} className={styles.carry} />
        ) : null)}
      {s.round ? (
        <circle
          cx={cx}
          cy={cy}
          r={s.w / 2}
          className={styles.ring}
          stroke={held ? fill!.blended : undefined}
        />
      ) : (
        <rect
          x={x0}
          y={y0}
          width={s.w}
          height={s.h}
          rx="0.6"
          className={styles.ring}
          stroke={held ? fill!.blended : undefined}
        />
      )}
    </g>
  );
});

/* The pipette's tip over a well, filled to what it holds (over the pipette's rated volume)
   in the colour of the liquid it drew, or the bare nozzle when no tip is on. */
function PipetteTip({
  frame,
  channel,
  x,
  y,
  scale,
  label,
  pipetteMax,
}: {
  frame: Frame;
  channel: number;
  x: number;
  y: number;
  scale: number;
  label: boolean;
  pipetteMax?: number;
}) {
  const on = frame.tipOn[channel] === 1;
  const H = (on ? 14 : 8) * scale;
  const W = 5 * scale;
  const top = y - 2.5 * scale;
  // a tip: a cone; no tip: the pipette's nozzle, a shoulder narrowing to a short stem
  const points = on
    ? `${x - W / 2},${top - H} ${x + W / 2},${top - H} ${x + W / 6},${top} ${x - W / 6},${top}`
    : `${x - W / 2},${top - H} ${x + W / 2},${top - H} ${x + W / 2},${top - H * 0.55} ${x + W / 4},${top - H * 0.4} ${x + W / 4},${top} ${x - W / 4},${top} ${x - W / 4},${top - H * 0.4} ${x - W / 2},${top - H * 0.55}`;
  const id = useId().replace(/:/g, "");
  const held = frame.held[channel];
  const max = pipetteMax ?? 300;
  const fillFraction = on ? Math.max(0, Math.min(1, held / max)) : 0;
  const [r, g, b] = frame.tipColour;
  const colour = `rgb(${Math.round(r * 255)},${Math.round(g * 255)},${Math.round(b * 255)})`;
  return (
    <g
      className={styles.pipette}
      data-tip={on ? "on" : "off"}
      data-held={Math.round(held * 100) / 100}
    >
      <clipPath id={`${id}-tipclip`}>
        <polygon points={points} />
      </clipPath>
      <polygon
        points={points}
        className={on ? styles.tipBody : styles.nozzle}
      />
      {fillFraction > 0 && (
        <rect
          x={x - W / 2}
          y={top - H * fillFraction}
          width={W}
          height={H * fillFraction}
          fill={colour}
          clipPath={`url(#${id}-tipclip)`}
        />
      )}
      <polygon points={points} className={styles.tipEdge} />
      {label && (
        <text
          x={x + W / 2 + 0.8 * scale}
          y={top - H / 2 + 1.2 * scale}
          className={styles.tipLabel}
          fontSize={3.2 * scale}
        >
          {on ? ul(held) : "no tip"}
        </text>
      )}
    </g>
  );
}

/* The bin's close-up: the tips the run has dropped so far, lying where the 3D view lays them
   (scene.binSpot on the bin's own footprint: the same spot for the same tip in both views), the count and the microlitres
   of waste, and, over the second half of a drop, the tips of this event falling from the
   pipette to their spots. Nothing but the ledger's two numbers is drawn: how many tips, how
   much liquid. */
const PILE_DRAWN = 120; // tips drawn in the pile; past that the count says the rest
function BinContents({
  w,
  h,
  frame,
  event,
  pipette,
}: {
  w: number;
  h: number;
  frame: Frame;
  event: ReplayEvent | null;
  pipette: { x: number; y: number; k: number }[];
}) {
  // the bin as a footprint centred on the drawing: scene x is svg x, scene z (towards the
  // front) is svg y, so the 3D view's spot is this spot
  const bin = { x: w / 2, z: h / 2, w, d: h } as LabwarePlacement;
  const spot = (n: number) => {
    const s = binSpot(n, bin);
    return { x: s.x, y: s.z, yaw: s.yaw };
  };
  const dropping =
    event?.op === "drop_tip" &&
    frame.phase === "action" &&
    frame.progress >= 0.5;
  const landing = dropping ? Math.max(1, frame.channels) : 0; // the tips of this event, already counted
  const settled = Math.min(PILE_DRAWN, frame.drops - landing);
  const fall = dropping ? easeInOut((frame.progress - 0.5) / 0.5) : 1;
  const from = (j: number) =>
    pipette[Math.min(j, pipette.length - 1)] ?? { x: w / 2, y: h / 2 };
  return (
    <g className={styles.bin} aria-hidden="true">
      {Array.from({ length: Math.max(0, settled) }, (_, n) => {
        const s = spot(n);
        return <DroppedTip key={n} x={s.x} y={s.y} yaw={s.yaw} />;
      })}
      {Array.from({ length: landing }, (_, j) => {
        const n = frame.drops - landing + j;
        const s = spot(n);
        const p = from(j);
        return (
          <DroppedTip
            key={`in${n}`}
            x={p.x + (s.x - p.x) * fall}
            y={p.y + (s.y - p.y) * fall}
            yaw={s.yaw * fall}
          />
        );
      })}
      {(frame.drops > 0 || frame.waste > 0) && (
        <text
          x={w / 2}
          y={h / 2 + 2}
          textAnchor="middle"
          className={styles.binCount}
          fontSize={5}
        >
          {frame.drops} tip{frame.drops === 1 ? "" : "s"}
          {frame.waste > 0 ? ` · ${ul(frame.waste)}` : ""}
        </text>
      )}
    </g>
  );
}

/* A tip lying in the bin: a slim cone on its side, turned by its yaw (radians, as the 3D view
   turns it). */
function DroppedTip({ x, y, yaw }: { x: number; y: number; yaw: number }) {
  return (
    <polygon
      points="-6,0 6,-1.6 6,1.6"
      transform={`translate(${x} ${y}) rotate(${(yaw * 180) / Math.PI})`}
      className={styles.droppedTip}
    />
  );
}

/* Two curved arrows in the well: it is being mixed, not drawn from and filled by mistake. */
function MixMark({ cx, cy, r }: { cx: number; cy: number; r: number }) {
  const k = r * 0.62;
  return (
    <g
      className={styles.mixMark}
      transform={`translate(${cx} ${cy})`}
      aria-hidden="true"
    >
      <path d={`M ${-k} 0 A ${k} ${k} 0 0 1 0 ${-k}`} />
      <path d={`M ${-k * 0.35} ${-k} L 0 ${-k} L 0 ${-k * 0.45}`} />
      <path d={`M ${k} 0 A ${k} ${k} 0 0 1 0 ${k}`} />
      <path d={`M ${k * 0.35} ${k} L 0 ${k} L 0 ${k * 0.45}`} />
    </g>
  );
}
