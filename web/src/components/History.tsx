import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import {
  ApiError,
  checkMemory,
  checks,
  live,
  type CheckListRow,
  type LiveRunCard,
  type PlanListRow,
} from "../lib/api";
import styles from "./History.module.css";
import { withJudge } from "../lib/withJudge";

/* The sidebar's history: everything a person made on this deployment, newest first, one line
   each (runs, plans that did not become a run, checks), in one flat list. It is read from
   GET /api/runs, /api/plans and /api/checks, never from the browser's storage, and read again
   when the page changes and every few seconds while something is still running.

   Each line has a "⋯" menu, as a chat app's: Pin (kept in this browser only, a per-viewer
   convenience) and Delete, which asks in a dialog and then calls DELETE on the same address
   behind the judge key; a run still going is refused until it is stopped. */

const PINS = "provette.pinned";
function readPins(): string[] {
  try {
    const v = JSON.parse(localStorage.getItem(PINS) ?? "[]") as unknown;
    return Array.isArray(v)
      ? v.filter((x): x is string => typeof x === "string")
      : [];
  } catch {
    return [];
  }
}
function writePins(keys: string[]): void {
  try {
    localStorage.setItem(PINS, JSON.stringify(keys));
  } catch {
    /* private window: pins last for this page only */
  }
}

type Dot = "ok" | "bad" | "running" | "muted";
interface Item {
  id: string;
  key: string;
  to: string;
  title: string;
  kind: "run" | "plan" | "check";
  dot: Dot;
  state: string;
  created: number;
}

function firstSentence(text: string): string {
  return text.split(/[.;](?:\s|$)/)[0].trim();
}

function runItem(r: LiveRunCard): Item {
  const dot: Dot =
    r.state === "running"
      ? "running"
      : r.state === "failed"
        ? "bad"
        : r.state === "stopped"
          ? "muted"
          : r.verified
            ? "ok"
            : "bad";
  const state =
    r.state === "running"
      ? "running"
      : r.state === "failed"
        ? "failed"
        : r.state === "stopped"
          ? "stopped"
          : r.verified
            ? "verified"
            : "not verified";
  return {
    id: r.run_id,
    key: `r${r.run_id}`,
    to: `/runs/${r.run_id}`,
    title: firstSentence(r.request),
    kind: "run",
    dot,
    state,
    created: r.created ?? 0,
  };
}

function planItem(p: PlanListRow): Item {
  const dot: Dot =
    p.outcome === "planning"
      ? "running"
      : p.outcome === "proposed" ||
          p.outcome === "stopped" ||
          p.outcome === "not a request"
        ? "muted"
        : "bad";
  return {
    id: p.id,
    key: `p${p.id}`,
    to: `/plan/${p.id}`,
    title: firstSentence(p.request),
    kind: "plan",
    dot,
    state: p.outcome === "proposed" ? "plan to approve" : p.outcome,
    created: p.created ?? 0,
  };
}

function checkItem(c: CheckListRow): Item {
  const dot: Dot =
    c.simulator === "rejected" ? "bad" : c.findings > 0 ? "bad" : "ok";
  const state =
    c.simulator === "rejected"
      ? "rejected"
      : c.findings > 0
        ? `${c.findings} finding${c.findings === 1 ? "" : "s"}`
        : "no findings";
  return {
    id: c.id,
    key: `c${c.id}`,
    to: `/check/${c.id}`,
    title: c.name,
    kind: "check",
    dot,
    state,
    created: c.created,
  };
}

/* A plan that became a run is shown as the run: a run of the same request started after it. */
function becameRun(p: PlanListRow, runs: LiveRunCard[]): boolean {
  return runs.some(
    (r) => r.request === p.request && (r.created ?? 0) >= (p.created ?? 0),
  );
}

