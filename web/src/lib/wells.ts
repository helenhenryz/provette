/* Well names as a person writes them: "A1–A12, B1–B6 in slot 2". */

import { wellRowCol } from "./plate";

export interface WellRef {
  well: string;
  slot?: string | null;
  labware?: string | null;
  labware_id?: string | null;
  liquid?: string | null;
}

/* Consecutive wells along a row fold into a range: A1, A2, A3 -> "A1–A3". */
export function collapseWells(names: string[]): string {
  const parsed = names
    .map((n) => ({ n, rc: wellRowCol(n) }))
    .sort((a, b) =>
      a.rc && b.rc
        ? a.rc.row - b.rc.row || a.rc.col - b.rc.col
        : a.n.localeCompare(b.n),
    );
  const out: string[] = [];
  let i = 0;
  while (i < parsed.length) {
    const start = parsed[i];
    let j = i;
    while (
      j + 1 < parsed.length &&
      start.rc &&
      parsed[j + 1].rc &&
      parsed[j + 1].rc!.row === start.rc.row &&
      parsed[j + 1].rc!.col === parsed[j].rc!.col + 1
    )
      j++;
    out.push(
      j - i >= 2
        ? `${start.n}–${parsed[j].n}`
        : j === i + 1
          ? `${start.n}, ${parsed[j].n}`
          : start.n,
    );
    i = j + 1;
  }
  return out.join(", ");
}

function bySlot(refs: WellRef[]): [string, string[]][] {
  const groups = new Map<string, string[]>();
  for (const r of refs) {
    const key = r.slot ? `slot ${r.slot}` : "";
    groups.set(key, [...(groups.get(key) ?? []), r.well]);
  }
  return [...groups.entries()];
}

/* Wells grouped by slot: "A1–A12, B1–B6 in slot 2 · C1 in slot 3". */
export function wellsWords(refs: WellRef[]): string {
  return bySlot(refs)
    .map(
      ([slot, wells]) => `${collapseWells(wells)}${slot ? ` in ${slot}` : ""}`,
    )
    .join(" · ");
}

/* The same, but more than a plate row of wells in one slot is its count: "96 wells in slot 1";
   a finding row shows this and carries `wellsWords` as its hover. */
export const WELLS_SPELLED_OUT = 12;
export function wellsShort(refs: WellRef[]): string {
  return bySlot(refs)
    .map(
      ([slot, wells]) =>
        `${wells.length > WELLS_SPELLED_OUT ? `${wells.length} wells` : collapseWells(wells)}${slot ? ` in ${slot}` : ""}`,
    )
    .join(" · ");
}
