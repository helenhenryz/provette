import { useEffect, useState } from "react";
import type { DraftRow, Finding, Step } from "../lib/api";
import { money, plural, seconds, simulatorTitle, tokens } from "../lib/format";
import { Lozenge, Row as CheckRow } from "./vocabulary";
import styles from "./Timeline.module.css";

/* The loop as it happens: every tool call as a row, each draft followed by the checker's
   verdict for it (simulator, plate map, findings by severity), the model's reasoning folded
   under the step, and the clock, tokens and cost ticking at the top. The same component shows
   the planner's turns and the writer's. */
export function Timeline({
  steps,
  drafts = [],
  state,
  thinking,
  created,
  seconds: took,
  tokensIn,
  tokensOut,
  cost,
  waitingWords = "Starting…",
}: {
  steps: Step[];
  drafts?: DraftRow[];
  state: "running" | "done" | "failed" | "stopped" | "timeout";
  thinking: boolean;
  created?: number | null;
  seconds?: number | null;
  tokensIn?: number | null;
  tokensOut?: number | null;
  cost?: number | null;
  waitingWords?: string;
}) {
  const elapsed = useElapsed(state === "running" ? created : null);
  const shownSeconds = state === "running" ? elapsed : (took ?? elapsed);
  const byDraft = new Map<number, DraftRow>();
  for (const d of drafts) byDraft.set(d.n, d);
  return (
    <div className={styles.timeline}>
      <div className={styles.counters} aria-live="off">
        <span className={styles.counter}>
          <strong>{shownSeconds != null ? seconds(shownSeconds) : "—"}</strong>{" "}
          {state === "running" ? "so far" : "in all"}
        </span>
        <span className={styles.counter}>
          <strong>{tokens(tokensIn ?? 0) || "0"}</strong> tokens in ·{" "}
          <strong>{tokens(tokensOut ?? 0) || "0"}</strong> out
        </span>
        <span className={styles.counter}>
          <strong>{cost != null ? money(cost) : "—"}</strong>{" "}
          {state === "running" ? "so far" : ""}
        </span>
        <span className={styles.counter}>
          <strong>
            {plural(steps.filter((s) => s.kind === "tool").length, "tool call")}
          </strong>
        </span>
      </div>
      <ol className={styles.list}>
        {steps.map((step, i) => (
          <Row
            key={i}
            step={step}
            draft={
              step.tool === "run_checks" && step.draft != null
                ? byDraft.get(step.draft)
                : undefined
            }
            previous={
              step.draft != null && step.draft > 0
                ? byDraft.get(step.draft - 1)
                : undefined
            }
          />
        ))}
        {state === "running" && (
          <li className={`${styles.row} ${styles.live}`}>
            <span
              className={`${styles.marker} ${styles.pulse}`}
              aria-hidden="true"
            />
            <div className={styles.body}>
              <span className={styles.title}>
                {thinking
                  ? "The model is thinking…"
                  : steps.length === 0
                    ? waitingWords
                    : "Running the checks…"}
              </span>
            </div>
          </li>
        )}
      </ol>
    </div>
  );
}

function Row({
  step,
  draft,
  previous,
}: {
  step: Step;
  draft?: DraftRow;
  previous?: DraftRow;
}) {
  const [open, setOpen] = useState(false);
  const hasDetail =
    step.detail.trim().length > 0 ||
    Boolean(step.arguments) ||
    Boolean(step.reasoning);
  const isCheck = step.tool === "run_checks";
  const isWrite = step.tool === "write_protocol";
  return (
    <li
      className={`${styles.row} ${styles[step.status]} ${isCheck ? styles.check : ""}`}
      data-row="step"
    >
      <span className={styles.marker} aria-hidden="true" />
      <div className={styles.body}>
        <div className={styles.head}>
          {step.draft != null &&
            (step.tool === "write_protocol" || isCheck) && (
              <span className={styles.draftChip}>draft {step.draft}</span>
            )}
          <button
            type="button"
            className={styles.title}
            onClick={() => hasDetail && setOpen((v) => !v)}
            aria-expanded={hasDetail ? open : undefined}
            disabled={!hasDetail}
          >
            {step.title}
            {hasDetail && (
              <span
                className={`${styles.chevron} ${open ? styles.chevronOpen : ""}`}
                aria-hidden="true"
              >
                ›
              </span>
            )}
          </button>
        </div>
        {isWrite &&
          step.draft != null &&
          step.draft > 0 &&
          previous &&
          repairedWords(previous) && (
            <p className={styles.repaired}>{repairedWords(previous)}</p>
          )}
        {isCheck && draft && (
          <Verdict draft={draft} previous={previous} report={step.report} />
        )}
        {open && hasDetail && (
          <div className={styles.detail}>
            {step.arguments && (
              <div className={styles.io}>
                <span className={styles.ioLabel}>asked</span>
                <code>{step.arguments}</code>
              </div>
            )}
            {step.detail.trim().length > 0 && (
              <div className={styles.io}>
                <span className={styles.ioLabel}>
                  {isCheck ? "said" : "answered"}
                </span>
                <span>{step.detail}</span>
              </div>
            )}
            {step.reasoning && step.reasoning.length > 0 && (
              <details className={styles.reasoning}>
                <summary>
                  the model's reasoning before this call,{" "}
                  {tokens(step.reasoning_chars)} characters
                </summary>
                <pre>{step.reasoning}</pre>
              </details>
            )}
          </div>
        )}
        <div className={styles.meta}>
          {step.tool && <span className="mono">{step.tool}</span>}
          {step.seconds != null && <span>{seconds(step.seconds)}</span>}
          {step.tokens_out != null && (
            <span>{tokens(step.tokens_out)} tokens</span>
          )}
          {step.reasoning_chars > 0 && (
            <span>thought {tokens(step.reasoning_chars)} characters</span>
          )}
        </div>
      </div>
    </li>
  );
}

