/* The 2D view and the component around it, on the frozen episode file. The 3D view is
   replaced by a stub here: jsdom has no WebGL (scene.test.ts holds its data layer). The
   clock's requestAnimationFrame is driven by hand. */

import { act, fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { series as analysis } from "../test/fixtures";
import { Deck2D } from "./Deck2D";
import { buildModel } from "./model";
import { Replay } from "./Replay";
import { StateCache, heightAt, stepOfFinding } from "./state";
import { buildTimeline, frameAt, makeFrame, type Frame } from "./timeline";

vi.mock("./Deck3D", () => ({
  Deck3D: () => <div data-testid="deck3d">3D</div>,
}));

const data = analysis.replay!;
const model = buildModel(data);
const cache = new StateCache(data);
const tl = buildTimeline(model, cache);

function at(t: number): Frame {
  return frameAt(model, tl, cache, t, makeFrame(cache));
}
const midAction = (i: number, p = 0.5) =>
  tl.start[i] + tl.travel[i] + tl.action[i] * p;

describe("Deck2D", () => {
  it("draws the deck's twelve slots and every labware, and follows the pipette to its labware", () => {
    render(
      <Deck2D
        model={model}
        frame={at(midAction(1))}
        selected={null}
        onSelect={() => {}}
      />,
    );
    const deck = screen.getByRole("img", { name: "The deck, seen from above" });
    expect(within(deck).getAllByRole("button")).toHaveLength(
      data.deck.labware.length,
    );
    // event 1 aspirates from tube A1 in slot 2: the close-up opens that rack
    expect(
      screen.getByRole("img", { name: /Close-up of slot 2/ }),
    ).toBeInTheDocument();
    const a1 = screen.getByRole("button", { name: "Well A1" });
    expect(a1).toHaveAttribute("data-acted", "true");
    // the tip above it holds half of the 200 µl
    const tip = document.querySelector('[data-tip="on"]')!;
    expect(tip).not.toBeNull();
    expect(Number(tip.getAttribute("data-held"))).toBeCloseTo(100);
    expect(screen.getByText("100 µl")).toBeInTheDocument();
  });

  it("fills a well with its liquid in proportion, growing as the dispense goes, and reads it in words on hover", async () => {
    const user = userEvent.setup();
    const { rerender } = render(
      <Deck2D
        model={model}
        frame={at(midAction(2, 0.25))}
        selected={null}
        onSelect={() => {}}
      />,
    );
    // event 2 dispenses 200 µl of drug into well A1 of the plate in slot 3
    expect(
      screen.getByRole("img", { name: /Close-up of slot 3/ }),
    ).toBeInTheDocument();
    let a1 = screen.getByRole("button", { name: "Well A1" });
    let band = a1.querySelector('rect[data-band="drug"]')!;
    expect(band).not.toBeNull();
    // 50 µl: at the height the well's own table gives it (a V-bottom PCR well), of the 5.34 mm drawing
    const g = model.byId
      .get("3:nest_96_wellplate_100ul_pcr_full_skirt")!
      .wells.find((w) => w.name === "A1")!.geometry;
    const level = (ul: number) => heightAt(g.height_at_ul!, ul) / g.depth!;
    expect(level(50)).toBeGreaterThan(0.3);
    expect(level(50)).toBeLessThan(0.5);
    expect(Number(band.getAttribute("height"))).toBeCloseTo(5.34 * level(50));
    expect(band.getAttribute("fill")).toMatch(/^url\(#.*-band-0\)$/); // the liquid's gradient, darker at its bottom
    expect(a1.querySelector("rect[data-surface]")).not.toBeNull(); // and a lighter line along the surface
    expect(Number(a1.getAttribute("data-volume"))).toBeCloseTo(50);
    rerender(
      <Deck2D
        model={model}
        frame={at(midAction(2, 0.999))}
        selected={null}
        onSelect={() => {}}
      />,
    );
    a1 = screen.getByRole("button", { name: "Well A1" });
    band = a1.querySelector('rect[data-band="drug"]')!;
    expect(Number(band.getAttribute("height"))).toBeCloseTo(
      5.34 * level(200),
      1,
    ); // 200 µl in a 100 µl well: nearly to the brim
    await user.hover(a1);
    expect(screen.getByText(/Well A1 in slot 3: /)).toBeInTheDocument();
    // B2 is never named by the trace: drawn empty, and not a button (there is nothing to read)
    const b2 = document.querySelector('[data-well="B2"]')!;
    expect(b2).not.toBeNull();
    expect(b2.querySelector("rect[data-band]")).toBeNull();
    expect(b2.getAttribute("role")).toBeNull();
  });

  it("shows the pipette travelling between labware, with the gantry on the overview", () => {
    // half-way through the move of event 2: between slot 2 and slot 3, over neither close-up
    const t = tl.start[2] + tl.rise[2] + tl.move[2] * 0.5;
    render(
      <Deck2D
        model={model}
        frame={at(t)}
        selected={null}
        onSelect={() => {}}
      />,
    );
    expect(document.querySelector('[data-tip="on"]')).toBeNull(); // not over the close-up's labware yet
    const deck = screen.getByRole("img", { name: "The deck, seen from above" });
    expect(deck.querySelector("line")).not.toBeNull(); // the beam
    expect(screen.getByRole("button", { name: "Well A1" })).not.toHaveAttribute(
      "data-acted",
    );
  });

  it("shows a tip rack losing its tips, and a pinned labware stays", () => {
    const onSelect = vi.fn();
    const rack = "1:opentrons_96_tiprack_300ul";
    const { rerender } = render(
      <Deck2D
        model={model}
        frame={at(midAction(0, 0.75))}
        selected={rack}
        onSelect={onSelect}
      />,
    );
    expect(
      screen.getByRole("img", { name: /Close-up of slot 1/ }),
    ).toBeInTheDocument();
    const a1 = screen.getByRole("button", { name: "Tip A1" });
    const b1 = screen.getByRole("button", { name: "Tip B1" });
    expect(a1.querySelector("rect[clip-path]")).toBeNull(); // picked up: the spot is empty
    expect(b1.querySelector("rect[clip-path]")).not.toBeNull(); // still fresh
    rerender(
      <Deck2D
        model={model}
        frame={at(midAction(0, 0.25))}
        selected={rack}
        onSelect={onSelect}
      />,
    );
    expect(
      screen
        .getByRole("button", { name: "Tip A1" })
        .querySelector("rect[clip-path]"),
    ).not.toBeNull(); // not yet
    rerender(
      <Deck2D
        model={model}
        frame={at(midAction(1))}
        selected={rack}
        onSelect={onSelect}
      />,
    );
    expect(
      screen.getByRole("img", { name: /Close-up of slot 1/ }),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Slot 3:/ }));
    expect(onSelect).toHaveBeenCalledWith(
      "3:nest_96_wellplate_100ul_pcr_full_skirt",
    );
  });

  it("opens the bin as the close-up while a tip drops, with the count, and goes back to the plate after", () => {
    const drop = data.events.findIndex((e) => e.op === "drop_tip");
    // three quarters through the drop: the tip has left the pipette and is falling into the pile
    const { rerender } = render(
      <Deck2D
        model={model}
        frame={at(midAction(drop, 0.75))}
        selected={null}
        onSelect={() => {}}
      />,
    );
    const bin = screen.getByRole("img", { name: /Close-up of slot 12: Trash/ });
    expect(bin).toBeInTheDocument();
    expect(within(bin).getByText("1 tip")).toBeInTheDocument();
    expect(bin.querySelectorAll("polygon[class*='droppedTip']")).toHaveLength(
      1,
    );
    expect(document.querySelector('[data-tip="on"]')).toBeNull(); // the tip is off the pipette
    // a quarter through: the tip is still on the pipette, over the bin, and nothing is in the pile yet
    rerender(
      <Deck2D
        model={model}
        frame={at(midAction(drop, 0.25))}
        selected={null}
        onSelect={() => {}}
      />,
    );
    expect(
      screen.getByRole("img", { name: /Close-up of slot 12/ }),
    ).toBeInTheDocument();
    expect(document.querySelector('[data-tip="on"]')).not.toBeNull();
    expect(
      screen
        .getByRole("img", { name: /Close-up of slot 12/ })
        .querySelectorAll("polygon[class*='droppedTip']"),
    ).toHaveLength(0);
    // the event after: the close-up is the labware the pipette goes to, not the bin
    rerender(
      <Deck2D
        model={model}
        frame={at(midAction(drop + 1))}
        selected={null}
        onSelect={() => {}}
      />,
    );
    expect(
      screen.queryByRole("img", { name: /Close-up of slot 12/ }),
    ).toBeNull();
  });

  it("outlines a finding's wells", () => {
    const finding = data.findings[0];
    render(
      <Deck2D
        model={model}
        frame={at(midAction(finding.root_event!))}
        selected={null}
        onSelect={() => {}}
        highlight={{
          wells: finding.well_index,
          downstream: finding.downstream_index,
        }}
      />,
    );
    const a1 = screen.getByRole("button", { name: "Well A1" });
    expect(a1.className.baseVal ?? a1.getAttribute("class")).toMatch(/marked/);
  });
});

/* requestAnimationFrame by hand: `frames(n, ms)` runs n frames ms apart. */
let queue: FrameRequestCallback[] = [];
let clock = 0;
beforeEach(() => {
  queue = [];
  clock = 0;
  vi.spyOn(window, "requestAnimationFrame").mockImplementation((cb) => {
    queue.push(cb);
    return queue.length;
  });
  vi.spyOn(window, "cancelAnimationFrame").mockImplementation(() => {
    queue = [];
  });
  vi.spyOn(performance, "now").mockImplementation(() => clock);
});
afterEach(() => vi.restoreAllMocks());
function frames(n: number, ms: number) {
  for (let k = 0; k < n; k++) {
    clock += ms;
    const cbs = queue;
    queue = [];
    act(() => cbs.forEach((cb) => cb(clock)));
  }
}

describe("Replay", () => {
  it("says the event in motion and lets the parent hold the step", async () => {
    const user = userEvent.setup();
    const onStep = vi.fn();
    render(<Replay data={data} step={1} onStep={onStep} />);
    expect(
      screen.getByText(
        "line 34 · aspirate 200 µl of drug from tube A1 in slot 2, tip A1",
      ),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("The deck replay")).toHaveAttribute(
      "data-step",
      "1",
    );
    expect(screen.getByLabelText("The deck replay")).toHaveAttribute(
      "data-time",
      tl.start[1].toFixed(2),
    );
    await user.click(screen.getByRole("button", { name: "Step forward" }));
    expect(onStep).toHaveBeenLastCalledWith(2);
    await user.click(screen.getByRole("button", { name: "Step back" }));
    expect(onStep).toHaveBeenLastCalledWith(1);
    await user.click(screen.getByRole("button", { name: "Last step" }));
    expect(onStep).toHaveBeenLastCalledWith(data.events.length);
    expect(screen.getByText(/^end of run · \d+ events$/)).toBeInTheDocument();
    expect(screen.getByTestId("deck3d")).toBeInTheDocument();
  });

  it("jumps to a finding at the start of its event's motion", () => {
    const f = data.findings[0];
    const step = stepOfFinding(data, f);
    render(
      <Replay
        data={data}
        step={step}
        highlight={{ wells: f.well_index }}
        view="2d"
      />,
    );
    const el = screen.getByLabelText("The deck replay");
    expect(el).toHaveAttribute("data-step", String(f.root_event));
    expect(el).toHaveAttribute("data-time", tl.start[f.root_event!].toFixed(2));
    expect(el).toHaveAttribute("data-phase", "travel");
  });

  it("keeps its own step without a parent, scrubs over time, and answers the keys", async () => {
    const user = userEvent.setup();
    render(<Replay data={data} view="2d" />);
    const el = screen.getByLabelText("The deck replay");
    expect(el).toHaveAttribute("data-step", "0");
    expect(screen.queryByTestId("deck3d")).toBeNull();
    await user.click(screen.getByRole("button", { name: "Step forward" }));
    await user.click(screen.getByRole("button", { name: "Step forward" }));
    expect(el).toHaveAttribute("data-step", "2");
    el.focus();
    await user.keyboard("{ArrowRight}");
    expect(el).toHaveAttribute("data-step", "3");
    await user.keyboard("{Home}");
    expect(el).toHaveAttribute("data-step", "0");
    fireEvent.change(screen.getByRole("slider", { name: "Time" }), {
      target: { value: "500" },
    });
    expect(Number(el.getAttribute("data-time"))).toBeCloseTo(tl.total / 2, 1);
    expect(el).toHaveAttribute(
      "data-step",
      String(
        Math.max(
          0,
          Math.min(data.events.length, Number(el.getAttribute("data-step"))),
        ),
      ),
    );
  });

  it("plays at the chosen speed, crossing events as the clock runs, and stops at the end", () => {
    render(<Replay data={data} view="2d" speed={1} />);
    const el = screen.getByLabelText("The deck replay");
    fireEvent.click(screen.getByRole("button", { name: "Play" }));
    expect(screen.getByRole("button", { name: "Pause" })).toBeInTheDocument();
    frames(1, 16);
    expect(Number(el.getAttribute("data-time"))).toBeCloseTo(0.016, 2);
    // to a moment inside event 1's action
    const target = tl.start[1] + tl.travel[1] + tl.action[1] / 2;
    const steps = Math.ceil((target - 0.016) / 0.016);
    frames(steps, 16);
    expect(el).toHaveAttribute("data-step", "1");
    expect(el).toHaveAttribute("data-phase", "action");
    fireEvent.change(screen.getByRole("combobox", { name: "Speed" }), {
      target: { value: "8" },
    });
    frames(Math.ceil(tl.total / (0.1 * 8)) + 2, 100); // a frame longer than 100 ms counts as 100 ms
    expect(Number(el.getAttribute("data-time"))).toBeCloseTo(tl.total, 1);
    expect(el).toHaveAttribute("data-step", String(data.events.length));
    expect(screen.getByRole("button", { name: "Play" })).toBeInTheDocument();
  });

  it("plays from the start on its own when asked, and waits for a reader who asked for reduced motion", () => {
    const { unmount } = render(<Replay data={data} view="2d" autoPlay />);
    expect(screen.getByRole("button", { name: "Pause" })).toBeInTheDocument();
    expect(screen.getByLabelText("The deck replay")).toHaveAttribute(
      "data-step",
      "0",
    );
    unmount();
    vi.stubGlobal("matchMedia", () => ({ matches: true }));
    render(<Replay data={data} view="2d" autoPlay />);
    expect(screen.getByRole("button", { name: "Play" })).toBeInTheDocument();
    vi.unstubAllGlobals();
  });

  it("lists the liquids with their colours and marks the findings on the scrubber", () => {
    render(<Replay data={data} view="2d" />);
    const legend = screen.getByRole("list", { name: "Liquids" });
    // one row per liquid, plus the two swatches the ledger's drawing needs: film only, not tracked
    expect(within(legend).getAllByRole("listitem")).toHaveLength(
      data.origins.length + 2,
    );
    expect(within(legend).getByText("drug")).toBeInTheDocument();
    const marks = document.querySelectorAll("svg line[class*='mark']");
    expect(marks.length).toBe(
      data.findings.filter((f) => f.root_event != null).length,
    );
  });
});
