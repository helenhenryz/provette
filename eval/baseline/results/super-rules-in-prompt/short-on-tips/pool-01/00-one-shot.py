from opentrons import protocol_api

metadata = {
    "protocolName": "Pool 48 Libraries",
    "author": "",
    "description": "Pools 5 µL from each of 48 indexed sequencing libraries into one 1.5 mL tube.",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # ---- Labware -----------------------------------------------------------
    tip_rack = protocol.load_labware('opentrons_96_tiprack_300ul', '1')
    lib_plate = protocol.load_labware('nest_96_wellplate_200ul_flat', '2')
    tube_rack = protocol.load_labware('opentrons_24_tuberack_nest_1.5ml_snapcap', '3')
    destination_tube = tube_rack['A1']

    # ---- Pipette -----------------------------------------------------------
    p300 = protocol.load_instrument('p300_single_gen2', 'right',
                                    tip_racks=[tip_rack])

    # ---- Prepare 48 library liquids ----------------------------------------
    # Order wells column‑wise (A1‑H1, A2‑H2 … A6‑H6) → 48 wells
    lib_wells = [
        f"{row}{col}"
        for col in range(1, 7)          # columns 1‑6
        for row in "ABCDEFGH"           # rows A‑H
    ]
    assert len(lib_wells) >= 48, "Not enough wells for 48 libraries"

    # Keep track of which well corresponds to which library number
    well_to_libnum = {}
    # Colors are arbitrary; just give each a distinct shade
    base_color = 0x100000  # start at a visible hex value

    for idx, well in enumerate(lib_wells[:48], start=1):
        lib_name = f"library {idx}"
        # define the liquid (only once per distinct liquid)
        liquid_obj = protocol.define_liquid(
            name=lib_name,
            description=f"Sequencing library {idx}",
            display_color="#{:06x}".format(base_color + idx)
        )
        lib_plate[well].load_liquid(liquid=liquid_obj, volume=20.0)  # start with 20 µL
        well_to_libnum[well] = idx

    # ---- Pooling -----------------------------------------------------------
    # Use a single tip for the whole operation to minimise tip consumption
    p300.pick_up_tip()

    for well in lib_wells[:48]:
        # Aspirate 5 µL from the library well
        p300.aspirate(5, lib_plate[well])
        # Dispense into the collection tube
        p300.dispense(5, destination_tube)

    p300.drop_tip()
