/* The replay, for a page: `<Replay data={analysis.replay} step={n} onStep={setN} highlight={...} />`
   and `stepOfFinding(data, finding)` for the step a finding jumps to.

   web/src/replay/
     types.ts     the data contract: the export the API serves, and what the views make of it
     model.ts     the export resolved once: wells to labware, labware to its place on the deck
     state.ts     the state at a step from the deltas, with checkpoints; the words for a well
     scene.ts     what the 3D view draws, as numbers (tested without WebGL)
     Deck2D.tsx   the deck grid and the close-up, SVG, in the plate map's language
     Deck3D.tsx   the deck in three.js (react-three-fiber), loaded on demand
     Controls.tsx the scrubber the views share
     timeline.ts  the motion model: the run as time, the pipette's path, volumes between states
     clock.ts     the playback clock (requestAnimationFrame)
     Replay.tsx   the component
     ReplayLab.tsx  /replay-lab, the demo page */

export { Replay, type ReplayView } from "./Replay";
export { LabwareCloseup } from "./Deck2D";
export { buildModel } from "./model";
export { StateCache } from "./state";
export { stepOfFinding } from "./state";
export { Clock } from "./clock";
export {
  buildTimeline,
  defaultSpeed,
  frameAt,
  makeFrame,
  timeOfStep,
  type Frame,
  type Timeline,
} from "./timeline";
export type { Highlight, ReplayData, ReplayFinding } from "./types";
