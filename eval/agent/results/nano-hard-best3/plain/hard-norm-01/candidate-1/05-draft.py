from opentrons import protocol_api

metadata = {
    "protocolName": "Normalize 48 libraries to 4 nM",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    buffer_res = protocol.load_labware("nest_12_reservoir_15ml", 2)
    source_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 3)
    dest_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 4)
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])

    # Define liquids
    buffer_liquid = protocol.define_liquid(name='buffer', description='Elution buffer', display_color='#0000FF')
    library_liquids = {}
    for i in range(1, 49):
        library_liquids[i] = protocol.define_liquid(name=f'library {i}', description=f'Library {i}', display_color='#FF0000')

    # Load buffer into reservoir
    buffer_res.well('A1').load_liquid(liquid=buffer_liquid, volume=1000)

    # Concentrations of libraries (nM)
    concentrations = [12, 45, 8, 80, 33, 5.5, 60, 21, 14, 9, 72, 27, 6, 40, 18, 55, 11, 30, 7.5, 65, 24, 16, 48, 10, 36, 13, 70, 22, 8.5, 50, 29, 19, 42, 15, 62, 25, 6.5, 38, 17, 76, 20, 9.5, 58, 31, 12.5, 44, 23, 7]

    # Calculate library volumes (ul) = 80 / concentration, rounded to 2 decimals
    library_volumes = [round(80 / conc, 2) for conc in concentrations]

    # Get ordered lists of wells
    source_wells = list(source_plate.wells())[:48]
    dest_wells = list(dest_plate.wells())[:48]

    # Load each library into source plate wells
    for i in range(48):
        lib_vol = library_volumes[i]
        source_wells[i].load_liquid(liquid=library_liquids[i+1], volume=lib_vol)

    # Transfer mixtures to destination plate
    for i in range(48):
        lib_vol = library_volumes[i]
        buf_vol = 20 - lib_vol

        # Aspirate library
        p20.pick_up_tip()
        p20.aspirate(lib_vol, source_wells[i])
        # Transfer library to destination
        p20.dispense(lib_vol, dest_wells[i])
        # Pick up fresh tip for buffer
        p20.pick_up_tip()
        # Aspirate buffer
        p20.aspirate(buf_vol, buffer_res['A1'])
        # Dispense total volume (lib_vol + buf_vol) into destination well
        p20.dispense(lib_vol + buf_vol, dest_wells[i])
        # Drop tip
        p20.drop_tip()
