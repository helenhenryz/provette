from opentrons import protocol_api

metadata = {
    "protocolName": "Cherrypick 10 wells",
    "author": "Lab",
    "description": "10 ul from 10 chosen source wells into A1, A2 ... A10 of the destination plate.",
}
requirements = {"robotType": "OT-2", "apiLevel": "2.19"}

PICKS = ["B3", "C7", "D1", "A12", "H6", "E5", "F9", "G2", "B11", "C4"]


def run(protocol: protocol_api.ProtocolContext):
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 4)
    source = protocol.load_labware("nest_96_wellplate_200ul_flat", 1, "Source plate")
    dest = protocol.load_labware("nest_96_wellplate_200ul_flat", 2, "Destination plate")
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips])

    for i, name in enumerate(PICKS):
        liq = protocol.define_liquid(f"Sample {name}", f"Source plate sample in well {name}",
                                     "#%02x%02x90" % (240 - i * 20, 40 + i * 20))
        source[name].load_liquid(liq, 100)

    # Ten different samples -> ten tips, the minimum without cross-contamination.
    # Destination wells are consecutive along row A: A1, A2 ... A10.
    for name, d in zip(PICKS, dest.rows()[0]):
        p20.pick_up_tip()
        p20.aspirate(10, source[name])
        p20.dispense(10, d)
        p20.blow_out(d.bottom(3))
        p20.drop_tip()
