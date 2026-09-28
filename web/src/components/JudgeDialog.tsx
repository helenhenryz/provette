import { type FormEvent, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { judge } from "../lib/api";
import styles from "./JudgeDialog.module.css";

/* The judge password, asked for over the page: a card in the middle on a desktop, a sheet from
   the bottom on a phone. The password is checked with the server before it is kept, so a wrong
   one is said at once, not on the next write. Escape, the backdrop or Cancel close it; Tab
   stays inside it; the page under it does not scroll. Kept for the tab's session only. It is
   drawn at the root of the page (a portal), so no box of the page can hold it in. */
export function JudgeDialog({
  open,
  onClose,
  onChange,
}: {
  open: boolean;
  onClose: () => void;
  onChange: (unlocked: boolean) => void;
}) {
  const [value, setValue] = useState("");
  const [show, setShow] = useState(false);
  const [state, setState] = useState<
    "idle" | "checking" | "wrong" | "none" | "error"
  >("idle");
  const unlocked = Boolean(judge.get());
  const card = useRef<HTMLFormElement>(null);
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!open) return;
    setValue("");
    setShow(false);
    setState("idle");
    const before = document.activeElement as HTMLElement | null;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const t = window.setTimeout(() => input.current?.focus(), 30);
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      } else if (e.key === "Tab" && card.current) {
        const all = card.current.querySelectorAll<HTMLElement>(
          "input, button:not([disabled])",
        );
        if (!all.length) return;
        const first = all[0];
        const last = all[all.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", onKey);
    return () => {
      window.clearTimeout(t);
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = overflow;
      before?.focus?.();
    };
  }, [open, onClose]);

  if (!open) return null;

  async function submit(e: FormEvent) {
    e.preventDefault();
    const v = value.trim();
    if (!v) return;
    setState("checking");
    try {
      const answer = await judge.check(v);
      if (answer === "ok") {
        judge.set(v);
        onChange(true);
        onClose();
      } else setState(answer);
    } catch {
      setState("error");
    }
  }

  function lock() {
    judge.set("");
    onChange(false);
    onClose();
  }

  const message =
    state === "wrong"
      ? "That password isn't right."
      : state === "none"
        ? "This deployment has no judge password set."
        : state === "error"
          ? "Couldn't reach the server. Try again."
          : null;

  // at the root of the page: the sidebar is a drawer that moves on a phone, and an overlay inside
  // a moved box would be held inside it
  return createPortal(
    <div
      className={styles.backdrop}
      onMouseDown={(e) => e.target === e.currentTarget && onClose()}
    >
      <form
        ref={card}
        className={styles.card}
        role="dialog"
        aria-modal="true"
        aria-labelledby="judge-title"
        aria-describedby="judge-words"
        onSubmit={submit}
      >
        <div className={styles.icon} aria-hidden="true">
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <circle cx="7.5" cy="15.5" r="4.5" />
            <path d="M10.7 12.3 21 2M15 8l3 3M18 5l3 3" />
          </svg>
        </div>
        <h2 id="judge-title" className={styles.title}>
          {unlocked ? "Unlocked" : "Enter the judge password"}
        </h2>
        <p id="judge-words" className={styles.words}>
          {unlocked
            ? "New runs, the rule form and the settings are open in this tab. Enter a new password to change it."
            : "It opens new runs, the rule form and the settings. It's in the submission notes."}
        </p>
        <div className={`${styles.field} ${message ? styles.fieldBad : ""}`}>
          <input
            ref={input}
            type={show ? "text" : "password"}
            value={value}
            onChange={(e) => {
              setValue(e.target.value);
              if (state !== "checking") setState("idle");
            }}
            placeholder="Password"
            aria-label="Judge password"
            aria-invalid={state === "wrong"}
            autoComplete="current-password"
            autoCapitalize="none"
            autoCorrect="off"
            spellCheck={false}
            enterKeyHint="go"
          />
          <button
            type="button"
            className={styles.reveal}
            onClick={() => {
              setShow((s) => !s);
              input.current?.focus();
            }}
            aria-label={show ? "Hide the password" : "Show the password"}
            aria-pressed={show}
          >
            {show ? "Hide" : "Show"}
          </button>
        </div>
        <p className={styles.message} role="alert">
          {message}
        </p>
        <div className={styles.actions}>
          {unlocked ? (
            <button type="button" className={styles.secondary} onClick={lock}>
              Lock
            </button>
          ) : (
            <button
              type="button"
              className={styles.secondary}
              onClick={onClose}
            >
              Cancel
            </button>
          )}
          <button
            type="submit"
            className={styles.primary}
            disabled={!value.trim() || state === "checking"}
          >
            {state === "checking" ? "Checking…" : "Unlock"}
          </button>
        </div>
      </form>
    </div>,
    document.body,
  );
}
