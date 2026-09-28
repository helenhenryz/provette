"""A serial dilution: the same volume of diluent in every well, and a carry from well to well.

The arithmetic, in the words a student would use. Every well must end up holding
`final_volume_ul`. Each well is made up to a little more than that, so that it can give some
away to the next well and still hold the final volume:

    carry = final / (factor - 1)      the volume passed from one well to the next
    made  = final + carry             what a well holds just after the carry arrives

For a 1:2 series of 100 ul, carry is 100 and each well is made up to 200. For a 1:10 series of
180 ul, carry is 20 and each well is made up to 200 (the "180 + 20" a request would say).

The diluent in every well is `made - carry`, which is always `final_volume_ul`. The first well
takes its carry from the stock tube; the others from the well before them. The last well gives
nothing away, so it holds `made` unless its excess `carry` is removed to leave it at `final`.
"""

from __future__ import annotations

from typing import TypedDict


class DilutionPoint(TypedDict):
    """One well of the series, in the order the liquid moves."""

    well_index: int  # 1 is the most concentrated
    diluent_ul: float  # add this much diluent to the well first
    transfer_in_ul: float  # then move this much in, from `transfer_from`, and mix
    transfer_from: str  # "stock" for the first well, else "well <index - 1>"
    transfer_out_ul: float  # what leaves this well for the next (0 for the last, unless removed)
    holds_ul: float  # what the well holds at the end
    stock_ul: float  # of which, this much is the original stock (after ideal mixing)
    concentration: float  # in the stock's own unit
    dilution: str  # "1:1" neat, "1:2", "1:4", ...
    note: str


def dilution_series(
    stock_concentration: float,
    points: int,
    factor: float,
    final_volume_ul: float,
    first_point_is_stock: bool,
    remove_excess: bool = True,
) -> list[DilutionPoint]:
    """What to put in each well of a serial dilution, and what each well then holds.

    `first_point_is_stock`: the first well holds undiluted stock (a standard curve "from 2 mg/ml
    down"); otherwise the first well is already diluted 1:factor. `remove_excess`: the last
    well's extra carry is taken out, so every well holds `final_volume_ul`; otherwise the last
    well is left holding more, at the same concentration.
    """
    if points < 1:
        raise ValueError("a dilution series needs at least one point")
    if factor <= 1:
        raise ValueError("the dilution factor must be above 1 (2 means 1:2, 10 means 1:10)")
    if final_volume_ul <= 0:
        raise ValueError("the final volume per well must be above 0 ul")
    carry = final_volume_ul / (factor - 1)
    made = final_volume_ul + carry
    series: list[DilutionPoint] = []
    for k in range(points):
        index = k + 1
        last = index == points
        dilution = factor ** (k if first_point_is_stock else k + 1)
        if index == 1 and first_point_is_stock:
            diluent, transfer_in = 0.0, made
        else:
            diluent, transfer_in = final_volume_ul, carry
        transfer_out = 0.0 if last and not remove_excess else carry
        holds = made - transfer_out
        if index == 1 and first_point_is_stock:
            note = f"undiluted stock: {_ul(made)} of stock straight from the tube"
        elif index == 1:
            note = f"{_ul(diluent)} diluent, then {_ul(transfer_in)} of stock; mix"
        else:
            note = f"{_ul(diluent)} diluent, then {_ul(transfer_in)} from well {index - 1}; mix"
        if last:
            note += (
                f"; last well: remove {_ul(carry)} to waste so it holds {_ul(holds)}"
                if remove_excess
                else f"; last well: nothing moves on, so it holds {_ul(holds)}"
            )
        series.append(
            DilutionPoint(
                well_index=index,
                diluent_ul=diluent,
                transfer_in_ul=transfer_in,
                transfer_from="stock" if index == 1 else f"well {index - 1}",
                transfer_out_ul=transfer_out,
                holds_ul=holds,
                stock_ul=holds / dilution,
                concentration=stock_concentration / dilution,
                dilution=f"1:{dilution:g}",
                note=note,
            )
        )
    return series


def _ul(volume: float) -> str:
    return f"{volume:.2f}".rstrip("0").rstrip(".") + " ul"
