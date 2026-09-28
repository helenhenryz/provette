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

    # Define liquids and keep references
    liq_buffer = protocol.define_liquid(name="buffer", description="assay buffer", display_color="#0000FF")
    liq_polymerase = protocol.define_liquid(name="polymerase", description="DNA polymerase", display_color="#FF0000")
    liq_fwd = protocol.define_liquid(name="fwd primer", description="forward primer", display_color="#00FF00")
    liq_rev = protocol.define_liquid(name="rev primer", description="reverse primer", display_color="#FFA500")
    liq_water = protocol.define_liquid(name="water", description="nuclease-free water", display_color="#FFFFFF")
    sample_liquids = {}
    for i in range(1, 13):
        name = f"sample {i}"
        liq = protocol.define_liquid(name=name, description=f"template {i}", display_color="#"+("{:02x}".format((i*17)%256)+"00"*2))
        sample_liquids[name] = liq

    # Load liquids into tubes (assign wells)
    buffer_well = tuberack["A1"]
    buffer_well.load_liquid(liquid=liq_buffer, volume=200)
    pol_well = tuberack["A2"]
    pol_well.load_liquid(liquid=liq_polymerase, volume=20)
    fwd_well = tuberack["A3"]
    fwd_well.load_liquid(liquid=liq_fwd, volume=30)
    rev_well = tuberack["A4"]
    rev_well.load_liquid(liquid=liq_rev, volume=30)
    water_well = tuberack["A5"]
    water_well.load_liquid(liquid=liq_water, volume=200)
    # Sample wells: fill column-wise A1,D1,A2,D2... until 12 samples
    sample_well_names = []
    for col in range(1, 7):  # columns 1-6
        for row in ['A', 'B', 'C', 'D']:
            sample_well_names.append(f"{row}{col}")
            if len(sample_well_names) == 12:
                break
        if len(sample_well_names) == 12:
            break
    for i, (name, liq) in enumerate(sample_liquids.items()):
        well = tuberack[sample_well_names[i]]
        well.load_liquid(liquid=liq, volume=500)

    # Master mix tube (use the next free well after samples, e.g., the 13th in list)
    # Continue the sequence to get a free well
    free_well_names = []
    for col in range(1, 7):
        for row in ['A', 'B', 'C', 'D']:
            w = f"{row}{col}"
            if w not in sample_well_names:
                free_well_names.append(w)
    mm_well_name = free_well_names[0]  # first free well
    mm_well = tuberack[mm_well_name]

    # Pool components into MM tube
    components = [
        (liq_buffer, buffer_well, 132),
        (liq_polymerase, pol_well, 6.6),
        (liq_fwd, fwd_well, 13.2),
        (liq_rev, rev_well, 13.2),
        (liq_water, water_well, 138.6)
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

    # Distribute master mix to wells (12 reactions) – columnwise A1..A12 of plate
    dest_wells = [plate.wells_by_name()[f"A{col}"] for col in range(1, 13)]  # plate columns 1-12 row A
    for well in dest_wells:
        p20.pick_up_tip()
        p20.aspirate(23, mm_well)
        p20.dispense(23, well)
        p20.drop_tip()

    # Add templates (2 ul each) from samples to corresponding wells
    for i, (name, liq) in enumerate(sample_liquids.items()):
        dest_well = dest_wells[i]
        sample_well = tuberack[sample_well_names[i]]
        p20.pick_up_tip()
        p20.aspirate(2, sample_well)
        p20.dispense(2, dest_well)
        p20.drop_tip()

    protocol.comment("PCR setup complete")
