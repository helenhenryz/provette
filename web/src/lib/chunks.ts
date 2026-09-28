/* A page loaded before a deploy asks for a chunk whose file name changed with the new build,
   and the old file is gone: "Failed to fetch dynamically imported module". The cure is the new
   index, so the page reloads itself once; the guard in sessionStorage keeps a real outage
   from reloading forever, and the second failure reaches the error page. */

const RELOADED = "provette.reloaded-for-chunk";

export function isChunkLoadError(error: unknown): boolean {
  const text = error instanceof Error ? error.message : String(error ?? "");
  return /dynamically imported module|Loading chunk|Importing a module script failed/i.test(
    text,
  );
}

/* True when the page reloaded itself (the caller then stops rendering); false when it already
   did once this browser session, so the caller shows the error instead. */
export function reloadOnceForChunk(): boolean {
  try {
    if (sessionStorage.getItem(RELOADED) === "1") return false;
    sessionStorage.setItem(RELOADED, "1");
  } catch {
    return false;
  }
  window.location.reload();
  return true;
}

/* The page rendered a chunk successfully: the next stale-chunk failure may reload again. */
export function chunkLoaded(): void {
  try {
    sessionStorage.removeItem(RELOADED);
  } catch {
    /* private mode */
  }
}

/* `import()` for a lazy component: a stale chunk reloads the page once, anything else throws. */
export async function importChunk<T>(load: () => Promise<T>): Promise<T> {
  try {
    const loaded = await load();
    chunkLoaded();
    return loaded;
  } catch (error) {
    if (isChunkLoadError(error) && reloadOnceForChunk())
      return new Promise<T>(() => undefined); // the reload takes over
    throw error;
  }
}
