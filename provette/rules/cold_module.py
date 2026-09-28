"""COLD-MODULE-NEVER-SET: a temperature module was loaded but never set.

In words. A temperature module is at room temperature until the protocol calls
`set_temperature`, which waits until the block gets there. Authors load one because the request
said "on a cold block" or "at 4 C", put the enzyme or the cells on it, and forget the call; the
robot then runs the whole protocol with the module off. The person setting up the deck sees a
module and assumes it is cold. Every enzyme datasheet says set up on ice or on a cold block; a
module that is loaded and never set is the exact opposite of what the author meant.

One finding per labware on a temperature module, a warning, anchored at the first aspirate from
or dispense into that labware that happens before any `set_temperature` for its module: never, or
only after the liquids had already been used and then to a cold setting, 10 C or below. The
finding names the liquids that were on the labware by then.

A later warm setting is a different thing. When the tubes are used first and the module is then
set to 37 C or so, the author meant to build the reactions at room temperature and warm them
afterwards: an incubation, planned and written down. That is not a forgotten cold call, so the
rule stays silent on it. Over the public library, 12 of the 16 protocols that set the module
only after using it set it warm, and every one of them was an incubation of this kind.

It does not fire on a module set before the first use of anything on it, at any temperature; on
a module used first and then set warm, above 10 C; on a module with nothing on it, or with labware
nobody pipettes from or into; on a thermocycler (its block is set by a profile); or on a
heater-shaker (nothing is meant to be held cold on it).

The catalogue (docs/detection-catalogue.md, rule 3) also specifies an error, `asked_and_absent`:
the request put a source on a cold block and no module is loaded, or the one loaded is never
set. That needs a field on the plate map that does not exist yet (`sources: [{liquid, cold}]`),
so it is not built here; the warning stands alone until the map carries it.
"""

from __future__ import annotations

from dataclasses import dataclass

from provette.model import Event, Labware, Trace, WellKey
from provette.rules import sources
from provette.rules.common import Facts, facts_of, listing, times, well_listing
from provette.rules.finding import Downstream, Finding
from provette.rules.rule import Rule
from provette.state import Run

RULE_ID = "COLD-MODULE-NEVER-SET"
TITLE = "A temperature module was loaded but never set"
TEMPERATURE_MODULE = "temperaturemodule"  # the model string starts with this: V1, V2
COLD_CELSIUS = 10.0  # a later setpoint at or below this is a cold block set late; above, warming


@dataclass(frozen=True)
class _Use:
    """One aspirate or dispense that touched labware on a temperature module."""

    event_index: int
    wells: tuple[WellKey, ...]


def check(trace: Trace, run: Run) -> list[Finding]:
    facts = facts_of(trace, run)
    on_module = [lw for lw in trace.deck.labware if _on_temperature_module(lw)]
    findings: list[Finding] = []
    for labware in on_module:
        first_set = _first_set(trace, labware)
        cutoff = first_set.index if first_set is not None else len(trace.events)
        uses = _uses(trace, labware, cutoff)
        if not uses:
            continue  # set before first use, or nobody pipettes from it
        if first_set is not None and not _cold(first_set):
            continue  # used first, then set warm: a planned incubation, not a forgotten cold call
        findings.append(_finding(facts, labware, uses, first_set))
    return findings


def _on_temperature_module(labware: Labware) -> bool:
    return labware.module is not None and labware.module.lower().startswith(TEMPERATURE_MODULE)


def _first_set(trace: Trace, labware: Labware) -> Event | None:
    """The first `set_temperature` for this labware's module, if any.

    The event names the labware when the module carried one at the time of the call; when it
    was set before the labware was loaded, only the module model is known, and that is matched.
    """
    for event in trace.events:
        if event.op != "set_temperature":
            continue
        if event.labware_id == labware.labware_id:
            return event
        if event.labware_id is None and event.module == labware.module:
            return event
    return None


