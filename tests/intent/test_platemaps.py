"""The arithmetic of eval/platemaps/build.py, and that every written map is a valid plate map."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from provette.intent.spec import PlateMapError, dump_platemap, load_platemap, platemap_from_dict

MAPS = Path(__file__).parents[2] / "eval" / "platemaps"
_spec = importlib.util.spec_from_file_location("platemap_build", MAPS / "build.py")
assert _spec and _spec.loader
build = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build)


def test_serial_dilution_halves_and_keeps_the_final_volume() -> None:
    wells = build.serial_dilution(12, 100, 2, first_is_neat=True, remove_excess=True)
    assert wells[0] == (100, 0) and wells[1] == (50, 50)
    assert wells[11][0] == pytest.approx(100 / 2**11)
    assert all(stock + diluent == pytest.approx(100) for stock, diluent in wells)
    kept = build.serial_dilution(12, 100, 2, first_is_neat=False, remove_excess=False)
    assert kept[0] == (50, 50) and sum(kept[11]) == pytest.approx(200)
    tenfold = build.serial_dilution(3, 180, 10, first_is_neat=False, remove_excess=True)
    assert tenfold[0] == pytest.approx((18, 162))


def test_a_serial_dilution_conserves_the_stock() -> None:
    wells = build.serial_dilution(8, 50, 2, first_is_neat=True, remove_excess=False)
    assert sum(stock for stock, _ in wells) == pytest.approx(100)  # 100 ul of stock went in


def test_normalisation() -> None:
    sample, water = build.normalisation(210, 10, 50)
    assert sample == pytest.approx(2.381, abs=1e-3) and sample + water == pytest.approx(50)
    assert sample * 210 == pytest.approx(10 * 50)


def test_every_map_on_disk_is_what_build_py_writes_and_is_valid() -> None:
    built = build.build_all()
    assert len(built) == 17
    for request_id, content in built.items():
        path = MAPS / f"{request_id}.json"
        assert json.loads(path.read_text()) == json.loads(json.dumps(content)), request_id
        platemap = load_platemap(path)
        assert platemap_from_dict(dump_platemap(platemap)) == platemap


def _pcr_with(contents: dict[str, float]) -> dict:  # type: ignore[type-arg]
    row = json.loads((MAPS / "pcr-01.json").read_text(encoding="utf-8"))
    row["variants"][0]["groups"][0]["members"][0] = contents
    return row


def test_an_unknown_liquid_is_refused_naming_the_declared_ones_and_the_fix() -> None:
    """The refusal a planner reads back: which liquids the map declares, and, for a name shaped
    like a by-well or an indexed liquid, the one sentence that makes it valid."""
    with pytest.raises(PlateMapError) as by_well:
        platemap_from_dict(_pcr_with({"master_mix": 20, "template@A1": 5}))
    text = str(by_well.value)
    assert text.startswith("variant '8 reactions', group 'reactions': 'template@A1' is not one of")
    assert "(declared: 'master_mix', 'sample_{i}')" in text
    assert text.endswith("declare 'template@{well}' in `liquids` with bind 'well'.")
    with pytest.raises(PlateMapError) as indexed:
        platemap_from_dict(_pcr_with({"master_mix": 20, "serum_3": 5}))
    assert str(indexed.value).endswith("declare 'serum_{i}' in `liquids` with bind 'indexed'.")
    with pytest.raises(PlateMapError) as plain:
        platemap_from_dict(_pcr_with({"master_mix": 20, "water": 5}))
    text = str(plain.value)
    assert "'water' is not one of the map's liquids (declared: 'master_mix', 'sample_{i}')." in text
    assert "To use it" not in text  # no shape to suggest a bind from
