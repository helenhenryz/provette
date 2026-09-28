import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { CodeView } from "../components/CodeView";
import { Fold } from "../components/vocabulary";
import { Findings } from "../components/Findings";
import { Loading, Notice } from "../components/Notice";
import {
  api,
  ApiError,
  declared,
  outcomes,
  type PreviewResult,
  type ShapeRow,
  type SourceRow,
} from "../lib/api";
import { ROLE_WORDS } from "../lib/rules";
import { useFetch } from "../lib/useFetch";
import styles from "./RuleForm.module.css";
import { withJudge } from "../lib/withJudge";

/* "New rule": a declared rule written from the product. A shape chosen by reading its sentence,
   the fields, a source picker, a preview on one episode's final draft, the file it will write,
   and Save as a proposed rule. The engine (provette/rules/declared.py) validates, previews and
   writes the file. `?from=<episode>` starts the form from a recorded failure. */

const ROLES = ["sample", "reagent", "carrier", "any"];
const INTO = ["stock", "sample_well", "reagent_well", "any"];
const SELECTORS = ["add_first", "add_last", "carrier", "sample", "reagent"];
const TEMPLATES: Record<ShapeRow["shape"], string> = {
  no_carry_over: "A tip that touched a sample must never go into a stock.",
  full_well_not_mixed:
    "A well more than 0.9 full must not be mixed with a stroke of more than 0.5 of its volume.",
  add_after:
    "An enzyme must go in after the diluent, and only once the well holds half its final diluent.",
};

type Draft = {
  id: string;
  shape: ShapeRow["shape"];
  title: string;
  severity: "error" | "warning" | "note";
  why: string;
  fix: string;
  sources: string[];
  proposed_by: string;
  carried_role: string;
  into_role: string;
  share: string;
  stroke_share: string;
  first: string;
  last: string;
  half_clause: boolean;
};

const EMPTY: Draft = {
  id: "",
  shape: "no_carry_over",
  title: "",
  severity: "warning",
  why: "",
  fix: "",
  sources: [],
  proposed_by: "",
  carried_role: "sample",
  into_role: "stock",
  share: "0.5",
  stroke_share: "0.5",
  first: "add_first",
  last: "add_last",
  half_clause: true,
};

