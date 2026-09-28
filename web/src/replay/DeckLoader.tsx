import styles from "./DeckLoader.module.css";

/* While the 3D deck loads: the OT-2's twelve slots, three across and four deep, lighting up
   in a wave, in the frame the deck will fill. */
export function DeckLoader({ overlay = false }: { overlay?: boolean }) {
  return (
    <div
      className={`${styles.loader} ${overlay ? styles.overlay : ""}`}
      role="status"
    >
      <div className={styles.deck} aria-hidden="true">
        {Array.from({ length: 12 }, (_, i) => (
          <span
            key={i}
            className={styles.slot}
            style={{
              animationDelay: `${(Math.floor(i / 3) + (i % 3)) * 90}ms`,
            }}
          />
        ))}
      </div>
      <span className="sr-only">Loading the 3D deck</span>
    </div>
  );
}
