/* The state at a step, rebuilt from the deltas the way provette/view/replay.js and
   provette.view.export.replay_deltas do it: step p means events 0 .. p-1 have happened.

   A checkpoint (a full copy of the three maps) is kept every `cache_every` events the first
   time it is passed, so a seek costs one clone of a few hundred entries plus at most
   `cache_every` deltas; stepping forward by one applies one delta to a clone. Nothing here
   is allocated per frame: the views call `at(step)` when the step changes. */

import { ul } from "../lib/format";
import { originName } from "./model";
import type { Band, WellRow } from "../lib/api";
import type {
  ReplayData,
  ReplayEvent,
  ReplayModel,
  TipStatus,
  WellFill,
} from "./types";

export interface ReplayState {
  step: number;
  wells: Map<number, WellRow>;
  racks: Map<number, TipStatus>;
  tips: Map<number, Band[]>; // residue: [origin, certain] per origin the tip has touched
}

function clone(s: ReplayState, step: number): ReplayState {
  return {
    step,
    wells: new Map(s.wells),
    racks: new Map(s.racks),
    tips: new Map(s.tips),
  };
}

export function applyDelta(
  state: ReplayState,
  delta: ReplayData["deltas"][number],
): void {
  if (!delta) return;
  if (delta.wells)
    for (const k in delta.wells) state.wells.set(Number(k), delta.wells[k]);
  if (delta.racks)
    for (const [i, status] of delta.racks)
      state.racks.set(i, status as TipStatus);
  if (delta.tips)
    for (const k in delta.tips) state.tips.set(Number(k), delta.tips[k]);
}

export class StateCache {
  readonly data: ReplayData;
  private readonly checkpoints: ReplayState[];
  private readonly every: number;
  private last: ReplayState | null = null;

  constructor(data: ReplayData) {
    this.data = data;
    this.every = Math.max(1, data.cache_every || 50);
    const wells = new Map<number, WellRow>();
    for (const k in data.initial) wells.set(Number(k), data.initial[k]);
    this.checkpoints = [{ step: 0, wells, racks: new Map(), tips: new Map() }];
  }

  get count(): number {
    return this.data.events.length;
  }

  /* The state at `step`, clamped to [0, events]. Returns a fresh object each time; the caller
     keeps it as long as it needs it. */
  at(step: number): ReplayState {
    const p = Math.max(0, Math.min(this.count, Math.floor(step)));
    if (this.last && p === this.last.step + 1) {
      const next = clone(this.last, p);
      applyDelta(next, this.data.deltas[p - 1]);
      this.last = next;
      return next;
    }
    const j = Math.floor(p / this.every);
    while (this.checkpoints.length <= j) {
      const from = (this.checkpoints.length - 1) * this.every;
      const s = clone(
        this.checkpoints[this.checkpoints.length - 1],
        from + this.every,
      );
      for (let i = from; i < from + this.every && i < this.count; i++)
        applyDelta(s, this.data.deltas[i]);
      this.checkpoints.push(s);
    }
    const out = clone(this.checkpoints[j], p);
    for (let k = j * this.every; k < p; k++)
      applyDelta(out, this.data.deltas[k]);
    this.last = out;
    return out;
  }
}

/* A well holding anything is drawn at least this full (a quarter), so 10 µl in a well rated
   200 µl (a PCR reaction) is a band a person can see across the room and not one pixel; the
   words give the number, and the stage's caption says so. A drawing rule, like a map's
   minimum line width, not a claim about the liquid. It holds for a well or a tube rated
   under a millilitre; a trough or a bigger tube is drawn at its true level, because there
   the level is the point (200 µl in a 15 ml trough is a trough about to run dry, and a
   quarter-full drawing would hide that), never thinner than a line (MIN_LINE of the depth). */
export const MIN_FILL = 0.25;
export const MIN_FILL_UNDER_UL = 1000;
export const MIN_LINE = 0.015;

/* The ledger's own volume-to-height table for a well: rows of [µl, mm] rising from [0, 0] to
   the brim, read as provette.state.contact.surface_mm reads it: a straight line between two
   rows, the brim's height past the last row. */
