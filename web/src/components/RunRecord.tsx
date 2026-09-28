import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import type { Analysis, DraftRow, Finding, PlateMap, Step } from "../lib/api";
import { money, plural, seconds } from "../lib/format";
import { reviewExtras, trashExtras } from "../lib/verdict";
import { wellsShort, wellsWords, type WellRef } from "../lib/wells";
import {
  Replay,
  stepOfFinding,
  type Highlight,
  type ReplayView,
} from "../replay";
import { Accounting, PrepSheet } from "./PrepSheet";
import { ChecksList } from "./ChecksList";
import { CodeReview } from "./CodeReview";
import { FindingCard } from "./Findings";
import { Notice } from "./Notice";
import { OutcomeForm } from "./OutcomeForm";
import { PlateGrid } from "./PlateGrid";
import { PlateMapSums } from "./PlateMapSums";
import { Timeline } from "./Timeline";
import { UnplacedLiquids } from "./UnplacedLiquids";
import {
  Badge,
  Bone,
  Fold,
  Lozenge,
  Rail,
  RailSection,
  Segments,
  Stage,
  Stepper,
  Tabs,
  type BadgeState,
} from "./vocabulary";
import { initialReplayView, rememberReplayView } from "../lib/replayView";
import styles from "./RunRecord.module.css";

/* The run record (docs/how-it-works.md, section 9): one screen for one run. The header (crumbs,
   the request, the badge, the meta row), the stage (Replay · Plate map · Protocol · Prep
   sheet, one height), the rail (the checks, the teaching card, the findings as rows that seek
   the stage, "did this run work?"), and two folds under the stage (the model's work, where
   every liquid ended up). The same page serves an evaluation episode, a live run that has
   ended, and a check result. The tab and the replay's step are in the URL hash. */

export type StageTab = "replay" | "platemap" | "protocol" | "prep";

export interface RecordHeader {
  stepper?: { at: 1 | 2 | 3; done?: boolean }; // the person's own flow shows the stepper, not the crumbs
  crumb: { to: string; label: string };
  crumbWord: string;
  action?: { to: string; label: string }; // a pill at the crumbs' right: "Check another"
  title: string;
  titleMono?: boolean;
  badge: BadgeState;
  badgeDetail?: string; // the full sentence, in the badge's popover
  chips?: React.ReactNode; // "stopped: token budget"
  meta: string[]; // "Nemotron 3 Super 120B" · "run 3" · "2 drafts" · …
}

export interface RecordWork {
  steps: Step[];
  drafts: DraftRow[];
  summary: {
    drafts?: number | null;
    toolCalls?: number | null;
    seconds?: number | null;
    cost?: number | null;
    tokensIn?: number | null;
    tokensOut?: number | null;
  };
}

export interface RecordReview {
  text: string | null;
  findings?: Finding[]; // an earlier draft's own findings
  marked?: number[];
  loading?: boolean;
  above?: React.ReactNode; // the draft chips
  isFinal?: boolean;
}

export interface RecordLive {
  steps: Step[];
  drafts: DraftRow[];
  state: "running" | "failed" | "stopped" | "timeout";
  thinking: boolean;
  created?: number | null;
  tokensIn?: number | null;
  tokensOut?: number | null;
  cost?: number | null;
  error?: string | null;
}

