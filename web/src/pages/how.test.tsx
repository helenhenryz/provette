/* Methods is the evidence, not the history: three questions, each answered in a sentence with
   its table, then one line to the repository's eval pages. No internal run names in the text,
   and nothing of the pasted-report era (E4) or the earlier runs. */

import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Evidence } from "../lib/api";
import { HowPage } from "./How";

const set = (
  name: string,
  extra: Partial<Evidence["agent"]["sets"][number]>,
): Evidence["agent"]["sets"][number] => ({
  set: name,
  model: "m",
  model_label: "Nemotron 3 Super 120B",
  requests: 34,
  pass_simulator_first: 30,
  clean_first: 5,
  problem_first: 25,
  verified_end: 30,
  repaired: 25,
  tokens_in: 1,
  tokens_out: 1,
  cost_usd: 1.68,
  per_verified_usd: 0.056,
  stop_reasons: {},
  run_label: "run 3",
  request_set: "the original set",
  source: `eval/agent/results/${name}/*/*/done.json`,
  ...extra,
});

const evidence: Evidence = {
  prices_read_on: "2026-09-22",
  prices_source: "eval/prices.json",
  checks: {
    sources: [
      "eval/checks/results/correct.json",
      "eval/checks/results/control.json",
      "eval/checks/results/mutants.json",
      "eval/checks/results/hand.json",
    ],
    correct: { protocols: 34, verified: 34, wells: 986 },
    control: { protocols: 34, verified: 0 },
    mutants: {
      generated: 279,
      pass_simulator: 242,
      equivalent: 10,
      change_the_deck: 232,
      caught: 212,
      missed: 20,
      missed_layout_swaps: 16,
      sample_lost: 31,
      sample_lost_caught: 31,
      by_operator: [],
    },
    hand: { protocols: 10, agree: 10 },
  },
  agent: {
    sets: [
      set("nano-hard-best3", {
        requests: 15,
        verified_end: 7,
        request_set: "the harder set",
      }),
      set("super", {}),
    ],
  },
  baseline: {
    run: "super-rules-in-prompt",
    model: "m",
    model_label: "Nemotron 3 Super 120B",
    requests: 34,
    pass_simulator_first: 25,
    clean_first: 4,
    problem_first: 21,
    verified_end: 4,
    repaired: 0,
    tokens_in: 1,
    tokens_out: 1,
    cost_usd: 0.4,
    source: "eval/baseline/results/super-rules-in-prompt/*/*/done.json",
    broke_rule: 17,
    map_mismatch: 12,
  },
  ledger: {
    library: 833,
    accepted: 788,
    compared: 788,
    agree: 788,
    independent: 16,
    independent_agree: 16,
    exported: 787,
    events: 974124,
    source: "eval/ledger/counts.json",
  },
  planner: {
    requests: 17,
    valid_map: 17,
    agree: 10,
    verify: 15,
    cost_usd: 0.05,
    tool_calls: [],
    source: "eval/planner/results/super/<id>.json",
  },
};

const repository = { url: "" };
vi.mock("../lib/api", () => ({
  evidence: () => Promise.resolve(evidence),
  get REPOSITORY() {
    return repository.url;
  },
}));

function page() {
  return render(
    <MemoryRouter>
      <HowPage />
    </MemoryRouter>,
  );
}

describe("HowPage", () => {
  afterEach(() => {
    repository.url = "";
  });

  it("says how the checks work, then answers the four questions from the numbers, without internal names", async () => {
    page();
    expect(
      await screen.findByRole("heading", {
        name: "Does a model write correct protocols with Provette?",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", {
        name: "Does Provette catch what the simulator passes?",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", {
        name: "Does it pass what is correct, and only that?",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("30 of 34", { selector: "strong" }),
    ).toBeInTheDocument(); // the headline set, sorted first
    expect(
      screen.getByText(/4 of 34 with the same rules written into its prompt/),
    ).toBeInTheDocument(); // the baseline
    expect(screen.getByText("228", { selector: "strong" })).toBeInTheDocument(); // 232 change the deck, 4 equivalent for the request
    expect(screen.getByText("212", { selector: "strong" })).toBeInTheDocument();
    expect(screen.getByText("15 of 17 verify")).toBeInTheDocument(); // the planner
    expect(screen.getAllByText("How we measured it")).toHaveLength(4);
    // how the checks work comes first, the terms beside it
    const headings = screen
      .getAllByRole("heading", { level: 2 })
      .map((h) => h.textContent);
    expect(headings.slice(0, 2)).toEqual(["How the checks work", "Terms"]);
    // the rules' evidence: told the rules, the model still broke them
    expect(screen.getByText("17", { selector: "strong" })).toBeInTheDocument();
    expect(document.body.textContent).toMatch(
      /of the 25 drafts the simulator passed, 17 broke a rule/,
    );
    // the ledger, against Opentrons' own analysis; independent from API 2.14, and says so
    expect(
      screen.getByRole("heading", { name: "Can the ledger be trusted?" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("788 of 788", { selector: "strong" }),
    ).toBeInTheDocument();
    expect(document.body.textContent).toMatch(/974,124 recorded/);
    expect(screen.getByText("16 of 16")).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/two independent readings/);
    // not flagged, split: nothing to catch and missed
    expect(
      screen.getByRole("columnheader", { name: "nothing to catch" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "missed" }),
    ).toBeInTheDocument();
    expect(screen.queryByText(/super/, { selector: "td, p, h2" })).toBeNull(); // run names are hovers and file paths only
    expect(screen.queryByText(/E4|E1 to E3|E5/)).toBeNull();
    expect(screen.queryByText("In words")).toBeNull();
    expect(screen.queryByText(/run 1 → run 2/)).toBeNull();
    expect(screen.queryByText(/under today's checks/)).toBeNull();
    // the last line names eval/ in plain text when the repository is not public
    expect(
      screen.getByText(
        /The earlier runs, every failure read by hand and the full tables:/,
      ),
    ).toHaveTextContent("the repository's eval/ pages.");
    expect(screen.queryByRole("link", { name: /eval pages/ })).toBeNull();
  });

  it("links the last line to the repository when the build names one", async () => {
    repository.url = "https://example.org/provette";
    page();
    const link = await screen.findByRole("link", {
      name: "the repository's eval pages",
    });
    expect(link).toHaveAttribute("href", "https://example.org/provette");
  });
});
