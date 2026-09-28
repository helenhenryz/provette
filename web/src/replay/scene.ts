/* What the 3D view draws, as numbers: where each labware and well sits, how tall the liquid
   column in a well is and what colour, which rack positions still hold a tip, where the
   pipette is. Pure functions over the model and a frame, so the tests can hold them without
   a WebGL context; Deck3D.tsx turns them into instanced meshes.

   Units are millimetres, the deck's own. Deck x is scene x, deck y (towards the back of the
   robot) is scene -z, and height is scene y. */

import { BASE_MM } from "./model";
import {
  rgb,
  shapeOf,
  wellFill,
  type HeightTable,
  type ReplayState,
  type WellShape,
} from "./state";
import { racksAt, rowAt, TRASH_HEIGHT_MM, type Frame } from "./timeline";
import type { LabwareModel, ReplayModel, TipStatus, WellRow } from "./types";

export { TRASH_HEIGHT_MM };
export const PIPETTE_LENGTH_MM = 70;
export const TIP_LENGTH_MM = 30; // the tip on the pipette; racks draw their tips at their well's depth

export interface WellPlacement {
  index: number; // -1 when the trace never names the well
  name: string; // "A1"
  x: number; // scene x of the well's centre
  z: number; // scene z of the well's centre
  rx: number; // half-width along x (radius for a round well)
  rz: number; // half-width along z
  depth: number;
  round: boolean;
  max: number | null;
  shape: WellShape | null; // the ledger's height table, when the export carries one
  bottom: "flat" | "u" | "v" | null; // the definition's word for the bottom
}

/* A well's outline as a profile to turn on a lathe: [radius, height] points from the floor
   to the rim, both as fractions (radius of the rim's, height of the depth). */
export type Profile = [number, number][];
export const STRAIGHT: Profile = [
  [1, 0],
  [1, 1],
];

export interface LabwarePlacement {
  lw: LabwareModel;
  x: number; // scene x of the footprint's centre
  z: number;
  w: number; // along x
  d: number; // along z (the deck's y)
  height: number; // above the deck
  wells: WellPlacement[];
  round: boolean; // the wells' shape (one geometry per labware)
  profile: Profile; // the wells' outline (one geometry per labware: the first well's with a table)
}

export function labwareHeight(lw: LabwareModel): number {
  return lw.row.is_trash ? TRASH_HEIGHT_MM : Math.max(lw.depth, 2) + BASE_MM;
}

export function place(model: ReplayModel): LabwarePlacement[] {
  return model.labware.map((lw) => {
    const { w, h } = lw.row;
    const height = labwareHeight(lw);
    const wells: WellPlacement[] = lw.wells.map((well) => {
      const g = well.geometry;
      const round = g.shape === "circular";
      const rx = round ? (g.d || 5) / 2 : (g.w || 5) / 2;
      const rz = round ? (g.d || 5) / 2 : (g.h || 5) / 2;
      return {
        index: well.index,
        name: well.name,
        x: lw.x + g.x,
        z: -(lw.y + g.y),
        rx,
        rz,
        depth: g.depth ?? lw.depth,
        round,
        max: g.max,
        shape: shapeOf(g),
        bottom: g.bottom ?? null,
      };
    });
    const shaped = wells.find((well) => well.shape);
    const profile = shaped
      ? unitProfile(
          shaped.shape!.table,
          shaped.depth,
          (shaped.round ? Math.PI : 4) * shaped.rx * shaped.rz,
          shaped.bottom,
        )
      : STRAIGHT;
    return {
      lw,
      x: lw.x + w / 2,
      z: -(lw.y + h / 2),
      w,
      d: h,
      height,
      wells,
      round: wells.length ? wells[0].round : true,
      profile,
    };
  });
}

/* A well's outline from the ledger's own table. Between two rows the table's slope, µl per
   mm, is the well's cross-section over that slice in mm², so the slice's radius as a fraction
   of the rim's is the square root of that over the rim's area (`rimArea`: π rx rz for a round
   well, 4 rx rz for a box). Each slice gives one point at its middle
   height; the floor is a point for a "u" or "v" bottom and the first slice's radius
   otherwise; the rim is the last slice's radius. No shape is recomputed here: the outline is
   the table read the other way. A well without a table is a straight column. */
export function unitProfile(
  table: HeightTable,
  depth: number,
  rimArea: number,
  bottom: WellPlacement["bottom"],
): Profile {
  if (table.length < 2 || depth <= 0 || rimArea <= 0) return STRAIGHT;
  const points: Profile = [];
  for (let i = 1; i < table.length; i++) {
    const [v0, h0] = table[i - 1];
    const [v1, h1] = table[i];
    if (h1 <= h0) continue;
    const area = Math.max(0, v1 - v0) / (h1 - h0);
    points.push([
      Math.min(1, Math.sqrt(area / rimArea)),
      Math.min(1, (h0 + h1) / 2 / depth),
    ]);
  }
  if (!points.length) return STRAIGHT;
  const floor = bottom === "u" || bottom === "v" ? 0 : points[0][0];
  return [[floor, 0], ...points, [points[points.length - 1][0], 1]];
}

