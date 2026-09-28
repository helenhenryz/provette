from opentrons import protocol_api

metadata = {"protocolName": "Aliquot protein into PCR strip tubes", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load tip rack
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    # Load tube rack with source protein
    tubes = protocol.load_labware("opentrons_15_tuberack_falcon_15ml_conical", 2)
    # Load temperature module and block
    temp_mod = protocol.load_module("temperature module gen2", 3)
    pcr_block = temp_mod.load_labware("opentrons_96_aluminumblock_generic_pcr_strip_200ul")
    # Set temperature to 4°C for protein stability
    temp_mod.set_temperature(4)
    # Load instrument
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])
    # Define liquid protein
    protein = protocol.define_liquid(name="protein", description="Protein stock", display_color="#FF0000")
    # Load protein into source well A1
    tubes["A1"].load_liquid(liquid=protein, volume=5000)
    # Generate list of 48 destination wells (rows 1-6, columns A-H)
    dest_well_names = []
    for row in range(1, 7):
        for col in "ABCDEFGH":
            dest_well_names.append(f"{col}{row}")
    # Perform transfers
    for well_name in dest_well_names:
        p300.pick_up_tip()
        p300.aspirate(50, tubes["A1"])
        p300.dispense(50, pcr_block[well_name])
        p300.drop_tip()
    # Deactivate temperature module
    temp_mod.deactivate()
