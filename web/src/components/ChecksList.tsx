import { type ReactNode, useEffect, useState } from "react";
import {
  coverage as fetchCoverage,
  type Analysis,
  type Coverage,
  type DraftRow,
  type Finding,
  type PrepJson,
} from "../lib/api";
import { plural, simulatorTitle } from "../lib/format";
import type { RowTone } from "./vocabulary";
import styles from "./ChecksList.module.css";

/* The rail's checks: one card, the way a CI run draws its checks. A line on top says how many
   passed, over a bar with one segment per check in its colour; then one row per check: a badge
   (✓ ✕ ! –), the check's name over what it looks at, and its result in its tone. A row opens:
   Biology to the rules that ran, each passed or with what it found; Simulator to what ran it
   and what it ran; Plate map and Stocks to their own tabs, which hold every well and every
   liquid. "Not checked" is its own state, a dash, never a tick. The card's foot is the fold:
   what was not looked at for this technique, one "write a rule" button for them, and the
   physics, which never is. The fold opens on the verdict in words (the badge's sentence), so it
   is read without a hover. Data: verify/check JSON, the prep sheet and
   provette/rules/coverage.yaml. */

type Check = {
  label: string;
  value: string;
  tone: RowTone;
  title?: string;
  detail?: ReactNode; // opens in place
  go?: () => void; // opens its tab
  goWords?: string;
};

export type ChecksTab = "platemap" | "prep";

// what each check looks at, under its name
const CAPTION: Record<string, string> = {
  "Plate map": "each well holds what was planned",
  Biology: "lab rules for this technique",
  Stocks: "enough of each liquid declared",
  Simulator: "Opentrons' own simulator",
};

