from opentrons import protocol_api
import opentrons

metadata = {"protocolName": "Cherrypick and add mix", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Labware
    src_plate = protocol.load_labware("corning_384_wellplate_112ul_flat", 1)
    dst_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 2)
    tiprack = protocol.load_labware("opentrons_96_tiprack_20ul", 3)
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 4)
    
    # Pipette
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tiprack])
    
    # Define liquids
    # Mix
    mix_liq = protocol.define_liquid(name="mix", description="PCR master mix", display_color="#FF0000")
    tuberack["A1"].load_liquid(liquid=mix_liq, volume=500)  # enough for 24*18=432 ul + overage
    
    # Source samples
    source_wells = ["A1", "B2", "C3", "D4", "E5", "F6", "G7", "H8",
                    "I9", "J10", "K11", "L12", "M13", "N14", "O15", "P16",
                    "A17", "B18", "C19", "D20", "E21", "F22", "G23", "H24"]
    dest_wells = ["A1", "B1", "C1", "D1", "E1", "F1", "G1", "H1",
                  "A2", "B2", "C2", "D2", "E2", "F2", "G2", "H2",
                  "A3", "B3", "C3", "D3", "E3", "F3", "G3", "H3"]
    
    for i, well in enumerate(source_wells):
        liq = protocol.define_liquid(name=f"sample_{well}", description=f"Sample from {well}", display_color="#00FF00")
        src_plate[well].load_liquid(liquid=liq, volume=50)
    
    # Cherrypick 2 ul from source to destination
    for src, dst in zip(source_wells, dest_wells):
        p20.pick_up_tip()
        p20.aspirate(2, src_plate[src])
        p20.dispense(2, dst_plate[dst])
        p20.drop_tip()
    
    # Add 18 ul mix to each destination well
    for dst in dest_wells:
        p20.pick_up_tip()
        p20.aspirate(18, tuberack["A1"])
        p20.dispense(18, dst_plate[dst])
        p20.drop_tip()
