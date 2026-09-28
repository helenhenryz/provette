/* The motion model: the run as time, and the deck at any moment of it.

   Every event gets a duration from its kind and from how far the pipette travels to it, so a
   long move across the deck takes longer than a short one. An event is a travel (rise to the
   travel height, move over the deck, descend into the well) and then the action (the plunger
   working, the tip seating in its rack, the tip dropping into the bin). Between two known
   positions the pipette is interpolated with an ease-in-out; during an action the volumes of
   the wells the ledger says changed are interpolated between the state before and the state
   after. Nothing else moves: no droplets, no splash, no meniscus; what the ledger does not
   know is not drawn.

   Units: millimetres on the deck (x right, y towards the back, h up) and playback seconds at
   1x. `defaultSpeed` picks the speed at which about 300 events play in a minute. */

import { BASE_MM, TIP_FRACTION, pipetteMaxOf, wellOnDeck } from "./model";
import {
  dryDraw,
  rgb,
  type ReplayState,
  type StateCache,
  wellFill,
} from "./state";
import type {
  Band,
  ReplayData,
  ReplayEvent,
  ReplayModel,
  WellInfo,
  WellRow,
} from "./types";

export const CHANNELS = 8; // the most a pipette here has
export const MOUNT_GAP_MM = 34; // the OT-2's right mount sits this far to the right of the left one
export const LEFT = 1; // a mount, as the timeline keeps it: 0 when the export does not say
export const RIGHT = 2;
export const TRAVEL_CLEARANCE_MM = 15; // how far above the tallest labware the pipette travels
export const TRASH_HEIGHT_MM = 60; // the fixed trash is a bin that rises above slot 12
export const XY_SPEED = 1500; // mm per playback second at 1x
export const Z_SPEED = 500;
export const SPEEDS = [0.5, 1, 2, 4, 8];

/* Seconds an action takes at 1x, by the event's kind; a mix's strokes are quicker. */
export const ACTION_S: Record<string, number> = {
  pick_up_tip: 0.3,
  drop_tip: 0.25,
  aspirate: 0.35,
  dispense: 0.35,
  blow_out: 0.2,
  touch_tip: 0.2,
  delay: 0.5,
  pause: 0.5,
};
export const OTHER_ACTION_S = 0.15;
export const MIX_STROKE_S = 0.15;

export interface Timeline {
  count: number;
  total: number; // playback seconds at 1x
  start: Float64Array; // start[i]: when event i's motion begins; start[count] = total
  travel: Float64Array; // seconds of travel before the action
  action: Float64Array; // seconds of action
  rise: Float64Array; // the three legs of the travel, seconds
  move: Float64Array;
  fall: Float64Array;
  fx: Float64Array; // the pipette's first channel before the event: x, y, tip height
  fy: Float64Array;
  fh: Float64Array;
  tx: Float64Array; // and where the event takes it
  ty: Float64Array;
  th: Float64Array;
  travelHeight: number;
  channels: Uint8Array; // channels the event uses; an event on no well keeps the last event's
  mount: Uint8Array; // the mount that acts (LEFT, RIGHT), carried over an event that names none; 0 if the export never says
  ox: Float32Array; // per channel k of event i: offset from the first channel, [i * CHANNELS + k]
  oy: Float32Array;
  heldFrom: Float32Array; // µl in channel k before and after the event
  heldTo: Float32Array;
  tipBefore: Uint8Array; // 1 when a tip is on the pipette during the travel to event i
  tipAfter: Uint8Array; // 1 when a tip is on after event i
  tipColour: Float32Array; // rgb 0..1 of what the tip holds after event i (the last well it drew from)
  tipColourBefore: Float32Array;
  drops: Int32Array; // drops[i]: tips in the bin before event i; drops[count] at the end
  waste: Float64Array; // waste[i]: µl dispensed or blown out into the trash before event i; waste[count] at the end
  dropColour: Float32Array; // rgb of the n-th dropped tip
  pipetteMax: number; // µl: the pipette's rated volume, from its name (p20 -> 20)
  park: [number, number]; // where the pipette waits before the run
}

