metadata = {
    "protocolName": "LB medium fill and glycerol stock inoculation",
    "author": "OpenTrons Assistant",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # -------------------------- Labware --------------------------
    # Reservoir for LB medium
    reservoir = protocol.load_labware("nest_1_reservoir_195ml", 1)
    # Destination deep‑well plate (will receive LB + inoculum)
    target_plate = protocol.load_labware("usascientific_96_wellplate_2.4ml_deep", 2)
    # Source glycerol‑stock plate (one strain per well)
    glycerol_plate = protocol.load_labware("usascientific_96_wellplate_2.4ml_deep", 3)
    # Tip racks
    tiprack_1000 = protocol.load_labware("opentrons_96_tiprack_1000ul", 4)   # for p1000
    tiprack_20   = protocol.load_labware("opentrons_96_tiprack_20ul",   5)   # for p20

    # -------------------------- Liquids --------------------------
    # LB medium (must be named exactly "lb")
    lb = protocol.define_liquid(
        name="lb",
        description="Luria‑Bertani medium",
        display_color="#FFFF00"   # bright yellow
    )
    # Glycerol stocks (any name)
    glycerol = protocol.define_liquid(
        name="glycerol_stock",
        description="Glycerol stock cultures",
        display_color="#00FF00"   # green
    )

    # Load liquids onto the deck at the start
    reservoir["A1"].load_liquid(lb, volume=150000)          # 150 mL – plenty for 96×500 µL
    for well in glycerol_plate.wells():
        well.load_liquid(glycerol, volume=100)             # 100 µL per stock well

    # -------------------------- Pipettes --------------------------
    p1000 = protocol.load_instrument(
        "p1000_single_gen2",
        "left",
        tip_racks=[tiprack_1000]
    )
    p20 = protocol.load_instrument(
        "p20_single_gen2",
        "right",
        tip_racks=[tiprack_20]
    )

    # -------------------------- Protocol Steps --------------------------

    # 1. Fill each well of the target plate with 500 µL LB from the reservoir
    p1000.distribute(
        volume=500,
        source=reservoir["A1"],
        dest=[well for well in target_plate.wells()],
        new_tip="always",      # fresh tip for each well → no carry‑over
        disposal_volume=0,
        blow_out=False,
        touch_tip=False
    )

    # 2. Inoculate each well with 5 µL from the matching glycerol‑stock well
    p20.transfer(
        volume=5,
        source=glycerol_plate.wells(),
        dest=target_plate.wells(),
        new_tip="always",      # fresh tip per transfer
        disposal_volume=0,
        blow_out=False,
        touch_tip=False
    )