export function RunRecord({
  header,
  analysis,
  analysisError,
  platemap,
  review,
  work,
  links,
  outcomeEpisode,
  onTaught,
  onNotChecked,
  live,
}: {
  header: RecordHeader;
  analysis: Analysis | null;
  analysisError?: string | null;
  platemap: PlateMap | null;
  review: RecordReview;
  work?: RecordWork; // none on a check result
  links: {
    protocolUrl: string;
    protocolName: string;
    replayUrl: string;
    jsonUrl?: string;
  };
  outcomeEpisode?: string; // "did this run work?" for an episode of the gallery or a live run
  onTaught?: () => void;
  onNotChecked?: () => void;
  live?: RecordLive; // a run in progress: the timeline in the stage, the checks filling in the rail
}) {
  const replay = analysis?.replay ?? null;
  const verify = analysis?.verify ?? null;
  // the prep sheet: the analysis's own, else (an analysis made before it had one) verify's
  const prep = analysis?.prep ?? verify?.prep ?? null;
  const findings: Finding[] = useMemo(
    () => [
      ...(analysis?.check?.findings ?? []).map((f) => ({
        ...f,
        source: "check" as const,
      })),
      ...(verify?.labware ?? []).map((f) => ({
        ...f,
        source: "verify" as const,
      })),
    ],
    [analysis, verify],
  );
  const extras = useMemo(
    () => [...reviewExtras(verify), ...trashExtras(verify, replay)],
    [verify, replay],
  );
  const technique = platemap?.technique ?? verify?.technique ?? null;
  const unplaced = useMemo(() => {
    const seen = new Set<string>();
    return [
      ...(analysis?.check?.unplaced_liquids ?? []),
      ...(verify?.unplaced_liquids ?? []),
    ].filter((u) => (seen.has(u.name) ? false : (seen.add(u.name), true)));
  }, [analysis, verify]);

  // The stage: which tab, the replay's step and view, the selected finding. The tab and the
  // step are in the hash so a link lands on what was meant (#protocol, #step=212).
  const fromHash = useMemo(() => readHash(), []);
  const [tab, setTabState] = useState<StageTab>(
    fromHash.tab ?? (platemap ? "platemap" : "replay"),
  );
  const [chosen, setChosen] = useState<boolean>(fromHash.tab != null); // the reader picked a tab; the page stops choosing
  const [step, setStep] = useState<number | undefined>(fromHash.step);
  const [view, setView] = useState<ReplayView>(initialReplayView); // 3D on a desktop, 2D on a phone
  const pickView = (v: ReplayView) => {
    setView(v);
    rememberReplayView(v);
  };
  const [highlight, setHighlight] = useState<Highlight | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [findingOpen, setFindingOpen] = useState<number | null>(null); // the rail's card, read in place
  // The hash follows the tab at once, and the step at most once a second (WebKit refuses more
  // than a hundred replaceState calls in thirty seconds, and a playing clock crosses several
  // events a second).
  const hashTimer = useRef<number | null>(null);
  const hashWanted = useRef<{ tab: StageTab; step: number | undefined }>({
    tab,
    step,
  });
  useEffect(() => {
    // A live run leaves the hash alone: the finished run opens on its replay, and a #platemap
    // written while the plan was all there was to see would read as the reader's pick.
    if (live) return;
    hashWanted.current = { tab, step: tab === "replay" ? step : undefined };
    if (hashTimer.current != null) return;
    hashTimer.current = window.setTimeout(() => {
      hashTimer.current = null;
      writeHash(hashWanted.current.tab, hashWanted.current.step);
    }, 1000);
  }, [tab, step, live]);
  useEffect(
    () => () => {
      if (hashTimer.current != null) window.clearTimeout(hashTimer.current);
    },
    [],
  );
  // A hash pasted into the same tab (#step=40) is a same-document change: read it too.
  useEffect(() => {
    const onHash = () => {
      const h = readHash();
      if (h.tab) setTabState(h.tab);
      if (h.step != null) setStep(h.step);
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  // The page opens playing from the start, so the run is seen moving at once; a link that
  // named a step opens there, paused. Played once: back on the tab later, the replay waits.
  const [autoPlay, setAutoPlay] = useState(fromHash.step === undefined);
  useEffect(() => {
    if (tab === "replay" && replay) setAutoPlay(false); // after the replay's own mount effect
  }, [tab, replay]);
  useEffect(() => {
    if (replay && step === undefined)
      setStep(autoPlay ? 0 : replay.events.length);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [replay]);
  // No replay (the simulator refused it, or the analysis is still running): open on the plate map.
  useEffect(() => {
    if (analysis && !replay && tab === "replay")
      setTabState(platemap ? "platemap" : "protocol");
  }, [analysis, replay, tab, platemap]);
  const setTab = (t: StageTab) => {
    setChosen(true);
    setTabState(t);
  };
  // The replay lands: the stage moves to it, unless the reader has picked a tab.
  useEffect(() => {
    if (replay && !chosen && tab !== "replay") setTabState("replay");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [replay]);

  function seek(f: Finding, i: number) {
    // The finding points; the stage answers: the code to its line, the replay to its event.
    setSelected(i);
    if (replay) {
      const rf =
        replay.findings.find(
          (x) =>
            x.rule_id === f.rule_id && x.line === f.line && x.title === f.title,
        ) ??
        replay.findings.find(
          (x) => x.rule_id === f.rule_id && x.line === f.line,
        );
      if (rf) {
        setStep(stepOfFinding(replay, rf));
        setView("2d"); // a finding names wells: the plate shows them best (not remembered)
        setHighlight({
          wells: rf.well_index ?? [],
          downstream: rf.downstream_index ?? [],
        });
      }
    }
  }

  const passed = analysis?.simulator.passed ?? null;
  const protocolCount =
    findings.filter((f) => f.line != null).length + extras.length;
  const tabs = [
    {
      key: "replay" as const,
      label: (
        <>
          Replay
          {!analysis && (
            <span
              className={styles.progressDot}
              aria-label="the replay is loading"
            />
          )}
        </>
      ),
      disabled: analysis != null && !replay,
      title:
        analysis && !replay
          ? "not available for this run"
          : !analysis
            ? "the replay is loading"
            : undefined,
    },
    {
      key: "platemap" as const,
      label: "Plate map",
      disabled: !platemap,
      title: platemap ? undefined : "no plate map was given",
    },
    { key: "protocol" as const, label: "Protocol", count: protocolCount },
    {
      key: "prep" as const,
      label: "Prep sheet",
      disabled: !prep,
      title: prep ? undefined : "needs a protocol the simulator passes",
    },
  ];

  return (
    <article className={styles.record}>
      <header className={styles.head}>
        {header.stepper ? (
          <Stepper at={header.stepper.at} done={header.stepper.done} />
        ) : (
          <div className={styles.crumbs}>
            <span>
              <Link to={header.crumb.to}>{header.crumb.label}</Link>{" "}
              <span className="faint">/</span>{" "}
              <span className="muted">{header.crumbWord}</span>
            </span>
            {header.action && (
              <Link to={header.action.to} className={styles.action}>
                {header.action.label}
              </Link>
            )}
          </div>
        )}
        <Title text={header.title} mono={header.titleMono} />
        <div className={styles.metaRow}>
          <Badge state={header.badge} size="lg" detail={header.badgeDetail} />
          {header.chips}
          <span className={styles.meta}>{header.meta.join(" · ")}</span>
        </div>
      </header>

      {analysisError && (
        <Notice tone="warning" title="The replay is not available">
          {analysisError}
        </Notice>
      )}

      {live && (
        <div className={styles.body}>
          <div className={styles.main}>
            {live.state === "failed" && (
              <Notice tone="error" title="The run failed">
                {live.error} · <Link to="/">start again</Link>
              </Notice>
            )}
            {live.state === "timeout" && (
              <Notice tone="warning" title="The stream timed out">
                Reload the page to read the run's state.
              </Notice>
            )}
            {live.state === "stopped" && (
              <Notice tone="warning" title="Stopped">
                Stopped before its next model call.{" "}
                <Link to="/">Start again</Link>
              </Notice>
            )}
            <Stage>
              <Timeline
                steps={live.steps}
                drafts={live.drafts}
                state={live.state}
                thinking={live.thinking}
                created={live.created}
                tokensIn={live.tokensIn}
                tokensOut={live.tokensOut}
                cost={live.cost}
                waitingWords="Starting the episode…"
              />
            </Stage>
          </div>
          <Rail>
            <RailSection title="Checks">
              <ChecksList
                analysis={null}
                findings={[]}
                hasMap={platemap != null}
                technique={technique}
                live
                liveDraft={live.drafts[live.drafts.length - 1] ?? null}
              />
            </RailSection>
            {platemap && (
              <RailSection title="Plate map">
                <PlateGrid platemap={platemap} stack />
              </RailSection>
            )}
          </Rail>
        </div>
      )}

      {!live && (
        <div className={styles.body}>
          <div className={styles.main}>
            <Stage>
              <Tabs
                items={tabs}
                value={tab}
                onChange={setTab}
                label="The stage"
                right={
                  tab === "replay" && replay ? (
                    <Segments
                      items={[
                        { key: "2d", label: "2D" },
                        { key: "3d", label: "3D" },
                      ]}
                      value={view}
                      onChange={pickView}
                      label="Replay view"
                    />
                  ) : undefined
                }
              />
              {tab === "replay" && (
                <>
                  {!analysis && <StageBone words="Replaying the protocol…" />}
                  {replay && (
                    <>
                      <Replay
                        data={replay}
                        step={step}
                        onStep={setStep}
                        highlight={highlight}
                        view={view}
                        autoPlay={autoPlay}
                      />
                    </>
                  )}
                </>
              )}
              {tab === "platemap" && platemap && (
                <PlateMapTab platemap={platemap} analysis={analysis} />
              )}
              {tab === "protocol" && (
                <div className={styles.protocol}>
                  {review.above}
                  <CodeReview
                    text={review.text}
                    loading={review.loading}
                    findings={
                      review.isFinal === false
                        ? (review.findings ?? [])
                        : findings
                    }
                    extras={review.isFinal === false ? [] : extras}
                    marked={review.marked}
                    onReplay={
                      replay && review.isFinal !== false
                        ? (f, i) => {
                            seek(f, i);
                            setTab("replay");
                          }
                        : undefined
                    }
                    list={review.isFinal === false}
                    selected={review.isFinal === false ? undefined : selected}
                    onSelect={
                      review.isFinal === false ? undefined : setSelected
                    }
                    empty={
                      analysis ? "No rule fired on this protocol." : "Checking…"
                    }
                  />
                </div>
              )}
              {tab === "prep" && prep && (
                <PrepSheet prep={prep} verify={verify} accounting={false} />
              )}
            </Stage>

            <div className={styles.folds}>
              {work && (
                <Fold
                  summary="The model's work"
                  hint={[
                    work.summary.drafts != null
                      ? plural(work.summary.drafts, "draft")
                      : null,
                    work.summary.toolCalls != null
                      ? plural(work.summary.toolCalls, "tool call")
                      : null,
                    work.summary.seconds != null
                      ? seconds(work.summary.seconds)
                      : null,
                    work.summary.cost != null ? money(work.summary.cost) : null,
                  ]
                    .filter(Boolean)
                    .join(" · ")}
                >
                  <Timeline
                    steps={work.steps}
                    drafts={work.drafts}
                    state="done"
                    thinking={false}
                    seconds={work.summary.seconds}
                    tokensIn={work.summary.tokensIn}
                    tokensOut={work.summary.tokensOut}
                    cost={work.summary.cost}
                  />
                </Fold>
              )}
              {verify && verify.accounting.length > 0 && (
                <Fold
                  summary={`Where every liquid ended up`}
                  hint={`${plural(verify.accounting.length, "liquid")} · ${plural(
                    (prep ?? verify.prep).tips.reduce((n, t) => n + t.tips, 0),
                    "tip",
                  )}`}
                >
                  <Accounting verify={verify} />
                </Fold>
              )}
              <p className={styles.links}>
                <a
                  href={links.protocolUrl}
                  download={links.protocolName}
                  title={links.protocolName}
                >
                  <svg
                    width="12"
                    height="12"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    <path d="M12 3v12M6 11l6 6 6-6M4 21h16" />
                  </svg>{" "}
                  Download the {header.badge === "verified" ? "verified " : ""}
                  protocol <span className="mono">.py</span>
                </a>
                <CopyLink />
                {links.jsonUrl && (
                  <a href={links.jsonUrl} target="_blank" rel="noreferrer">
                    JSON
                  </a>
                )}
              </p>
            </div>
          </div>

          <Rail>
            <RailSection title="Checks">
              <ChecksList
                analysis={analysis}
                findings={findings}
                hasMap={platemap != null}
                technique={technique}
                prep={prep}
                onNotChecked={onNotChecked}
                verdict={header.badgeDetail}
                onOpenTab={setTab}
                onFinding={(ruleId) => {
                  const i = findings.findIndex((f) => f.rule_id === ruleId);
                  if (i < 0) return;
                  seek(findings[i], i);
                  setFindingOpen(i);
                  requestAnimationFrame(() =>
                    document
                      .querySelector(`[data-finding="${i}"]`)
                      ?.scrollIntoView({
                        block: "nearest",
                        behavior: "smooth",
                      }),
                  );
                }}
              />
            </RailSection>
            {onTaught && unplaced.length > 0 && (
              <UnplacedLiquids liquids={unplaced} onTaught={onTaught} />
            )}
            <RailSection
              title="Findings"
              count={analysis ? findings.length + extras.length : null}
            >
              {!analysis && <Bone height={40} />}
              {analysis && findings.length === 0 && extras.length === 0 && (
                <p className={styles.none}>
                  {passed
                    ? "No rule fired on this protocol."
                    : "The simulator rejected the protocol, so nothing else was checked."}
                </p>
              )}
              <ol className={styles.findingRows}>
                {findings.map((f, i) => (
                  <li
                    key={i}
                    data-finding={i}
                    data-severity={f.severity}
                    className={`${styles.findingRow} ${selected === i ? styles.findingOn : ""}`}
                  >
                    <button
                      type="button"
                      className={styles.findingButton}
                      onClick={() => {
                        seek(f, i);
                        if (tab !== "replay" && tab !== "protocol")
                          setTab("protocol");
                      }}
                      aria-pressed={selected === i}
                    >
                      <span className={styles.findingHead}>
                        <Lozenge severity={f.severity} certain={f.certain} />
                        <span className={styles.findingTitle}>
                          {f.title.replace(/^\(proposed\)\s*/i, "")}
                        </span>
                      </span>
                      <span className={styles.findingWhere}>
                        {f.line != null && <span>line {f.line}</span>}
                        {((f.wells as WellRef[] | undefined) ?? []).length >
                          0 && (
                          <span
                            title={wellsWords((f.wells as WellRef[]) ?? [])}
                          >
                            {wellsShort((f.wells as WellRef[]) ?? [])}
                          </span>
                        )}
                        {f.source === "verify" && (
                          <span className="faint">runs in verify</span>
                        )}
                      </span>
                    </button>
                    <span className={styles.findingActions}>
                      {f.line != null && (
                        <button
                          type="button"
                          className={styles.findingIcon}
                          onClick={() => {
                            seek(f, i);
                            setTab("protocol");
                          }}
                          title="in the code"
                          aria-label={`Line ${f.line} in the protocol`}
                        >
                          Code
                        </button>
                      )}
                      {replay && (
                        <button
                          type="button"
                          className={styles.findingIcon}
                          onClick={() => {
                            seek(f, i);
                            setTab("replay");
                          }}
                          title="in the replay"
                          aria-label="The step that did it, in the replay"
                        >
                          Replay
                        </button>
                      )}
                      <button
                        type="button"
                        className={`${styles.findingIcon} ${styles.findingChevron} ${findingOpen === i ? styles.findingChevronOpen : ""}`}
                        onClick={() =>
                          setFindingOpen(findingOpen === i ? null : i)
                        }
                        aria-expanded={findingOpen === i}
                        title={findingOpen === i ? "less" : "read"}
                        aria-label={
                          findingOpen === i
                            ? "Close the finding"
                            : "Read the finding"
                        }
                      >
                        ›
                      </button>
                    </span>
                    {findingOpen === i && (
                      <div className={styles.findingCard}>
                        <FindingCard f={f} index={i} />
                      </div>
                    )}
                  </li>
                ))}
                {extras.map((x, i) => (
                  <li
                    key={`x${i}`}
                    data-severity={x.severity}
                    className={styles.findingRow}
                  >
                    <span className={styles.findingHead}>
                      <Lozenge severity={x.severity} />
                      <span className={styles.findingTitle}>{x.title}</span>
                    </span>
                    <span className={styles.findingWords}>{x.words}</span>
                    {x.step != null && replay && (
                      <span className={styles.findingActions}>
                        <button
                          type="button"
                          className={styles.findingIcon}
                          onClick={() => {
                            setStep(x.step!);
                            setHighlight(null);
                            setTab("replay");
                          }}
                          title="in the replay"
                          aria-label="The event, in the replay"
                        >
                          Replay
                        </button>
                      </span>
                    )}
                  </li>
                ))}
              </ol>
            </RailSection>
            {outcomeEpisode && <OutcomeForm episode={outcomeEpisode} />}
          </Rail>
        </div>
      )}
    </article>
  );
}

/* The request, two lines; when it runs past them, "Show all" opens the rest (and "Show less"
   closes it). Whether it runs past is measured on the page, not guessed from its length. */
export function Title({ text, mono }: { text: string; mono?: boolean }) {
  const [open, setOpen] = useState(false);
  const [clipped, setClipped] = useState(false);
  const ref = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const measure = () => setClipped(el.scrollHeight > el.clientHeight + 1);
    measure();
    const observer =
      typeof ResizeObserver !== "undefined"
        ? new ResizeObserver(measure)
        : null;
    observer?.observe(el);
    return () => observer?.disconnect();
  }, [text, open]);
  return (
    <div className={styles.titleBlock}>
      <h1
        ref={ref}
        className={`${styles.title} ${mono ? "mono" : ""} ${!open ? styles.titleClamped : ""}`}
        title={open ? undefined : text}
      >
        {text}
      </h1>
      {(clipped || open) && (
        <button
          type="button"
          className={styles.more}
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
        >
          {open ? "Show less" : "Show all"}
        </button>
      )}
    </div>
  );
}

function PlateMapTab({
  platemap,
  analysis,
}: {
  platemap: PlateMap;
  analysis: Analysis | null;
}) {
  const [segment, setSegment] = useState<"wells" | "numbers">("wells");
  return (
    <div className={styles.plateTab}>
      <Segments
        items={[
          { key: "wells", label: "Wells" },
          { key: "numbers", label: "Numbers" },
        ]}
        value={segment}
        onChange={setSegment}
        label="The plate map as"
      />
      {segment === "wells" && (
        <PlateGrid
          platemap={platemap}
          verify={analysis?.verify ?? null}
          replay={analysis?.replay ?? null}
        />
      )}
      {segment === "numbers" && (
        <PlateMapSums
          platemap={platemap}
          variant={analysis?.verify?.intent.variant}
          compact
        />
      )}
      {platemap.notes.length > 0 && (
        <Fold
          summary="The planner's notes"
          hint={plural(platemap.notes.length, "note")}
        >
          <ul className={styles.notes}>
            {platemap.notes.map((n, i) => (
              <li key={i}>{n}</li>
            ))}
          </ul>
        </Fold>
      )}
    </div>
  );
}

function CopyLink() {
  const [done, setDone] = useState(false);
  async function copy() {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setDone(true);
      setTimeout(() => setDone(false), 2000);
    } catch {
      window.prompt("Copy this link", window.location.href);
    }
  }
  return (
    <button type="button" className={styles.linkButton} onClick={copy}>
      {done ? "Link copied" : "Copy link"}
    </button>
  );
}

function StageBone({ words }: { words: string }) {
  return (
    <div className={styles.stageBone} aria-busy="true" aria-live="polite">
      <span className="sr-only">{words}</span>
      <Bone height={320} />
      <Bone height={24} width="60%" />
    </div>
  );
}

/* The whole page's skeleton, for the first load: header, stage, rail. */
export function RunRecordSkeleton() {
  return (
    <div className={styles.record} aria-busy="true" aria-live="polite">
      <span className="sr-only">Loading the run…</span>
      <div className={styles.head}>
        <Bone height={14} width="20%" />
        <Bone height={26} width="70%" />
        <Bone height={22} width="50%" />
      </div>
      <div className={styles.body}>
        <div className={styles.main}>
          <Bone height={32} width="40%" />
          <Bone height={520} />
        </div>
        <div className={styles.railBones}>
          <Bone height={90} />
          <Bone height={140} />
        </div>
      </div>
    </div>
  );
}

/* #replay · #platemap · #protocol · #prep, and #step=212 (the replay at a step). */
function readHash(): { tab?: StageTab; step?: number } {
  if (typeof window === "undefined") return {};
  const h = window.location.hash.replace(/^#/, "");
  if (!h) return {};
  const out: { tab?: StageTab; step?: number } = {};
  for (const part of h.split("&")) {
    const m = /^step=(\d+)$/.exec(part);
    if (m) {
      out.step = Number(m[1]);
      out.tab = "replay";
    } else if (
      part === "replay" ||
      part === "platemap" ||
      part === "protocol" ||
      part === "prep"
    )
      out.tab = part;
  }
  return out;
}

function writeHash(tab: StageTab, step: number | undefined) {
  if (typeof window === "undefined") return;
  const next = tab === "replay" && step != null ? `#step=${step}` : `#${tab}`;
  if (window.location.hash !== next)
    window.history.replaceState(
      null,
      "",
      `${window.location.pathname}${window.location.search}${next}`,
    );
}