/* An aspirate or dispense inside a `mix(...)`: the export writes the wrapper's name in
   `parent` (provette/view/export.py `_event`: "mix", "transfer", ... or null); lib/api.ts types
   the field as a number, which it never is. */
export function isMixStroke(e: ReplayEvent): boolean {
  return (
    (e.parent as unknown) === "mix" &&
    (e.op === "aspirate" || e.op === "dispense")
  );
}

export function easeInOut(p: number): number {
  const x = Math.max(0, Math.min(1, p));
  return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
}

/* The tip's point when the event acts in a well: at the liquid's level (the lower of the volume
   before and after, which is what the ledger knows), never under 1 mm from the bottom; in a
   tip rack, where the seated tip's point is; over the trash, above its rim. */
function actionHeight(
  model: ReplayModel,
  before: ReplayState,
  after: ReplayState,
  wellIndex: number,
): number {
  const info = model.wells[wellIndex];
  const lw = info?.labware;
  if (!lw) return TRAVEL_CLEARANCE_MM;
  if (lw.row.is_trash) return TRASH_HEIGHT_MM + 10;
  const depth = info.geometry?.depth ?? lw.depth;
  if (lw.row.is_tiprack) return BASE_MM + depth * (1 - TIP_FRACTION);
  const a = wellFill(
    model.data,
    before.wells.get(wellIndex),
    info.geometry?.max,
  );
  const b = wellFill(
    model.data,
    after.wells.get(wellIndex),
    info.geometry?.max,
  );
  const level =
    Math.min(
      a?.bands.length ? a.fraction : 0,
      b?.bands.length ? b.fraction : 0,
    ) * depth;
  return BASE_MM + Math.max(1, level);
}

/* Where each channel's tip goes, as offsets from the first channel's well. A multichannel's
   nozzles are NOZZLE_PITCH_MM apart along the deck's y, the A tip at the back and the H tip
   at the front: the row of a plate column. The trace names every channel's well, so a plate
   column gives eight wells at their own places. A trough, or the bin, is one well long
   enough for the whole row, and the trace names that same well for every channel: the real
   robot then centres the row on the well (the reservoir and trash definitions carry the
   quirk `centerMultichannelOnWells`), so that is where the tips are drawn, 9 mm apart along
   y about the well's centre. A well too short for the row keeps every channel at its centre,
   and the views draw one tip there. Nothing here is a claim the ledger does not make: the
   ledger says which well each channel touched; this is the geometry of the pipette. */
export const NOZZLE_PITCH_MM = 9;
const TIP_ROOM_MM = 5; // a tip's width at the liquid: the row needs this much past its pitch
function channelOffsets(
  model: ReplayModel,
  targets: number[][],
  channels: number,
  at: { x: number; y: number },
  ox: Float32Array,
  oy: Float32Array,
  base: number,
): void {
  let k = 0;
  while (k < channels) {
    const wellIndex = targets[k][1];
    let m = 1;
    while (k + m < channels && targets[k + m][1] === wellIndex) m++;
    const w = model.wells[wellIndex];
    const p = w?.labware ? wellOnDeck(w.labware, w.name) : at;
    const spread =
      m > 1 &&
      w?.labware != null &&
      wellExtentY(w) >= NOZZLE_PITCH_MM * (m - 1) + TIP_ROOM_MM;
    for (let j = 0; j < m; j++) {
      ox[base + k + j] = p.x - at.x;
      oy[base + k + j] =
        p.y - at.y + (spread ? NOZZLE_PITCH_MM * ((m - 1) / 2 - j) : 0);
    }
    k += m;
  }
}

/* How long a well is along the deck's y: a trough's long side, a round well's diameter, and
   for the trash (no wells in its definition) the bin's whole footprint. */
