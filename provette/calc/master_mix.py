"""A master mix: every component pooled once for all reactions, with a little extra.

Each component is multiplied by the number of reactions and by (1 + overage), so that the
pipetting losses of dispensing many times do not leave the last reaction short. The per-reaction
dispense volume is the sum of the components, without overage.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TypedDict


class Component(TypedDict):
    name: str
    ul_per_reaction: float
    ul_to_pool: float


class MasterMix(TypedDict):
    reactions: int
    overage_fraction: float
    reactions_made: float  # reactions * (1 + overage)
    components: list[Component]
    per_reaction_ul: float  # what to dispense into each reaction
    total_ul: float  # what the pooled tube holds


def master_mix(
    components: Mapping[str, float], reactions: int, overage_fraction: float = 0.1
) -> MasterMix:
    """How much of each component to pool for `reactions`, with `overage_fraction` extra."""
    if reactions < 1:
        raise ValueError("a master mix is for at least one reaction")
    if overage_fraction < 0:
        raise ValueError("the overage cannot be negative")
    if not components:
        raise ValueError("a master mix needs at least one component")
    made = reactions * (1 + overage_fraction)
    rows: list[Component] = []
    for name, per_reaction in components.items():
        if per_reaction <= 0:
            raise ValueError(f"{name}: a volume per reaction must be above 0")
        rows.append(
            Component(name=name, ul_per_reaction=per_reaction, ul_to_pool=per_reaction * made)
        )
    return MasterMix(
        reactions=reactions,
        overage_fraction=overage_fraction,
        reactions_made=made,
        components=rows,
        per_reaction_ul=sum(components.values()),
        total_ul=sum(row["ul_to_pool"] for row in rows),
    )
