/* A dry draw: an aspirate from a well the ledger has at 0 µl draws nothing, and the replay
   says so, in the event line, in the 2D readout and as a warning tick on the scrubber. A
   small hand-written export: a reservoir well declared at 100 µl, drawn down in one
   aspirate, then drawn again when it is empty. */

import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { ReplayExport } from "../lib/api";
import { Controls } from "./Controls";
import { Deck2D } from "./Deck2D";
import { buildModel } from "./model";
import { dryDraw, eventLine, StateCache, tipWords } from "./state";
import {
  buildTimeline,
  dryTicksOf,
  frameAt,
  makeFrame,
  ticksOf,
} from "./timeline";

vi.mock("./Deck3D", () => ({
  Deck3D: () => <div data-testid="deck3d">3D</div>,
}));

const well = (x: number, y: number) => ({
  x,
  y,
  shape: "circular",
  d: 6,
  w: null,
  h: null,
  depth: 10,
  max: 200,
});
const event = (
  i: number,
  op: string,
  line: number,
  vol: number | null,
  targets: number[][],
  held: number[],
  text: string,
) => ({ i, op, line, parent: null, t: null, vol, targets, text, held });

const data: ReplayExport = {
  schema_version: 1,
  protocol: "dry.py",
  api_level: "2.19",
  opentrons_version: "8.8.2",
  source: [],
  deck: {
    width: 400,
    height: 300,
    slots: [
      { id: "1", x: 0, y: 0, width: 128, height: 86 },
      { id: "8", x: 132, y: 180, width: 128, height: 86 },
      { id: "9", x: 264, y: 180, width: 128, height: 86 },
    ],
    labware: [
      {
        id: "1:tips",
        slot: "1",
        name: "tips",
        load_name: "opentrons_96_tiprack_300ul",
        is_tiprack: true,
        is_trash: false,
        module: null,
        kind: "tip rack",
        measured: true,
        slot_x: 0,
        slot_y: 0,
        w: 128,
        h: 86,
        ox: 0,
        oy: 0,
        wells: { A1: well(14, 74) },
      },
      {
        id: "8:res",
        slot: "8",
        name: "reservoir",
        load_name: "nest_12_reservoir_15ml",
        is_tiprack: false,
        is_trash: false,
        module: null,
        kind: "reservoir",
        measured: true,
        slot_x: 132,
        slot_y: 180,
        w: 128,
        h: 86,
        ox: 0,
        oy: 0,
        wells: { A1: well(14, 43) },
      },
      {
        id: "9:plate",
        slot: "9",
        name: "plate",
        load_name: "nest_96_wellplate_2ml_deep",
        is_tiprack: false,
        is_trash: false,
        module: null,
        kind: "plate",
        measured: true,
        slot_x: 264,
        slot_y: 180,
        w: 128,
        h: 86,
        ox: 0,
        oy: 0,
        wells: { A1: well(14, 74), A2: well(23, 74) },
      },
    ],
  },
  pipettes: [{ mount: "left", name: "p300_single_gen2", channels: 1 }],
  wells: ["8:res[A1]", "1:tips[A1]", "9:plate[A1]", "9:plate[A2]"],
  origins: [
    {
      well: 0,
      name: "buffer",
      declared: true,
      place: "A1 in slot 8",
      volume: 100,
      colour: "#3366cc",
    },
  ],
  events: [
    event(
      0,
      "pick_up_tip",
      10,
      null,
      [[1, 1]],
      [0],
      "pick up tip A1 from slot 1",
    ),
    event(
      1,
      "aspirate",
      11,
      100,
      [[1, 0]],
      [100],
      "aspirate 100 µl from well A1 in slot 8, tip A1",
    ),
    event(
      2,
      "dispense",
      12,
      100,
      [[1, 2]],
      [0],
      "dispense 100 µl into well A1 in slot 9, tip A1",
    ),
    event(
      3,
      "aspirate",
      11,
      100,
      [[1, 0]],
      [0],
      "aspirate 100 µl from well A1 in slot 8, tip A1",
    ),
    event(
      4,
      "dispense",
      12,
      100,
      [[1, 3]],
      [0],
      "dispense 100 µl into well A2 in slot 9, tip A1",
    ),
  ],
  initial: { 0: [100, 15000, [[0, 100, 0, 1]]] },
  deltas: [
    { racks: [[1, "in_use"]] },
    { wells: { 0: [0, 15000, [[0, 0, 0, 1]]] }, tips: { 1: [[0, 1]] } },
    { wells: { 2: [100, 2000, [[0, 100, 0, 1]]] } },
    null,
    { wells: { 3: [0, 2000, [[0, 0, 1, 1]]] } },
  ],
  cache_every: 50,
  findings: [],
  summary: {
    simulator: "passed",
    check: "clean",
    verify: null,
    counts: {},
    events: 5,
  },
  verify: null,
};

const model = buildModel(data);
const cache = new StateCache(data);
const tl = buildTimeline(model, cache);

describe("a dry draw", () => {
  it("is an aspirate from a well at 0 µl whose tip does not fill, and not the draw that emptied it", () => {
    expect(dryDraw(model, data.events[1], cache.at(1))).toBeNull(); // 100 µl there: it fills
    expect(dryDraw(model, data.events[3], cache.at(3))).toBe(0); // empty now: nothing drawn
    expect(dryDraw(model, data.events[2], cache.at(2))).toBeNull(); // a dispense is never one
  });

  it("says so in the event line and the tip's words", () => {
    expect(eventLine(model, data.events[3], cache.at(3))).toBe(
      "line 11 · drew nothing: A1 in slot 8 is empty · asked for 100 µl",
    );
    expect(eventLine(model, data.events[1], cache.at(1))).toBe(
      "line 11 · aspirate 100 µl of buffer from well A1 in slot 8, tip A1",
    );
    expect(tipWords(model, data.events[3], cache.at(4), cache.at(3))).toBe(
      "Tip A1 drew nothing: A1 in slot 8 is empty; it holds 0 µl and has touched: buffer.",
    );
    expect(tipWords(model, data.events[1], cache.at(2), cache.at(1))).toBe(
      "Tip A1 holds 100 µl and has touched: buffer.",
    );
  });

  it("is a warning tick on the scrubber, at the event's start", () => {
    const dry = dryTicksOf(model, cache, tl);
    expect(dry).toEqual([tl.start[3] / tl.total]);
    expect(ticksOf(data, tl)).toHaveLength(5);
    render(
      <Controls
        time={0}
        duration={tl.total}
        step={0}
        count={5}
        playing={false}
        speed={1}
        line=""
        ticks={ticksOf(data, tl)}
        marks={[]}
        dry={dry}
        onSeek={() => {}}
        onStep={() => {}}
        onPlay={() => {}}
        onSpeed={() => {}}
      />,
    );
    const svg = document.querySelector("svg[data-dry]")!;
    expect(svg.getAttribute("data-dry")).toBe("1");
    expect(svg.querySelectorAll("line").length).toBe(6); // five ticks and the one dry draw
  });

  it("reads 'drew nothing' in the 2D readout during the dry draw", () => {
    const t = tl.start[3] + tl.travel[3] + tl.action[3] * 0.5;
    render(
      <Deck2D
        model={model}
        frame={frameAt(model, tl, cache, t, makeFrame(cache))}
        selected={null}
        onSelect={() => {}}
      />,
    );
    expect(
      screen.getByText(/^Tip A1 drew nothing: A1 in slot 8 is empty/),
    ).toBeInTheDocument();
  });
});
