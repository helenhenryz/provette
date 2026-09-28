/* Rendering tests of each component on the frozen episode files (tests/web/fixtures). */

import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import type { PlateMap } from "../lib/api";
import { analysis, episode, episodes, series } from "../test/fixtures";
import dil01Json from "../../../eval/platemaps/dil-01.json";
import { CodeView } from "./CodeView";
import { EpisodeCard } from "./EpisodeCard";
import { Findings } from "./Findings";
import { PlateGrid } from "./PlateGrid";
import { PrepSheet } from "./PrepSheet";
import { Timeline } from "./Timeline";
import { Badge } from "./vocabulary";

// the dil-01 plate map, which the series fixture (tests/fixtures/protocols/dil_series.py) was checked against
const dil01 = dil01Json as unknown as PlateMap;

describe("EpisodeCard", () => {
  it("shows the request (clamped to two lines, whole on hover), the model, the verdict, the cost and the time", () => {
    const card = episodes.episodes.find((e) => e.id === "super/plain/dil-03")!;
    render(
      <MemoryRouter>
        <EpisodeCard episode={card} />
      </MemoryRouter>,
    );
    expect(screen.getByTitle(card.request)).toBeInTheDocument();
    expect(screen.getByText(card.request)).toHaveAttribute(
      "title",
      card.request,
    );
    expect(screen.getByText(/Super/)).toBeInTheDocument();
    expect(screen.getByText("Verified")).toBeInTheDocument();
    expect(screen.getByRole("link")).toHaveAttribute(
      "href",
      "/episodes/super/plain/dil-03",
    );
    expect(screen.getByText(/¢|\$/)).toBeInTheDocument();
  });
});

describe("Badge", () => {
  it("says the state in words, never colour alone", () => {
    render(<Badge state="not_verified" />);
    expect(screen.getByText("Not verified")).toBeInTheDocument();
  });
});

describe("Timeline", () => {
  it("renders every step of the frozen transcript and opens a row to what the tool answered", async () => {
    render(
      <Timeline
        steps={episode.steps}
        drafts={episode.draft_rows}
        state="done"
        thinking={false}
      />,
    );
    const items = document.querySelectorAll('[data-row="step"]'); // a draft's findings are list items of their own
    expect(items).toHaveLength(episode.steps.length);
    expect(screen.getByText("Read the plate map")).toBeInTheDocument();
    const withDetail = episode.steps.find((s) => s.detail.trim().length > 0)!;
    await userEvent.click(screen.getByText(withDetail.title));
    expect(screen.getByText(withDetail.detail)).toBeInTheDocument();
  });
});

describe("Findings", () => {
  it("says so when there is nothing, and renders any finding shape", () => {
    const { rerender } = render(<Findings findings={[]} />);
    expect(
      screen.getByText("No rule fired on this protocol."),
    ).toBeInTheDocument();
    rerender(
      <Findings
        findings={[
          {
            rule_id: "NEW-RULE",
            severity: "warning",
            certain: true,
            line: 12,
            title: "A brand new finding",
            explanation: "Explained in words.",
            fix: "Do this.",
            extra_field: { anything: 1 },
          },
        ]}
      />,
    );
    expect(screen.getByText("A brand new finding")).toBeInTheDocument();
    expect(screen.getByText("NEW-RULE")).toBeInTheDocument();
    expect(screen.getByText("line 12")).toBeInTheDocument();
    expect(screen.getByText(/Do this\./)).toBeInTheDocument();
  });
});

describe("PlateGrid as the replay's plate", () => {
  it("draws the map with the replay's close-up, proposed wells dashed, and reads a well on hover", async () => {
    const map = structuredClone(dil01);
    map.variants[0].groups = [
      {
        name: "controls",
        members: [{ water: 5 }, { water: 5 }],
        within: null,
        position: "free",
        order_hint: null,
      },
    ];
    render(<PlateGrid platemap={map} />);
    expect(
      screen.getByRole("img", { name: /Close-up of slot 1/ }),
    ).toBeInTheDocument();
    const a1 = screen.getByRole("button", { name: "Well A1" });
    await userEvent.hover(a1);
    expect(screen.getAllByText(/Expected:/).length).toBeGreaterThan(0);
    const proposed = document.querySelectorAll('[class*="proposed"]');
    expect(proposed.length).toBeGreaterThanOrEqual(2);
  });
});

describe("PlateGrid", () => {
  it("draws the destination plate from the map, the check and the replay", () => {
    render(
      <PlateGrid
        platemap={dil01}
        verify={series.verify}
        replay={series.replay}
      />,
    );
    // the plate is the replay's own close-up, and the key counts the wells
    expect(
      screen.getByRole("img", { name: /Close-up of slot 1/ }),
    ).toBeInTheDocument();
    expect(screen.getByText(/ringed: 0 wells do not/)).toBeInTheDocument();
    // the twelve wells of the series hold liquid and the map's destination is named
    expect(screen.getByText(/NEST 96 Well Plate/)).toBeInTheDocument();
    expect(screen.getAllByText(/drug|pbs/i).length).toBeGreaterThan(0);
    expect(
      screen.getByText(/hold what the plate map says/),
    ).toBeInTheDocument();
  });

  it("draws a plate from the map alone: the pinned wells, unchecked", () => {
    render(<PlateGrid platemap={dil01} />);
    expect(screen.getByText(/12 wells planned/)).toBeInTheDocument();
    expect(screen.queryByText(/Hover or tap/)).toBeNull(); // the readout is empty until a well is hovered
    // no check ran, so nothing is said to hold, or not hold, what the map says
    expect(
      screen.queryByText(/hold what the plate map says/),
    ).not.toBeInTheDocument();
    expect(screen.queryByText(/do not/)).not.toBeInTheDocument();
  });

  it("lists a group whose wells may sit anywhere", () => {
    const map = structuredClone(dil01);
    map.variants[0].pinned = {};
    map.variants[0].groups = [
      {
        name: "series",
        members: [
          { drug: 50, pbs: 50 },
          { drug: 25, pbs: 75 },
        ],
        within: null,
        position: "free",
        order_hint: "index",
      },
    ];
    render(<PlateGrid platemap={map} />);
    expect(
      screen.getByText(/2 wells anywhere on the plate, in order/),
    ).toBeInTheDocument();
  });
});

describe("PrepSheet", () => {
  it("lists every line of the verify report's prep sheet and the tip count", () => {
    const verify = analysis.verify!;
    render(<PrepSheet prep={verify.prep} verify={verify} />);
    // one header row, one heading row per slot, one row per line
    const slots = new Set(
      verify.prep.lines.map((l) => `${l.slot}|${l.labware}`),
    ).size;
    const rows = within(
      screen.getByRole("table", { name: "What to load" }),
    ).getAllByRole("row");
    expect(rows).toHaveLength(1 + slots + verify.prep.lines.length);
    const tips = verify.prep.tips.reduce((n, t) => n + t.tips, 0);
    expect(
      screen.getAllByText(new RegExp(`${tips} tips?`)).length,
    ).toBeGreaterThan(0);
  });
});

describe("CodeView", () => {
  it("numbers the lines and marks the one asked for", () => {
    render(<CodeView text={"a\nb\nc\n"} marked={[2]} />);
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("b").closest("tr")?.className).toMatch(/hit/);
  });
});
