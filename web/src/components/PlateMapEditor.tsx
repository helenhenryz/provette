import { useState } from "react";
import type { Amount, Contents, PlateMap } from "../lib/api";
import { liquidName } from "../lib/format";
import { PlateGrid } from "./PlateGrid";
import { PlateMapSums } from "./PlateMapSums";
import styles from "./PlateMapEditor.module.css";

/* The planner's proposal, as a plate the person can read and edit well by well before
   approving it. Volumes are edited in place; the map's structure (which liquids, which
   groups) stays the planner's, and the whole JSON is one click away for anything else. */
export function PlateMapEditor({
  platemap,
  onChange,
  mode = "all",
}: {
  platemap: PlateMap;
  onChange: (next: PlateMap) => void;
  mode?: "all" | "numbers";
}) {
  const [json, setJson] = useState(false);
  const [jsonText, setJsonText] = useState("");
  const [jsonError, setJsonError] = useState<string | null>(null);
  const variant = platemap.variants[0];

  function setAmount(
    path: { well?: string; group?: number; member?: number },
    liquid: string,
    value: string,
  ) {
    const next: PlateMap = structuredClone(platemap);
    const v = next.variants[0];
    const target: Contents | undefined =
      path.well != null
        ? v.pinned[path.well]
        : v.groups[path.group!].members[path.member!];
    if (!target) return;
    if (value === "declared") target[liquid] = "declared";
    else {
      const n = Number(value);
      if (!Number.isFinite(n) || n < 0) return;
      target[liquid] = n;
    }
    onChange(next);
  }

  function openJson() {
    setJsonText(JSON.stringify(platemap, null, 1));
    setJsonError(null);
    setJson(true);
  }

  function applyJson() {
    try {
      const parsed = JSON.parse(jsonText) as PlateMap;
      onChange(parsed);
      setJson(false);
    } catch (e) {
      setJsonError(e instanceof Error ? e.message : String(e));
    }
  }

  return (
    <div className="stack">
      {mode === "all" && <PlateGrid platemap={platemap} />}
      {mode === "all" && platemap.notes.length > 0 && (
        <div className={styles.notes}>
          <div className={styles.notesTitle}>The planner's notes</div>
          <ul>
            {platemap.notes.map((n, i) => (
              <li key={i}>{n}</li>
            ))}
          </ul>
        </div>
      )}
      {variant && (
        <details className={styles.sums} open>
          <summary>
            The map in numbers: check each well's sum before approving
          </summary>
          <PlateMapSums platemap={platemap} compact />
        </details>
      )}
      {variant && (
        <div className={styles.tables}>
          {Object.keys(variant.pinned).length > 0 && (
            <table>
              <thead>
                <tr>
                  <th>Well</th>
                  <th>Holds at the end (µl)</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(variant.pinned).map(([well, contents]) => (
                  <tr key={well}>
                    <td className="mono">{well}</td>
                    <td>
                      <ContentsInputs
                        contents={contents}
                        onChange={(liquid, value) =>
                          setAmount({ well }, liquid, value)
                        }
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {variant.groups.map((group, g) => (
            <table key={g}>
              <thead>
                <tr>
                  <th>
                    {group.name}: {group.members.length} wells,{" "}
                    {group.within
                      ? `within ${group.within.join(", ")}`
                      : "anywhere on the plate"}
                  </th>
                  <th>Holds at the end (µl)</th>
                </tr>
              </thead>
              <tbody>
                {group.members.map((contents, m) => (
                  <tr key={m}>
                    <td className="muted">well {m + 1}</td>
                    <td>
                      <ContentsInputs
                        contents={contents}
                        onChange={(liquid, value) =>
                          setAmount({ group: g, member: m }, liquid, value)
                        }
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ))}
        </div>
      )}
      <div className="row">
        {!json ? (
          <button
            type="button"
            className={styles.linkButton}
            onClick={openJson}
          >
            Edit the plate map as JSON
          </button>
        ) : (
          <div className={`stack ${styles.jsonBox}`}>
            <textarea
              className={styles.json}
              value={jsonText}
              onChange={(e) => setJsonText(e.target.value)}
              rows={16}
              spellCheck={false}
            />
            {jsonError && <p className={styles.error}>{jsonError}</p>}
            <div className="row">
              <button
                type="button"
                className={styles.button}
                onClick={applyJson}
              >
                Use this JSON
              </button>
              <button
                type="button"
                className={styles.linkButton}
                onClick={() => setJson(false)}
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function ContentsInputs({
  contents,
  onChange,
}: {
  contents: Contents;
  onChange: (liquid: string, value: string) => void;
}) {
  return (
    <div className={styles.inputs}>
      {Object.entries(contents).map(([liquid, amount]) => (
        <label key={liquid} className={styles.amount}>
          <span>{liquidName(liquid)}</span>
          <AmountInput value={amount} onChange={(v) => onChange(liquid, v)} />
        </label>
      ))}
    </div>
  );
}

function AmountInput({
  value,
  onChange,
}: {
  value: Amount;
  onChange: (v: string) => void;
}) {
  if (value === "declared")
    return <span className={styles.declared}>all of it (as declared)</span>;
  return (
    <input
      type="number"
      min={0}
      step="any"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className={styles.number}
    />
  );
}
