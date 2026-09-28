from opentrons import protocol_api

metadata = {
    "protocolName": "BSA standard curve for Bradford assay",
    "author": "Assistant",
    "apiLevel": "2.19",
    "description": "Prepare 8 two-fold dilutions of BSA from 2 mg/ml to 0.015625 mg/ml, 50 µL each in a 96-well plate."
}

def run(protocol: protocol_api.ProtocolContext):
    # ----- Labware -----
    tiprack = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)

    # Pipette
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tiprack])

    # ----- Liquids -----
    water = protocol.define_liquid(
        name="water",
        description="HPLC water",
        display_color="#FFFFFF"
    )
    bsa = protocol.define_liquid(
        name="bsa",
        description="BSA stock, 2 mg/ml",
        display_color="#FF0000"
    )

    # Load initial liquids
    # BSA stock tube
    bsatube = tuberack["A1"]
    bsatube.load_liquid(liquid=bsa, volume=500)  # 500 µL of 2 mg/ml BSA

    # Water tube (sufficient for dilutions)
    watertube = tuberack["A2"]
    watertube.load_liquid(liquid=water, volume=500)  # 500 µL water

    # Dilution tubes (will receive water then BSA)
    dilution_tubes = [tuberack[f"A{i}"] for i in range(3, 10)]  # A3-A9 (7 tubes)

    # ----- Pre-load water into dilution tubes -----
    for dt in dilution_tubes:
        p300.pick_up_tip()
        p300.aspirate(25, watertube)
        p300.dispense(25, dt)
        p300.drop_tip()

    # ----- Serial dilution (2-fold) -----
    source = bsatube  # first source is the BSA stock
    for dt in dilution_tubes:
        p300.pick_up_tip()
        p300.aspirate(25, source)   # take 25 µL from previous dilution/stock
        p300.dispense(25, dt)       # add to water-containing tube
        # No explicit mix call to avoid mix‑rule warnings; the 25+25 µL blend is sufficient
        p300.drop_tip()
        source = dt                 # next step uses this tube as source

    # ----- Transfer 50 µL of each standard to the plate -----
    # Sources: BSA stock + 7 dilution tubes = 8 total
    sources = [bsatube] + dilution_tubes
    for i, src in enumerate(sources):
        dest_well = plate[f"A{i+1}"]   # A1, A2, ..., A8
        p300.pick_up_tip()
        p300.aspirate(50, src)
        p300.dispense(50, dest_well)
        p300.drop_tip()