export type HeightTable = [number, number][];
export function heightAt(table: HeightTable, volume: number): number {
  const v = Math.max(0, volume);
  const last = table[table.length - 1];
  if (v >= last[0]) return last[1];
  let i = 1;
  while (i < table.length - 1 && table[i][0] <= v) i++;
  const [v0, h0] = table[i - 1];
  const [v1, h1] = table[i];
  return v1 === v0 ? h0 : h0 + ((h1 - h0) * (v - v0)) / (v1 - v0);
}

/* What the drawing needs of a well's real shape: its depth and its table. */
export interface WellShape {
  depth: number;
  table: HeightTable;
}
export function shapeOf(
  g:
    | { depth: number | null; height_at_ul?: HeightTable | null }
    | null
    | undefined,
): WellShape | null {
  return g && g.height_at_ul && g.height_at_ul.length > 1 && g.depth
    ? { depth: g.depth, table: g.height_at_ul }
    : null;
}

/* What a well's row means to a drawing: the fill fraction, the bands and their shares, the
   films. Mirrors `drawWell` in provette/view/replay.js: a bulk arrival of unknown amount shares
   the height equally; an unknown total shows the lower bound, or a third of the well. With
   the well's shape the fraction is the ledger's own height for the volume over the depth;
   without it, the volume over the rated maximum. */
export function wellFill(
  data: ReplayData,
  row: WellRow | null | undefined,
  max: number | null | undefined,
  shape?: WellShape | null,
): WellFill | null {
  if (!row) return null;
  const [volume, minVolume, bands] = row;
  const cap = max || 0;
  const level = (ul: number) =>
    shape
      ? Math.min(1, heightAt(shape.table, ul) / shape.depth)
      : Math.min(1, ul / cap);
  const sized = Boolean(shape) || cap > 0;
  let fraction: number;
  if (volume === null)
    fraction = sized && minVolume ? level(minVolume ?? 0) : 0.35;
  else
    fraction = sized ? (volume > 0 ? level(volume) : 0) : volume > 0 ? 0.5 : 0;
  const floor = cap > 0 && cap >= MIN_FILL_UNDER_UL ? MIN_LINE : MIN_FILL;
  if (volume !== null && volume > 0 && fraction < floor) fraction = floor;
  const bulk = bands.filter((b) => b[2] === 0);
  const known = bulk.reduce((a, b) => a + (b[1] === null ? 0 : b[1]), 0);
  const unknownCount = bulk.filter((b) => b[1] === null).length;
  const unit = unknownCount ? (known > 0 ? known / bulk.length : 1) : 0;
  const total = known + unit * unknownCount;
  const out: WellFill["bands"] = [];
  let r = 0;
  let g = 0;
  let bl = 0;
  for (const b of bulk) {
    const weight = b[1] === null ? unit : b[1];
    const share = total > 0 ? weight / total : 1 / bulk.length;
    const colour = data.origins[b[0]]?.colour ?? "#888888";
    out.push({
      origin: b[0],
      colour,
      share,
      certain: b[3] === 1,
      unknown: b[1] === null,
    });
    const [cr, cg, cb] = rgb(colour);
    r += cr * share;
    g += cg * share;
    bl += cb * share;
  }
  const films = bands
    .filter((b) => b[2] === 1)
    .map((b) => ({
      origin: b[0],
      colour: data.origins[b[0]]?.colour ?? "#888888",
      certain: b[3] === 1,
    }));
  const blended = out.length
    ? hex(r, g, bl)
    : films.length
      ? films[0].colour
      : "#888888";
  return {
    volume,
    minVolume: minVolume ?? 0,
    fraction,
    bands: out,
    films,
    blended,
  };
}

export function rgb(colour: string): [number, number, number] {
  const m = /^#?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(colour.trim());
  if (!m) return [136, 136, 136];
  return [parseInt(m[1], 16), parseInt(m[2], 16), parseInt(m[3], 16)];
}

function hex(r: number, g: number, b: number): string {
  const two = (n: number) =>
    Math.max(0, Math.min(255, Math.round(n)))
      .toString(16)
      .padStart(2, "0");
  return `#${two(r)}${two(g)}${two(b)}`;
}

/* A colour moved part of the way (0..1) towards another: the shade at the bottom of a band
   (towards black) and the light along its surface (towards white). */
export function mixHex(colour: string, towards: string, t: number): string {
  const [r, g, b] = rgb(colour);
  const [r2, g2, b2] = rgb(towards);
  return hex(r + (r2 - r) * t, g + (g2 - g) * t, b + (b2 - b) * t);
}

