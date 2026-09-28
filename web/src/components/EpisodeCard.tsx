import { Link } from "react-router-dom";
import type { EpisodeCard as Card } from "../lib/api";
import { money, plural, seconds } from "../lib/format";
import styles from "./EpisodeCard.module.css";
import { Badge, Tag } from "./vocabulary";

/* One pre-run episode in the gallery: the gist of the request (the whole request on hover),
   the model, the verdict, the cost and the time. */
/* "Super", "Nano, best of 3", "Super, few tips": what tells this card from its neighbours. */
function runWords(e: Card): string {
  const model = e.model_label.replace(/^Nemotron 3 /, "").replace(/ \d+B$/, "");
  const best = e.candidates ? `, best of ${e.candidates.n}` : "";
  const cond =
    e.condition === "plain"
      ? ""
      : e.condition === "few_tips" || /few tips/.test(e.condition_label)
        ? ", few tips"
        : `, ${e.condition}`;
  return `${model}${best}${cond}`;
}

export function EpisodeCard({
  episode,
  to,
  state,
}: {
  episode: Card;
  to?: string;
  state?: "running" | "done" | "failed";
}) {
  const live = episode.set === "runs";
  return (
    <Link to={to ?? `/episodes/${episode.id}`} className={styles.card}>
      <div className={styles.top}>
        <span className={styles.technique}>
          {episode.technique ?? episode.request_id}
          <span className={styles.run}> · {runWords(episode)}</span>
        </span>
        <Badge
          state={
            state === "running"
              ? "running"
              : state === "failed"
                ? "failed"
                : episode.verified
                  ? "verified"
                  : "not_verified"
          }
        />
      </div>
      <p className={styles.request} title={episode.request}>
        {episode.request}
      </p>
      <div className={styles.meta}>
        <span className={styles.item}>
          {plural(episode.drafts ?? 0, "draft")}
        </span>
        <span className={styles.item}>{seconds(episode.seconds)}</span>
        <span className={styles.item}>{money(episode.cost_usd)}</span>
        {live && <Tag title="a run made on this deployment">live</Tag>}
      </div>
      {episode.condition !== "plain" && (
        <div className={styles.condition}>{episode.condition_label}</div>
      )}
    </Link>
  );
}
