/* What the 3D view draws, as numbers. Mounting the react-three-fiber Canvas is not tested:
   jsdom has no WebGL context and three's renderer needs a real one (a full mock would be a
   second renderer), so the scene's data layer is held here and the Canvas is looked at in a
   browser (the /replay-lab screenshots). */

import { describe, expect, it } from "vitest";
import { series as analysis } from "../test/fixtures";
import { BASE_MM, buildModel } from "./model";
import {
  BIN_WALL_MM,
  LABEL_MARGIN_MM,
  STRAIGHT,
  TALL_MM,
  TIP_LENGTH_MM,
  TIP_RADIUS_MM,
  TRASH_HEIGHT_MM,
  VIEW_LOW,
  VIEW_STEEP,
  binSpot,
  binTipEnds,
  columnOf,
  homeView,
  PROFILE_POINTS,
  fitProfile,
  labelHeight,
  labwareHeight,
  liquidColumns,
  place,
  radiusAt,
  rowsOfFrame,
  rowsOfState,
  tallestLabware,
  tipsInRack,
  unitProfile,
  type Column,
  type Profile,
} from "./scene";
import {
  MIN_FILL,
  MIN_LINE,
  StateCache,
  heightAt,
  wellFill,
  type HeightTable,
} from "./state";
import {
  NOZZLE_PITCH_MM,
  buildTimeline,
  drawnChannels,
  frameAt,
  makeFrame,
} from "./timeline";
import type { ReplayModel } from "./types";

const data = analysis.replay!;
const model = buildModel(data);
const placements = place(model);
const cache = new StateCache(data);
const tl = buildTimeline(model, cache);

describe("place", () => {
  it("puts every labware at its slot with its footprint, and its wells at their definition's places", () => {
    const plate = placements.find(
      (p) => p.lw.row.id === "3:nest_96_wellplate_100ul_pcr_full_skirt",
    )!;
    expect(plate.w).toBeCloseTo(127.76);
    expect(plate.d).toBeCloseTo(85.48);
    expect(plate.x).toBeCloseTo(265 + 127.76 / 2);
    expect(plate.z).toBeCloseTo(-(0 + 85.48 / 2));
    const a1 = plate.wells.find((w) => w.name === "A1")!;
    expect(a1.x).toBeCloseTo(265 + 14.38);
    expect(a1.z).toBeCloseTo(-74.24);
    expect(a1.rx).toBeCloseTo(5.34 / 2);
    expect(a1.depth).toBeCloseTo(14.78);
    expect(a1.round).toBe(true);
    expect(plate.height).toBeCloseTo(14.78 + BASE_MM);
    // the export's shape: a V bottom and the ledger's table, from (0, 0) to the brim
    expect(a1.bottom).toBe("v");
    expect(a1.shape!.table[0]).toEqual([0, 0]);
    expect(a1.shape!.table[a1.shape!.table.length - 1][0]).toBeGreaterThan(200); // the brim, past the 100 µl rating
    expect(a1.shape!.depth).toBeCloseTo(14.78);
    // the labware's outline: a point at the floor, the rim's radius at the top
    expect(plate.profile[0]).toEqual([0, 0]);
    expect(plate.profile[plate.profile.length - 1][1]).toBe(1);
    expect(plate.profile[plate.profile.length - 1][0]).toBeGreaterThan(0.9);
    const rack = placements.find((p) => p.lw.row.is_tiprack)!;
    expect(rack.profile).toBe(STRAIGHT); // no table: a straight column
  });

  it("draws a trough as a box and the trash as a bin", () => {
    const trough = placements.find(
      (p) => p.lw.row.id === "4:nest_12_reservoir_15ml",
    )!;
    expect(trough.round).toBe(false);
    expect(trough.wells[0].rx).toBeCloseTo(8.2 / 2);
    expect(trough.wells[0].rz).toBeCloseTo(71.2 / 2);
    const trash = placements.find((p) => p.lw.row.is_trash)!;
    expect(trash.height).toBe(TRASH_HEIGHT_MM);
    expect(labwareHeight(trash.lw)).toBe(TRASH_HEIGHT_MM);
  });
});

