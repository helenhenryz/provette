import { useEffect, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { runSettings, type RunSetting } from "../lib/api";
import type { Theme } from "../lib/theme";
import styles from "./Settings.module.css";
import { withJudge } from "../lib/withJudge";

/* Settings, as a chat app's: a dialog with a short list of sections on the left and rows of
   "what it is · the control" on the right. General is this browser's (the theme); Runs and
   plans are the deployment's budgets (api/run_settings.py), saved with the judge key and
   reset to the defaults in one click. */

type Section = "general" | "runs";

export function Settings({
  onClose,
  theme,
  onTheme,
}: {
  onClose: () => void;
  theme: Theme;
  onTheme: (t: Theme) => void;
}) {
  const [section, setSection] = useState<Section>("general");
  const dialog = useRef<HTMLDivElement>(null);
  useEffect(() => {
    dialog.current?.focus();
    const key = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", key);
    return () => document.removeEventListener("keydown", key);
  }, [onClose]);

  return createPortal(
    <div
      className={styles.scrim}
      onMouseDown={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        ref={dialog}
        className={styles.dialog}
        role="dialog"
        aria-modal="true"
        aria-label="Settings"
        tabIndex={-1}
      >
        <nav className={styles.nav} aria-label="Settings sections">
          <div className={styles.navLabel}>Settings</div>
          <button
            type="button"
            className={`${styles.navItem} ${section === "general" ? styles.navOn : ""}`}
            onClick={() => setSection("general")}
            aria-current={section === "general" ? "page" : undefined}
          >
            General
          </button>
          <button
            type="button"
            className={`${styles.navItem} ${section === "runs" ? styles.navOn : ""}`}
            onClick={() => setSection("runs")}
            aria-current={section === "runs" ? "page" : undefined}
          >
            Runs and plans
          </button>
        </nav>
        <div className={styles.body}>
          <button
            type="button"
            className={styles.close}
            onClick={onClose}
            aria-label="Close the settings"
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              aria-hidden="true"
            >
              <path d="M6 6l12 12M18 6L6 18" />
            </svg>
          </button>
          {section === "general" ? (
            <General theme={theme} onTheme={onTheme} />
          ) : (
            <Budgets />
          )}
        </div>
      </div>
    </div>,
    document.body,
  );
}

function Row({
  label,
  words,
  children,
}: {
  label: string;
  words?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className={styles.row}>
      <div className={styles.rowText}>
        <div className={styles.rowLabel}>{label}</div>
        {words && <div className={styles.rowWords}>{words}</div>}
      </div>
      <div className={styles.rowControl}>{children}</div>
    </div>
  );
}

const THEMES: { value: Theme; label: string }[] = [
  { value: "auto", label: "System" },
  { value: "light", label: "Light" },
  { value: "dark", label: "Dark" },
];

function General({
  theme,
  onTheme,
}: {
  theme: Theme;
  onTheme: (t: Theme) => void;
}) {
  return (
    <section>
      <h2 className={styles.heading}>Appearance</h2>
      <Row label="Theme" words="Kept in this browser.">
        <div className={styles.segments} role="radiogroup" aria-label="Theme">
          {THEMES.map((t) => (
            <button
              key={t.value}
              type="button"
              role="radio"
              aria-checked={theme === t.value}
              className={`${styles.segment} ${theme === t.value ? styles.segmentOn : ""}`}
              onClick={() => onTheme(t.value)}
            >
              {t.label}
            </button>
          ))}
        </div>
      </Row>
    </section>
  );
}

function Budgets() {
  const [rows, setRows] = useState<RunSetting[] | null>(null);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [note, setNote] = useState<{
    tone: "ok" | "error";
    words: string;
  } | null>(null);
  const [busy, setBusy] = useState(false);

  function take(settings: RunSetting[]) {
    setRows(settings);
    setDraft(Object.fromEntries(settings.map((s) => [s.key, String(s.value)])));
  }
  useEffect(() => {
    runSettings.get().then(
      (r) => take(r.settings),
      (e: unknown) =>
        setNote({
          tone: "error",
          words: e instanceof Error ? e.message : String(e),
        }),
    );
  }, []);

  const changed = rows
    ? rows.filter((s) => draft[s.key] !== String(s.value))
    : [];
  const invalid = rows
    ? rows.filter((s) => {
        const n = Number(draft[s.key]);
        return !Number.isInteger(n) || n < s.low || n > s.high;
      })
    : [];
  const atDefaults = rows ? rows.every((s) => s.value === s.default) : true;

  async function act(
    work: () => Promise<{ settings: RunSetting[] }>,
    done: string,
  ) {
    setNote(null);
    setBusy(true);
    try {
      const r = await withJudge(work);
      if (!r) return; // not run: the password dialog is open
      take(r.settings);
      setNote({ tone: "ok", words: done });
    } catch (e) {
      setNote({
        tone: "error",
        words: e instanceof Error ? e.message : String(e),
      });
    } finally {
      setBusy(false);
    }
  }

  const groups = rows ? [...new Set(rows.map((s) => s.group))] : [];
  return (
    <section>
      <p className={styles.lead}>
        For everyone on this deployment, from the next plan or run. Changing
        them needs the judge key.
      </p>
      {!rows && !note && <p className={styles.rowWords}>Loading…</p>}
      {groups.map((g) => (
        <div key={g} className={styles.group}>
          <h2 className={styles.heading}>{g}</h2>
          {rows!
            .filter((s) => s.group === g)
            .map((s) => {
              const bad = invalid.includes(s);
              return (
                <Row key={s.key} label={s.label} words={s.words}>
                  <div className={styles.field}>
                    <div className={styles.fieldRow}>
                      {draft[s.key] !== String(s.default) && (
                        <button
                          type="button"
                          className={styles.toDefault}
                          onClick={() => {
                            setNote(null);
                            setDraft((d) => ({
                              ...d,
                              [s.key]: String(s.default),
                            }));
                          }}
                          title={`Back to the default, ${s.default.toLocaleString()}`}
                          aria-label={`${s.label}: back to the default, ${s.default.toLocaleString()}`}
                        >
                          <svg
                            width="14"
                            height="14"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            aria-hidden="true"
                          >
                            <path d="M3 12a9 9 0 1 0 3-6.7L3 8" />
                            <path d="M3 3v5h5" />
                          </svg>
                        </button>
                      )}
                      <input
                        className={`${styles.number} ${bad ? styles.numberBad : ""}`}
                        type="number"
                        inputMode="numeric"
                        min={s.low}
                        max={s.high}
                        step={1}
                        value={draft[s.key] ?? ""}
                        onChange={(e) => {
                          setNote(null);
                          setDraft((d) => ({ ...d, [s.key]: e.target.value }));
                        }}
                        aria-label={s.label}
                        aria-invalid={bad}
                        aria-describedby={`range-${s.key}`}
                      />
                    </div>
                    <span
                      id={`range-${s.key}`}
                      className={`${styles.range} ${bad ? styles.rangeBad : ""}`}
                    >
                      {s.low.toLocaleString()}–{s.high.toLocaleString()}
                    </span>
                  </div>
                </Row>
              );
            })}
        </div>
      ))}
      {rows && (
        <div className={styles.foot}>
          <button
            type="button"
            className="btn"
            onClick={() =>
              void act(() => runSettings.reset(), "Back to the defaults.")
            }
            disabled={busy || (atDefaults && changed.length === 0)}
          >
            Reset to defaults
          </button>
          <span className={styles.footSpace} />
          {note && (
            <span
              className={note.tone === "ok" ? styles.noteOk : styles.noteError}
              role="status"
            >
              {note.words}
            </span>
          )}
          <button
            type="button"
            className="btn primary"
            onClick={() =>
              void act(
                () =>
                  runSettings.save(
                    Object.fromEntries(
                      changed.map((s) => [s.key, Number(draft[s.key])]),
                    ),
                  ),
                "Saved.",
              )
            }
            disabled={busy || changed.length === 0 || invalid.length > 0}
          >
            {busy ? "Saving…" : "Save"}
          </button>
        </div>
      )}
      {!rows && note && <p className={styles.noteError}>{note.words}</p>}
    </section>
  );
}
