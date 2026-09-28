"""Is this text a request for a liquid-handling run at all? Asked before any model is called.

The gate is deliberately generous: it refuses only text with no lab word and no amount in
it ("What is the purpose of life?", "hello"), so a real request is never turned away, and the
page still offers to send it anyway. Anything that passes goes to the planner, which may itself
say the text is not a request (`provette.planner.tools`, `not_a_request`).

Measured on every request on file (`eval/requests/`, `eval/requests-hard/`): all pass
(`tests/planner/test_gate.py`).
"""

from __future__ import annotations

import re

# an amount: a number and a unit a bench uses (5 ul, 1.5 ml, 10 ng/ul, 2x, 50%, 1:2)
_AMOUNT = re.compile(
    r"\d\s*(?:µl|μl|ul|ml|nl|l\b|ng|µg|μg|ug|mg|g\b|mm\b|µm|μm|um\b|nm\b|m\b|x\b|%|°c|c\b)"
    r"|\d\s*:\s*\d",
    re.IGNORECASE,
)

# word stems a liquid-handling request uses; one is enough
_LAB_WORDS = (
    "well", "plate", "tube", "rack", "reservoir", "trough", "tip", "pipet", "labware", "deck",
    "robot", "opentrons", "ot-2", "ot2", "flex", "protocol",
    "sample", "reagent", "buffer", "stock", "diluent", "dilut", "serial", "mix", "master",
    "aliquot", "transfer", "dispense", "aspirat", "pool", "normali", "titrat", "gradient",
    "replicate", "duplicate", "triplicate", "blank", "control", "standard", "column", "row",
    "pcr", "elisa", "bradford", "bca", "assay", "reaction", "cycler", "incubat", "heat",
    "magnet", "bead", "wash", "elut", "lysis", "lysate", "lyse", "extract", "digest", "ligat",
    "dna", "rna", "cdna", "protein", "primer", "oligo", "template", "enzyme", "polymerase",
    "antibod", "substrate", "dye", "stain", "pbs", "water", "medium", "media", "broth", "agar",
    "cell", "culture", "colon", "bacteri", "yeast", "serum", "plasma", "blood", "library",
    "plasmid", "drug", "compound", "inhibitor", "microlit", "millilit", "microl", "volume",
    "blot", "gel", "load", "lane", "seed", "passag", "transfect", "sequenc", "kit", "vial",
    "flask", "falcon", "eppendorf", "cuvette", "vortex", "centrifug", "spin", "thaw",
    "resuspend", "harvest", "stamp", "cherry", "pick", "screen", "dose", "concentrat", "molar",
    "ethanol", "glycerol", "tris", "edta", "dmso", "saline", "trypsin", "fbs", "sds", "lb",
    "qpcr", "rt-", "cfu", "od", "absorbance", "fluoresc", "luminesc", "reader", "spot",
)  # fmt: skip
_WORD = re.compile(r"[a-zµμ0-9-]+", re.IGNORECASE)


def looks_like_lab_request(text: str) -> bool:
    """True unless the text has no amount and no lab word in it."""
    if _AMOUNT.search(text):
        return True
    words = [w.lower() for w in _WORD.findall(text)]
    return any(w.startswith(stem) for w in words for stem in _LAB_WORDS) or any(
        stem in w for w in words for stem in ("well", "plate", "pcr", "elisa", "dna", "rna")
    )


NOT_A_REQUEST = (
    "This does not read as a liquid-handling request: it names no liquid, labware or volume. "
    "Say what should end up in each well, for example “8 PCR reactions, 20 µl master mix and "
    "5 µl sample each, in a 96-well PCR plate”."
)