/* The outline's radius at a height (0..1 of the depth): a straight line between two points. */
export function radiusAt(profile: Profile, y: number): number {
  const last = profile[profile.length - 1];
  if (y >= last[1]) return last[0];
  let i = 1;
  while (i < profile.length - 1 && profile[i][1] <= y) i++;
  const [r0, y0] = profile[i - 1];
  const [r1, y1] = profile[i];
  return y1 === y0 ? r0 : r0 + ((r1 - r0) * (y - y0)) / (y1 - y0);
}

/* One well's column: written into `out`, nothing allocated but what wellFill reads. */
export interface Column {
  fraction: number; // of the well's depth: the ledger's height with the well's shape, else volume over the rated maximum
  r: number;
  g: number;
  b: number;
  film: number; // 1: carry-over only, no volume
  certain: number; // 0: rests on a contact the model could not decide
}

export function columnOf(
  model: ReplayModel,
  row: WellRow | undefined,
  max: number | null,
  out: Column,
  shape: WellShape | null = null,
): Column {
  const fill = row ? wellFill(model.data, row, max, shape) : null;
  if (!fill) {
    out.fraction = 0;
    out.film = 0;
    out.certain = 1;
    out.r = out.g = out.b = 0;
    return out;
  }
  out.fraction = fill.bands.length ? fill.fraction : 0;
  out.film = fill.bands.length === 0 && fill.films.length ? 1 : 0;
  out.certain = fill.bands.length
    ? fill.bands.every((b) => b.certain)
      ? 1
      : 0
    : fill.films.every((f) => f.certain)
      ? 1
      : 0;
  const [r, g, b] = rgb(fill.blended);
  out.r = r / 255;
  out.g = g / 255;
  out.b = b / 255;
  return out;
}

const scratch: Column = { fraction: 0, r: 0, g: 0, b: 0, film: 0, certain: 1 };

/* The liquid column of every well of a labware: height fraction and colour (the bands'
   colours blended by their share of the volume: one column, one colour; the 2D view shows
   the stack), written into arrays the caller owns. `rows` gives a well's row at the moment:
   a state's, or a frame's (interpolated while the event acts). */
export function liquidColumns(
  model: ReplayModel,
  rows: (index: number) => WellRow | undefined,
  placement: LabwarePlacement,
  fractions: Float32Array,
  colours: Float32Array, // rgb 0..1 per well
  films: Float32Array, // 1 when the well holds carry-over only (a film, no volume)
  certain: Float32Array, // 0 when the presence rests on a contact the model could not decide
): void {
  placement.wells.forEach((well, i) => {
    columnOf(
      model,
      well.index >= 0 ? rows(well.index) : undefined,
      well.max,
      scratch,
      well.shape,
    );
    fractions[i] = scratch.fraction;
    films[i] = scratch.film;
    certain[i] = scratch.certain;
    colours[i * 3] = scratch.r;
    colours[i * 3 + 1] = scratch.g;
    colours[i * 3 + 2] = scratch.b;
  });
}

export function rowsOfState(
  state: ReplayState,
): (index: number) => WellRow | undefined {
  return (i) => state.wells.get(i);
}

export function rowsOfFrame(
  frame: Frame,
): (index: number) => WellRow | undefined {
  return (i) => rowAt(frame, i);
}

/* Which rack positions show a tip: a fresh tip, or a used one put back (drawn duller). */
export function tipsInRack(
  racks: ReplayState["racks"],
  placement: LabwarePlacement,
  shown: Float32Array,
): void {
  placement.wells.forEach((well, i) => {
    const status: TipStatus =
      well.index >= 0 ? (racks.get(well.index) ?? "fresh") : "fresh";
    shown[i] = status === "fresh" ? 1 : status === "parked" ? 0.5 : 0;
  });
}

export function racksOfFrame(frame: Frame): ReplayState["racks"] {
  return racksAt(frame);
}

/* Where the n-th tip dropped in the bin lies: a spot inside the bin's footprint from its
   number (the same every time), turned and tilted, so a pile grows as the run drops tips.
   Where a tip lands in a bin is not in the ledger; that it is in the bin is, so the whole tip
   lies inside: the spot's range shrinks by the wall, the tip's radius and the reach of its
   two ends along each side. `yaw` turns the tip in the deck's plane (radians from scene +x
   towards +z, the front) and `pitch` tips one end down. */
export const TIP_RADIUS_MM = 2.2;
export const BIN_WALL_MM = 2;
export interface BinSpot {
  x: number;
  y: number;
  z: number;
  yaw: number;
  pitch: number;
  tilt: number; // -0.5..0.5, the number the yaw and pitch come from
}
export function binSpot(n: number, p: LabwarePlacement): BinSpot {
  const { a, b, tilt } = binSpotUnit(n);
  const yaw = tilt * 140 * (Math.PI / 180);
  const pitch = tilt * 0.8;
  const reach = (TIP_LENGTH_MM / 2) * Math.cos(pitch);
  const margin = BIN_WALL_MM + TIP_RADIUS_MM;
  const rangeX = Math.max(
    0,
    p.w / 2 - margin - reach * Math.abs(Math.cos(yaw)),
  );
  const rangeZ = Math.max(
    0,
    p.d / 2 - margin - reach * Math.abs(Math.sin(yaw)),
  );
  const lift =
    BIN_WALL_MM +
    TIP_RADIUS_MM +
    (TIP_LENGTH_MM / 2) * Math.abs(Math.sin(pitch));
  return {
    x: p.x + a * rangeX,
    z: p.z + b * rangeZ,
    y: lift + Math.min(20, n * 0.15),
    yaw,
    pitch,
    tilt,
  };
}