function wellExtentY(w: WellInfo): number {
  const g = w.geometry;
  if (g) return g.shape === "circular" ? g.d || 0 : g.h || 0;
  return w.labware?.row.h ?? 0;
}

export function buildTimeline(model: ReplayModel, cache: StateCache): Timeline {
  const { data } = model;
  const n = data.events.length;
  const deck = data.deck;
  const tallest = model.labware.reduce(
    (h, lw) =>
      Math.max(h, lw.row.is_trash ? TRASH_HEIGHT_MM : lw.depth + BASE_MM),
    0,
  );
  const H = tallest + TRAVEL_CLEARANCE_MM;
  const park: [number, number] = [deck.width - 20, deck.height - 20];
  const tl: Timeline = {
    count: n,
    total: 0,
    start: new Float64Array(n + 1),
    travel: new Float64Array(n),
    action: new Float64Array(n),
    rise: new Float64Array(n),
    move: new Float64Array(n),
    fall: new Float64Array(n),
    fx: new Float64Array(n),
    fy: new Float64Array(n),
    fh: new Float64Array(n),
    tx: new Float64Array(n),
    ty: new Float64Array(n),
    th: new Float64Array(n),
    travelHeight: H,
    channels: new Uint8Array(n),
    mount: new Uint8Array(n),
    ox: new Float32Array(n * CHANNELS),
    oy: new Float32Array(n * CHANNELS),
    heldFrom: new Float32Array(n * CHANNELS),
    heldTo: new Float32Array(n * CHANNELS),
    tipBefore: new Uint8Array(n),
    tipAfter: new Uint8Array(n),
    tipColour: new Float32Array(n * 3),
    tipColourBefore: new Float32Array(n * 3),
    drops: new Int32Array(n + 1),
    waste: new Float64Array(n + 1),
    dropColour: new Float32Array(0),
    pipetteMax: pipetteMaxOf(model),
    park,
  };
  let x = park[0];
  let y = park[1];
  let h = H;
  let t = 0;
  let tipOn = 0;
  const held = new Float32Array(CHANNELS); // by channel, carried across events
  const colour = new Float32Array([0.5, 0.5, 0.5]);
  let heldTotal = 0;
  let wasteTotal = 0; // µl in the bin so far
  const dropColours: number[] = [];
  let before = cache.at(0);
  // the mount that acts: from the first event that names one, then each event's own. When the
  // other mount takes over, the carriage has not moved: the new pipette's first tip is the
  // mount gap to the side, and its row starts where its own nozzles hang (each body stands
  // over the middle of its row, rowMid), so the travel starts from there, not from the last tip
  let mount = mountCode(data.events.find((e) => mountCode(e) !== 0));
  for (let i = 0; i < n; i++) {
    const e = data.events[i];
    const m = mountCode(e);
    if (m !== 0 && mount !== 0 && m !== mount) {
      x += m === RIGHT ? MOUNT_GAP_MM : -MOUNT_GAP_MM;
      // deck y grows to the back and a row's first nozzle (row A) is its back one: the mount is
      // rowMid in front of the old first tip, and the new first tip rowMid behind the mount
      y += rowMid(channelsOn(data, m)) - rowMid(channelsOn(data, mount));
    }
    if (m !== 0) mount = m;
    tl.mount[i] = mount;
    const after = cache.at(i + 1);
    tl.start[i] = t;
    tl.fx[i] = x;
    tl.fy[i] = y;
    tl.fh[i] = h;
    tl.tipBefore[i] = tipOn;
    tl.tipColourBefore.set(colour, i * 3);
    tl.drops[i] = dropColours.length / 3;
    tl.waste[i] = wasteTotal;
    const targets = e.targets;
    tl.channels[i] = Math.min(CHANNELS, targets.length);
    // an event that touches no well (a mix's or a transfer's own line, a comment, a delay, a
    // module) leaves the pipette as it was: its channels, their spacing and their tips carry
    // over, so a tip on stays drawn and eight channels do not fold onto one point
    if (!targets.length && i > 0) {
      tl.channels[i] = tl.channels[i - 1];
      for (let k = 0; k < CHANNELS; k++) {
        tl.ox[i * CHANNELS + k] = tl.ox[(i - 1) * CHANNELS + k];
        tl.oy[i * CHANNELS + k] = tl.oy[(i - 1) * CHANNELS + k];
      }
    }
    if (
      (e.op === "dispense" || e.op === "blow_out") &&
      targets.length &&
      model.wells[targets[0][1]]?.labware?.row.is_trash
    ) {
      // every channel's tip empties into the bin: the event's volume per channel, or what
      // each tip held for a blow-out
      for (let k = 0; k < tl.channels[i]; k++)
        wasteTotal += e.vol ?? Math.max(0, held[k]);
    }
    let tx = x;
    let ty = y;
    let th = h;
    if (targets.length) {
      const first = model.wells[targets[0][1]];
      const at = first?.labware
        ? wellOnDeck(first.labware, first.name)
        : { x, y };
      tx = at.x;
      ty = at.y;
      th = actionHeight(model, before, after, targets[0][1]);
      channelOffsets(
        model,
        targets,
        tl.channels[i],
        at,
        tl.ox,
        tl.oy,
        i * CHANNELS,
      );
    }
    const dist = Math.hypot(tx - x, ty - y);
    if (dist < 0.5 && targets.length) th = h === H ? th : h; // the same well again (a mix): no travel, no jump
    const inPlace = dist < 0.5 && Math.abs(th - h) < 0.01;
    tl.rise[i] = inPlace ? 0 : (H - h) / Z_SPEED;
    tl.move[i] = inPlace ? 0 : dist / XY_SPEED;
    tl.fall[i] = inPlace ? 0 : (H - th) / Z_SPEED;
    tl.travel[i] = tl.rise[i] + tl.move[i] + tl.fall[i];
    tl.action[i] = isMixStroke(e)
      ? MIX_STROKE_S
      : (ACTION_S[e.op] ?? OTHER_ACTION_S);
    tl.tx[i] = tx;
    tl.ty[i] = ty;
    tl.th[i] = th;
    // what each channel holds, before and after
    for (let k = 0; k < CHANNELS; k++) tl.heldFrom[i * CHANNELS + k] = held[k];
    if (e.op === "pick_up_tip") held.fill(0);
    for (let k = 0; k < tl.channels[i]; k++)
      if (e.held && e.held[k] != null) held[k] = e.held[k];
    if (e.op === "drop_tip" || e.op === "blow_out")
      for (let k = 0; k < tl.channels[i]; k++)
        held[k] = e.op === "blow_out" && e.held ? (e.held[k] ?? 0) : 0;
    for (let k = 0; k < CHANNELS; k++) tl.heldTo[i * CHANNELS + k] = held[k];
    // the colour of what the tip holds: the wells it drew from, blended by volume
    if (e.op === "aspirate" && targets.length) {
      const src = wellFill(
        data,
        before.wells.get(targets[0][1]),
        model.wells[targets[0][1]]?.geometry?.max,
      );
      const c = rgb(src?.blended ?? "#888888");
      const drawn = e.vol ?? 0;
      const total = heldTotal + drawn;
      if (total > 0)
        for (let j = 0; j < 3; j++)
          colour[j] = (colour[j] * heldTotal + (c[j] / 255) * drawn) / total;
      heldTotal = total;
    } else if (e.op === "dispense" || e.op === "blow_out") {
      heldTotal = Math.max(0, tl.heldTo[i * CHANNELS] ?? 0);
    }
    if (e.op === "drop_tip") {
      // one tip per channel lands in the bin
      const residue = tipResidueColour(data, after, targets);
      for (let k = 0; k < Math.max(1, tl.channels[i]); k++)
        dropColours.push(...(residue ?? [0.6, 0.6, 0.6]));
      heldTotal = 0;
      tipOn = 0;
    } else if (e.op === "pick_up_tip") {
      tipOn = 1;
      colour.set([0.5, 0.5, 0.5]);
    } else if (targets.length && targets[0][0] !== null) tipOn = 1;
    tl.tipAfter[i] = tipOn;
    tl.tipColour.set(colour, i * 3);
    t += tl.travel[i] + tl.action[i];
    x = tx;
    y = ty;
    h = th;
    before = after;
  }
  tl.start[n] = t;
  tl.total = t;
  tl.drops[n] = dropColours.length / 3;
  tl.waste[n] = wasteTotal;
  tl.dropColour = new Float32Array(dropColours);
  return tl;
}

