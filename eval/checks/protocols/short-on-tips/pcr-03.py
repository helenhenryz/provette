from opentrons import protocol_api

metadata = {
    "protocolName": "96-well PCR setup: 18 ul master mix + 2 ul template",
    "author": "Lab",
    "description": "Master mix from a reservoir and template from the matching well of a sample plate.",
}
requirements = {"robotType": "OT-2", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 4)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 1)
    samples = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 2, "Template plate")
    pcr = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 3, "PCR plate")
    m20 = protocol.load_instrument("p20_multi_gen2", "left", tip_racks=[tips])

    mm = protocol.define_liquid("Master mix", "PCR master mix (96 x 18 ul + excess)", "#1f77b4")
    reservoir["A1"].load_liquid(mm, 2500)
    for i, well in enumerate(samples.wells()):
        liq = protocol.define_liquid(
            f"Template {well.well_name}", f"Template DNA sample in {well.well_name}",
            "#%02x%02x%02x" % (200, (i * 2) % 256, (255 - i * 2) % 256))
        well.load_liquid(liq, 20)

    # Tip budget: exactly one rack (96 tips).
    # Master mix goes into the EMPTY plate first with a single set of 8 tips.
    # Those tips have only touched master mix, so they are reused for the
    # first template column. Every template column then gets its own tips.
    m20.pick_up_tip()
    for col in range(12):
        m20.aspirate(18, reservoir["A1"])
        m20.dispense(18, pcr.rows()[0][col])
        m20.blow_out(pcr.rows()[0][col].top(-2))

    for col in range(12):
        if not m20.has_tip:
            m20.pick_up_tip()
        m20.aspirate(2, samples.rows()[0][col])
        m20.dispense(2, pcr.rows()[0][col])
        m20.mix(3, 10, pcr.rows()[0][col])
        m20.blow_out(pcr.rows()[0][col].top(-2))
        m20.drop_tip()
