/* How fast a scrub and a played frame are on a big export. PROVETTE_BIG_REPLAY names an
   analysis JSON (the API's answer for an episode); without it, the largest analysis the dev
   API has cached under `.data/cache` is used, so `make check` runs this on every machine that
   has served an episode, and skips only on a clone that never ran the API. The numbers go
   to the console:

     PROVETTE_BIG_REPLAY=/path/analysis.json npx vitest run src/replay/perf.test.ts

   The numbers for nano-best3/short-on-tips/pcr-03 (3,746 events, 291 wells named,
   two 96-well plates, two racks and a trough) are in the commit message. */

import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { buildModel } from "./model";
import {
  liquidColumns,
  place,
  racksOfFrame,
  rowsOfFrame,
  tipsInRack,
} from "./scene";
import { StateCache, eventLine } from "./state";
import { buildTimeline, defaultSpeed, frameAt, makeFrame } from "./timeline";
import type { ReplayData } from "./types";

const path = process.env.PROVETTE_BIG_REPLAY || largestCached();

/* The biggest analysis file under .data/cache (the dev API's cache), or undefined. */
function largestCached(): string | undefined {
  const dir = join(process.cwd(), "..", ".data", "cache");
  try {
    const files = readdirSync(dir).filter((f) => f.endsWith(".json"));
    let best: { file: string; size: number } | null = null;
    for (const f of files) {
      const size = statSync(join(dir, f)).size;
      if (!best || size > best.size) best = { file: join(dir, f), size };
    }
    return best?.file;
  } catch {
    return undefined;
  }
}

describe.skipIf(!path)("the largest episode", () => {
  const data = path
    ? (JSON.parse(readFileSync(path, "utf-8")) as { replay: ReplayData }).replay
    : null!;

  it("builds the timeline and plays a frame in well under a screen refresh", () => {
    const t0 = performance.now();
    const model = buildModel(data);
    const cache = new StateCache(data);
    const tl = buildTimeline(model, cache);
    const built = performance.now() - t0;
    const placements = place(model);
    const buffers = placements.map((p) => ({
      p,
      fractions: new Float32Array(p.wells.length),
      colours: new Float32Array(p.wells.length * 3),
      films: new Float32Array(p.wells.length),
      certain: new Float32Array(p.wells.length),
      shown: new Float32Array(p.wells.length),
    }));
    const frame = makeFrame(cache);
    const speed = defaultSpeed(tl);
    const n = data.events.length;
    // playing: one frame every 16 ms at the default speed, the whole run
    const dt = 0.016 * speed;
    let frames = 0;
    let worst = 0;
    let event = -1;
    let eventChanges = 0;
    const t1 = performance.now();
    for (let t = 0; t <= tl.total; t += dt) {
      const f0 = performance.now();
      frameAt(model, tl, cache, t, frame);
      if (frame.event !== event) {
        // what the 3D view does on an event change: every column of every labware
        event = frame.event;
        eventChanges++;
        for (const b of buffers) {
          if (b.p.lw.row.is_tiprack)
            tipsInRack(racksOfFrame(frame), b.p, b.shown);
          else
            liquidColumns(
              model,
              rowsOfFrame(frame),
              b.p,
              b.fractions,
              b.colours,
              b.films,
              b.certain,
            );
        }
        if (event < n) eventLine(model, data.events[event], frame.state);
      }
      const cost = performance.now() - f0;
      if (cost > worst) worst = cost;
      frames++;
    }
    const played = (performance.now() - t1) / frames;
    // scrubbing: random seeks
    const t2 = performance.now();
    let seed = 7;
    const seeks = 2000;
    let worstSeek = 0;
    for (let k = 0; k < seeks; k++) {
      seed = (seed * 48271) % 2147483647;
      const s0 = performance.now();
      frameAt(model, tl, cache, (seed / 2147483647) * tl.total, frame);
      const cost = performance.now() - s0;
      if (cost > worstSeek) worstSeek = cost;
    }
    const seek = (performance.now() - t2) / seeks;
    console.log(
      `events ${n}, wells ${data.wells.length}: timeline ${built.toFixed(0)} ms, ${tl.total.toFixed(0)} s at 1x, default ${speed}x (${(tl.total / speed / 60).toFixed(1)} min); ` +
        `played frame ${played.toFixed(3)} ms (worst ${worst.toFixed(2)} ms, ${eventChanges} event changes over ${frames} frames); random seek ${seek.toFixed(3)} ms (worst ${worstSeek.toFixed(2)} ms)`,
    );
    expect(played).toBeLessThan(2);
    expect(seek).toBeLessThan(2);
    expect(built).toBeLessThan(2000);
  });
});
