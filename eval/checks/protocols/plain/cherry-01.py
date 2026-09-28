from opentrons import protocol_api

metadata = {
    "protocolName": "Cherrypick 10 wells",
    "author": "Lab",
    "description": "10 ul from 10 chosen source wells into consecutive destination wells starting at A1.",
    "apiLevel": "2.19",
}

SOURCE_WELLS = ["B3", "C7", "D1", "A12", "H6", "E5", "F9", "G2", "B11", "C4"]
VOL = 10


def run(protocol: protocol_api.ProtocolContext):
    source = protocol.load_labware("nest_96_wellplate_200ul_flat", 1, "Source plate")
    dest = protocol.load_labware("nest_96_wellplate_200ul_flat", 2, "Destination plate")
    tips = protocol.load_labware("opentrons_96_filtertiprack_20ul", 4)

    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])

    colors = ["#E41A1C", "#377EB8", "#4DAF4A", "#984EA3", "#FF7F00",
              "#A65628", "#F781BF", "#999999", "#66C2A5", "#FFD92F"]
    for name, color in zip(SOURCE_WELLS, colors):
        liq = protocol.define_liquid(f"Sample {name}", f"Sample in source well {name}", color)
        source[name].load_liquid(liq, 100)

    # Consecutive destination wells A1, B1, C1 ... (down column 1, then column 2)
    for name, d in zip(SOURCE_WELLS, dest.wells()):
        p20.pick_up_tip()
        p20.aspirate(VOL, source[name])
        p20.dispense(VOL, d)
        p20.blow_out(d.bottom(3))
        p20.drop_tip()
        protocol.comment(f"{name} -> {d.well_name}")
