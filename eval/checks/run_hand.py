"""The prep sheet by hand: starting volumes worked out by hand from the protocol source,
against prep.py.

    env -u PYTHONPATH uv run python eval/checks/run_hand.py      (after run_correct.py)

Each entry below was derived by reading the protocol file, not the trace: the loop counts and
volume constants are in the comment. Volumes in ul per source well; `tips` per tip-rack slot.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).parent

NORM = [85, 120, 44, 67, 210, 95, 33, 150, 78, 60, 101, 55,
        190, 72, 48, 130, 88, 25, 64, 110, 39, 175, 92, 58]  # fmt: skip
NORM_SAMPLE = [round(500 / c, 2) for c in NORM]  # the protocol rounds to 0.01 ul

HAND: dict[str, dict[str, Any]] = {
    # 14 reactions' worth pooled: 10.5*14, 10*14, 1*14, 1*14, 0.5*14; 2 ul of each template
    "plain/pcr-07": {
        "wells": {
            "1:A5": 147,
            "1:A1": 140,
            "1:A3": 14,
            "1:A4": 14,
            "1:A2": 7,
            **{f"1:{r}{c}": 2 for r in "BC" for c in range(1, 7)},
        },
        "tips": {"4": 3, "5": 15},  # water, buffer, dispensing | fwd, rev, polymerase, 12 templates
    },  # fmt: skip
    # water 12 x 12; buffer drawn 14, 2 returned, drawn 14 again: deepest point 14 - 2 + 14 = 26;
    # enzyme 12 + 2 spare in one draw; 5 ul of each plasmid (wells()[4:16] = A2..D4)
    "short-on-tips/clone-01": {
        "wells": {
            "1:A1": 144,
            "1:B1": 26,
            "1:C1": 14,
            **{f"1:{r}{c}": 5 for c in (2, 3, 4) for r in "ABCD"},
        },
        "tips": {"3": 14},
    },  # fmt: skip
    # PBS 11 x 100; drug 200 once
    "short-on-tips/dil-01": {"wells": {"2:A1": 1100, "3:A1": 200}, "tips": {"4": 1}},
    # water 7 x 50; BSA 100 once; tips 1 + 1 + 7 + 1
    "plain/dil-03": {"wells": {"1:A2": 350, "1:A1": 100}, "tips": {"4": 10}},
    # sample i: round(500/c, 2); water: the sum of round(50 - that, 2)
    "plain/norm-01": {
        "wells": {
            "3:A1": round(sum(round(50 - v, 2) for v in NORM_SAMPLE), 2),
            **{f"1:{'ABCDEFGH'[i % 8]}{i // 8 + 1}": v for i, v in enumerate(NORM_SAMPLE)},
        },
        "tips": {"4": 1, "5": 24},
    },  # fmt: skip
    # master mix 18 x 8; each cDNA 3 x 2 + 1 spare
    "short-on-tips/pcr-04": {
        "wells": {"5:A1": 144, **{f"2:{r}1": 7 for r in "ABCDEF"}},
        "tips": {"6": 7},
    },
    # reagent: 8 channels x 250 x 3 columns from each of two reservoir wells; samples 2 x 5
    "plain/brad-01": {
        "wells": {
            "2:A1": 6000,
            "2:A2": 6000,
            **{f"3:{'ABCD'[i % 4]}{i // 4 + 1}": 10 for i in range(20)},
        },
        "tips": {"4": 20, "5": 48},
    },  # fmt: skip
    # 100 ul of each of 40 sera (A1..H5) and of 8 standards (tubes A1..D2); 5 x 8 tips + 1
    "short-on-tips/elisa-01": {
        "wells": {
            **{f"1:{r}{c}": 100 for c in range(1, 6) for r in "ABCDEFGH"},
            **{f"3:{r}{c}": 100 for c in (1, 2) for r in "ABCD"},
        },
        "tips": {"4": 41},
    },  # fmt: skip
    # master mix 24 x 12.5, water 24 x 10.5, 2 ul of each of 24 gDNA; tips 1 + 24 + 24
    "plain/pcr-02": {
        "wells": {
            "5:A1": 300,
            "5:B1": 252,
            **{f"4:{'ABCD'[i % 4]}{i // 4 + 1}": 2 for i in range(24)},
        },
        "tips": {"1": 49},
    },  # fmt: skip
    # 48 x 50
    "plain/fill-02": {"wells": {"2:A1": 2400}, "tips": {"1": 1}},
}


def main() -> None:
    rows = json.loads((HERE / "results" / "correct.json").read_text())
    by_name = {f"{row['condition']}/{row['id']}": row for row in rows}
    out = []
    for name, hand in HAND.items():
        prep = by_name[name]["prep"]
        got = {f"{p['slot']}:{p['well']}": p["needed_ul"] for p in prep["lines"] if p["needed_ul"]}
        tips = {t["slot"]: t["tips"] for t in prep["tips"]}
        wrong = {
            well: (hand["wells"].get(well), got.get(well))
            for well in sorted(set(hand["wells"]) | set(got))
            if abs((hand["wells"].get(well) or 0) - (got.get(well) or 0)) > 0.005
        }
        ok = not wrong and tips == hand["tips"]
        out.append({"protocol": name, "source_wells": len(hand["wells"]), "agree": ok,
                    "differences": wrong, "tips_hand": hand["tips"],
                    "tips_prep": tips})  # fmt: skip
        print(f"{name:<26} {len(hand['wells']):>3} source wells  "
              f"{'AGREE' if ok else 'DIFFER ' + str(wrong) + str(tips)}")  # fmt: skip
    (HERE / "results" / "hand.json").write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
