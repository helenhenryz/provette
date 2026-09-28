"""A negative control: each plain protocol against the plate map of a DIFFERENT request.

    env -u PYTHONPATH uv run python eval/checks/control.py

If any of these verified, "verified" would mean little.
"""

from __future__ import annotations

import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from provette.intent.cli import verify
from provette.intent.spec import load_platemap

ROOT = Path(__file__).parents[2]
HERE = Path(__file__).parent


def one(job: tuple[str, str]) -> dict[str, str]:
    protocol, other = job
    result = verify(
        HERE / "protocols" / "plain" / f"{protocol}.py",
        load_platemap(ROOT / "eval" / "platemaps" / f"{other}.json"),
    )
    return {"protocol": protocol, "platemap": other, "intent": result.intent.status}


def main() -> None:
    ids = sorted(p.stem for p in (ROOT / "eval" / "platemaps").glob("*.json"))
    jobs = [(ids[i], ids[(i + shift) % len(ids)]) for shift in (1, 5) for i in range(len(ids))]
    with ProcessPoolExecutor(max_workers=8) as pool:
        rows = list(pool.map(one, jobs))
    (HERE / "results" / "control.json").write_text(json.dumps(rows, indent=1) + "\n")
    for status in ("verified", "mismatch", "cannot_check"):
        print(status, sum(r["intent"] == status for r in rows))
    print([r for r in rows if r["intent"] == "verified"])


if __name__ == "__main__":
    main()
