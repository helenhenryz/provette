import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Loading, Notice } from "../components/Notice";
import {
  Chip,
  Fold,
  LinkCard,
  Lozenge,
  SourceList,
  Tabs,
  Tag,
} from "../components/vocabulary";
import {
  api,
  coverageTechniques,
  declared,
  outcomes,
  roles,
  type RoleLists,
  type RuleRow,
} from "../lib/api";
import { plural } from "../lib/format";
import { ruleSentence } from "../lib/rules";
import { useFetch } from "../lib/useFetch";
import styles from "./Knows.module.css";
import { withJudge } from "../lib/withJudge";

/* Rules (docs/how-it-works.md, section 9): the rules as rows, the words the team
   owns, what is covered per technique, and the failures nobody has a rule for yet. The tabs
   are the jump list; the URL hash keeps the tab. No lead on any tab: the rows are the page. */

type Tab = "rules" | "words" | "coverage" | "failures";
const TABS: Tab[] = ["rules", "words", "coverage", "failures"];

const LIST_WORDS: Record<string, string> = {
  sample: "a sample: one of many, must not meet the others",
  reagent: "a reagent: shared, active",
  carrier: "a carrier: water, buffer, medium; inert",
  add_last: "an enzyme or mix that goes in last",
  add_first: "a diluent or buffer that goes in first",
  mix: "a word that names a PCR mix",
  rt: "a word that names the reverse transcriptase",
};
/* The tier as one word on the row; the sentence is its hover. */
const TIER_TAG: Record<string, string> = {
  structural: "replay",
  role: "roles",
};
const TIER_WORDS: Record<string, string> = {
  structural: "reads the replay only",
  role: "needs to know what a liquid is",
};

const BOOK = (
  <svg
    width="18"
    height="18"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.8"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20V3H6.5A2.5 2.5 0 0 0 4 5.5z" />
    <path d="M4 19.5A2.5 2.5 0 0 0 6.5 22H20v-5" />
  </svg>
);

