/* The rail's checks list opens its Not-checked fold on the verdict in words (the badge's
   sentence), so a reader who never hovers the badge reads what "Verified" means first. */

import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { Coverage } from "../lib/api";
import { analysis, series } from "../test/fixtures";
import { ChecksList } from "./ChecksList";

const coverage: Coverage = {
  technique: "Serial dilution",
  matched: true,
  key: "serial_dilution",
  available: true,
  source: "provette/rules/coverage.yaml",
  checked: ["CONTAM-STOCK"],
  not_checked: [
    "the pipetting order of the standards",
    "evaporation from the plate",
  ],
  physics: ["viscosity"],
};

describe("ChecksList", () => {
  it("puts the verdict sentence first inside the Not-checked fold, closed", () => {
    const sentence =
      "Verified: draft 2 passed the simulator, holds what the plate map says in every well, and has no biology problems.";
    render(
      <ChecksList
        analysis={analysis}
        findings={[]}
        hasMap
        technique="Serial dilution"
        preloaded={coverage}
        verdict={sentence}
      />,
    );
    const line = screen.getByText(sentence);
    const fold = line.closest("details");
    expect(fold).not.toBeNull();
    expect(fold).not.toHaveAttribute("open");
    expect(line.parentElement!.firstElementChild).toBe(line); // before the list of what is not checked
    expect(
      screen.getByText("the pipetting order of the standards"),
    ).toBeInTheDocument();
    expect(screen.getByText("Not checked")).toBeInTheDocument();
  });

  it("draws the fold without the line when there is no verdict yet", () => {
    render(
      <ChecksList
        analysis={analysis}
        findings={[]}
        hasMap
        technique="Serial dilution"
        preloaded={coverage}
      />,
    );
    expect(screen.queryByText(/^Verified:/)).toBeNull();
    expect(screen.getByText("Not checked")).toBeInTheDocument();
  });

  it("opens Biology to the rules that ran, each passed or with what it found, a finding one click away", async () => {
    const onFinding = vi.fn();
    const findings = series.check!.findings;
    render(
      <ChecksList
        analysis={series}
        findings={findings}
        hasMap
        technique="Serial dilution"
        preloaded={{
          ...coverage,
          checked: ["WELL-CAPACITY: a well filled past its rim"],
        }}
        onFinding={onFinding}
      />,
    );
    const biology = screen.getByRole("button", { name: /Biology/ });
    expect(biology).toHaveAttribute("aria-expanded", "false");
    await userEvent.click(biology);
    expect(biology).toHaveAttribute("aria-expanded", "true");
    const ran = series.check!.rules.length + (series.verify ? 1 : 0);
    expect(
      screen.getByText(`${ran} rules ran on this protocol`),
    ).toBeInTheDocument();
    // the technique's own words where coverage.yaml has them
    const capacity = screen.getByText("WELL-CAPACITY").closest("li")!;
    expect(
      within(capacity).getByText("a well filled past its rim"),
    ).toBeInTheDocument();
    const count = findings.filter((f) => f.rule_id === "WELL-CAPACITY").length;
    await userEvent.click(within(capacity).getByRole("button"));
    expect(onFinding).toHaveBeenCalledWith("WELL-CAPACITY");
    expect(within(capacity).getByRole("button").textContent).toMatch(
      new RegExp(`^${count} `),
    );
    // a rule that found nothing reads as passed
    const clean = screen.getByText("CONTAM-STOCK").closest("li")!;
    expect(within(clean).getByText("passed")).toBeInTheDocument();
  });

  it("opens Simulator to what ran it, and sends Plate map and Stocks to their tabs", async () => {
    const onOpenTab = vi.fn();
    render(
      <ChecksList
        analysis={series}
        findings={[]}
        hasMap
        technique="Serial dilution"
        preloaded={coverage}
        prep={series.prep}
        onOpenTab={onOpenTab}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: /Simulator/ }));
    expect(screen.getByText("8.8.2")).toBeInTheDocument();
    expect(
      screen.getByText(
        new RegExp(`${series.replay!.events.length} liquid steps`),
      ),
    ).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Plate map/ }));
    expect(onOpenTab).toHaveBeenCalledWith("platemap");
    if (series.prep) {
      await userEvent.click(screen.getByRole("button", { name: /Stocks/ }));
      expect(onOpenTab).toHaveBeenCalledWith("prep");
    }
  });
});