export function ChecksList({
  analysis,
  findings,
  hasMap,
  technique,
  prep,
  preloaded,
  onNotChecked,
  liveDraft,
  live = false,
  verdict,
  onOpenTab,
  onFinding,
}: {
  analysis: Analysis | null;
  findings: Finding[];
  hasMap: boolean;
  technique: string | null | undefined;
  prep?: PrepJson | null; // the prep sheet, for the stocks row; none on an analysis made before it had one
  preloaded?: Coverage;
  onNotChecked?: () => void; // "Write a rule for one of these"
  liveDraft?: DraftRow | null; // while a run goes: the latest draft's checks, the way a CI check fills in
  live?: boolean;
  verdict?: string | null; // the badge's sentence, the first line inside the Not-checked fold
  onOpenTab?: (tab: ChecksTab) => void; // the Plate map and Stocks rows open their tabs
  onFinding?: (ruleId: string) => void; // a rule that fired, in the Biology row, opens its finding
}) {
  const [data, setData] = useState<Coverage | null>(preloaded ?? null);
  useEffect(() => {
    if (preloaded) return;
    let alive = true;
    fetchCoverage(technique).then(
      (c) => alive && setData(c),
      () => alive && setData(null),
    );
    return () => {
      alive = false;
    };
  }, [technique, preloaded]);

  const name = data?.matched && data.technique ? data.technique : null;
  const notChecked = data?.available ? data.not_checked.length : null;
  const [open, setOpen] = useState<Set<string>>(new Set());
  const toggle = (label: string) =>
    setOpen((o) => {
      const n = new Set(o);
      if (n.has(label)) n.delete(label);
      else n.add(label);
      return n;
    });
  const checks: Check[] =
    analysis != null
      ? finalChecks(analysis, findings, hasMap, prep).map((c) =>
          withDetail(c, analysis, findings, data, onOpenTab, onFinding),
        )
      : live && liveDraft
        ? liveChecks(liveDraft, hasMap)
        : [
            {
              label: "Plate map",
              value: live ? "queued" : "checking…",
              tone: "muted",
            },
            {
              label: "Biology",
              value: live ? "queued" : "checking…",
              tone: "muted",
            },
            {
              label: "Simulator",
              value: live ? "queued" : "running…",
              tone: "muted",
            },
          ];

  return (
    <div className={styles.card}>
      <Summary
        checks={checks}
        draft={analysis == null ? liveDraft?.n : undefined}
      />
      <ul className={styles.rows}>
        {checks.map((c) => {
          const inner = (
            <>
              <Badge tone={c.tone} />
              <span className="sr-only">{WORD[c.tone]}</span>
              <span className={styles.text}>
                <span className={styles.label}>{c.label}</span>
                <span className={styles.caption}>{CAPTION[c.label]}</span>
              </span>
              <span className={`${styles.value} ${styles[`tone_${c.tone}`]}`}>
                {c.value}
              </span>
            </>
          );
          const isOpen = open.has(c.label);
          return (
            <li key={c.label} className={styles.item}>
              {c.detail ? (
                <button
                  type="button"
                  className={`${styles.row} ${styles.rowButton}`}
                  onClick={() => toggle(c.label)}
                  aria-expanded={isOpen}
                  title={c.title}
                >
                  {inner}
                  <span
                    className={`${styles.more} ${isOpen ? styles.moreOpen : ""}`}
                    aria-hidden="true"
                  >
                    ›
                  </span>
                </button>
              ) : c.go ? (
                <button
                  type="button"
                  className={`${styles.row} ${styles.rowButton}`}
                  onClick={c.go}
                  title={c.goWords}
                >
                  {inner}
                  <span className={styles.more} aria-hidden="true">
                    ›
                  </span>
                </button>
              ) : (
                <div className={styles.row} title={c.title}>
                  {inner}
                  <span className={styles.more} aria-hidden="true" />
                </div>
              )}
              {c.detail && isOpen && (
                <div className={styles.detail}>{c.detail}</div>
              )}
            </li>
          );
        })}
      </ul>
      {data && data.available && (
        <details className={styles.fold}>
          <summary className={styles.foldSummary}>
            <span className={styles.chevron} aria-hidden="true">
              ›
            </span>
            <span className={styles.foldLabel}>Not checked</span>
            {notChecked != null && (
              <span className={styles.foldCount}>
                {`${notChecked}${name ? ` for ${name}` : ""}`}
              </span>
            )}
          </summary>
          <div className={styles.foldBody}>
            {verdict && <p className={styles.verdict}>{verdict}</p>}
            <ul className={styles.items}>
              {data.not_checked.map((s, i) => (
                <li key={i}>
                  <span>{s}</span>
                </li>
              ))}
              {!data.matched && data.technique && (
                <li className={styles.general}>
                  No list for {data.technique} yet; these are the general ones.
                </li>
              )}
            </ul>
            {onNotChecked && data.not_checked.length > 0 && (
              <button
                type="button"
                className={styles.write}
                onClick={onNotChecked}
              >
                Write a rule for one of these
              </button>
            )}
            <p className={styles.physics}>
              {data.physics.length
                ? `Physics not checked: ${data.physics.map((s) => s.replace(/[.;]\s*$/, "")).join("; ")}.`
                : "Physics not checked."}
            </p>
          </div>
        </details>
      )}
      {data && !data.available && (
        <div className={styles.foot}>
          <span className={styles.foldLabel}>Not checked</span>
          <span className={styles.foldCount}>the physics</span>
        </div>
      )}
    </div>
  );
}

const WORD: Record<RowTone, string> = {
  ok: "passed: ",
  bad: "failed: ",
  warn: "a warning: ",
  skip: "not checked: ",
  muted: "",
};

/* The line on top: how the checks came out, over one bar segment per check. */
function Summary({ checks, draft }: { checks: Check[]; draft?: number }) {
  const n = (t: RowTone) => checks.filter((c) => c.tone === t).length;
  const pending = n("muted");
  const bad = n("bad");
  const warn = n("warn");
  const ok = n("ok");
  const ran = checks.length - n("skip");
  const [word, tone]: [string, RowTone] = pending
    ? [draft != null ? `Checking draft ${draft}…` : "Checking…", "muted"]
    : bad
      ? [`${bad} of ${ran} failed`, "bad"]
      : warn
        ? [`${ok} of ${ran} passed · ${plural(warn, "warning")}`, "warn"]
        : [
            ran === checks.length
              ? `All ${ran} passed`
              : `${ok} of ${ran} passed`,
            "ok",
          ];
  return (
    <div className={styles.summary}>
      <span className={`${styles.summaryWord} ${styles[`tone_${tone}`]}`}>
        {word}
      </span>
      <span className={styles.bar} aria-hidden="true">
        {checks.map((c) => (
          <span
            key={c.label}
            className={`${styles.segment} ${styles[`seg_${c.tone}`]}`}
          />
        ))}
      </span>
    </div>
  );
}

