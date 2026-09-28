import { useEffect, useId, useRef, useState } from "react";
import { Link } from "react-router-dom";
import styles from "./vocabulary.module.css";

/* The component vocabulary of docs/how-it-works.md, section 9, by name, so the code and
   the proposal agree:

     Badge    a static status word with a dot: Verified · Not verified · Running · Checked
     Lozenge  a severity: ERROR · WARNING · NOTE
     Chip     an interactive tag: a technique, a draft, a filter, an answer
     Row      label · value, one line: the unit of the rail and of stats
     Fold     a <details> closed by default; never holds anything a user must see
     Tabs     segments inside the stage; four at most
     Popover  hover or tap detail; one at a time
     Stage    the fixed-height region that holds the replay, the plate, the code
     Rail     the sticky right column: the checks, the findings, the teaching cards */

export type BadgeState =
  "verified" | "not_verified" | "running" | "checked" | "failed" | "stopped";
const BADGE_WORDS: Record<BadgeState, string> = {
  verified: "Verified",
  not_verified: "Not verified",
  running: "Running",
  checked: "Checked",
  failed: "Failed",
  stopped: "Stopped",
};

export function Badge({
  state,
  size = "sm",
  detail,
  children,
}: {
  state: BadgeState;
  size?: "sm" | "lg";
  detail?: React.ReactNode;
  children?: React.ReactNode;
}) {
  const body = (
    <span
      className={`${styles.badge} ${styles[`badge_${state}`]} ${size === "lg" ? styles.badgeLg : ""}`}
    >
      <span className={styles.badgeDot} aria-hidden="true" />
      {children ?? BADGE_WORDS[state]}
    </span>
  );
  return detail ? <Popover content={detail}>{body}</Popover> : body;
}

export function Lozenge({
  severity,
  certain = true,
}: {
  severity: string;
  certain?: boolean;
}) {
  const known =
    severity === "error" || severity === "warning" || severity === "note";
  return (
    <span
      className={`${styles.lozenge} ${known ? styles[`lozenge_${severity}`] : ""}`}
    >
      {severity}
      {!certain && (
        <span title="the replay could not be sure the tip touched the liquid">
          {" "}
          · uncertain
        </span>
      )}
    </span>
  );
}

export function Chip({
  on = false,
  count,
  onClick,
  title,
  children,
  disabled,
}: {
  on?: boolean;
  count?: number | string | null;
  onClick?: () => void;
  title?: string;
  children: React.ReactNode;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      className={`${styles.chip} ${on ? styles.chipOn : ""}`}
      onClick={onClick}
      title={title}
      aria-pressed={onClick ? on : undefined}
      disabled={disabled}
    >
      {children}
      {count != null && <span className={styles.chipCount}>{count}</span>}
    </button>
  );
}

/* A static word in a pill: "stopped: token budget", "reads the replay only", "proposed by
   example", "adopted". Never a count, never pressable. */
export function Tag({
  tone = "muted",
  title,
  children,
}: {
  tone?: "muted" | "warning" | "verified" | "note";
  title?: string;
  children: React.ReactNode;
}) {
  return (
    <span className={`${styles.tag} ${styles[`tag_${tone}`]}`} title={title}>
      {children}
    </span>
  );
}

export type RowTone = "ok" | "bad" | "warn" | "muted" | "skip";

/* label · value, one line. `tone` colours the value and the icon: ok ✓, bad ✕, warn !, muted ·,
   skip – ("not checked" is its own state, never a tick). `to` makes the row a link. */
export function Row({
  label,
  value,
  tone = "muted",
  onClick,
  to,
  icon = true,
  title,
  children,
}: {
  label: React.ReactNode;
  value?: React.ReactNode;
  tone?: RowTone;
  onClick?: () => void;
  to?: string;
  icon?: boolean;
  title?: string;
  children?: React.ReactNode;
}) {
  const glyph =
    tone === "ok"
      ? "✓"
      : tone === "bad"
        ? "✕"
        : tone === "warn"
          ? "!"
          : tone === "skip"
            ? "–"
            : "·";
  const word =
    tone === "ok"
      ? "passed"
      : tone === "bad"
        ? "failed"
        : tone === "warn"
          ? "a warning"
          : tone === "skip"
            ? "not checked"
            : "";
  const inner = (
    <>
      {icon && (
        <span
          className={`${styles.rowIcon} ${styles[`tone_${tone}`]}`}
          aria-hidden="true"
        >
          {glyph}
        </span>
      )}
      {icon && word && <span className="sr-only">{word}: </span>}
      <span className={styles.rowLabel}>{label}</span>
      {value != null && (
        <span className={`${styles.rowValue} ${styles[`tone_${tone}`]}`}>
          {value}
        </span>
      )}
      {children}
    </>
  );
  return to ? (
    <Link to={to} className={`${styles.row} ${styles.rowButton}`} title={title}>
      {inner}
    </Link>
  ) : onClick ? (
    <button
      type="button"
      className={`${styles.row} ${styles.rowButton}`}
      onClick={onClick}
      title={title}
    >
      {inner}
    </button>
  ) : (
    <div className={styles.row} title={title}>
      {inner}
    </div>
  );
}

