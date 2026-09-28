/* The replay's state at a position, rebuilt from the deltas exactly as provette/view/replay.js
   and provette.view.export.replay_deltas do it: position p means events 0 .. p-1 have happened. */

import type { Band, ReplayExport, WellRow } from "./api";

export interface ReplayState {
  wells: Map<number, WellRow>;
  racks: Map<number, string>;
  tips: Map<number, Band[]>;
}

export function initialState(data: ReplayExport): ReplayState {
  const wells = new Map<number, WellRow>();
  for (const k of Object.keys(data.initial))
    wells.set(Number(k), data.initial[k]);
  return { wells, racks: new Map(), tips: new Map() };
}

export function applyDelta(
  state: ReplayState,
  delta: ReplayExport["deltas"][number],
): void {
  if (!delta) return;
  if (delta.wells)
    for (const k of Object.keys(delta.wells))
      state.wells.set(Number(k), delta.wells[k]);
  if (delta.racks)
    for (const [i, status] of delta.racks) state.racks.set(i, status);
  if (delta.tips)
    for (const k of Object.keys(delta.tips))
      state.tips.set(Number(k), delta.tips[k]);
}

export function stateAt(data: ReplayExport, position: number): ReplayState {
  const state = initialState(data);
  const upto = Math.min(position, data.events.length);
  for (let i = 0; i < upto; i++) applyDelta(state, data.deltas[i]);
  return state;
}

export function finalState(data: ReplayExport): ReplayState {
  return stateAt(data, data.events.length);
}

/* "1:nest_96_wellplate_100ul_pcr_full_skirt[A1]" -> { labware, well } */
export function parseWellKey(key: string): { labware: string; well: string } {
  const m = /^(.*)\[([^\]]+)\]$/.exec(key);
  return m ? { labware: m[1], well: m[2] } : { labware: key, well: "" };
}

/* The well index of every well of one labware, by well name. */
export function wellsOf(
  data: ReplayExport,
  labwareId: string,
): Map<string, number> {
  const out = new Map<string, number>();
  data.wells.forEach((key, i) => {
    const { labware, well } = parseWellKey(key);
    if (labware === labwareId) out.set(well, i);
  });
  return out;
}