function idFromTitle(title: string): string {
  return title
    .toUpperCase()
    .replace(/^(A|AN|THE)\s+/, "")
    .replace(/[^A-Z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 40);
}

function toRule(
  d: Draft,
  forPreview = false,
  anySource = "",
): Record<string, unknown> {
  const id = (
    d.id.trim() ||
    idFromTitle(d.title) ||
    (forPreview ? "PREVIEW" : "")
  ).toUpperCase();
  const common = {
    id,
    shape: d.shape,
    title: d.title.trim() || (forPreview ? "(preview)" : ""),
    severity: d.severity,
    why: d.why.trim() || (forPreview ? "(preview)" : ""),
    fix: d.fix.trim() || (forPreview ? "(preview)" : ""),
    sources: d.sources.length || !forPreview ? d.sources : [anySource],
    proposed_by: d.proposed_by.trim() || (forPreview ? "preview" : ""),
    status: "proposed",
    adopted_on: null,
  };
  if (d.shape === "no_carry_over")
    return { ...common, carried_role: d.carried_role, into_role: d.into_role };
  if (d.shape === "full_well_not_mixed")
    return {
      ...common,
      share: Number(d.share),
      stroke_share: Number(d.stroke_share),
    };
  return {
    ...common,
    first: d.first,
    last: d.last,
    half_clause: d.half_clause,
    share: Number(d.share),
  };
}

/* What is missing before the file can be written, by the field's label. */
function missing(d: Draft): string[] {
  const out: string[] = [];
  const id = d.id.trim() || idFromTitle(d.title);
  if (!d.title.trim()) out.push("title");
  if (!/^[A-Z0-9][A-Z0-9-]*$/.test(id)) out.push("id");
  if (!d.why.trim()) out.push("why");
  if (!d.fix.trim()) out.push("fix");
  if (d.sources.length === 0) out.push("one source");
  if (!d.proposed_by.trim()) out.push("proposer");
  if (d.shape === "add_after" && d.first === d.last)
    out.push("two different things for 'first' and 'last'");
  return out;
}

/* The YAML the engine will write, so "a rule is a file" is visible. Flat keys, plain values. */
function toYaml(rule: Record<string, unknown>): string {
  const quote = (s: string) =>
    /[:#'"{}\[\],&*?|<>=!%@`\n]/.test(s) || s.trim() !== s || s === ""
      ? JSON.stringify(s)
      : s;
  const lines: string[] = [];
  for (const [k, v] of Object.entries(rule)) {
    if (Array.isArray(v)) {
      lines.push(`${k}:`);
      for (const item of v) lines.push(`  - ${quote(String(item))}`);
    } else if (v === null) lines.push(`${k}: null`);
    else if (typeof v === "string")
      lines.push(
        k === "why" || k === "fix"
          ? `${k}: >\n  ${v.replace(/\s+/g, " ")}`
          : `${k}: ${quote(v)}`,
      );
    else lines.push(`${k}: ${String(v)}`);
  }
  return lines.join("\n") + "\n";
}

function stripInternal(message: string): string {
  return message
    .replace(/^<preview>:\s*/, "")
    .replace(/^[A-Z0-9-]+(\.yaml)?:\s*/, "");
}

export function RuleFormPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const from = params.get("from");
  const notChecked = params.get("not_checked"); // a "Not checked" item: the title and a note to start from
  const meta = useFetch(declared.sources, "rule-sources");
  const episodes = useFetch(api.episodes, "episodes");
  const checker = useFetch(api.rules, "rules"); // the rules that exist, to rank the sources by how often they are cited
  const declaredRules = useFetch(declared.list, "declared");
  const failure = useFetch(
    () => (from ? outcomes.forEpisode(from) : Promise.resolve(null)),
    `from:${from ?? ""}`,
  );
  const [draft, setDraft] = useState<Draft>(EMPTY);
  const [episode, setEpisode] = useState(from ?? "");
  const [preview, setPreview] = useState<PreviewResult | null>(null);
  const [previewing, setPreviewing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("");
  const [allSources, setAllSources] = useState(false);
  const shapes = meta.data?.shapes ?? [];
  const [added, setAdded] = useState<SourceRow[]>([]); // sources added from this form, listed at once
  const sources = [
    ...(meta.data?.sources ?? []),
    ...added.filter(
      (a) => !(meta.data?.sources ?? []).some((s) => s.key === a.key),
    ),
  ];
  const current = useMemo(() => episodes.data?.episodes ?? [], [episodes.data]);
  // The preview defaults to an episode the shape can fire on: carry-over in a PCR setup where
  // a used tip goes into the master mix, order of addition in a cloning or PCR episode.
  useEffect(() => {
    if (episode || !current.length) return;
    const want =
      draft.shape === "no_carry_over"
        ? /pcr-03$/
        : draft.shape === "add_after"
          ? /^(Cloning|PCR setup)$/
          : /^Serial dilution$/;
    const pick =
      current.find((e) =>
        draft.shape === "no_carry_over"
          ? want.test(e.request_id)
          : want.test(e.technique ?? ""),
      ) ?? current[0];
    setEpisode(pick.id);
  }, [current, episode, draft.shape]);
  useEffect(() => {
    const note = failure.data?.latest?.note;
    if (note && !draft.why)
      setDraft((d) => ({ ...d, why: `Seen on the bench: ${note}` }));
    // Pre-fill `why` once, when the failure arrives; the draft must not re-run this on every edit.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [failure.data]);
  useEffect(() => {
    if (notChecked) {
      const title = notChecked
        .replace(/\s*\((?:N\d+|[^)]*rows?)\)\s*/g, " ")
        .replace(/\s+/g, " ")
        .replace(/[.;]\s*$/, "")
        .trim();
      const id = idFromTitle(title.split(/\s+/).slice(0, 4).join(" "));
      setDraft((d) =>
        d.title
          ? d
          : {
              ...d,
              title,
              id,
              severity: "note",
              why: `Not checked today for ${params.get("technique") ?? "this technique"}: ${notChecked}`,
            },
      );
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [notChecked]);

  const set = <K extends keyof Draft>(key: K, value: Draft[K]) =>
    setDraft((d) => ({ ...d, [key]: value }));
  const gaps = missing(draft);
  const rule = toRule(draft);
  const idShown = draft.id || idFromTitle(draft.title);

  async function runPreview() {
    setPreviewing(true);
    setError(null);
    setPreview(null);
    try {
      setPreview(
        await declared.preview(
          toRule(draft, true, sources[0]?.key ?? ""),
          episode,
        ),
      );
    } catch (e) {
      setError(stripInternal(e instanceof Error ? e.message : String(e)));
    } finally {
      setPreviewing(false);
    }
  }

  async function save() {
    setError(null);
    if (gaps.length) {
      setError(`Before saving: ${gaps.join(", ")}.`);
      return;
    }
    setSaving(true);
    try {
      const saved = await withJudge(() => declared.save(rule).then(() => true));
      if (saved) navigate("/rules#rules"); // null: not run, the password dialog is open
    } catch (e) {
      setError(stripInternal(e instanceof Error ? e.message : String(e)));
    } finally {
      setSaving(false);
    }
  }

  // How often each source is cited by a rule that exists (the checker's by URL, a declared one by key).
  const cited = useMemo(() => {
    const n = new Map<string, number>();
    const byUrl = new Map(
      (meta.data?.sources ?? []).map((s) => [s.url, s.key]),
    );
    for (const r of checker.data?.rules ?? [])
      for (const src of r.sources ?? [])
        n.set(
          byUrl.get(src.url) ?? src.name,
          (n.get(byUrl.get(src.url) ?? src.name) ?? 0) + 1,
        );
    for (const r of declaredRules.data?.rules ?? [])
      for (const key of r.sources) n.set(key, (n.get(key) ?? 0) + 1);
    return n;
  }, [meta.data, checker.data, declaredRules.data]);
  const MOST_USED = 8;
  const matching = sources.filter(
    (s) =>
      !filter ||
      s.name.toLowerCase().includes(filter.toLowerCase()) ||
      draft.sources.includes(s.key),
  );
  const ranked = [...matching].sort(
    (a, b) =>
      (cited.get(b.key) ?? 0) - (cited.get(a.key) ?? 0) ||
      sources.indexOf(a) - sources.indexOf(b),
  );
  const shown =
    filter || allSources || matching.length <= MOST_USED
      ? matching
      : ranked.slice(0, MOST_USED).filter((s) => matching.includes(s));

  return (
    <div className={`stack-lg ${styles.page}`}>
      <header className="stack">
        <p className="small">
          <Link to="/rules">Rules</Link> <span className="faint">/</span>{" "}
          <span className="muted">New rule</span>
        </p>
        <h1>A new rule</h1>
        {notChecked && (
          <Notice tone="info" title="Started from a Not-checked item">
            No shape fits? Keep it under "Why it matters".
          </Notice>
        )}
        {from &&
          failure.data &&
          !(failure.data.latest && !failure.data.latest.ok) && (
            <Notice tone="info" title="Nothing recorded for that episode yet">
              Mark <Link to={`/episodes/${from}`}>the episode</Link> under its
              verdict first.
            </Notice>
          )}
        {from && failure.data?.latest && !failure.data.latest.ok && (
          <Notice tone="info" title="Started from a recorded failure">
            <Link to={`/episodes/${from}`}>The episode</Link>'s note is under
            "Why it matters".
          </Notice>
        )}
      </header>

      {meta.loading && <Loading what="Loading the shapes and sources" />}
      {meta.data && (
        <form className={styles.form} onSubmit={(e) => e.preventDefault()}>
          <fieldset className={`${styles.fieldset} ${styles.sentenceBox}`}>
            <legend>The rule</legend>
            {draft.shape === "no_carry_over" && (
              <p className={styles.sentence}>
                A tip that touched{" "}
                <Pick
                  value={draft.carried_role}
                  options={ROLES}
                  onChange={(v) => set("carried_role", v)}
                />{" "}
                must never go into{" "}
                <Pick
                  value={draft.into_role}
                  options={INTO}
                  onChange={(v) => set("into_role", v)}
                />
                .
              </p>
            )}
            {draft.shape === "full_well_not_mixed" && (
              <p className={styles.sentence}>
                A well more than{" "}
                <Num value={draft.share} onChange={(v) => set("share", v)} />{" "}
                full must not be mixed with a stroke of more than{" "}
                <Num
                  value={draft.stroke_share}
                  onChange={(v) => set("stroke_share", v)}
                />{" "}
                of its volume (shares of the well, 0 to 1).
              </p>
            )}
            {draft.shape === "add_after" && (
              <p className={styles.sentence}>
                <Pick
                  value={draft.last}
                  options={SELECTORS}
                  onChange={(v) => set("last", v)}
                />{" "}
                must go in after{" "}
                <Pick
                  value={draft.first}
                  options={SELECTORS}
                  onChange={(v) => set("first", v)}
                />{" "}
                <label className={styles.inline}>
                  <input
                    type="checkbox"
                    checked={draft.half_clause}
                    onChange={(e) => set("half_clause", e.target.checked)}
                  />{" "}
                  only when the well held less than{" "}
                  <Num value={draft.share} onChange={(v) => set("share", v)} />{" "}
                  of its final diluent at the time
                </label>
              </p>
            )}
            <div className={styles.severityRow}>
              <label className={styles.inline}>
                severity{" "}
                <select
                  value={draft.severity}
                  onChange={(e) =>
                    set("severity", e.target.value as Draft["severity"])
                  }
                  className={styles.pick}
                >
                  <option value="error">error: the plate must be redone</option>
                  <option value="warning">
                    warning: a result will be biased
                  </option>
                  <option value="note">note: advice</option>
                </select>
              </label>
            </div>
            <div
              className={styles.shapes}
              role="radiogroup"
              aria-label="The shape"
            >
              <span className={styles.shapeLabel}>shape</span>
              {shapes.map((s) => (
                <label
                  key={s.shape}
                  className={`${styles.shapeChip} ${draft.shape === s.shape ? styles.shapeOn : ""}`}
                  title={TEMPLATES[s.shape]}
                >
                  <input
                    type="radio"
                    name="shape"
                    checked={draft.shape === s.shape}
                    onChange={() => set("shape", s.shape)}
                  />
                  {s.words}
                </label>
              ))}
            </div>
          </fieldset>

          <fieldset className={styles.fieldset}>
            <legend>The rule in words</legend>
            <label className={styles.field}>
              Title
              <input
                value={draft.title}
                onChange={(e) => set("title", e.target.value)}
                className={styles.input}
                placeholder="one line, what happened: a sample went into a reagent well"
              />
            </label>
            <label className={styles.field}>
              Id
              <input
                value={draft.id}
                onChange={(e) => set("id", e.target.value.toUpperCase())}
                onBlur={() => !draft.id && set("id", idFromTitle(draft.title))}
                className={styles.input}
                placeholder={idShown || "SAMPLE-INTO-REAGENT-WELL"}
                title="capitals and dashes; suggested from the title"
              />
            </label>
            <label className={styles.field}>
              Why it matters
              <textarea
                value={draft.why}
                onChange={(e) => set("why", e.target.value)}
                rows={3}
                className={styles.input}
                placeholder="what it does to the experiment"
              />
            </label>
            <label className={styles.field}>
              The fix
              <textarea
                value={draft.fix}
                onChange={(e) => set("fix", e.target.value)}
                rows={2}
                className={styles.input}
                placeholder="what to do instead; {wells} and {liquids} are filled in"
              />
            </label>
            <label className={styles.field}>
              Proposed by
              <input
                value={draft.proposed_by}
                onChange={(e) => set("proposed_by", e.target.value)}
                className={styles.input}
                placeholder="your name"
              />
            </label>
          </fieldset>

          <fieldset className={styles.fieldset}>
            <legend title="at least one source">Rests on *</legend>
            <input
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className={styles.input}
              placeholder="type to find a source"
            />
            <div className={styles.sources}>
              {shown.map((s: SourceRow) => (
                <label key={s.key} className={styles.check}>
                  <input
                    type="checkbox"
                    checked={draft.sources.includes(s.key)}
                    onChange={(e) =>
                      set(
                        "sources",
                        e.target.checked
                          ? [...draft.sources, s.key]
                          : draft.sources.filter((k) => k !== s.key),
                      )
                    }
                  />{" "}
                  {s.name}
                </label>
              ))}
            </div>
            {shown.length < matching.length && (
              <button
                type="button"
                className={styles.quiet}
                onClick={() => setAllSources(true)}
              >
                Show all {matching.length}
              </button>
            )}
            <AddSource
              onAdded={(row) => {
                setAdded((a) => [...a, row]);
                set("sources", [...draft.sources, row.key]);
              }}
            />
          </fieldset>

          <fieldset className={styles.fieldset}>
            <legend>Try it on an episode</legend>
            <div className="row">
              <select
                value={episode}
                onChange={(e) => setEpisode(e.target.value)}
                className={styles.input}
              >
                {current.map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.technique ?? e.request_id} · {e.request_id} ·{" "}
                    {e.model_label
                      .replace(/^Nemotron 3 /, "")
                      .replace(/ \d+B$/, "")}
                  </option>
                ))}
              </select>
              <button
                type="button"
                className={styles.quiet}
                onClick={runPreview}
                disabled={previewing || !episode}
              >
                {previewing ? "Running…" : "Preview the findings"}
              </button>
            </div>
            {(() => {
              const wanted =
                draft.shape === "no_carry_over"
                  ? /^CONTAM-/
                  : draft.shape === "add_after"
                    ? /ENZYME-BEFORE|ORDER/
                    : /MIX-/;
              const hit = current.find((e) =>
                (e.outcome?.findings ?? []).some((f) => wanted.test(f.rule_id)),
              );
              const f = hit
                ? (hit.outcome?.findings ?? []).find((x) =>
                    wanted.test(x.rule_id),
                  )
                : null;
              return hit && f ? (
                <p
                  className="muted small"
                  title="the rule runs on that episode's final protocol; nothing is saved"
                >
                  Try {hit.request_id}:{" "}
                  {f.title.replace(/^\(proposed\)\s*/i, "").toLowerCase()}
                </p>
              ) : null;
            })()}
            {preview && (
              <div className={styles.preview}>
                {!preview.simulator.passed ? (
                  <p className="muted">
                    Simulator rejected the final draft; the rule did not run.
                  </p>
                ) : (
                  <>
                    <p className="muted small">
                      {preview.findings.length} finding
                      {preview.findings.length === 1 ? "" : "s"} ·{" "}
                      {preview.seconds} s
                    </p>
                    <Findings
                      findings={preview.findings}
                      empty="No finding on this episode."
                    />
                  </>
                )}
              </div>
            )}
          </fieldset>

          <Fold
            summary="The file this writes"
            hint={`provette/rules/declared/${idShown || "<ID>"}.yaml`}
          >
            <CodeView text={toYaml(rule)} maxHeight="360px" language="yaml" />
          </Fold>

          {error && (
            <Notice tone="error" title="Not yet">
              {error}
            </Notice>
          )}
          <div className={styles.saveBar}>
            <button
              type="button"
              className={styles.primary}
              onClick={save}
              disabled={saving || gaps.length > 0}
              title={
                gaps.length ? `Still needed: ${gaps.join(", ")}` : undefined
              }
            >
              {saving ? "Saving…" : "Save as a proposed rule"}
            </button>
            {gaps.length > 0 && (
              <span className="muted small">
                Still needed: {gaps.join(", ")}
              </span>
            )}
          </div>
        </form>
      )}
    </div>
  );
}

/* A source not in the list: a name, its address, and a key suggested from the name. The engine
   writes it to provette/rules/sources.yaml and the picker lists it, selected. */
function AddSource({ onAdded }: { onAdded: (row: SourceRow) => void }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [key, setKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const suggested = name
    .toUpperCase()
    .replace(/[^A-Z0-9]+/g, "_")
    .replace(/^_|_$/g, "")
    .slice(0, 40);
  const keyShown = key || suggested;
  const ready =
    name.trim().length > 2 &&
    /^https?:\/\/\S+$/.test(url.trim()) &&
    /^[A-Z][A-Z0-9_]*$/.test(keyShown);

  async function add() {
    setError(null);
    setBusy(true);
    try {
      const r = await withJudge(() =>
        declared.addSource({
          key: keyShown,
          name: name.trim(),
          url: url.trim(),
        }),
      );
      if (!r) return; // not run: the password dialog is open
      onAdded(r.added);
      setName("");
      setUrl("");
      setKey("");
      setOpen(false);
    } catch (e) {
      if (e instanceof ApiError && e.status === 409)
        setError("A source with that key is already in the list.");
      else setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  if (!open)
    return (
      <button
        type="button"
        className={styles.quiet}
        onClick={() => setOpen(true)}
      >
        A source not in this list
      </button>
    );
  return (
    <div className={styles.addSource}>
      <label className={styles.field}>
        Source
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          className={styles.input}
          placeholder="as cited: NEB: Q5 High-Fidelity PCR kit manual"
        />
      </label>
      <label className={styles.field}>
        URL
        <input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          className={styles.input}
          placeholder="https://"
          inputMode="url"
        />
      </label>
      <label
        className={styles.field}
        title="capitals, digits and underscores; suggested from the name"
      >
        Key
        <input
          value={key}
          onChange={(e) => setKey(e.target.value.toUpperCase())}
          className={styles.input}
          placeholder={suggested || "NEB_Q5_MANUAL"}
        />
      </label>
      <div className="row">
        <button
          type="button"
          className={styles.quiet}
          onClick={add}
          disabled={busy || !ready}
        >
          {busy ? "Adding…" : "Add the source"}
        </button>
        <button
          type="button"
          className={styles.quiet}
          onClick={() => setOpen(false)}
        >
          Cancel
        </button>
      </div>
      {error && <p className={styles.error}>{error}</p>}
    </div>
  );
}

function Pick({
  value,
  options,
  onChange,
}: {
  value: string;
  options: string[];
  onChange: (v: string) => void;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className={styles.pick}
    >
      {options.map((o) => (
        <option key={o} value={o}>
          {ROLE_WORDS[o] ?? o}
        </option>
      ))}
    </select>
  );
}

function Num({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <input
      type="number"
      min={0}
      max={1}
      step="0.05"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className={styles.num}
    />
  );
}