export function History({ onNavigate }: { onNavigate?: () => void }) {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const [tick, setTick] = useState(0);
  const [menu, setMenu] = useState<{
    item: Item;
    x: number;
    y: number;
    up: boolean;
  } | null>(null);
  const [deleting, setDeleting] = useState<Item | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [busyDelete, setBusyDelete] = useState(false);
  const [pins, setPins] = useState<string[]>(readPins);

  function togglePin(item: Item) {
    const next = pins.includes(item.key)
      ? pins.filter((k) => k !== item.key)
      : [item.key, ...pins];
    setPins(next);
    writePins(next);
  }

  async function remove(item: Item) {
    setBusyDelete(true);
    try {
      // with no password, the password dialog opens and the delete dialog stays to confirm again
      const done = await withJudge(() =>
        live.remove(item.kind, item.id).then(() => true),
      );
      if (!done) return;
      if (item.kind === "run" && data) {
        // The plans shown as this run go with it; left alone, they would come back as lines of their own.
        const run = data.runs.find((r) => r.run_id === item.id);
        const others = data.runs.filter((r) => r.run_id !== item.id);
        const behind = run
          ? data.plans.filter(
              (p) => becameRun(p, [run]) && !becameRun(p, others),
            )
          : [];
        await Promise.all(
          behind.map((p) => live.remove("plan", p.id).catch(() => undefined)),
        );
      }
      if (item.kind === "check" && checkMemory.last.get() === item.id)
        checkMemory.last.forget();
      if (pins.includes(item.key)) {
        const next = pins.filter((k) => k !== item.key);
        setPins(next);
        writePins(next);
      }
      setDeleting(null);
      setProblem(null);
      setTick((n) => n + 1);
      if (pathname === item.to) navigate("/");
    } catch (e) {
      setProblem(
        e instanceof ApiError && e.status === 409
          ? "This run is still going. Stop it first, then delete it."
          : "It could not be deleted. Try again in a moment.",
      );
    } finally {
      setBusyDelete(false);
    }
  }
  const [data, setData] = useState<{
    runs: LiveRunCard[];
    plans: PlanListRow[];
    checks: CheckListRow[];
  } | null>(null);

  useEffect(() => {
    let alive = true;
    Promise.all([
      live.runs().catch(() => ({ runs: [] })),
      live.plans().catch(() => ({ plans: [] })),
      checks.list().catch(() => ({ checks: [] })),
    ]).then(([r, p, c]) => {
      if (alive) setData({ runs: r.runs, plans: p.plans, checks: c.checks });
    });
    return () => {
      alive = false;
    };
  }, [pathname, tick]);

  const items = useMemo(() => {
    if (!data) return [];
    const runs = data.runs.map(runItem);
    const plans = data.plans
      .filter((p) => !becameRun(p, data.runs))
      .map(planItem);
    return [...runs, ...plans, ...data.checks.map(checkItem)].sort(
      (a, b) => b.created - a.created,
    );
  }, [data]);

  const busy = items.some((i) => i.dot === "running");
  useEffect(() => {
    if (!busy) return;
    const t = window.setInterval(() => setTick((n) => n + 1), 5000);
    return () => window.clearInterval(t);
  }, [busy]);

  // Pinned first (in the order pinned), then everything else newest first
  const groups = useMemo(() => {
    const pinned = pins
      .map((k) => items.find((i) => i.key === k))
      .filter((i): i is Item => !!i);
    const rest = items.filter((i) => !pins.includes(i.key));
    return [
      ...(pinned.length ? [{ label: "Pinned", items: pinned }] : []),
      { label: "History", items: rest },
    ];
  }, [items, pins]);

  function openMenu(item: Item, button: HTMLButtonElement) {
    const r = button.getBoundingClientRect();
    const up = r.bottom + 110 > window.innerHeight; // no room below: open upwards
    setMenu({ item, x: r.right, y: up ? r.top - 4 : r.bottom + 4, up });
  }

  return (
    <nav className={styles.history} aria-label="Your history">
      {groups.map((g) => (
        <section key={g.label} className={styles.group}>
          <div className={styles.groupLabel}>{g.label}</div>
          {g.label === "History" && data && items.length === 0 && (
            <p className={styles.empty}>Your runs and checks appear here.</p>
          )}
          <ul className={styles.list}>
            {g.items.map((i) => (
              <li
                key={i.key}
                className={`${styles.row} ${menu?.item.key === i.key ? styles.rowOpen : ""}`}
              >
                <NavLink
                  to={i.to}
                  onClick={onNavigate}
                  className={({ isActive }) =>
                    `${styles.item} ${isActive || pathname === i.to ? styles.itemOn : ""}`
                  }
                  title={`${i.title} · ${i.kind} · ${i.state}`}
                >
                  <Marker kind={i.kind} dot={i.dot} />
                  <span className={styles.title}>{i.title}</span>
                  {i.kind !== "run" && (
                    <span className="sr-only"> · {i.kind}</span>
                  )}
                </NavLink>
                <button
                  type="button"
                  className={styles.more}
                  onClick={(e) =>
                    menu?.item.key === i.key
                      ? setMenu(null)
                      : openMenu(i, e.currentTarget)
                  }
                  aria-label={`More for ${i.title}`}
                  aria-haspopup="menu"
                  aria-expanded={menu?.item.key === i.key}
                >
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="currentColor"
                    aria-hidden="true"
                  >
                    <circle cx="12" cy="5" r="1.8" />
                    <circle cx="12" cy="12" r="1.8" />
                    <circle cx="12" cy="19" r="1.8" />
                  </svg>
                </button>
              </li>
            ))}
          </ul>
        </section>
      ))}
      {menu && (
        <RowMenu
          at={menu}
          pinned={pins.includes(menu.item.key)}
          onClose={() => setMenu(null)}
          onPin={() => {
            togglePin(menu.item);
            setMenu(null);
          }}
          onDelete={() => {
            setProblem(null);
            setDeleting(menu.item);
            setMenu(null);
          }}
        />
      )}
      {deleting && (
        <ConfirmDelete
          item={deleting}
          problem={problem}
          busy={busyDelete}
          onCancel={() => {
            setDeleting(null);
            setProblem(null);
          }}
          onDelete={() => void remove(deleting)}
        />
      )}
    </nav>
  );
}

