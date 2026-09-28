/* The replay opens in 3D on a desktop that can draw it, in 2D on a phone or without WebGL, and a
   view the reader picked wins from then on. */

import { afterEach, describe, expect, it, vi } from "vitest";
import { initialReplayView, rememberReplayView } from "./replayView";

function device({ desktop, webgl }: { desktop: boolean; webgl: boolean }) {
  vi.stubGlobal("matchMedia", (q: string) => ({
    matches: desktop && q.includes("min-width"),
    media: q,
  }));
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockImplementation((() =>
    webgl ? {} : null) as unknown as HTMLCanvasElement["getContext"]);
}

describe("initialReplayView", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it("is 3D on a desktop that can draw it", () => {
    device({ desktop: true, webgl: true });
    expect(initialReplayView()).toBe("3d");
  });

  it("is 2D on a phone, or where WebGL is missing", () => {
    device({ desktop: false, webgl: true });
    expect(initialReplayView()).toBe("2d");
    device({ desktop: true, webgl: false });
    expect(initialReplayView()).toBe("2d");
  });

  it("keeps the view the reader picked", () => {
    device({ desktop: true, webgl: true });
    rememberReplayView("2d");
    expect(initialReplayView()).toBe("2d");
  });
});
