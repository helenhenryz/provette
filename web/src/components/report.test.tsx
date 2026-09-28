/* The run record lists verify's labware findings beside the rules' findings in its rail, with
   only a small label telling them apart, and its checks rows come from the analysis. */

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { analysis, episode } from "../test/fixtures";
import type { Analysis, Finding } from "../lib/api";
import { RunRecord } from "./RunRecord";

vi.mock("../replay/Deck3D", () => ({
  Deck3D: () => <div data-testid="deck3d">3D</div>,
}));

const labware: Finding = {
  rule_id: "LABWARE-FOR-TECHNIQUE",
  severity: "warning",
  certain: true,
  line: 12,
  title: "A PCR plate is used as the ELISA plate",
  explanation:
    "An ELISA is read through a flat, clear plate; a PCR plate is neither.",
  fix: "Load a flat 96-well plate as the destination.",
};

function record(a: Analysis, platemap = episode.platemap) {
  return render(
    <MemoryRouter>
      <RunRecord
        header={{
          crumb: { to: "/runs", label: "Runs" },
          crumbWord: "Serial dilution",
          title: episode.request,
          badge: "verified",
          meta: ["Nemotron 3 Super 120B", "run 3"],
        }}
        analysis={a}
        platemap={platemap}
        review={{ text: "from opentrons import protocol_api\n" }}
        links={{
          protocolUrl: "/p.py",
          protocolName: "p.py",
          replayUrl: "/r.html",
        }}
      />
    </MemoryRouter>,
  );
}

describe("RunRecord", () => {
  it("lists a labware finding from verify with the rules' findings and a small label", () => {
    const withLabware: Analysis = structuredClone(analysis);
    withLabware.check!.findings = [
      {
        ...labware,
        rule_id: "CONTAM-STOCK",
        title: "A used tip went into a stock",
        severity: "error",
      },
    ];
    withLabware.verify!.labware = [labware];
    record(withLabware);
    expect(
      screen.getByText("A used tip went into a stock"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("A PCR plate is used as the ELISA plate"),
    ).toBeInTheDocument();
    expect(screen.getAllByText("runs in verify")).toHaveLength(1);
    expect(screen.getByText("Findings")).toBeInTheDocument();
  });

  it("draws the checks as rows from the analysis: the plate map's wells, the biology, the simulator", () => {
    record(analysis);
    const wells = `${analysis.verify!.intent.wells_ok} of ${analysis.verify!.intent.wells_total} wells`;
    expect(screen.getByText(wells)).toBeInTheDocument();
    expect(screen.getByText("Simulator")).toBeInTheDocument();
    expect(screen.getByText(/passed$/)).toBeInTheDocument();
    // the stage opens on the replay, with the four tabs
    expect(screen.getByRole("tab", { name: /Replay/ })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(screen.getAllByRole("tab")).toHaveLength(4);
    // the stocks row: this run declares enough of both liquids
    expect(screen.getByText("Stocks")).toBeInTheDocument();
    expect(screen.getByText("enough declared")).toBeInTheDocument();
  });

  it("enables the prep sheet without a plate map, and says in the rail what would run dry", async () => {
    const user = userEvent.setup();
    // a check with no map: no verify, the analysis's own prep sheet with one stock drawn past what it declares
    const noMap: Analysis = structuredClone(analysis);
    noMap.verify = null;
    noMap.prep = {
      lines: [
        {
          slot: "2",
          labware: "tubes",
          well: "A1",
          liquid: "drug",
          declared_ul: 150,
          needed_ul: 300,
          flag: "would_run_dry",
          already_in_plate: false,
        },
        {
          slot: "4",
          labware: "reservoir",
          well: "A1",
          liquid: "pbs",
          declared_ul: 2000,
          needed_ul: 1100,
          flag: null,
          already_in_plate: false,
        },
      ],
      tips: [{ slot: "1", rack: "Opentrons OT-2 96 Tip Rack 300 µL", tips: 3 }],
    };
    record(noMap, null);
    expect(screen.getByText("1 would run dry")).toBeInTheDocument();
    expect(screen.getByText("none given")).toBeInTheDocument(); // the plate map row
    const tab = screen.getByRole("tab", { name: "Prep sheet" });
    expect(tab).not.toBeDisabled();
    await user.click(tab);
    expect(
      screen.getByRole("table", { name: "What to load" }),
    ).toBeInTheDocument();
    expect(screen.getByText("would run dry")).toBeInTheDocument();
    expect(
      screen.getByRole("table", { name: "What to load" }).parentElement
        ?.textContent,
    ).toContain("3 from Opentrons OT-2 96 Tip Rack 300 µL in slot 1");
  });

  it("says when no stock was declared, and leaves the row out of an analysis made before the sheet", () => {
    const none: Analysis = structuredClone(analysis);
    none.verify = null;
    none.prep = {
      lines: [
        {
          slot: "2",
          labware: "tubes",
          well: "A1",
          liquid: "",
          declared_ul: null,
          needed_ul: 300,
          flag: "draws_air",
        },
      ],
      tips: [],
    };
    const { unmount } = record(none, null);
    expect(screen.getByText("none declared")).toBeInTheDocument();
    unmount();
    const before: Analysis = structuredClone(analysis);
    before.verify = null;
    delete before.prep;
    record(before, null);
    expect(screen.queryByText("Stocks")).toBeNull();
    expect(screen.getByRole("tab", { name: "Prep sheet" })).toBeDisabled();
  });
});
