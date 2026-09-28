"""How far are the correct protocols' wells from the plate maps? The basis of `tolerance_ul`.

env -u PYTHONPATH uv run python eval/checks/measure_tolerance.py
"""

from __future__ import annotations

import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from provette.intent.cli import verify
from provette.intent.spec import load_platemap

ROOT = Path(__file__).parents[2]
HERE = Path(__file__).parent


def deviations(job: tuple[str, str]) -> list[tuple[float, float, str]]:
    condition, request_id = job
    result = verify(
        HERE / "protocols" / condition / f"{request_id}.py",
        load_platemap(ROOT / "eval" / "platemaps" / f"{request_id}.json"),
    )
    out = []
    for r in result.intent.wells:
        for liquid, want in r.expected.items():
            have = r.found.get(liquid, 0.0)
            out.append((abs(have - want), want, f"{condition}/{request_id} {r.well} {liquid}"))
    return out


def main() -> None:
    ids = sorted(p.stem for p in (ROOT / "eval" / "platemaps").glob("*.json"))
    jobs = [(c, i) for c in ("plain", "short-on-tips") for i in ids]
    with ProcessPoolExecutor(max_workers=8) as pool:
        rows = [row for rows in pool.map(deviations, jobs) for row in rows]
    rows.sort(reverse=True)
    nonzero = [row for row in rows if row[0] > 1e-9]
    print(f"{len(rows)} expected amounts; {len(nonzero)} differ from the map at all")
    for off, want, where in nonzero[:8]:
        print(f"  off by {off:.4f} ul of {want:.4f} ({100 * off / want:.2f}%)  {where}")
    summary = {
        "expected_amounts": len(rows),
        "differ_at_all": len(nonzero),
        "largest_absolute_ul": max((r[0] for r in rows), default=0),
        "largest_relative": max((r[0] / r[1] for r in rows), default=0),
        "worst": [{"off_ul": o, "expected_ul": w, "where": s} for o, w, s in nonzero[:8]],
    }
    (HERE / "results" / "tolerance.json").write_text(json.dumps(summary, indent=1) + "\n")


if __name__ == "__main__":
    main()
