/* The sidebar's history: runs, plans that did not become a run, and checks, newest first, each
   linking to its page; a plan approved into a run is shown once, as the run. */

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { History } from "./History";

const now = Math.floor(Date.now() / 1000);

const removed: string[] = [];

vi.mock("../lib/api", () => ({
  ApiError: class extends Error {
    status = 0;
  },
  judge: { get: () => "key", requestUnlock: () => undefined },
  checkMemory: { last: { get: () => "", forget: () => undefined } },
  live: {
    remove: (kind: string, id: string) => {
      removed.push(`${kind}:${id}`);
      return Promise.resolve({ id, deleted: true });
    },
    runs: () =>
      Promise.resolve({
        runs: [
          {
            run_id: "run9",
            request: "Set up PCR reactions for 8 DNA samples. Each is 25 ul.",
            created: now - 10,
            state: "done",
            verified: true,
          },
        ],
      }),
    plans: () =>
      Promise.resolve({
        plans: [
          {
            id: "planA",
            request: "Set up PCR reactions for 8 DNA samples. Each is 25 ul.",
            technique: null,
            created: now - 60,
            state: "done",
            outcome: "proposed",
            tool_calls: 2,
            cost_usd: 0.004,
          },
          {
            id: "planB",
            request: "Make a 1:2 serial dilution of a drug in PBS.",
            technique: null,
            created: now - 5,
            state: "done",
            outcome: "proposed",
            tool_calls: 2,
            cost_usd: 0.004,
          },
        ],
      }),
  },
  checks: {
    list: () =>
      Promise.resolve({
        checks: [
          {
            id: "chk1",
            name: "pcr_buggy.py",
            created: now - 1,
            simulator: "passed",
            findings: 4,
            has_map: true,
          },
        ],
      }),
  },
}));

describe("History", () => {
  it("lists what was made, newest first, each linking to its page", async () => {
    render(
      <MemoryRouter>
        <History />
      </MemoryRouter>,
    );
    const check = await screen.findByRole("link", { name: /pcr_buggy\.py/ });
    expect(check).toHaveAttribute("href", "/check/chk1");
    expect(
      screen.getByRole("link", { name: /Make a 1:2 serial dilution/ }),
    ).toHaveAttribute("href", "/plan/planB");
    expect(
      screen.getByRole("link", {
        name: /Set up PCR reactions for 8 DNA samples/,
      }),
    ).toHaveAttribute("href", "/runs/run9");
    expect(screen.queryByRole("link", { name: /planA/ })).toBeNull();
    expect(screen.getAllByRole("link")).toHaveLength(3); // the approved plan is the run
    const names = screen
      .getAllByRole("link")
      .map((a) => a.getAttribute("href"));
    expect(names).toEqual(["/check/chk1", "/plan/planB", "/runs/run9"]);
  });
});

describe("History, the row menu", () => {
  it("deletes from the menu after asking in a dialog", async () => {
    render(
      <MemoryRouter>
        <History />
      </MemoryRouter>,
    );
    await userEvent.click(
      await screen.findByRole("button", { name: "More for pcr_buggy.py" }),
    );
    await userEvent.click(screen.getByRole("menuitem", { name: "Delete" }));
    expect(
      screen.getByRole("alertdialog", { name: "Delete this check?" }),
    ).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.queryByRole("alertdialog")).toBeNull();
    expect(removed).toEqual([]);
    await userEvent.click(
      screen.getByRole("button", { name: "More for pcr_buggy.py" }),
    );
    await userEvent.click(screen.getByRole("menuitem", { name: "Delete" }));
    await userEvent.click(screen.getByRole("button", { name: "Delete" }));
    expect(removed).toEqual(["check:chk1"]);
  });

  it("deleting a run takes the plan it was approved from, so it does not come back as a plan", async () => {
    removed.length = 0;
    render(
      <MemoryRouter>
        <History />
      </MemoryRouter>,
    );
    await userEvent.click(
      await screen.findByRole("button", {
        name: /More for Set up PCR reactions/,
      }),
    );
    await userEvent.click(screen.getByRole("menuitem", { name: "Delete" }));
    await userEvent.click(screen.getByRole("button", { name: "Delete" }));
    expect(removed).toEqual(["run:run9", "plan:planA"]); // planB is another request, left alone
  });

  it("pins a row to the top, in this browser, and unpins it", async () => {
    localStorage.clear();
    render(
      <MemoryRouter>
        <History />
      </MemoryRouter>,
    );
    await userEvent.click(
      await screen.findByRole("button", {
        name: /More for Set up PCR reactions/,
      }),
    );
    await userEvent.click(screen.getByRole("menuitem", { name: "Pin" }));
    expect(screen.getByText("Pinned")).toBeInTheDocument();
    expect(
      screen.getAllByRole("link").map((a) => a.getAttribute("href")),
    ).toEqual(["/runs/run9", "/check/chk1", "/plan/planB"]);
    expect(JSON.parse(localStorage.getItem("provette.pinned") ?? "[]")).toEqual(
      ["rrun9"],
    );
    await userEvent.click(
      screen.getByRole("button", { name: /More for Set up PCR reactions/ }),
    );
    await userEvent.click(screen.getByRole("menuitem", { name: "Unpin" }));
    expect(screen.queryByText("Pinned")).toBeNull();
  });
});
