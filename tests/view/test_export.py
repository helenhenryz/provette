"""The exported data: the right events, real wells, and deltas that replay to the run's state.

The page's JavaScript rebuilds every well by applying deltas; `replay_deltas` does the same in
Python, so holding it to `run.wells` and `run.well_before` is the test that the page's logic is
right.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from provette.check import CheckResult
from provette.intent import load_platemap
from provette.intent.cli import verify_trace
from provette.model import WellKey
from provette.rules import run_rules
from provette.state import Run, replay
from provette.view import export, render, replay_deltas
from provette.view.export import _on_module, describe
from provette.view.geometry import Slot, grid
from tests.state.builder import ABOVE, FLAT, FLAT_ID, PCR, PLATE_ID, TraceBuilder, plate, tip, tube
from tests.view.conftest import PLATEMAPS, PROTOCOLS

FIXTURES = ["pcr_buggy.py", "pcr_clean.py"]
THREE_MB = 3 * 1024 * 1024


# ---------------------------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------------------------


def _bands(row: list[Any]) -> dict[int, tuple[float | None, int, int]]:
    return {band[0]: (band[1], band[2], band[3]) for band in row[2]}


def _expected(data: dict[str, Any], run: Run, well: WellKey, state: Any) -> tuple[Any, Any, Any]:
    index = {name: i for i, name in enumerate(data["wells"])}
    bands = {
        index[str(atom)]: (_r(p.volume_ul), 0 if p.mode == "bulk" else 1, 1 if p.certain else 0)
        for atom, p in state.atoms.items()
    }
    return _r(state.volume_ul), _r(state.min_volume_ul), bands


def _r(volume: float | None) -> float | None:
    """The page carries volumes to the nanolitre."""
    return None if volume is None else round(volume, 3)


def assert_state_matches(data: dict[str, Any], run: Run, position: int | None) -> None:
    """The deltas applied up to `position` equal `well_before(well, position)` for every well
    the run knows (`run.wells` when `position` is None)."""
    replayed = replay_deltas(data, position)["wells"]
    index = {name: i for i, name in enumerate(data["wells"])}
    for well in run.wells:
        state = run.wells[well] if position is None else run.well_before(well, position)
        if str(well) not in index:  # the run made a record of it but nothing ever reached it
            assert not state.atoms and not state.volume_ul, f"{well} is not in the page"
            continue
        row = replayed.get(str(index[str(well)]))
        if row is None:
            assert not state.atoms and not state.volume_ul, f"{well} missing at {position}"
            continue
        assert (row[0], row[1], _bands(row)) == _expected(data, run, well, state), (
            f"{well} at position {position}"
        )
    for key, row in replayed.items():
        if row[2] or row[0]:
            assert WellKey(*_split(data["wells"][int(key)])) in run.wells


def _split(name: str) -> tuple[str, str]:
    cut = name.rindex("[")
    return name[:cut], name[cut + 1 : -1]


def hand_built() -> CheckResult:
    """A PCR set-up on the fixed deck of tests/state/builder: one tip through four samples."""
    loads = {tube("A1"): ("PCR master mix", 200.0)}
    loads.update({tube(f"B{i}"): (f"sample {i}", 50.0) for i in range(1, 5)})
    b = TraceBuilder(loads)
    b.pick_up(tip("A1"))
    for i in range(1, 5):
        b.aspirate(tip("A1"), tube("A1"), 20)
        b.dispense(tip("A1"), plate(f"A{i}"), 20, height=ABOVE)
    b.drop(tip("A1"))
    b.pick_up(tip("A2"))
    for i in range(1, 5):
        b.aspirate(tip("A2"), tube(f"B{i}"), 5)
        b.dispense(tip("A2"), plate(f"A{i}"), 5)
    b.drop(tip("A2"), returned=True)
    b.pick_up(tip("A2"))
    b.aspirate(tip("A2"), tube("A1"), 10)
    b.dispense(tip("A2"), plate("H12"), 10)
    b.drop(tip("A2"))
    b.delay(30)
    trace = b.trace()
    run = replay(trace)
    source = tuple(f"line {n}" for n in range(1, len(trace.events) + 1))
    findings = tuple(run_rules(trace, run, source))
    return CheckResult(Path("hand_built.py"), source, findings, trace, run)


# ---------------------------------------------------------------------------------------------
# Hand-built: the schema, no simulator
# ---------------------------------------------------------------------------------------------


def test_schema_on_hand_built_trace() -> None:
    result = hand_built()
    data = export(result)
    assert data["schema_version"] == 4
    assert data["protocol"] == "hand_built.py"
    assert len(data["events"]) == len(result.trace.events) == len(data["deltas"])
    assert [e["i"] for e in data["events"]] == list(range(len(result.trace.events)))
    for event in data["events"]:
        assert set(event) == {
            "i", "op", "line", "parent", "t", "vol", "targets", "text", "held", "mount"
        }  # fmt: skip
        assert event["mount"] in ("left", "right", None)
        assert event["text"]
        assert len(event["held"]) == len(event["targets"])
    # After event 1 (aspirate 20 µl) the tip holds 20 µl; after event 2 (dispense) nothing.
    assert data["events"][1]["held"] == [20.0] and data["events"][2]["held"] == [0.0]
    # Every origin has a colour of its own and a plain name.
    colours = [o["colour"] for o in data["origins"]]
    assert len(set(colours)) == len(colours)
    assert all(re.fullmatch(r"#[0-9A-F]{6}", c) for c in colours)
    assert {o["name"] for o in data["origins"]} == {
        "PCR master mix", "sample 1", "sample 2", "sample 3", "sample 4"
    }  # fmt: skip
    # The plate and the tip rack are the real geometries, so the shipped definitions match. The
    # builder's tube rack has a diameter (8.7 mm) no shipped version has (10.2, 9.9): its wells
    # fall back to a grid, and the page says so.
    by_slot = {lw["slot"]: lw for lw in data["deck"]["labware"]}
    assert by_slot["1"]["measured"] and by_slot["3"]["measured"]
    assert not by_slot["2"]["measured"]
    assert len(by_slot["2"]["wells"]) == 24
    assert len(data["deck"]["slots"]) == 12
    assert data["deck"]["width"] > 390 and data["deck"]["height"] > 350
    # Findings carry the indices the page draws with.
    assert result.findings, "the one-tip set-up should give a finding"
    for finding in data["findings"]:
        assert finding["root_event"] == finding["occurrences"][0]["event_index"]
        assert len(finding["well_index"]) == len(finding["wells"])
        assert len(finding["downstream_index"]) == finding["downstream"]["count"]
    assert data["summary"]["check"].startswith("Provette found")
    assert data["summary"]["verify"] is None
    assert data["verify"] is None


def test_well_shape_is_exported_as_the_ledger_holds_it() -> None:
    """The page draws a well's liquid at the height the state computes with: the definition's
    word for the bottom and the volume-to-height table go out per well, as they are."""
    from dataclasses import replace

    result = hand_built()
    table = [(0.0, 0.0), (5.0, 2.1), (60.0, 7.4), (217.0, 14.78)]
    conical = replace(PCR, bottom_shape="v", height_at_ul=table)
    flat = replace(FLAT, bottom_shape="flat")
    reshaped = [
        replace(lw, wells={name: conical for name in lw.wells})
        if lw.labware_id == PLATE_ID
        else replace(lw, wells={name: flat for name in lw.wells})
        if lw.labware_id == FLAT_ID
        else lw
        for lw in result.trace.deck.labware
    ]
    trace = replace(result.trace, deck=replace(result.trace.deck, labware=reshaped))
    data = export(CheckResult(result.path, result.source_lines, (), trace, replay(trace)))
    by_slot = {lw["slot"]: lw for lw in data["deck"]["labware"]}
    well = by_slot["1"]["wells"]["A1"]
    assert well["bottom"] == "v"
    assert well["height_at_ul"] == [[v, h] for v, h in table]
    assert well["height_at_ul"][-1][0] == conical.brim_ul
    flat_well = by_slot["4"]["wells"]["A1"]
    assert flat_well["bottom"] == "flat" and flat_well["height_at_ul"] is None
    tube_well = by_slot["2"]["wells"]["A1"]  # the builder's tube says nothing about its bottom
    assert tube_well["bottom"] is None and tube_well["height_at_ul"] is None
    # the outline fields are as before
    assert set(well) == {"x", "y", "shape", "d", "w", "h", "depth", "max", "bottom", "height_at_ul"}


def test_hand_built_deltas_replay() -> None:
    result = hand_built()
    data = export(result)
    assert_state_matches(data, result.run, None)
    for position in range(len(result.trace.events) + 1):
        assert_state_matches(data, result.run, position)


def test_hand_built_racks_and_tips() -> None:
    result = hand_built()
    data = export(result)
    index = {name: i for i, name in enumerate(data["wells"])}
    a1, a2 = str(index[str(tip("A1"))]), str(index[str(tip("A2"))])
    final = replay_deltas(data)
    assert final["racks"][a1] == "gone"
    assert final["racks"][a2] == "gone"
    after_return = replay_deltas(data, 20)  # event 19 put the second tip back in its rack
    assert after_return["racks"][a2] == "parked"
    # The derived residue is the run's residue.
    for tip_key, state in result.run.tips.items():
        residue = final["tips"][str(index[str(tip_key)])]
        assert {atom for atom, _ in residue} == {index[str(a)] for a in state.residue}
        for atom, sure in residue:
            atom_key = WellKey(*_split(data["wells"][atom]))
            assert bool(sure) == state.residue[atom_key].certain
    # The parked tip kept its residue when it was picked up again (event 20).
    parked = after_return["tips"][a2]
    assert len(parked) >= 4  # the four samples, and the master mix it dipped into
    assert replay_deltas(data, 21)["tips"][a2] == parked


def test_event_words() -> None:
    result = hand_built()
    words = [describe(e, result.trace.deck) for e in result.trace.events]
    assert words[0] == "pick up tip A1 from the rack in slot 3"
    assert words[1] == "aspirate 20 µl from tube A1 in slot 2, tip A1"
    assert words[2] == "dispense 20 µl into well A1 in slot 1, tip A1"
    assert words[9] == "drop tip A1 in the trash"
    assert words[19] == "put tip A2 back in the rack"
    assert words[-1] == "wait 30 seconds"


def test_a_blank_comment_is_not_a_line() -> None:
    """The library's protocols print blank lines (`comment("\\n")`, 351 events in 120 of them):
    the page falls through to the raw op rather than showing nothing."""
    from dataclasses import replace

    result = hand_built()
    last = result.trace.events[-1]
    deck = result.trace.deck
    blank = replace(last, op="other", detail="\n", raw_op="command.COMMENT")
    assert describe(blank, deck) == "comment"
    said = replace(last, op="other", detail="  Engaging Magnetic Module ", raw_op="comment")
    assert describe(said, deck) == "Engaging Magnetic Module"


def test_grid_fallback_when_no_definition_matches() -> None:
    from tests.state.builder import PCR

    names = [f"{row}{col}" for row in "AB" for col in (1, 2, 3)]
    shape = grid({name: PCR for name in names}, 128.0, 86.0)
    assert not shape.measured
    assert set(shape.wells) == set(names)
    assert shape.wells["A1"].y > shape.wells["B1"].y  # row A is at the back (larger y)
    assert shape.wells["A1"].x < shape.wells["A2"].x < shape.wells["A3"].x
    for position in shape.wells.values():
        assert 0 < position.x < 128 and 0 < position.y < 86


def test_page_is_self_contained_hand_built() -> None:
    page = render(export(hand_built()))
    assert_self_contained(page)


def assert_self_contained(page: str) -> None:
    """No script, style, image or font comes from anywhere but the file itself. The findings'
    sources are URLs inside the data block, and are text, not loads."""
    without_data = re.sub(
        r'<script id="provette-data" type="application/json">.*?</script>', "", page, flags=re.S
    )
    urls = set(re.findall(r"https?://[^\s\"'<>)]+", without_data))
    assert urls <= {"http://www.w3.org/2000/svg"}, urls
    assert "<script src" not in page and "<link " not in page and "@import" not in page
    assert "fetch(" not in page and "XMLHttpRequest" not in page and "<img" not in page


def test_javascript_parses() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    js = Path(__file__).parents[2] / "provette" / "view" / "replay.js"
    done = subprocess.run([node, "--check", str(js)], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr


# ---------------------------------------------------------------------------------------------
# The fixture protocols through the simulator
# ---------------------------------------------------------------------------------------------


@pytest.mark.sim
@pytest.mark.parametrize("name", FIXTURES)
def test_fixture_export(name: str, checked: Callable[[Path], CheckResult]) -> None:
    result = checked(PROTOCOLS / name)
    data = export(result)
    assert len(data["events"]) == len(result.trace.events) == len(data["deltas"])
    # Every well the page names is on the deck (the trash has no wells: any name is allowed).
    labware = {lw["id"]: lw for lw in data["deck"]["labware"]}
    for row in data["wells"]:
        labware_id, well = _split(row)
        assert labware_id in labware, row
        assert well in labware[labware_id]["wells"] or labware[labware_id]["is_trash"], row
    assert all(lw["measured"] for lw in labware.values()), "a shipped definition did not match"
    assert_state_matches(data, result.run, None)
    n = len(result.trace.events)
    for position in {0, 1, 2, n // 3, n // 2, n - 1, n}:
        assert_state_matches(data, result.run, position)


@pytest.mark.sim
@pytest.mark.parametrize("name", FIXTURES)
def test_fixture_page(name: str, checked: Callable[[Path], CheckResult]) -> None:
    result = checked(PROTOCOLS / name)
    verification = verify_trace(result.trace, result.run, load_platemap(PLATEMAPS / "pcr-01.json"))
    page = render(export(result, verification))
    assert len(page.encode("utf-8")) < THREE_MB
    assert_self_contained(page)
    assert "Prep sheet" in page and "This checks the logic of the protocol" in page
    data = json.loads(
        re.search(
            r'<script id="provette-data" type="application/json">(.*?)</script>', page, re.S
        ).group(1)
    )
    assert data["verify"]["intent"]["status"] in ("verified", "mismatch")
    assert data["summary"]["verify"].split(":")[0] in ("VERIFIED", "MISMATCH")
    if name == "pcr_buggy.py":
        assert data["summary"]["counts"]["error"] >= 1
        assert "4 biology problems (2 errors, 2 notes)" in data["summary"]["check"]
    else:  # clean of contamination; the note is the missing no-template control
        assert data["summary"]["check"] == "Provette found 1 biology problem (1 note)."


@pytest.mark.sim
def test_the_command(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from provette.cli import main

    out = tmp_path / "replay.html"
    args = ["view", str(PROTOCOLS / "pcr_buggy.py"), "--out", str(out)]
    assert main(args + ["--platemap", str(PLATEMAPS / "pcr-01.json")]) == 0
    assert out.is_file() and out.stat().st_size < THREE_MB
    assert "Wrote" in capsys.readouterr().out
    assert main(["view", str(PROTOCOLS / "bad_protocol.py"), "--out", str(out)]) == 2
    assert main(args + ["--platemap", str(tmp_path / "missing.json")]) == 3


def test_the_fixed_trash_labware_is_the_bin() -> None:
    """Below API 2.16 the trash is a labware with one huge well: the page draws it as the bin,
    not as a plate, and the words call it the trash (every public-library protocol loads it)."""
    from dataclasses import replace

    from provette.model import Labware, WellGeometry
    from provette.view.export import is_trash

    trash = Labware(
        labware_id="12:opentrons_1_trash_1100ml_fixed",
        load_name="opentrons_1_trash_1100ml_fixed",
        display_name="Opentrons Fixed Trash",
        slot="12",
        is_tiprack=False,
        module=None,
        label=None,
        wells={"A1": WellGeometry(82.0, 1100000.0, "rectangular", None, 107.11, 165.67)},
    )
    assert is_trash(trash)
    b = TraceBuilder({tube("A1"): ("water", 200.0)})
    b.deck = replace(b.deck, labware=[*b.deck.labware, trash])
    b.pick_up(tip("A1"))
    b.aspirate(tip("A1"), tube("A1"), 20)
    b.blow_out(tip("A1"), WellKey(trash.labware_id, "A1"))
    trace = b.trace()
    run = replay(trace)
    result = CheckResult(Path("trash.py"), ("line 1",), (), trace, run)
    data = export(result)
    row = next(lw for lw in data["deck"]["labware"] if lw["id"] == trash.labware_id)
    assert row["is_trash"] and row["wells"] == {} and row["measured"]
    assert row["w"] > 100 and row["h"] > 80  # the slot's box, not the well's
    assert describe(trace.events[-1], trace.deck) == "blow out the tip into the trash, tip A1"
    assert_state_matches(data, run, None)


@pytest.mark.sim
def test_a_labware_on_a_module_stands_at_the_modules_height(
    checked: Callable[[Path], CheckResult],
) -> None:
    """The module definitions' own numbers (opentrons_shared_data): where a module holds its
    labware above the deck, and its body; a labware on the deck stands at 0 with no body."""
    data = export(checked(PROTOCOLS / "modules.py"))
    rows = {lw["slot"]: lw for lw in data["deck"]["labware"]}
    cold = rows["6"]
    assert cold["module"] == "temperatureModuleV2"
    assert cold["elevation"] == pytest.approx(80.09)
    assert cold["module_body"]["height"] == pytest.approx(80.09)
    assert cold["module_body"]["name"] == "Temperature Module GEN2"
    assert (cold["module_body"]["w"], cold["module_body"]["h"]) == (cold["w"], cold["h"])
    cycler = rows["7"]  # API 2.27: the definition's offset; the plate in the middle of its body
    assert cycler["elevation"] == pytest.approx(108.96)
    assert cycler["oy"] == pytest.approx(68.8)
    body = cycler["module_body"]
    assert (body["w"], body["h"]) == (pytest.approx(172), pytest.approx(245.2))
    assert body["x"] == pytest.approx(cycler["slot_x"] - 22.125)
    assert rows["1"]["elevation"] == pytest.approx(68.275)  # the heater-shaker
    assert rows["9"]["elevation"] == 0.0 and rows["9"]["module_body"] is None  # the tips


def test_the_thermocycler_holds_its_plate_lower_below_api_2_14() -> None:
    """Below API 2.14 the legacy core puts a thermocycler GEN2's plate at its older offset
    (opentrons, protocol_api/core/legacy/module_geometry.py); from 2.14, the definition's."""
    slot = Slot("7", 0.0, 181.0, 128.0, 86.0)
    old = _on_module("thermocyclerModuleV2", slot, 127.76, 85.48, "2.13")
    new = _on_module("thermocyclerModuleV2", slot, 127.76, 85.48, "2.14")
    assert old is not None and new is not None
    assert old["elevation"] == pytest.approx(98.26) and old["dy"] == pytest.approx(68.06)
    assert new["elevation"] == pytest.approx(108.96) and new["dy"] == pytest.approx(68.8)
    assert _on_module(None, slot, 127.76, 85.48, "2.19") is None
    assert _on_module("noSuchModuleV9", slot, 127.76, 85.48, "2.19") is None
