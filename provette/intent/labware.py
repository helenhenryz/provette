"""LABWARE-FOR-TECHNIQUE: is the destination the right kind of plate for what was asked?

In words. A PCR reaction assembled in a flat culture plate cannot go into a thermocycler; an
ELISA in a PCR plate cannot be coated or read; an enzyme in a 15 ml reservoir is a millimetre
of liquid at room temperature. Opentrons raises nothing: "It's your responsibility to ensure
the labware and module combinations you load together work together." The plate map verifies
what each well holds, not what plate it is, so `select: auto` accepted a flat plate as the PCR
plate in three of Super's verified drafts (eval/agent). The request always says the technique,
and the technique decides the plate.

This is a verify component, not a rule in `RULES`: `provette check` has no plate map and so no
technique, and stays silent. The technique comes from the plate map (`technique`, copied from
the request by the planner); the class of a labware comes from its load name (`labware_class`
below). Two findings, both certain:

* **warning**, `wrong_destination`: once per destination labware (the one `compare` verified),
  when the technique's row of `TECHNIQUES` names a class the destination is not. The line is
  the first step that puts liquid into that labware.
* **note**, `reagent_in_trough`: a liquid whose name makes it a reagent (`roles.role_of`) or
  an add-last one (`roles.order_of`: enzyme, polymerase, ligase, master mix), never a carrier
  or a sample, declared in a reservoir, for a technique whose row says its reagents belong in
  tubes, when the request says "tube" or names a temperature. The line is the `load_liquid`.

What it does not fire on: a technique not in the table, or a map with no technique; a labware
whose load name says nothing (custom definitions); a reservoir holding a carrier (water, PBS,
buffer: that is what troughs are for); a labware the map does not call the destination.

The table is ours to extend: one row per technique word as `requests.jsonl` writes it.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Literal

from provette.intent.compare import IntentReport
from provette.intent.spec import PlateMap
from provette.model import Labware, LiquidLoad, Trace, WellKey
from provette.rules import sources
from provette.rules.finding import Downstream, Finding, Occurrence, WellRef, fingerprint
from provette.rules.roles import order_of, role_of
from provette.state.contact import surface_mm

RULE_ID = "LABWARE-FOR-TECHNIQUE"
FAMILY = 10  # labware for the technique; 9 is what a well holds and how deep it is
SOURCES = (sources.OPENTRONS_MODULE_SETUP, sources.OPENTRONS_THERMOCYCLER, sources.ABC_BENCH_2026)

LabwareClass = Literal["pcr", "flat", "deep", "reservoir", "tubes"]

# The load-name classifier. First match wins, so "aluminumblock_generic_pcr_strip" is PCR and
# "tuberack" is tubes; a name with none of these words is unclassed and the check says nothing.
_CLASSES: tuple[tuple[LabwareClass, tuple[str, ...]], ...] = (
    ("pcr", ("pcr", "strip", "aluminumblock_generic_pcr")),
    ("flat", ("flat",)),
    ("deep", ("deep",)),
    ("reservoir", ("reservoir",)),
    ("tubes", ("tuberack", "tube")),
)
_CLASS_WORDS: dict[str, str] = {
    "pcr": "a PCR plate or PCR strips",
    "flat": "a flat plate",
    "deep": "a deep-well plate",
    "reservoir": "a reservoir",
    "tubes": "a tube rack",
}


@dataclass(frozen=True)
class Need:
    """What one technique asks of the labware."""

    destination: tuple[LabwareClass, ...] | None  # None: any plate will do
    reagents_not_in: tuple[LabwareClass, ...] = ()  # where a reagent must not be declared


_PCR = Need(("pcr",), ("reservoir",))
_FLAT_OR_DEEP = Need(("flat", "deep"))
_ANY = Need(None)

# technique word (as requests.jsonl writes it, matched without case) -> what it needs
TECHNIQUES: dict[str, Need] = {
    "PCR setup": _PCR,
    "qPCR setup": _PCR,
    "Cloning": _PCR,
    "Transformation": _PCR,
    "Protein": _PCR,  # gel samples: sample plus loading dye, then heated
    "ELISA": _FLAT_OR_DEEP,
    "Bradford assay": _FLAT_OR_DEEP,
    "Protein assay": _FLAT_OR_DEEP,
    "Cell assay": _FLAT_OR_DEEP,
    "Cell culture": _FLAT_OR_DEEP,
    "Serial dilution": _ANY,
    "Normalization": _ANY,
    "Pooling": _ANY,
    "Cherrypicking": _ANY,
    "Plate filling": _ANY,
    "Bead cleanup": _ANY,
    "Nucleic acid extraction": _ANY,
}

# The request says its reagents are in tubes, or names a temperature ("at 4 C", "37 °C").
_TUBE_OR_TEMPERATURE = re.compile(r"\btubes?\b|\d\s*(?:°|º|deg(?:rees)?)?\s*C\b")


def labware_class(load_name: str) -> LabwareClass | None:
    """What kind of labware a load name describes, or None when the name says nothing."""
    lowered = load_name.lower()
    for kind, words in _CLASSES:
        if any(word in lowered for word in words):
            return kind
    return None


def need_of(technique: str | None) -> Need | None:
    """The table row for a technique word, matched without case; None when there is none."""
    if technique is None:
        return None
    wanted = technique.strip().lower()
    return next((need for word, need in TECHNIQUES.items() if word.lower() == wanted), None)


def labware_for_technique(
    trace: Trace,
    platemap: PlateMap,
    intent: IntentReport,
    source_lines: Sequence[str] | None = None,
) -> list[Finding]:
    """The findings of this check for one verification. Silent without a technique."""
    need = need_of(platemap.technique)
    if need is None or platemap.technique is None:
        return []
    labware = {lw.labware_id: lw for lw in trace.deck.labware}
    findings: list[Finding] = []
    destination = labware.get(intent.destination or "")
    if destination is not None and need.destination is not None:
        got = labware_class(destination.load_name)
        if got is not None and got not in need.destination:
            findings.append(
                _wrong_destination(trace, platemap.technique, need, destination, got, intent)
            )
    if need.reagents_not_in and _TUBE_OR_TEMPERATURE.search(platemap.request):
        for load in trace.deck.liquid_loads:
            lw = labware.get(load.well.labware_id)
            if lw is None or labware_class(lw.load_name) not in need.reagents_not_in:
                continue
            if not _is_add_last_reagent(load):
                continue
            findings.append(_reagent_in_trough(platemap.technique, load, lw))
    return [_fingerprinted(f, source_lines) for f in findings]


def _is_add_last_reagent(load: LiquidLoad) -> bool:
    """An enzyme, polymerase, ligase or master mix: a reagent by name that goes in last."""
    role = role_of(load.liquid_name, load.description)
    if role in ("carrier", "sample"):
        return False
    return order_of(load.liquid_name, load.description) == "last" or role == "reagent"


# ---------------------------------------------------------------------------------------------
# The two findings
# ---------------------------------------------------------------------------------------------


def _wrong_destination(
    trace: Trace,
    technique: str,
    need: Need,
    destination: Labware,
    got: LabwareClass,
    intent: IntentReport,
) -> Finding:
    assert need.destination is not None
    wanted = " or ".join(_CLASS_WORDS[kind] for kind in need.destination)
    shown = destination.label or destination.display_name
    first = next(
        (
            event
            for event in trace.events
            if event.op in ("dispense", "blow_out")
            and any(t.well.labware_id == destination.labware_id for t in event.targets)
        ),
        None,
    )
    wells = _refs(trace, destination, sorted({r.well for r in intent.wells if r.well}))
    return Finding(
        rule_id=RULE_ID,
        family=FAMILY,
        tier="structural",
        severity="warning",
        certain=True,
        roles_basis="none",
        title=(
            f"The wrong kind of plate: {shown} is {_CLASS_WORDS[got]}, and {technique} needs "
            f"{wanted}"
        ),
        explanation=(
            f"The plate map says the technique is {technique}, which needs {wanted} as its "
            f"destination. The protocol delivers into {shown} (slot {destination.slot}, load "
            f"name {destination.load_name}), which is {_CLASS_WORDS[got]}. "
            + _why(need.destination[0], got)
            + (
                " Every well still holds what the plate map asks for, so the map verifies; the "
                "plate is the problem."
                if intent.status == "verified"
                else " The plate map checks what each well holds, not what plate it is."
            )
        ),
        fix=_fix(need.destination[0], got),
        line=first.line if first else None,
        stack=tuple(first.stack) if first else (),
        occurrences=(Occurrence(first.index, first.line),) if first else (),
        wells=wells,
        downstream=Downstream(0, ()),
        sources=SOURCES,
    )


def _why(wanted: LabwareClass, got: LabwareClass) -> str:
    if wanted == "pcr":
        if got in ("flat", "deep"):
            return (
                "A thermocycler block is drilled for thin-walled 0.2 ml PCR wells; a "
                f"{'flat' if got == 'flat' else 'deep-well'} plate does not fit in it, so the "
                "reaction can never be run."
            )
        if got == "tubes":
            return (
                "A tube rack holds 1.5 ml or larger tubes, which do not fit a thermocycler "
                "block; PCR tubes or strips on the aluminium block do."
            )
        return "A reservoir is a trough, not a plate: nothing in it can be thermocycled."
    # wanted flat or deep
    if got == "pcr":
        return (
            "A plate reader reads a flat, clear-bottomed plate, and an ELISA plate is coated "
            "before the samples arrive; a PCR plate is neither coated nor readable, and its "
            "thin-walled conical wells hold little and are meant for a thermocycler."
        )
    return (
        "A plate reader reads a 96-well plate; a reservoir or a tube rack cannot be put in it, "
        "so nothing here can be measured."
    )


def _fix(wanted: LabwareClass, got: LabwareClass) -> str:
    if wanted == "pcr":
        return (
            "Load nest_96_wellplate_100ul_pcr_full_skirt (or the 200 ul PCR plate, or PCR "
            f"strips on the aluminium block) as the destination; {_CLASS_WORDS[got]} cannot go "
            "in a thermocycler."
        )
    return (
        "Load a flat plate (corning_96_wellplate_360ul_flat or nest_96_wellplate_200ul_flat) as "
        "the destination: it is what a plate reader reads and what an assay or a culture is "
        "done in."
    )


def _reagent_in_trough(technique: str, load: LiquidLoad, lw: Labware) -> Finding:
    shown = lw.label or lw.display_name
    ref = WellRef(lw.labware_id, load.well.well, lw.slot, shown, load.liquid_name)
    depth = surface_mm(lw.wells.get(load.well.well), load.volume_ul)
    how_deep = f"{depth:.1f} mm deep" if depth is not None else "a thin film"
    return Finding(
        rule_id=RULE_ID,
        family=FAMILY,
        tier="role",
        severity="note",
        certain=True,
        roles_basis="declared",
        title=f"{load.liquid_name} is declared in a reservoir channel, not a tube",
        explanation=(
            f"Line {load.line} declares {load.volume_ul:g} ul of {load.liquid_name} in channel "
            f"{load.well.well} of {shown} (slot {lw.slot}, load name {lw.load_name}). The request "
            f"({technique}) puts its reagents in tubes, or at a temperature, and a "
            f"reservoir channel is neither: {load.volume_ul:g} ul spread over the channel is "
            f"{how_deep}, open to the air and at room temperature, so it warms and evaporates "
            "while the run goes on, and the tip may not reach it."
        ),
        fix=(
            f"Put {load.liquid_name} in a tube on the block (a tube rack, or a temperature "
            "module with a tube block), not in a reservoir channel."
        ),
        line=load.line,
        stack=(),
        occurrences=(),
        wells=(ref,),
        downstream=Downstream(0, ()),
        sources=SOURCES,
    )


# ---------------------------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------------------------


def _refs(trace: Trace, lw: Labware, wells: Sequence[str]) -> tuple[WellRef, ...]:
    declared = {load.well: load.liquid_name for load in trace.deck.liquid_loads if load.liquid_name}
    shown = lw.label or lw.display_name
    return tuple(
        WellRef(lw.labware_id, well, lw.slot, shown, declared.get(WellKey(lw.labware_id, well)))
        for well in wells
    )


def _fingerprinted(finding: Finding, source_lines: Sequence[str] | None) -> Finding:
    return replace(finding, fingerprint=fingerprint(finding, source_lines))
