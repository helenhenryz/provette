/* The night's three pieces: the failed-run record, the map's arithmetic, the coverage panel;
   and the plan page, on a frozen planning result. */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import planJson from "../../../tests/web/fixtures/plan-free-group.json";
import type {
  Coverage,
  PlanSnapshot,
  PlateMap,
  PlateMapVariant,
} from "../lib/api";
import { dilutionStep, variantArithmetic, wellSum } from "../lib/plate";
import { PlanPage } from "../pages/Plan";
import { episode } from "../test/fixtures";
import dil01Json from "../../../eval/platemaps/dil-01.json";
import { ChecksList } from "./ChecksList";
import { OutcomeForm } from "./OutcomeForm";
import { PlateMapSums } from "./PlateMapSums";

// the dil-01 plate map, which the series fixture (tests/fixtures/protocols/dil_series.py) was checked against
const dil01 = dil01Json as unknown as PlateMap;

/* The plan page reads one snapshot; the rest of the API module is the real one. */
const planned = planJson as unknown as Omit<
  PlanSnapshot,
  | "id"
  | "request"
  | "technique"
  | "created"
  | "model"
  | "model_label"
  | "state"
  | "thinking"
>;
const snapshot: { current: PlanSnapshot } = {
  current: {
    ...planned,
    id: "p1",
    request: planned.platemap!.request,
    technique: null,
    created: 1,
    model: "m",
    model_label: "Nemotron 3 Super 120B",
    state: "done",
    thinking: false,
  },
};
const { stopPlan } = vi.hoisted(() => ({
  stopPlan: vi.fn(() => Promise.resolve({ id: "p1", state: "stopping" })),
}));
vi.mock("../lib/api", async (importOriginal) => {
  const real = await importOriginal<typeof import("../lib/api")>();
  return {
    ...real,
    live: {
      ...real.live,
      planSnapshot: () => Promise.resolve(snapshot.current),
      stopPlan,
    },
  };
});

/* jsdom has no EventSource; the page opens one while the planner runs. */
class FakeSource {
  addEventListener() {}
  close() {}
  onerror: null | (() => void) = null;
}

