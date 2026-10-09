/* The export, resolved once: every well index to its labware and geometry, every labware to its
   place on the deck. Built once per data object and shared by both views. */

import { liquidName } from "../lib/format";
import { parseWellKey } from "../lib/replayState";
import type { LabwareModel, ReplayData, ReplayModel, WellInfo } from "./types";

export const BASE_MM = 2; // the base under the wells: a labware stands this much above its slot
export const TIP_FRACTION = 0.85; // how much of a rack well's depth a tip sticks up (a drawing choice)

export function buildModel(data: ReplayData): ReplayModel {
  const byId = new Map<string, LabwareModel>();
  const wellIndex = new Map<string, number>();
  const wells: WellInfo[] = [];
  data.wells.forEach((key, i) => {
    const { labware, well } = parseWellKey(key);
    wellIndex.set(`${labware}|${well}`, i);
    wells[i] = { index: i, labware: null, name: well, geometry: null };
  });
  const labware: LabwareModel[] = data.deck.labware.map((row) => {
    const list = Object.entries(row.wells).map(([name, geometry]) => ({
      name,
      index: wellIndex.get(`${row.id}|${name}`) ?? -1,
      geometry,
    }));
    const model: LabwareModel = {
      row,
      x: row.slot_x + row.ox,
      y: row.slot_y + row.oy,
      elevation: row.elevation ?? 0,
      depth: list.reduce((d, w) => Math.max(d, w.geometry.depth ?? 0), 0),
      wells: list,
    };
    byId.set(row.id, model);
    return model;
  });
  for (const lw of labware) {
    for (const w of lw.wells) {
      if (w.index >= 0)
        wells[w.index] = {
          index: w.index,
          labware: lw,
          name: w.name,
          geometry: w.geometry,
        };
    }
  }
  // The trash has no wells, and the trace drops tips into its invented "A1": that well belongs
  // to the trash with no geometry (drawn at the bin's centre). A well the trace names on a
  // labware the deck does not list (should not happen) keeps its parsed name and no labware.
  data.wells.forEach((key, i) => {
    if (wells[i].labware) return;
    const lw = byId.get(parseWellKey(key).labware);
    if (lw) wells[i] = { ...wells[i], labware: lw };
  });
  return { data, labware, byId, wells, count: data.events.length };
}

/* A well's centre on the deck, mm. */
export function wellOnDeck(
  lw: LabwareModel,
  name: string,
): { x: number; y: number } {
  const g = lw.row.wells[name];
  return g
    ? { x: lw.x + g.x, y: lw.y + g.y }
    : { x: lw.x + lw.row.w / 2, y: lw.y + lw.row.h / 2 };
}

/* The size a well is drawn at, mm: a circle's diameter or a rectangle's sides. */
export function wellSize(g: {
  shape: string;
  d: number | null;
  w: number | null;
  h: number | null;
}): { w: number; h: number; round: boolean } {
  if (g.shape === "circular") {
    const d = g.d || 5;
    return { w: d, h: d, round: true };
  }
  return { w: g.w || 5, h: g.h || 5, round: false };
}

/* A liquid's name as a student reads it: "sample_A1 of NEST 96 Well Plate 100 µL PCR Full Skirt
   on slot 2" (the name a protocol declares, place and all) reads as "sample A1"; the origin's
   `place` says where it started. The Findings component shortens the same way. */
export function originName(o: { name: string }): string {
  return liquidName(o.name.replace(/^(\S+) of [^()]+? on slot \d+$/, "$1"));
}

export function labwareTitle(lw: LabwareModel): string {
  return lw.row.is_trash ? "Trash" : lw.row.name;
}

/* The pipette's rated volume in µl, from its name ("p20_single_gen2" -> 20): what a tip is
   filled over. 300 when the export names no pipette. */
export function pipetteMaxOf(model: ReplayModel): number {
  const m = /p(\d+)/i.exec(model.data.pipettes[0]?.name ?? "");
  return m ? Number(m[1]) : 300;
}
