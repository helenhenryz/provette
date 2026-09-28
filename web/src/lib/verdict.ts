import type { Analysis, DraftRow, VerifyMismatch } from "./api";
import { plural, ul } from "./format";

/* The words for what the verifier found, in its own wording (provette/intent/report.py). */

function contentsWords(c: Record<string, number>): string {
  const parts = Object.entries(c)
    .filter(([k]) => k !== "?")
    .map(([k, v]) => `${ul(v)} ${k}`);
  return parts.length ? parts.join(", ") : "nothing";
}

export function mismatchWords(m: VerifyMismatch): string {
  if (m.text && m.text.length) return m.text.join(" ");
  const issues = m.issues.map((x) => {
    switch (x.kind) {
      case "wrong_amount":
        return `wrong amount of ${x.liquid}: the plate map says ${ul(x.expected_ul ?? 0)}, the protocol delivers ${ul(x.found_ul ?? 0)}`;
      case "missing_liquid":
        return `${x.liquid} is missing: the plate map says ${ul(x.expected_ul ?? 0)}, none arrives`;
      case "unexpected_liquid":
        return `holds ${ul(x.found_ul ?? 0)} of ${x.liquid}, which the plate map does not list for this well`;
      case "well_empty":
        return (
          "the well is empty at the end" + (x.detail ? ` (${x.detail})` : "")
        );
      case "no_well":
        return `no well on the plate holds ${contentsWords(m.expected)}`;
      case "unexpected_well":
        return "the plate map says nothing about this well, but it holds liquid";
      case "wrong_position":
        return `in the wrong well: ${x.detail}`;
      default:
        return `the amount cannot be known: ${x.detail}`;
    }
  });
  return issues.join("; ");
}

export interface ReviewExtra {
  title: string; // a card with no line: a plate-map mismatch, a flag
  words: string;
  severity: "error" | "warning" | "note";
  step?: number; // the replay's event to seek, when the ledger names one
}

/* The cards with no line of their own: the wells that do not hold what the map says, the flags. */
export function reviewExtras(verify: Analysis["verify"]): ReviewExtra[] {
  if (!verify) return [];
  const out: ReviewExtra[] = verify.intent.mismatches.map((m) => ({
    title: m.well
      ? `Well ${m.well} does not hold what the plate map says`
      : `No well holds what the plate map asks${m.group ? ` (${m.group})` : ""}`,
    words: mismatchWords(m),
    severity: "error" as const,
  }));
  for (const f of verify.flags ?? [])
    out.push({
      title: "A flag from the replay",
      words: f,
      severity: "warning",
    });
  return out;
}

/* Liquid that ended in the trash, from the accounting, with the first dispense or blow-out
   into the bin as the event to seek. */
export function trashExtras(
  verify: Analysis["verify"],
  replay: Analysis["replay"],
): ReviewExtra[] {
  if (!verify || !replay) return [];
  const trashIds = new Set(
    replay.deck.labware.filter((l) => l.is_trash).map((l) => l.id),
  );
  const trashWells = new Set(
    replay.wells
      .map((w, i) => (trashIds.has(w.split("[")[0]) ? i : -1))
      .filter((i) => i >= 0),
  );
  const first = replay.events.find(
    (e) =>
      (e.op === "dispense" || e.op === "blow_out") &&
      e.targets.some((t) => trashWells.has(t[1])),
  );
  // the number is the accounting's own (a blow-out's event carries no volume); the events give the step
  const total = verify.accounting.reduce((n, a) => n + (a.trash_ul ?? 0), 0);
  if (!first && total <= 0) return [];
  const lost = verify.accounting
    .filter((a) => a.lost_ul > 0)
    .map((a) => `${ul(a.lost_ul)} of ${a.liquid}`);
  return [
    {
      title: `${ul(total)} went into the trash`,
      words: lost.length
        ? `Not delivered anywhere: ${lost.join(", ")}. The replay shows the first dispense into the bin.`
        : "Dispensed or blown out into the bin; the accounting counts it as lost to the experiment.",
      severity: "note",
      step: first?.i,
    },
  ];
}

/* "4 findings raised, all repaired" / "2 findings left of 6 raised": counted from the drafts'
   own checks. A plate-map mismatch and an unplaced liquid count as findings too. */
export function checksRaised(
  rows: DraftRow[],
  finalN: number | null,
): string | null {
  const final = finalN ?? rows[rows.length - 1]?.n ?? null;
  const before = rows.filter(
    (d) => d.checked && d.n !== final && d.simulator !== "rejected",
  );
  const count = (d: DraftRow) =>
    (d.findings?.length ?? 0) +
    (d.verify_exit != null && d.verify_exit !== 0 ? 1 : 0);
  const raised = before.reduce((n, d) => n + count(d), 0);
  if (raised === 0) return null;
  const last = rows.find((d) => d.n === final);
  const left =
    last && last.checked && last.simulator !== "rejected" ? count(last) : 0;
  return left === 0
    ? `${plural(raised, "finding")} raised, all repaired`
    : `${plural(left, "finding")} left of ${raised} raised`;
}
