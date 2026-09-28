/* What a plate-map grid shows: for every well of the destination plate, what the map says it
   should hold, what the replay says it does hold, and whether the check agreed.

   Sources, in order of trust: `verify.intent.wells` when provette lists every checked well
   (docs/ui-needs.md #1); otherwise the map's pinned wells for the expectation, the replay's
   final state for the contents, and `verify.intent.mismatches` for what is wrong. A group whose
   members may sit anywhere is listed beside the grid, not placed on it. */

import type {
  Contents,
  PlateMap,
  PlateMapGroup,
  PlateMapVariant,
  ReplayExport,
  VerifyMismatch,
  VerifyReport,
} from "./api";
import { finalState, wellsOf } from "./replayState";

export interface Holding {
  name: string; // the liquid's name (the map's logical name, or the protocol's declared name)
  ul: number | null;
  colour?: string;
  carryOver?: boolean; // only a film from a used tip
}

export interface PlateCell {
  well: string;
  row: number;
  col: number;
  expected: Holding[] | null; // null: the map pins nothing here
  found: Holding[] | null; // null: no replay
  status: "ok" | "mismatch" | "unchecked" | "empty" | "proposed";
  issues: string[];
  group?: string; // a free group's member, drawn where it could go
}

export interface PlateView {
  rows: number;
  cols: number;
  cells: PlateCell[];
  groups: { group: PlateMapGroup; placed: boolean; shownIn?: string }[]; // shownIn: "A1–H1" when drawn as a proposal
  variant: string | null;
  destinationName: string | null;
  legend: { name: string; colour: string }[];
}

const ROWS = "ABCDEFGHIJKLMNOP";

export function wellRowCol(name: string): { row: number; col: number } | null {
  const m = /^([A-P])(\d{1,2})$/.exec(name);
  if (!m) return null;
  return { row: ROWS.indexOf(m[1]), col: Number(m[2]) - 1 };
}

export function wellName(row: number, col: number): string {
  return `${ROWS[row]}${col + 1}`;
}

function contentsToHoldings(
  contents: Contents | Record<string, number>,
): Holding[] {
  return Object.entries(contents).map(([name, amount]) => ({
    name,
    ul: typeof amount === "number" ? amount : null,
  }));
}

function pickVariant(
  platemap: PlateMap,
  verify: VerifyReport | null | undefined,
) {
  const wanted = verify?.intent.variant;
  return (
    platemap.variants.find((v) => v.name === wanted) ??
    platemap.variants[0] ??
    null
  );
}