function tipResidueColour(
  data: ReplayData,
  state: ReplayState,
  targets: number[][],
): [number, number, number] | null {
  const tip = targets[0]?.[0];
  if (tip == null) return null;
  const residue = state.tips.get(tip) ?? [];
  if (!residue.length) return null;
  const [r, g, b] = rgb(
    data.origins[residue[residue.length - 1][0]]?.colour ?? "#888888",
  );
  return [r / 255, g / 255, b / 255];
}

/* The speed at which about 300 events play in a minute, from the list a person can choose. */
export function defaultSpeed(tl: Timeline): number {
  if (tl.count === 0) return 1;
  const wanted = tl.total / ((tl.count / 300) * 60);
  let best = SPEEDS[0];
  for (const s of SPEEDS)
    if (Math.abs(Math.log(s / wanted)) < Math.abs(Math.log(best / wanted)))
      best = s;
  return best;
}

/* The event whose motion contains time t: the last i with start[i] <= t (count when t is past
   the end). `hint` is the last answer, so a playing clock finds the next event in one step. */
export function eventAt(tl: Timeline, t: number, hint = 0): number {
  const n = tl.count;
  if (t >= tl.total) return n;
  if (t <= 0) return 0;
  let i = Math.max(0, Math.min(n - 1, hint));
  if (tl.start[i] <= t && t < tl.start[i + 1]) return i;
  if (i + 1 < n && tl.start[i + 1] <= t && t < tl.start[i + 2]) return i + 1;
  let lo = 0;
  let hi = n - 1;
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1;
    if (tl.start[mid] <= t) lo = mid;
    else hi = mid - 1;
  }
  return lo;
}

