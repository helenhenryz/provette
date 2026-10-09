import { useCallback, useEffect, useRef, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import {
  api,
  judge,
  REPOSITORY,
  UNLOCK_EVENT,
  type UnlockRequest,
} from "../lib/api";
import { useFetch } from "../lib/useFetch";
import { applyTheme, readTheme, type Theme } from "../lib/theme";
import { History } from "./History";
import { JudgeDialog } from "./JudgeDialog";
import { Settings } from "./Settings";
import styles from "./Shell.module.css";

/* The one sentence about what Provette is not; it is said once, on About, and inside the
   Not-checked fold where it answers a question. The footer carries links and the version. */
export const DISCLAIMER =
  "Provette checks the logic of a protocol, not the physics.";

const PLACES = [
  { to: "/examples", label: "Examples", icon: "examples" },
  { to: "/rules", label: "Rules", icon: "rules" },
  { to: "/methods", label: "Methods", icon: "methods" },
  { to: "/about", label: "About", icon: "about" },
] as const;

/* The frame around every page, in the pattern people already know from chat apps: one sidebar
   holds everything (a new run first, then checking a protocol and the reading pages, then this
   deployment's history, then the tools at its foot); the page itself has no bar on a desktop.
   On a phone the sidebar is a drawer, and a slim bar carries the menu, the name and a new run. */
export function Shell() {
  const [theme, setTheme] = useState<Theme>(() => readTheme());
  useEffect(() => applyTheme(theme), [theme]);
  const health = useFetch(api.health, "health");
  const [drawer, setDrawer] = useState(false);
  const [settings, setSettings] = useState(false);
  const { pathname } = useLocation();
  useEffect(() => setDrawer(false), [pathname]);
  const onCheck = pathname === "/check" || pathname.startsWith("/check/");
  return (
    <div className={`${styles.shell} ${drawer ? styles.drawerOpen : ""}`}>
      <aside className={styles.sidebar} aria-label="Provette">
        <div className={styles.sideTop}>
          <NavLink to="/" className={styles.brand} end>
            <Mark />
            <span>Provette</span>
          </NavLink>
          <button
            type="button"
            className={styles.close}
            onClick={() => setDrawer(false)}
            aria-label="Close the menu"
          >
            <Glyph name="close" />
          </button>
        </div>
        <nav className={styles.actions} aria-label="Main">
          <NavLink
            to="/"
            end
            className={({ isActive }) =>
              `${styles.action} ${styles.newRun} ${isActive ? styles.actionOn : ""}`
            }
          >
            <Glyph name="plus" />
            New run
          </NavLink>
          <NavLink
            to="/check?new"
            className={() =>
              `${styles.action} ${onCheck ? styles.actionOn : ""}`
            }
          >
            <Glyph name="check" />
            Check a protocol
          </NavLink>
          {PLACES.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `${styles.action} ${isActive ? styles.actionOn : ""}`
              }
            >
              <Glyph name={item.icon} />
              {item.label}
            </NavLink>
          ))}
          {REPOSITORY && (
            <a
              href={REPOSITORY}
              target="_blank"
              rel="noreferrer"
              className={styles.action}
            >
              <Glyph name="code" />
              Code
            </a>
          )}
        </nav>
        <div className={styles.historyWrap}>
          <History onNavigate={() => setDrawer(false)} />
        </div>
        <div className={styles.foot}>
          <span className={styles.version}>
            {health.data
              ? `v${health.data.provette} · opentrons ${health.data.opentrons}`
              : ""}
          </span>
          <div className={styles.tools}>
            <JudgeKey />
            <button
              type="button"
              className={styles.theme}
              onClick={() => setSettings(true)}
              title="Settings"
              aria-label="Settings"
            >
              <svg
                width="15"
                height="15"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.9"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <circle cx="12" cy="12" r="3" />
                <path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z" />
              </svg>
            </button>
          </div>
        </div>
      </aside>
      {settings && (
        <Settings
          onClose={() => setSettings(false)}
          theme={theme}
          onTheme={setTheme}
        />
      )}
      <button
        type="button"
        className={styles.scrim}
        aria-label="Close the menu"
        onClick={() => setDrawer(false)}
        tabIndex={drawer ? 0 : -1}
      />

      <div className={styles.column}>
        <header className={styles.phoneBar}>
          <button
            type="button"
            className={styles.iconButton}
            onClick={() => setDrawer(true)}
            aria-label="Open the menu"
          >
            <Glyph name="panel" />
          </button>
          <NavLink to="/" className={styles.brand} end>
            <Mark />
            <span>Provette</span>
          </NavLink>
          <NavLink
            to="/"
            end
            className={styles.iconButton}
            aria-label="New run"
          >
            <Glyph name="plus" />
          </NavLink>
        </header>
        <main className={styles.main}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}

