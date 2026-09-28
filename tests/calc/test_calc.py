"""provette.calc against the frozen plate maps and the numbers eval/platemaps/build.py wrote.

The plate maps on disk were written before any protocol was seen; they are the fixed point.
`build.py` now imports from provette.calc, so `tests/intent/test_platemaps.py` (every map on disk
is what build.py writes) is the other half of this check.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from provette.calc import dilution_series, master_mix, normalise

MAPS = Path(__file__).parents[2] / "eval" / "platemaps"


def _pinned(map_id: str, variant: str) -> dict[str, dict[str, float]]:
    content = json.loads((MAPS / f"{map_id}.json").read_text())
    return next(v["pinned"] for v in content["variants"] if v["name"] == variant)


def _members(map_id: str, variant: str) -> list[dict[str, float]]:
    content = json.loads((MAPS / f"{map_id}.json").read_text())
    return next(v["groups"][0]["members"] for v in content["variants"] if v["name"] == variant)


# -- dilution_series -----------------------------------------------------------------------------


def test_dil_01_first_point_is_1_to_2_excess_removed() -> None:
    """Row A of the frozen dil-01 map: the composition of each well is what the steps make."""
    pinned = _pinned("dil-01", "row A; first point is 1:2; excess removed from the last well")
    series = dilution_series(1.0, 12, 2, 100, first_point_is_stock=False, remove_excess=True)
    for point in series:
        expected = pinned[f"A{point['well_index']}"]
        assert point["stock_ul"] == pytest.approx(expected["drug"], abs=1e-4)
        assert point["holds_ul"] - point["stock_ul"] == pytest.approx(expected["pbs"], abs=1e-4)
        assert point["holds_ul"] == pytest.approx(100)
    assert series[0]["transfer_from"] == "stock"
    assert series[0]["diluent_ul"] == 100 and series[0]["transfer_in_ul"] == 100
    assert series[11]["transfer_out_ul"] == 100  # removed to waste


def test_dil_01_neat_first_point_last_well_kept() -> None:
    pinned = _pinned("dil-01", "row C; first point is neat stock; last well keeps 200 ul")
    series = dilution_series(1.0, 12, 2, 100, first_point_is_stock=True, remove_excess=False)
    assert series[0]["diluent_ul"] == 0 and series[0]["transfer_in_ul"] == 200
    assert (
        series[0]["stock_ul"] == pytest.approx(pinned["C1"]["drug"]) and "pbs" not in pinned["C1"]
    )
    assert series[11]["holds_ul"] == pytest.approx(200) and series[11]["transfer_out_ul"] == 0
    assert series[11]["stock_ul"] == pytest.approx(pinned["C12"]["drug"], abs=1e-4)


def test_dil_03_standard_curve_from_the_stock_down() -> None:
    members = _members("dil-03", "8 standards; excess removed from the last well")
    series = dilution_series(2.0, 8, 2, 50, first_point_is_stock=True)
    assert [p["concentration"] for p in series] == [2 / 2**k for k in range(8)]
    for point, expected in zip(series, members, strict=True):
        assert point["stock_ul"] == pytest.approx(expected["bsa"], abs=1e-4)
        assert point["holds_ul"] - point["stock_ul"] == pytest.approx(
            expected.get("water", 0), abs=1e-4
        )


def test_a_tenfold_series_is_the_180_plus_20_a_request_says() -> None:
    series = dilution_series(1.0, 6, 10, 180, first_point_is_stock=False)
    assert all(p["diluent_ul"] == 180 and p["transfer_in_ul"] == pytest.approx(20) for p in series)
    assert series[2]["dilution"] == "1:1000" and series[2]["concentration"] == pytest.approx(1e-3)


def test_the_stock_is_conserved() -> None:
    series = dilution_series(1.0, 8, 2, 50, first_point_is_stock=True, remove_excess=False)
    assert sum(p["stock_ul"] for p in series) == pytest.approx(100)  # 100 ul of stock went in


def test_dilution_series_refuses_nonsense() -> None:
    with pytest.raises(ValueError):
        dilution_series(1.0, 0, 2, 100, first_point_is_stock=True)
    with pytest.raises(ValueError):
        dilution_series(1.0, 4, 1, 100, first_point_is_stock=True)
    with pytest.raises(ValueError):
        dilution_series(1.0, 4, 2, 0, first_point_is_stock=True)


# -- normalise -----------------------------------------------------------------------------------


def test_norm_01_matches_the_frozen_map() -> None:
    concentrations = [85, 120, 44, 67, 210, 95, 33, 150, 78, 60, 101, 55, 190, 72, 48, 130, 88,
                      25, 64, 110, 39, 175, 92, 58]  # fmt: skip
    members = _members("norm-01", "24 normalised samples")
    rows = normalise(concentrations, 10, 50, min_pipette_ul=1)
    for row, expected in zip(rows, members, strict=True):
        assert row["sample_ul"] == pytest.approx(expected[f"sample_{row['index']}"], abs=1e-4)
        assert row["diluent_ul"] == pytest.approx(expected["water"], abs=1e-4)
        assert row["warning"] is None
        assert row["sample_ul"] * row["concentration"] == pytest.approx(500)


def test_normalise_warns_below_the_pipette_and_below_the_target() -> None:
    rows = normalise([210, 5], 10, 50, min_pipette_ul=2.5)
    assert rows[0]["sample_ul"] == pytest.approx(2.381, abs=1e-3)
    assert rows[0]["warning"] and "2.5 ul" in rows[0]["warning"]
    assert rows[1]["sample_ul"] == 50 and rows[1]["diluent_ul"] == 0
    assert rows[1]["warning"] and "below the target" in rows[1]["warning"]
    with pytest.raises(ValueError):
        normalise([0], 10, 50)


# -- master_mix ----------------------------------------------------------------------------------


def test_master_mix_for_pcr_07() -> None:
    mix = master_mix({"buffer": 10, "polymerase": 0.5, "fwd": 1, "rev": 1, "water": 10.5}, 12, 0.1)
    assert mix["per_reaction_ul"] == pytest.approx(23)
    assert mix["reactions_made"] == pytest.approx(13.2)
    by_name = {c["name"]: c["ul_to_pool"] for c in mix["components"]}
    assert by_name["polymerase"] == pytest.approx(6.6) and by_name["buffer"] == pytest.approx(132)
    assert mix["total_ul"] == pytest.approx(23 * 13.2)
    with pytest.raises(ValueError):
        master_mix({}, 8)
    with pytest.raises(ValueError):
        master_mix({"x": 1}, 0)
