from opentrons import protocol_api

metadata = {"protocolName": "ELISA Transfer", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    source_plate = protocol.load_labware('nest_96_wellplate_100ul_pcr_full_skirt', 1)
    elisa_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 3, label='elisa')
    tip_rack = protocol.load_labware('opentrons_96_tiprack_300ul', 4)
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tip_rack])
    standards_tuberack = protocol.load_labware('opentrons_24_tuberack_nest_1.5ml_snapcap', 2)

    # Define liquids and load them into source wells
    well_names = ["A1","A2","A3","A4","A5","A6","A7","A8","B1","B2","B3","B4","B5","B6","B7","B8","C1","C2","C3","C4","C5","C6","C7","C8","D1","D2","D3","D4","D5","D6","D7","D8","E1","E2","E3","E4","E5","E6","E7","E8"]
    for i, well in enumerate(well_names, start=1):
        serum_liquid = protocol.define_liquid(name=f"serum {i}", description=f"Serum sample {i}", display_color="#FF0000")
        source_plate[well].load_liquid(liquid=serum_liquid, volume=100)

    # Define liquids and load them into tube rack wells
    standard_source_well_names = ["A1","A2","A3","A4","A5","A6","B1","B2"]
    for i, well in enumerate(standard_source_well_names, start=1):
        standard_liquid = protocol.define_liquid(name=f"standard {i}", description=f"Standard {i}", display_color="#00FF00")
        standards_tuberack[well].load_liquid(liquid=standard_liquid, volume=100)

    # Transfer serum samples
    for well in well_names:
        p300.pick_up_tip()
        p300.aspirate(100, source_plate[well])
        p300.dispense(100, elisa_plate[well])
        p300.drop_tip()

    # Transfer standards
    standard_destination_wells = ["A12","B12","C12","D12","E12","F12","G12","H12"]
    for i, dest_well in enumerate(standard_destination_wells):
        src_well = standards_tuberack[standard_source_well_names[i]]
        p300.pick_up_tip()
        p300.aspirate(100, src_well)
        p300.dispense(100, elisa_plate[dest_well])
        p300.drop_tip()