type GlyphName =
  | "plus"
  | "check"
  | "examples"
  | "rules"
  | "methods"
  | "about"
  | "code"
  | "close"
  | "panel";

/* The sidebar's icons: 16 px strokes in the text's colour. */
function Glyph({ name }: { name: GlyphName }) {
  const paths: Record<GlyphName, React.ReactNode> = {
    plus: <path d="M12 5v14M5 12h14" />,
    check: (
      <>
        <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
        <path d="M14 3v5h5M9 14l2 2 4-4" />
      </>
    ),
    examples: (
      <>
        <rect x="3" y="3" width="7" height="7" rx="1.5" />
        <rect x="14" y="3" width="7" height="7" rx="1.5" />
        <rect x="3" y="14" width="7" height="7" rx="1.5" />
        <rect x="14" y="14" width="7" height="7" rx="1.5" />
      </>
    ),
    rules: <path d="M9 6h11M9 12h11M9 18h11M4.5 6h.01M4.5 12h.01M4.5 18h.01" />,
    methods: <path d="M4 20V10M10 20V4M16 20v-7M22 20H2" />,
    about: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 11v5M12 8h.01" />
      </>
    ),
    code: <path d="M8 7l-5 5 5 5M16 7l5 5-5 5" />,
    close: <path d="M6 6l12 12M18 6L6 18" />,
    panel: (
      <>
        <rect x="3" y="4" width="18" height="16" rx="2.5" />
        <path d="M9 4v16" />
      </>
    ),
  };
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {paths[name]}
    </svg>
  );
}

/* The one judge password, kept in one place: a key in the header. It unlocks the live run and
   every write to the rulebook (a word, a rule, a failed-run record); the gallery and the checker
   need nothing. A form that needs it opens the dialog with `judge.requestUnlock()`. */
function JudgeKey() {
  const [open, setOpen] = useState(false);
  const [saved, setSaved] = useState(Boolean(judge.get()));
  // the actions waiting on the dialog (withJudge): told on close whether the tab is unlocked
  const waiting = useRef<((unlocked: boolean) => void)[]>([]);
  useEffect(() => {
    const onUnlock = (e: Event) => {
      const ask = (e as CustomEvent<UnlockRequest | undefined>).detail;
      if (ask) waiting.current.push(ask.resolve);
      setOpen(true);
    };
    window.addEventListener(UNLOCK_EVENT, onUnlock);
    return () => window.removeEventListener(UNLOCK_EVENT, onUnlock);
  }, []);
  const close = useCallback(() => {
    setOpen(false);
    const unlocked = Boolean(judge.get());
    for (const resolve of waiting.current.splice(0)) resolve(unlocked);
  }, []);
  return (
    <div className={styles.key}>
      <button
        type="button"
        className={`${styles.keyButton} ${saved ? styles.keySet : ""}`}
        onClick={() => setOpen(true)}
        aria-haspopup="dialog"
        aria-label={
          saved
            ? "Judge password set; click to change it"
            : "Unlock with the judge password"
        }
        title={saved ? "Judge password set" : "Unlock with the judge password"}
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
          <circle cx="7.5" cy="15.5" r="4.5" />
          <path d="M10.7 12.3 21 2M15 8l3 3M18 5l3 3" />
        </svg>
      </button>
      <JudgeDialog open={open} onClose={close} onChange={setSaved} />
    </div>
  );
}

function Mark() {
  return (
    <svg width="20" height="20" viewBox="0 0 32 32" aria-hidden="true">
      <rect width="32" height="32" rx="7" fill="var(--verified)" />
      <circle cx="11" cy="11" r="3.2" fill="var(--on-accent)" />
      <circle cx="21" cy="11" r="3.2" fill="var(--on-accent)" opacity=".55" />
      <circle cx="11" cy="21" r="3.2" fill="var(--on-accent)" opacity=".55" />
      <circle cx="21" cy="21" r="3.2" fill="var(--on-accent)" />
    </svg>
  );
}
