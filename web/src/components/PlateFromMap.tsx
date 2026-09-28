import { useMemo, useState } from "react";
import type { ReplayExport, WellRow } from "../lib/api";
import type { PlateView } from "../lib/plate";
import { wellRowCol } from "../lib/plate";
import { buildModel, LabwareCloseup, StateCache } from "../replay";

/* The plate map drawn with the replay's own close-up, so the map she approves and the plate
   she gets after the run are one drawing: the same wells, the same bands, the same tokens.
   A well the check found wrong is ringed (`marked`, as a finding's well is in the replay).
   The map has no deck, so a plate of the map's size is made up (a standard 96- or 384-well
   footprint) and filled with what each well should hold; a free group's proposed wells are
   dashed. */
export function PlateFromMap({
  view,
  onHover,
}: {
  view: PlateView;
  onHover: (well: string | null) => void;
}) {
  const { data, byIndex, proposed, marked } = useMemo(
    () => synthesise(view),
    [view],
  );
  const model = useMemo(() => buildModel(data), [data]);
  const state = useMemo(() => new StateCache(data).at(0), [data]);
  const [, setHovered] = useState<number | null>(null);
  const labware = model.labware[0];
  if (!labware) return null;
  return (
    <LabwareCloseup
      model={model}
      labware={labware}
      state={state}
      event={null}
      acted={new Set()}
      marked={marked}
      reached={new Set()}
      proposed={proposed}
      onHover={(i) => {
        setHovered(i);
        onHover(i == null ? null : (byIndex.get(i) ?? null));
      }}
    />
  );
}

const ID = "map:plate";

/* Opentrons' standard footprints: 127.76 × 85.48 mm; a 96-well plate pitches 9 mm from A1 at
   (14.38, 74.24), a 384-well plate 4.5 mm from (12.13, 76.24). */
function synthesise(view: PlateView): {
  data: ReplayExport;
  byIndex: Map<number, string>;
  proposed: Set<number>;
  marked: Set<number>;
} {
  const dense = view.cols > 12 || view.rows > 8;
  const pitch = dense ? 4.5 : 9;
  const x0 = dense ? 12.13 : 14.38;
  const y0 = dense ? 76.24 : 74.24;
  const d = dense ? 3.3 : 5.5;
  const max = dense ? 100 : 200;
  const legendIndex = new Map(view.legend.map((l, i) => [l.name, i]));
  const wells: string[] = [];
  const geometry: Record<
    string,
    ReplayExport["deck"]["labware"][number]["wells"][string]
  > = {};
  const initial: Record<string, WellRow> = {};
  const byIndex = new Map<number, string>();
  const proposed = new Set<number>();
  const marked = new Set<number>();
  for (const cell of view.cells) {
    const rc = wellRowCol(cell.well);
    if (!rc) continue;
    const index = wells.length;
    wells.push(`${ID}[${cell.well}]`);
    byIndex.set(index, cell.well);
    geometry[cell.well] = {
      x: x0 + rc.col * pitch,
      y: y0 - rc.row * pitch,
      shape: "circular",
      d,
      w: null,
      h: null,
      depth: 15,
      max,
    };
    // what the well does hold once the run is checked, else what the map says it should
    const holdings = cell.found ?? cell.expected ?? [];
    if (holdings.length) {
      const bands = holdings.map(
        (h) =>
          [
            legendIndex.get(h.name) ?? 0,
            h.carryOver ? null : h.ul,
            h.carryOver ? 1 : 0,
            1,
          ] as WellRow[2][number],
      );
      const volumes = holdings.filter((h) => !h.carryOver);
      const known = volumes.every((h) => h.ul != null);
      initial[String(index)] = [
        known ? volumes.reduce((n, h) => n + (h.ul ?? 0), 0) : null,
        max,
        bands,
      ];
    }
    if (cell.status === "proposed") proposed.add(index);
    if (cell.status === "mismatch") marked.add(index);
  }
  const data: ReplayExport = {
    schema_version: 1,
    protocol: "",
    api_level: "",
    opentrons_version: "",
    source: [],
    deck: {
      width: 127.76,
      height: 85.48,
      slots: [{ id: "1", x: 0, y: 0, width: 127.76, height: 85.48 }],
      labware: [
        {
          id: ID,
          slot: "1",
          name: view.destinationName ?? "the destination plate",
          load_name: dense ? "corning_384_wellplate" : "corning_96_wellplate",
          is_tiprack: false,
          is_trash: false,
          module: null,
          kind: "plate",
          measured: true,
          slot_x: 0,
          slot_y: 0,
          w: 127.76,
          h: 85.48,
          ox: 0,
          oy: 0,
          wells: geometry,
        },
      ],
    },
    pipettes: [],
    wells,
    origins: view.legend.map((l) => ({
      well: 0,
      name: l.name,
      declared: true,
      place: "the plate map",
      volume: null,
      colour: l.colour,
    })),
    events: [],
    initial,
    deltas: [],
    cache_every: 50,
    findings: [],
    summary: { simulator: "", check: "", verify: null, counts: {}, events: 0 },
    verify: null,
  };
  return { data, byIndex, proposed, marked };
}
