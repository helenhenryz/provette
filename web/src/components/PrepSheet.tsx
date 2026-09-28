import { useState } from "react";
import type { PrepJson, VerifyReport } from "../lib/api";
import { plural, ul } from "../lib/format";
import styles from "./PrepSheet.module.css";

/* What to put on the deck before pressing start, as a bench sheet: one block per slot, the
   wells under it, the tips, and under a fold, where every liquid ended up. From the prep
   sheet the replay computed (every checked protocol has one; a plate map is not needed) and
   the verify report's accounting when there was a map, so it cannot be invented. Printable. */
export function PrepSheet({
  prep,
  verify = null,
  accounting = true,
}: {
  prep: PrepJson;
  verify?: VerifyReport | null;
  accounting?: boolean;
}) {
  const lines = prep.lines;
  const tips = prep.tips;
  const totalTips = tips.reduce((n, t) => n + t.tips, 0);
  const anyFlag = lines.some((l) => l.flag || l.already_in_plate);
  const slots = new Map<string, { labware: string; rows: typeof lines }>();
  for (const line of lines) {
    const key = `${line.slot}|${line.labware}`;
    const group = slots.get(key) ?? { labware: line.labware, rows: [] };
    group.rows.push(line);
    slots.set(key, group);
  }
  const [showAccounting, setShowAccounting] = useState(false);
  return (
    <div className={styles.prep} id="prep-sheet">
      <div className={styles.toolbar}>
        <span className="muted small">
          {plural(lines.length, "source well")} in{" "}
          {slots.size === 1 ? "one labware" : `${slots.size} pieces of labware`}{" "}
          · {plural(totalTips, "tip")}
        </span>
        <button
          type="button"
          className={styles.print}
          onClick={() => window.print()}
        >
          Print
        </button>
      </div>
      <table className={styles.table} aria-label="What to load">
        <thead>
          <tr>
            <th>Well</th>
            <th>Liquid</th>
            <th className="num">Load at least</th>
            <th className="num">Declared</th>
            {anyFlag && <th>Note</th>}
          </tr>
        </thead>
        {[...slots.entries()].map(([key, group]) => (
          <tbody key={key}>
            <tr className={styles.slotRow}>
              <th colSpan={anyFlag ? 5 : 4}>
                Slot {key.split("|")[0]} · {group.labware}
              </th>
            </tr>
            {group.rows.map((line, i) => (
              <tr key={i} className={line.flag ? styles.flagged : undefined}>
                <td className="mono">{line.well}</td>
                <td>{line.liquid}</td>
                <td className="num">{ul(line.needed_ul)}</td>
                <td className="num">
                  {line.declared_ul == null ? "—" : ul(line.declared_ul)}
                </td>
                {anyFlag && (
                  <td>
                    {line.flag ? (
                      <span className={styles.flag}>
                        {flagWords(line.flag)}
                      </span>
                    ) : line.already_in_plate && line.declared_ul != null ? (
                      <span className={styles.note}>
                        already in the plate: {ul(line.declared_ul)} declared,
                        nothing drawn
                      </span>
                    ) : (
                      ""
                    )}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        ))}
      </table>
      <div className={styles.tips}>
        <strong>Tips:</strong> {plural(totalTips, "tip")}
        {tips.length > 0 && (
          <>
            {" "}
            (
            {tips.map((t, i) => (
              <span key={i}>
                {i > 0 && ", "}
                {t.tips} from {t.rack} in slot {t.slot}
              </span>
            ))}
            )
          </>
        )}
      </div>
      {accounting && verify && verify.accounting.length > 0 && (
        <details
          className={styles.accounting}
          open={showAccounting}
          onToggle={(e) =>
            setShowAccounting((e.target as HTMLDetailsElement).open)
          }
        >
          <summary>Where every liquid ended up</summary>
          <Accounting verify={verify} />
        </details>
      )}
    </div>
  );
}

/* Where every liquid ended up: declared, delivered, left in the source, elsewhere, lost. */
export function Accounting({ verify }: { verify: VerifyReport }) {
  return (
    <div className={styles.scroll}>
      <table className={styles.table} aria-label="Where every liquid ended up">
        <thead>
          <tr>
            <th>Liquid</th>
            <th className="num">Declared</th>
            <th className="num">Delivered</th>
            <th className="num">Left in source</th>
            <th className="num">Elsewhere</th>
            <th className="num">Lost</th>
            <th>Flags</th>
          </tr>
        </thead>
        <tbody>
          {verify.accounting.map((a, i) => (
            <tr key={i} className={a.flags.length ? styles.flagged : undefined}>
              <td>
                {a.liquid}
                {a.logical && a.logical !== a.liquid && (
                  <span className="muted">
                    {" "}
                    ({a.logical.replace(/_/g, " ")})
                  </span>
                )}
              </td>
              <td className="num">{ul(a.declared_ul)}</td>
              <td className="num">{ul(a.delivered_ul)}</td>
              <td className="num">{ul(a.left_in_source_ul)}</td>
              <td className="num">
                {a.elsewhere.length
                  ? ul(a.elsewhere.reduce((n, e) => n + e.ul, 0))
                  : "—"}
              </td>
              <td className="num">{a.lost_ul > 0 ? ul(a.lost_ul) : "—"}</td>
              <td>
                {a.flags.map((f, j) => (
                  <span key={j} className={styles.flag}>
                    {f}
                  </span>
                ))}
                {a.notes.map((f, j) => (
                  <span key={j} className={styles.note}>
                    {f}
                  </span>
                ))}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function flagWords(flag: string): string {
  switch (flag) {
    case "would_run_dry":
      return "would run dry";
    case "no_margin":
      return "no margin";
    case "draws_air":
      return "draws air";
    default:
      return flag.replace(/_/g, " ");
  }
}
