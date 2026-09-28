from opentrons import protocol_api

metadata = {
    "protocolName": "PCR assembly from separate components - 12 samples",
    "author": "Lab",
    "description": (
        "Combines buffer mix, polymerase, primers and water into a master mix in an empty tube "
        "(0.5 ul polymerase per reaction is too small to pipette well-by-well), then dispenses "
        "23 ul master mix + 2 ul template per 25 ul reaction."
    ),
}
requirements = {"robotType": "OT-2", "apiLevel": "2.19"}

NUM_SAMPLES = 12
N_MIX = 14  # reactions' worth of master mix (12 + 2 overage)

# ul per reaction
BUFFER = 10
POLYMERASE = 0.5
FWD = 1
REV = 1
WATER = 10.5
TEMPLATE = 2
MM_PER_RXN = BUFFER + POLYMERASE + FWD + REV + WATER  # 23 ul


def run(protocol: protocol_api.ProtocolContext):
    # Labware
    cold_block = protocol.load_labware(
        "opentrons_24_aluminumblock_nest_1.5ml_snapcap", 1, "Cold block: components + templates"
    )
    pcr_plate = protocol.load_labware(
        "opentrons_96_aluminumblock_nest_wellplate_100ul", 2, "PCR plate on cold block"
    )
    tips300 = protocol.load_labware("opentrons_96_filtertiprack_200ul", 4)
    tips20 = protocol.load_labware("opentrons_96_filtertiprack_20ul", 5)

    p300 = protocol.load_instrument("p300_single_gen2", "left", tip_racks=[tips300])
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips20])

    # Cold block layout
    buffer_tube = cold_block["A1"]
    pol_tube = cold_block["A2"]
    fwd_tube = cold_block["A3"]
    rev_tube = cold_block["A4"]
    water_tube = cold_block["A5"]
    mm_tube = cold_block["A6"]  # EMPTY 1.5 ml tube for the master mix
    template_tubes = cold_block.rows()[1] + cold_block.rows()[2]  # B1-B6, C1-C6
    dest_wells = pcr_plate.rows()[0][:NUM_SAMPLES]  # A1-A12

    # Liquids
    def liquid(name, desc, color, well, vol):
        liq = protocol.define_liquid(name=name, description=desc, display_color=color)
        well.load_liquid(liq, volume=vol)

    liquid("PCR buffer mix", "Buffer mix (buffer, dNTPs, MgCl2)", "#1F77B4", buffer_tube, 200)
    liquid("DNA polymerase", "DNA polymerase in glycerol storage buffer", "#D62728", pol_tube, 20)
    liquid("Forward primer", "Forward primer working stock", "#2CA02C", fwd_tube, 50)
    liquid("Reverse primer", "Reverse primer working stock", "#9467BD", rev_tube, 50)
    liquid("Nuclease-free water", "Nuclease-free water", "#AEC7E8", water_tube, 500)
    for i, tube in enumerate(template_tubes):
        shade = format(40 + i * 15, "02X")
        liquid(f"Template {i + 1}", f"Template DNA, sample {i + 1}", f"#FF{shade}00", tube, 20)

    # 1. Build the master mix: water and buffer first, then primers, polymerase last
    p300.transfer(WATER * N_MIX, water_tube, mm_tube, new_tip="always")          # 147 ul
    p300.transfer(BUFFER * N_MIX, buffer_tube, mm_tube.bottom(3), new_tip="always")  # 140 ul
    p20.transfer(FWD * N_MIX, fwd_tube, mm_tube.bottom(3), new_tip="always", mix_after=(2, 10))  # 14 ul
    p20.transfer(REV * N_MIX, rev_tube, mm_tube.bottom(3), new_tip="always", mix_after=(2, 10))  # 14 ul

    # Polymerase is viscous: pipette slowly and rinse the tip in the mix
    p20.pick_up_tip()
    p20.aspirate(POLYMERASE * N_MIX, pol_tube.bottom(1), rate=0.3)  # 7 ul
    protocol.delay(seconds=2)
    p20.dispense(POLYMERASE * N_MIX, mm_tube.bottom(3), rate=0.3)
    p20.mix(3, 15, mm_tube.bottom(3), rate=0.5)
    p20.blow_out(mm_tube.top(-5))
    p20.drop_tip()

    # 2. Mix the master mix thoroughly (322 ul total) and dispense 23 ul per well
    p300.pick_up_tip()
    p300.mix(8, 150, mm_tube.bottom(2), rate=0.6)
    for well in dest_wells:
        p300.aspirate(MM_PER_RXN, mm_tube.bottom(1.5), rate=0.5)
        p300.dispense(MM_PER_RXN, well.bottom(1), rate=0.5)
        p300.blow_out(well.top(-2))
        p300.touch_tip(well, v_offset=-2)
    p300.drop_tip()

    # 3. Templates, fresh tip each, mix
    for src, dest in zip(template_tubes, dest_wells):
        p20.pick_up_tip()
        p20.aspirate(TEMPLATE, src.bottom(1))
        p20.dispense(TEMPLATE, dest.bottom(1))
        p20.mix(3, 15, dest.bottom(1), rate=0.5)
        p20.blow_out(dest.top(-2))
        p20.drop_tip()

    protocol.comment("Reactions assembled (25 ul each in A1-A12). Seal, spin down and transfer to the thermocycler.")
