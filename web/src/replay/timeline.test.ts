/* The motion model on the frozen episode file: the clock's mapping between events and time,
   the durations by kind and distance, the pipette's path, and the volumes half-way through
   an event. */

import { describe, expect, it } from "vitest";
import { series as analysis } from "../test/fixtures";
import { BASE_MM, buildModel, TIP_FRACTION, wellOnDeck } from "./model";
import { StateCache, stepOfFinding, wellFill } from "./state";
import {
  ACTION_S,
  LEFT,
  MIX_STROKE_S,
  MOUNT_GAP_MM,
  RIGHT,
  NOZZLE_PITCH_MM,
  SPEEDS,
  TRASH_HEIGHT_MM,
  XY_SPEED,
  Z_SPEED,
  buildTimeline,
  defaultSpeed,
  drawnChannels,
  eventAt,
  frameAt,
  isMixStroke,
  makeFrame,
  racksAt,
  rowAt,
  timeOfStep,
} from "./timeline";

const data = analysis.replay!;
const model = buildModel(data);
const cache = new StateCache(data);
const tl = buildTimeline(model, cache);
const n = data.events.length;

describe("the clock's mapping", () => {
  it("starts every event after the one before and ends at the total", () => {
    expect(tl.start[0]).toBe(0);
    for (let i = 0; i < n; i++)
      expect(tl.start[i + 1]).toBeCloseTo(
        tl.start[i] + tl.travel[i] + tl.action[i],
        9,
      );
    expect(tl.start[n]).toBeCloseTo(tl.total, 9);
    expect(tl.total).toBeGreaterThan(0);
  });

  it("finds the event at a time, with or without a hint, and the end past the total", () => {
    for (let i = 0; i < n; i++) {
      const t = tl.start[i] + (tl.travel[i] + tl.action[i]) / 2;
      expect(eventAt(tl, t)).toBe(i);
      expect(eventAt(tl, t, 0)).toBe(i);
      expect(eventAt(tl, t, i - 1)).toBe(i);
      expect(eventAt(tl, t, n - 1)).toBe(i);
      expect(eventAt(tl, tl.start[i])).toBe(i);
    }
    expect(eventAt(tl, tl.total)).toBe(n);
    expect(eventAt(tl, tl.total + 5)).toBe(n);
    expect(eventAt(tl, -1)).toBe(0);
  });

  it("maps a step to the start of that event's motion, and a finding to its event", () => {
    expect(timeOfStep(tl, 0)).toBe(0);
    expect(timeOfStep(tl, 7)).toBe(tl.start[7]);
    expect(timeOfStep(tl, n)).toBe(tl.total);
    expect(timeOfStep(tl, n + 10)).toBe(tl.total);
    const f = data.findings[0];
    expect(stepOfFinding(data, f)).toBe(f.root_event);
    expect(eventAt(tl, timeOfStep(tl, stepOfFinding(data, f)))).toBe(
      f.root_event,
    );
    expect(stepOfFinding(data, { root_event: null })).toBe(n);
  });

  it("picks a default speed from the list at which about 300 events play in a minute", () => {
    const s = defaultSpeed(tl);
    expect(SPEEDS).toContain(s);
    const minutes = tl.total / s / 60;
    const per300 = minutes / (n / 300);
    expect(per300).toBeGreaterThan(0.5);
    expect(per300).toBeLessThan(2);
  });
});

describe("durations", () => {
  it("gives an action its time by kind, and a mix's strokes less", () => {
    data.events.forEach((e, i) => {
      const want = isMixStroke(e) ? MIX_STROKE_S : (ACTION_S[e.op] ?? 0.15);
      expect(tl.action[i], `event ${i} ${e.op}`).toBeCloseTo(want, 9);
    });
  });

  it("makes a travel take longer the further it goes, at the travel speed", () => {
    // event 1: the rack in slot 1 to the tube in slot 2; event 2: the tube to the plate in slot 3
    const d1 = Math.hypot(tl.tx[1] - tl.fx[1], tl.ty[1] - tl.fy[1]);
    const d2 = Math.hypot(tl.tx[2] - tl.fx[2], tl.ty[2] - tl.fy[2]);
    expect(tl.move[1]).toBeCloseTo(d1 / XY_SPEED, 9);
    expect(tl.move[2]).toBeCloseTo(d2 / XY_SPEED, 9);
    expect(d2 > d1 ? tl.move[2] > tl.move[1] : tl.move[1] > tl.move[2]).toBe(
      true,
    );
    expect(tl.rise[1]).toBeCloseTo((tl.travelHeight - tl.fh[1]) / Z_SPEED, 9);
    expect(tl.fall[1]).toBeCloseTo((tl.travelHeight - tl.th[1]) / Z_SPEED, 9);
  });

  it("gives a mix's strokes in the same well no travel", () => {
    const i = data.events.findIndex(
      (e, k) =>
        isMixStroke(e) &&
        k > 0 &&
        data.events[k - 1].targets[0]?.[1] === e.targets[0]?.[1],
    );
    expect(i).toBeGreaterThan(0);
    expect(tl.travel[i]).toBe(0);
    expect(tl.th[i]).toBe(tl.fh[i]);
  });
});