describe("liquidColumns", () => {
  const plate = placements.find(
    (p) => p.lw.row.id === "3:nest_96_wellplate_100ul_pcr_full_skirt",
  )!;
  const n = plate.wells.length;
  const fractions = new Float32Array(n);
  const colours = new Float32Array(n * 3);
  const films = new Float32Array(n);
  const certain = new Float32Array(n);

  it("fills each well to the ledger's height for its volume, coloured by its liquids", () => {
    liquidColumns(
      model,
      rowsOfState(cache.at(3)),
      plate,
      fractions,
      colours,
      films,
      certain,
    );
    const i = plate.wells.findIndex((w) => w.name === "A1");
    const a1 = plate.wells[i];
    // 200 µl in a well rated 100 µl: nearly to the brim (217 µl), by the well's own table
    expect(fractions[i]).toBeCloseTo(heightAt(a1.shape!.table, 200) / a1.depth);
    expect(fractions[i]).toBeGreaterThan(0.9);
    expect(fractions[i]).toBeLessThan(1);
    expect(colours[i * 3]).toBeCloseTo(0, 2);
    expect(colours[i * 3 + 1]).toBeCloseTo(0x72 / 255, 2);
    expect(colours[i * 3 + 2]).toBeCloseTo(0xb2 / 255, 2);
    expect(certain[i]).toBe(1);
    const empty = plate.wells.findIndex((w) => w.name === "H12");
    expect(fractions[empty]).toBe(0);
    liquidColumns(
      model,
      rowsOfState(cache.at(0)),
      plate,
      fractions,
      colours,
      films,
      certain,
    );
    expect(fractions[i]).toBe(0);
  });

  it("reads a frame's live rows: a column half as tall half-way through the dispense", () => {
    const f = makeFrame(cache);
    frameAt(
      model,
      tl,
      cache,
      tl.start[2] + tl.travel[2] + tl.action[2] * 0.5,
      f,
    );
    liquidColumns(
      model,
      rowsOfFrame(f),
      plate,
      fractions,
      colours,
      films,
      certain,
    );
    const i = plate.wells.findIndex((w) => w.name === "A1");
    const a1 = plate.wells[i];
    expect(fractions[i]).toBeCloseTo(heightAt(a1.shape!.table, 100) / a1.depth); // 100 µl of 200, at the table's height
    frameAt(
      model,
      tl,
      cache,
      tl.start[2] + tl.travel[2] + tl.action[2] * 0.25,
      f,
    );
    const col: Column = { fraction: 0, r: 0, g: 0, b: 0, film: 0, certain: 1 };
    columnOf(model, rowsOfFrame(f)(3), 100, col);
    expect(col.fraction).toBeCloseTo(0.5); // 50 µl of the 100 µl rating, with no shape given
    columnOf(model, rowsOfFrame(f)(3), 100, col, a1.shape);
    expect(col.fraction).toBeCloseTo(heightAt(a1.shape!.table, 50) / a1.depth); // and with it, the table's
    expect(col.g).toBeCloseTo(0x72 / 255, 2);
  });
});

