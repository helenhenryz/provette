import { useEffect, useRef, useState } from "react";
import { Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { Notice } from "../components/Notice";
import { checkMemory, checks, type CheckDraft } from "../lib/api";
import EditorModule from "react-simple-code-editor";
import { highlightNode } from "../lib/highlight";

/* The package is CommonJS: the production bundle hands its default export over wrapped once more
   than the test runner does (a page that rendered in tests and crashed in the build, error #130). */
const Editor = ((EditorModule as unknown as { default?: typeof EditorModule })
  .default ?? EditorModule) as typeof EditorModule;
import styles from "./Check.module.css";
import { looksLikeProtocol } from "../lib/protocolFile";

/* Flow 3: paste, choose or drop a protocol, optionally with a plate map, and get the report.
   The Check tab and /check open the last check of this tab when one is remembered
   (lib/api.ts, `checkMemory`); /check?new is the composer, which "Check another" on the
   result opens. A remembered id that no longer exists falls through to the composer
   (CheckResult.tsx). */
export function CheckPage() {
  const [params] = useSearchParams();
  const last = checkMemory.last.get();
  if (last && !params.has("new"))
    return <Navigate to={`/check/${last}`} replace />;
  return <Composer draft={checkMemory.draft.get()} />;
}

/* The composer remembers its draft for the tab's session, so a half-typed check survives a
   tab switch; the draft goes when a check is posted. */
function Composer({ draft }: { draft: CheckDraft | null }) {
  const navigate = useNavigate();
  const [protocol, setProtocol] = useState(draft?.protocol ?? "");
  const [name, setName] = useState(draft?.name ?? "protocol.py");
  const [mapMode, setMapMode] = useState<"none" | "example" | "paste">(
    draft?.mapMode ?? "none",
  );
  const [mapId, setMapId] = useState(draft?.mapId ?? "");
  const [mapText, setMapText] = useState(draft?.mapText ?? "");
  const [maps, setMaps] = useState<{ id: string; request: string }[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [over, setOver] = useState(false); // a file is being dragged over the composer
  const [dropNote, setDropNote] = useState<string | null>(null); // what a drop did not take
  const protocolInput = useRef<HTMLInputElement>(null);
  const mapInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    checks
      .platemaps()
      .then((r) => setMaps(r.platemaps))
      .catch(() => setMaps([]));
  }, []);

  useEffect(() => {
    checkMemory.draft.set({ protocol, name, mapMode, mapId, mapText });
  }, [protocol, name, mapMode, mapId, mapText]);

  async function loadExample() {
    setError(null);
    const example = await checks.example();
    setProtocol(example.protocol);
    setName(example.name);
    setMapMode("example");
    setMapId(example.platemap_id);
  }

  /* Files from a drop or a file input, read here in the browser: a .py is the protocol, a
     .json is the plate map (dropped with the protocol or after it), and anything else is
     named in a sentence and left alone. */
  async function takeFiles(files: ArrayLike<File> | null | undefined) {
    const left: string[] = [];
    const refused: string[] = [];
    for (const file of Array.from(files ?? [])) {
      const lower = file.name.toLowerCase();
      if (lower.endsWith(".py")) {
        const text = await readText(file);
        if (!looksLikeProtocol(text)) {
          refused.push(file.name);
          continue;
        }
        setProtocol(text);
        setName(file.name);
      } else if (lower.endsWith(".json")) {
        setMapText(await readText(file));
        setMapMode("paste");
      } else left.push(file.name);
    }
    const notes = [
      refused.length
        ? `${refused.join(", ")}: not an Opentrons protocol (no run(protocol) function), so it was not added.`
        : "",
      left.length
        ? `${left.join(", ")}: not a .py protocol or a .json plate map, so it was left alone.`
        : "",
    ].filter(Boolean);
    setDropNote(notes.length ? notes.join(" ") : null);
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setOver(false);
    void takeFiles(e.dataTransfer?.files);
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      let platemap: string | Record<string, unknown> | null = null;
      if (mapMode === "example" && mapId)
        platemap = (await checks.platemap(mapId)) as unknown as Record<
          string,
          unknown
        >;
      if (mapMode === "paste" && mapText.trim()) platemap = mapText;
      const row = await checks.create({ protocol, platemap, name });
      checkMemory.last.set(row.id);
      checkMemory.draft.forget();
      navigate(`/check/${row.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <h1 title="no model: the simulator, the replay, twelve rules">
          Check a protocol
        </h1>
        <p className={styles.sub}>
          Simulator, replay, twelve checks. No model.
        </p>
      </header>

      <form
        className={`${styles.form} ${over ? styles.over : ""}`}
        onSubmit={submit}
        onDragOver={(e) => {
          e.preventDefault();
          setOver(true);
        }}
        onDragLeave={() => setOver(false)}
        onDrop={onDrop}
        data-testid="composer"
      >
        <section className={styles.editor}>
          <div className={styles.editorBar}>
            <div className={styles.editorLabel}>
              <label
                htmlFor="protocol"
                title="an Opentrons protocol, as the robot would run it"
              >
                Protocol (.py)
              </label>
              {name !== "protocol.py" && (
                <span className={styles.fileChip}>
                  <span className="mono">{name}</span>
                  <button
                    type="button"
                    onClick={() => setName("protocol.py")}
                    aria-label="Forget the file name"
                    title="Forget the file name"
                  >
                    ×
                  </button>
                </span>
              )}
            </div>
            <div className={styles.editorActions}>
              <span className={styles.dropHint} aria-hidden="true">
                {over ? "Drop it" : "Drop a .py or"}
              </span>
              <button
                type="button"
                className="btn ghost"
                onClick={() => protocolInput.current?.click()}
              >
                Choose a file
              </button>
              <button
                type="button"
                className="btn"
                onClick={loadExample}
                title="a PCR set-up with bugs planted on purpose: the simulator passes it, the checks do not"
              >
                Try the example
              </button>
              <input
                ref={protocolInput}
                type="file"
                accept=".py,text/x-python,text/plain"
                hidden
                aria-label="The protocol file"
                onChange={(e) => void takeFiles(e.target.files)}
              />
            </div>
          </div>
          {dropNote && (
            <p className={styles.dropNote} role="status">
              {dropNote}
            </p>
          )}
          {/* a text box with the same text coloured under it (react-simple-code-editor): typing, pasting
              and dropping work as in any text box */}
          <Editor
            textareaId="protocol"
            className={styles.code}
            value={protocol}
            onValueChange={setProtocol}
            highlight={(code) => highlightNode(code)}
            padding={16}
            placeholder={
              "from opentrons import protocol_api\n\nmetadata = {'apiLevel': '2.19'}\n\ndef run(protocol):\n    ..."
            }
            spellCheck={false}
            required
          />
        </section>

        <aside className={styles.panel}>
          <fieldset className={styles.field}>
            <legend title="what every well should hold at the end">
              Plate map, optional
            </legend>
            <div className={styles.choices}>
              <label
                className={mapMode === "none" ? styles.choiceOn : undefined}
              >
                <input
                  type="radio"
                  name="map"
                  checked={mapMode === "none"}
                  onChange={() => setMapMode("none")}
                />{" "}
                None
              </label>
              <label
                className={mapMode === "example" ? styles.choiceOn : undefined}
              >
                <input
                  type="radio"
                  name="map"
                  checked={mapMode === "example"}
                  onChange={() => setMapMode("example")}
                />{" "}
                An example map
              </label>
              <label
                className={mapMode === "paste" ? styles.choiceOn : undefined}
              >
                <input
                  type="radio"
                  name="map"
                  checked={mapMode === "paste"}
                  onChange={() => setMapMode("paste")}
                />{" "}
                Paste or upload JSON
              </label>
            </div>
            {mapMode === "example" && (
              <select
                value={mapId}
                onChange={(e) => setMapId(e.target.value)}
                className="field"
                required
              >
                <option value="">Choose a plate map…</option>
                {maps.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.id}: {m.request.slice(0, 60)}
                    {m.request.length > 60 ? "…" : ""}
                  </option>
                ))}
              </select>
            )}
            {mapMode === "paste" && (
              <>
                <textarea
                  className={`${styles.code} ${styles.mapCode}`}
                  value={mapText}
                  onChange={(e) => setMapText(e.target.value)}
                  rows={8}
                  spellCheck={false}
                  placeholder='{"id": "...", "liquids": [...], "variants": [...]}'
                />
                <button
                  type="button"
                  className="btn ghost"
                  onClick={() => mapInput.current?.click()}
                >
                  Choose a .json file
                </button>
                <input
                  ref={mapInput}
                  type="file"
                  accept=".json,application/json"
                  hidden
                  aria-label="The plate map file"
                  onChange={(e) => void takeFiles(e.target.files)}
                />
              </>
            )}
          </fieldset>

          <button
            type="submit"
            className={`btn primary lg ${styles.submit}`}
            disabled={busy || !protocol.trim()}
          >
            {busy ? "Checking…" : "Check the protocol"}
          </button>
          {busy && (
            <div className={styles.thinking} aria-live="polite">
              <span className={styles.pulse} aria-hidden="true" />
              Simulator, then the replay: about five seconds…
            </div>
          )}
          {error && (
            <Notice tone="error" title="The check did not run">
              {error}
            </Notice>
          )}
        </aside>
      </form>
    </div>
  );
}

/* A file's text, read in the browser; nothing is sent until the form is. */
function readText(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () =>
      resolve(typeof reader.result === "string" ? reader.result : "");
    reader.onerror = () =>
      reject(reader.error ?? new Error(`could not read ${file.name}`));
    reader.readAsText(file);
  });
}
