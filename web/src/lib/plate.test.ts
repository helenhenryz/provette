import { describe, expect, it } from "vitest";
import dil01 from "../../../eval/platemaps/dil-01.json";
import { series as analysis } from "../test/fixtures";

import planJson from "../../../tests/web/fixtures/plan-free-group.json";
import type { PlateMap } from "./api";
import { plateView, wellName, wellRowCol } from "./plate";
import { finalState, wellsOf } from "./replayState";

// the plate map the series fixture was checked against (tests/fixtures/protocols/dil_series.py)
const episode = { platemap: dil01 as unknown as PlateMap };

describe("replayState", () => {
  it("rebuilds the final state: the twelve wells of the series hold liquid", () => {
    const replay = analysis.replay!;
    const state = finalState(replay);
    const destination = analysis.verify!.intent.destination!;
    const wells = wellsOf(replay, destination);
    const filled = [...wells.values()].filter(
      (i) => (state.wells.get(i)?.[0] ?? 0) > 0,
    );
    expect(filled).toHaveLength(12);
  });
});

describe("plateView", () => {
  it("names wells and reads them back", () => {
    expect(wellRowCol("H12")).toEqual({ row: 7, col: 11 });
    expect(wellName(0, 0)).toBe("A1");
    expect(wellRowCol("tube")).toBeNull();
  });

  it("marks the checked wells ok on a verified episode, with what they hold", () => {
    const view = plateView(episode.platemap, analysis.verify, analysis.replay);
    expect(view.rows).toBe(8);
    expect(view.cols).toBe(12);
    const inUse = view.cells.filter((c) => c.status !== "empty");
    expect(inUse).toHaveLength(12);
    expect(inUse.every((c) => c.found && c.found.length > 0)).toBe(true);
    expect(view.legend.length).toBeGreaterThan(0);
  });

  it("marks a mismatch from the verify report", () => {
    const verify = structuredClone(analysis.verify!);
    verify.intent.status = "mismatch";
    verify.intent.mismatches = [
      {
        well: "A1",
        group: "series",
        expected: { drug: 50 },
        found: { drug: 25 },
        issues: [
          {
            kind: "wrong_amount",
            liquid: "drug",
            expected_ul: 50,
            found_ul: 25,
            detail: "",
          },
        ],
      },
    ];
    const view = plateView(episode.platemap, verify, analysis.replay);
    const a1 = view.cells.find((c) => c.well === "A1")!;
    expect(a1.status).toBe("mismatch");
    expect(a1.issues[0]).toBe("drug: 25 µl where 50 µl was asked");
  });

  it("reads a well the map never named, whose issue names no liquid", () => {
    // `super/short-on-tips/pcr-02` blanked the page on this: `liquid` is null on an
    // `unexpected_well`, and the words must not touch it.
    const verify = structuredClone(analysis.verify!);
    verify.intent.status = "mismatch";
    verify.intent.mismatches = [
      {
        well: "A1",
        group: null,
        expected: {},
        found: { water: 10.5, master_mix: 12.5 },
        issues: [
          {
            kind: "unexpected_well",
            liquid: null,
            expected_ul: null,
            found_ul: null,
            detail: "",
          },
        ],
      },
    ];
    const view = plateView(episode.platemap, verify, analysis.replay);
    const a1 = view.cells.find((c) => c.well === "A1")!;
    expect(a1.status).toBe("mismatch");
    expect(a1.issues[0]).toBe(
      "the plate map says nothing about this well, but it holds liquid",
    );
  });

  it("draws a free group as a proposed layout down the first column, with a legend", () => {
    // the planner's map for "8 PCR reactions", which pins no well: nothing to draw, before
    const view = plateView(
      (planJson as { platemap: PlateMap }).platemap,
      null,
      null,
    );
    const proposed = view.cells.filter((c) => c.status === "proposed");
    expect(proposed.map((c) => c.well)).toEqual([
      "A1",
      "B1",
      "C1",
      "D1",
      "E1",
      "F1",
      "G1",
      "H1",
    ]);
    expect(proposed[0].expected?.map((h) => h.name)).toEqual([
      "master_mix",
      "sample_1",
    ]);
    expect(view.groups[0].shownIn).toBe("A1–H1");
    expect(view.legend.map((l) => l.name)).toContain("master_mix");
  });

  it("keeps a proposed layout off the pinned wells and inside `within`", () => {
    const map = structuredClone((planJson as { platemap: PlateMap }).platemap);
    map.variants[0].pinned = { A1: { water: 10 } };
    map.variants[0].groups[0].within = [
      "A1",
      "A2",
      "A3",
      "B1",
      "B2",
      "B3",
      "C1",
      "C2",
      "C3",
    ];
    const view = plateView(map, null, null);
    const proposed = view.cells
      .filter((c) => c.status === "proposed")
      .map((c) => c.well);
    expect(proposed).toEqual(["A2", "A3", "B1", "B2", "B3", "C1", "C2", "C3"]);
    expect(view.cells.find((c) => c.well === "A1")!.status).toBe("unchecked");
  });

  it("does not propose once a replay says where things really are", () => {
    const view = plateView(episode.platemap, analysis.verify, analysis.replay);
    expect(view.cells.some((c) => c.status === "proposed")).toBe(false);
  });

  it("falls back to a 96-well grid with the map alone", () => {
    const view = plateView(episode.platemap, null, null);
    expect(view.cells).toHaveLength(96);
    expect(view.groups).toHaveLength(
      episode.platemap!.variants[0].groups.length,
    );
  });
});