export function plateView(
  platemap: PlateMap | null,
  verify: VerifyReport | null | undefined,
  replay: ReplayExport | null | undefined,
): PlateView {
  const variant = platemap ? pickVariant(platemap, verify) : null;
  const pinned = variant?.pinned ?? {};
  const groups = variant?.groups ?? [];

  // The destination labware in the replay, if there is one.
  const destinationId = verify?.intent.destination ?? null;
  const labware =
    replay && destinationId
      ? replay.deck.labware.find((l) => l.id === destinationId)
      : undefined;

  // Size: from the labware, else from the names the map uses, else a 96-well plate.
  let rows = 8;
  let cols = 12;
  if (labware) {
    const names = Object.keys(labware.wells);
    rows = 0;
    cols = 0;
    for (const name of names) {
      const rc = wellRowCol(name);
      if (rc) {
        rows = Math.max(rows, rc.row + 1);
        cols = Math.max(cols, rc.col + 1);
      }
    }
    if (rows === 0 || cols === 0) {
      rows = 8;
      cols = 12;
    }
  } else {
    const names = [
      ...Object.keys(pinned),
      ...groups.flatMap((g) => g.within ?? []),
    ];
    for (const n of names) {
      const rc = wellRowCol(n);
      if (rc) {
        rows = Math.max(rows, rc.row + 1);
        cols = Math.max(cols, rc.col + 1);
      }
    }
  }

  // Found: the replay's final state of the destination labware.
  const found = new Map<string, Holding[]>();
  const legendMap = new Map<string, string>();
  if (replay && destinationId) {
    const state = finalState(replay);
    for (const [name, index] of wellsOf(replay, destinationId)) {
      const row = state.wells.get(index);
      if (!row) continue;
      const holdings: Holding[] = row[2].map(([origin, ul, mode]) => {
        const o = replay.origins[origin];
        legendMap.set(o.name, o.colour);
        return { name: o.name, ul, colour: o.colour, carryOver: mode === 1 };
      });
      if (holdings.length) found.set(name, holdings);
    }
  }

  // Wrong: what verify said.
  const mismatches = new Map<string, VerifyMismatch>();
  for (const m of verify?.intent.mismatches ?? [])
    if (m.well) mismatches.set(m.well, m);
  const checked = new Map<
    string,
    {
      ok: boolean;
      expected: Record<string, number>;
      found: Record<string, number>;
    }
  >();
  for (const w of verify?.intent.wells ?? [])
    if (w.well) checked.set(w.well, w);

  const cells: PlateCell[] = [];
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const well = wellName(r, c);
      const pin = pinned[well];
      const check = checked.get(well);
      const miss = mismatches.get(well);
      const expected = check
        ? contentsToHoldings(check.expected)
        : pin
          ? contentsToHoldings(pin)
          : miss
            ? contentsToHoldings(miss.expected)
            : null;
      const holds =
        found.get(well) ?? (check ? contentsToHoldings(check.found) : null);
      let status: PlateCell["status"] = "empty";
      if (miss) status = "mismatch";
      else if (check) status = check.ok ? "ok" : "mismatch";
      else if (pin && verify && verify.intent.status !== "cannot_check")
        status = "ok";
      else if (pin || holds) status = "unchecked";
      const issues = miss ? miss.issues.map(issueWords) : [];
      cells.push({
        well,
        row: r,
        col: c,
        expected,
        found: holds,
        status,
        issues,
      });
    }
  }

  // A group whose members may sit anywhere is drawn as a proposed layout when nothing real is
  // known yet (no replay): down the columns from A1, or inside `within` when the map says so,
  // skipping wells the map pins. The replay's real wells replace it once there is one.
  const proposals = new Map<string, { holdings: Holding[]; group: string }>();
  const shown = new Map<string, string>();
  if (found.size === 0 && checked.size === 0) {
    const taken = new Set<string>([...Object.keys(pinned)]);
    for (const group of groups) {
      const candidates = group.within ?? columnOrder(rows, cols);
      const placed: string[] = [];
      for (const member of group.members) {
        const well = candidates.find((w) => !taken.has(w) && !proposals.has(w));
        if (!well) break;
        taken.add(well);
        proposals.set(well, {
          holdings: contentsToHoldings(member),
          group: group.name,
        });
        placed.push(well);
      }
      if (placed.length)
        shown.set(
          group.name,
          placed.length === 1
            ? placed[0]
            : `${placed[0]}–${placed[placed.length - 1]}`,
        );
    }
  }
  for (const cell of cells) {
    const p = proposals.get(cell.well);
    if (p && cell.status === "empty") {
      cell.expected = p.holdings;
      cell.status = "proposed";
      cell.group = p.group;
    }
  }

  // No replay: the map's own liquids get colours, so a proposed or pinned well is not grey.
  if (legendMap.size === 0) {
    const names = new Map<string, string>();
    for (const cell of cells)
      for (const h of cell.expected ?? [])
        if (!names.has(h.name))
          names.set(h.name, PALETTE[names.size % PALETTE.length]);
    for (const cell of cells)
      for (const h of cell.expected ?? []) h.colour = names.get(h.name);
    for (const [name, colour] of names) legendMap.set(name, colour);
  }

  const legend = [...legendMap.entries()].map(([name, colour]) => ({
    name,
    colour,
  }));
  return {
    rows,
    cols,
    cells,
    groups: groups.map((group) => ({
      group,
      placed: shown.has(group.name),
      shownIn: shown.get(group.name),
    })),
    variant: variant?.name ?? null,
    destinationName:
      verify?.destination_name ??
      (labware ? `${labware.name} (slot ${labware.slot})` : null),
    legend,
  };
}

/* The map's liquids, before a replay names any colour: the view's palette order. */
const PALETTE = [
  "#2f80ed",
  "#f2b233",
  "#27ae60",
  "#eb5757",
  "#9b51e0",
  "#f2994a",
  "#56ccf2",
  "#bb6bd9",
  "#6fcf97",
  "#e0a800",
  "#4f6bed",
  "#d35400",
];

