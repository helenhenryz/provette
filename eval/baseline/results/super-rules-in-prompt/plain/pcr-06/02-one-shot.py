from opentrons import protocol_api

metadata = {
    "protocolName": "Colony PCR preparation",
    "author": "",
    "description": "Distribute PCR mix and add colony suspensions.",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # ----- Labware -----------------------------------------------------------
    tiprack = protocol.load_labware("opentrons_96_tiprack_20ul", "1")
    tuberack = protocol.load_labware(
        "opentrons_24_tuberack_nest_1.5ml_snapcap", "2"
    )
    pcr_plate = protocol.load_labware(
        "nest_96_wellplate_100ul_pcr_full_skirt", "3"
    )               # destination plate (PCR)
    colony_plate = protocol.load_labware(
        "nest_96_wellplate_200ul_flat", "4"
    )                         # source plate (colonies)

    # ----- Pipette -----------------------------------------------------------
    p20 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tiprack])

    # ----- Liquid definitions ------------------------------------------------
    pcr_mix = protocol.define_liquid(
        name="pcr mix",
        description="PCR master mix",
        display_color="#FF0000"
    )
    colony_liquids = [
        protocol.define_liquid(
            name=f"colony {i}",
            description=f"Suspension of colony {i}",
            display_color="#00AA00"
        )
        for i in range(1, 17)
    ]

    # Helper to generate well positions column-major: A1, B1 ... H1, A2 ...
    def first_n_positions(n: int):
        rows = ["A", "B", "C", "D", "E", "F", "G", "H"]
        positions = []
        col = 0
        while len(positions) < n:
            for r in rows:
                if len(positions) >= n:
                    break
                positions.append(f"{r}{col + 1}")
            col += 1
        return positions

    positions_16 = first_n_positions(16)

    # ----- Load liquids ------------------------------------------------------
    # PCR mix in tube A1 of the tuberack
    tuberack["A1"].load_liquid(pcr_mix, volume=400.0)   # >16 * 20 µL

    # Colony suspensions in the source plate
    colony_wells = [colony_plate[p] for p in positions_16]
    for well, liq in zip(colony_wells, colony_liquids):
        well.load_liquid(liq, volume=10.0)             # enough for several transfers

    # Destination wells in the PCR plate
    dest_wells = [pcr_plate[p] for p in positions_16]

    # ----- Distribute PCR mix (20 µL each) ------------------------------------
    for dw in dest_wells:
        p20.pick_up_tip()
        p20.aspirate(20, tuberack["A1"])
        p20.dispense(20, dw)
        p20.blow_out(tuberack["A1"])
        p20.drop_tip()

    # ----- Add colony material (1 µL each) -------------------------------------
    for src_well, dst_well in zip(colony_wells, dest_wells):
        p20.pick_up_tip()
        p20.aspirate(1, src_well)
        p20.dispense(1, dst_well)
        p20.blow_out(dst_well)
        p20.drop_tip()