describe("the well's shape", () => {
  // a cone 10 mm deep, 2 mm across at the rim: V = (π/3) r² h with r = h/10
  const cone: HeightTable = [0, 2, 4, 6, 8, 10].map((h) => [
    Math.round((Math.PI / 3) * (h / 10) ** 2 * h * 1000) / 1000,
    h,
  ]);
  // a straight column 10 mm deep, 2 mm across: V = π h
  const column: HeightTable = [0, 5, 10].map((h) => [Math.PI * h, h]);

  it("reads the height at a volume as the ledger does: straight lines between rows, the brim past the end", () => {
    const table: HeightTable = [
      [0, 0],
      [10.3, 1.56],
      [1898, 37.9],
    ];
    expect(heightAt(table, 0)).toBe(0);
    expect(heightAt(table, 5.15)).toBeCloseTo(0.78);
    expect(heightAt(table, 10.3)).toBeCloseTo(1.56);
    expect(heightAt(table, 954.15)).toBeCloseTo((1.56 + 37.9) / 2);
    expect(heightAt(table, 5000)).toBe(37.9);
    expect(heightAt(table, -1)).toBe(0);
  });

  it("turns a table into an outline: a cone widens up from a point, a column is straight", () => {
    const v = unitProfile(cone, 10, Math.PI, "v");
    expect(v[0]).toEqual([0, 0]);
    for (let i = 2; i < v.length - 1; i++)
      expect(v[i][0]).toBeGreaterThan(v[i - 1][0]);
    expect(v[v.length - 1]).toEqual([v[v.length - 2][0], 1]); // the rim: the last slice's radius
    expect(radiusAt(v, 0)).toBe(0);
    expect(radiusAt(v, 0.5)).toBeGreaterThan(0.4);
    expect(radiusAt(v, 0.5)).toBeLessThan(0.6);
    const straight = unitProfile(column, 10, Math.PI, "flat");
    for (const [r] of straight) expect(r).toBeCloseTo(1);
    expect(radiusAt(straight, 0.3)).toBeCloseTo(1);
    expect(unitProfile([[0, 0]], 10, Math.PI, null)).toBe(STRAIGHT);
    expect(radiusAt(STRAIGHT, 0.7)).toBe(1);
  });

  it("draws 20 µl higher in a conical PCR well than in a flat deep well, as it sits on the bench", () => {
    const pcr = placements.find(
      (p) => p.lw.row.id === "3:nest_96_wellplate_100ul_pcr_full_skirt",
    )!.wells[0];
    const row = [20, 20, [[0, 20, 0, 1]]] as Parameters<typeof wellFill>[1];
    const inCone = wellFill(data, row, pcr.max, pcr.shape)!.fraction;
    // a 2 ml deep well, 8.2 mm square, 40 mm deep: a straight table of its own
    const deep = wellFill(data, row, 2000, {
      depth: 40,
      table: [0, 10, 20, 30, 40].map((h) => [8.2 * 8.2 * h, h]),
    })!.fraction;
    expect(heightAt(pcr.shape!.table, 20) / pcr.depth).toBeGreaterThan(0.15); // 20 µl fills the cone's tip
    expect(inCone).toBeGreaterThanOrEqual(MIN_FILL); // never under the drawing floor
    expect(20 / (8.2 * 8.2) / 40).toBeLessThan(MIN_LINE); // under 1 mm of 40: a big well is drawn true, never thinner than a line
    expect(deep).toBe(MIN_LINE);
    expect(inCone).toBeGreaterThan(deep * 5);
  });
});

describe("tipsInRack", () => {
  it("shows a fresh tip, hides one on the pipette or in the trash, dulls one put back", () => {
    const rack = placements.find((p) => p.lw.row.is_tiprack)!;
    const shown = new Float32Array(rack.wells.length);
    const a1 = rack.wells.findIndex((w) => w.name === "A1");
    tipsInRack(cache.at(0).racks, rack, shown);
    expect(shown[a1]).toBe(1);
    tipsInRack(cache.at(1).racks, rack, shown); // event 0 picked up A1
    expect(shown[a1]).toBe(0);
    expect(shown.filter((s) => s === 1).length).toBe(rack.wells.length - 1);
    tipsInRack(
      new Map([[rack.wells[a1].index, "parked" as const]]),
      rack,
      shown,
    );
    expect(shown[a1]).toBe(0.5);
  });
});

describe("binSpot", () => {
  it("lays every dropped tip wholly inside the bin, both ends and the radius, the same place every time", () => {
    const trash = placements.find((p) => p.lw.row.is_trash)!;
    let turned = 0;
    for (let n = 1; n <= 200; n++) {
      const s = binSpot(n, trash);
      expect(binSpot(n, trash)).toEqual(s);
      for (const [x, y, z] of binTipEnds(s)) {
        expect(Math.abs(x - trash.x)).toBeLessThanOrEqual(
          trash.w / 2 - BIN_WALL_MM - TIP_RADIUS_MM + 1e-9,
        );
        expect(Math.abs(z - trash.z)).toBeLessThanOrEqual(
          trash.d / 2 - BIN_WALL_MM - TIP_RADIUS_MM + 1e-9,
        );
        expect(y).toBeGreaterThanOrEqual(BIN_WALL_MM);
        expect(y).toBeLessThan(TRASH_HEIGHT_MM);
      }
      if (Math.abs(s.yaw) > 0.5) turned++;
    }
    expect(turned).toBeGreaterThan(50); // a pile, not a row: the tips point different ways
    // the ends are a tip's length apart
    const [a, b] = binTipEnds(binSpot(7, trash));
    expect(Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2])).toBeCloseTo(
      TIP_LENGTH_MM,
    );
  });
});

