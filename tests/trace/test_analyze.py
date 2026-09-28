"""`reduce_analysis` on hand-written analysis JSON: no simulator needed."""

from __future__ import annotations

from typing import Any

from provette.trace.analyze import LiquidOp, reduce_analysis


def command(kind: str, result: dict[str, Any] | None = None, **params: Any) -> dict[str, Any]:
    return {"commandType": kind, "params": params, "result": result or {}}


LOADS = [
    command("loadModule", {"moduleId": "m"}, location={"slotName": "4"}, model="x"),
    command("loadLabware", {"labwareId": "plate"}, location={"moduleId": "m"}, loadName="p96"),
    command("loadLabware", {"labwareId": "tips"}, location={"slotName": "3"}, loadName="t300"),
]


def test_labware_on_a_module_gets_the_modules_slot() -> None:
    ops = reduce_analysis(
        {
            "commands": [
                *LOADS,
                command("aspirate", pipetteId="p", labwareId="plate", wellName="B2", volume=5),
            ]
        }
    )
    assert ops == [LiquidOp("aspirate", "p96", "4", "B2", 5)]


def test_in_place_commands_take_the_place_of_the_last_move() -> None:
    commands = [
        *LOADS,
        command("pickUpTip", pipetteId="p", labwareId="tips", wellName="A1"),
        command("aspirate", pipetteId="p", labwareId="plate", wellName="A1", volume=50),
        command("moveToWell", pipetteId="p", labwareId="plate", wellName="A1"),
        command("prepareToAspirate", pipetteId="p"),
        command("airGapInPlace", pipetteId="p", volume=20),
        command("moveToAddressableAreaForDropTip", pipetteId="p", addressableAreaName="fixedTrash"),
        command("dropTipInPlace", pipetteId="p"),
    ]
    assert reduce_analysis({"commands": commands}) == [
        LiquidOp("pick_up_tip", "t300", "3", "A1", None),
        LiquidOp("aspirate", "p96", "4", "A1", 50),
        LiquidOp("aspirate", "p96", "4", "A1", 20),
        LiquidOp("drop_tip", "fixedTrash", None, None, None),
    ]


def test_a_moved_labware_keeps_its_first_slot() -> None:
    commands = [
        *LOADS,
        command("moveLabware", labwareId="tips", newLocation={"slotName": "9"}),
        command("pickUpTip", pipetteId="p", labwareId="tips", wellName="A1"),
    ]
    assert reduce_analysis({"commands": commands})[0].slot == "3"


def test_old_api_fixed_trash_is_a_labware_no_command_loads() -> None:
    analysis = {
        "labware": [
            {
                "id": "fixedTrash",
                "loadName": "opentrons_1_trash_1100ml_fixed",
                "location": {"slotName": "12"},
            }
        ],
        "commands": [command("dropTip", pipetteId="p", labwareId="fixedTrash", wellName="A1")],
    }
    assert reduce_analysis(analysis) == [
        LiquidOp("drop_tip", "opentrons_1_trash_1100ml_fixed", "12", "A1", None)
    ]


def test_cross_check_reconciles_zero_volumes_and_old_engine_dispenses() -> None:
    from provette.model import Deck, Event, Pipette, Target, Trace, WellKey
    from provette.trace import cross_check

    def event(index: int, volume: float) -> Event:
        well = WellKey("1:p96", "A1")
        target = Target(tip=WellKey("3:t300", "A1"), well=well)
        return Event(
            index,
            "dispense",
            1,
            [],
            None,
            "right",
            [target],
            volume,
            1.0,
            0.0,
            None,
            None,
            None,
            None,
        )

    def deck(api_level: str) -> Deck:
        return Deck("x.py", api_level, "8.8.2", [], [Pipette("right", "p300", 1, 20, 300)], [])

    events = [event(0, 0.0), event(1, 90.0)]
    asked = [LiquidOp("dispense", "p96", "1", "A1", 200.0)]  # the old analysis: no 0 uL step
    assert cross_check(Trace(deck("2.13"), events), asked) == []
    held = [
        LiquidOp("dispense", "p96", "1", "A1", 0.0),
        LiquidOp("dispense", "p96", "1", "A1", 90.0),
    ]
    assert cross_check(Trace(deck("2.15"), events), held) == []
    assert cross_check(Trace(deck("2.15"), events), asked)  # the new engine must say 90
    less = [LiquidOp("dispense", "p96", "1", "A1", 50.0)]
    assert cross_check(Trace(deck("2.13"), events), less)  # less than the trace is never excused
