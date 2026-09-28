from opentrons import protocol_api

metadata = {"protocolName": "Pool_48_libraries", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 1)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    tiprack = protocol.load_labware("opentrons_96_tiprack_20ul", 3)
    
    # Load the p20 pipette with the tip rack
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tiprack])
    
    # Load each library liquid into a well of the plate
    # Use the first 48 wells: columns A-F, rows 1-8
    well_names = []
    for col in ["A", "B", "C", "D", "E", "F"]:
        for row in range(1, 9):
            well_names.append(col + str(row))
    for i, well_name in enumerate(well_names):
        lib_obj = protocol.define_liquid(
            name=f"library {i+1}",
            description=f"Sequencing library {i+1}",
            display_color="#FF0000"
        )
        well = plate[well_name]
        well.load_liquid(liquid=lib_obj, volume=100)  # 100 ul per library
    
    # Pool 5 ul from each library into a single tube
    dest_tube = tubes["A1"]
    p20.pick_up_tip()
    for well_name in well_names:
        p20.aspirate(5, plate[well_name])
        p20.dispense(5, dest_tube)
    p20.drop_tip()
