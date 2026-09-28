Reference (the same for every model; it names what exists, and says nothing about how to do the biology):

Pipettes (OT-2 GEN2), as `protocol.load_instrument(name, "left" or "right", tip_racks=[...])`:
p20_single_gen2 (1-20 ul), p300_single_gen2 (20-300 ul), p1000_single_gen2 (100-1000 ul), p20_multi_gen2 and p300_multi_gen2 (8 channels).

Tip racks: opentrons_96_tiprack_20ul, opentrons_96_tiprack_300ul, opentrons_96_tiprack_1000ul, opentrons_96_filtertiprack_20ul, opentrons_96_filtertiprack_200ul, opentrons_96_filtertiprack_1000ul.

Plates: nest_96_wellplate_100ul_pcr_full_skirt, biorad_96_wellplate_200ul_pcr, nest_96_wellplate_200ul_flat, corning_96_wellplate_360ul_flat, nest_96_wellplate_2ml_deep, usascientific_96_wellplate_2.4ml_deep, corning_384_wellplate_112ul_flat.

Tubes: opentrons_24_tuberack_nest_1.5ml_snapcap, opentrons_24_tuberack_nest_2ml_snapcap, opentrons_15_tuberack_falcon_15ml_conical, opentrons_6_tuberack_falcon_50ml_conical, opentrons_10_tuberack_falcon_4x50ml_6x15ml_conical.

Cold blocks and strips: opentrons_24_aluminumblock_nest_1.5ml_snapcap, opentrons_96_aluminumblock_generic_pcr_strip_200ul, opentrons_96_aluminumblock_nest_wellplate_100ul.

Reservoirs: nest_12_reservoir_15ml, nest_1_reservoir_195ml.

Modules, as `protocol.load_module(name, slot)` then `module.load_labware(...)`: "temperature module gen2", "magnetic module gen2", "thermocyclerModuleV2", "heaterShakerModuleV1". On a temperature module load only the aluminium blocks above, never a tube rack: the pipette cannot arc over a rack on a module.

The shape of a protocol file:

```python
from opentrons import protocol_api

metadata = {"protocolName": "Example", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    buffer = protocol.define_liquid(
        name="buffer", description="assay buffer", display_color="#0000FF"
    )
    tubes["A1"].load_liquid(liquid=buffer, volume=1000)  # what is in the tube when the run starts

    p300.pick_up_tip()
    p300.aspirate(50, tubes["A1"])
    p300.dispense(50, plate["A1"])
    p300.drop_tip()
```

`load_liquid` only describes what a person has put on the deck before the run. The robot fills wells by aspirating and dispensing.
