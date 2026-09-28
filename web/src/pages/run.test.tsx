/* The live run page: Stop beside the Running badge while the run goes (with the key), and the
   Stopped record with the steps so far once the stream says so. */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { RunSnapshot, Step } from "../lib/api";
import { episode } from "../test/fixtures";
import { RunResultPage } from "./RunResult";

const step: Step = {
  turn: 0,
  kind: "tool",
  tool: "platemap",
  title: "Read the plate map",
  detail: "",
  status: "ok",
  draft: null,
  seconds: 1.2,
  tokens_out: 100,
  reasoning_chars: 0,
  cut: false,
};
const snapshot: { current: RunSnapshot } = {
  current: {
    ...episode,
    outcome: null,
    state: "running",
    error: null,
    thinking: false,
    created: 1,
    steps: [step],
    draft_rows: [],
    tool_calls: 1,
    cost_usd: 0.001,
  } as RunSnapshot,
};
const { stopRun } = vi.hoisted(() => ({
  stopRun: vi.fn(() => Promise.resolve({ id: "r1", state: "stopping" })),
}));
vi.mock("../lib/api", async (importOriginal) => {
  const real = await importOriginal<typeof import("../lib/api")>();
  return {
    ...real,
    live: {
      ...real.live,
      snapshot: () => Promise.resolve(snapshot.current),
      stopRun,
    },
  };
});
vi.mock("../replay/Deck3D", () => ({
  Deck3D: () => <div data-testid="deck3d">3D</div>,
}));

class FakeSource {
  addEventListener() {}
  close() {}
  onerror: null | (() => void) = null;
}

function page() {
  return render(
    <MemoryRouter initialEntries={["/runs/r1"]}>
      <Routes>
        <Route path="/runs/:id" element={<RunResultPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("RunResultPage", () => {
  beforeEach(() => vi.stubGlobal("EventSource", FakeSource));
  afterEach(() => {
    vi.unstubAllGlobals();
    sessionStorage.removeItem("provette.judge");
    stopRun.mockClear();
  });

  it("offers Stop beside the Running badge with the key, then shows the Stopped record with the steps so far", async () => {
    const { unmount } = page();
    expect(await screen.findByText("Running")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Stop" })).toBeNull();
    unmount();
    sessionStorage.setItem("provette.judge", "k");
    const withKey = page();
    await userEvent
      .setup()
      .click(await screen.findByRole("button", { name: "Stop" }));
    await waitFor(() => expect(stopRun).toHaveBeenCalledWith("r1"));
    expect(screen.getByRole("button", { name: "Stopping…" })).toBeDisabled();
    withKey.unmount();
    snapshot.current = { ...snapshot.current, state: "stopped" };
    page();
    expect(
      await screen.findByText("Stopped", { selector: "span" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/stopped by you after 1 tool call/),
    ).toBeInTheDocument();
    expect(screen.getByText("Read the plate map")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Stop" })).toBeNull();
  });

  it("leaves the hash alone while the run goes, so the finished run opens on its replay", async () => {
    snapshot.current = { ...snapshot.current, state: "running" };
    window.history.replaceState(null, "", "/");
    page();
    expect(await screen.findByText("Running")).toBeInTheDocument();
    await new Promise((r) => setTimeout(r, 1200)); // past the hash's one-second timer
    expect(window.location.hash).toBe("");
  });
});
