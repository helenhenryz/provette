/* The Write composer: the model that writes, named in the toolbar; the button carries its own
   state. What a person made before lives in the sidebar's history (components/history.test.tsx). */

import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { HomePage, SHOWCASE } from "./Home";

const lists = {
  plans: [
    {
      id: "planA",
      request: "Make a 1:2 serial dilution of a drug in PBS over 12 wells.",
      technique: null,
      created: 5,
      state: "done",
      outcome: "proposed",
      tool_calls: 3,
      cost_usd: 0.004,
    },
  ],
  runs: [] as {
    run_id: string;
    request: string;
    created: number;
    state: string;
  }[],
};

vi.mock("../lib/api", () => ({
  ApiError: class extends Error {},
  judge: { get: () => "", requestUnlock: () => undefined },
  api: {
    episodes: () =>
      Promise.resolve({
        episodes: [],
        sets: [],
        current_sets: [],
        prices_read_on: null,
      }),
  },
  live: {
    status: () =>
      Promise.resolve({
        enabled: false,
        model: "m",
        model_label: "Nemotron 3 Test 1B",
        runner: "r",
        runner_label: "R",
        cap_usd: 1,
        spent_today_usd: 0,
        remaining_usd: 1,
        running: 0,
        examples: [],
      }),
    runs: () => Promise.resolve({ runs: lists.runs }),
    plans: () => Promise.resolve({ plans: lists.plans }),
    startPlan: vi.fn(),
  },
}));

function page() {
  return render(
    <MemoryRouter>
      <HomePage />
    </MemoryRouter>,
  );
}

describe("HomePage", () => {
  it("names the model that writes, as GET /api/live reports it, in the composer's toolbar", async () => {
    page();
    expect(await screen.findByText("Nemotron 3 Test 1B")).toBeInTheDocument();
    expect(screen.queryByText(/Written by/)).toBeNull();
    // no key on this deployment: the button carries its own state, and no sentence sits under it
    expect(
      screen.getByRole("button", { name: "Needs the key" }),
    ).toBeDisabled();
    expect(screen.queryByText(/Needs a Token Factory key/)).toBeNull();
  });

  it("links one finished run to watch, the gallery's 96-well qPCR plate", async () => {
    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    );
    const link = await screen.findByRole("link", { name: /watch a finished run/i });
    expect(link.getAttribute("href")).toBe(`/episodes/${SHOWCASE}`);
  });
});
