from pathlib import Path

from provette.model import (
    Deck,
    Event,
    Labware,
    LiquidLoad,
    Pipette,
    Target,
    Trace,
    WellGeometry,
    WellKey,
)


def _trace() -> Trace:
    tube = WellKey("2:opentrons_24_tuberack_nest_1.5ml_snapcap", "A1")
    tip = WellKey("3:opentrons_96_tiprack_300ul", "A1")
    geometry = WellGeometry(
        depth_mm=37.9,
        max_volume_ul=1500,
        shape="circular",
        diameter_mm=8.7,
        bottom_shape="v",
        height_at_ul=[(0.0, 0.0), (10.3, 1.56), (1898.0, 37.9)],
    )
    deck = Deck(
        protocol_name="p.py",
        api_level="2.27",
        opentrons_version="8.8.2",
        labware=[
            Labware(
                labware_id=tube.labware_id,
                load_name="opentrons_24_tuberack_nest_1.5ml_snapcap",
                display_name="tubes",
                slot="2",
                is_tiprack=False,
                module=None,
                label=None,
                wells={"A1": geometry},
            )
        ],
        pipettes=[Pipette("right", "p300_single_gen2", 1, 20, 300)],
        liquid_loads=[LiquidLoad(tube, "PCR master mix", "Taq + dNTPs", 1000, 9)],
    )
    event = Event(
        index=0,
        op="aspirate",
        line=14,
        stack=["run:14"],
        parent=None,
        mount="right",
        targets=[Target(tip=tip, well=tube)],
        volume_ul=40,
        height_mm=1.0,
        t_est_s=3.5,
        duration_s=None,
        celsius=None,
        module=None,
        labware_id=None,
        detail="Aspirating 40.0 uL",
        raw_op="command.ASPIRATE",
    )
    return Trace(deck=deck, events=[event])


def test_trace_round_trips_through_jsonl(tmp_path: Path) -> None:
    trace = _trace()
    path = tmp_path / "trace.jsonl"
    trace.dump(path)
    assert Trace.load(path) == trace
