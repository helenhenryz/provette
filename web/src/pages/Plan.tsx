import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Notice } from "../components/Notice";
import { PlateGrid } from "../components/PlateGrid";
import { PlateMapEditor } from "../components/PlateMapEditor";
import { RunRecordSkeleton, Title } from "../components/RunRecord";
import { Timeline } from "../components/Timeline";
import {
  Badge,
  Fold,
  Rail,
  RailSection,
  Segments,
  Stage,
  Stepper,
} from "../components/vocabulary";
import { judge, live, type PlanSnapshot, type PlateMap } from "../lib/api";
import { money, plural, seconds } from "../lib/format";
import styles from "./Plan.module.css";
import { withJudge } from "../lib/withJudge";

/* Plan (docs/how-it-works.md, section 9): the planner reads the request and proposes the plate
   map, its tool calls arriving as they happen in the stage; when the map is in, the stage is
   the plate (Wells | Numbers), the rail says what it holds, and Approve starts the run. */

/* Why there is no map, in plain words: how many tries, and the last problem the
   validator named; or, when no map was ever handed in, what ran out. Never the loop's own
   "no plate map: call budget". */
function noMapWords(
  snap: Pick<PlanSnapshot, "rejections" | "stop_reason" | "tool_calls">,
): string {
  const tries = snap.rejections.length;
  if (tries > 0)
    return `The planner could not write a map in ${plural(tries, "try", "tries")}. The last problem: ${snap.rejections[tries - 1]}`;
  const why: Record<string, string> = {
    "call budget": `it used all ${plural(snap.tool_calls, "tool call")} without handing one in`,
    "token budget": "it used all its tokens without handing one in",
    "model stopped using tools": "it stopped calling the tools",
    "api errors": "the model's service kept failing",
  };
  return `The planner never handed a map in: ${why[snap.stop_reason ?? ""] ?? (snap.stop_reason || "it stopped")}.`;
}
export function PlanPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const [snap, setSnap] = useState<PlanSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [platemap, setPlatemap] = useState<PlateMap | null>(null);
  const [segment, setSegment] = useState<"wells" | "numbers">("wells");
  const [busy, setBusy] = useState<"run" | "again" | "stop" | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const key = judge.get(); // the Stop button needs the same key as starting a plan

  useEffect(() => {
    let source: EventSource | null = null;
    let alive = true;
    live.planSnapshot(id).then(
      (first) => {
        if (!alive) return;
        setSnap(first);
        if (first.state === "running") {
          source = new EventSource(live.planEventsUrl(id));
          source.addEventListener("snapshot", (e) =>
            setSnap(JSON.parse((e as MessageEvent).data) as PlanSnapshot),
          );
          source.addEventListener("done", () => source?.close());
          source.onerror = () => {
            source?.close();
            live
              .planSnapshot(id)
              .then((s) => alive && setSnap(s))
              .catch(() => undefined);
          };
        }
      },
      (e: unknown) =>
        alive && setError(e instanceof Error ? e.message : String(e)),
    );
    return () => {
      alive = false;
      source?.close();
    };
  }, [id]);
  useEffect(() => {
    if (snap?.platemap && !platemap) setPlatemap(snap.platemap);
  }, [snap?.platemap, platemap]);

  async function guarded<T>(work: () => Promise<T>): Promise<T | null> {
    setActionError(null);
    try {
      return await withJudge(work); // null if not run: the password dialog is open
    } catch (e) {
      setActionError(e instanceof Error ? e.message : String(e));
      return null;
    }
  }

  async function approve() {
    if (!snap || !platemap) return;
    setBusy("run");
    const started = await guarded(() =>
      live.start(snap.request, platemap, snap.technique),
    );
    setBusy(null);
    if (started) navigate(`/runs/${started.id}`);
  }

  async function stop() {
    setBusy("stop");
    await guarded(() => live.stopPlan(id));
    // the stream reports "stopped" once the planner has come back from its current call
  }

  async function again(anyway = false) {
    if (!snap) return;
    setBusy("again");
    const next = await guarded(() =>
      live.startPlan(snap.request, snap.technique, anyway),
    );
    setBusy(null);
    if (next) {
      setPlatemap(null);
      navigate(`/plan/${next.id}`);
    }
  }

  if (error)
    return (
      <Notice tone="error" title="No such plan">
        {error && error.toLowerCase() !== "no such plan" && <>{error} · </>}
        <Link to="/">a new run</Link> · <Link to="/examples">Examples</Link> ·{" "}
        <Link to="/check">check one</Link>
      </Notice>
    );
  if (!snap) return <RunRecordSkeleton />;
  const proposed = snap.state === "done" && snap.platemap != null;
  const stopped = snap.state === "stopped";
  const declined =
    snap.state === "done" && snap.platemap == null && snap.declined
      ? snap.declined
      : null;
  const lastStep = snap.steps[snap.steps.length - 1]?.title;
  const status =
    snap.state === "running"
      ? snap.thinking
        ? "reading the request…"
        : (lastStep ?? "starting…")
      : snap.state === "failed"
        ? "the planner failed"
        : stopped
          ? `stopped by you after ${plural(snap.tool_calls, "tool call")} for ${money(snap.cost_usd)}`
          : proposed
            ? `proposed in ${snap.seconds} s for ${money(snap.cost_usd)}`
            : declined
              ? "not a lab request"
              : "no map";
  const groups = platemap?.variants[0]?.groups ?? [];
  const pinned = Object.keys(platemap?.variants[0]?.pinned ?? {}).length;

  return (
    <article className={styles.record}>
      <header className={styles.head}>
        <Stepper at={2} done={proposed} />
        <Title text={snap.request} />
        <div className={styles.metaRow}>
          <Badge
            state={
              snap.state === "running"
                ? "running"
                : snap.state === "failed"
                  ? "failed"
                  : stopped
                    ? "stopped"
                    : proposed
                      ? "checked"
                      : "not_verified"
            }
            size="lg"
          >
            {snap.state === "running"
              ? "Planning"
              : snap.state === "failed"
                ? "Failed"
                : stopped
                  ? "Stopped"
                  : proposed
                    ? "Proposed"
                    : declined
                      ? "Not a request"
                      : "No map"}
          </Badge>
          {snap.state === "running" && key && (
            <button
              type="button"
              className={styles.stop}
              onClick={stop}
              disabled={busy === "stop"}
            >
              {busy === "stop" ? "Stopping…" : "Stop"}
            </button>
          )}
          <span className={styles.meta}>
            {snap.model_label} · {status}
          </span>
        </div>
        {actionError && !proposed && (
          <Notice
            tone="error"
            title="That didn't go through"
            onDismiss={() => setActionError(null)}
          >
            {actionError}
          </Notice>
        )}
      </header>

      <div className={styles.body}>
        <div className={styles.main}>
          {!proposed && (
            <Stage>
              <Timeline
                steps={snap.steps}
                state={snap.state}
                thinking={snap.thinking}
                created={snap.created}
                seconds={snap.seconds}
                tokensIn={snap.tokens_in}
                tokensOut={snap.tokens_out}
                cost={snap.cost_usd}
                waitingWords="Reading the request…"
              />
              {snap.state === "failed" && (
                <Notice tone="error" title="The planner failed">
                  {snap.error} · <Link to="/">start again</Link>
                </Notice>
              )}
              {stopped && (
                <Notice tone="warning" title="Stopped">
                  Stopped before its next model call.{" "}
                  <Link to="/">Start again</Link>, or{" "}
                  <button
                    type="button"
                    className={styles.linkButton}
                    onClick={() => void again()}
                    disabled={busy != null}
                  >
                    propose again
                  </button>
                  .
                </Notice>
              )}
              {declined && (
                <Notice tone="warning" title="Not a lab request">
                  {declined} No plate map was made.{" "}
                  <Link to="/">Write a request</Link> that says what should end
                  up in each well, or{" "}
                  <button
                    type="button"
                    className={styles.linkButton}
                    onClick={() => void again(true)}
                    disabled={busy != null}
                  >
                    plan it anyway
                  </button>
                  .
                </Notice>
              )}
              {snap.state === "done" && snap.platemap == null && !declined && (
                <Notice tone="warning" title="No plate map">
                  {noMapWords(snap)}{" "}
                  <Link to="/">Say the volumes and the number of samples</Link>,
                  or{" "}
                  <button
                    type="button"
                    className={styles.linkButton}
                    onClick={() => void again()}
                    disabled={busy != null}
                  >
                    propose again
                  </button>
                  .
                </Notice>
              )}
            </Stage>
          )}
          {proposed && platemap && (
            <>
              <Stage>
                <Segments
                  items={[
                    { key: "wells", label: "Wells" },
                    { key: "numbers", label: "Numbers" },
                  ]}
                  value={segment}
                  onChange={setSegment}
                  label="The plate map as"
                />
                {segment === "wells" && <PlateGrid platemap={platemap} />}
                {segment === "numbers" && (
                  <PlateMapEditor
                    platemap={platemap}
                    onChange={setPlatemap}
                    mode="numbers"
                  />
                )}
              </Stage>
              {/* the planner's turns stay, folded under the plate, as the run record keeps the model's work */}
              <div className={styles.folds}>
                <Fold
                  summary="The planner's work"
                  hint={[
                    plural(snap.tool_calls, "tool call"),
                    snap.seconds != null ? seconds(snap.seconds) : null,
                    snap.cost_usd != null ? money(snap.cost_usd) : null,
                  ]
                    .filter(Boolean)
                    .join(" · ")}
                >
                  <Timeline
                    steps={snap.steps}
                    state="done"
                    thinking={false}
                    seconds={snap.seconds}
                    tokensIn={snap.tokens_in}
                    tokensOut={snap.tokens_out}
                    cost={snap.cost_usd}
                  />
                </Fold>
              </div>
            </>
          )}
        </div>

        <Rail>
          {proposed && platemap && (
            <>
              <RailSection title="What it holds">
                <ul className={styles.holds}>
                  {pinned > 0 && <li>{plural(pinned, "pinned well")}</li>}
                  {groups.map((g, i) => (
                    <li key={i}>
                      {plural(g.members.length, "well")}{" "}
                      {g.within
                        ? `within ${g.within.join(", ")}`
                        : "anywhere on the plate"}
                      {g.order_hint === "index" && ", in order"}
                    </li>
                  ))}
                  <li>{plural(platemap.liquids.length, "liquid")}</li>
                </ul>
              </RailSection>
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
              {actionError && (
                <Notice
                  tone="error"
                  title="Couldn't start"
                  onDismiss={() => setActionError(null)}
                >
                  {actionError}
                </Notice>
              )}
              <div className={styles.controls}>
                <button
                  type="button"
                  className={styles.primary}
                  disabled={busy != null}
                  onClick={approve}
                >
                  {busy === "run"
                    ? "Starting…"
                    : "Approve and write the protocol"}
                </button>
                <button
                  type="button"
                  className={styles.quiet}
                  disabled={busy != null}
                  onClick={() => void again()}
                >
                  {busy === "again" ? "Proposing…" : "Propose again"}
                </button>
                <Link to="/" className={styles.quietLink}>
                  Change the request
                </Link>
              </div>
            </>
          )}
        </Rail>
      </div>
    </article>
  );
}