/* A check's state as a round badge: a tick, a cross, a bang, a dash, or a ring while it waits. */
function Badge({ tone }: { tone: RowTone }) {
  const path =
    tone === "ok"
      ? "M5 10.5l3.2 3.2L15 7"
      : tone === "bad"
        ? "M6.5 6.5l7 7M13.5 6.5l-7 7"
        : tone === "warn"
          ? "M10 5.5v5.5M10 14.2v.3"
          : tone === "skip"
            ? "M6.5 10h7"
            : null;
  return (
    <span
      className={`${styles.badge} ${styles[`badge_${tone}`]}`}
      aria-hidden="true"
    >
      <svg viewBox="0 0 20 20" width="12" height="12">
        {path ? (
          <path
            d={path}
            fill="none"
            stroke="currentColor"
            strokeWidth="2.2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        ) : (
          <circle cx="10" cy="10" r="3" fill="currentColor" />
        )}
      </svg>
    </span>
  );
}

function biologyWords(findings: { severity: string }[]): string {
  const counts: Record<string, number> = {};
  for (const f of findings) counts[f.severity] = (counts[f.severity] ?? 0) + 1;
  return findings.length
    ? ["error", "warning", "note"]
        .filter((s) => counts[s])
        .map((s) => plural(counts[s], s))
        .join(", ")
    : "no problems";
}

/* The analysed protocol's checks. */
function finalChecks(
  analysis: Analysis,
  findings: Finding[],
  hasMap: boolean,
  prep: PrepJson | null | undefined,
): Check[] {
  const intent = analysis.verify?.intent;
  const passed = analysis.simulator.passed;
  const errors = findings.filter((f) => f.severity === "error").length;
  const version = analysis.check?.simulator.opentrons_version ?? "";
  const out: Check[] = [];
  if (!hasMap)
    out.push({ label: "Plate map", value: "none given", tone: "skip" });
  else if (!intent || !passed)
    out.push({ label: "Plate map", value: "not checked", tone: "skip" });
  else if (intent.status === "cannot_check")
    out.push({
      label: "Plate map",
      value: "could not be checked",
      tone: "warn",
    });
  else
    out.push({
      label: "Plate map",
      value: `${intent.wells_ok} of ${intent.wells_total} wells`,
      tone: intent.status === "verified" ? "ok" : "bad",
    });
  out.push(
    passed
      ? {
          label: "Biology",
          value: biologyWords(findings),
          tone: errors ? "bad" : findings.length ? "warn" : "ok",
        }
      : { label: "Biology", value: "not checked", tone: "skip" },
  );
  if (passed && prep) out.push({ label: "Stocks", ...stocksState(prep) });
  else if (!passed)
    out.push({ label: "Stocks", value: "not checked", tone: "skip" });
  out.push({
    label: "Simulator",
    value: passed
      ? "passed"
      : `rejected${analysis.simulator.line != null ? ` at line ${analysis.simulator.line}` : ""}`,
    tone: passed ? "ok" : "bad",
    title: simulatorTitle(version),
  });
  return out;
}

/* A final check's way in: Biology and Simulator open in place, Plate map and Stocks open
   their tabs. A check that did not run opens nothing. */
