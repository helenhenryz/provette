import { useEffect } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Notice } from "../components/Notice";
import { RunRecord, RunRecordSkeleton } from "../components/RunRecord";
import { checkMemory, checks, type Analysis } from "../lib/api";
import { plural, when } from "../lib/format";
import { useFetch } from "../lib/useFetch";

/* The result of a check, as the run record: no model's work, the file name as the title.
   "Check another" opens the composer; the tab's remembered check (lib/api.ts, `checkMemory`)
   stays until a new one is posted. */

/* The badge's popover: one sentence for the whole verdict. */
function checkSentence(analysis: Analysis, hasMap: boolean): string {
  if (!analysis.simulator.passed)
    return "The simulator rejected the protocol, so nothing else was checked.";
  const findings = analysis.check?.findings ?? [];
  const errors = findings.filter((f) => f.severity === "error").length;
  const intent = analysis.verify?.intent.status;
  const rules =
    findings.length === 0
      ? "no rule fired"
      : errors > 0
        ? `${plural(errors, "rule")} found an error`
        : `${plural(findings.length, "rule")} spoke`;
  if (!hasMap)
    return `No plate map was given, so only the biology rules ran: ${rules}.`;
  if (intent === "verified")
    return `Every well holds what the plate map says, and ${rules}.`;
  if (intent === "cannot_check")
    return `The plate map could not be checked against this protocol; ${rules}.`;
  return `The plate does not match the plate map, and ${rules}.`;
}

export function CheckResultPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const row = useFetch(() => checks.get(id), `check:${id}`);
  // The remembered check is gone (another deployment, cleaned data): forget it and fall
  // through to the composer, silently.
  const stale = row.status === 404 && checkMemory.last.get() === id;
  useEffect(() => {
    if (!stale) return;
    checkMemory.last.forget();
    navigate("/check", { replace: true });
  }, [stale, navigate]);
  if (row.loading || stale) return <RunRecordSkeleton />;
  if (row.error || !row.data)
    return (
      <Notice
        tone="error"
        title={
          row.status === 404 ? "No such check" : "The check could not be loaded"
        }
      >
        {row.error && row.error.toLowerCase() !== "no such check" && (
          <>{row.error} · </>
        )}
        <Link to="/check?new">check a protocol</Link> ·{" "}
        <Link to="/runs">Past runs</Link> · <Link to="/">write one</Link>
      </Notice>
    );
  const check = row.data;
  const analysis = check.analysis;
  const marked =
    analysis.simulator.line != null ? [analysis.simulator.line] : [];
  const hasMap = check.platemap != null;
  const findings = analysis.check?.findings ?? [];
  const verdict: "verified" | "not_verified" | "checked" = !analysis.simulator
    .passed
    ? "not_verified"
    : hasMap
      ? analysis.verify?.intent.status === "verified" &&
        findings.every((f) => f.severity === "note")
        ? "verified"
        : "not_verified"
      : "checked";
  return (
    <RunRecord
      header={{
        crumb: { to: "/check?new", label: "Check" },
        crumbWord: check.name,
        action: { to: "/check?new", label: "Check another" },
        title: check.name,
        titleMono: true,
        badge: verdict,
        badgeDetail: checkSentence(analysis, hasMap),
        meta: [
          `checked ${when(check.created)}`,
          `${analysis.seconds} s`,
          hasMap ? "with a plate map" : "no plate map",
        ],
      }}
      analysis={analysis}
      platemap={check.platemap}
      review={{ text: check.protocol, marked }}
      links={{
        protocolUrl: checks.protocolUrl(id),
        protocolName: check.name,
        replayUrl: checks.replayUrl(id),
        jsonUrl: `/api/checks/${id}`,
      }}
      onTaught={() =>
        checks
          .create({
            protocol: check.protocol,
            platemap: check.platemap as unknown as Record<
              string,
              unknown
            > | null,
            name: check.name,
          })
          .then((next) => {
            checkMemory.last.set(next.id);
            navigate(`/check/${next.id}`);
          })
      }
      onNotChecked={() => navigate("/rules/new")}
    />
  );
}
