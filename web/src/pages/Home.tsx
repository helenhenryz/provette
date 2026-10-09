import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Notice } from "../components/Notice";
import { Chip } from "../components/vocabulary";
import { ApiError, live } from "../lib/api";
import { gist, money } from "../lib/format";
import { useFetch } from "../lib/useFetch";
import styles from "./Home.module.css";
import { withJudge } from "../lib/withJudge";

/* Write (docs/how-it-works.md, section 9): the h1, the box, the button, three recent cards. */

/* The three requests a person can try with one click: ones both models verified in few drafts in
   the evaluation (eval/agent/README.md, run 3: pcr-02 in 2 and 4 drafts, brad-01 in 3 and 2, norm-01
   in 3 and 2), three techniques. A first click should show the loop landing, not a hard case. */
const SHOWN_EXAMPLES = ["pcr-02", "brad-01", "norm-01"];

/* One finished run to watch, for a visitor who has not got the key or the minute a live run takes:
   a whole 96-well qPCR plate, the job every OT-2 user knows. Its drafts show the loop at work:
   out of tips, a draw too shallow for the tip, master mix carried into the template stocks (which
   the simulator passes), then verified with nothing left. tests/api/test_gallery.py keeps it in
   the gallery and verified. */
export const SHOWCASE = "super-hard/plain/hard-pcr-01";

export function HomePage() {
  const navigate = useNavigate();
  const status = useFetch(live.status, "live");
  const [request, setRequest] = useState("");
  const [technique, setTechnique] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notARequest, setNotARequest] = useState<string | null>(null); // the gate's sentence, with "Send anyway"

  const examples = useMemo(() => {
    const all = status.data?.examples ?? [];
    const picked = SHOWN_EXAMPLES.map((id) =>
      all.find((e) => e.id === id),
    ).filter((e): e is NonNullable<typeof e> => Boolean(e));
    return picked.length >= 3 ? picked : all.slice(0, 3);
  }, [status.data]);
  const techniques = useMemo(
    () =>
      [
        ...new Set(
          (status.data?.examples ?? [])
            .map((e) => e.technique)
            .filter((t): t is string => Boolean(t)),
        ),
      ].sort(),
    [status.data],
  );
  const off = status.data && !status.data.enabled;
  const paused = status.data && status.data.remaining_usd <= 0;
  const ready = request.trim().length >= 10 && !busy && !off && !paused;
  const buttonWords = busy
    ? "Starting…"
    : off
      ? "Needs the key"
      : paused
        ? "Budget spent today"
        : "Write it";

  async function write(anyway = false) {
    setError(null);
    setNotARequest(null);
    setBusy(true);
    try {
      // with no password, the dialog opens and the request stays here to send again
      const started = await withJudge(() =>
        live.startPlan(request.trim(), technique || null, anyway),
      );
      if (started) navigate(`/plan/${started.id}`);
      else setBusy(false); // it did not run: the dialog is asking for the password
    } catch (e) {
      if (e instanceof ApiError && e.code === "not_a_request")
        setNotARequest(e.message);
      else setError(e instanceof Error ? e.message : String(e));
      setBusy(false);
    }
  }

  return (
    <div className={styles.page}>
      <header className={styles.hero}>
        <h1 className={styles.headline}>
          <Mark />
          Say what should end up in every well.
        </h1>
      </header>

      <section className={styles.composer} aria-label="Your request">
        <textarea
          className={styles.request}
          value={request}
          onChange={(e) => {
            setRequest(e.target.value);
            setNotARequest(null);
            setError(null); // an edit answers the error
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey) && ready)
              void write();
          }}
          rows={3}
          maxLength={2000}
          placeholder="8 PCR reactions, 20 µl master mix and 5 µl sample each, in a 96-well PCR plate"
          aria-label="Your request, in your own words"
        />
        <div className={styles.toolbar}>
          <select
            className={styles.select}
            value={technique}
            onChange={(e) => setTechnique(e.target.value)}
            aria-label="Technique"
          >
            <option value="">Any technique</option>
            {techniques.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
          <div className={styles.toolRight}>
            {status.data && (
              <span
                className={styles.model}
                title={`${status.data.model_label} on Nebius Token Factory: the plate map first, then the protocol, with the checks as its tools${!off ? ` · ${money(status.data.spent_today_usd)} of ${money(status.data.cap_usd)} spent today` : ""}`}
              >
                {status.data.model_label}
              </span>
            )}
            <button
              type="button"
              className={`${styles.send} ${!busy && !off && !paused ? styles.sendArrow : styles.sendWords}`}
              disabled={!ready}
              onClick={() => void write()}
              aria-label={buttonWords}
            >
              {!busy && !off && !paused ? (
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.4"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <path d="M12 19V5M5 12l7-7 7 7" />
                </svg>
              ) : (
                buttonWords
              )}
            </button>
          </div>
        </div>
      </section>

      <div className={styles.chips} aria-label="Examples">
        {examples.map((e) => (
          <Chip
            key={e.id}
            on={request === e.request}
            onClick={() => {
              setRequest(e.request);
              if (e.technique) setTechnique(e.technique);
            }}
            title={e.request}
          >
            {e.technique ?? gist(e.request)}
          </Chip>
        ))}
      </div>
      <p className={styles.showcase}>
        <Link to={`/episodes/${SHOWCASE}`}>
          Or watch a finished run: a 96-well qPCR plate
          <span aria-hidden="true"> →</span>
        </Link>
      </p>

      {notARequest && (
        <Notice tone="warning" title="Not a lab request">
          {notARequest}{" "}
          <button
            type="button"
            className={styles.anyway}
            onClick={() => void write(true)}
            disabled={busy}
          >
            Send anyway
          </button>
        </Notice>
      )}
      {error && (
        <Notice
          tone="error"
          title="Couldn't start"
          onDismiss={() => setError(null)}
        >
          {error}
        </Notice>
      )}
    </div>
  );
}

/* The Provette mark beside the greeting, as a chat app's logo beside its own. */
function Mark() {
  return (
    <svg className={styles.mark} viewBox="0 0 32 32" aria-hidden="true">
      <rect width="32" height="32" rx="8" fill="var(--verified)" />
      <circle cx="11" cy="11" r="3.3" fill="var(--on-accent)" />
      <circle cx="21" cy="11" r="3.3" fill="var(--on-accent)" opacity=".55" />
      <circle cx="11" cy="21" r="3.3" fill="var(--on-accent)" opacity=".55" />
      <circle cx="21" cy="21" r="3.3" fill="var(--on-accent)" />
    </svg>
  );
}
