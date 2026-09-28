import { useMemo, useState } from "react";
import { Loading, Notice } from "../components/Notice";
import { RunGroup } from "../components/RunGroup";
import { Bone, Chip } from "../components/vocabulary";
import { api, type EpisodeCard as Card } from "../lib/api";
import { useFetch } from "../lib/useFetch";
import styles from "./Gallery.module.css";

/* Examples (docs/how-it-works.md, section 9): what Provette does on real requests. The evaluation's
   current runs, the request as written, grouped by request with a row per model (Super, Nano best
   of 3); a harder request carries a tag. The numbers across all of them are on Methods, and a
   person's own runs, plans and checks are in the sidebar, so this page is examples only. */

export function GalleryPage() {
  const { data, error, loading } = useFetch(api.episodes, "episodes");
  const [technique, setTechnique] = useState<string>("all");

  const order = useMemo(() => data?.sets ?? [], [data]);
  const pool = useMemo(
    () => (data?.episodes ?? []).filter((e) => e.condition === "plain"),
    [data],
  );
  const techniques = useMemo(() => {
    const counts = new Map<string, Set<string>>();
    for (const e of pool) {
      const t = e.technique ?? e.request_id;
      counts.set(t, (counts.get(t) ?? new Set()).add(e.request_id));
    }
    return [...counts.entries()]
      .map(([t, ids]) => [t, ids.size] as const)
      .sort((a, b) => a[0].localeCompare(b[0]));
  }, [pool]);
  const groups = useMemo(() => {
    const by = new Map<
      string,
      { technique: string; request: string; harder: boolean; runs: Card[] }
    >();
    for (const e of pool) {
      if (technique !== "all" && (e.technique ?? e.request_id) !== technique)
        continue;
      const key = `${e.request_id}|${e.request}`;
      const g = by.get(key) ?? {
        technique: e.technique ?? e.request_id,
        request: e.request,
        harder: e.request_id.startsWith("hard-"),
        runs: [],
      };
      g.runs.push(e);
      by.set(key, g);
    }
    const list = [...by.values()];
    list.forEach((g) =>
      g.runs.sort(
        (a, b) =>
          order.indexOf(a.set) - order.indexOf(b.set) ||
          a.model_label.localeCompare(b.model_label),
      ),
    );
    return list.sort(
      (a, b) =>
        Number(a.harder) - Number(b.harder) ||
        a.technique.localeCompare(b.technique) ||
        a.request.localeCompare(b.request),
    );
  }, [pool, technique, order]);

  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <h1>Examples</h1>
        <p className={styles.sub}>
          The evaluation's requests: each protocol written by Nemotron on Nebius
          Token Factory and checked by Provette.
        </p>
      </header>

      {error && (
        <Notice tone="error" title="The examples could not be loaded">
          {error}
        </Notice>
      )}
      {loading && (
        <div className={styles.grid} aria-busy="true">
          {[0, 1, 2, 3].map((i) => (
            <Bone key={i} height={150} />
          ))}
          <Loading what="Loading the examples" />
        </div>
      )}
      {data && (
        <>
          <div className={styles.toolbar}>
            <div className={styles.chips} role="group" aria-label="Technique">
              <Chip
                on={technique === "all"}
                count={techniques.reduce((n, [, count]) => n + count, 0)}
                onClick={() => setTechnique("all")}
              >
                All
              </Chip>
              {techniques.map(([name, count]) => (
                <Chip
                  key={name}
                  on={technique === name}
                  count={count}
                  onClick={() => setTechnique(name)}
                >
                  {name}
                </Chip>
              ))}
            </div>
          </div>
          <div className={styles.grid}>
            {groups.map((g) => (
              <RunGroup
                key={g.runs[0].id}
                technique={g.technique}
                request={g.request}
                runs={g.runs}
                tag={g.harder ? "harder" : undefined}
                to={(e) => `/episodes/${e.id}`}
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
