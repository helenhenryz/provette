/* The replay's data contract.

   The API already serves the replay as JSON: `analysis.replay` from GET /api/episodes/{id}/analysis,
   GET /api/runs/{id}/analysis and GET /api/checks/{id} is `provette view`'s own export
   (provette/view/export.py), the same object the HTML page embeds. `ReplayData` is that export,
   typed in lib/api.ts as `ReplayExport`; the names below say what each part means to the views.

   State is shipped as the initial state plus one delta per event (the wells whose contents
   changed, the tip-rack positions whose status changed, the tips whose residue changed) and
   rebuilt here (state.ts), with a full checkpoint every `cache_every` events so a seek is
   never more than `cache_every` deltas away. A 3,700-event episode is 3 MB this way; the
   full state per event would be events x wells. */

import type {
  Band,
  ReplayExport,
  ReplayLabware,
  ReplayWellGeometry,
  WellRow,
} from "../lib/api";

export type ReplayData = ReplayExport;
export type { Band, ReplayLabware, ReplayWellGeometry, WellRow };

/* The deck: `data.deck.slots` in mm (x right, y towards the back, origin at the front-left of
   slot 1), `data.deck.labware` with each labware's footprint (w, h), its corner offset (ox, oy)
   from its slot's corner (slot_x, slot_y) and every well's centre (x, y from the labware's
   front-left corner), shape, diameter or sides, depth and rated volume. */
export type Slot = ReplayData["deck"]["slots"][number];

/* One liquid: where it started, its declared name (or "the liquid from tube B1 in slot 2") and
   the colour every band of it is drawn in. `data.origins[n]`; a band names it by `n`. */
export type Origin = ReplayData["origins"][number];

/* One event: its 0-based index `i`, the protocol line, the op, the channels it used as
   `[tip index | null, well index]` pairs, the volume per channel, the text a student can read,
   and `held`: what each tip holds after the event. */
export type ReplayEvent = ReplayData["events"][number];

export type Delta = NonNullable<ReplayData["deltas"][number]>;

/* A finding as the export carries it: `root_event` is the event that did the damage, and
   `well_index` / `downstream_index` are indices into `data.wells`. */
export type ReplayFinding = ReplayData["findings"][number];

/* A tip-rack position's status: no entry means a fresh tip. */
export type TipStatus = "fresh" | "in_use" | "parked" | "gone";

/* What the views draw per well after the export's bands are read: `fraction` is how far up the
   well the liquid is drawn: the ledger's own height for the volume (the well's `height_at_ul`
   table) over the well's depth when the export carries the table, else the volume over the
   rated maximum, and never under the drawing floor (state.ts MIN_FILL); `bands` are the liquids
   pipetted in, bottom to top, each with its share of the fill; `films` are carry-over only (no
   volume). */
export interface WellFill {
  volume: number | null; // null: not known (an undeclared well the robot drew from)
  minVolume: number;
  fraction: number; // 0..1 of the well's depth
  bands: {
    origin: number;
    colour: string;
    share: number;
    certain: boolean;
    unknown: boolean;
  }[];
  films: { origin: number; colour: string; certain: boolean }[];
  blended: string; // one colour for the whole fill: the bands' colours weighted by share
}

/* One well, resolved once from `data.wells[i]` = "labware_id[well]". */
export interface WellInfo {
  index: number;
  labware: LabwareModel | null;
  name: string;
  geometry: ReplayWellGeometry | null;
}

/* A labware with its wells as an ordered list, and where it sits on the deck. */
export interface LabwareModel {
  row: ReplayLabware;
  /* the labware's front-left corner on the deck, mm */
  x: number;
  y: number;
  /* how high it stands: 0 on the deck, a module's labware offset on a module (schema 4) */
  elevation: number;
  /* the deepest well: the labware's height above the deck is this plus a base. The export
     carries no overall height, so nothing taller is drawn. */
  depth: number;
  wells: { name: string; index: number; geometry: ReplayWellGeometry }[];
}

export interface ReplayModel {
  data: ReplayData;
  labware: LabwareModel[];
  byId: Map<string, LabwareModel>;
  wells: WellInfo[]; // by well index
  count: number; // events
}

/* The wells a finding names, for an outline: red for the wells it is about, orange for the
   wells the damage reached later. */
export interface Highlight {
  wells: number[];
  downstream?: number[];
}