/* The words for a well at a step: "Tube A3 in slot 2: 25 µl = 20 µl of master mix + 5 µl of
   sample 1. Carry-over on a tip brought: pbs." */
export function wellText(
  model: ReplayModel,
  state: ReplayState,
  index: number,
): string {
  const info = model.wells[index];
  const head = capital(wellWordsOf(model, index));
  if (info?.labware?.row.is_tiprack) {
    const st = state.racks.get(index) ?? "fresh";
    const words: Record<TipStatus, string> = {
      fresh: "a fresh tip",
      in_use: "the tip is on the pipette",
      parked: "a used tip, put back",
      gone: "the tip was used and thrown away",
    };
    return `${head}: ${words[st]}.`;
  }
  const row = state.wells.get(index);
  if (!row) return `${head}: empty.`;
  const parts: string[] = [];
  const carry: string[] = [];
  for (const b of row[2]) {
    const o = model.data.origins[b[0]];
    const name = o ? originName(o) : "a liquid";
    const sure = b[3] ? "" : " (not certain)";
    if (b[2] === 0)
      parts.push(
        `${b[1] === null ? "some" : b[1] === 0 ? "a trace of" : `${ul(b[1])} of`} ${name}${sure}`,
      );
    else carry.push(name + sure);
  }
  let text = `${head}: ${row[0] === null ? `at least ${ul(row[1])}` : ul(row[0])}`;
  if (parts.length) text += ` = ${parts.join(" + ")}`;
  if (carry.length)
    text += `. Carry-over on a tip brought: ${carry.join("; ")}`;
  return `${text}.`;
}

function wellWordsOf(model: ReplayModel, index: number): string {
  const info = model.wells[index];
  if (!info) return "a well";
  const lw = info.labware;
  if (!lw) return `${info.name} of ${info.index}`;
  if (lw.row.is_trash) return "the trash";
  if (lw.row.is_tiprack)
    return `tip ${info.name} of the rack in slot ${lw.row.slot}`;
  return `${lw.row.kind} ${info.name} in slot ${lw.row.slot}`;
}

