# WHAT THIS TESTS (should NOT fire)
# A colony PCR: 16 colony suspensions each get 2 ul into 18 ul of Taq master mix, and a 17th
# well gets 18 ul of the mix alone. Mix alone, with nothing in place of the template, is still
# a no-template control, so the rule is silent. The mix is handed out first with one tip,
# and each colony gets its own.
from opentrons import protocol_api

metadata = {"protocolName": "colony PCR, 16 colonies, mix-only well", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 3)
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips])

    mix = protocol.define_liquid("Taq master mix", "2x Taq PCR master mix with primers", "#2ca02c")
    tubes["A1"].load_liquid(mix, 500)
    positions = [f"{row}{n}" for row in "BCD" for n in range(1, 7)][:16]
    colonies = []
    for n, position in enumerate(positions, start=1):
        colony = protocol.define_liquid(f"colony {n}", f"colony {n} in 20 ul of water", "#d62728")
        tubes[position].load_liquid(colony, 20)
        colonies.append(tubes[position])

    reactions = [plate[f"{row}{n}"] for row in "AB" for n in range(1, 9)]
    control = plate["C1"]

    p20.pick_up_tip()
    for well in reactions + [control]:
        p20.aspirate(18, tubes["A1"])
        p20.dispense(18, well)
    p20.drop_tip()

    for source, well in zip(colonies, reactions):
        p20.pick_up_tip()
        p20.aspirate(2, source)
        p20.dispense(2, well)
        p20.mix(3, 10, well)
        p20.drop_tip()