def _cold(set_event: Event) -> bool:
    """Whether a `set_temperature` asks for a cold block: a known setpoint of 10 C or below."""
    return set_event.celsius is not None and set_event.celsius <= COLD_CELSIUS


def _uses(trace: Trace, labware: Labware, cutoff: int) -> list[_Use]:
    uses: list[_Use] = []
    for event in trace.events[:cutoff]:
        if event.op not in ("aspirate", "dispense") or not event.volume_ul:
            continue
        wells = tuple(t.well for t in event.targets if t.well.labware_id == labware.labware_id)
        if wells:
            uses.append(_Use(event.index, wells))
    return uses


def _liquids(facts: Facts, labware: Labware, last_index: int) -> list[str]:
    """The declared liquids that were on the labware by `last_index`, by name and role."""
    named: dict[str, str | None] = {}
    for (well, liquid), since in facts.real_since.items():
        if well.labware_id != labware.labware_id or since > last_index:
            continue
        name = facts.liquid_name(liquid)
        if name is not None and name not in named:
            named[name] = facts.role(liquid)
    return [f"{name} ({role})" if role else name for name, role in sorted(named.items())]


def _finding(facts: Facts, labware: Labware, uses: list[_Use], first_set: Event | None) -> Finding:
    first = facts.event(uses[0].event_index)
    wells = facts.refs(w for use in uses for w in use.wells)
    liquids = _liquids(facts, labware, uses[-1].event_index)
    what = listing(liquids) if liquids else "liquids the protocol does not name"
    shown = f"{labware.label or labware.display_name} in slot {labware.slot}"
    verb = "draws from" if first.op == "aspirate" else "puts liquid into"
    if first_set is None:
        title = TITLE
        story = (
            f"At line {first.line} the robot {verb} {well_listing(wells)}, on a temperature "
            f"module that the protocol never sets. A temperature module stays at room "
            f"temperature until `set_temperature` is called, so {what} sat on a block that was "
            f"never cold; the robot pipetted there {times(len(uses))} over the run. The person "
            "setting up the deck sees a module and assumes it is cold."
        )
    else:
        celsius = f" to {first_set.celsius:g} C" if first_set.celsius is not None else ""
        title = "A temperature module was set only after its liquids were used"
        story = (
            f"At line {first.line} the robot {verb} {well_listing(wells)}, on a temperature "
            f"module that the protocol sets{celsius} only at line {first_set.line}, after "
            f"{what} had already been used: the robot pipetted there {times(len(uses))} before "
            "the call. A temperature module stays at room temperature until `set_temperature` "
            "is called, so every one of those transfers happened on a warm block."
        )
    return Finding(
        rule_id=RULE_ID,
        family=RULE.family,
        tier=RULE.tier,
        severity="warning",
        certain=True,
        roles_basis="none",
        title=title,
        explanation=story + f" Wells: {well_listing(wells)}.",
        fix=(
            f"Call `temp_module.set_temperature(4)` before the first transfer from {shown}, "
            "and `temp_module.deactivate()` at the end."
        ),
        line=first.line,
        stack=tuple(first.stack),
        occurrences=facts.occurrences(use.event_index for use in uses),
        wells=wells,
        downstream=Downstream(0, ()),
        sources=RULE.sources,
    )


RULE = Rule(
    rule_id=RULE_ID,
    family=8,
    tier="structural",
    title=TITLE,
    description=(
        "Labware sits on a temperature module, and liquid is drawn from or put into it before "
        "the protocol ever sets the module's temperature: the block is at room temperature "
        "until it is set. Warning, once per labware; if a cold setting (10 C or below) comes "
        "later, the "
        "finding says at which line. A module used first and then set warm is a planned "
        "incubation and is left alone, as are thermocyclers, heater-shakers and untouched labware."
    ),
    sources=(sources.OPENTRONS_TEMPERATURE_MODULE, sources.THERMO_T4_LIGASE, sources.NEB_Q5_MANUAL),
    check=check,
)
