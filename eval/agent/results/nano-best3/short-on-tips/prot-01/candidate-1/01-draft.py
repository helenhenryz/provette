from opentrons import protocol_api

metadata = {
    "protocolName": "SDS-PAGE Sample Preparation",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    source_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 2)
    dest_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 3)
    dye_tube_rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 4)
    
    # Load pipette
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])
    
    # Define liquids
    dye = protocol.define_liquid(
        name="dye",
        description="4x loading dye",
        display_color="#FF0000"
    )
    samples = {}
    for i in range(1, 13):
        sample_name = f"sample {i}"
        samples[sample_name] = protocol.define_liquid(
            name=sample_name,
            description=f"Protein sample {i}",
            display_color="#000000"
        )
    
    # Load liquids into source wells
    for i in range(1, 13):
        well_name = f"A{i}"
        source_plate.well(well_name).load_liquid(
            liquid=samples[f"sample {i}"],
            volume=100
        )
    # Load dye into tube rack well A1
    dye_tube_rack.well("A1").load_liquid(
        liquid=dye,
        volume=100
    )
    
    # Mix each sample with dye
    p20.pick_up_tip()
    for i in range(1, 13):
        # Aspirate 15 ul from sample well
        sample_well = source_plate.well(f"A{i}")
        p20.aspirate(15, sample_well)
        # Aspirate 5 ul from dye well
        p20.aspirate(5, dye_tube_rack.well("A1"))
        # Dispense 20 ul into destination well
        dest_well = dest_plate.well(f"A{i}")
        p20.dispense(20, dest_well)
    p20.drop_tip()
