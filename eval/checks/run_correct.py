"""The correct protocols against their own plate maps: `provette verify` on the 17 requests
with a map, in both conditions.

    env -u PYTHONPATH uv run python eval/checks/run_correct.py

Writes results/correct.json (one row per protocol) and results/correct/<condition>-<id>.txt (the
report a person reads).
"""

from __future__ import annotations

import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

from provette.intent.cli import verify
from provette.intent.report import report_json, report_text
from provette.intent.spec import load_platemap
from provette.trace import TraceError

HERE = Path(__file__).parent
ROOT = HERE.parents[1]
MAPS = ROOT / "eval" / "platemaps"
PILOT = HERE / "protocols"
CONDITIONS = ("plain", "short-on-tips")


def request_ids() -> list[str]:
    return sorted(path.stem for path in MAPS.glob("*.json"))


def one(job: tuple[str, str]) -> dict[str, Any]:
    condition, request_id = job
    protocol = PILOT / condition / f"{request_id}.py"
    try:
        result = verify(protocol, load_platemap(MAPS / f"{request_id}.json"))
    except TraceError as error:
        return {"condition": condition, "id": request_id, "exit_code": 2, "error": str(error)}
    out = HERE / "results" / "correct"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{condition}-{request_id}.txt").write_text(report_text(result), encoding="utf-8")
    return {"condition": condition, "id": request_id, **report_json(result)}


def main() -> None:
    jobs = [(condition, request_id) for condition in CONDITIONS for request_id in request_ids()]
    with ProcessPoolExecutor(max_workers=8) as pool:
        rows = list(pool.map(one, jobs))
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / "correct.json").write_text(json.dumps(rows, indent=1) + "\n")
    for row in rows:
        intent = row.get("intent", {})
        flags = sum(bool(a["flags"]) for a in row.get("accounting", []))
        prep = sum(bool(p["flag"]) for p in row.get("prep", {}).get("lines", []))
        print(
            f"{row['condition']:<14}{row['id']:<10} exit {row['exit_code']}  "
            f"{intent.get('status', 'rejected'):<13} wells {intent.get('wells_ok')}/"
            f"{intent.get('wells_total')}  accounting flags {flags}  prep flags {prep}"
        )


if __name__ == "__main__":
    main()