export function Fold({
  summary,
  hint,
  open,
  onToggle,
  children,
}: {
  summary: React.ReactNode;
  hint?: React.ReactNode;
  open?: boolean;
  onToggle?: (open: boolean) => void;
  children: React.ReactNode;
}) {
  return (
    <details
      className={styles.fold}
      open={open}
      onToggle={(e) => onToggle?.((e.target as HTMLDetailsElement).open)}
    >
      <summary className={styles.foldSummary}>
        <span className={styles.foldChevron} aria-hidden="true">
          ›
        </span>
        <span className={styles.foldWords}>{summary}</span>
        {hint && <span className={styles.foldHint}>{hint}</span>}
      </summary>
      <div className={styles.foldBody}>{children}</div>
    </details>
  );
}

export interface TabItem<K extends string> {
  key: K;
  label: React.ReactNode;
  count?: number | string | null;
  disabled?: boolean;
  title?: string;
}

export function Tabs<K extends string>({
  items,
  value,
  onChange,
  label,
  right,
}: {
  items: TabItem<K>[];
  value: K;
  onChange: (k: K) => void;
  label: string;
  right?: React.ReactNode;
}) {
  // one tab stop, the selected tab; the arrows move between the tabs that can be chosen
  const onKey = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (
      e.key !== "ArrowRight" &&
      e.key !== "ArrowLeft" &&
      e.key !== "Home" &&
      e.key !== "End"
    )
      return;
    const open = items.filter((t) => !t.disabled);
    const at = Math.max(
      0,
      open.findIndex((t) => t.key === value),
    );
    const next =
      e.key === "Home"
        ? open[0]
        : e.key === "End"
          ? open[open.length - 1]
          : open[
              (at + (e.key === "ArrowRight" ? 1 : open.length - 1)) %
                open.length
            ];
    if (next && next.key !== value) {
      onChange(next.key);
      (
        e.currentTarget.querySelector(
          `[data-tab="${next.key}"]`,
        ) as HTMLElement | null
      )?.focus();
    }
    e.preventDefault();
  };
  return (
    <div className={styles.tabBar}>
      <div
        className={styles.tabs}
        role="tablist"
        aria-label={label}
        onKeyDown={onKey}
      >
        {items.map((t) => (
          <button
            key={t.key}
            type="button"
            role="tab"
            data-tab={t.key}
            aria-selected={value === t.key}
            tabIndex={value === t.key ? 0 : -1}
            className={`${styles.tab} ${value === t.key ? styles.tabOn : ""}`}
            onClick={() => !t.disabled && onChange(t.key)}
            disabled={t.disabled}
            title={t.title}
          >
            {t.label}
            {t.count != null && (
              <span className={styles.tabCount}>{t.count}</span>
            )}
          </button>
        ))}
      </div>
      {right && <div className={styles.tabRight}>{right}</div>}
    </div>
  );
}

/* A segmented control: like Tabs, smaller, for a view choice (2D | 3D). */
export function Segments<K extends string>({
  items,
  value,
  onChange,
  label,
}: {
  items: { key: K; label: string; disabled?: boolean }[];
  value: K;
  onChange: (k: K) => void;
  label: string;
}) {
  return (
    <div className={styles.segments} role="radiogroup" aria-label={label}>
      {items.map((s) => (
        <button
          key={s.key}
          type="button"
          role="radio"
          aria-checked={value === s.key}
          className={value === s.key ? styles.segmentOn : undefined}
          onClick={() => onChange(s.key)}
          disabled={s.disabled}
        >
          {s.label}
        </button>
      ))}
    </div>
  );
}

/* Hover or focus shows `content`; tap toggles it; it closes when the pointer leaves. */
export function Popover({
  content,
  children,
}: {
  content: React.ReactNode;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const ref = useRef<HTMLSpanElement | null>(null);
  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node))
        setOpen(false);
    };
    document.addEventListener("click", onDoc);
    return () => document.removeEventListener("click", onDoc);
  }, [open]);
  return (
    <span
      ref={ref}
      className={styles.popoverHost}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <button
        type="button"
        className={styles.popoverTrigger}
        onClick={() => setOpen((v) => !v)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        aria-describedby={open ? id : undefined}
        aria-expanded={open}
      >
        {children}
      </button>
      {open && (
        <span role="tooltip" id={id} className={styles.popover}>
          {content}
        </span>
      )}
    </span>
  );
}