describe("the path", () => {
  it("goes from the park to the rack, to the tube, to the plate, at the wells' places", () => {
    const rack = model.byId.get("1:opentrons_96_tiprack_300ul")!;
    const tubes = model.byId.get("2:opentrons_24_tuberack_nest_1.5ml_snapcap")!;
    const plate = model.byId.get("3:nest_96_wellplate_100ul_pcr_full_skirt")!;
    expect([tl.fx[0], tl.fy[0]]).toEqual(tl.park);
    expect(tl.fh[0]).toBe(tl.travelHeight);
    const a1 = wellOnDeck(rack, "A1");
    expect(tl.tx[0]).toBeCloseTo(a1.x);
    expect(tl.ty[0]).toBeCloseTo(a1.y);
    expect(tl.th[0]).toBeCloseTo(
      BASE_MM + rack.wells[0].geometry.depth! * (1 - TIP_FRACTION),
    ); // where the seated tip's point is
    const tube = wellOnDeck(tubes, "A1");
    expect([tl.fx[1], tl.fy[1]]).toEqual([tl.tx[0], tl.ty[0]]);
    expect(tl.tx[1]).toBeCloseTo(tube.x);
    expect(tl.ty[1]).toBeCloseTo(tube.y);
    const well = wellOnDeck(plate, "A1");
    expect(tl.tx[2]).toBeCloseTo(well.x);
    expect(tl.ty[2]).toBeCloseTo(well.y);
    expect(tl.travelHeight).toBeGreaterThan(TRASH_HEIGHT_MM);
  });

  it("descends to the liquid's level the ledger knows, never under 1 mm, and rises above the trash", () => {
    // event 1 aspirates 200 µl from a 1.5 ml tube holding 500 µl: the level after (300 µl)
    const tubes = model.byId.get("2:opentrons_24_tuberack_nest_1.5ml_snapcap")!;
    const g = tubes.wells[0].geometry;
    const after = wellFill(data, cache.at(2).wells.get(0), g.max)!;
    expect(tl.th[1]).toBeCloseTo(BASE_MM + after.fraction * g.depth!);
    // event 2 dispenses into an empty well: the tip goes to 1 mm from the bottom
    expect(tl.th[2]).toBeCloseTo(BASE_MM + 1);
    const drop = data.events.findIndex((e) => e.op === "drop_tip");
    expect(tl.th[drop]).toBe(TRASH_HEIGHT_MM + 10);
  });

  it("rises, moves and falls in order, eased, with the tip on after the pick-up", () => {
    const f = makeFrame(cache);
    // during the rise of event 1 the pipette is still over the rack, climbing
    frameAt(model, tl, cache, tl.start[1] + tl.rise[1] * 0.5, f);
    expect(f.event).toBe(1);
    expect(f.phase).toBe("travel");
    expect(f.x).toBeCloseTo(tl.fx[1]);
    expect(f.h).toBeGreaterThan(tl.fh[1]);
    expect(f.h).toBeLessThan(tl.travelHeight);
    expect(f.tipOn[0]).toBe(1);
    // half-way through the move: between the two wells, at the travel height
    frameAt(model, tl, cache, tl.start[1] + tl.rise[1] + tl.move[1] * 0.5, f);
    expect(f.h).toBeCloseTo(tl.travelHeight);
    expect(f.x).toBeCloseTo((tl.fx[1] + tl.tx[1]) / 2, 0);
    // a quarter of the way in, eased: less than a quarter of the distance
    frameAt(model, tl, cache, tl.start[1] + tl.rise[1] + tl.move[1] * 0.25, f);
    expect(Math.abs(f.x - tl.fx[1])).toBeLessThan(
      Math.abs(tl.tx[1] - tl.fx[1]) * 0.25,
    );
    // at the end of the fall: in the well
    frameAt(model, tl, cache, tl.start[1] + tl.travel[1] - 1e-9, f);
    expect(f.h).toBeCloseTo(tl.th[1], 1);
    expect(f.x).toBeCloseTo(tl.tx[1]);
    // before the pick-up the pipette has no tip; after half the action it has one
    frameAt(model, tl, cache, tl.start[0] + tl.travel[0] * 0.5, f);
    expect(f.tipOn[0]).toBe(0);
    frameAt(
      model,
      tl,
      cache,
      tl.start[0] + tl.travel[0] + tl.action[0] * 0.75,
      f,
    );
    expect(f.tipOn[0]).toBe(1);
    expect(racksAt(f).get(2)).toBe("in_use"); // the rack has lost A1
    frameAt(
      model,
      tl,
      cache,
      tl.start[0] + tl.travel[0] + tl.action[0] * 0.25,
      f,
    );
    expect(racksAt(f).get(2)).toBeUndefined(); // not yet
  });

  it("keeps the tip drawn through an event on no well (a mix's own line, a comment)", () => {
    // every event that touches no well, with a tip on the pipette before it
    const quiet = data.events
      .map((e, i) => ({ e, i }))
      .filter(
        ({ e, i }) => e.targets.length === 0 && i > 0 && tl.tipBefore[i] === 1,
      );
    expect(quiet.length).toBeGreaterThan(0);
    const f = makeFrame(cache);
    for (const { i } of quiet) {
      expect(tl.channels[i]).toBe(tl.channels[i - 1]);
      for (const at of [0.25, 0.75]) {
        const t = tl.start[i] + (tl.travel[i] + tl.action[i]) * at;
        frameAt(model, tl, cache, t, f);
        expect(f.tipOn[0]).toBe(1);
      }
    }
  });

  it("drops the tip into the bin half-way through the drop, and keeps the count", () => {
    const f = makeFrame(cache);
    const drop = data.events.findIndex((e) => e.op === "drop_tip");
    frameAt(
      model,
      tl,
      cache,
      tl.start[drop] + tl.travel[drop] + tl.action[drop] * 0.25,
      f,
    );
    expect(f.tipOn[0]).toBe(1);
    expect(f.drops).toBe(0);
    frameAt(
      model,
      tl,
      cache,
      tl.start[drop] + tl.travel[drop] + tl.action[drop] * 0.75,
      f,
    );
    expect(f.tipOn[0]).toBe(0);
    expect(f.drops).toBe(1);
    frameAt(model, tl, cache, tl.total, f);
    expect(f.phase).toBe("done");
    expect(f.drops).toBe(tl.drops[n]);
    expect(f.drops).toBe(data.events.filter((e) => e.op === "drop_tip").length);
    expect(tl.dropColour.length).toBe(f.drops * 3);
  });
});

