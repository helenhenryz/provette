import { useState } from "react";
import { roles, type UnplacedLiquid } from "../lib/api";
import styles from "./UnplacedLiquids.module.css";
import { withJudge } from "../lib/withJudge";

/* "‘lysozyme’ is …": one card per declared liquid no word list knows, and five answers. An
   answer is written to the word lists the team owns and the checks run again. */
const CHOICES: { list: string; words: string }[] = [
  { list: "sample", words: "a sample" },
  { list: "reagent", words: "a reagent" },
  { list: "carrier", words: "a carrier" },
  { list: "add_last", words: "an enzyme: add last" },
  { list: "add_first", words: "a diluent: add first" },
];

export function UnplacedLiquids({
  liquids,
  onTaught,
}: {
  liquids: UnplacedLiquid[];
  onTaught: () => void;
}) {
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [taught, setTaught] = useState<Record<string, string>>({});

  if (liquids.length === 0) return null;

  async function teach(name: string, list: string) {
    setBusy(`${name}:${list}`);
    setError(null);
    try {
      const r = await withJudge(() => roles.add(list, name));
      if (!r) return; // not run: the password dialog is open
      setTaught((t) => ({ ...t, [name]: list }));
      onTaught();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className={styles.box}>
      <div
        className={styles.head}
        title="no word list knows these; say what each is and the checks run again"
      >
        Unplaced liquids
      </div>
      <ul className={styles.list}>
        {liquids.map((liquid) => (
          <li key={liquid.name} className={styles.card}>
            <div className={styles.name}>
              <strong>‘{liquid.name}’</strong> is
            </div>
            <div className={styles.where}>
              {[
                liquid.description ? `“${liquid.description}”` : null,
                liquid.line != null ? `line ${liquid.line}` : null,
                liquid.wells.length > 0
                  ? `in ${liquid.wells.join(", ")}`
                  : null,
              ]
                .filter(Boolean)
                .join(" · ")}
            </div>
            {taught[liquid.name] ? (
              <p className={styles.done}>
                {CHOICES.find((c) => c.list === taught[liquid.name])?.words} ·
                checking again…
              </p>
            ) : (
              <div className={styles.buttons}>
                {CHOICES.map((c) => (
                  <button
                    key={c.list}
                    type="button"
                    className={styles.choice}
                    disabled={busy != null}
                    onClick={() => teach(liquid.name, c.list)}
                  >
                    {busy === `${liquid.name}:${c.list}` ? "…" : c.words}
                  </button>
                ))}
              </div>
            )}
          </li>
        ))}
      </ul>
      {error && <p className={styles.error}>{error}</p>}
    </div>
  );
}
