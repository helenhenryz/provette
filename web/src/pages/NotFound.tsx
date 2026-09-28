import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <div className="stack">
      <h1>There is nothing at this address.</h1>
      <p className="muted">
        <Link to="/">A new run</Link> · <Link to="/examples">Examples</Link> ·{" "}
        <Link to="/check?new">Check a protocol</Link>
      </p>
    </div>
  );
}
