import type { ReplayView } from "../replay/Replay";

/* Which replay view a run record opens on. On a desktop that can draw it, the 3D deck: it is
   the view that shows the run as the robot does it. On a phone, or where WebGL is missing, the
   2D plate. A view the reader picks is remembered in this browser and wins from then on. */

const KEY = "provette.replayView";

function canDraw3d(): boolean {
  try {
    const canvas = document.createElement("canvas");
    return Boolean(canvas.getContext("webgl2") ?? canvas.getContext("webgl"));
  } catch {
    return false;
  }
}

function isDesktop(): boolean {
  try {
    return window.matchMedia("(min-width: 900px) and (pointer: fine)").matches;
  } catch {
    return false;
  }
}

export function initialReplayView(): ReplayView {
  try {
    const saved = localStorage.getItem(KEY);
    if (saved === "2d" || saved === "3d") return saved;
  } catch {
    /* no storage: fall through to the device's default */
  }
  return isDesktop() && canDraw3d() ? "3d" : "2d";
}

export function rememberReplayView(view: ReplayView): void {
  try {
    localStorage.setItem(KEY, view);
  } catch {
    /* private window: the choice lasts for this page only */
  }
}