function withDetail(
  c: Check,
  analysis: Analysis,
  findings: Finding[],
  coverage: Coverage | null,
  onOpenTab: ((tab: ChecksTab) => void) | undefined,
  onFinding: ((ruleId: string) => void) | undefined,
): Check {
  if (c.tone === "skip") return c;
  if (c.label === "Biology" && analysis.check)
    return {
      ...c,
      detail: (
        <RulesRan
          analysis={analysis}
          findings={findings}
          coverage={coverage}
          onFinding={onFinding}
        />
      ),
    };
  if (c.label === "Simulator")
    return { ...c, detail: <SimulatorRan analysis={analysis} /> };
  if (c.label === "Plate map" && onOpenTab)
    return {
      ...c,
      go: () => onOpenTab("platemap"),
      goWords: "Every well, planned and got: the Plate map tab",
    };
  if (c.label === "Stocks" && onOpenTab)
    return {
      ...c,
      go: () => onOpenTab("prep"),
      goWords: "Every liquid, used and declared: the Prep sheet tab",
    };
  return c;
}

/* The rules that ran on this protocol, each in the technique's words where coverage.yaml has
   them ("CONTAM-STOCK: a tip that touched a template goes back into the master mix"), else the
   rule's own first sentence; each passed, or with what it found (a link to the finding). */
function RulesRan({
  analysis,
  findings,
  coverage,
  onFinding,
}: {
  analysis: Analysis;
  findings: Finding[];
  coverage: Coverage | null;
  onFinding?: (ruleId: string) => void;
}) {
  const words = new Map<string, string>();
  for (const line of coverage?.checked ?? []) {
    const m = /^([A-Z0-9-]+):\s*(.+)$/.exec(line);
    if (m) words.set(m[1], m[2]);
  }
  const rules = analysis.check?.rules ?? [];
  const ids = rules.map((r) => r.rule_id);
  const rows = rules.map((r) => ({
    id: r.rule_id,
    words:
      words.get(r.rule_id) ?? r.title ?? firstSentence(r.description ?? ""),
  }));
  // the labware rule runs with the plate map (verify), not with the rest
  if (analysis.verify && !ids.includes("LABWARE-FOR-TECHNIQUE"))
    rows.push({
      id: "LABWARE-FOR-TECHNIQUE",
      words:
        words.get("LABWARE-FOR-TECHNIQUE") ?? "the labware suits the technique",
    });
  return (
    <>
      <p className={styles.detailHead}>
        {plural(rows.length, "rule")} ran on this protocol
      </p>
      <ul className={styles.rules}>
        {rows.map((r) => {
          const hits = findings.filter((f) => f.rule_id === r.id);
          const worst = (["error", "warning", "note"] as const).find((s) =>
            hits.some((f) => f.severity === s),
          );
          // the mark in the severity's own colour, as the finding's lozenge has it
          const mark = !hits.length
            ? "ok"
            : worst === "error"
              ? "bad"
              : worst === "warning"
                ? "warn"
                : "note";
          return (
            <li key={r.id} className={styles.rule}>
              <span
                className={`${styles.ruleMark} ${styles[`tone_${mark}`]}`}
                aria-hidden="true"
              >
                {mark === "ok" ? "✓" : mark === "bad" ? "✕" : "!"}
              </span>
              <span className={styles.ruleText}>
                <span className={styles.ruleId}>{r.id}</span>
                <span className={styles.ruleWords}>{r.words}</span>
              </span>
              {hits.length > 0 &&
                (onFinding ? (
                  <button
                    type="button"
                    className={`${styles.ruleHit} ${styles[`tone_${mark}`]}`}
                    onClick={() => onFinding(r.id)}
                  >
                    {plural(hits.length, worst ?? "finding")}
                  </button>
                ) : (
                  <span
                    className={`${styles.ruleHit} ${styles[`tone_${mark}`]}`}
                  >
                    {plural(hits.length, worst ?? "finding")}
                  </span>
                ))}
              {!hits.length && <span className="sr-only">passed</span>}
            </li>
          );
        })}
      </ul>
    </>
  );
}

function firstSentence(text: string): string {
  const m = /^(.+?[.:])(\s|$)/.exec(text);
  return (m ? m[1] : text).replace(/[.:]$/, "");
}