export type Phase = "travel" | "action" | "done";

/* The deck at one moment, written in place: no allocation while the clock runs except when
   the event changes (then the two states around it are fetched and the live rows made). */
export interface Frame {
  t: number;
  event: number; // the event in motion, or count when the run is over
  phase: Phase;
  progress: number; // 0..1 through the phase
  state: ReplayState; // before the event
  after: ReplayState; // after it
  live: Map<number, WellRow>; // the rows of the wells this event changes, interpolated
  x: number; // the first channel's tip point on the deck, mm
  y: number;
  h: number;
  channels: number;
  mount: number; // the mount that acts now (LEFT, RIGHT), 0 when the export does not say
  ox: Float32Array; // per channel offsets from the first
  oy: Float32Array;
  held: Float32Array; // µl per channel now
  tipOn: Uint8Array; // per channel: a tip on the pipette
  tipColour: Float32Array; // rgb 0..1 of the tip's contents
  racksAfter: boolean; // the tip racks as after the event (a tip picked up or dropped past half-way)
  drops: number; // tips in the bin
  waste: number; // µl in the bin
  version: number;
}

export function makeFrame(cache: StateCache): Frame {
  const state = cache.at(0);
  return {
    t: 0,
    event: -1,
    phase: "travel",
    progress: 0,
    state,
    after: state,
    live: new Map(),
    x: 0,
    y: 0,
    h: 0,
    channels: 0,
    mount: 0,
    ox: new Float32Array(CHANNELS),
    oy: new Float32Array(CHANNELS),
    held: new Float32Array(CHANNELS),
    tipOn: new Uint8Array(CHANNELS),
    tipColour: new Float32Array(3),
    racksAfter: false,
    drops: 0,
    waste: 0,
    version: 0,
  };
}