const pinIcon = <path d="M12 17v5M9 3h6l-1 5 3 3v2H7v-2l3-3-1-5z" />;
const trashIcon = (
  <path d="M4 7h16M10 11v6M14 11v6M6 7l1 12a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-12M9 7V4h6v3" />
);
function Icon({ children }: { children: ReactNode }) {
  return (
    <svg
      width="15"
      height="15"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {children}
    </svg>
  );
}

/* The row's menu, fixed to the viewport (the sidebar scrolls and, on a phone, slides), closed
   by a click elsewhere, Escape, or a scroll. */
function RowMenu({
  at,
  pinned,
  onClose,
  onPin,
  onDelete,
}: {
  at: { x: number; y: number; up: boolean };
  pinned: boolean;
  onClose: () => void;
  onPin: () => void;
  onDelete: () => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    ref.current?.querySelector("button")?.focus();
    const away = (e: Event) => {
      if (
        ref.current &&
        !ref.current.contains(e.target as Node) &&
        !(e.target as HTMLElement).closest?.("[aria-haspopup='menu']")
      )
        onClose();
    };
    const key = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    const scroll = (e: Event) =>
      !ref.current?.contains(e.target as Node) && onClose();
    document.addEventListener("mousedown", away);
    document.addEventListener("keydown", key);
    window.addEventListener("scroll", scroll, true);
    window.addEventListener("resize", onClose);
    return () => {
      document.removeEventListener("mousedown", away);
      document.removeEventListener("keydown", key);
      window.removeEventListener("scroll", scroll, true);
      window.removeEventListener("resize", onClose);
    };
  }, [onClose]);
  const style = {
    left: Math.max(8, at.x - 180),
    ...(at.up ? { bottom: window.innerHeight - at.y } : { top: at.y }),
  };
  return createPortal(
    <div ref={ref} className={styles.menu} role="menu" style={style}>
      <button
        type="button"
        role="menuitem"
        className={styles.menuItem}
        onClick={onPin}
      >
        <Icon>{pinIcon}</Icon>
        {pinned ? "Unpin" : "Pin"}
      </button>
      <div className={styles.menuRule} />
      <button
        type="button"
        role="menuitem"
        className={`${styles.menuItem} ${styles.menuDanger}`}
        onClick={onDelete}
      >
        <Icon>{trashIcon}</Icon>
        Delete
      </button>
    </div>,
    document.body,
  );
}

function ConfirmDelete({
  item,
  problem,
  busy,
  onCancel,
  onDelete,
}: {
  item: Item;
  problem: string | null;
  busy: boolean;
  onCancel: () => void;
  onDelete: () => void;
}) {
  const yes = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    yes.current?.focus();
    const key = (e: KeyboardEvent) => e.key === "Escape" && onCancel();
    document.addEventListener("keydown", key);
    return () => document.removeEventListener("keydown", key);
  }, [onCancel]);
  return createPortal(
    <div
      className={styles.scrim}
      onMouseDown={(e) => e.target === e.currentTarget && onCancel()}
    >
      <div
        className={styles.dialog}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="delete-title"
        aria-describedby="delete-words"
      >
        <h2 id="delete-title" className={styles.dialogTitle}>
          Delete this {item.kind}?
        </h2>
        <p id="delete-words" className={styles.dialogWords}>
          This {item.kind} will be permanently deleted. This can't be undone.
        </p>
        {problem && (
          <p className={styles.dialogProblem} role="alert">
            {problem}
          </p>
        )}
        <div className={styles.dialogButtons}>
          <button type="button" className="btn" onClick={onCancel}>
            Cancel
          </button>
          <button
            type="button"
            ref={yes}
            className={`btn ${styles.danger}`}
            onClick={onDelete}
            disabled={busy}
          >
            {busy ? "Deleting…" : "Delete"}
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}

/* The row's mark, in the state's colour: a run is a dot, a check a page with a tick, a plan a
   plate. One slot wide for all three, so the titles line up; the kind is said to a screen
   reader after the title, and in the row's hover. */
function Marker({ kind, dot }: { kind: Item["kind"]; dot: Dot }) {
  const tone = `${styles.mark} ${styles[`mark_${dot}`]}`;
  if (kind === "run")
    return (
      <span className={tone} aria-hidden="true">
        <span className={styles.dot} />
      </span>
    );
  return (
    <span className={tone} aria-hidden="true" data-kind={kind}>
      <svg
        width="14"
        height="14"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        {kind === "check" ? (
          <>
            <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
            <path d="M14 3v5h5" />
            <path d="m9 14 2 2 4-4" />
          </>
        ) : (
          <>
            <rect x="3" y="5" width="18" height="14" rx="2" />
            <circle cx="8.5" cy="10" r="1" fill="currentColor" />
            <circle cx="12" cy="10" r="1" fill="currentColor" />
            <circle cx="15.5" cy="10" r="1" fill="currentColor" />
            <circle cx="8.5" cy="14" r="1" fill="currentColor" />
            <circle cx="12" cy="14" r="1" fill="currentColor" />
          </>
        )}
      </svg>
    </span>
  );
}