/* What ran the protocol: Opentrons' own simulator at the pinned version, and what it ran. */
function SimulatorRan({ analysis }: { analysis: Analysis }) {
  const version =
    analysis.check?.simulator.opentrons_version ??
    analysis.replay?.opentrons_version ??
    null;
  const replay = analysis.replay;
  const sim = analysis.simulator;
  return (
    <dl className={styles.facts}>
      <dt>Version</dt>
      <dd>
        Opentrons{" "}
        {version ? <span className="mono">{version}</span> : "(pinned)"}
      </dd>
      {analysis.check?.api_level && (
        <>
          <dt>API level</dt>
          <dd className="mono">{analysis.check.api_level}</dd>
        </>
      )}
      {replay && (
        <>
          <dt>Ran</dt>
          <dd>
            {plural(replay.events.length, "liquid step")} ·{" "}
            {plural(replay.deck.labware.length, "labware", "labware")}
          </dd>
          <dt>Pipettes</dt>
          <dd className="mono">
            {replay.pipettes.map((p) => p.name).join(", ")}
          </dd>
        </>
      )}
      {!sim.passed && (
        <>
          <dt>Stopped</dt>
          <dd>
            {sim.line != null ? `at line ${sim.line}: ` : ""}
            {(sim.error ?? "").split("\n")[0]}
          </dd>
        </>
      )}
    </dl>
  );
}

/* The stocks row: the prep sheet's flags as one state. A source well the run draws below
   what the protocol declares "would run dry" (provette/intent/prep.py: `would_run_dry`); one
   drawn past 90 % of it has "no margin"; else the declared stocks are enough, or nothing was
   declared at all (no `load_liquid`, so there is nothing to run dry against). */
function stocksState(prep: PrepJson): { value: string; tone: RowTone } {
  const dry = prep.lines.filter((l) => l.flag === "would_run_dry").length;
  const tight = prep.lines.filter((l) => l.flag === "no_margin").length;
  const declared = prep.lines.filter((l) => l.declared_ul != null).length;
  if (dry) return { value: `${dry} would run dry`, tone: "bad" };
  if (tight) return { value: `${tight} with no margin`, tone: "warn" };
  if (declared) return { value: "enough declared", tone: "ok" };
  return { value: "none declared", tone: "skip" };
}

/* The latest draft's checks while the run goes: draft n's simulator, wells and findings. */
function liveChecks(draft: DraftRow, hasMap: boolean): Check[] {
  const tag = `draft ${draft.n}`;
  if (!draft.checked)
    return [
      { label: "Plate map", value: `${tag} · checking…`, tone: "muted" },
      { label: "Biology", value: `${tag} · checking…`, tone: "muted" },
      { label: "Simulator", value: `${tag} · running…`, tone: "muted" },
    ];
  if (draft.simulator === "timeout")
    // the server was too slow to finish: no verdict either way, said as such
    return [
      { label: "Plate map", value: `${tag} · did not finish`, tone: "muted" },
      { label: "Biology", value: `${tag} · did not finish`, tone: "muted" },
      {
        label: "Simulator",
        value: `${tag} · did not finish in time`,
        tone: "muted",
      },
    ];
  const rejected = draft.simulator === "rejected";
  const findings = draft.findings ?? [];
  const errors = findings.filter((f) => f.severity === "error").length;
  const map: Check = !hasMap
    ? { label: "Plate map", value: "none given", tone: "skip" }
    : rejected
      ? { label: "Plate map", value: `${tag} · not checked`, tone: "skip" }
      : draft.wells_total != null
        ? {
            label: "Plate map",
            value: `${tag} · ${draft.wells_ok ?? 0} of ${draft.wells_total} wells`,
            tone: draft.verify_exit === 0 ? "ok" : "bad",
          }
        : {
            label: "Plate map",
            value: `${tag} · ${draft.verify_exit === 0 ? "verified" : "not verified"}`,
            tone: draft.verify_exit === 0 ? "ok" : "bad",
          };
  return [
    map,
    rejected
      ? { label: "Biology", value: `${tag} · not checked`, tone: "skip" }
      : {
          label: "Biology",
          value: `${tag} · ${biologyWords(findings)}`,
          tone: errors ? "bad" : findings.length ? "warn" : "ok",
        },
    {
      label: "Simulator",
      value: `${tag} · ${rejected ? "rejected" : "passed"}`,
      tone: rejected ? "bad" : "ok",
      title: simulatorTitle(),
    },
  ];
}