export function KnowsPage() {
  const rules = useFetch(api.rules, "rules");
  const failed = useFetch(outcomes.all, "outcomes");
  const words = useFetch(roles.get, "roles");
  const files = useFetch(declared.list, "declared");
  const cover = useFetch(coverageTechniques, "coverage-techniques");
  // rules deleted from this page: hidden at once (the server has reloaded its rules already)
  const [gone, setGone] = useState<Set<string>>(() => new Set());
  const removable = new Set(
    (files.data?.rules ?? []).filter((r) => r.removable).map((r) => r.id),
  );
  const forget = (id: string) => setGone((g) => new Set(g).add(id));
  const { hash } = useLocation();
  const navigate = useNavigate();
  const fromHash = hash.replace(/^#/, "") as Tab;
  const [tab, setTab] = useState<Tab>(
    TABS.includes(fromHash) ? fromHash : "rules",
  );
  useEffect(() => {
    if (TABS.includes(fromHash) && fromHash !== tab) setTab(fromHash);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hash]);
  const pick = (t: Tab) => {
    setTab(t);
    window.history.replaceState(null, "", `${window.location.pathname}#${t}`);
  };
  const ruleCount =
    (rules.data?.rules.length ?? 0) +
    (files.data?.rules.filter(
      (r) => !rules.data?.rules.some((x) => x.rule_id === r.id),
    ).length ?? 0);
  const techniques =
    cover.data?.techniques.filter((t) => t.technique !== "default") ?? [];

  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <h1>Rules</h1>
        <Link to="/rules/new" className="btn primary">
          + New rule
        </Link>
      </header>
      <Tabs
        items={[
          {
            key: "rules" as const,
            label: "Rules",
            count: rules.data ? ruleCount : null,
          },
          {
            key: "words" as const,
            label: "Words",
            count: words.data ? `${words.data.list_names.length} lists` : null,
          },
          {
            key: "coverage" as const,
            label: "Coverage",
            count: cover.data ? techniques.length : null,
          },
          {
            key: "failures" as const,
            label: "Failures",
            count: failed.data ? failed.data.failures.length : null,
          },
        ]}
        value={tab}
        onChange={pick}
        label="Rules"
      />

      {tab === "rules" && (
        <section className={styles.tab}>
          {rules.loading && <Loading what="Loading the rules" />}
          {rules.error && (
            <Notice tone="error" title="The rules could not be loaded">
              {rules.error}
            </Notice>
          )}
          <p className={styles.howRun}>
            Every rule runs on every protocol; each speaks only when its
            situation occurs.
          </p>
          {rules.data && (
            <ol className={styles.rows}>
              {rules.data.rules
                .filter((rule) => !gone.has(rule.rule_id))
                .map((rule) => (
                  <RuleRowItem
                    key={rule.rule_id}
                    rule={rule}
                    removable={removable.has(rule.rule_id)}
                    onDeleted={forget}
                  />
                ))}
              {(files.data?.rules ?? [])
                .filter(
                  (r) =>
                    !gone.has(r.id) &&
                    !rules.data!.rules.some((x) => x.rule_id === r.id),
                )
                .map((r) => (
                  <li key={r.id} className={styles.row}>
                    <Fold
                      summary={
                        <span className={styles.rowHead}>
                          <span className={`mono ${styles.id}`}>{r.id}</span>
                          <span className={styles.rowTitle}>{r.title}</span>
                          <span className={styles.tags}>
                            <Tag
                              tone={
                                r.status === "adopted" ? "verified" : "warning"
                              }
                              title={
                                r.status === "adopted"
                                  ? undefined
                                  : "runs on every check; its findings are notes until adopted in the file"
                              }
                            >
                              {r.status === "adopted"
                                ? `adopted ${r.adopted_on ?? ""}`
                                : `proposed by ${r.proposed_by}`}
                            </Tag>
                            <Lozenge severity={r.severity} />
                          </span>
                        </span>
                      }
                    >
                      <p className={styles.text}>{ruleSentence(r)}.</p>
                      <p className={styles.text}>{r.why}</p>
                      <p className={styles.muted}>Fix: {r.fix}</p>
                      <p className={`${styles.muted} mono`}>
                        provette/rules/declared/{r.file}
                      </p>
                      {r.removable && (
                        <DeleteRule id={r.id} onDeleted={forget} />
                      )}
                    </Fold>
                  </li>
                ))}
            </ol>
          )}
          <div className={styles.foot}>
            <LinkCard
              to="/docs/rulebook"
              title="The rulebook"
              words="Every rule in words, its numbers and its sources."
              icon={BOOK}
            />
          </div>
        </section>
      )}

      {tab === "words" && (
        <section className={styles.tab}>
          {words.data && <WordLists initial={words.data} />}
        </section>
      )}

      {tab === "coverage" && (
        <section className={styles.tab}>
          {cover.loading && <Loading what="Loading the coverage" />}
          {cover.data && (
            <ol className={styles.rows}>
              {techniques.map((t) => (
                <li key={t.technique} className={styles.row}>
                  <Fold
                    summary={
                      <span className={styles.rowHead}>
                        <span className={styles.rowTitle}>{t.technique}</span>
                        <span className={styles.ok}>
                          {plural(t.checked.length, "check")} ran
                        </span>
                        <span className={styles.skip}>
                          {t.not_checked.length} not checked
                        </span>
                      </span>
                    }
                  >
                    <div className={styles.coverage}>
                      <div>
                        <div className={styles.coverageHead}>Not checked</div>
                        <ul className={styles.no}>
                          {t.not_checked.map((s, i) => (
                            <li key={i}>
                              <span>{s}</span>
                              <button
                                type="button"
                                className={styles.write}
                                onClick={() =>
                                  navigate(
                                    `/rules/new?not_checked=${encodeURIComponent(s)}&technique=${encodeURIComponent(t.technique)}`,
                                  )
                                }
                              >
                                write a rule
                              </button>
                            </li>
                          ))}
                        </ul>
                      </div>
                      <div>
                        <div className={styles.coverageHead}>Checked</div>
                        <ul className={styles.yes}>
                          {t.checked.map((s, i) => (
                            <li key={i}>{s}</li>
                          ))}
                        </ul>
                      </div>
                      {t.physics.length > 0 && (
                        <p className={styles.muted}>
                          Physics not checked:{" "}
                          {t.physics
                            .map((s) => s.replace(/[.;]\s*$/, ""))
                            .join("; ")}
                          .
                        </p>
                      )}
                    </div>
                  </Fold>
                </li>
              ))}
            </ol>
          )}
        </section>
      )}

      {tab === "failures" && (
        <section className={styles.tab}>
          {failed.data && failed.data.failures.length === 0 && (
            <div className={styles.empty}>
              <p
                className={styles.emptyTitle}
                title="runs the checks passed and the bench did not"
              >
                None yet
              </p>
              <p className={styles.muted}>
                Mark a run under its verdict: "Did this run work? No".
              </p>
              <Link to="/examples" className="btn">
                Open the examples
              </Link>
            </div>
          )}
          {failed.data && failed.data.failures.length > 0 && (
            <ul className={styles.failures}>
              {failed.data.failures.map((f) => (
                <li key={f.episode + f.when}>
                  <Link
                    to={
                      f.episode.startsWith("runs/live/")
                        ? `/runs/${f.episode.slice("runs/live/".length)}`
                        : `/episodes/${f.episode}`
                    }
                    className={styles.failureTitle}
                  >
                    {f.request ??
                      (f.episode.startsWith("runs/live/")
                        ? "A live run"
                        : f.episode)}
                  </Link>
                  <span className={styles.muted}>
                    {" "}
                    · {f.model_label ??
                      (f.set === "runs" ? "live" : f.set)} ·{" "}
                    {f.when.slice(0, 10)}
                  </span>
                  <div className={styles.text}>{f.note}</div>
                  <Link
                    to={`/rules/new?from=${encodeURIComponent(f.episode)}`}
                    className="small"
                  >
                    Start a rule from this
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
    </div>
  );
}

/* A rule of the checker: id, title, tier as a one-word tag with the sentence on hover. The rules
   route carries no severity (a rule picks it per finding), so no lozenge here; a declared rule
   has one and shows it. */
function RuleRowItem({
  rule,
  removable = false,
  onDeleted,
}: {
  rule: RuleRow;
  removable?: boolean; // added on this deployment and still proposed
  onDeleted?: (id: string) => void;
}) {
  return (
    <li className={styles.row} id={rule.rule_id}>
      <Fold
        summary={
          <span className={styles.rowHead}>
            <span className={`mono ${styles.id}`}>{rule.rule_id}</span>
            <span className={styles.rowTitle}>
              {rule.title ?? rule.rule_id}
            </span>
            <span className={styles.tags}>
              {rule.status === "proposed" && (
                <Tag
                  tone="warning"
                  title="runs on every check; its findings are notes until adopted in the file"
                >
                  proposed by {rule.proposed_by}
                </Tag>
              )}
              <Tag title={TIER_WORDS[rule.tier] ?? `tier: ${rule.tier}`}>
                {TIER_TAG[rule.tier] ?? rule.tier}
              </Tag>
            </span>
          </span>
        }
      >
        <p className={styles.text}>{rule.description}</p>
        {rule.sources && rule.sources.length > 0 && (
          <SourceList sources={rule.sources} label="Rests on" />
        )}
        {removable && onDeleted && (
          <DeleteRule id={rule.rule_id} onDeleted={onDeleted} />
        )}
      </Fold>
    </li>
  );
}

/* The lists, with an "add a word" box on each. A pattern (an entry written /like this/) is
   shown by its count, with the pattern itself in the tooltip. */
function WordLists({ initial }: { initial: RoleLists }) {
  const [lists, setLists] = useState<Record<string, string[]>>(initial.lists);
  // the words added on this site, by list: only these can be taken out
  const [added, setAdded] = useState<Record<string, string[]>>(
    initial.added_here ?? {},
  );
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState<string | null>(
    () => initial.list_names[0] ?? null,
  ); // the first list open, so the tab is never blank

  async function add(list: string) {
    const word = (drafts[list] ?? "").trim().toLowerCase();
    if (!word) return;
    setError(null);
    setBusy(list);
    try {
      const r = await withJudge(() => roles.add(list, word));
      if (!r) return; // not run: the password dialog is open
      setLists(r.lists);
      setAdded(
        (r as { added_here?: Record<string, string[]> }).added_here ?? {},
      );
      setDrafts((d) => ({ ...d, [list]: "" }));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  }

  async function takeOut(list: string, word: string) {
    setError(null);
    setBusy(list);
    try {
      const r = await withJudge(() => roles.remove(list, word));
      if (!r) return; // not run: the password dialog is open
      setLists(r.lists);
      setAdded(r.added_here ?? {});
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  }

  const summary = useMemo(
    () =>
      initial.list_names.map((name) => ({
        name,
        n: (lists[name] ?? []).length,
      })),
    [initial.list_names, lists],
  );
  return (
    <div className={styles.words}>
      <div className={styles.wordChips}>
        {summary.map(({ name, n }) => (
          <Chip
            key={name}
            on={open === name}
            count={plural(n, "word")}
            onClick={() => setOpen(open === name ? null : name)}
          >
            {name}
          </Chip>
        ))}
      </div>
      {open && (
        <div className={styles.wordList}>
          <div className={styles.wordHead}>
            <span className="mono">{open}</span>{" "}
            <span className={styles.muted}>· {LIST_WORDS[open] ?? ""}</span>
          </div>
          <p className={styles.text}>
            {(lists[open] ?? [])
              .filter(
                (e) => !e.startsWith("/") && !(added[open] ?? []).includes(e),
              )
              .join(", ")}
            {(lists[open] ?? []).some((e) => e.startsWith("/")) && (
              <span
                className={styles.muted}
                title={(lists[open] ?? [])
                  .filter((e) => e.startsWith("/"))
                  .join("\n")}
              >
                , and{" "}
                {plural(
                  (lists[open] ?? []).filter((e) => e.startsWith("/")).length,
                  "pattern",
                )}
              </span>
            )}
          </p>
          {(added[open] ?? []).length > 0 && (
            <div className={styles.addedRow}>
              <span className={styles.muted}>added on this site</span>
              {(added[open] ?? []).map((w) => (
                <span key={w} className={styles.addedWord}>
                  {w}
                  <button
                    type="button"
                    className={styles.addedRemove}
                    onClick={() => void takeOut(open, w)}
                    disabled={busy === open}
                    aria-label={`Take ${w} out of the ${open} list`}
                    title="take it out"
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          )}
          <div className={styles.addRow}>
            <input
              value={drafts[open] ?? ""}
              onChange={(e) =>
                setDrafts((d) => ({ ...d, [open]: e.target.value }))
              }
              onKeyDown={(e) => e.key === "Enter" && add(open)}
              placeholder={`add a word to ${open}`}
              aria-label={`A word to add to the ${open} list`}
              className={styles.addInput}
            />
            <button
              type="button"
              className={styles.addButton}
              disabled={busy === open || !(drafts[open] ?? "").trim()}
              onClick={() => add(open)}
            >
              {busy === open ? "Adding…" : "Add"}
            </button>
          </div>
          {error && <p className={styles.error}>{error}</p>}
        </div>
      )}
    </div>
  );
}

/* Delete a rule added on this site (still proposed): asked once, in place, behind the password.
   A shipped or adopted rule never shows this; it changes through the repository. */
function DeleteRule({
  id,
  onDeleted,
}: {
  id: string;
  onDeleted: (id: string) => void;
}) {
  const [asking, setAsking] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function remove() {
    setBusy(true);
    setError(null);
    try {
      const r = await withJudge(() => declared.remove(id));
      if (r) onDeleted(id); // null: not run, the password dialog is open
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }
  if (!asking)
    return (
      <button
        type="button"
        className={styles.deleteLink}
        onClick={() => setAsking(true)}
      >
        Delete this rule
      </button>
    );
  return (
    <div className={styles.confirm} role="group" aria-label={`Delete ${id}`}>
      <span>
        Delete <span className="mono">{id}</span>? It stops running from the
        next check. This can't be undone.
      </span>
      <span className={styles.confirmButtons}>
        <button type="button" className="btn" onClick={() => setAsking(false)}>
          Cancel
        </button>
        <button
          type="button"
          className={`btn ${styles.danger}`}
          onClick={() => void remove()}
          disabled={busy}
        >
          {busy ? "Deleting…" : "Delete"}
        </button>
      </span>
      {error && <p className={styles.error}>{error}</p>}
    </div>
  );
}
