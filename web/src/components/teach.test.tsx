/* The two ways the product learns from the verdict page: an unplaced liquid placed, a rule
   declared. Rendering only; the API is tested in tests/api. */

import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

vi.mock("../replay/Deck3D", () => ({
  Deck3D: () => <div data-testid="deck3d">3D</div>,
}));
import type { Analysis } from "../lib/api";
import { analysis, episode } from "../test/fixtures";
import { RunRecord } from "./RunRecord";
import { UnplacedLiquids } from "./UnplacedLiquids";

const lysozyme = {
  name: "lysozyme",
  description: "lysozyme stock",
  wells: ["A1 in slot 2"],
  line: 12,
  sentence:
    "I do not know what 'lysozyme' is (declared at line 12): tell me whether it is a sample, a reagent, a carrier, an enzyme to add last, or a diluent to add first.",
};

describe("UnplacedLiquids", () => {
  it("asks about each unplaced liquid with five answers, and nothing when there are none", () => {
    const { rerender } = render(
      <UnplacedLiquids liquids={[lysozyme]} onTaught={() => undefined} />,
    );
    expect(screen.getByText("‘lysozyme’")).toBeInTheDocument();
    expect(
      screen.getByText("“lysozyme stock” · line 12 · in A1 in slot 2"),
    ).toBeInTheDocument();
    expect(screen.queryByText(/I do not know what/)).toBeNull(); // the question is the card's shape, not a sentence
    expect(
      screen
        .getAllByRole("button")
        .filter((b) => b.textContent && !/…/.test(b.textContent)),
    ).toHaveLength(5);
    expect(screen.getByText("an enzyme: add last")).toBeInTheDocument();
    rerender(<UnplacedLiquids liquids={[]} onTaught={() => undefined} />);
    expect(screen.queryByText("‘lysozyme’")).not.toBeInTheDocument();
  });

  it("appears on the verdict when the check reports one", () => {
    const withUnplaced: Analysis = structuredClone(analysis);
    withUnplaced.check!.unplaced_liquids = [lysozyme];
    render(
      <MemoryRouter>
        <RunRecord
          header={{
            crumb: { to: "/runs", label: "Runs" },
            crumbWord: "x",
            title: "x",
            badge: "verified",
            meta: [],
          }}
          analysis={withUnplaced}
          platemap={episode.platemap}
          review={{ text: "" }}
          links={{
            protocolUrl: "/p.py",
            protocolName: "p.py",
            replayUrl: "/r.html",
          }}
          onTaught={() => undefined}
        />
      </MemoryRouter>,
    );
    expect(screen.getByText("Unplaced liquids")).toBeInTheDocument();
  });
});