/* The same deck with every well shallow: nothing on it over TALL_MM. */
function shallow(): ReplayModel {
  const low = structuredClone(data);
  for (const lw of low.deck.labware)
    for (const g of Object.values(lw.wells)) g.depth = 10;
  return buildModel(low);
}

describe("homeView", () => {
  it("looks at the middle of the machine, over the deck's centre, from above and in front", () => {
    const home = homeView(model);
    expect(home.target[0]).toBe(data.deck.width / 2);
    expect(home.target[2]).toBe(-data.deck.height / 2);
    expect(home.target[1]).toBeGreaterThan(0); // above the deck, among the labware and the frame
    expect(home.position[1]).toBeGreaterThan(home.target[1]);
    expect(home.position[2]).toBeGreaterThan(0);
  });

  it("looks from a front corner, so the deck reads in 3D", () => {
    const home = homeView(model);
    expect(home.position[0]).toBeLessThan(home.target[0]); // the left of the deck
    expect(home.position[2]).toBeGreaterThan(home.target[2]); // in front of it
  });

  it("looks from steeper above when a labware is over 25 mm tall, so a tall front row hides nothing", () => {
    const elevation = (m: ReplayModel) => {
      const h = homeView(m);
      return Math.atan2(
        h.position[1] - h.target[1],
        h.position[2] - h.target[2],
      );
    };
    // this deck has a rack of 300 µl tips, 59 mm deep, and the reservoir's wells are 27 mm deep
    expect(tallestLabware(model)).toBeGreaterThan(TALL_MM);
    expect(elevation(model)).toBeCloseTo(
      Math.atan2(VIEW_STEEP[1], VIEW_STEEP[2]),
    );
    const low = shallow();
    expect(tallestLabware(low)).toBeLessThanOrEqual(TALL_MM);
    expect(elevation(low)).toBeCloseTo(Math.atan2(VIEW_LOW[1], VIEW_LOW[2]));
    expect(elevation(model)).toBeGreaterThan(elevation(low));
    // the trash is 60 mm on every deck and never decides the view
    expect(tallestLabware(low)).toBeLessThan(TRASH_HEIGHT_MM);
  });
});

describe("labelHeight", () => {
  it("prints every name above the tallest labware plus a margin", () => {
    const y = labelHeight(model);
    for (const p of placements)
      if (!p.lw.row.is_trash)
        expect(y).toBeGreaterThanOrEqual(p.height + LABEL_MARGIN_MM);
    expect(y).toBeCloseTo(59.3 + BASE_MM + LABEL_MARGIN_MM); // the tip rack
    const low = shallow();
    expect(labelHeight(low)).toBeCloseTo(10 + BASE_MM + LABEL_MARGIN_MM);
  });
});

describe("an 8-channel pipette's tips in the scene", () => {
  it("lie in a row inside the trough's footprint, one cone each", () => {
    const multi = structuredClone(data);
    multi.pipettes = [{ mount: "right", name: "p300_multi_gen2", channels: 8 }];
    const trough = 1; // the reservoir's A1 in slot 4
    const i = multi.events.findIndex(
      (e) => e.op === "aspirate" && e.targets[0][1] === trough,
    );
    multi.events[i].targets = Array.from({ length: 8 }, (_, k) => [k, trough]);
    const m = buildModel(multi);
    const c = new StateCache(multi);
    const t = buildTimeline(m, c);
    const f = frameAt(
      m,
      t,
      c,
      t.start[i] + t.travel[i] + t.action[i] / 2,
      makeFrame(c),
    );
    const p = place(m).find((x) => x.lw.row.id === "4:nest_12_reservoir_15ml")!;
    const well = p.wells.find((w) => w.name === "A1")!;
    const drawn = drawnChannels(f);
    expect(drawn).toHaveLength(8);
    const zs = drawn.map((k) => -(f.y + f.oy[k]));
    for (const z of zs) expect(Math.abs(z - well.z)).toBeLessThan(well.rz); // inside the trough along z
    for (let k = 1; k < 8; k++)
      expect(zs[k] - zs[k - 1]).toBeCloseTo(NOZZLE_PITCH_MM); // the H tip towards the front (+z)
    for (const k of drawn) expect(f.x + f.ox[k]).toBeCloseTo(well.x);
  });
});

