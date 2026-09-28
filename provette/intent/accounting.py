"""Sample accounting: where did every declared liquid end up?

For each liquid the protocol declares: how much reached the wells the plate map wants it in,
how much is still in its own tube, how much sits in other wells, and how much is LOST: thrown
away inside a tip or blown out into the trash. A sample that is lost, or that ends in a well the
map does not list, is flagged. Reagents get a note only: a little spare master mix thrown away
with the tip is normal practice.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from provette.intent.compare import REAL_UL, IntentReport
from provette.intent.spec import PlateMap
from provette.model import Trace, WellKey
from provette.state import Run

# The replay loses nothing to rounding, so anything above this is liquid really thrown away.
LOST_ALLOWANCE_UL = 0.05
# A sample that loses LESS THAN ONE DOSE (the smallest amount the plate map wants of it in one
# well) gets a note, not a flag: that is the spare microlitre drawn so that the last of several
# dispenses is a full one, and it is thrown away on purpose (the correct protocol
# eval/checks/protocols/short-on-tips/pcr-04.py draws 3 x 2 + 1 ul of each cDNA). A whole
# dose or more in the trash is a sample that went missing.


@dataclass(frozen=True)
class LiquidAccount:
    logical: str | None  # the plate map's name for it, if bound
    name: str  # the protocol's name for it
    role: Literal["sample", "reagent", "unbound"]
    sources: tuple[WellKey, ...]
    declared_ul: float
    delivered_ul: float  # in wells where the map expects this liquid
    left_in_source_ul: float
    elsewhere: tuple[tuple[WellKey, float], ...]  # other wells on the deck
    trash_ul: float  # dispensed or blown out into the trash
    lost_ul: float  # declared minus everything still in a well; includes `trash_ul`
    flags: tuple[str, ...]  # sentences; a flag fails the verification
    notes: tuple[str, ...]


@dataclass(frozen=True)
class Accounting:
    liquids: tuple[LiquidAccount, ...]

    @property
    def flagged(self) -> tuple[LiquidAccount, ...]:
        return tuple(liquid for liquid in self.liquids if liquid.flags)


def account(trace: Trace, run: Run, platemap: PlateMap, report: IntentReport) -> Accounting:
    trash = {lw.labware_id for lw in trace.deck.labware if not lw.wells}
    groups: dict[str, list[WellKey]] = {}
    for atom, origin in run.origins.items():
        if origin.kind != "declared" or not origin.liquid_name:
            continue
        logical = report.binding.logical_of.get(atom)
        groups.setdefault(logical or f"[{origin.liquid_name}]", []).append(atom)

    where: dict[WellKey, dict[WellKey, float]] = {}  # atom -> well -> ul
    for key, state in run.wells.items():
        for atom, presence in state.atoms.items():
            if presence.volume_ul is not None and presence.volume_ul > 0:
                where.setdefault(atom, {})[key] = presence.volume_ul

    accounts = []
    for label, atoms in groups.items():
        logical = label if not label.startswith("[") else None
        spec = platemap.spec_of(logical) if logical else None
        expected = report.expected_wells(logical) if logical else set()
        declared = sum(run.origins[a].initial_volume_ul or 0.0 for a in atoms)
        delivered = left = in_trash = 0.0
        elsewhere: dict[WellKey, float] = {}
        for atom in atoms:
            for key, volume in where.get(atom, {}).items():
                if key.labware_id in trash:
                    in_trash += volume
                elif key in atoms:
                    left += volume
                elif key.labware_id == report.destination and key.well in expected:
                    delivered += volume
                elif volume > REAL_UL:
                    elsewhere[key] = elsewhere.get(key, 0.0) + volume
                # a film under REAL_UL is neither delivered nor lost to anyone's eye
        lost = max(0.0, declared - delivered - left - sum(elsewhere.values()))
        role: Literal["sample", "reagent", "unbound"] = spec.role if spec else "unbound"
        name = " / ".join(dict.fromkeys(run.origins[a].liquid_name or "?" for a in atoms))
        dose = report.dose_ul(logical) if logical else None
        flags, notes = _judge(
            name, role, logical in platemap.discard_intended, lost, in_trash, elsewhere, dose
        )
        accounts.append(
            LiquidAccount(
                logical, name, role, tuple(atoms), declared, delivered, left,
                tuple(sorted(elsewhere.items())), in_trash, lost, tuple(flags), tuple(notes),
            )
        )  # fmt: skip
    return Accounting(tuple(accounts))


def _judge(
    name: str,
    role: str,
    discard_intended: bool,
    lost: float,
    in_trash: float,
    elsewhere: dict[WellKey, float],
    dose: float | None,
) -> tuple[list[str], list[str]]:
    flags: list[str] = []
    notes: list[str] = []
    if lost > LOST_ALLOWANCE_UL and not discard_intended:
        how = (
            f"{in_trash:.1f} ul of it was dispensed into the trash"
            if in_trash > LOST_ALLOWANCE_UL
            else "it left the deck inside a tip that was thrown away"
        )
        sentence = f"{lost:.1f} ul of {name} is lost: {how}."
        spare = dose is not None and lost < dose - LOST_ALLOWANCE_UL
        if spare:
            sentence += " That is less than one well's worth: a spare volume, if it was meant."
        (flags if role == "sample" and not spare else notes).append(sentence)
    if elsewhere:
        wells = ", ".join(f"{key.well} in slot {key.labware_id.split(':')[0]} ({ul:.1f} ul)"
                          for key, ul in sorted(elsewhere.items())[:6])  # fmt: skip
        more = f" and {len(elsewhere) - 6} more" if len(elsewhere) > 6 else ""
        sentence = f"{name} ends in wells the plate map does not list for it: {wells}{more}."
        (flags if role == "sample" else notes).append(sentence)
    return flags, notes