describe("volumes over time", () => {
  it("moves the source's volume into the tip over the aspirate, and out over the dispense", () => {
    const f = makeFrame(cache);
    // event 1: aspirate 200 µl from tube A1 (500 µl) in slot 2
    const half = tl.start[1] + tl.travel[1] + tl.action[1] * 0.5;
    frameAt(model, tl, cache, half, f);
    expect(f.phase).toBe("action");
    expect(f.progress).toBeCloseTo(0.5);
    expect(f.live.has(0)).toBe(true);
    const tube = rowAt(f, 0)!;
    expect(tube[0]).toBeCloseTo(400);
    expect(tube[2]).toHaveLength(1);
    expect(tube[2][0][1]).toBeCloseTo(400);
    expect(f.held[0]).toBeCloseTo(100);
    // at the start of the action nothing has moved; at the end it all has
    frameAt(model, tl, cache, tl.start[1] + tl.travel[1], f);
    expect(rowAt(f, 0)![0]).toBeCloseTo(500);
    expect(f.held[0]).toBeCloseTo(0);
    frameAt(model, tl, cache, tl.start[2] - 1e-9, f);
    expect(rowAt(f, 0)![0]).toBeCloseTo(300, 1);
    expect(f.held[0]).toBeCloseTo(200, 1);
    // event 2: dispense 200 µl into well A1 of the plate, empty before
    frameAt(
      model,
      tl,
      cache,
      tl.start[2] + tl.travel[2] + tl.action[2] * 0.25,
      f,
    );
    expect(f.live.has(3)).toBe(true);
    const well = rowAt(f, 3)!;
    expect(well[0]).toBeCloseTo(50);
    expect(well[2][0][1]).toBeCloseTo(50);
    expect(f.held[0]).toBeCloseTo(150);
    // and the wells the event does not touch are the state's own rows
    expect(rowAt(f, 1)).toBe(f.state.wells.get(1));
  });

  it("colours the tip with what it drew", () => {
    const f = makeFrame(cache);
    frameAt(model, tl, cache, tl.start[2], f);
    const [r, g, b] = f.tipColour;
    expect(Math.round(r * 255)).toBe(0x00);
    expect(Math.round(g * 255)).toBe(0x72);
    expect(Math.round(b * 255)).toBe(0xb2);
  });

  it("writes into the same frame and allocates no live rows between events", () => {
    const f = makeFrame(cache);
    frameAt(model, tl, cache, tl.start[1] + tl.travel[1] + 0.01, f);
    const row = rowAt(f, 0);
    const held = f.held;
    frameAt(model, tl, cache, tl.start[1] + tl.travel[1] + 0.02, f);
    expect(rowAt(f, 0)).toBe(row);
    expect(f.held).toBe(held);
    expect(f.version).toBeGreaterThan(0);
  });
});

