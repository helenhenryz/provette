import { useState } from "react";
import type { Finding } from "../lib/api";
import { plural } from "../lib/format";
import { wellsWords, type WellRef } from "../lib/wells";
import { Lozenge, SourceList } from "./vocabulary";
import styles from "./Findings.module.css";

/* The findings `provette check` reported, generically: severity, title, the wells, the
   explanation a student can read, the fix, what it rests on, the line. A new rule's finding
   renders here unchanged. A proposed rule that fires on the same line as an adopted one is
   folded under it as "also fires". */
export function Findings({
  findings,
  onLine,
  onReplay,
  empty = "No rule fired on this protocol.",
}: {
  findings: Finding[];
  onLine?: (line: number) => void; // "line 91" jumps to the code
  onReplay?: (finding: Finding, index: number) => void; // "show in the replay"
  empty?: string;
}) {
  if (findings.length === 0) return <p className={styles.empty}>{empty}</p>;
  const groups = fold(findings);
  return (
    <ol className={styles.list}>
      {groups.map(({ main, index, also }) => (
        <li key={index} className={styles.finding}>
          <FindingCard
            f={main}
            index={index}
            onLine={onLine}
            onReplay={onReplay}
          />
          {also.length > 0 && (
            <ul className={styles.also}>
              {also.map((a) => (
                <li key={a.index}>
                  also fires: <span className="mono">{a.f.rule_id}</span>{" "}
                  <ProposedChip f={a.f} /> {stripProposed(a.f.title)}
                </li>
              ))}
            </ul>
          )}
        </li>
      ))}
    </ol>
  );
}

/* "sample_A1 of NEST 96 Well Plate 100 µL PCR Full Skirt on slot 2 (well A1 in slot 2)" reads
   as "sample_A1 (A1, slot 2)"; the labware is on the plate map above. */
function shortNames(text: string): string {
  return text.replace(
    /(\S+) of [^()]+? on slot (\d+) \(well (\w+) in slot \2\)/g,
    "$1 ($3, slot $2)",
  );
}

export function FindingCard({
  f,
  index,
  onLine,
  onReplay,
}: {
  f: Finding;
  index: number;
  onLine?: (line: number) => void;
  onReplay?: (f: Finding, i: number) => void;
}) {
  const [more, setMore] = useState(false);
  const wells = (f.wells as WellRef[] | undefined) ?? [];
  const sources =
    (f.sources as { name: string; url: string }[] | undefined) ?? [];
  const downstream =
    (f.downstream as { count?: number } | undefined)?.count ?? 0;
  const occurrences = (f.occurrences as unknown[] | undefined)?.length ?? 0;
  const long = f.explanation.length > 320;
  return (
    <>
      <div className={styles.head}>
        <Lozenge severity={f.severity} certain={f.certain} />
        <span className={styles.rule}>{f.rule_id}</span>
        <ProposedChip f={f} />
        {f.line != null &&
          (onLine ? (
            <button
              type="button"
              className={styles.lineLink}
              onClick={() => onLine(f.line!)}
              title="Show this line in the protocol"
            >
              line {f.line} ↓
            </button>
          ) : (
            <span className={styles.line}>line {f.line}</span>
          ))}
        {onReplay && (
          <button
            type="button"
            className={styles.lineLink}
            onClick={() => onReplay(f, index)}
            title="Open the replay at the step that did it"
          >
            show in the replay
          </button>
        )}
        {f.source === "verify" && (
          <span
            className={styles.origin}
            title="This check runs with the plate map (provette verify), not as a biology rule (provette check)."
          >
            runs in verify
          </span>
        )}
      </div>
      <div className={styles.title}>{stripProposed(f.title)}</div>
      {wells.length > 0 && (
        <div className={styles.wells}>
          Wells: {wellsWords(wells)}
          {occurrences > 1 && (
            <span className="muted">
              {" "}
              · this line did it {occurrences} times
            </span>
          )}
          {downstream > 0 && (
            <span className="muted">
              {" "}
              · reached {plural(downstream, "more well")} later
            </span>
          )}
        </div>
      )}
      <p className={`${styles.text} ${long && !more ? styles.clamped : ""}`}>
        {shortNames(f.explanation)}
      </p>
      {long && (
        <button
          type="button"
          className={styles.more}
          onClick={() => setMore((v) => !v)}
        >
          {more ? "less" : "more"}
        </button>
      )}
      {f.fix && (
        <p className={styles.fix}>
          <span className={styles.fixLabel}>Fix</span> {f.fix}
        </p>
      )}
      {sources.length > 0 && (
        <div className={styles.sources}>
          <SourceList sources={sources} label="Rests on" />
        </div>
      )}
    </>
  );
}

function stripProposed(title: string): string {
  return title.replace(/^\(proposed\)\s*/i, "");
}

function ProposedChip({ f }: { f: Finding }) {
  const proposed =
    (f.status as string | undefined) === "proposed" ||
    /^\(proposed\)/i.test(f.title);
  return proposed ? <span className={styles.proposed}>proposed</span> : null;
}

/* A proposed finding on the same line as an earlier finding folds under it. */
function fold(
  findings: Finding[],
): { main: Finding; index: number; also: { f: Finding; index: number }[] }[] {
  const groups: {
    main: Finding;
    index: number;
    also: { f: Finding; index: number }[];
  }[] = [];
  findings.forEach((f, index) => {
    const proposed =
      (f.status as string | undefined) === "proposed" ||
      /^\(proposed\)/i.test(f.title);
    const host =
      proposed && f.line != null
        ? groups.find((g) => g.main.line === f.line)
        : undefined;
    if (host) host.also.push({ f, index });
    else groups.push({ main: f, index, also: [] });
  });
  return groups;
}
