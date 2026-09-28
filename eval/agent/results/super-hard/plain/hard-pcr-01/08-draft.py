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

    # Prepare dicts for source well liquids
    template_liquids = {}
    water_liquid_A1 = None

    for col in range(1, 13):
        for row in ['A','B','C','D','E','F','G','H']:
            well_name = f"{row}{col}"
            if well_name == "A1":
                liq = protocol.define_liquid(name=f"water_{well_name}", description=f"water {well_name}", display_color="#0000FF")
                water_liquid_A1 = liq
            else:
                liq = protocol.define_liquid(name=f"template_{well_name}", description=f"sample {well_name}", display_color="#00FF00")
                template_liquids[well_name] = liq

    # Load liquids into source plate wells
    for col in range(1, 13):
        for row in ['A','B','C','D','E','F','G','H']:
            well_name = f"{row}{col}"
            if well_name == "A1":
                src_plate[well_name].load_liquid(liquid=water_liquid_A1, volume=100)
            else:
                src_plate[well_name].load_liquid(liquid=template_liquids[well_name], volume=100)

    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips1, tips2])

    # Process each well: mix first with fresh tip, then template/water with fresh tip
    for col in range(1, 13):
        for row in ['A','B','C','D','E','F','G','H']:
            dst = dest_plate[f"{row}{col}"]
            src = src_plate[f"{row}{col}"]
            # Add mix
            p20.pick_up_tip()
            p20.aspirate(15, mix_tube)
            p20.dispense(15, dst)
            p20.drop_tip()
            # Add template or water (A1)
            p20.pick_up_tip()
            p20.aspirate(5, src)
            p20.dispense(5, dst)
            # Mix after addition
            p20.mix(5, 10, dst)
            p20.drop_tip()
