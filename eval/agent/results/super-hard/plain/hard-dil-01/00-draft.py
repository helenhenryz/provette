import json
from opentrons import protocol_api

metadata = {"protocolName": "Serum dilution and ELISA transfer", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Define liquids
    serum_names = [f"serum {i}" for i in range(1, 25)]
    for name in serum_names:
        protocol.define_liquid(name=name, description=f"Serum sample {name.split()[1]}", display_color="#FF0000")
    protocol.define_liquid(name="pbs", description="Phosphate buffered saline", display_color="#00FF00")

    # Load labware
    tips_300 = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    tips_1000 = protocol.load_labware("opentrons_96_tiprack_1000ul", 4)
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 3)
    intermediate_plate = protocol.load_labware("nest_96_wellplate_2ml_deep", 5)
    elisa_plate = protocol.load_labware("corning_96_wellplate_360ul_flat", 6)

    # Load liquids into tubes and reservoir
    for i, tube in enumerate(tuberack.wells()):
        tube.load_liquid(liquid=protocol.get_liquid_by_name(f"serum {i+1}"), volume=1000)  # 1 mL each
    reservoir["A1"].load_liquid(liquid=protocol.get_liquid_by_name("pbs"), volume=12000)  # enough PBS

    # Instruments
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips_300])
    p1000 = protocol.load_instrument("p1000_single_gen2", "left", tip_racks=[tips_1000])

    # Step 1: Transfer 50 µL serum to intermediate wells
    intermediate_wells = intermediate_plate.wells()[:24]
    for src_tube, dest_well in zip(tuberack.wells(), intermediate_wells):
        p300.pick_up_tip()
        p300.aspirate(50, src_tube)
        p300.dispense(50, dest_well)
        p300.drop_tip()

    # Step 2: Add 450 µL PBS to each intermediate well
    pbs_well = reservoir["A1"]
    for dest_well in intermediate_wells:
        p1000.pick_up_tip()
        p1000.aspirate(450, pbs_well)
        p1000.dispense(450, dest_well)
        p1000.drop_tip()

    # Step 3: Transfer 100 µL of each dilution in duplicate to ELISA plate
    elisa_wells = elisa_plate.wells()[:48]  # first 48 wells
    for i, src_well in enumerate(intermediate_wells):
        dest1 = elisa_wells[2*i]
        dest2 = elisa_wells[2*i+1]
        p300.pick_up_tip()
        p300.aspirate(200, src_well)
        p300.dispense(100, dest1)
        p300.dispense(100, dest2)
        p300.drop_tip()
