from opentrons import protocol_api

metadata = {
    "protocolName": "Pool 5 ul from each of 48 indexed sequencing libraries into a single 1.5 ml tube",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tip_rack = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)
    
    # Load pipette
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tip_rack])
    
    # Define liquids
    libraries = []
    for i in range(1, 49):
        lib = protocol.define_liquid(name=f"library {i}", description=None, display_color='#1f77b4')
        libraries.append(lib)
    
    # Generate well names A1..D12 (48 wells)
    well_names = []
    for col in range(1, 13):
        well_names.append(f"A{col}")
    for col in range(1, 13):
        well_names.append(f"B{col}")
    for col in range(1, 13):
        well_names.append(f"C{col}")
    for col in range(1, 13):
        well_names.append(f"D{col}")
    
    # Load each library into its well with 50 ul starting volume
    for i, well_name in enumerate(well_names):
        well = plate[well_name]
        lib = libraries[i]
        well.load_liquid(liquid=lib, volume=50)
    
    # Select destination tube
    destination_tube = tubes["A1"]
    
    # Pick up tip once
    p20.pick_up_tip()
    
    # Process each well individually
    for well_name in well_names:
        well = plate[well_name]
        # Aspirate 5 ul from the well
        p20.aspirate(5, well)
        # Dispense 5 ul into the destination tube
        p20.dispense(5, destination_tube)
    
    # Drop tip
    p20.drop_tip()
