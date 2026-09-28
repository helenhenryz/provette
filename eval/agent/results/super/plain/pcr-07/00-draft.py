import math
from opentrons import protocol_api

metadata = {"protocolName": "PCR setup from components", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Labware
    tips20 = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 3)
    # Pipette
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips20])

    # Define liquids
    sample_liquids = [f"sample {i}" for i in range(1, 13)]
    liquids = sample_liquids + ["polymerase", "fwd primer", "rev primer", "water", "buffer"]
    for name in liquids:
        protocol.define_liquid(name=name, description=f"{name}", display_color="#FFFFFF")

    # Load liquids into tubes (assign wells)
    # Buffer
    buffer_well = tuberack["A1"]
    buffer_well.load_liquid(liquid="buffer", volume=200)  # enough for pool + extra
    # Polymerase
    pol_well = tuberack["A2"]
    pol_well.load_liquid(liquid="polymerase", volume=20)
    # Fwd primer
    fwd_well = tuberack["A3"]
    fwd_well.load_liquid(liquid="fwd primer", volume=30)
    # Rev primer
    rev_well = tuberack["A4"]
    rev_well.load_liquid(liquid="rev primer", volume=30)
    # Water
    water_well = tuberack["A5"]
    water_well.load_liquid(liquid="water", volume=200)
    # Samples
    for i, name in enumerate(sample_liquids, start=1):
        well = tuberack[f"A{5+i}"]  # A6 onward
        well.load_liquid(liquid=name, volume=500)

    # Master mix tube (use A8)
    mm_well = tuberack["A8"]
    # Pool components into MM tube
    components = [
        ("buffer", buffer_well, 132),
        ("polymerase", pol_well, 6.6),
        ("fwd primer", fwd_well, 13.2),
        ("rev primer", rev_well, 13.2),
        ("water", water_well, 138.6)
    ]
    for liq, src, vol in components:
        p20.pick_up_tip()
        p20.aspirate(vol, src)
        p20.dispense(vol, mm_well)
        p20.drop_tip()
    # Mix master mix
    p20.pick_up_tip()
    for _ in range(3):
        p20.aspirate(150, mm_well)
        p20.dispense(150, mm_well)
    p20.drop_tip()

    # Distribute master mix to wells (12 reactions) – columnwise A1..A12
    dest_wells = [plate.wells_by_name()[f"A{col}"] for col in range(1, 13)]
    for well in dest_wells:
        p20.pick_up_tip()
        p20.aspirate(23, mm_well)
        p20.dispense(23, well)
        p20.drop_tip()

    # Add templates (2 ul each) from samples to corresponding wells
    for i, (sample_name, dest_well) in enumerate(zip(sample_liquids, dest_wells)):
        sample_well = tuberack[f"A{6+i}"]  # A6..A17
        p20.pick_up_tip()
        p20.aspirate(2, sample_well)
        p20.dispense(2, dest_well)
        p20.drop_tip()

    protocol.comment("PCR setup complete")
