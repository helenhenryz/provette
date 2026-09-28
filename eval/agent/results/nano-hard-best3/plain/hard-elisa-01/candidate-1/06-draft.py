from opentrons import protocol_api

metadata = {
    "protocolName": "ELISA Standard Curve",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1)
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    tiprack_300 = protocol.load_labware("opentrons_96_tiprack_300ul", 3)
    source_plate = protocol.load_labware("nest_96_wellplate_2ml_deep", 4)
    
    # Load instrument
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tiprack_300])
    
    # Define liquids
    standard_liquid = protocol.define_liquid(
        name="standard", description="200 ng/ml standard stock", display_color="#FF0000"
    )
    diluent_liquid = protocol.define_liquid(
        name="diluent", description="assay diluent", display_color="#00FF00"
    )
    serum_liquids = {}
    for i in range(1, 33):
        serum_liquids[i] = protocol.define_liquid(
            name=f"serum {i}", description=f"Serum sample {i}", display_color="#0000FF"
        )
    
    # Generate well name lists for source plate
    well_names = []
    for row in "ABCDEFGHI":
        for col in range(1, 13):
            well_names.append(f"{row}{col}")
    
    # Load liquids into source wells
    tuberack["A1"].load_liquid(liquid=standard_liquid, volume=500)
    tuberack["A2"].load_liquid(liquid=diluent_liquid, volume=1700)
    for i in range(32):
        source_plate[well_names[i]].load_liquid(liquid=serum_liquids[i+1], volume=300)
    
    # Generate list of all 96 destination wells (plate)
    rows = "ABCDEFGHI"
    dest_well_names = []
    for row in rows:
        for col in range(1, 13):
            dest_well_names.append(f"{row}{col}")
    
    # Standard mixture volumes for each of the 16 standard/sample wells
    std_mix = [
        (50, 50), (50, 50),
        (25, 75), (25, 75),
        (12.5, 87.5), (12.5, 87.5),
        (6.25, 93.75), (6.25, 93.75),
        (3.12, 96.88), (3.12, 96.88),
        (1.56, 98.44), (1.56, 98.44),
        (0.78, 99.22), (0.78, 99.22),
        (0, 100), (0, 100)
    ]
    
    # Fill standards and blank in the plate
    for i, (std_vol, dil_vol) in enumerate(std_mix):
        # Aspirate standard if needed
        if std_vol > 0:
            p300.pick_up_tip()
            p300.aspirate(std_vol, tuberack["A1"])
            p300.dispense(std_vol, plate[dest_well_names[i]])
            p300.drop_tip()
        # Aspirate diluent and dispense
        p300.pick_up_tip()
        p300.aspirate(dil_vol, tuberack["A2"])
        p300.dispense(dil_vol, plate[dest_well_names[i]])
        p300.drop_tip()
    
    # Fill serum samples (32 samples, each in duplicate)
    for i in range(32):
        p300.pick_up_tip()
        p300.aspirate(100, source_plate[well_names[i]])
        p300.dispense(100, plate[dest_well_names[16 + 2*i]])
        p300.aspirate(100, source_plate[well_names[i]])
        p300.dispense(100, plate[dest_well_names[16 + 2*i + 1]])
        p300.drop_tip()
