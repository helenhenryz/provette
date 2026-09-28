/* The state rebuild, held to the reference in lib/replayState.ts (the page's own logic, which
   provette.view.export.replay_deltas mirrors and the Python tests hold to run.wells). */

import { describe, expect, it } from "vitest";
import { stateAt } from "../lib/replayState";
import { series as analysis } from "../test/fixtures";
import { buildModel } from "./model";
import {
  MIN_FILL,
  MIN_FILL_UNDER_UL,
  MIN_LINE,
  StateCache,
  eventLine,
  stepOfFinding,
  tipWords,
  wellFill,
  wellText,
} from "./state";
import type { ReplayData } from "./types";

const data = analysis.replay!;

function plain(s: {
  wells: Map<number, unknown>;
  racks: Map<number, string>;
  tips: Map<number, unknown>;
}) {
  return {
    wells: Object.fromEntries(s.wells),
    racks: Object.fromEntries(s.racks),
    tips: Object.fromEntries(s.tips),
  };
}

describe("StateCache", () => {
  it("matches the reference rebuild at every checkpoint edge and at the end", () => {
    const cache = new StateCache(data);
    const n = data.events.length;
    for (const p of [0, 1, 49, 50, 51, 99, 100, 137, n - 1, n]) {
      expect(plain(cache.at(p)), `step ${p}`).toEqual(plain(stateAt(data, p)));
    }
  });

  it("steps forward one at a time to the same states as a seek", () => {
    const cache = new StateCache(data);
    const seek = new StateCache(data);
    for (let p = 0; p <= data.events.length; p++) {
      expect(plain(cache.at(p))).toEqual(plain(seek.at(p)));
    }
  });

  it("seeks backwards and out of range", () => {
    const cache = new StateCache(data);
    cache.at(120);
    expect(plain(cache.at(3))).toEqual(plain(stateAt(data, 3)));
    expect(cache.at(-5).step).toBe(0);
    expect(cache.at(10_000).step).toBe(data.events.length);
  });

  it("returns a fresh object each time, so a kept state never changes under a view", () => {
    const cache = new StateCache(data);
    const a = cache.at(2);
    const b = cache.at(3);
    expect(a).not.toBe(b);
    expect(plain(a)).toEqual(plain(stateAt(data, 2)));
  });

  it("applies a hand-built delta list: wells, racks and tips", () => {
    const small: ReplayData = {
      ...data,
      wells: ["1:rack[A1]", "2:tubes[A1]", "3:plate[A1]"],
      origins: [
        {
          well: 1,
          name: "water",
          declared: true,
          place: "tube A1 in slot 2",
          volume: 100,
          colour: "#0072B2",
        },
      ],
      events: [
        {
          i: 0,
          op: "pick_up_tip",
          line: 1,
          parent: null,
          t: 0,
          vol: null,
          targets: [[0, 0]],
          text: "pick up tip A1",
          held: [0],
        },
        {
          i: 1,
          op: "aspirate",
          line: 2,
          parent: null,
          t: 1,
          vol: 10,
          targets: [[0, 1]],
          text: "aspirate 10 µl from tube A1 in slot 2, tip A1",
          held: [10],
        },
        {
          i: 2,
          op: "dispense",
          line: 3,
          parent: null,
          t: 2,
          vol: 10,
          targets: [[0, 2]],
          text: "dispense 10 µl into well A1 in slot 3, tip A1",
          held: [0],
        },
      ],
      initial: { "1": [100, 100, [[0, 100, 0, 1]]] },
      deltas: [
        { racks: [[0, "in_use"]], tips: { "0": [] } },
        { wells: { "1": [90, 90, [[0, 90, 0, 1]]] }, tips: { "0": [[0, 1]] } },
        { wells: { "2": [10, 10, [[0, 10, 0, 1]]] } },
      ],
      cache_every: 2,
      findings: [],
    };
    const cache = new StateCache(small);
    expect(plain(cache.at(0))).toEqual({
      wells: { "1": [100, 100, [[0, 100, 0, 1]]] },
      racks: {},
      tips: {},
    });
    expect(plain(cache.at(1)).racks).toEqual({ "0": "in_use" });
    expect(plain(cache.at(3)).wells).toEqual({
      "1": [90, 90, [[0, 90, 0, 1]]],
      "2": [10, 10, [[0, 10, 0, 1]]],
    });
    expect(plain(cache.at(3)).tips).toEqual({ "0": [[0, 1]] });
    expect(plain(cache.at(2)).wells).toEqual({
      "1": [90, 90, [[0, 90, 0, 1]]],
    });
  });
});

