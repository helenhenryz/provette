/* About, in the authors' words: what it does, the harness, and three results computed from the
   same evidence as Methods, never typed; nothing about how the authors met, and nothing that
   talks down to the people who use it. */

import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import type { Evidence } from "../lib/api";
import { AboutPage } from "./About";

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
        model_label: "Nemotron 3 Nano 30B",
        requests: 15,
        verified_end: 7,
        request_set: "the harder set",
      }),
      set("nano-best3", {
        model_label: "Nemotron 3 Nano 30B",
        verified_end: 28,
        clean_first: 1,
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

vi.mock("../lib/api", () => ({
  evidence: () => Promise.resolve(evidence),
  REPOSITORY: "",
}));

describe("AboutPage", () => {
  it("says what it does and how, with the results from the evidence", async () => {
    const { container } = render(
      <MemoryRouter>
        <AboutPage />
      </MemoryRouter>,
    );
    expect(
      await screen.findByRole("heading", { name: "What we found" }),
    ).toBeInTheDocument();
    const text = container.textContent ?? "";
    expect(text).toMatch(
      /verified protocol for 30 of 34 requests, at about 6 cents each, against 5 on its own and 4 with the same rules/,
    );
    expect(text).toMatch(/The much smaller Nano gets to 28\./);
    expect(text).toMatch(
      /of the 228 that change what a well ends up holding.*Provette caught 212/,
    );
    expect(text).toMatch(/no false alarm, across 986 wells/);
    expect(
      screen.getByRole("heading", { name: "What it does" }),
    ).toBeInTheDocument();
    expect(text).toMatch(/agent harness/);
    // the whole of it is theirs: what they built, not a part of someone else's
    expect(
      screen.getByRole("heading", { name: "What we built" }),
    ).toBeInTheDocument();
    expect(text).not.toMatch(
      /Our part|looked after the biology|small agent harness/,
    );
    // the biology rests on its sources, and says so
    expect(text).toMatch(/Every rule rests on a published source/);
    // the model is what the product runs on, never read as what built it
    expect(
      screen.getByRole("heading", { name: "What it runs on" }),
    ).toBeInTheDocument();
    expect(text).toMatch(
      /Nebius Token Factory plans and\s+writes the protocols/,
    );
    expect(screen.queryByRole("heading", { name: "Built with" })).toBeNull();
    expect(text).not.toMatch(/LinkedIn|met through|how we met|at our stage/i);
    // the names link to their profiles and the universities to their own sites, with no word
    // about where the links go
    expect(screen.getByRole("link", { name: "Helen" })).toHaveAttribute(
      "href",
      "https://www.linkedin.com/in/helen-henryz/",
    );
    expect(screen.getByRole("link", { name: "Nyle" })).toHaveAttribute(
      "href",
      "https://www.linkedin.com/in/nyle-hussain-b7ab05423/",
    );
    expect(
      screen.getByRole("link", { name: "Tampere University" }),
    ).toHaveAttribute("href", "https://www.tuni.fi/en");
    expect(
      screen.getByRole("link", { name: "University of Glasgow" }),
    ).toHaveAttribute("href", "https://www.gla.ac.uk/");
    // the hackathon, where it is named, links to its page
    for (const a of screen.getAllByRole("link", {
      name: "Nebius × NVIDIA Global AI Hackathon",
    }))
      expect(a).toHaveAttribute(
        "href",
        "https://nebiusglobalaihackathon.devpost.com/",
      );
  });
});