describe("an outline longer than the shader holds", () => {
  // An Eppendorf 1.5 ml tube's table gives 66 points; the 3D view's shader holds 32. Cutting the
  // list kept its top half: the tube was drawn open at the bottom, its liquid a flat disc.
  const long: Profile = Array.from({ length: 66 }, (_, i) => {
    const y = i / 65;
    return [y < 0.45 ? 0.07 + (0.93 * y) / 0.45 : 1, y];
  });

  it("keeps a short outline as it is", () => {
    expect(fitProfile(STRAIGHT)).toBe(STRAIGHT);
  });

  it("keeps the whole of a long one, floor to rim, in at most PROFILE_POINTS points", () => {
    const fit = fitProfile(long);
    expect(fit.length).toBeLessThanOrEqual(PROFILE_POINTS);
    expect(fit[0]).toEqual(long[0]);
    expect(fit[fit.length - 1]).toEqual(long[long.length - 1]);
    for (const y of [0.1, 0.3, 0.5, 0.8])
      expect(radiusAt(fit, y)).toBeCloseTo(radiusAt(long, y), 1);
  });

  it("draws a tube with a 115-row table with its cone and its floor", () => {
    const copy = structuredClone(data);
    const id = "3:nest_96_wellplate_100ul_pcr_full_skirt";
    const row = copy.deck.labware.find((l) => l.id === id)!;
    const depth = 39.1;
    const r = 4.4;
    const table: [number, number][] = [[0, 0]];
    for (let i = 1; i <= 115; i++) {
      const h = (depth * i) / 115;
      const rr = h < 17 ? (r * h) / 17 : r;
      table.push([table[i - 1][0] + Math.PI * rr * rr * (depth / 115), h]);
    }
    for (const w of Object.values(row.wells)) {
      w.height_at_ul = table;
      w.depth = depth;
      w.d = 2 * r;
    }
    const p = place(buildModel(copy)).find((q) => q.lw.row.id === id)!;
    expect(p.profile.length).toBeLessThanOrEqual(PROFILE_POINTS);
    expect(p.profile[0]).toEqual([0, 0]); // a V bottom: a point at the floor
    expect(radiusAt(p.profile, 0.2)).toBeLessThan(0.6); // the cone is drawn
    expect(radiusAt(p.profile, 0.9)).toBeCloseTo(1, 1);
  });
});

describe("a labware on a module", () => {
  const id = "3:nest_96_wellplate_100ul_pcr_full_skirt";
  const copy = structuredClone(data);
  const row = copy.deck.labware.find((l) => l.id === id)!;
  row.module = "temperatureModuleV2";
  row.elevation = 80.09;
  row.module_body = {
    x: row.slot_x,
    y: row.slot_y,
    w: row.w,
    h: row.h,
    height: 80.09,
    name: "Temperature Module GEN2",
  };
  const raised = buildModel(copy);
  const plate = place(raised).find((p) => p.lw.row.id === id)!;

  it("stands at the module's height, and the camera frames it", () => {
    expect(plate.elevation).toBeCloseTo(80.09);
    expect(plate.height).toBeCloseTo(14.78 + BASE_MM); // its own height, from its base
    expect(tallestLabware(raised)).toBeCloseTo(80.09 + plate.height);
    expect(homeView(raised).target[1]).toBeGreaterThan(homeView(model).target[1]);
  });

  it("prints the other names at the deck's height, not over the module", () => {
    expect(labelHeight(raised)).toBeCloseTo(labelHeight(model));
  });

  it("sends the pipette down to the raised wells, and the gantry over them", () => {
    const t = buildTimeline(raised, new StateCache(copy));
    const i = data.events.findIndex(
      (e) =>
        (e.op === "aspirate" || e.op === "dispense") &&
        e.targets.some((x) => model.wells[x[1]]?.labware?.row.id === id),
    );
    expect(i).toBeGreaterThanOrEqual(0);
    expect(t.th[i] - tl.th[i]).toBeCloseTo(80.09);
    expect(t.travelHeight).toBeGreaterThan(80.09 + plate.height);
  });
});