/* The channels the views draw a tip for: the first, and every channel whose tip point is its
   own. Channels sent to one well too short for the row all sit on that well's centre (see
   channelOffsets), and one tip is drawn there; the readout says how many tips there are. */
export function drawnChannels(f: Frame): number[] {
  const out: number[] = [];
  const n = Math.max(1, f.channels);
  for (let k = 0; k < n; k++) {
    let own = true;
    for (let j = 0; j < k && own; j++)
      own =
        Math.abs(f.ox[j] - f.ox[k]) > 0.01 ||
        Math.abs(f.oy[j] - f.oy[k]) > 0.01;
    if (own) out.push(k);
  }
  return out;
}

/* A row interpolated between the well's row before the event and after it: the volume and every
   band's volume move linearly with the action's progress, bands present on one side only grow
   from nothing or shrink to it, and a film (carry-over) is there from the moment the tip is in.
   An unknown volume stays unknown: the row switches half-way. */
function lerpRow(
  before: WellRow | undefined,
  after: WellRow | undefined,
  p: number,
  into: WellRow | null,
): WellRow {
  const a = before ?? [0, 0, []];
  const b = after ?? [0, 0, []];
  if (a[0] === null || b[0] === null) return p < 0.5 ? a : b;
  const bands: Band[] = into ? into[2] : [];
  bands.length = 0;
  const seen = new Set<number>();
  for (const band of b[2]) {
    seen.add(band[0] * 2 + band[2]);
    const prior = a[2].find((x) => x[0] === band[0] && x[2] === band[2]);
    if (band[2] === 1) bands.push(band);
    else if (band[1] === null || (prior && prior[1] === null))
      bands.push(p < 0.5 && prior ? prior : band);
    else
      bands.push([
        band[0],
        (prior ? prior[1]! : 0) + (band[1] - (prior ? prior[1]! : 0)) * p,
        0,
        band[3],
      ]);
  }
  for (const band of a[2]) {
    if (seen.has(band[0] * 2 + band[2])) continue;
    if (band[2] === 1) continue; // a film that is gone after: it goes when the row does
    if (band[1] === null) {
      if (p < 0.5) bands.push(band);
      continue;
    }
    bands.push([band[0], band[1] * (1 - p), 0, band[3]]);
  }
  const row: WellRow = into ?? [0, 0, bands];
  row[0] = a[0] + (b[0] - a[0]) * p;
  row[1] = (a[1] ?? 0) + ((b[1] ?? 0) - (a[1] ?? 0)) * p;
  row[2] = bands;
  return row;
}

