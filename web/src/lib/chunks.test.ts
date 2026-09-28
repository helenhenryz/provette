import { afterEach, describe, expect, it, vi } from "vitest";
import { importChunk, isChunkLoadError, reloadOnceForChunk } from "./chunks";

describe("a chunk gone stale under a deploy", () => {
  afterEach(() => {
    sessionStorage.clear();
    vi.restoreAllMocks();
  });

  it("is told apart from any other error by the browser's own words", () => {
    expect(
      isChunkLoadError(
        new TypeError(
          "Failed to fetch dynamically imported module: /assets/Deck3D-CbeNrWCN.js",
        ),
      ),
    ).toBe(true);
    expect(
      isChunkLoadError(new Error("Importing a module script failed.")),
    ).toBe(true);
    expect(isChunkLoadError(new Error("Cannot read properties of null"))).toBe(
      false,
    );
  });

  it("reloads the page once, and not again in the same session", () => {
    const reload = vi.fn();
    Object.defineProperty(window, "location", {
      value: { ...window.location, reload },
      writable: true,
    });
    expect(reloadOnceForChunk()).toBe(true);
    expect(reload).toHaveBeenCalledTimes(1);
    expect(reloadOnceForChunk()).toBe(false);
    expect(reload).toHaveBeenCalledTimes(1);
  });

  it("hands a loaded chunk through, and rethrows an error that is not a stale chunk", async () => {
    await expect(
      importChunk(() => Promise.resolve({ ok: 1 })),
    ).resolves.toEqual({ ok: 1 });
    await expect(
      importChunk(() => Promise.reject(new Error("boom"))),
    ).rejects.toThrow("boom");
  });
});