export function Stage({
  children,
  caption,
}: {
  children: React.ReactNode;
  caption?: React.ReactNode;
}) {
  return (
    <section className={styles.stage} aria-label="The stage">
      <div className={styles.stageBody}>{children}</div>
      {caption && <p className={styles.stageCaption}>{caption}</p>}
    </section>
  );
}

export function Rail({ children }: { children: React.ReactNode }) {
  return (
    <aside className={styles.rail} aria-label="The checks and the findings">
      {children}
    </aside>
  );
}

export function RailSection({
  title,
  count,
  children,
}: {
  title: string;
  count?: number | string | null;
  children: React.ReactNode;
}) {
  return (
    <section className={styles.railSection}>
      <h2 className={styles.railTitle}>
        {title}
        {count != null && <span className={styles.railCount}> · {count}</span>}
      </h2>
      {children}
    </section>
  );
}

/* A grey block in the shape of what is coming, for the first load only. */
export function Bone({
  height,
  width,
}: {
  height: number | string;
  width?: number | string;
}) {
  return (
    <span
      className={styles.bone}
      style={{ height, width } as React.CSSProperties}
      aria-hidden="true"
    />
  );
}

/* Write · Plan · Run: only on a new run's own flow. `at` is the step under way; the ones
   before it are done; on a phone the same three, closer together. */
export function Stepper({
  at,
  done = false,
}: {
  at: 1 | 2 | 3;
  done?: boolean;
}) {
  const steps = ["Write", "Plan", "Run"];
  return (
    <ol className={styles.stepper} aria-label="The three steps">
      {steps.map((label, i) => {
        const n = (i + 1) as 1 | 2 | 3;
        const state =
          n < at || (n === at && done) ? "done" : n === at ? "on" : "todo";
        return (
          <li
            key={label}
            className={`${styles.step} ${styles[`step_${state}`]}`}
            aria-current={state === "on" ? "step" : undefined}
          >
            <span className={styles.stepN} aria-hidden="true">
              {state === "done" ? "✓" : n}
            </span>
            <span className={styles.stepLabel}>{label}</span>
          </li>
        );
      })}
    </ol>
  );
}

/* What a rule rests on: one source per line, the publisher or author first and the title after,
   each its own link, so two sources never run together. "Lab Manager: minimizing …" is split
   at its first colon; a name without one is shown whole. */
export function SourceList({
  sources,
  label = "Sources",
}: {
  sources: { name: string; url?: string | null }[];
  label?: string;
}) {
  if (sources.length === 0) return null;
  return (
    <div className={styles.sources}>
      <div className={styles.sourcesLabel}>{label}</div>
      <ul className={styles.sourceList}>
        {sources.map((s, i) => {
          const cut = s.name.indexOf(": ");
          const who = cut > 0 ? s.name.slice(0, cut) : null;
          const what = cut > 0 ? s.name.slice(cut + 2) : s.name;
          const body = (
            <>
              <svg
                className={styles.sourceIcon}
                width="13"
                height="13"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="M14 3h7v7M21 3l-9 9M19 14v5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h5" />
              </svg>
              <span>
                {who && <span className={styles.sourceWho}>{who}</span>}
                <span className={styles.sourceWhat}>{what}</span>
              </span>
            </>
          );
          return (
            <li key={i}>
              {s.url ? (
                <a
                  className={styles.source}
                  href={s.url}
                  target="_blank"
                  rel="noreferrer"
                >
                  {body}
                </a>
              ) : (
                <span className={styles.source}>{body}</span>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

/* A way on to another page: a bordered row with a title, one line of what is there, and a
   chevron; in place of a bare "The rulebook →". */
export function LinkCard({
  to,
  title,
  words,
  icon,
}: {
  to: string;
  title: string;
  words: string;
  icon?: React.ReactNode;
}) {
  return (
    <Link to={to} className={styles.linkCard}>
      {icon && <span className={styles.linkCardIcon}>{icon}</span>}
      <span className={styles.linkCardText}>
        <span className={styles.linkCardTitle}>{title}</span>
        <span className={styles.linkCardWords}>{words}</span>
      </span>
      <svg
        className={styles.linkCardChevron}
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <path d="M9 6l6 6-6 6" />
      </svg>
    </Link>
  );
}