export function frameAt(
  model: ReplayModel,
  tl: Timeline,
  cache: StateCache,
  t: number,
  f: Frame,
): Frame {
  const n = tl.count;
  const i = eventAt(tl, t, f.event < 0 ? 0 : f.event);
  f.t = t;
  if (i !== f.event) {
    f.event = i;
    f.state = cache.at(i);
    f.after = cache.at(Math.min(n, i + 1));
    f.live.clear();
    if (i < n) {
      const delta = model.data.deltas[i];
      if (delta?.wells)
        for (const k in delta.wells) f.live.set(Number(k), [0, 0, []]);
    }
  }
  const data = model.data;
  if (i >= n) {
    f.phase = "done";
    f.progress = 1;
    const last = n - 1;
    f.x = last >= 0 ? tl.tx[last] : tl.park[0];
    f.y = last >= 0 ? tl.ty[last] : tl.park[1];
    f.h = last >= 0 ? tl.th[last] : tl.travelHeight;
    f.channels = last >= 0 ? tl.channels[last] : 0;
    f.mount = last >= 0 ? tl.mount[last] : 0;
    for (let k = 0; k < CHANNELS; k++) {
      f.ox[k] = last >= 0 ? tl.ox[last * CHANNELS + k] : 0;
      f.oy[k] = last >= 0 ? tl.oy[last * CHANNELS + k] : 0;
      f.held[k] = last >= 0 ? tl.heldTo[last * CHANNELS + k] : 0;
      f.tipOn[k] = last >= 0 && k < f.channels ? tl.tipAfter[last] : 0;
    }
    if (last >= 0)
      f.tipColour.set(tl.tipColour.subarray(last * 3, last * 3 + 3));
    f.racksAfter = false;
    f.drops = tl.drops[n];
    f.waste = tl.waste[n];
    f.live.clear();
    f.version++;
    return f;
  }
  const e: ReplayEvent = data.events[i];
  const local = t - tl.start[i];
  const travel = tl.travel[i];
  f.channels = tl.channels[i];
  f.mount = tl.mount[i];
  const prevChannels = i > 0 ? tl.channels[i - 1] : 0;
  if (local < travel) {
    f.phase = "travel";
    f.progress = travel > 0 ? local / travel : 1;
    // the three legs: rise, move, fall, each eased on its own
    const r = tl.rise[i];
    const m = tl.move[i];
    if (local < r) {
      const p = easeInOut(local / r);
      f.x = tl.fx[i];
      f.y = tl.fy[i];
      f.h = tl.fh[i] + (tl.travelHeight - tl.fh[i]) * p;
    } else if (local < r + m) {
      const p = easeInOut((local - r) / m);
      f.x = tl.fx[i] + (tl.tx[i] - tl.fx[i]) * p;
      f.y = tl.fy[i] + (tl.ty[i] - tl.fy[i]) * p;
      f.h = tl.travelHeight;
    } else {
      const p = easeInOut((local - r - m) / tl.fall[i]);
      f.x = tl.tx[i];
      f.y = tl.ty[i];
      f.h = tl.travelHeight + (tl.th[i] - tl.travelHeight) * p;
    }
    const blend = easeInOut(f.progress);
    for (let k = 0; k < CHANNELS; k++) {
      const from =
        i > 0 && k < prevChannels
          ? tl.ox[(i - 1) * CHANNELS + k]
          : tl.ox[i * CHANNELS + k];
      const fromY =
        i > 0 && k < prevChannels
          ? tl.oy[(i - 1) * CHANNELS + k]
          : tl.oy[i * CHANNELS + k];
      f.ox[k] = from + (tl.ox[i * CHANNELS + k] - from) * blend;
      f.oy[k] = fromY + (tl.oy[i * CHANNELS + k] - fromY) * blend;
      f.held[k] = tl.heldFrom[i * CHANNELS + k];
      f.tipOn[k] = k < Math.max(f.channels, prevChannels) ? tl.tipBefore[i] : 0;
    }
    f.tipColour.set(tl.tipColourBefore.subarray(i * 3, i * 3 + 3));
    f.racksAfter = false;
    f.drops = tl.drops[i];
    f.waste = tl.waste[i];
    for (const [k, row] of f.live)
      lerpRow(f.state.wells.get(k), f.after.wells.get(k), 0, row);
  } else {
    f.phase = "action";
    const p = Math.min(1, (local - travel) / tl.action[i]);
    f.progress = p;
    f.x = tl.tx[i];
    f.y = tl.ty[i];
    f.h = tl.th[i];
    const half = p >= 0.5;
    for (let k = 0; k < CHANNELS; k++) {
      f.ox[k] = tl.ox[i * CHANNELS + k];
      f.oy[k] = tl.oy[i * CHANNELS + k];
      f.held[k] =
        tl.heldFrom[i * CHANNELS + k] +
        (tl.heldTo[i * CHANNELS + k] - tl.heldFrom[i * CHANNELS + k]) * p;
      f.tipOn[k] =
        k < f.channels ? (half ? tl.tipAfter[i] : tl.tipBefore[i]) : 0;
    }
    const c = half || e.op !== "aspirate" ? tl.tipColour : tl.tipColourBefore;
    if (e.op === "aspirate") {
      for (let j = 0; j < 3; j++)
        f.tipColour[j] =
          tl.tipColourBefore[i * 3 + j] +
          (tl.tipColour[i * 3 + j] - tl.tipColourBefore[i * 3 + j]) * p;
    } else f.tipColour.set(c.subarray(i * 3, i * 3 + 3));
    f.racksAfter = half && (e.op === "pick_up_tip" || e.op === "drop_tip");
    f.drops =
      tl.drops[i] +
      (half && e.op === "drop_tip" ? tl.drops[i + 1] - tl.drops[i] : 0);
    f.waste = tl.waste[i] + (tl.waste[i + 1] - tl.waste[i]) * p; // a dispense into the bin drains over the action
    for (const [k, row] of f.live)
      lerpRow(f.state.wells.get(k), f.after.wells.get(k), p, row);
  }
  f.version++;
  return f;
}

