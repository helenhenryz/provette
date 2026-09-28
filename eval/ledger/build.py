"""The ledger over the public library: does the record of a run hold up on protocols written
by people who are not us?

Reads the two sweeps of Opentrons/Protocols at the pinned commit (D-05), written by
`provette corpus run`:

* `.cache/corpus/trace_worker.jsonl`: every protocol through the tracer, and the tracer's
  record checked against `opentrons.cli analyze`, Opentrons' own reading of the same run (D-09);
  `cross_check` is the number of places the two disagree. From API level 2.14 the analysis is
  independent of the messages the tracer reads; below it, Opentrons builds the analysis from
  the same messages, so there it checks our reading of them (D-10);
* `.cache/corpus/export_worker.jsonl`: every protocol through the replay export, the JSON the
  pages draw.

Writes `counts.json`: counts only. Nothing from the library is copied here (D-05).

    env -u PYTHONPATH uv run provette corpus run \
        --worker provette.corpus.workers:trace_worker --jobs 10
    env -u PYTHONPATH uv run provette corpus run \
        --worker provette.corpus.workers:export_worker --jobs 10
    env -u PYTHONPATH uv run python eval/ledger/build.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / ".cache" / "corpus"
HERE = Path(__file__).resolve().parent


def rows(name: str) -> list[dict]:  # type: ignore[type-arg]
    text = (CORPUS / f"{name}.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def api_level(row: dict) -> tuple[int, int]:  # type: ignore[type-arg]
    try:
        major, minor = str(row.get("api_level") or "").split(".")
        return int(major), int(minor)
    except ValueError:
        return (0, 0)


INDEPENDENT_FROM = (2, 14)  # D-10


def main() -> None:
    traced = rows("trace_worker")
    exported = rows("export_worker")
    accepted = [r for r in traced if r["status"] == "ok"]
    compared = [r for r in accepted if r["payload"].get("cross_check") is not None]
    agree = [r for r in compared if r["payload"]["cross_check"] == 0]
    independent = [r for r in compared if api_level(r) >= INDEPENDENT_FROM]
    accepted_slugs = {r["slug"] for r in accepted}
    export_ok = [r for r in exported if r["status"] == "ok" and r["slug"] in accepted_slugs]
    counts = {
        "library": len(traced),
        "accepted": len(accepted),
        "compared": len(compared),
        "agree": len(agree),
        "independent": len(independent),
        "independent_agree": sum(r["payload"]["cross_check"] == 0 for r in independent),
        "exported": len(export_ok),
        "events": sum(int(r["payload"].get("events") or 0) for r in accepted),
        "sources": [".cache/corpus/trace_worker.jsonl", ".cache/corpus/export_worker.jsonl"],
    }
    (HERE / "counts.json").write_text(json.dumps(counts, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(counts, indent=1))


if __name__ == "__main__":
    main()
