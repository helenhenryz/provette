from opentrons import protocol_api

metadata = {"protocolName": "Serum dilution and ELISA transfer", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Define liquids
    serum_liquids = {}
    for i in range(1, 25):
        name = f"serum {i}"
        serum_liquids[name] = protocol.define_liquid(
            name=name,
            description=f"Serum sample {i}",
            display_color="#FF0000"
        )
    pbs_liquid = protocol.define_liquid(
        name="pbs",
        description="Phosphate buffered saline",
        display_color="#00FF00"
    )

    # Load labware
    tips_20 = protocol.load_labware("opentrons_96_tiprack_20ul", 1)   # for small volumes if needed
    tips_300 = protocol.load_labware("opentrons_96_tiprack_300ul", 2)
    tips_1000 = protocol.load_labware("opentrons_96_tiprack_1000ul", 3)
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 4)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 5)
    elisa_plate = protocol.load_labware("corning_96_wellplate_360ul_flat", 6)

    # Load liquids into tubes and reservoir
    for i, tube in enumerate(tuberack.wells()):
        tube.load_liquid(liquid=serum_liquids[f"serum {i+1}"], volume=1000)  # 1 mL each
    reservoir["A1"].load_liquid(liquid=pbs_liquid, volume=12000)  # enough PBS

    # Instruments
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips_20])  # not used but okay
    p300 = protocol.load_instrument("p300_single_gen2", "left", tip_racks=[tips_300])
    p1000 = protocol.load_instrument("p1000_single_gen2", "right", tip_racks=[tips_1000])  # note: overlapping right/left? need separate mounts.
    # Actually we can't have two instruments on same mount. Let's rearrange: p300 right, p1000 left.