/* "draft 2 · repaired from Provette's report (1 warning)": why the model wrote this draft, from
   what the checks said of the one before. */
function repairedWords(previous: DraftRow): string {
  if (!previous.checked) return "";
  if (previous.simulator === "rejected")
    return "repaired from the simulator's error";
  const findings = previous.findings ?? [];
  const counts: Record<string, number> = {};
  for (const f of findings) counts[f.severity] = (counts[f.severity] ?? 0) + 1;
  const parts = ["error", "warning", "note"]
    .filter((k) => counts[k])
    .map((k) => plural(counts[k], k));
  if (previous.verify_exit != null && previous.verify_exit !== 0)
    parts.unshift("the plate map not met");
  return parts.length
    ? `repaired from Provette's report (${parts.join(", ")})`
    : "written again after a clean report";
}

const sameFinding = (a: Finding, b: Finding) =>
  a.rule_id === b.rule_id &&
  ((a.line != null && a.line === b.line) || a.title === b.title);

/* What the checks said of one draft, as the rail says it: Simulator, Plate map, Biology with
   every finding inline; the findings of the draft before that are gone, marked fixed; and
   under a fold, the report as the model received it. */
function Verdict({
  draft,
  previous,
  report,
}: {
  draft: DraftRow;
  previous?: DraftRow;
  report?: string;
}) {
  if (!draft.checked) return null;
  const rejected = draft.simulator === "rejected";
  const findings = draft.findings ?? [];
  // a finding is fixed only when this draft's checks ran and did not raise it again; a
  // rejected draft checked nothing and fixed nothing
  const fixed =
    rejected || !draft.checked
      ? []
      : (previous?.findings ?? []).filter(
          (f) => !findings.some((g) => sameFinding(f, g)),
        );
  const errors = findings.filter((f) => f.severity === "error").length;
  const text = report || draft.report || "";
  return (
    <div className={styles.verdict}>
      <div className={styles.checks}>
        <CheckRow
          label="Simulator"
          value={
            rejected
              ? `rejected: ${(draft.simulator_error ?? "").replace(/^line \d+:\s*/, "").slice(0, 120) || "an error"}`
              : "passed"
          }
          tone={rejected ? "bad" : "ok"}
          title={simulatorTitle()}
        />
        {rejected ? (
          <CheckRow
            label="Plate map"
            value="not run: the simulator rejected the draft"
            tone="skip"
          />
        ) : draft.wells_total != null ? (
          <CheckRow
            label="Plate map"
            value={`${draft.wells_ok ?? 0} of ${draft.wells_total} wells`}
            tone={draft.verify_exit === 0 ? "ok" : "bad"}
          />
        ) : draft.verify_exit == null ? (
          <CheckRow label="Plate map" value="no plate map" tone="skip" />
        ) : (
          <CheckRow
            label="Plate map"
            value={draft.verify_exit === 0 ? "verified" : "not verified"}
            tone={draft.verify_exit === 0 ? "ok" : "bad"}
          />
        )}
        {rejected ? (
          <CheckRow
            label="Biology"
            value="not run: the simulator rejected the draft"
            tone="skip"
          />
        ) : (
          <CheckRow
            label="Biology"
            value={
              findings.length
                ? plural(findings.length, "finding")
                : "no problems"
            }
            tone={errors ? "bad" : findings.length ? "warn" : "ok"}
          />
        )}
      </div>
      {findings.length > 0 && (
        <ul className={styles.inlineFindings}>
          {findings.map((f, i) => (
            <li key={i}>
              <Lozenge severity={f.severity} certain={f.certain} />
              <span>{f.title.replace(/^\(proposed\)\s*/i, "")}</span>
              {f.line != null && (
                <span className={styles.at}>· line {f.line}</span>
              )}
            </li>
          ))}
        </ul>
      )}
      {fixed.length > 0 && (
        <ul className={styles.inlineFindings}>
          {fixed.map((f, i) => (
            <li key={`fixed-${i}`} className={styles.fixed}>
              <span className={styles.fixedMark}>fixed</span>
              <span>{f.title.replace(/^\(proposed\)\s*/i, "")}</span>
              {f.line != null && (
                <span className={styles.at}>· was at line {f.line}</span>
              )}
            </li>
          ))}
        </ul>
      )}
      {text && (
        <details className={styles.told}>
          <summary>what the model was told</summary>
          <pre>{text}</pre>
        </details>
      )}
    </div>
  );
}

/* Seconds since `created`, ticking once a second while it is set. */
function useElapsed(created: number | null | undefined): number | null {
  const [now, setNow] = useState(() => Date.now() / 1000);
  useEffect(() => {
    if (created == null) return;
    const t = setInterval(() => setNow(Date.now() / 1000), 1000);
    return () => clearInterval(t);
  }, [created]);
  if (created == null) return null;
  return Math.max(0, now - created);
}
