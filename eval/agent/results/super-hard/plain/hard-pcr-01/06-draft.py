import opentrons
from opentrons import protocol_api

metadata = {"protocolName": "qPCR setup with NTC", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Labware
    tips1 = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    tips2 = protocol.load_labware("opentrons_96_tiprack_20ul", 6)
    mix_tube = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)['A1']
    water_tube = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 5)['A1']  # water source
    dest_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 3)
    src_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 4)

    # Liquids
    mix = protocol.define_liquid(name="mix", description="master mix", display_color="#FF0000")
    mix_tube.load_liquid(liquid=mix, volume=1700)  # enough for 96*15 + excess

    water = protocol.define_liquid(name="water", description="nuclease-free water", display_color="#0000FF")
    water_tube.load_liquid(liquid=water, volume=1500)  # plenty

    # Define template liquids for all source wells (including A1 which will hold water)
    for col in range(1, 13):
        for row in ['A','B','C','D','E','F','G','H']:
            well_name = f"{row}{col}"
            liq = protocol.define_liquid(name=f"template_{well_name}", description=f"sample {well_name}", display_color="#00FF00")
            src_plate[well_name].load_liquid(liquid=liq, volume=100)  # all wells get 100 ul of liquid
    # Overwrite A1 well with water instead of template liquid (but keep same liquid name)
    # Actually we loaded liquid named template_A1 with volume 100 of the liquid we just defined (which is template liquid).
    # To replace with water, we need to unload and reload? Simpler: after defining, we load water into that well.
    # We'll just load water into A1 well, overriding previous load.
    src_plate['A1'].load_liquid(liquid=water, volume=100)

    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips1, tips2])

    # Process each well with one tip per well
    for col in range(1, 13):
        for row in ['A','B','C','D','E','F','G','H']:
            dst = dest_plate[f"{row}{col}"]
            src = src_plate[f"{row}{col}"]
            p20.pick_up_tip()
            # add template or water (for A1)
            p20.aspirate(5, src)
            p20.dispense(5, dst)
            # add mix
            p20.aspirate(15, mix_tube)
            p20.dispense(15, dst)
            # Mix after addition
            p20.mix(5, 10, dst)  # 5 repetitions of 10 ul
            p20.drop_tip()
