from opentrons import protocol_api

metadata = {
    "protocolName": "Seed 96-well plate with cell lines",
    "apiLevel": "2.19"
}


def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    tubes = protocol.load_labware("opentrons_15_tuberack_falcon_15ml_conical", 2)
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 3)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    # Define liquids
    line1 = protocol.define_liquid(name="line 1", description="Cell line 1 suspension", display_color="#FF0000")
    line2 = protocol.define_liquid(name="line 2", description="Cell line 2 suspension", display_color="#00FF00")
    line3 = protocol.define_liquid(name="line 3", description="Cell line 3 suspension", display_color="#0000FF")

    # Load liquids into tube rack wells
    tubes["A1"].load_liquid(liquid=line1, volume=5000)
    tubes["A2"].load_liquid(liquid=line2, volume=5000)
    tubes["A3"].load_liquid(liquid=line3, volume=5000)

    # Row letters for wells
    row_letters = "ABCDEFGH"

    # Process each column
    for col in range(1, 13):
        # Determine source well based on column
        if col <= 4:
            src = tubes["A1"]
        elif col <= 8:
            src = tubes["A2"]
        else:
            src = tubes["A3"]
        # Process each row in the column
        for row_letter in row_letters:
            dest = plate[f"{row_letter}{col}"]
            # Pick up tip
            p300.pick_up_tip()
            # Aspirate 100 ul from source
            p300.aspirate(100, src)
            # Dispense 100 ul into destination
            p300.dispense(100, dest)
            # Drop tip
            p300.drop_tip()
