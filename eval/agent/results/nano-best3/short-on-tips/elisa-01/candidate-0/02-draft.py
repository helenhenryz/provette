from opentrons import protocol_api

metadata = {"protocolName": "ELISA Transfer Protocol", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Define liquids: standards 1-8
    standard_liquids = {}
    for i in range(1, 9):
        standard_liquids[f"standard {i}"] = protocol.define_liquid(
            name=f"standard {i}",
            description=f"Standard {i}",
            display_color="#FF0000"
        )
    # Define liquids: serum 1-40
    serum_liquids = {}
    for i in range(1, 41):
        serum_liquids[f"serum {i}"] = protocol.define_liquid(
            name=f"serum {i}",
            description=f"Serum {i}",
            display_color="#00FF00"
        )
    
    # Load labware
    source_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1)
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    elisa_plate = protocol.load_labware("corning_96_wellplate_360ul_flat", 3, label="Coated ELISA Plate")
    tip_rack = protocol.load_labware("opentrons_96_tiprack_300ul", 4)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tip_rack])
    
    # Generate list of well names for the first 40 wells in row-major order
    well_names = []
    for row in ["A", "B", "C", "D", "E", "F", "G", "H"]:
        for col in range(1, 13):
            well_names.append(row + str(col))
    serum_well_names = well_names[:40]
    
    # Load serum liquids into source plate wells
    for i in range(40):
        well_name = serum_well_names[i]
        source_plate[well_name].load_liquid(
            liquid=serum_liquids[f"serum {i+1}"],
            volume=100
        )
    
    # Define mapping of standard index to tuberack well name
    standard_source_well_names = ["A1", "A2", "A3", "A4", "A5", "A6", "B1", "B2"]
    # Load standard liquids into tuberack wells
    for i in range(8):
        well_name = standard_source_well_names[i]
        tuberack[well_name].load_liquid(
            liquid=standard_liquids[f"standard {i+1}"],
            volume=100
        )
    
    # Perform transfers using a fresh tip for each transfer to avoid cross-contamination
    # Transfer serum samples (40 transfers)
    for i in range(40):
        p300.pick_up_tip()
        src_well = source_plate[serum_well_names[i]]
        dest_well = elisa_plate[serum_well_names[i]]  # same well name
        p300.aspirate(100, src_well)
        p300.dispense(100, dest_well)
        p300.drop_tip()
    # Transfer standards (8 transfers)
    for i in range(8):
        p300.pick_up_tip()
        src_well = tuberack[standard_source_well_names[i]]
        # Compute destination well name in column 12
        row_letter = chr(ord('A') + i)
        dest_well_name = row_letter + "12"
        dest_well = elisa_plate[dest_well_name]
        p300.aspirate(100, src_well)
        p300.dispense(100, dest_well)
        p300.drop_tip()
