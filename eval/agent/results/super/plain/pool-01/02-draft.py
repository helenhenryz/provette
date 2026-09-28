from opentrons import protocol_api

metadata = {"protocolName": "Pool 48 libraries", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # labware
    src_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 1)
    dst_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 4)
    tips20 = protocol.load_labware("opentrons_96_tiprack_20ul", 3)
    
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips20])
    
    # define liquids
    lib_names = [f"library {i}" for i in range(1, 49)]
    liquids = {}
    for name in lib_names:
        liquids[name] = protocol.define_liquid(
            name=name,
            description="indexed sequencing library",
            display_color="#FF6600"
        )
    # pool liquid (optional)
    pool_liq = protocol.define_liquid(
        name="pool",
        description="pooled libraries",
        display_color="#00FF00"
    )
    
    # load source libraries: 50 µL each in wells A1-H6 (48 wells)
    src_wells = src_plate.wells()[:48]
    for i, well in enumerate(src_wells):
        well.load_liquid(liquid=liquids[lib_names[i]], volume=50)
    
    # destination well (A1 of destination plate) - start empty
    dst_well = dst_plate["A1"]
    dst_well.load_liquid(liquid=pool_liq, volume=0)
    
    # transfer 5 µL from each source well to destination well
    for src in src_wells:
        p20.pick_up_tip()
        p20.aspirate(5, src)
        p20.dispense(5, dst_well)
        p20.drop_tip()
