"""Write the plate maps of the hard request set: what each well should end up holding.

    env -u PYTHONPATH uv run python eval/requests-hard/build.py

Same form as `eval/platemaps/build.py`, whose helpers are repeated here so this folder stands
alone: one small function per request, the arithmetic from `provette.calc`, the format from
`provette/intent/spec.py`. Every map was written from the request text before any protocol
for it existed.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from provette.calc import dilution_series, normalise

HERE = Path(__file__).parent
REQUESTS = HERE / "requests.jsonl"

ROWS = "ABCDEFGH"
WELLS_BY_COLUMN = [f"{row}{col}" for col in range(1, 13) for row in ROWS]
WELLS_BY_ROW = [f"{row}{col}" for row in ROWS for col in range(1, 13)]

Map = dict[str, Any]
Contents = dict[str, Any]

WATER = r"(?i)water|h2o"
MIX = r"(?i)master\s*mix|mastermix|\bmix\b|sybr"


def reagent(name: str, pattern: str) -> Map:
    return {"name": name, "role": "reagent", "bind": "name", "pattern": pattern}


def samples(stem: str, pattern: str, count: int, index: str = "number") -> Map:
    return {
        "name": stem + "_{i}",
        "role": "sample",
        "bind": "indexed",
        "pattern": pattern,
        "count": count,
        "index": index,
    }


def by_well(stem: str, pattern: str) -> Map:
    return {"name": stem + "@{well}", "role": "sample", "bind": "well", "pattern": pattern}


def group(name: str, members: list[Contents], *, within=None, position="free", order_hint=None):
    return {
        "name": name,
        "members": members,
        "within": within,
        "position": position,
        "order_hint": order_hint,
    }


def variant(name: str, why: str, *, pinned=None, groups=None) -> Map:
    return {"name": name, "why": why, "pinned": pinned or {}, "groups": groups or []}


def platemap(liquids, variants, *, destination=None, notes=None) -> Map:
    return {
        "liquids": liquids,
        "destination": destination or {"select": "auto"},
        "variants": variants,
        "discard_intended": [],
        "notes": notes or [],
    }


def rounded(contents: Contents) -> Contents:
    return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in contents.items()}


def serial_dilution(points, final_ul, factor, *, first_is_neat, remove_excess):
    """(stock ul, diluent ul) in each well of a serial dilution, after the last step."""
    series = dilution_series(1.0, points, factor, final_ul, first_is_neat, remove_excess)
    return [(p["stock_ul"], p["holds_ul"] - p["stock_ul"]) for p in series]


def scaled(stock_ul, diluent_ul, taken_ul, held_ul, stock, diluent) -> Contents:
    """What `taken_ul` drawn from a well holding `held_ul` of (stock, diluent) contains."""
    contents = {stock: stock_ul * taken_ul / held_ul}
    if diluent_ul > 1e-9:
        contents[diluent] = diluent_ul * taken_ul / held_ul
    return rounded(contents)


# ---------------------------------------------------------------------------------------------
# One function per request
# ---------------------------------------------------------------------------------------------


def hard_dil_01() -> Map:
    members = [{f"serum_{i}": 10, "pbs": 90} for i in range(1, 25) for _ in range(2)]
    return platemap(
        [
            samples("serum", r"(?i)(?:serum|sample)\D{0,12}?(\d+)", 24),
            reagent("pbs", r"(?i)pbs|diluent|buffer|saline"),
        ],
        [
            variant(
                "48 wells of 1:10 serum on the ELISA plate",
                "the request pins duplicates, not positions",
                groups=[group("dilutions", members, order_hint="index")],
            )
        ],
        notes=[
            "The destination is the ELISA plate; the 500 ul dilutions are an intermediate.",
            "100 ul of a well holding 50 ul serum + 450 ul PBS is 10 ul serum + 90 ul PBS.",
        ],
    )


def hard_pool_01() -> Map:
    pool = {f"library_{i}": 25 for i in range(1, 97)}
    return platemap(
        [samples("library", r"(?i)(?:library|lib|sample)\D{0,12}?(\d+)", 96, index="any")],
        [variant("one pool", "one tube, any position", groups=[group("pool", [pool])])],
        notes=["96 x 25 ul is 2.4 ml: the tube must hold it."],
    )


def hard_qpcr_01() -> Map:
    members = []
    for gene in range(1, 4):
        for s in range(1, 9):
            members += [
                {"sybr": 10, f"fwd_{gene}": 1, f"rev_{gene}": 1, f"cdna_{s}": 2, "water": 6}
            ] * 3
        members += [{"sybr": 10, f"fwd_{gene}": 1, f"rev_{gene}": 1, "water": 8}] * 3
    return platemap(
        [
            reagent("sybr", MIX),
            samples("fwd", r"(?i)(?:forward|fwd)\D{0,12}?(\d+)", 3),
            samples("rev", r"(?i)(?:reverse|rev)\D{0,12}?(\d+)", 3),
            samples("cdna", r"(?i)(?:cdna|sample|template)\D{0,12}?(\d+)", 8),
            reagent("water", WATER),
        ],
        [
            variant(
                "72 reactions and 9 no-template controls",
                "the request does not say which wells",
                groups=[group("reactions", members, order_hint="index")],
            )
        ],
        notes=[
            "The primers are declared per gene ('forward primer 1', 'reverse primer 2').",
            "The nine NTC wells are part of the map: a plate without them does not verify.",
        ],
    )


def hard_dil_02() -> Map:
    series = serial_dilution(6, 60, 3, first_is_neat=True, remove_excess=True)
    pinned = {}
    for c, row in enumerate("ABCD", start=1):
        for k, (stock_ul, dmso_ul) in enumerate(series):
            taken = scaled(stock_ul, dmso_ul, 10, 60, f"compound_{c}", "dmso")
            pinned[f"{row}{k + 1}"] = {"medium": "declared", **taken}
    return platemap(
        [
            samples("compound", r"(?i)(?:compound|cmpd|drug)\D{0,12}?(\d+)", 4),
            reagent("dmso", r"(?i)dmso"),
            reagent("medium", r"(?i)medium|media"),
        ],
        [
            variant(
                "4 rows x 6 points on the assay plate",
                "'matching well' and 'one compound per row' pin every position",
                pinned=pinned,
            )
        ],
        notes=[
            "The destination is the assay plate, whose wells keep their declared 90 ul of medium "
            "and gain 10 ul of the dilution point: compound 10/3^k ul and DMSO the rest. Six "
            "points, because the checker counts anything at or below 0.01 ul as absent.",
            "Point 1 is the neat stock ('starting from the neat 10 mM stocks').",
        ],
    )


HARD_NORM_01_NM = [
    12,
    45,
    8,
    80,
    33,
    5.5,
    60,
    21,
    14,
    9,
    72,
    27,
    6,
    40,
    18,
    55,
    11,
    30,
    7.5,
    65,
    24,
    16,
    48,
    10,
    36,
    13,
    70,
    22,
    8.5,
    50,
    29,
    19,
    42,
    15,
    62,
    25,
    6.5,
    38,
    17,
    76,
    20,
    9.5,
    58,
    31,
    12.5,
    44,
    23,
    7,
]


def hard_norm_01() -> Map:
    members = []
    for i, conc in enumerate(HARD_NORM_01_NM, start=1):
        row = normalise([conc], 4, 20)[0]
        members.append(rounded({f"library_{i}": row["sample_ul"], "buffer": row["diluent_ul"]}))
    return platemap(
        [
            reagent("buffer", r"(?i)buffer|\beb\b|elution|\bte\b|water"),
            samples("library", r"(?i)(?:library|lib|sample)\D{0,12}?(\d+)", 48),
        ],
        [
            variant(
                "48 normalised libraries",
                "'a new PCR plate': which wells is free",
                groups=[group("normalised", members, order_hint="index")],
            )
        ],
        notes=["Library i has the i-th concentration. Volumes are exact (80 / concentration)."],
    )


def hard_clone_01() -> Map:
    members = [
        {"buffer": 2, "ligase": 1, "vector": 3, f"insert_{i}": 5, "water": 9} for i in range(1, 25)
    ]
    return platemap(
        [
            reagent("buffer", r"(?i)buffer"),
            reagent("ligase", r"(?i)ligase|enzyme"),
            reagent("vector", r"(?i)vector|backbone|plasmid"),
            samples("insert", r"(?i)(?:insert|fragment|sample)\D{0,12}?(\d+)", 24),
            reagent("water", WATER),
        ],
        [
            variant(
                "24 ligations",
                "the request does not say which wells",
                groups=[group("ligations", members, order_hint="index")],
            )
        ],
        notes=["Buffer, ligase, vector and water may be pooled first; each well still resolves."],
    )


def hard_pcr_01() -> Map:
    pinned = {well: {"mix": 15, f"template@{well}": 5} for well in WELLS_BY_COLUMN}
    return platemap(
        [reagent("mix", MIX), by_well("template", r"(?i)template|sample|dna")],
        [variant("full plate", "'matching well' pins every position", pinned=pinned)],
        notes=["96 x 15 ul is 1,440 ul of the 1,600 ul available: 160 ul is left at the end."],
    )


def hard_elisa_01() -> Map:
    variants = []
    for first_is_neat in (False, True):
        series = serial_dilution(7, 250, 2, first_is_neat=first_is_neat, remove_excess=True)
        standards = []
        for stock_ul, diluent_ul in series:
            standards += [scaled(stock_ul, diluent_ul, 100, 250, "standard", "diluent")] * 2
        standards += [{"diluent": 100}] * 2
        sera = [{f"serum_{i}": 100} for i in range(1, 33) for _ in range(2)]
        first = "first point is the neat stock" if first_is_neat else "first point is 1:2"
        variants.append(
            variant(
                f"16 standard wells and 64 sample wells; {first}",
                "positions are free; whether point 1 is neat is ambiguous",
                groups=[group("standards", standards), group("samples", sera, order_hint="index")],
            )
        )
    return platemap(
        [
            reagent("standard", r"(?i)standard|stock"),
            reagent("diluent", r"(?i)diluent|buffer|pbs"),
            samples("serum", r"(?i)(?:serum|sample)\D{0,12}?(\d+)", 32),
        ],
        variants,
        notes=[
            "The destination is the ELISA plate; the 250 ul dilution series is intermediate "
            "(500 ul in a point before it is passed on: the series plate must hold that).",
            "Each standard well holds 100 ul of its point: the stock's share and the diluent's.",
        ],
    )


def hard_cell_01() -> Map:
    pinned = {}
    for line, columns in ((1, range(1, 5)), (2, range(5, 9)), (3, range(9, 13))):
        for col in columns:
            for row in ROWS:
                pinned[f"{row}{col}"] = {f"line_{line}": 100}
    return platemap(
        [samples("line", r"(?i)(?:line|cells?)\D{0,12}?(\d+)", 3)],
        [variant("three lines by column block", "the request pins the columns", pinned=pinned)],
    )


def hard_bca_01() -> Map:
    series = serial_dilution(7, 100, 2, first_is_neat=True, remove_excess=True)
    standards = []
    for stock_ul, water_ul in series:
        standards += [{**scaled(stock_ul, water_ul, 25, 100, "bsa", "water"), "reagent": 200}] * 2
    standards += [{"water": 25, "reagent": 200}] * 2
    members = [{f"sample_{i}": 25, "reagent": 200} for i in range(1, 41) for _ in range(2)]
    return platemap(
        [
            reagent("reagent", r"(?i)bca|working reagent|reagent"),
            reagent("bsa", r"(?i)bsa|standard|albumin"),
            reagent("water", WATER),
            samples("sample", r"(?i)(?:sample|protein|lysate)\D{0,12}?(\d+)", 40),
        ],
        [
            variant(
                "80 sample wells and 16 standard wells",
                "positions are free",
                groups=[
                    group("samples", members, order_hint="index"),
                    group("standards", standards),
                ],
            )
        ],
        notes=["Every well ends at 225 ul; the plate must hold that."],
    )


def hard_pcr_02() -> Map:
    members = [{"mix": 50, "water": 42, f"template_{i}": 8} for i in range(1, 9)]
    return platemap(
        [
            reagent("mix", MIX),
            reagent("water", WATER),
            samples("template", r"(?i)(?:template|sample|dna)\D{0,12}?(\d+)", 8),
        ],
        [
            variant(
                "8 reactions of 100 ul",
                "the request does not say which wells",
                groups=[group("reactions", members, order_hint="index")],
            )
        ],
        notes=["100 ul reactions: a plate rated 100 ul is full to its working volume."],
    )


def hard_pcr_03() -> Map:
    members = [
        {
            "buffer": 5,
            "dntp": 0.5,
            "polymerase": 0.25,
            "fwd_primer": 1.25,
            "rev_primer": 1.25,
            "water": 14.75,
            f"template_{i}": 2,
        }
        for i in range(1, 49)
    ]
    return platemap(
        [
            samples("template", r"(?i)(?:template|sample|dna)\D{0,12}?(\d+)", 48),
            reagent("fwd_primer", r"(?i)forward|fwd"),
            reagent("rev_primer", r"(?i)reverse|rev\b"),
            reagent("polymerase", r"(?i)polymerase|taq|enzyme"),
            reagent("dntp", r"(?i)dntp"),
            reagent("buffer", r"(?i)buffer"),
            reagent("water", WATER),
        ],
        [
            variant(
                "48 reactions",
                "the request does not say which wells",
                groups=[group("reactions", members, order_hint="index")],
            )
        ],
        notes=[
            "0.25 ul of polymerase and 0.5 ul of dNTPs are below any OT-2 pipette: a master mix "
            "is the only way; after ideal mixing each well still resolves to the listed amounts."
        ],
    )


HARD_CHERRY_01_SOURCES = [
    "A1",
    "B2",
    "C3",
    "D4",
    "E5",
    "F6",
    "G7",
    "H8",
    "I9",
    "J10",
    "K11",
    "L12",
    "M13",
    "N14",
    "O15",
    "P16",
    "A17",
    "B18",
    "C19",
    "D20",
    "E21",
    "F22",
    "G23",
    "H24",
]


def hard_cherry_01() -> Map:
    variants = []
    for name, order in (
        ("down the column (A1, B1, ...)", WELLS_BY_COLUMN),
        ("along the row (A1, A2, ...)", WELLS_BY_ROW),
    ):
        pinned = {
            dest: {f"source@{src}": 2, "mix": 18}
            for src, dest in zip(HARD_CHERRY_01_SOURCES, order, strict=False)
        }
        variants.append(variant(name, "'consecutive' can be read either way", pinned=pinned))
    return platemap(
        [reagent("mix", MIX), by_well("source", r".+")],
        variants,
        notes=["The source is a 384-well plate; its well names run to P24."],
    )


def hard_mic_01() -> Map:
    variants = []
    for remove_excess in (True, False):
        series = serial_dilution(10, 50, 2, first_is_neat=False, remove_excess=remove_excess)
        pinned = {}
        for a, row in enumerate("AB", start=1):
            for k, (stock_ul, broth_ul) in enumerate(series):
                pinned[f"{row}{k + 1}"] = rounded(
                    {f"antibiotic_{a}": stock_ul, "broth": broth_ul, "culture": 50}
                )
            pinned[f"{row}11"] = {"broth": 50, "culture": 50}
            pinned[f"{row}12"] = {"broth": 100}
        last = (
            "excess removed from column 10" if remove_excess else "column 10 keeps its extra 50 ul"
        )
        variants.append(
            variant(f"rows A and B; {last}", "the request pins every position", pinned=pinned)
        )
    return platemap(
        [
            samples("antibiotic", r"(?i)(?:antibiotic|abx|drug|compound)\D{0,12}?(\d+)", 2),
            reagent("broth", r"(?i)broth|mueller|mhb|medium|media"),
            reagent("culture", r"(?i)culture|bacteria|inoculum|cells"),
        ],
        variants,
        notes=[
            "Column 1 is 1:2 of the stock in 50 ul of broth; each later column halves it.",
            "Ambiguous: '50 ul per well' holds in column 10 only if its extra 50 ul is removed.",
        ],
    )


def hard_rt_01() -> Map:
    with_rt = [
        {"buffer": 4, "rt": 1, "dntp": 1, "primers": 1, f"rna_{i}": 8, "water": 5}
        for i in range(1, 13)
    ]
    without = [
        {"buffer": 4, "dntp": 1, "primers": 1, f"rna_{i}": 8, "water": 6} for i in range(1, 13)
    ]
    return platemap(
        [
            reagent("buffer", r"(?i)buffer"),
            reagent("rt", r"(?i)reverse transcriptase|\brt\b|rtase|enzyme"),
            reagent("dntp", r"(?i)dntp"),
            reagent("primers", r"(?i)primer"),
            samples("rna", r"(?i)(?:rna|sample)\D{0,12}?(\d+)", 12),
            reagent("water", WATER),
        ],
        [
            variant(
                "12 reactions and 12 no-RT controls",
                "the request does not say which wells",
                groups=[
                    group("reactions", with_rt, order_hint="index"),
                    group("no-RT controls", without, order_hint="index"),
                ],
            )
        ],
        notes=["The twelve no-RT wells are part of the map: a plate without them does not verify."],
    )


BUILDERS: dict[str, Callable[[], Map]] = {
    "hard-dil-01": hard_dil_01,
    "hard-pool-01": hard_pool_01,
    "hard-qpcr-01": hard_qpcr_01,
    "hard-dil-02": hard_dil_02,
    "hard-norm-01": hard_norm_01,
    "hard-clone-01": hard_clone_01,
    "hard-pcr-01": hard_pcr_01,
    "hard-elisa-01": hard_elisa_01,
    "hard-cell-01": hard_cell_01,
    "hard-bca-01": hard_bca_01,
    "hard-pcr-02": hard_pcr_02,
    "hard-pcr-03": hard_pcr_03,
    "hard-cherry-01": hard_cherry_01,
    "hard-mic-01": hard_mic_01,
    "hard-rt-01": hard_rt_01,
}


def build_all() -> dict[str, Map]:
    requests = {}
    for line in REQUESTS.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            requests[row["id"]] = row
    return {
        request_id: {
            "id": request_id,
            "request": requests[request_id]["request"],
            "technique": requests[request_id]["technique"],  # what LABWARE-FOR-TECHNIQUE reads
            **builder(),
        }
        for request_id, builder in BUILDERS.items()
    }


def main() -> None:
    for request_id, content in build_all().items():
        path = HERE / f"{request_id}.json"
        path.write_text(json.dumps(content, indent=1) + "\n", encoding="utf-8")
        print(f"wrote {path.name}: {len(content['variants'])} variant(s)")


if __name__ == "__main__":
    main()
