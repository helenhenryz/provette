from opentrons import protocol_api

metadata = {
    "protocolName": "1:2 serial dilution of drug into PBS",
    "author": "Assistant",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # ----- labware -----
    tiprack = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    reservoir = protocol.load_labware("nest_1_reservoir_195ml", 2)   # PBS
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3)   # drug stock
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 4)   # dilution plate

    # ----- liquids -----
    pbs = protocol.define_liquid(
        name="pbs",
        description="phosphate‑buffered saline",
        display_color="#00FF00"
    )
    drug = protocol.define_liquid(
        name="drug",
        description="drug stock solution",
        display_color="#FF0000"
    )

    # load liquids into deck wells
    reservoir["A1"].load_liquid(liquid=pbs, volume=150_000)   # 150 mL PBS
    tuberack["A1"].load_liquid(liquid=drug, volume=500)       # 0.5 mL drug stock

    # ----- pipette -----
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tiprack])

    # ----- parameters -----
    transfer_vol = 50      # µL of drug or diluted solution each step
    pbs_vol = 50           # µL PBS per step
    start_col = 1          # first column to use
    n_wells = 12
    row = "A"

    prev_well = None  # will hold the well we just finished (source for next step)

    for i in range(n_wells):
        # choose source: drug stock for first well, previous well thereafter
        if i == 0:
            source_well = tuberack["A1"]
        else:
            source_well = prev_well

        target_well = plate[f"{row}{start_col + i}"]

        # --- add drug / diluted solution ---
        p300.pick_up_tip()
        p300.aspirate(transfer_vol, source_well)
        p300.dispense(transfer_vol, target_well)
        p300.drop_tip()

        # --- add PBS to reach 100 µL total ---
        p300.pick_up_tip()
        p300.aspirate(pbs_vol, reservoir["A1"])
        p300.dispense(pbs_vol, target_well)
        # mix to homogenise before next withdrawal
        p300.mix(repeat=3, volume=40)   # 3 strokes, 40 µL each (< well volume)
        p300.drop_tip()

        prev_well = target_well   # this well becomes the source for the next dilution
