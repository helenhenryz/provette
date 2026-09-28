from opentrons import protocol_api

metadata = {
    "protocolName": "RT_setup",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tip_racks = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    tube_rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    rna_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)
    pcr_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 4)
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tip_racks])

    # Define liquids
    buffer = protocol.define_liquid(name="buffer", description="5x RT buffer", display_color="#0000FF")
    rt = protocol.define_liquid(name="rt", description="reverse transcriptase", display_color="#000000")
    dntp = protocol.define_liquid(name="dntp", description="dNTP mix", display_color="#00FF00")
    primers = protocol.define_liquid(name="primers", description="random primers", display_color="#FF6600")
    water = protocol.define_liquid(name="water", description="nuclease-free water", display_color="#0000FF")
    rna_liquids = {}
    for i in range(1, 13):
        rna_liquids[f"rna {i}"] = protocol.define_liquid(name=f"rna {i}", description=f"RNA sample {i}", display_color="#000000")

    # Load liquids into source wells
    buffer_well = tube_rack["A1"]
    buffer_well.load_liquid(liquid=buffer, volume=200)
    rt_well = tube_rack["A2"]
    rt_well.load_liquid(liquid=rt, volume=200)
    dntp_well = tube_rack["A3"]
    dntp_well.load_liquid(liquid=dntp, volume=200)
    primers_well = tube_rack["A4"]
    primers_well.load_liquid(liquid=primers, volume=200)
    water_well = tube_rack["A5"]
    water_well.load_liquid(liquid=water, volume=200)
    for i in range(1, 13):
        rna_well = rna_plate[f"A{i}"]
        rna_well.load_liquid(liquid=rna_liquids[f"rna {i}"], volume=50)

    # Set up reactions and no-RT controls
    for i in range(1, 13):
        # Water: 5 ul into reaction well, 6 ul into control well
        p20.pick_up_tip()
        p20.aspirate(5, water_well)
        p20.dispense(5, pcr_plate[f"A{i}"])
        p20.aspirate(6, water_well)
        p20.dispense(6, pcr_plate[f"B{i}"])
        p20.drop_tip()

        # Buffer: 4 ul into reaction well, 4 ul into control well
        p20.pick_up_tip()
        p20.aspirate(8, buffer_well)
        p20.dispense(4, pcr_plate[f"A{i}"])
        p20.dispense(4, pcr_plate[f"B{i}"])
        p20.drop_tip()

        # dNTPs: 1 ul into reaction well, 1 ul into control well
        p20.pick_up_tip()
        p20.aspirate(2, dntp_well)
        p20.dispense(1, pcr_plate[f"A{i}"])
        p20.dispense(1, pcr_plate[f"B{i}"])
        p20.drop_tip()

        # Primers: 1 ul into reaction well, 1 ul into control well
        p20.pick_up_tip()
        p20.aspirate(2, primers_well)
        p20.dispense(1, pcr_plate[f"A{i}"])
        p20.dispense(1, pcr_plate[f"B{i}"])
        p20.drop_tip()

        # RNA: 8 ul into reaction well, 8 ul into control well
        rna_i_well = rna_plate[f"A{i}"]
        p20.pick_up_tip()
        p20.aspirate(16, rna_i_well)
        p20.dispense(8, pcr_plate[f"A{i}"])
        p20.dispense(8, pcr_plate[f"B{i}"])
        p20.drop_tip()

        # Reverse transcriptase: 1 ul into reaction well only
        p20.pick_up_tip()
        p20.aspirate(1, rt_well)
        p20.dispense(1, pcr_plate[f"A{i}"])
        p20.drop_tip()
