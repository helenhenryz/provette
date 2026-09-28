import { useEffect } from "react";
import { Link, isRouteErrorResponse, useRouteError } from "react-router-dom";
import { isChunkLoadError, reloadOnceForChunk } from "../lib/chunks";

/* What a reader sees when a page throws, in the product's words, never the router's developer
   screen. A stale chunk after a deploy reloads the page once on its own (lib/chunks.ts). */
export function ErrorPage() {
  const error = useRouteError();
  const stale = isChunkLoadError(error);
  useEffect(() => {
    if (stale) reloadOnceForChunk();
  }, [stale]);
  const words = isRouteErrorResponse(error)
    ? `${error.status} ${error.statusText}`
    : error instanceof Error
      ? error.message
      : String(error ?? "unknown");
  return (
    <div className="stack">
      <h1>
        {stale
          ? "The product was updated; reloading."
          : "This page hit an error."}
      </h1>
      <p className="muted">{words}</p>
      <p className="muted">
        <button type="button" onClick={() => window.location.reload()}>
          Reload
        </button>{" "}
        · <Link to="/">Write</Link> · <Link to="/examples">Examples</Link> ·{" "}
        <Link to="/check">Check</Link>
      </p>
    </div>
  );
}
