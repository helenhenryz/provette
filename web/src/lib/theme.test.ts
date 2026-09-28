/* The theme: dark until the reader picks, and a pick (System included) is kept. */

import { afterEach, describe, expect, it } from "vitest";
import { readTheme } from "./theme";

describe("readTheme", () => {
  afterEach(() => localStorage.clear());

  it("is dark until the reader picks", () => {
    expect(readTheme()).toBe("dark");
  });

  it("keeps a pick, System included", () => {
    localStorage.setItem("provette.theme", "light");
    expect(readTheme()).toBe("light");
    localStorage.setItem("provette.theme", "auto");
    expect(readTheme()).toBe("auto");
  });
});