/* A well's row at this moment: the interpolated one while its event acts, else the state's. */
export function rowAt(f: Frame, index: number): WellRow | undefined {
  return f.live.get(index) ?? f.state.wells.get(index);
}

/* The tip-rack status to draw: the state after the event once a pick-up or drop is half done. */
export function racksAt(f: Frame): ReplayState["racks"] {
  return f.racksAfter ? f.after.racks : f.state.racks;
}

/* The time a step (an event index) starts at; `count` is the end of the run. */
export function timeOfStep(tl: Timeline, step: number): number {
  return tl.start[Math.max(0, Math.min(tl.count, Math.floor(step)))];
}

/* The dry draws of the run, as fractions of the run for the scrubber's warning ticks: every
   aspirate from a well the ledger had at 0 µl (state.ts `dryDraw`). */
export function dryTicksOf(
  model: ReplayModel,
  cache: StateCache,
  tl: Timeline,
): number[] {
  if (tl.total <= 0) return [];
  const out: number[] = [];
  model.data.events.forEach((e, i) => {
    if (e.op === "aspirate" && dryDraw(model, e, cache.at(i)) !== null)
      out.push(tl.start[i] / tl.total);
  });
  return out;
}

/* Ticks for the scrubber: the fraction of the run at which each event outside a mix starts,
   thinned to at most `most`. */
export function ticksOf(data: ReplayData, tl: Timeline, most = 400): number[] {
  if (tl.total <= 0) return [];
  const all: number[] = [];
  data.events.forEach((e, i) => {
    if (!isMixStroke(e)) all.push(tl.start[i] / tl.total);
  });
  if (all.length <= most) return all;
  const stride = Math.ceil(all.length / most);
  return all.filter((_, i) => i % stride === 0);
}

function mountCode(e: { mount?: string | null } | undefined): number {
  return e?.mount === "left" ? LEFT : e?.mount === "right" ? RIGHT : 0;
}

/* The channels of the pipette on a mount (1 when the export does not say). */
export function channelsOn(data: ReplayData, mount: number): number {
  const name = mount === LEFT ? "left" : mount === RIGHT ? "right" : null;
  const p = data.pipettes.find((q) => q.mount === name);
  return Math.max(1, Math.min(CHANNELS, p?.channels ?? 1));
}

/* How far toward the front of the deck a pipette's mount sits from its first nozzle: the body
   stands over the middle of its row (an 8-channel's A1 is 31.5 mm behind its mount). */
export function rowMid(channels: number): number {
  return (
    ((Math.max(1, Math.min(CHANNELS, channels)) - 1) * NOZZLE_PITCH_MM) / 2
  );
}
