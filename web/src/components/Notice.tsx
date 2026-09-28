import styles from "./Notice.module.css";

/* A sentence in a box: what happened, what to do. `tone` picks the colour and the mark beside
   it (i, ✓, !, ✕); `onDismiss` adds a × that closes it. */
export function Notice({
  tone = "info",
  title,
  children,
  onDismiss,
}: {
  tone?: "info" | "ok" | "warning" | "error";
  title?: string;
  children: React.ReactNode;
  onDismiss?: () => void;
}) {
  return (
    <div
      className={`${styles.notice} ${styles[tone]}`}
      role={tone === "error" ? "alert" : undefined}
    >
      <span className={styles.mark} aria-hidden="true">
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <circle cx="12" cy="12" r="9.5" />
          {tone === "ok" ? (
            <path d="m8 12.5 2.8 2.8L16.5 9.5" />
          ) : tone === "error" ? (
            <path d="M9 9l6 6M15 9l-6 6" />
          ) : tone === "warning" ? (
            <path d="M12 7.5v5.5M12 16.5v.01" />
          ) : (
            <path d="M12 11v5.5M12 7.5v.01" />
          )}
        </svg>
      </span>
      <div className={styles.body}>
        {title && <div className={styles.title}>{title}</div>}
        <div className={styles.words}>{children}</div>
      </div>
      {onDismiss && (
        <button
          type="button"
          className={styles.dismiss}
          onClick={onDismiss}
          aria-label="Dismiss"
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            aria-hidden="true"
          >
            <path d="M6 6l12 12M18 6 6 18" />
          </svg>
        </button>
      )}
    </div>
  );
}

/* While a page loads: three grey blocks in the shape of a page (title, a plate, a list), so
   the page does not blank and jump. The sentence is read out; the blocks are decoration. */
export function Loading({ what = "Loading" }: { what?: string }) {
  return (
    <div className={styles.loading} aria-live="polite" aria-busy="true">
      <span className="sr-only">{what}…</span>
      <div className={styles.skeleton} aria-hidden="true">
        <div className={styles.boneTitle} />
        <div className={styles.boneLine} />
        <div className={styles.boneBlock} />
        <div className={styles.boneLine} />
        <div className={styles.boneLineShort} />
        <div className={styles.boneLine} />
      </div>
      <p className={styles.loadingWords} aria-hidden="true">
        {what}…
      </p>
    </div>
  );
}
