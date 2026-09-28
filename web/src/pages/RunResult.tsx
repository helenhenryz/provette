import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Notice } from "../components/Notice";
import { RunRecord, RunRecordSkeleton } from "../components/RunRecord";
import { Tag } from "../components/vocabulary";
import {
  ApiError,
  judge,
  live,
  type Analysis,
  type EpisodeDetail,
  type RunSnapshot,
} from "../lib/api";
import { plural } from "../lib/format";
import { EpisodeView } from "./Episode";
import styles from "./Plan.module.css";

/* Steps 2 and 3 of the loop, live, at a stable address: the model's tool calls stream in as
   rows, each draft followed by the checker's verdict for it; when it ends, the page is the
   same verdict page as any episode's, and it appears under Past runs. */
export function RunResultPage() {
  const { id = "" } = useParams();
  const [snap, setSnap] = useState<RunSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [stopping, setStopping] = useState(false);
  const [stopError, setStopError] = useState<string | null>(null);
  const key = judge.get(); // the Stop button needs the same key as starting a run

  useEffect(() => {
    let source: EventSource | null = null;
    let alive = true;
    live.snapshot(id).then(
      (first) => {
        if (!alive) return;
        setSnap(first);
        if (first.state === "running") {
          source = new EventSource(live.eventsUrl(id));
          source.addEventListener("snapshot", (e) =>
            setSnap(JSON.parse((e as MessageEvent).data) as RunSnapshot),
          );
          source.addEventListener("done", () => source?.close());
          source.onerror = () => {
            // The stream dropped: read the state once more rather than spin.
            source?.close();
            live
              .snapshot(id)
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
    if (snap?.state === "done" && !analysis) {
      live
        .analysis(id)
        .then(setAnalysis, (e: unknown) =>
          setAnalysisError(e instanceof Error ? e.message : String(e)),
        );
    }
  }, [snap?.state, id, analysis]);

  if (error)
    return (
      <Notice tone="error" title="No such run">
        {error} · <Link to="/">start one</Link>
      </Notice>
    );
  if (!snap) return <RunRecordSkeleton />;

  async function stop() {
    setStopping(true);
    setStopError(null);
    try {
      await live.stopRun(id);
      // the stream reports "stopped" once the model has come back from its current call
    } catch (e) {
      setStopping(false);
      if (e instanceof ApiError && e.status === 401) judge.requestUnlock();
      setStopError(e instanceof Error ? e.message : String(e));
    }
  }

  if (snap.state === "done" && snap.outcome) {
    const episode = snap as unknown as EpisodeDetail;
    return (
      <EpisodeView
        episode={episode}
        analysis={analysis}
        analysisError={analysisError}
        source={{
          key: `run:${id}`,
          replayUrl: live.replayUrl(id),
          protocolUrl: live.protocolUrl(id),
          jsonUrl: `/api/runs/${id}/analysis`,
          draft: (n) => live.draft(id, n),
        }}
        crumb={{ to: "/", label: "New run" }}
        stepper={{ at: 3, done: true }}
      />
    );
  }
  const last = snap.draft_rows[snap.draft_rows.length - 1];
  const stopped = snap.state === "stopped";
  return (
    <RunRecord
      header={{
        stepper: { at: 3 },
        crumb: { to: "/", label: "New run" },
        crumbWord: "live",
        title: snap.request,
        badge:
          snap.state === "failed" ? "failed" : stopped ? "stopped" : "running",
        chips: (
          <>
            {snap.state === "running" && key && (
              <button
                type="button"
                className={styles.stop}
                onClick={stop}
                disabled={stopping}
              >
                {stopping ? "Stopping…" : "Stop"}
              </button>
            )}
            {stopError && <Tag tone="warning">{stopError}</Tag>}
          </>
        ),
        // the model and where the run is; the time, tokens and cost are the timeline's stat bar
        meta: [
          snap.model_label,
          stopped
            ? `stopped by you after ${plural(snap.tool_calls ?? 0, "tool call")}`
            : last
              ? `draft ${last.n}`
              : "starting",
        ],
      }}
      analysis={null}
      platemap={snap.platemap}
      review={{ text: null }}
      links={{
        protocolUrl: live.protocolUrl(id),
        protocolName: `${id}.py`,
        replayUrl: live.replayUrl(id),
      }}
      live={{
        steps: snap.steps,
        drafts: snap.draft_rows,
        state:
          snap.state === "running"
            ? "running"
            : snap.state === "failed"
              ? "failed"
              : stopped
                ? "stopped"
                : "timeout",
        thinking: snap.thinking,
        created: snap.created,
        tokensIn: snap.tokens_in,
        tokensOut: snap.tokens_out,
        cost: snap.cost_usd,
        error: snap.error,
      }}
    />
  );
}
