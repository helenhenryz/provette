/* The run record's meta row counts the findings the drafts raised: "2 findings left of 6
   raised" when the final draft still has some, "6 findings raised, all repaired" when not. */

import { describe, expect, it } from "vitest";
import type { DraftRow, Finding } from "./api";
import { checksRaised } from "./verdict";

const findings = (n: number): Finding[] =>
  Array.from({ length: n }, (_, i) => ({
    rule_id: `RULE-${i}`,
    severity: "error",
    certain: true,
    line: 1,
    title: "t",
    explanation: "e",
    fix: "f",
  }));
const row = (n: number, found: number, verify_exit = 0): DraftRow => ({
  n,
  lines: 10,
  checked: true,
  summary: null,
  simulator: "passed",
  verify_exit,
  findings: findings(found),
});

describe("checksRaised", () => {
  it("says what is left of what was raised, the number a reader wants first", () => {
    // draft 1: three findings and a plate-map mismatch; draft 2: two; the final draft 3 keeps two
    expect(checksRaised([row(1, 3, 1), row(2, 2), row(3, 2)], 3)).toBe(
      "2 findings left of 6 raised",
    );
    expect(checksRaised([row(1, 1, 1), row(2, 1)], 2)).toBe(
      "1 finding left of 2 raised",
    );
  });

  it("says all repaired when the final draft has none, and nothing when none was raised", () => {
    expect(checksRaised([row(1, 3, 1), row(2, 0)], 2)).toBe(
      "4 findings raised, all repaired",
    );
    expect(checksRaised([row(1, 0)], 1)).toBeNull();
  });
});
