from opentrons import protocol_api

metadata = {
    "protocolName": "12 restriction digests (20 ul)",
    "author": "Lab",
    "description": "12 ul water, 2 ul 10x buffer, 1 ul enzyme and 5 ul of a different plasmid per reaction; reagents at 4 C.",
}
requirements = {"robotType": "OT-2", "apiLevel": "2.19"}

N = 12


def run(protocol: protocol_api.ProtocolContext):
    temp = protocol.load_module("temperature module gen2", 1)
    block = temp.load_labware("opentrons_24_aluminumblock_nest_1.5ml_snapcap", "Reagents at 4 C")
    pcr = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 2, "Digest plate")
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 3)
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips])

    water_t, buffer_t, enzyme_t = block["A1"], block["B1"], block["C1"]
    plasmid_tubes = block.wells()[4:4 + N]          # A2 ... D4
    water = protocol.define_liquid("Water", "Nuclease-free water", "#1f77b4")
    buffer = protocol.define_liquid("10x buffer", "10x restriction buffer", "#2ca02c")
    enzyme = protocol.define_liquid("Restriction enzyme", "Restriction enzyme in 50% glycerol", "#d62728")
    water_t.load_liquid(water, 500)
    buffer_t.load_liquid(buffer, 100)
    enzyme_t.load_liquid(enzyme, 30)
    for i, t in enumerate(plasmid_tubes):
        liq = protocol.define_liquid(f"Plasmid {i + 1}", f"Plasmid DNA {i + 1} ({t.well_name})",
                                     "#%02x%02xc0" % (240 - i * 15, 80 + i * 12))
        t.load_liquid(liq, 30)

    temp.set_temperature(4)
    rxns = pcr.rows()[0][:N]     # A1-A12

    # 14 tips total.
    # Tip 1: water into the empty wells, then (same tip) buffer. When the buffer is
    # added every well holds exactly the same thing (water), so touching them
    # with one tip cannot cross-contaminate anything.
    p20.pick_up_tip()
    for w in rxns:
        p20.aspirate(12, water_t)
        p20.dispense(12, w)
    p20.blow_out(rxns[-1].top(-2))
    for chunk in (rxns[:6], rxns[6:]):
        p20.aspirate(2 * len(chunk) + 2, buffer_t)
        for w in chunk:
            p20.dispense(2, w)
        p20.dispense(2, buffer_t)      # return the excess
        p20.blow_out(buffer_t.top(-2))
    p20.drop_tip()

    # Tip 2: enzyme. One aspiration for all 12 reactions (wells are still
    # identical: water + buffer), so the tip never goes back into the stock.
    p20.pick_up_tip()
    p20.aspirate(N * 1 + 2, enzyme_t, rate=0.3)
    protocol.delay(seconds=2)
    for w in rxns:
        p20.dispense(1, w, rate=0.5)
    p20.drop_tip()                     # 2 ul excess goes with the tip

    # Tips 3-14: one per plasmid, which also mixes the finished reaction.
    for t, w in zip(plasmid_tubes, rxns):
        p20.pick_up_tip()
        p20.aspirate(5, t)
        p20.dispense(5, w)
        p20.mix(4, 12, w)
        p20.blow_out(w.top(-2))
        p20.drop_tip()

    temp.deactivate()
