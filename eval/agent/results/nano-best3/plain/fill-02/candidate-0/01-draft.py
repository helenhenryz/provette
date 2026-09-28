from opentrons import protocol_api

metadata = {
    "protocolName": "Aliquot protein into PCR strip tubes",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load tip rack
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 1)

    # Load tube rack with protein stock
    tubes = protocol.load_labware("opentrons_15_tuberack_falcon_15ml_conical", 2)

    # Load temperature module and aluminium block
    temp_mod = protocol.load_module("temperature module gen2", 3)
    block = temp_mod.load_labware("opentrons_96_aluminumblock_generic_pcr_strip_200ul")
    
    # Set temperature to 4°C for protein stability
    temp_mod.set_temperature(4)

    # Define the protein liquid
    protein = protocol.define_liquid(
        name="protein",
        description="protein stock",
        display_color="#0000FF"
    )
    # Load 5000 µL of protein into tube A1
    tubes["A1"].load_liquid(liquid=protein, volume=5000)

    # Load the p300 single channel pipette
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    # Define destination wells: first 48 wells of the block (A1-A12, B1-B12, C1-C12, D1-D12)
    dest_wells = []
    for col in "ABCD":
        for row in range(1,13):
            dest_wells.append(f"{col}{row}")

    # Transfer 50 µL of protein to each destination well
    for well in dest_wells:
        p300.pick_up_tip()
        p300.aspirate(50, tubes["A1"])
        p300.dispense(50, block[well])
        p300.drop_tip()

    # Deactivate temperature module
    temp_mod.deactivate()
