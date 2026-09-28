import { describe, expect, it } from "vitest";
import { codeLines } from "./highlight";

describe("codeLines", () => {
  it("keeps one line per source line, a blank line empty, and colours the keywords", () => {
    const lines = codeLines(
      'import x\n\ndef run(p):\n    """doc\n\n    more"""\n',
    );
    expect(lines).toHaveLength(6);
    expect(lines[1].map((t) => t.content).join("")).toBe("");
    expect(lines[4].map((t) => t.content).join("")).toBe("");
    expect(lines[0][0]).toMatchObject({ content: "import" });
    expect(lines[0][0].types).toContain("keyword");
  });
});
