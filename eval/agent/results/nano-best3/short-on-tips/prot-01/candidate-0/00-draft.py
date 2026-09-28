from opentrons import protocol_api

metadata = {"protocolName": "Prepare 12 samples for SDS-PAGE", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tip_racks = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    source_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 2)
    dye_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 3)
    dest_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 4)

    # Load pipette
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tip_racks])

    # Define liquids
    dye_liquid = protocol.define_liquid(name="dye", description="4x loading dye", display_color="#FF6600")
    sample_liquids = {}
    for i in range(1, 13):
        sample_liquids[f"sample {i}"] = protocol.define_liquid(name=f"sample {i}", description=f"Protein sample {i}", display_color=f"#{i:06X}")

    # Load liquids into wells
    dye_plate["A1"].load_liquid(liquid=dye_liquid, volume=100)
    source_wells = [
        source_plate["A1"], source_plate["B1"], source_plate["C1"], source_plate["D1"],
        source_plate["E1"], source_plate["F1"], source_plate["G1"], source_plate["H1"],
        source_plate["A2"], source_plate["B2"], source_plate["C2"], source_plate["D2"]
    ]
    for i, well in enumerate(source_wells, start=1):
        well.load_liquid(liquid=sample_liquids[f"sample {i}"], volume=150)

    # Destination wells in same order
    dest_wells = [
        dest_plate["A1"], dest_plate["B1"], dest_plate["C1"], dest_plate["D1"],
        dest_plate["E1"], dest_plate["F1"], dest_plate["G1"], dest_plate["H1"],
        dest_plate["A2"], dest_plate["B2"], dest_plate["C2"], dest_plate["D2"]
    ]

    # Transfer mixes
    for i in range(12):
        p20.pick_up_tip()
        # aspirate 15 ul sample
        p20.aspirate(15, source_wells[i])
        # aspirate 5 ul dye
        p20.aspirate(5, dye_plate["A1"])
        # dispense 20 ul mixture into destination well
        p20.dispense(20, dest_wells[i])
        p20.drop_tip()