function capital(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

/* A dry draw: an aspirate whose source well the ledger had at 0 µl before the event, so the
   tip took nothing (`held` did not grow). The well's index, or null. `before` is the state
   before the event; the earlier event's `held` is what the tip held going in. */
export function dryDraw(
  model: ReplayModel,
  event: ReplayEvent,
  before: ReplayState,
): number | null {
  if (event.op !== "aspirate" || event.targets.length === 0 || !event.held)
    return null;
  const well = event.targets[0][1];
  const row = before.wells.get(well);
  if (!row || row[0] !== 0) return null;
  const earlier =
    event.i > 0 ? model.data.events[event.i - 1]?.held : undefined;
  const heldBefore = earlier ? (earlier[0] ?? 0) : 0;
  return (event.held[0] ?? 0) <= heldBefore ? well : null;
}

/* "A1 in slot 8 is empty": where a dry draw came from, for the readouts. */
export function dryWords(model: ReplayModel, well: number): string {
  const info = model.wells[well];
  const slot = info?.labware ? ` in slot ${info.labware.row.slot}` : "";
  return `drew nothing: ${info?.name ?? "the well"}${slot} is empty`;
}

/* "Tip A1 holds 25 µl and has touched: master mix, sample 1." per channel of the event; on a
   dry draw, "Tip A1 drew nothing: A1 in slot 8 is empty; it holds 0 µl and is clean." */
export function tipWords(
  model: ReplayModel,
  event: ReplayEvent,
  state: ReplayState,
  before?: ReplayState,
): string {
  const parts: string[] = [];
  const dry = before ? dryDraw(model, event, before) : null;
  event.targets.forEach((t, k) => {
    if (t[0] === null) return;
    const residue = state.tips.get(t[0]) ?? [];
    const name = model.wells[t[0]]?.name ?? "?";
    const names = residue.map(
      (r) =>
        (model.data.origins[r[0]]
          ? originName(model.data.origins[r[0]])
          : "a liquid") + (r[1] ? "" : " (not certain)"),
    );
    const held = event.held ? event.held[k] : 0;
    const touched =
      names.length > 5
        ? `${names.slice(0, 5).join(", ")} and ${names.length - 5} more`
        : names.join(", ");
    const holds = `holds ${ul(held)}${names.length ? ` and has touched: ${touched}` : " and is clean"}.`;
    parts.push(
      dry !== null
        ? `Tip ${name} ${dryWords(model, dry)}; it ${holds}`
        : `Tip ${name} ${holds}`,
    );
  });
  if (parts.length > 1)
    return `${parts[0]} (${parts.length} tips; the first is described.)`;
  return parts.join(" ");
}

/* "line 34 · aspirate 5 µl of sample 1 from tube A3 in slot 2, tip A1": the export's own line,
   with the liquids the source well holds named on an aspirate, read from the state before the
   event (what the tip is about to draw). */
/* The strokes of every mix: for event i inside a `mix(...)`, which stroke of how many. A
   stroke is an aspirate and its dispense in the same well by the same tip; consecutive
   strokes with no other move between them are one mix. */
export interface MixStroke {
  stroke: number; // 1-based
  strokes: number;
  volume: number | null;
  well: number; // well index
}
export function mixStrokes(data: ReplayData): Map<number, MixStroke> {
  const out = new Map<number, MixStroke>();
  const events = data.events;
  let i = 0;
  while (i < events.length) {
    const e = events[i];
    const isStroke = (x: ReplayEvent) =>
      (x.parent as unknown) === "mix" &&
      (x.op === "aspirate" || x.op === "dispense") &&
      x.targets.length > 0;
    if (!isStroke(e)) {
      i++;
      continue;
    }
    const well = e.targets[0][1];
    const tip = e.targets[0][0];
    let j = i;
    while (
      j < events.length &&
      isStroke(events[j]) &&
      events[j].targets[0][1] === well &&
      events[j].targets[0][0] === tip
    )
      j++;
    const group = events.slice(i, j);
    const strokes =
      group.filter((x) => x.op === "aspirate").length ||
      Math.ceil(group.length / 2);
    let stroke = 0;
    for (let k = i; k < j; k++) {
      if (events[k].op === "aspirate" || k === i) stroke++;
      out.set(k, {
        stroke: Math.min(stroke, strokes),
        strokes,
        volume: events[k].vol,
        well,
      });
    }
    i = j;
  }
  return out;
}

export function eventLine(
  model: ReplayModel,
  event: ReplayEvent,
  before: ReplayState,
  mix?: MixStroke,
): string {
  const dry = dryDraw(model, event, before);
  if (dry !== null) {
    // "line 144 · drew nothing: A1 in slot 8 is empty · asked for 100 µl, 8 tips"
    const tips =
      event.targets.length > 1 ? `, ${event.targets.length} tips` : "";
    const words = `${dryWords(model, dry)} · asked for ${event.vol != null ? ul(event.vol) : "an unknown amount"}${tips}`;
    return event.line !== null ? `line ${event.line} · ${words}` : words;
  }
  if (mix) {
    const w = model.wells[mix.well];
    const where = w?.labware
      ? `${w.name} (slot ${w.labware.row.slot})`
      : (w?.name ?? "the well");
    const words = `mix ${mix.strokes} × ${mix.volume != null ? ul(mix.volume) : "?"} in ${where} · stroke ${mix.stroke} of ${mix.strokes}`;
    return event.line !== null ? `line ${event.line} · ${words}` : words;
  }
  let text = event.text;
  if (event.op === "aspirate" && event.targets.length) {
    const row = before.wells.get(event.targets[0][1]);
    const names = row
      ? row[2]
          .filter((b) => b[2] === 0)
          .map((b) =>
            model.data.origins[b[0]]
              ? originName(model.data.origins[b[0]])
              : "a liquid",
          )
      : [];
    if (names.length) {
      const shown =
        names.length > 3
          ? `${names.slice(0, 3).join(", ")} and ${names.length - 3} more`
          : names.join(", ");
      text = text.replace(
        /^aspirate (\S+ µl|an unknown amount) from/,
        `aspirate $1 of ${shown} from`,
      );
    }
  }
  return event.line !== null ? `line ${event.line} · ${text}` : text;
}

/* The step a finding jumps to: the event that did the damage, at the start of its motion, so
   that pressing play shows it happen. A finding with no event lands at the end of the run. */
export function stepOfFinding(
  data: ReplayData,
  finding: { root_event?: number | null },
): number {
  return finding.root_event == null ? data.events.length : finding.root_event;
}