/* The two ends of a tip lying at a spot, in scene mm: the mouth and the point (the cone's
   axis after Deck3D's rotation: yaw about the vertical, then the pitch). */
export function binTipEnds(
  s: BinSpot,
): [[number, number, number], [number, number, number]] {
  const dx = Math.cos(s.yaw) * Math.cos(s.pitch) * (TIP_LENGTH_MM / 2);
  const dz = Math.sin(s.yaw) * Math.cos(s.pitch) * (TIP_LENGTH_MM / 2);
  const dy = -Math.sin(s.pitch) * (TIP_LENGTH_MM / 2);
  return [
    [s.x - dx, s.y - dy, s.z - dz],
    [s.x + dx, s.y + dy, s.z + dz],
  ];
}

/* The n-th tip's spot as fractions of the bin's usable half-sides (-1..1 across x, -1..1
   across scene z, towards the front) and its tilt, so the 2D close-up lays the same tip in
   the same place through `binSpot` on a footprint of the bin's size. */
export function binSpotUnit(n: number): { a: number; b: number; tilt: number } {
  // two irrational strides that do not add to one (0.618 and 0.382 did, which laid every
  // tip on one diagonal); the plastic constant's pair spreads the pile over the floor
  return {
    a: ((n * 0.7548776662) % 1) * 2 - 1,
    b: (((n * 0.569840291 + 0.25) % 1) * 2 - 1) * 1,
    tilt: ((n * 7) % 11) / 11 - 0.5,
  };
}

/* The tallest labware on the deck, the trash aside (it is a bin at the back corner, always
   the same height, and nothing stands behind it). A tip rack counts: its tips stand as tall
   as its wells are deep. */
export function tallestLabware(model: ReplayModel): number {
  return model.labware.reduce(
    (h, lw) => (lw.row.is_trash ? h : Math.max(h, labwareHeight(lw))),
    0,
  );
}

/* Where every labware's name is printed: one height for the whole deck, above the tallest
   labware plus a margin, so no name prints across a taller neighbour's tips. The trash keeps
   its name on its own rim. */
export const LABEL_MARGIN_MM = 3;
export function labelHeight(model: ReplayModel): number {
  return tallestLabware(model) + LABEL_MARGIN_MM;
}

/* The home camera: the whole deck in the frame. The deck's box (width × height, and the
   tallest labware above it) is fitted to the canvas at the camera's vertical field of view,
   from a front corner, more from the side than the top, so the deck reads as a solid thing and the front row of labware
   is never cut off. A deck with tall labware (a deep-well plate, a rack of long tips: anything
   over TALL_MM) is seen from steeper above, so a tall piece in the front row does not hide the
   rows behind it. */
export const CAMERA_FOV = 32; // degrees, vertical
export const TALL_MM = 25;
export const VIEW_LOW: [number, number, number] = [-0.43, 0.57, 0.69]; // the front-left corner, 35° up, normalised
export const VIEW_STEEP: [number, number, number] = [-0.37, 0.71, 0.6]; // 45° up
export function homeView(
  model: ReplayModel,
  aspect = 4 / 3,
): { position: [number, number, number]; target: [number, number, number] } {
  const { width, height } = model.data.deck;
  // aimed a little above the deck's centre, at the middle of the machine (the deck and the
  // gantry's frame over it), so the whole of it sits centred in the view
  const target: [number, number, number] = [
    width / 2,
    labelHeight(model) * 0.6,
    -height / 2,
  ];
  const dir = tallestLabware(model) > TALL_MM ? VIEW_STEEP : VIEW_LOW;
  const n = Math.hypot(dir[0], dir[1], dir[2]);
  // the deck seen from the corner: its extent along the line of sight (foreshortened from
  // above, plus the labels, which stand above the tallest labware, seen edge-on) and across it
  const flat = Math.hypot(dir[0], dir[2]);
  const along = (Math.abs(width * dir[0]) + Math.abs(height * dir[2])) / flat;
  const across = (Math.abs(width * dir[2]) + Math.abs(height * dir[0])) / flat;
  const top = labelHeight(model) + 10;
  const half =
    Math.max(along * 0.95, (along * dir[1] + top * flat) / n, across / aspect) /
    2;
  const distance = (half / Math.tan((CAMERA_FOV / 2) * (Math.PI / 180))) * 1.4; // room for the gantry's frame
  return {
    position: [
      target[0] + (dir[0] / n) * distance,
      target[1] + (dir[1] / n) * distance,
      target[2] + (dir[2] / n) * distance,
    ],
    target,
  };
}
