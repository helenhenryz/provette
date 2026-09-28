import { useState } from "react";
import type { PlateMap, ReplayExport, VerifyReport } from "../lib/api";
import { liquidName, plural, ul } from "../lib/format";
import { plateView, type Holding, type PlateCell } from "../lib/plate";
import { PlateFromMap } from "./PlateFromMap";
import styles from "./PlateGrid.module.css";

/* The plate map as a plate: every well of the destination, what it should hold, what it does
   hold, and whether the check agreed. Drawn with the replay's own close-up (PlateFromMap), so
   the map the person approves, the plate the check verified and the replay's plate are one
   drawing. Hover a well to read it in words; nothing on the page says so. */
export function PlateGrid({
  platemap,
  verify,
  replay,
  title,
  stack = false,
}: {
  platemap: PlateMap | null;
  verify?: VerifyReport | null;
  replay?: ReplayExport | null;
  title?: string;
  stack?: boolean; // the side column under the plate (in a rail)
}) {
  const view = plateView(platemap, verify, replay);
  const [hover, setHover] = useState<PlateCell | null>(null);
  const filled = view.cells.filter((c) => c.status !== "empty");
  const proposed = view.groups.filter((g) => g.shownIn);
  return (
    <div className={`${styles.wrap} ${stack ? styles.stacked : ""}`}>
      <div className={styles.plate}>
        {title && <div className={styles.title}>{title}</div>}
        <div className={styles.replayPlate}>
          <PlateFromMap
            view={view}
            onHover={(well) =>
              setHover(
                well ? (view.cells.find((c) => c.well === well) ?? null) : null,
              )
            }
          />
        </div>
        <div className={styles.readout} aria-live="polite">
          {hover && <CellWords cell={hover} />}
        </div>
      </div>
      <div className={styles.side}>
        {view.destinationName && (
          <div className={styles.dest}>{view.destinationName}</div>
        )}
        {view.variant && platemap && platemap.variants.length > 1 && (
          <div className="small muted">
            Reading of the request: {view.variant}
          </div>
        )}
        {view.groups.map(({ group, shownIn }, i) => (
          <div key={i} className={styles.group}>
            <div className={styles.groupTitle}>
              {plural(group.members.length, "well")}{" "}
              {group.within
                ? `within ${group.within.join(", ")}`
                : "anywhere on the plate"}
              {group.position === "same_as_source" &&
                ", each in the well its sample came from"}
              {group.order_hint === "index" && ", in order"}
              {shownIn && <span className="muted"> · shown in {shownIn}</span>}
            </div>
            <GroupMembers members={group.members} />
          </div>
        ))}
        {view.legend.length > 0 && <Legend legend={view.legend} />}
        <ul className={styles.key}>
          {verify ? (
            <>
              <li>
                <span className={styles.keyDot} />{" "}
                {plural(filled.filter((c) => c.status === "ok").length, "well")}{" "}
                hold what the plate map says
              </li>
              <li>
                <span className={`${styles.keyDot} ${styles.mismatch}`} />{" "}
                ringed:{" "}
                {plural(
                  filled.filter((c) => c.status === "mismatch").length,
                  "well",
                )}{" "}
                do not
              </li>
            </>
          ) : (
            <li>
              <span className={styles.keyDot} />{" "}
              {filled.length
                ? `${plural(filled.length, "well")} planned`
                : "no well planned"}
            </li>
          )}
          {proposed.length > 0 && (
            <li>
              <span className={`${styles.keyDot} ${styles.proposedDot}`} />{" "}
              dashed: could go anywhere
            </li>
          )}
        </ul>
      </div>
    </div>
  );
}

/* Up to twelve liquids are listed. A longer legend (one liquid per sample well) folds into a
   colour bar and one line, and opens on request. */
function Legend({ legend }: { legend: { name: string; colour: string }[] }) {
  const list = (
    <ul className={styles.legend}>
      {legend.map((l) => (
        <li key={l.name}>
          <span className={styles.swatch} style={{ background: l.colour }} />{" "}
          {liquidName(l.name)}
        </li>
      ))}
    </ul>
  );
  if (legend.length <= 12) return list;
  const families = new Set(
    legend.map((l) =>
      l.name
        .replace(/ of .*$/, "")
        .replace(/@.*$/, "")
        .replace(/[_ ]?[A-P]?\d+$/, ""),
    ),
  );
  const words =
    families.size === 1
      ? `${legend.length} × ${liquidName([...families][0])}, one per well`
      : `${legend.length} liquids`;
  return (
    <details className={styles.legendFold}>
      <summary>
        <span className={styles.bar} aria-hidden="true">
          {legend.map((l) => (
            <span key={l.name} style={{ background: l.colour }} />
          ))}
        </span>
        {words}
      </summary>
      {list}
    </details>
  );
}

function CellWords({ cell }: { cell: PlateCell }) {
  return (
    <div>
      <strong>{cell.well}</strong>{" "}
      {cell.status === "mismatch" && (
        <span className={styles.bad}>
          does not hold what the plate map says.{" "}
        </span>
      )}
      {cell.status === "ok" && (
        <span className={styles.good}>holds what the plate map says. </span>
      )}
      {cell.status === "proposed" && (
        <span className={styles.muted}>
          a proposed place for one of the {cell.group ?? "group"} wells.{" "}
        </span>
      )}
      {cell.expected && (
        <span>
          Expected: <HoldingWords holdings={cell.expected} />
          {sumWords(cell.expected)}.{" "}
        </span>
      )}
      {cell.found && (
        <span>
          Holds: <HoldingWords holdings={cell.found} />.
        </span>
      )}
      {cell.issues.length > 0 && <span> {cell.issues.join("; ")}.</span>}
      {!cell.expected && !cell.found && <span className="faint">empty</span>}
    </div>
  );
}

function sumWords(holdings: Holding[]): string {
  if (holdings.length < 2 || holdings.some((h) => h.ul == null)) return "";
  return ` = ${ul(holdings.reduce((n, h) => n + (h.ul ?? 0), 0))}`;
}

function HoldingWords({ holdings }: { holdings: Holding[] }) {
  return (
    <>
      {holdings.map((h, i) => (
        <span key={i}>
          {i > 0 && ", "}
          {h.carryOver
            ? `a film of ${h.name}`
            : h.ul == null
              ? `${liquidName(h.name)} (all of it)`
              : `${ul(h.ul)} ${liquidName(h.name)}`}
        </span>
      ))}
    </>
  );
}

function GroupMembers({
  members,
}: {
  members: PlateMap["variants"][number]["groups"][number]["members"];
}) {
  // Collapse members that differ only by an index: "20 µl master mix + 5 µl sample 1..8".
  const signature = (m: Record<string, number | "declared">) =>
    Object.entries(m)
      .map(([k, v]) => `${k.replace(/_\d+$/, "_n")}=${v}`)
      .join("|");
  const seen = new Map<
    string,
    { first: Record<string, number | "declared">; count: number }
  >();
  for (const m of members) {
    const s = signature(m);
    const row = seen.get(s);
    if (row) row.count += 1;
    else seen.set(s, { first: m, count: 1 });
  }
  return (
    <ul className={styles.members}>
      {[...seen.values()].map(({ first, count }, i) => (
        <li key={i}>
          {count > 1 && <span className="muted">{count} × </span>}
          {Object.entries(first)
            .map(
              ([k, v]) =>
                `${v === "declared" ? "all of the" : ul(v)} ${liquidName(count > 1 ? k.replace(/_\d+$/, " n") : k)}`,
            )
            .join(" + ")}
        </li>
      ))}
    </ul>
  );
}
