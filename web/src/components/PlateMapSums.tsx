import type { PlateMap } from "../lib/api";
import { liquidName, ul } from "../lib/format";
import { variantArithmetic } from "../lib/plate";
import styles from "./PlateMapSums.module.css";

/* Each well's expected contents as a sum, from the map's numbers: "50 µl drug + 50 µl pbs =
   100 µl · 1:2 of the previous well". Approving a map is checking these sums. */
export function PlateMapSums({
  platemap,
  variant: variantName,
  compact = false,
}: {
  platemap: PlateMap;
  variant?: string | null;
  compact?: boolean;
}) {
  const variant =
    platemap.variants.find((v) => v.name === variantName) ??
    platemap.variants[0];
  if (!variant) return null;
  const rows = variantArithmetic(variant);
  const shown = compact
    ? collapse(rows)
    : rows.map((r) => ({ ...r, count: 1 }));
  return (
    <table className={styles.table}>
      <thead>
        <tr>
          <th>well</th>
          <th>holds at the end</th>
          <th className="num">sum</th>
          <th>step</th>
        </tr>
      </thead>
      <tbody>
        {shown.map((r, i) => (
          <tr key={i}>
            <td className="mono">
              {r.well}
              {r.count > 1 && <span className="muted"> ×{r.count}</span>}
            </td>
            <td>
              {r.sum.parts.map((p, j) => (
                <span key={j}>
                  {j > 0 && " + "}
                  {p.ul == null ? "all of the" : ul(p.ul)} {liquidName(p.name)}
                </span>
              ))}
            </td>
            <td className="num">
              {r.sum.total == null ? "—" : ul(r.sum.total)}
            </td>
            <td className="muted">
              {r.step ? `${r.step} of the previous well` : ""}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

type Row = ReturnType<typeof variantArithmetic>[number];

/* Consecutive wells with the same sum and the same amounts (samples differing only by their
   number) fold into one row, so 40 reaction wells read as one line. Series never fold. */
function collapse(rows: Row[]): (Row & { count: number })[] {
  const out: (Row & { count: number })[] = [];
  const signature = (r: Row) =>
    r.sum.parts
      .map((p) => `${p.name.replace(/_\d+$/, "_n")}=${p.ul}`)
      .join("|") + `|${r.step ?? ""}`;
  for (const r of rows) {
    const last = out[out.length - 1];
    if (last && !r.step && signature(last) === signature(r)) {
      last.count += 1;
      last.well = `${last.well.split(" to ")[0]} to ${r.well}`;
    } else out.push({ ...r, count: 1 });
  }
  return out;
}
