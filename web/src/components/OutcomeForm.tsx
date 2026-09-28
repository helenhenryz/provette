import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { outcomes, type RunOutcome } from "../lib/api";
import { when } from "../lib/format";
import styles from "./OutcomeForm.module.css";
import { withJudge } from "../lib/withJudge";

/* The failed-run record: "Did this run work?", and two sentences when it did not. The record
   is the seed of a rule; the rules page lists the failures without a rule yet. */
export function OutcomeForm({ episode }: { episode: string }) {
  const [latest, setLatest] = useState<RunOutcome | null | undefined>(
    undefined,
  );
  const [answer, setAnswer] = useState<boolean | null>(null);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    outcomes.forEpisode(episode).then(
      (r) => alive && setLatest(r.latest),
      () => alive && setLatest(null),
    );
    return () => {
      alive = false;
    };
  }, [episode]);

  async function save(ok: boolean) {
    setBusy(true);
    setError(null);
    try {
      const row = await withJudge(() =>
        outcomes.record({ episode, ok, note: ok ? "" : note }),
      );
      if (!row) return; // not run: the password dialog is open
      setLatest(row);
      setAnswer(null);
      setNote("");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={styles.box}>
      <div className={styles.question}>Did this run work?</div>
      {latest && (
        <p className={styles.recorded}>
          {when(latest.when)}:{" "}
          {latest.ok ? "worked." : `did not. ${latest.note}`}{" "}
          <button
            type="button"
            className={styles.link}
            onClick={() => setAnswer(latest.ok ? false : true)}
          >
            change
          </button>
          {!latest.ok && (
            <>
              {" · "}
              <Link to="/rules#failures">see Failures</Link>
            </>
          )}
        </p>
      )}
      {(latest === null || answer != null) && (
        <div className={styles.controls}>
          <button
            type="button"
            className={`${styles.choice} ${answer === true ? styles.chosen : ""}`}
            onClick={() => setAnswer(true)}
          >
            Yes
          </button>
          <button
            type="button"
            className={`${styles.choice} ${answer === false ? styles.chosen : ""}`}
            onClick={() => setAnswer(false)}
          >
            No
          </button>
          {answer === false && (
            <textarea
              className={styles.note}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={2}
              maxLength={600}
              placeholder="What went wrong, and in which wells"
            />
          )}
          {answer != null && (
            <div className={styles.row}>
              <button
                type="button"
                className={styles.save}
                disabled={busy || (answer === false && note.trim().length < 3)}
                onClick={() => save(answer)}
              >
                {busy ? "Saving…" : "Save"}
              </button>
            </div>
          )}
          {error && <p className={styles.error}>{error}</p>}
        </div>
      )}
      {latest === undefined && <p className="faint small">Loading…</p>}
    </div>
  );
}
