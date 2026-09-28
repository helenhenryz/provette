import { useEffect, useMemo, useRef, useState } from "react";
import type { Finding } from "../lib/api";
import { plural } from "../lib/format";
import type { ReviewExtra } from "../lib/verdict";
import { FindingCard } from "./Findings";
import { Lozenge } from "./vocabulary";
import { CodeLine, codeLines, hangingIndent } from "../lib/highlight";
import styles from "./CodeReview.module.css";

export type { ReviewExtra };

/* The protocol and what Provette found, as a code review: the file on the left with a marker
   in the gutter at every finding's line, a finding's card opening inline under its line when
   the marker or the finding is clicked; the findings list on the right (above, on a phone),
   linked both ways. The code is shown whole, coloured and soft-wrapped (no box to scroll inside);
   picking a finding scrolls the page to its line, and opening the tab moves nothing. */
export function CodeReview({
  text,
  findings,
  extras = [],
  onReplay,
  marked = [],
  loading = false,
  empty = "No biology problems: no rule fired on this protocol.",
  list = true,
  selected: selectedIn,
  onSelect,
}: {
  text: string | null;
  findings: Finding[];
  extras?: ReviewExtra[];
  onReplay?: (finding: Finding, index: number) => void;
  marked?: number[]; // a line to mark that is not a finding's: the simulator's error
  loading?: boolean;
  empty?: string;
  list?: boolean; // the findings list beside the code; off when the rail is the index
  selected?: number | null; // held by the page when the rail's rows select too
  onSelect?: (i: number | null) => void;
}) {
  const [own, setOwn] = useState<number | null>(null);
  const selected = selectedIn !== undefined ? selectedIn : own;
  const setSelected = (i: number | null) => {
    setOwn(i);
    onSelect?.(i);
  };
  const rows = useRef(new Map<number, HTMLTableRowElement>());
  const codeBox = useRef<HTMLDivElement | null>(null);
  const listBox = useRef<HTMLDivElement | null>(null);
  const lines = useMemo(() => codeLines(text ?? ""), [text]);
  const byLine = useMemo(() => {
    const m = new Map<number, number[]>();
    findings.forEach((f, i) => {
      if (f.line != null) m.set(f.line, [...(m.get(f.line) ?? []), i]);
    });
    return m;
  }, [findings]);
  const worst = (idx: number[]) =>
    idx.some((i) => findings[i].severity === "error")
      ? "error"
      : idx.some((i) => findings[i].severity === "warning")
        ? "warning"
        : "note";

  useEffect(() => {
    setOwn(null);
  }, [text]);
  // A selection made elsewhere (the rail) scrolls the code to its line.
  useEffect(() => {
    if (selectedIn != null && findings[selectedIn]?.line != null)
      scrollCodeTo(findings[selectedIn].line!);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedIn, text]);

  // The line comes into view on the page (the code has no scroll box of its own); a line
  // already on screen is left where it is.
  function scrollCodeTo(line: number) {
    const row = rows.current.get(line);
    if (!row?.getBoundingClientRect) return;
    const r = row.getBoundingClientRect();
    if (r.top < 80 || r.bottom > window.innerHeight - 40)
      row.scrollIntoView?.({ block: "center", behavior: "smooth" });
  }
  function pick(i: number | null) {
    setSelected(i);
    if (i != null) {
      const f = findings[i];
      if (f.line != null) scrollCodeTo(f.line);
      const card = listBox.current?.querySelector<HTMLElement>(
        `[data-finding="${i}"]`,
      );
      card?.scrollIntoView?.({ block: "nearest" });
    }
  }
  const firstMark = marked.length ? Math.min(...marked) : null;
  const markedKey = marked.join(",");
  const mounted = useRef(false);
  useEffect(() => {
    // a draft chosen later brings its mark into view; the tab opening does not move the page
    if (!mounted.current) {
      mounted.current = true;
      return;
    }
    if (firstMark != null) scrollCodeTo(firstMark);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [firstMark, markedKey, text]);

  const markedSet = new Set(marked);
  return (
    <div className={`${styles.review} ${list ? "" : styles.codeOnly}`}>
      <div ref={codeBox} className={styles.code} aria-label="The protocol">
        {loading && <p className={styles.loading}>Loading the draft…</p>}
        {text != null && (
          <table className={styles.table}>
            <tbody>
              {lines.map((line, i) => {
                const n = i + 1;
                const here = byLine.get(n);
                const open =
                  here != null && selected != null && here.includes(selected);
                const hit = here != null || markedSet.has(n);
                return [
                  <tr
                    key={n}
                    ref={(el) => {
                      if (el) rows.current.set(n, el);
                      else rows.current.delete(n);
                    }}
                    className={`${hit ? styles.hit : ""} ${here ? styles[`hit_${worst(here)}`] : markedSet.has(n) ? styles.hit_rejected : ""} ${open ? styles.open : ""}`}
                  >
                    <td className={styles.gutter}>
                      {here && (
                        <button
                          type="button"
                          className={`${styles.marker} ${styles[`marker_${worst(here)}`]}`}
                          onClick={() => pick(open ? null : here[0])}
                          aria-label={`${plural(here.length, "finding")} at line ${n}`}
                          title={here.map((i) => findings[i].title).join("; ")}
                        />
                      )}
                    </td>
                    <td className={styles.n}>{n}</td>
                    <td className={styles.line} style={hangingIndent(line)}>
                      <CodeLine tokens={line} />
                    </td>
                  </tr>,
                  open ? (
                    <tr key={`${n}-card`} className={styles.inline}>
                      <td colSpan={3}>
                        <div className={styles.inlineCard}>
                          <FindingCard
                            f={findings[selected!]}
                            index={selected!}
                            onReplay={onReplay}
                          />
                          {here!.length > 1 && (
                            <div className={styles.alsoHere}>
                              {here!
                                .filter((i) => i !== selected)
                                .map((i) => (
                                  <button
                                    key={i}
                                    type="button"
                                    className={styles.alsoLink}
                                    onClick={() => pick(i)}
                                  >
                                    also here:{" "}
                                    <span className="mono">
                                      {findings[i].rule_id}
                                    </span>
                                  </button>
                                ))}
                            </div>
                          )}
                          <button
                            type="button"
                            className={styles.close}
                            onClick={() => pick(null)}
                          >
                            close
                          </button>
                        </div>
                      </td>
                    </tr>
                  ) : null,
                ];
              })}
            </tbody>
          </table>
        )}
      </div>
      {list && (
        <div
          ref={listBox}
          className={styles.list}
          aria-label="What Provette found"
        >
          {findings.length === 0 && extras.length === 0 && (
            <p className={styles.empty}>{empty}</p>
          )}
          {findings.map((f, i) => (
            <button
              key={i}
              type="button"
              data-finding={i}
              className={`${styles.item} ${selected === i ? styles.itemOn : ""}`}
              onClick={() => pick(selected === i ? null : i)}
              aria-expanded={selected === i}
            >
              <span className={styles.itemHead}>
                <Lozenge severity={f.severity} certain={f.certain} />
                <span className="mono">{f.rule_id}</span>
                {f.source === "verify" && (
                  <span
                    className={styles.origin}
                    title="This check runs with the plate map (provette verify), not as a biology rule (provette check)."
                  >
                    runs in verify
                  </span>
                )}
                {f.line != null && (
                  <span className={styles.itemLine}>line {f.line}</span>
                )}
              </span>
              <span className={styles.itemTitle}>
                {f.title.replace(/^\(proposed\)\s*/i, "")}
              </span>
            </button>
          ))}
          {extras.map((x, i) => (
            <div key={`x${i}`} className={styles.extra}>
              <span className={styles.itemHead}>
                <Lozenge severity={x.severity} />
                <span className={styles.itemTitle}>{x.title}</span>
              </span>
              <span className={styles.extraWords}>{x.words}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
