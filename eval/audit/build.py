"""The public-library audit: the rules of today over the 833 protocols of Opentrons/Protocols.

Reads `.cache/corpus/check_worker.jsonl` (written by `provette corpus run --worker
provette.corpus.workers:check_worker`) and writes:

* `counts.json`: findings by rule and severity, protocols by worst finding, by category;
* `triage.csv`: one row per finding that a person should judge (every error, every uncertain
  warning, and a sample of the rest), with the slug, the line, the explanation and a link to
  the protocol on library.opentrons.com. Nothing from the library is copied here (D-05).

We fill in the last two columns: verdict (real / deliberate / false alarm / not
sure) and why. Their labels are the precision numbers; until they exist the counts are
counts of findings, not of problems.

    env -u PYTHONPATH uv run python eval/audit/build.py
"""

from __future__ import annotations

import collections
import csv
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / ".cache" / "corpus" / "check_worker.jsonl"
HERE = Path(__file__).resolve().parent
LIBRARY = "https://library.opentrons.com/p/"

RANK = {"error": 2, "warning": 1, "note": 0}


def main() -> None:
    rows = [json.loads(line) for line in SOURCE.read_text(encoding="utf-8").splitlines()]
    ok = [r for r in rows if r["status"] == "ok"]
    by_rule: collections.Counter[str] = collections.Counter()
    worst: collections.Counter[str] = collections.Counter()
    by_category: dict[str, collections.Counter[str]] = collections.defaultdict(collections.Counter)
    findings = []
    for r in ok:
        top = -1
        for f in r["payload"].get("findings", []):
            by_rule[f"{f['rule_id']}:{f['severity']}"] += 1
            top = max(top, RANK[f["severity"]])
            findings.append((r, f))
        label = {2: "error", 1: "warning", 0: "note", -1: "clean"}[top]
        worst[label] += 1
        for category in r.get("categories") or ["(none)"]:
            by_category[category][label] += 1
    counts = {
        "protocols_checked": len(ok),
        "protocols_not_simulating": len(rows) - len(ok),
        "findings_by_rule_and_severity": dict(by_rule),
        "protocols_by_worst_finding": dict(worst),
        "by_category": {k: dict(v) for k, v in sorted(by_category.items())},
        "caveats": [
            "Parameters take the library's default values (fields.json), which may not be what "
            "a user would run.",
            "Only 11 of 833 protocols declare their liquids, so the contamination rules cannot "
            "tell eight replicates from eight samples; those findings need a person.",
            "A finding is a finding, not a confirmed problem, until the triage column is filled.",
        ],
    }
    (HERE / "counts.json").write_text(json.dumps(counts, indent=1), encoding="utf-8")

    random.seed(2026)
    must = [(r, f) for r, f in findings if f["severity"] == "error" or not f["certain"]]
    rest = [(r, f) for r, f in findings if not (f["severity"] == "error" or not f["certain"])]
    sample = must + random.sample(rest, min(150, len(rest)))
    with (HERE / "triage.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(
            [
                "slug",
                "link",
                "category",
                "rule",
                "severity",
                "certain",
                "line",
                "title",
                "explanation",
                "fix",
                "verdict (real / deliberate / false alarm / not sure)",
                "why",
            ]
        )
        for r, f in sorted(sample, key=lambda x: (x[0]["slug"], x[1]["line"] or 0)):
            w.writerow(
                [
                    r["slug"],
                    LIBRARY + r["slug"],
                    "; ".join(r.get("categories") or []),
                    f["rule_id"],
                    f["severity"],
                    f["certain"],
                    f["line"],
                    f["title"],
                    f["explanation"],
                    f.get("fix", ""),
                    "",
                    "",
                ]
            )
    print(json.dumps({k: v for k, v in counts.items() if k != "by_category"}, indent=1))
    print(f"triage rows: {len(sample)} (every error and uncertain finding, plus 150 sampled)")


if __name__ == "__main__":
    main()
