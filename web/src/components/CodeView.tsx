import { useEffect, useRef } from "react";
import {
  CodeLine,
  codeLines,
  hangingIndent,
  type Language,
} from "../lib/highlight";
import styles from "./CodeView.module.css";

/* Source with line numbers, coloured (lib/highlight) and soft-wrapped; `marked` lines are
   highlighted and the first one is scrolled into view inside the box. */
export function CodeView({
  text,
  marked = [],
  maxHeight,
  language = "python",
}: {
  text: string;
  marked?: number[];
  maxHeight?: string;
  language?: Language;
}) {
  const lines = codeLines(text, language);
  const first = marked.length ? Math.min(...marked) : null;
  const ref = useRef<HTMLTableRowElement | null>(null);
  const box = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    // Scroll the code box, never the page: a reader who has not asked for the code stays put.
    const row = ref.current;
    const container = box.current;
    if (row && container)
      container.scrollTop = row.offsetTop - container.clientHeight / 2;
  }, [first]);
  const set = new Set(marked);
  return (
    <div
      ref={box}
      className={styles.code}
      style={maxHeight ? { maxHeight } : undefined}
    >
      <table className={styles.table}>
        <tbody>
          {lines.map((line, i) => {
            const n = i + 1;
            const hit = set.has(n);
            return (
              <tr
                key={n}
                className={hit ? styles.hit : undefined}
                ref={n === first ? ref : undefined}
              >
                <td className={styles.n}>{n}</td>
                <td className={styles.line} style={hangingIndent(line)}>
                  <CodeLine tokens={line} />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
