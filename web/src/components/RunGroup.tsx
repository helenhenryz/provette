import { Link } from "react-router-dom";
import type { EpisodeCard as Card } from "../lib/api";
import { money, plural, seconds } from "../lib/format";
import { Badge, Tag } from "./vocabulary";
import styles from "./RunGroup.module.css";

/* One request, its runs as rows (docs/how-it-works.md, section 9): the same request written by
   Super, by Nano best of 3, with "use as few tips as possible"; one card, a row per run. */

/* "Super", "Nano, best of 3", "Super, few tips": what tells one row from the next. */
export function runWords(e: Card): string {
  const model = e.model_label.replace(/^Nemotron 3 /, "").replace(/ \d+B$/, "");
  const best = e.candidates ? `, best of ${e.candidates.n}` : "";
  const cond =
    e.condition === "plain"
      ? ""
      : /few tips/.test(e.condition_label)
        ? ", few tips"
        : `, ${e.condition}`;
  return `${model}${best}${cond}`;
}

export function RunGroup({
  technique,
  request,
  runs,
  to,
  tag,
}: {
  technique: string;
  request: string;
  runs: Card[];
  to: (e: Card) => string;
  tag?: string;
}) {
  return (
    <section className={styles.group}>
      <div className={styles.top}>
        <span className={styles.technique}>{technique}</span>
        {tag ? (
          <Tag title="one of the fifteen harder requests">{tag}</Tag>
        ) : (
          <span className={styles.count}>{plural(runs.length, "run")}</span>
        )}
      </div>
      <p className={styles.request} title={request}>
        {request}
      </p>
      <ul className={styles.rows}>
        {runs.map((e) => (
          <li key={e.id}>
            <Link to={to(e)} className={styles.row}>
              <span className={styles.words}>{runWords(e)}</span>
              <Badge state={e.verified ? "verified" : "not_verified"} />
              <span className={styles.meta}>
                {e.drafts != null && plural(e.drafts, "draft")}
                {e.seconds != null && ` · ${seconds(e.seconds)}`}
                {e.cost_usd != null && ` · ${money(e.cost_usd)}`}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
