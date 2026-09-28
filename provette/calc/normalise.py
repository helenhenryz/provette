"""Normalisation: bring every sample to the same concentration in the same final volume.

    sample_ul  = target * final_volume / concentration
    diluent_ul = final_volume - sample_ul

A sample below the target concentration cannot be brought up to it by diluting, and a sample
so concentrated that its volume falls under what the pipette can move cannot be pipetted
exactly. Both get a warning; the arithmetic is still returned so the protocol can say so.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TypedDict


class Normalised(TypedDict):
    index: int  # 1 is the first concentration given
    concentration: float
    sample_ul: float
    diluent_ul: float
    warning: str | None


def normalise(
    concentrations: Sequence[float],
    target: float,
    final_volume_ul: float,
    min_pipette_ul: float = 1.0,
) -> list[Normalised]:
    """Sample and diluent volumes that bring each sample to `target` in `final_volume_ul`.

    `concentrations` and `target` share one unit (ng/ul, mg/ml, ...). `min_pipette_ul` is the
    smallest volume the pipette in use can move (1 ul for a p20 on an OT-2).
    """
    if target <= 0 or final_volume_ul <= 0:
        raise ValueError("the target concentration and the final volume must be above 0")
    rows: list[Normalised] = []
    for index, concentration in enumerate(concentrations, start=1):
        if concentration <= 0:
            raise ValueError(f"sample {index}: a concentration must be above 0")
        sample = target * final_volume_ul / concentration
        warning: str | None = None
        if sample > final_volume_ul:
            sample = final_volume_ul
            warning = (
                f"sample {index} is at {concentration:g}, below the target {target:g}: "
                f"diluting cannot raise it. Use {final_volume_ul:g} ul of it neat, at "
                f"{concentration:g}, and say so."
            )
        elif sample < min_pipette_ul:
            warning = (
                f"sample {index} needs {sample:.2f} ul, below the {min_pipette_ul:g} ul the "
                "pipette can move: either dilute this sample first, or move "
                f"{min_pipette_ul:g} ul into a larger final volume ("
                f"{min_pipette_ul * concentration / target:.1f} ul in all)."
            )
        rows.append(
            Normalised(
                index=index,
                concentration=concentration,
                sample_ul=sample,
                diluent_ul=final_volume_ul - sample,
                warning=warning,
            )
        )
    return rows
