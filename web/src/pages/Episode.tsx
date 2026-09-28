import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Notice } from "../components/Notice";
import {
  RunRecord,
  RunRecordSkeleton,
  type RecordReview,
} from "../components/RunRecord";
import { Chip, Tag } from "../components/vocabulary";
import { api, type Analysis, type Draft, type EpisodeDetail } from "../lib/api";
import { money, plural, seconds } from "../lib/format";
import { checksRaised } from "../lib/verdict";
import { useFetch } from "../lib/useFetch";
import styles from "./Episode.module.css";

/* One evaluation episode, as the run record (docs/how-it-works.md, section 9). */
export function EpisodePage() {
  const { set, condition, requestId } = useParams();
  const id = `${set}/${condition}/${requestId}`;
  const episode = useFetch(() => api.episode(id), `episode:${id}`);
  const [round, setRound] = useState(0); // bumped when a word is taught: the checks run again
  const analysis = useFetch(() => api.analysis(id), `analysis:${id}:${round}`);

  if (episode.loading) return <RunRecordSkeleton />;
  if (episode.error || !episode.data)
    return (
      <Notice
        tone="error"
        title={
          episode.status === 404
            ? "No such episode"
            : "The episode could not be loaded"
        }
      >
        {episode.error && episode.error.toLowerCase() !== "no such episode" && (
          <>{episode.error} · </>
        )}
        <Link to="/examples">Examples</Link> · <Link to="/">a new run</Link> ·{" "}
        <Link to="/check">check one</Link>
      </Notice>
    );
  return (
    <EpisodeView
      episode={episode.data}
      analysis={analysis.data}
      analysisError={analysis.error}
      source={{
        replayUrl: api.replayUrl(id),
        protocolUrl: api.protocolUrl(id),
        jsonUrl: `/api/episodes/${id}/analysis`,
        draft: (n) => api.draft(id, n),
        key: id,
      }}
      crumb={{ to: "/examples", label: "Examples" }}
      onTaught={() => setRound((r) => r + 1)}
    />
  );
}

/* Where an episode's files come from: the gallery's routes, or a live run's. */
export interface EpisodeSource {
  key: string;
  replayUrl: string;
  protocolUrl: string;
  jsonUrl?: string;
  draft: (n: number) => Promise<Draft>;
}

export function EpisodeView({
  episode,
  analysis,
  analysisError,
  source,
  crumb,
  onTaught,
  stepper,
}: {
  episode: EpisodeDetail;
  analysis: Analysis | null;
  analysisError?: string | null;
  source: EpisodeSource;
  crumb: { to: string; label: string };
  onTaught?: () => void;
  stepper?: { at: 1 | 2 | 3; done?: boolean };
}) {
  const navigate = useNavigate();
  const review = useDraftReview(source, episode);
  const stop = episode.outcome.stop_reason;
  const stopChip =
    stop && stop !== "submitted" ? (
      <Tag tone="warning">stopped: {stop}</Tag>
    ) : null;
  // A condition is a chip beside the badge: "few tips"; the sentence is its hover.
  const conditionChip =
    episode.condition !== "plain" ? (
      <Tag title={episode.condition_label}>
        {/few tips/.test(episode.condition_label)
          ? "few tips"
          : episode.condition.replace(/-/g, " ")}
      </Tag>
    ) : null;
  const raised = checksRaised(episode.draft_rows, episode.final_draft);
  const c = episode.candidates; // "2 of 3 candidates verified": the one shown is the one the checks kept
  const meta = [
    episode.model_label,
    c ? `${c.verified} of ${c.n} candidates verified` : null,
    episode.drafts != null ? plural(episode.drafts, "draft") : null,
    raised,
    episode.tool_calls != null ? plural(episode.tool_calls, "tool call") : null,
    episode.seconds != null ? seconds(episode.seconds) : null,
    episode.cost_usd != null ? money(episode.cost_usd) : null,
  ].filter((p): p is string => Boolean(p));
  return (
    <RunRecord
      header={{
        stepper,
        crumb,
        crumbWord: episode.technique ?? episode.request_id,
        title: episode.request,
        badge: episode.verified ? "verified" : "not_verified",
        badgeDetail: `${episode.outcome.sentence} The checks ran ${episode.runner_label}.`,
        chips: (
          <>
            {stopChip}
            {conditionChip}
          </>
        ),
        meta,
      }}
      analysis={analysis}
      analysisError={analysisError}
      platemap={episode.platemap}
      review={review}
      work={{
        steps: episode.steps,
        drafts: episode.draft_rows,
        summary: {
          drafts: episode.drafts,
          toolCalls: episode.tool_calls,
          seconds: episode.seconds,
          cost: episode.cost_usd,
          tokensIn: episode.tokens_in,
          tokensOut: episode.tokens_out,
        },
      }}
      links={{
        protocolUrl: source.protocolUrl,
        protocolName: `${episode.request_id}.py`,
        replayUrl: source.replayUrl,
        jsonUrl: source.jsonUrl,
      }}
      outcomeEpisode={episode.id}
      onTaught={onTaught}
      onNotChecked={() => navigate("/rules/new")}
    />
  );
}

/* The drafts: which one the chips show, its text, and what the review pane should mark. The
   final draft shows the analysis's findings; an earlier draft shows what its own checks said. */
function useDraftReview(
  source: EpisodeSource,
  episode: EpisodeDetail,
): RecordReview {
  const finalN =
    episode.final_draft ??
    episode.draft_rows[episode.draft_rows.length - 1]?.n ??
    0;
  const [n, setN] = useState<number>(finalN);
  const [asWritten, setAsWritten] = useState(false);
  const draft = useFetch(() => source.draft(n), `draft:${source.key}:${n}`);
  const row = episode.draft_rows.find((d) => d.n === n);
  const err =
    row?.simulator === "rejected" ? draft.data?.checks?.simulator_error : null;
  const m = typeof err === "string" ? /^line (\d+)/.exec(err) : null;
  const marked = m ? [Number(m[1])] : [];
  const isFinal = n === finalN;
  const text = draft.data
    ? asWritten && draft.data.as_written
      ? draft.data.as_written
      : draft.data.text
    : null;
  const above = (
    <div className={styles.draftBar}>
      <div className={styles.tabs} role="group" aria-label="Drafts">
        {episode.draft_rows.map((d) => {
          const errors =
            d.findings?.filter((f) => f.severity === "error").length ?? 0;
          const count = d.findings?.length ?? 0;
          return (
            <Chip
              key={d.n}
              on={d.n === n}
              onClick={() => setN(d.n)}
              title={d.summary?.title ?? "not checked"}
            >
              draft {d.n}
              {d.n === finalN && <span className="muted"> · final</span>}
              {count > 0 && (
                <span className="muted">
                  {" "}
                  ·{" "}
                  {errors ? plural(errors, "error") : plural(count, "finding")}
                </span>
              )}
            </Chip>
          );
        })}
      </div>
      {row?.summary && (
        <span
          className={`${styles.draftSummary} ${styles[`text_${row.summary.status}`]}`}
        >
          {row.summary.title}
        </span>
      )}
      {draft.data?.as_written && (
        <label
          className={styles.asWritten}
          title="before the known slips were repaired"
        >
          <input
            type="checkbox"
            checked={asWritten}
            onChange={(e) => setAsWritten(e.target.checked)}
          />{" "}
          as the model wrote it
        </label>
      )}
    </div>
  );
  return {
    text,
    findings: row?.findings ?? [],
    marked: asWritten ? [] : marked,
    loading: draft.loading,
    above,
    isFinal,
  };
}