describe("a multichannel pipette at the bin", () => {
  // the same run with every drop and every trash dispense done by eight channels at once
  const trash = data.wells.findIndex((w) => /trash/i.test(w));
  const wide = structuredClone(data);
  for (const e of wide.events) {
    if (
      e.op === "drop_tip" ||
      ((e.op === "dispense" || e.op === "blow_out") &&
        e.targets.some((t) => t[1] === trash))
    ) {
      e.targets = Array.from({ length: 8 }, (_, k) => [k, e.targets[0][1]]);
    }
  }
  const wideModel = buildModel(wide);
  const wideCache = new StateCache(wide);
  const wideTl = buildTimeline(wideModel, wideCache);

  it("counts a tip per channel in the bin, with a colour each", () => {
    const drops = data.events.filter((e) => e.op === "drop_tip").length;
    expect(drops).toBeGreaterThan(0);
    expect(wideTl.drops[n]).toBe(drops * 8);
    expect(wideTl.dropColour.length).toBe(drops * 8 * 3);
    expect(tl.drops[n]).toBe(drops);
  });

  it("counts every channel's volume into the bin", () => {
    expect(trash).toBeGreaterThanOrEqual(0);
    const into = data.events.filter(
      (e) =>
        e.op === "dispense" &&
        e.targets.some((t) => t[1] === trash) &&
        e.vol != null,
    );
    if (into.length === 0) return; // this run never dispenses into the bin; the drop test above covers the count
    expect(wideTl.waste[n]).toBeCloseTo(tl.waste[n] * 8, 6);
  });

  it("spreads the eight tips 9 mm apart across the bin, centred on it", () => {
    const drop = wide.events.findIndex((e) => e.op === "drop_tip");
    const oy = Array.from(wideTl.oy.subarray(drop * 8, drop * 8 + 8));
    for (let k = 1; k < 8; k++)
      expect(oy[k - 1] - oy[k]).toBeCloseTo(NOZZLE_PITCH_MM);
    expect(oy[0] + oy[7]).toBeCloseTo(0);
    const bin = wideModel.wells[trash].labware!;
    for (const y of oy) expect(Math.abs(y)).toBeLessThan(bin.row.h / 2);
  });
});