describe("wellFill", () => {
  it("stacks two liquids by their share of the volume and fills to volume over the maximum", () => {
    const fill = wellFill(
      data,
      [
        25,
        25,
        [
          [0, 20, 0, 1],
          [1, 5, 0, 1],
        ],
      ],
      100,
    )!;
    expect(fill.fraction).toBeCloseTo(0.25);
    expect(fill.bands.map((b) => b.share)).toEqual([0.8, 0.2]);
    expect(fill.bands.map((b) => b.colour)).toEqual([
      data.origins[0].colour,
      data.origins[1].colour,
    ]);
    expect(fill.films).toEqual([]);
    expect(fill.blended).toMatch(/^#[0-9a-f]{6}$/);
  });

  it("draws a film for carry-over only, with no height", () => {
    const fill = wellFill(data, [0, 0, [[1, null, 1, 0]]], 100)!;
    expect(fill.fraction).toBe(0);
    expect(fill.bands).toEqual([]);
    expect(fill.films).toEqual([
      { origin: 1, colour: data.origins[1].colour, certain: false },
    ]);
  });

  it("shows the lower bound when the volume is not known", () => {
    const fill = wellFill(data, [null, 30, [[0, null, 0, 1]]], 100)!;
    expect(fill.volume).toBeNull();
    expect(fill.fraction).toBeCloseTo(0.3);
    expect(fill.bands[0].unknown).toBe(true);
  });

  it("is null for an empty well", () => {
    expect(wellFill(data, undefined, 100)).toBeNull();
  });

  it("with the well's shape, fills to the ledger's height for the volume over the depth", () => {
    const shape = {
      depth: 10,
      table: [
        [0, 0],
        [10, 5],
        [40, 10],
      ] as [number, number][],
    };
    expect(
      wellFill(data, [10, 10, [[0, 10, 0, 1]]], 100, shape)!.fraction,
    ).toBeCloseTo(0.5); // 10 µl is 5 mm up
    expect(
      wellFill(data, [25, 25, [[0, 25, 0, 1]]], 100, shape)!.fraction,
    ).toBeCloseTo(0.75);
    expect(
      wellFill(data, [100, 100, [[0, 100, 0, 1]]], 100, shape)!.fraction,
    ).toBe(1); // past the brim: full
    expect(wellFill(data, [1, 1, [[0, 1, 0, 1]]], 100, shape)!.fraction).toBe(
      MIN_FILL,
    ); // the floor still holds
    expect(
      wellFill(data, [null, 10, [[0, null, 0, 1]]], 100, shape)!.fraction,
    ).toBeCloseTo(0.5); // the lower bound, by the table
    expect(
      wellFill(data, [10, 10, [[0, 10, 0, 1]]], 100, null)!.fraction,
    ).toBeCloseTo(MIN_FILL); // without it, 10 of 100, floored
  });

  it("draws a small well at least a quarter full, and a trough or a big tube at its true level", () => {
    const band = (v: number) => [[0, v, 0, 1]] as [number, number, 0, 1][];
    expect(wellFill(data, [10, 10, band(10)], 200)!.fraction).toBe(MIN_FILL); // 5 % of a PCR well
    expect(wellFill(data, [50, 50, band(50)], 100)!.fraction).toBeCloseTo(0.5);
    expect(
      wellFill(data, [1000, 1000, band(1000)], 15000)!.fraction,
    ).toBeCloseTo(1000 / 15000); // a trough at its level
    expect(wellFill(data, [200, 200, band(200)], 15000)!.fraction).toBe(
      MIN_LINE,
    ); // 1.3 %: a line, never invisible
    expect(wellFill(data, [50, 50, band(50)], 1500)!.fraction).toBeCloseTo(
      50 / 1500,
    ); // a 1.5 ml tube
    expect(wellFill(data, [10, 10, band(10)], 999)!.fraction).toBe(MIN_FILL); // the floor holds under a millilitre
    expect(MIN_FILL_UNDER_UL).toBe(1000);
  });
});

describe("the words", () => {
  const model = buildModel(data);
  const cache = new StateCache(model.data);

  it("names the liquid the tip draws on an aspirate", () => {
    const line = eventLine(model, data.events[1], cache.at(1));
    expect(line).toBe(
      "line 34 · aspirate 200 µl of drug from tube A1 in slot 2, tip A1",
    );
  });

  it("reads a well in words, with its volume and what it holds", () => {
    const text = wellText(model, cache.at(3), 3);
    expect(text).toMatch(/^Well A1 in slot 3: 200 µl = 200 µl of drug\.$/);
    expect(wellText(model, cache.at(0), 3)).toBe("Well A1 in slot 3: empty.");
    expect(wellText(model, cache.at(1), 2)).toBe(
      "Tip A1 of the rack in slot 1: the tip is on the pipette.",
    );
  });

  it("says what the tip holds and has touched", () => {
    expect(tipWords(model, data.events[1], cache.at(2))).toBe(
      "Tip A1 holds 200 µl and has touched: drug.",
    );
  });

  it("jumps a finding to the event that did the damage, at the start of its motion", () => {
    expect(stepOfFinding(data, { root_event: 2 })).toBe(2);
    expect(stepOfFinding(data, { root_event: null })).toBe(data.events.length);
  });
});
