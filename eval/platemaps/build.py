"""Write the plate maps: what each well should end up holding, from the request alone.

    env -u PYTHONPATH uv run python eval/platemaps/build.py

One small function per request, so the arithmetic (dilution series, normalisation volumes,
per-well totals) is code that can be read and tested, never typed by hand. The arithmetic itself
lives in `provette.calc`, the same functions the agent's tools call, so the expectation and the
model's numbers come from one place. Every map here was written from the text in
`eval/requests/requests.jsonl` BEFORE any protocol under `eval/checks/protocols/` was opened;
later widenings are marked `widened` in the variant that carries them, with the reason.

The format is documented in `provette/intent/spec.py`. In short:

* `liquids`: the logical liquids and how each binds to what a protocol declares. `bind` is
  "name" (one regex; every declared liquid it matches is that liquid), "indexed" (a regex whose
  capture group is the sample number: `sample_{i}`) or "well" (`stock@{well}` is whatever the
  protocol declares in that well of the source plate).
* `variants`: the readings of the request the map accepts. A protocol verifies if it matches
  any one of them. Each has `pinned` wells (position fixed by the request) and `groups`
  (N wells with these contents, anywhere, or anywhere `within` a set of wells).
* a content amount is microlitres of a STARTING liquid after ideal mixing, or "declared"
  (the well keeps the volume the protocol declared it with).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from provette.calc import dilution_series, normalise

HERE = Path(__file__).parent
REQUESTS = HERE.parent / "requests" / "requests.jsonl"

ROWS = "ABCDEFGH"
WELLS_BY_COLUMN = [f"{row}{col}" for col in range(1, 13) for row in ROWS]
WELLS_BY_ROW = [f"{row}{col}" for row in ROWS for col in range(1, 13)]

Map = dict[str, Any]
Contents = dict[str, Any]

WATER = r"(?i)water|h2o"
NUMBERED_SAMPLE = r"(?i)(?:sample|dna|template)\D{0,12}?(\d+)"


# ---------------------------------------------------------------------------------------------
# Small builders
# ---------------------------------------------------------------------------------------------


def reagent(name: str, pattern: str) -> Map:
    return {"name": name, "role": "reagent", "bind": "name", "pattern": pattern}


def samples(stem: str, pattern: str, count: int, index: str = "number") -> Map:
    """`index` "number": the capture group is the sample number and the number matters.
    "any": which sample is which does not change the expected plate (every sample is treated
    the same), so if the names carry no number the declared order is used."""
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


def group(
    name: str,
    members: list[Contents],
    *,
    within: list[str] | None = None,
    position: str = "free",
    order_hint: str | None = None,
) -> Map:
    return {
        "name": name,
        "members": members,
        "within": within,
        "position": position,
        "order_hint": order_hint,
    }


def variant(
    name: str,
    why: str,
    *,
    pinned: dict[str, Contents] | None = None,
    groups: list[Map] | None = None,
) -> Map:
    return {"name": name, "why": why, "pinned": pinned or {}, "groups": groups or []}


def platemap(
    liquids: list[Map],
    variants: list[Map],
    *,
    destination: Map | None = None,
    notes: list[str] | None = None,
) -> Map:
    return {
        "liquids": liquids,
        "destination": destination or {"select": "auto"},
        "variants": variants,
        "discard_intended": [],
        "notes": notes or [],
    }


def rounded(contents: Contents) -> Contents:
    return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in contents.items()}


# ---------------------------------------------------------------------------------------------
# Arithmetic: from provette.calc, the one source of truth the model's tools also use
# ---------------------------------------------------------------------------------------------


def serial_dilution(
    points: int, final_ul: float, factor: float, *, first_is_neat: bool, remove_excess: bool
) -> list[tuple[float, float]]:
    """(stock ul, diluent ul) in each well of a serial dilution, after the last step.

    `first_is_neat`: the first point is undiluted stock; otherwise it is already 1:factor.
    `remove_excess`: the last well's extra carry is taken out so it, too, holds `final_ul`.
    """
    series = dilution_series(1.0, points, factor, final_ul, first_is_neat, remove_excess)
    return [(point["stock_ul"], point["holds_ul"] - point["stock_ul"]) for point in series]


def normalisation(conc_ng_ul: float, target_ng_ul: float, final_ul: float) -> tuple[float, float]:
    """(sample ul, water ul) to bring a sample to `target_ng_ul` in `final_ul`."""
    row = normalise([conc_ng_ul], target_ng_ul, final_ul)[0]
    return row["sample_ul"], row["diluent_ul"]


# ---------------------------------------------------------------------------------------------
# One function per request
# ---------------------------------------------------------------------------------------------


def pcr_01() -> Map:
    members = [{"master_mix": 20, f"sample_{i}": 5} for i in range(1, 9)]
    return platemap(
        [
            reagent("master_mix", r"(?i)master\s*mix|mastermix"),
            samples("sample", NUMBERED_SAMPLE, 8),
        ],
        [
            variant(
                "8 reactions",
                "the request does not say which wells",
                groups=[group("reactions", members, order_hint="index")],
            )
        ],
    )


def pcr_02() -> Map:
    members = [{"master_mix": 12.5, "water": 10.5, f"sample_{i}": 2} for i in range(1, 25)]
    return platemap(
        [
            reagent("master_mix", r"(?i)master\s*mix|mastermix"),
            reagent("water", WATER),
            samples("sample", NUMBERED_SAMPLE, 24),
        ],
        [
            variant(
                "24 reactions",
                "the request does not say which wells",
                groups=[group("reactions", members, order_hint="index")],
            )
        ],
        notes=[
            "Master mix and water may be pooled on the deck first: after ideal mixing each "
            "well still resolves to 12.5 + 10.5 ul."
        ],
    )


def pcr_03() -> Map:
    pinned = {well: {"master_mix": 18, f"template@{well}": 2} for well in WELLS_BY_COLUMN}
    return platemap(
        [reagent("master_mix", r"(?i)master\s*mix|mastermix"), by_well("template", r".+")],
        [variant("full plate", "'matching well' pins every position", pinned=pinned)],
    )


def pcr_04() -> Map:
    members = [{"master_mix": 8, f"sample_{i}": 2} for i in range(1, 7) for _ in range(3)]
    return platemap(
        [
            reagent("master_mix", r"(?i)master\s*mix|mastermix|sybr"),
            samples("sample", r"(?i)(?:sample|cdna)\D{0,12}?(\d+)", 6),
        ],
        [
            variant(
                "6 samples x 3",
                "the request does not say which wells",
                groups=[group("reactions", members, order_hint="index")],
            )
        ],
    )


def pcr_06() -> Map:
    members = [{"pcr_mix": 20, f"colony_{i}": 1} for i in range(1, 17)]
    return platemap(
        [
            reagent("pcr_mix", r"(?i)\bmix\b|master"),
            samples("colony", r"(?i)(?:colony|resuspension|clone)\D{0,20}?(\d+)", 16),
        ],
        [
            variant(
                "16 reactions",
                "'16 wells of a PCR plate': which wells is free",
                groups=[group("reactions", members, order_hint="index")],
            )
        ],
    )


def pcr_07() -> Map:
    members = [
        {
            "buffer": 10,
            "polymerase": 0.5,
            "fwd_primer": 1,
            "rev_primer": 1,
            "water": 10.5,
            f"sample_{i}": 2,
        }
        for i in range(1, 13)
    ]
    return platemap(
        [
            samples("sample", NUMBERED_SAMPLE, 12),
            reagent("polymerase", r"(?i)polymerase|taq"),
            reagent("fwd_primer", r"(?i)forward|fwd"),
            reagent("rev_primer", r"(?i)reverse|rev\b"),
            reagent("water", WATER),
            reagent("buffer", r"(?i)buffer"),
        ],
        [
            variant(
                "12 reactions",
                "the request does not say which wells",
                groups=[group("reactions", members, order_hint="index")],
            )
        ],
        notes=[
            "0.5 ul is below what an OT-2 pipette can move alone, so a pooled master mix is "
            "expected; after ideal mixing each well still resolves to the listed amounts."
        ],
    )


def _row(
    row: str, series: list[tuple[float, float]], stock: str, diluent: str
) -> dict[str, Contents]:
    pinned = {}
    for k, (stock_ul, diluent_ul) in enumerate(series):
        contents = {stock: stock_ul}
        if diluent_ul > 1e-9:
            contents[diluent] = diluent_ul
        pinned[f"{row}{k + 1}"] = rounded(contents)
    return pinned


def dil_01() -> Map:
    variants = []
    for first_is_neat in (False, True):
        for remove_excess in (True, False):
            series = serial_dilution(
                12, 100, 2, first_is_neat=first_is_neat, remove_excess=remove_excess
            )
            first = "first point is neat stock" if first_is_neat else "first point is 1:2"
            last = (
                "excess removed from the last well" if remove_excess else "last well keeps 200 ul"
            )
            for row in ROWS:
                variants.append(
                    variant(
                        f"row {row}; {first}; {last}",
                        "'across one row' pins columns 1 to 12 of one row, not which row",
                        pinned=_row(row, series, "drug", "pbs"),
                    )
                )
    return platemap(
        [reagent("pbs", r"(?i)pbs|diluent|buffer"), reagent("drug", r"(?i)drug|stock|compound")],
        variants,
        notes=[
            "Ambiguous: whether the first of the 12 points is the undiluted stock or the first "
            "1:2 dilution. Both are accepted.",
            "Ambiguous: '100 ul final volume per well' is met in the last well only if the last "
            "100 ul is removed. A last well left at 200 ul is accepted (same concentration).",
            "Left to right is taken as pinned: column 1 is the most concentrated.",
        ],
    )


def dil_03() -> Map:
    variants = []
    for remove_excess in (True, False):
        series = serial_dilution(8, 50, 2, first_is_neat=True, remove_excess=remove_excess)
        members = []
        for bsa, water in series:
            contents = {"bsa": bsa}
            if water > 1e-9:
                contents["water"] = water
            members.append(rounded(contents))
        last = "excess removed from the last well" if remove_excess else "last well keeps 100 ul"
        variants.append(
            variant(
                f"8 standards; {last}",
                "'from 2 mg/ml down' makes the first point the neat stock",
                groups=[group("standards", members, order_hint="index")],
            )
        )
    return platemap(
        [reagent("water", WATER), reagent("bsa", r"(?i)bsa|stock|albumin")],
        variants,
        notes=[
            "Composition only: a curve made by direct dilution of each point gives the same "
            "wells as a serial one and is accepted.",
            "Ambiguous: '50 ul each' holds for the last well only if the excess 50 ul is "
            "removed. A last well left at 100 ul is accepted.",
        ],
    )


def elisa_01() -> Map:
    sera = [{f"serum_{i}": 100} for i in range(1, 41)]
    standards = [{f"standard_{i}": 100} for i in range(1, 9)]
    column_12 = [f"{row}12" for row in ROWS]
    return platemap(
        [
            samples("standard", r"(?i)(?:standard|std|calibrator)\D{0,12}?(\d+)", 8),
            samples("serum", r"(?i)(?:serum|sample)\D{0,12}?(\d+)", 40, index="any"),
        ],
        [
            variant(
                "40 sera + 8 standards",
                "'matching wells' and 'column 12' pin positions",
                groups=[
                    group("sera", sera, position="same_as_source"),
                    group("standards", standards, within=column_12, order_hint="index"),
                ],
            )
        ],
        destination={"select": "regex", "pattern": r"(?i)elisa|coated|assay"},
        notes=[
            "The request gives no volume for the standards; 100 ul, the same as the samples, is "
            "the only reading that gives a usable ELISA plate.",
            "Which 40 source wells hold serum is the protocol's choice; each must land in the "
            "well of the same name. Standard 1 in A12 down to standard 8 in H12 is a hint only.",
        ],
    )


def brad_01() -> Map:
    members = [{f"sample_{i}": 5, "bradford": 250} for i in range(1, 21) for _ in range(2)]
    standards = [{f"standard_{i}": "declared", "bradford": 250} for i in range(1, 9)]
    return platemap(
        [
            reagent("bradford", r"(?i)bradford|coomassie|dye reagent"),
            samples("standard", r"(?i)(?:standard|std|bsa)\D{0,12}?(\d+)", 8, index="any"),
            samples("sample", r"(?i)(?:sample|protein)\D{0,12}?(\d+)", 20),
        ],
        [
            variant(
                "40 sample wells + 8 standard wells",
                "positions are free",
                groups=[
                    group("samples", members, order_hint="index"),
                    group("standards", standards),
                ],
            )
        ],
        notes=[
            "The standards are 'already in the plate': each standard well must keep the "
            "volume the protocol declares for it and gain 250 ul of reagent."
        ],
    )


NORM_01_NG_UL = [
    85,
    120,
    44,
    67,
    210,
    95,
    33,
    150,
    78,
    60,
    101,
    55,
    190,
    72,
    48,
    130,
    88,
    25,
    64,
    110,
    39,
    175,
    92,
    58,
]


def norm_01() -> Map:
    members = []
    for i, conc in enumerate(NORM_01_NG_UL, start=1):
        sample, water = normalisation(conc, 10, 50)
        members.append(rounded({f"sample_{i}": sample, "water": water}))
    return platemap(
        [reagent("water", WATER), samples("sample", NUMBERED_SAMPLE, 24)],
        [
            variant(
                "24 normalised samples",
                "'a new plate': which wells is free",
                groups=[group("normalised", members, order_hint="index")],
            )
        ],
        notes=[
            "Sample i has the i-th concentration in the request. Volumes are exact "
            "(500 / concentration); a protocol that rounds to 0.1 ul is within tolerance."
        ],
    )


def pool_01() -> Map:
    pool = {f"library_{i}": 5 for i in range(1, 49)}
    return platemap(
        [samples("library", r"(?i)(?:library|lib|sample)\D{0,12}?(\d+)", 48, index="any")],
        [variant("one pool", "one tube, any position in its rack", groups=[group("pool", [pool])])],
        destination={"select": "auto"},
    )


CHERRY_01_SOURCES = ["B3", "C7", "D1", "A12", "H6", "E5", "F9", "G2", "B11", "C4"]


def cherry_01() -> Map:
    variants = []
    for name, order in (
        ("down the column (A1, B1, ...)", WELLS_BY_COLUMN),
        ("along the row (A1, A2, ...)", WELLS_BY_ROW),
    ):
        pinned = {
            dest: {f"source@{src}": 10} for src, dest in zip(CHERRY_01_SOURCES, order, strict=False)
        }
        variants.append(
            variant(
                name, "'consecutive wells starting at A1' can be read either way", pinned=pinned
            )
        )
    return platemap(
        [by_well("source", r".+")],
        variants,
        notes=[
            "Ambiguous: 'consecutive' is down the column in Opentrons' own well order and "
            "along the row for most people reading a plate. Both are accepted; the order of "
            "the picks is pinned in both."
        ],
    )


def fill_01() -> Map:
    pinned = {well: {"lb": 500, f"stock@{well}": 5} for well in WELLS_BY_COLUMN}
    return platemap(
        [
            reagent("lb", r"(?i)\blb\b|medium|media|broth"),
            by_well("stock", r"(?i)glycerol|stock|strain|clone"),
        ],
        [variant("full plate", "'matching well' pins every position", pinned=pinned)],
    )


def fill_02() -> Map:
    return platemap(
        [reagent("protein", r"(?i)protein|stock")],
        [
            variant(
                "48 aliquots",
                "which 48 positions of the block is free",
                groups=[group("aliquots", [{"protein": 50} for _ in range(48)])],
            )
        ],
    )


def prot_01() -> Map:
    members = [{f"sample_{i}": 15, "dye": 5} for i in range(1, 13)]
    return platemap(
        [
            reagent("dye", r"(?i)dye|loading|laemmli"),
            samples("sample", r"(?i)(?:sample|protein)\D{0,12}?(\d+)", 12),
        ],
        [
            variant(
                "12 gel samples",
                "the request does not say which wells",
                groups=[group("gel samples", members, order_hint="index")],
            )
        ],
    )


def clone_01() -> Map:
    members = [{"buffer": 2, "enzyme": 1, f"plasmid_{i}": 5, "water": 12} for i in range(1, 13)]
    return platemap(
        [
            samples("plasmid", r"(?i)(?:plasmid|dna|sample)\D{0,12}?(\d+)", 12),
            reagent("water", WATER),
            reagent("buffer", r"(?i)buffer"),
            reagent("enzyme", r"(?i)enzyme|ecori|bamhi|hindiii|restriction|nuclease"),
        ],
        [
            variant(
                "12 digests",
                "the request does not say which wells",
                groups=[group("digests", members, order_hint="index")],
            )
        ],
        notes=[
            "Buffer, enzyme and water may be pooled on the deck first; after ideal mixing "
            "each well still resolves to 2 + 1 + 12 ul."
        ],
    )


BUILDERS: dict[str, Callable[[], Map]] = {
    "pcr-01": pcr_01,
    "pcr-02": pcr_02,
    "pcr-03": pcr_03,
    "pcr-04": pcr_04,
    "pcr-06": pcr_06,
    "pcr-07": pcr_07,
    "dil-01": dil_01,
    "dil-03": dil_03,
    "elisa-01": elisa_01,
    "brad-01": brad_01,
    "norm-01": norm_01,
    "pool-01": pool_01,
    "cherry-01": cherry_01,
    "fill-01": fill_01,
    "fill-02": fill_02,
    "prot-01": prot_01,
    "clone-01": clone_01,
}


def build_all() -> dict[str, Map]:
    requests = {}
    for line in REQUESTS.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            requests[row["id"]] = row
    maps = {}
    for request_id, builder in BUILDERS.items():
        row = requests[request_id]
        maps[request_id] = {
            "id": request_id,
            "request": row["request"],
            "technique": row["technique"],  # what LABWARE-FOR-TECHNIQUE reads
            **builder(),
        }
    return maps


def main() -> None:
    for request_id, content in build_all().items():
        path = HERE / f"{request_id}.json"
        path.write_text(json.dumps(content, indent=1) + "\n", encoding="utf-8")
        print(f"wrote {path.name}: {len(content['variants'])} variant(s)")


if __name__ == "__main__":
    main()
