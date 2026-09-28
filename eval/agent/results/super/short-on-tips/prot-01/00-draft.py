import json
from opentrons import protocol_api

metadata = {"protocolName": "Prepare SDS-PAGE samples", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # labware
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    dye_tube = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    src_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)
    dst_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 4)

    # pipette
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])

    # define liquids
    dye = protocol.define_liquid(name="dye", description="4x loading dye", display_color="#FF0000")
    samples = []
    for i in range(1, 13):
        liq = protocol.define_liquid(name=f"sample {i}", description=f"Protein sample {i}", display_color="#00FF00")
        samples.append(liq)

    # load liquids
    dye_tube["A1"].load_liquid(liquid=dye, volume=500)  # enough for all
    for i, well in enumerate(["A1","B1","C1","D1","E1","F1","G1","H1","I1","J1","K1","L1"]):
        src_plate[well].load_liquid(liquid=samples[i], volume=100)

    # prepare samples
    dye_well = dye_tube["A1"]
    src_wells = [src_plate[w] for w in ["A1","B1","C1","D1","E1","F1","G1","H1","I1","J1","K1","L1"]]
    dst_wells = [dst_plate[w] for w in ["A1","B1","C1","D1","E1","F1","G1","H1","I1","J1","K1","L1"]]

    for src, dst in zip(src_wells, dst_wells):
        p20.pick_up_tip()
        p20.aspirate(5, dye_well)
        p20.dispense(5, dst)
        p20.aspirate(15, src)
        p20.dispense(15, dst)
        p20.mix(3, 20, dst)  # optional mix
        p20.drop_tip()
