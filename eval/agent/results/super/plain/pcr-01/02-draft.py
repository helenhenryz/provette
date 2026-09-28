from opentrons import protocol_api

metadata = {"protocolName": "PCR setup for 8 samples", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Labware
    tips_20 = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    tips_300 = protocol.load_labware("opentrons_96_tiprack_300ul", 2)
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3)
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 4)

    # Pipettes
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips_20])
    p300 = protocol.load_instrument("p300_single_gen2", "left", tip_racks=[tips_300])

    # Define liquids
    mm_liq = protocol.define_liquid(name="master mix", description="PCR master mix", display_color="#FF0000")
    sample_liqs = []
    for i in range(1, 9):
        liq = protocol.define_liquid(name=f"sample {i}", description=f"DNA sample {i}", display_color="#00FF00")
        sample_liqs.append(liq)

    # Load liquids into wells
    mm_well = tuberack["A1"]
    mm_well.load_liquid(mm_liq, volume=500)  # starting volume

    sample_well_names = ["A2", "A3", "A4", "A5", "A6", "B1", "B2", "B3"]
    for well_name, liq in zip(sample_well_names, sample_liqs):
        tuberack[well_name].load_liquid(liq, volume=200)

    # Destination wells: first 8 wells of column 1 (A1..A8)
    dest_wells = [plate[f"{chr(ord('A')+r)}1"] for r in range(8)]  # A1..A8

    # Add master mix (20 ul) to each destination well
    for well in dest_wells:
        p300.pick_up_tip()
        p300.aspirate(20, mm_well)
        p300.dispense(20, well)
        p300.blow_out()
        p300.drop_tip()

    # Add samples (5 ul) to each destination well
    for i, well in enumerate(dest_wells):
        sample_well = tuberack[sample_well_names[i]]
        p20.pick_up_tip()
        p20.aspirate(5, sample_well)
        p20.dispense(5, well)
        p20.blow_out()
        p20.drop_tip()