/* A1, B1, … H1, A2, …: down each column, the way a hand fills a plate. */
function columnOrder(rows: number, cols: number): string[] {
  const out: string[] = [];
  for (let c = 0; c < cols; c++)
    for (let r = 0; r < rows; r++) out.push(wellName(r, c));
  return out;
}

export function issueWords(issue: {
  kind: string;
  liquid: string | null;
  expected_ul: number | null;
  found_ul: number | null;
  detail: string;
}): string {
  // An `unexpected_well` names no liquid (the map says nothing about the well), so the liquid
  // can be null; every sentence below must stand without it.
  const liquid = (issue.liquid ?? "a liquid").replace(/_/g, " ");
  switch (issue.kind) {
    case "wrong_amount":
      return `${liquid}: ${issue.found_ul} µl where ${issue.expected_ul} µl was asked`;
    case "missing":
    case "missing_liquid":
      return `${liquid} never arrived`;
    case "extra":
    case "unexpected":
    case "unexpected_liquid":
      return `${liquid} should not be here (${issue.found_ul} µl)`;
    case "unexpected_well":
      return "the plate map says nothing about this well, but it holds liquid";
    case "well_empty":
      return "empty at the end" + (issue.detail ? ` (${issue.detail})` : "");
    default:
      return issue.detail || `${issue.kind}: ${liquid}`;
  }
}

/* The arithmetic of a well, from the map's own numbers and nothing else: the parts, their sum,
   and, when the same liquid shrinks from the previous well of the series, the dilution step. */
export interface WellSum {
  parts: { name: string; ul: number | null }[];
  total: number | null; // null when a part is "declared" (all of it, amount unknown here)
  unknownParts: number;
}

export function wellSum(contents: Contents): WellSum {
  const parts = Object.entries(contents).map(([name, amount]) => ({
    name,
    ul: typeof amount === "number" ? amount : null,
  }));
  const unknownParts = parts.filter((p) => p.ul == null).length;
  const total = unknownParts
    ? null
    : parts.reduce((n, p) => n + (p.ul ?? 0), 0);
  return { parts, total, unknownParts };
}

/* "1:2" when every numeric liquid of `well` that also appears in `previous` is a fixed fraction
   of it, and the well's total matches: the step of a dilution series. Otherwise null. */
export function dilutionStep(
  previous: Contents,
  well: Contents,
): string | null {
  const ratios: number[] = [];
  for (const [name, amount] of Object.entries(well)) {
    const before = previous[name];
    if (
      typeof amount !== "number" ||
      typeof before !== "number" ||
      before <= 0 ||
      amount <= 0
    )
      continue;
    if (amount < before) ratios.push(before / amount);
  }
  if (ratios.length === 0) return null;
  const r = ratios[0];
  if (!ratios.every((x) => Math.abs(x - r) / r < 0.01)) return null;
  const rounded = Math.round(r * 100) / 100;
  return Number.isInteger(rounded) ? `1:${rounded}` : `1:${rounded}`;
}

/* The wells of a variant in order, with their sums and dilution steps: what an approver reads. */
export function variantArithmetic(variant: PlateMapVariant): {
  well: string;
  contents: Contents;
  sum: WellSum;
  step: string | null;
}[] {
  const rows: {
    well: string;
    contents: Contents;
    sum: WellSum;
    step: string | null;
  }[] = [];
  const pinned = Object.entries(variant.pinned).sort(([a], [b]) => {
    const ra = wellRowCol(a);
    const rb = wellRowCol(b);
    if (!ra || !rb) return a.localeCompare(b);
    return ra.row - rb.row || ra.col - rb.col;
  });
  let previous: Contents | null = null;
  for (const [well, contents] of pinned) {
    rows.push({
      well,
      contents,
      sum: wellSum(contents),
      step: previous ? dilutionStep(previous, contents) : null,
    });
    previous = contents;
  }
  for (const group of variant.groups) {
    previous = null;
    group.members.forEach((contents, i) => {
      rows.push({
        well: `${group.name} ${i + 1}`,
        contents,
        sum: wellSum(contents),
        step: previous ? dilutionStep(previous, contents) : null,
      });
      previous = contents;
    });
  }
  return rows;
}