function planPage() {
  return render(
    <MemoryRouter initialEntries={["/plan/p1"]}>
      <Routes>
        <Route path="/plan/:id" element={<PlanPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

const done = (): PlanSnapshot => ({
  ...planned,
  id: "p1",
  request: planned.platemap!.request,
  technique: null,
  created: 1,
  model: "m",
  model_label: "Nemotron 3 Super 120B",
  state: "done",
  thinking: false,
});

describe("PlanPage", () => {
  beforeEach(() => {
    vi.stubGlobal("EventSource", FakeSource);
    snapshot.current = done();
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    sessionStorage.removeItem("provette.judge");
    stopPlan.mockClear();
  });

  it("says a message that is not a lab request is not one, with no map, and offers to plan it anyway", async () => {
    snapshot.current = {
      ...done(),
      request: "What is the purpose of life?",
      platemap: null,
      stop_reason: "not a request",
      declined: "It is a question, not a liquid-handling request.",
      rejections: [],
    };
    planPage();
    expect(await screen.findByText("Not a lab request")).toBeInTheDocument();
    expect(
      screen.getByText(
        /It is a question, not a liquid-handling request\. No plate map was made\./,
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "plan it anyway" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("No plate map")).toBeNull();
    expect(screen.queryByRole("button", { name: /Approve/ })).toBeNull();
  });

  it("offers Stop beside the Planning badge only while running and with the key, and says Stopped after", async () => {
    const running: PlanSnapshot = {
      ...snapshot.current,
      state: "running",
      platemap: null,
      stop_reason: null,
      tool_calls: 1,
      seconds: null,
    };
    snapshot.current = running;
    const { unmount } = planPage();
    expect(await screen.findByText("Planning")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Stop" })).toBeNull(); // no key: no button
    unmount();
    sessionStorage.setItem("provette.judge", "k");
    const withKey = planPage();
    const stop = await screen.findByRole("button", { name: "Stop" });
    await userEvent.setup().click(stop);
    await waitFor(() => expect(stopPlan).toHaveBeenCalledWith("p1"));
    expect(screen.getByRole("button", { name: "Stopping…" })).toBeDisabled();
    withKey.unmount();
    // the stream then reports the stopped record: the badge, the words, the steps so far
    snapshot.current = {
      ...running,
      state: "stopped",
      stop_reason: "stopped by the user",
      thinking: false,
    };
    planPage();
    expect(
      await screen.findByText("Stopped", { selector: "span" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/stopped by you after 1 tool call/),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Stop" })).toBeNull();
    expect(screen.getByText("Proposed the plate map")).toBeInTheDocument();
    expect(screen.queryByText(/could not write a map/)).toBeNull();
  });

  it("says why there is no map in plain words: the tries and the last problem, never the loop's own string", async () => {
    const refusal =
      "variant '40 samples', group 'samples': 'serum@A1' is not one of the map's liquids (declared: 'serum_{i}'). To use it, declare 'serum@{well}' in `liquids` with bind 'well'.";
    snapshot.current = {
      ...done(),
      platemap: null,
      stop_reason: "call budget",
      error: "no plate map: call budget. Last refusal: " + refusal,
      rejections: [refusal, refusal],
      tool_calls: 12,
    };
    const { unmount } = planPage();
    expect(await screen.findByText("No plate map")).toBeInTheDocument();
    expect(
      screen.getByText(
        /^The planner could not write a map in 2 tries\. The last problem: variant '40 samples'/,
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText(/no plate map: call budget/)).toBeNull();
    expect(
      screen.getByRole("button", { name: "propose again" }),
    ).toBeInTheDocument();
    expect(screen.getByText("No map")).toBeInTheDocument();
    unmount();
    // no proposal was ever handed in: what ran out, in words
    snapshot.current = {
      ...done(),
      platemap: null,
      stop_reason: "call budget",
      error: "no plate map: call budget.",
      rejections: [],
      tool_calls: 12,
    };
    planPage();
    expect(
      await screen.findByText(
        /^The planner never handed a map in: it used all 12 tool calls without handing one in\./,
      ),
    ).toBeInTheDocument();
  });

  it("keeps the planner's work under a fold once the map is proposed, with the calls, the time and the cost", async () => {
    planPage();
    const fold = (await screen.findByText("The planner's work")).closest(
      "details",
    )!;
    expect(screen.getByText("Proposed")).toBeInTheDocument();
    expect(fold).not.toBeNull();
    expect(fold.open).toBe(false);
    expect(fold).toHaveTextContent("1 tool call · 4 s · 0.2 ¢");
    // the timeline is inside it: the one step of the frozen result
    expect(fold).toHaveTextContent("Proposed the plate map");
    // and the plate is on the stage
    expect(screen.getByRole("radio", { name: "Wells" })).toBeChecked();
  });
});

describe("the map's arithmetic", () => {
  it("sums a well from the map's numbers and reads a 1:2 step", () => {
    expect(wellSum({ drug: 50, pbs: 50 })).toEqual({
      parts: [
        { name: "drug", ul: 50 },
        { name: "pbs", ul: 50 },
      ],
      total: 100,
      unknownParts: 0,
    });
    expect(wellSum({ bsa: "declared", bradford: 250 }).total).toBeNull();
    expect(dilutionStep({ drug: 50, pbs: 50 }, { drug: 25, pbs: 75 })).toBe(
      "1:2",
    );
    expect(
      dilutionStep({ drug: 50, pbs: 50 }, { drug: 50, pbs: 50 }),
    ).toBeNull();
    expect(
      dilutionStep({ compound: 90, dmso: 10 }, { compound: 30, dmso: 70 }),
    ).toBe("1:3");
  });

  it("lists the dilution series of the frozen map with sums and steps", () => {
    const rows = variantArithmetic(dil01.variants[0]);
    expect(rows[0].well).toBe("A1");
    expect(rows[0].sum.total).toBe(100);
    expect(rows[1].step).toBe("1:2");
    render(<PlateMapSums platemap={dil01} />);
    expect(screen.getAllByText("1:2 of the previous well").length).toBe(11);
  });

  it("folds identical reaction wells into one line", () => {
    const variant: PlateMapVariant = {
      name: "8 reactions",
      why: "",
      pinned: {},
      groups: [
        {
          name: "reactions",
          members: [1, 2, 3, 4].map((i) => ({
            master_mix: 20,
            [`sample_${i}`]: 5,
          })),
          within: null,
          position: "free",
          order_hint: "index",
        },
      ],
    };
    render(
      <PlateMapSums
        platemap={{ ...episode.platemap!, variants: [variant] }}
        compact
      />,
    );
    expect(screen.getByText("×4")).toBeInTheDocument();
    expect(screen.getByText("25 µl")).toBeInTheDocument();
  });
});

describe("ChecksList", () => {
  it("lists what was not checked as its own row, and the physics", () => {
    const data: Coverage = {
      technique: "PCR setup",
      matched: true,
      key: "PCR setup",
      available: true,
      source: "coverage.yaml",
      checked: ["Every reaction well holds the master mix and the sample."],
      not_checked: ["Whether the primers are right."],
      physics: ["Whether 2 µl is pipetted accurately."],
    };
    render(
      <ChecksList
        analysis={null}
        findings={[]}
        hasMap
        technique="PCR setup"
        preloaded={data}
      />,
    );
    expect(screen.getByText("Not checked")).toBeInTheDocument();
    expect(screen.getByText("1 for PCR setup")).toBeInTheDocument();
    expect(
      screen.getByText("Whether the primers are right."),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Physics not checked: Whether 2 µl/),
    ).toBeInTheDocument();
  });

  it("says when a technique has no list of its own", () => {
    const data: Coverage = {
      technique: "Bead cleanup",
      matched: false,
      key: "default",
      available: true,
      source: "coverage.yaml",
      checked: ["Every well holds what the plate map asks for."],
      not_checked: [],
      physics: [],
    };
    render(
      <ChecksList
        analysis={null}
        findings={[]}
        hasMap
        technique="Bead cleanup"
        preloaded={data}
      />,
    );
    expect(
      screen.getByText(/No list for Bead cleanup yet/),
    ).toBeInTheDocument();
  });
});

describe("OutcomeForm", () => {
  it("asks whether the run worked", () => {
    render(
      <MemoryRouter>
        <OutcomeForm episode="super/plain/pcr-01" />
      </MemoryRouter>,
    );
    expect(screen.getByText("Did this run work?")).toBeInTheDocument();
  });
});
