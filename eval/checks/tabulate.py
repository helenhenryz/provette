"""The mutant table of the README, from results/mutants.json (and the survivors, to read)."""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).parent
NAMES = {
    "a": "a volume",
    "b": "b drop-last",
    "c": "c reorder",
    "d": "d wrong-source",
    "e": "e to-trash",
}


def main() -> None:
    rows = json.loads((HERE / "results" / "mutants.json").read_text())
    print("| operator | generated | pass the simulator | compare | cannot check | accounting "
          "| prep | `provette check` | nothing |")  # fmt: skip
    print("|---|---|---|---|---|---|---|---|---|")
    for op in [*NAMES, None]:
        mine = [r for r in rows if op is None or r["operator"] == op]
        live = [r for r in mine if r["simulator"] == "passed"]
        cells = [
            len(mine),
            len(live),
            sum(r["intent"] == "mismatch" for r in live),
            sum(r["intent"] == "cannot_check" for r in live),
            sum(bool(r["accounting_flags"]) for r in live),
            sum(bool(r["prep_flags"]) for r in live),
            sum(bool(r["check_findings"]) for r in live),
            sum(nothing(r) for r in live),
        ]
        print(f"| {NAMES.get(op, 'all')} | " + " | ".join(map(str, cells)) + " |")  # type: ignore[arg-type]
    print()
    for r in rows:
        if r["simulator"] == "passed" and nothing(r):
            print(f"SURVIVOR {r['mutant']} line {r['line']}: {r['description']}  same_deck="
                  f"{r['same_deck']} same_destination={r['same_destination']} "
                  f"order_note={r['order_note']} layout_free={r['layout_free']}")  # fmt: skip
            for d in r["diff"]:
                print("      ", d)


def nothing(r: dict) -> bool:  # type: ignore[type-arg]
    return (r["intent"] == "verified" and not r["accounting_flags"] and not r["prep_flags"]
            and not r["check_findings"])  # fmt: skip


if __name__ == "__main__":
    main()