describe("an 8-channel pipette's tips", () => {
  // the same run with every channel in play: eight tips into one trough, one round tube, and
  // a plate column
  const multi = structuredClone(data);
  multi.pipettes = [{ mount: "right", name: "p300_multi_gen2", channels: 8 }];
  const plateId = "3:nest_96_wellplate_100ul_pcr_full_skirt";
  const column = ["A1", "B1", "C1", "D1", "E1", "F1", "G1", "H1"].map((name) =>
    name === "A1" ? 3 : multi.wells.push(`${plateId}[${name}]`) - 1,
  );
  const tube = 0; // the 1.5 ml tube in slot 2, round
  const trough = 1; // the 15 ml reservoir's A1 in slot 4, 71 mm long
  const fromTube = 1; // event 1 aspirates from the tube
  const intoColumn = 2; // event 2 dispenses into the plate
  const fromTrough = data.events.findIndex(
    (e) => e.op === "aspirate" && e.targets[0][1] === trough,
  );
  multi.events[fromTube].targets = Array.from({ length: 8 }, (_, k) => [
    k,
    tube,
  ]);
  multi.events[intoColumn].targets = column.map((w, k) => [k, w]);
  multi.events[fromTrough].targets = Array.from({ length: 8 }, (_, k) => [
    k,
    trough,
  ]);
  const multiModel = buildModel(multi);
  const multiCache = new StateCache(multi);
  const multiTl = buildTimeline(multiModel, multiCache);
  const offsets = (i: number) =>
    Array.from({ length: 8 }, (_, k) => [
      multiTl.ox[i * 8 + k],
      multiTl.oy[i * 8 + k],
    ]);

  it("dips eight tips into one trough in a row 9 mm apart along y, centred in the trough", () => {
    expect(fromTrough).toBeGreaterThan(0);
    const g = multiModel.wells[trough].geometry!;
    expect(g.h).toBeGreaterThan(NOZZLE_PITCH_MM * 7);
    const o = offsets(fromTrough);
    for (let k = 0; k < 8; k++) expect(o[k][0]).toBeCloseTo(0);
    for (let k = 1; k < 8; k++)
      expect(o[k - 1][1] - o[k][1]).toBeCloseTo(NOZZLE_PITCH_MM);
    expect(o[0][1] + o[7][1]).toBeCloseTo(0); // centred
    for (const [, y] of o) expect(Math.abs(y)).toBeLessThan(g.h! / 2); // inside the trough
    expect(new Set(o.map(([, y]) => y.toFixed(3))).size).toBe(8);
    const f = makeFrame(multiCache);
    frameAt(
      multiModel,
      multiTl,
      multiCache,
      multiTl.start[fromTrough] +
        multiTl.travel[fromTrough] +
        multiTl.action[fromTrough] / 2,
      f,
    );
    expect(drawnChannels(f)).toEqual([0, 1, 2, 3, 4, 5, 6, 7]);
  });

  it("keeps a plate column's tips at the wells' own places", () => {
    const plate = multiModel.byId.get(plateId)!;
    const a1 = wellOnDeck(plate, "A1");
    const o = offsets(intoColumn);
    ["A1", "B1", "C1", "D1", "E1", "F1", "G1", "H1"].forEach((name, k) => {
      const at = wellOnDeck(plate, name);
      expect(o[k][0]).toBeCloseTo(at.x - a1.x);
      expect(o[k][1]).toBeCloseTo(at.y - a1.y);
    });
    expect(o[0][1] - o[1][1]).toBeCloseTo(NOZZLE_PITCH_MM); // a 96-well plate's rows are 9 mm apart too
  });

  it("collapses eight channels sent to one round tube, and draws one tip there", () => {
    const o = offsets(fromTube);
    for (const [x, y] of o) {
      expect(x).toBeCloseTo(0);
      expect(y).toBeCloseTo(0);
    }
    const f = makeFrame(multiCache);
    frameAt(
      multiModel,
      multiTl,
      multiCache,
      multiTl.start[fromTube] +
        multiTl.travel[fromTube] +
        multiTl.action[fromTube] / 2,
      f,
    );
    expect(f.channels).toBe(8);
    expect(drawnChannels(f)).toEqual([0]);
  });
});

describe("two mounts", () => {
  // the same run, the first half on the left mount and the rest on the right
  const two = structuredClone(data);
  two.pipettes = [
    { mount: "left", name: "p300_single_gen2", channels: 1 },
    { mount: "right", name: "p20_single_gen2", channels: 1 },
  ];
  const half = Math.floor(two.events.length / 2);
  two.events.forEach((e, i) => {
    e.mount = e.targets.length ? (i < half ? "left" : "right") : null;
  });
  const twoModel = buildModel(two);
  const twoCache = new StateCache(two);
  const twoTl = buildTimeline(twoModel, twoCache);
  const swap = two.events.findIndex((e, i) => i >= half && e.targets.length);

  it("says which mount works at every event, carried over an event that names none", () => {
    expect(twoTl.mount[0]).toBe(LEFT);
    expect(twoTl.mount[swap - 1]).toBe(LEFT);
    expect(twoTl.mount[swap]).toBe(RIGHT);
    expect(twoTl.mount[two.events.length - 1]).toBe(RIGHT);
    const f = makeFrame(twoCache);
    frameAt(twoModel, twoTl, twoCache, twoTl.start[swap] + 0.01, f);
    expect(f.mount).toBe(RIGHT);
  });

  it("starts the right pipette's first move from its own tip, the mount gap to the right", () => {
    // the carriage has not moved: the other pipette's tip is where the last one's was, 34 mm over
    expect(twoTl.fx[swap]).toBeCloseTo(twoTl.tx[swap - 1] + MOUNT_GAP_MM, 6);
    expect(twoTl.fy[swap]).toBeCloseTo(twoTl.ty[swap - 1], 6);
  });

  it("knows the mount on an export without it (schema before 3) as 0, and moves as before", () => {
    const old = structuredClone(two);
    for (const e of old.events) delete e.mount;
    const oldTl = buildTimeline(buildModel(old), new StateCache(old));
    expect(Array.from(oldTl.mount).every((m) => m === 0)).toBe(true);
    expect(oldTl.fx[swap]).toBeCloseTo(oldTl.tx[swap - 1], 6); // no swap to make
  });
});
