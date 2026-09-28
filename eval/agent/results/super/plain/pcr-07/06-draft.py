import math
from opentrons import protocol_api

metadata = {"protocolName": "PCR setup from components", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Labware
    tips20 = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    tips300 = protocol.load_labware("opentrons_96_tiprack_300ul", 2)
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3)
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 4)
    # Pipettes
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips20])
    p300 = protocol.load_instrument("p300_single_gen2", "left", tip_racks=[tips300])

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
    # Determine sample wells: all wells except those used above
    used_wells = {"A1","A2","A3","A4","A5"}
    all_wells = [f"{row}{col}" for col in range(1,7) for row in ['A','B','C','D']]
    sample_well_names = [w for w in all_wells if w not in used_wells][:12]
    for i, (name, liq) in enumerate(sample_liquids.items()):
        well = tuberack[sample_well_names[i]]
        well.load_liquid(liquid=liq, volume=500)

    # Master mix tube: pick a free well not used by buffers or samples
    used_wells.update(set(sample_well_names))
    free_well_names = [w for w in all_wells if w not in used_wells]
    mm_well_name = free_well_names[0]  # first free well
    mm_well = tuberack[mm_well_name]

    # Pool components into MM tube (water first, then buffer, then primers, polymerase last)
    def transfer_with_appropriate_pipette(vol, src, dst):
        if vol <= 20:
            p20.pick_up_tip()
            p20.aspirate(vol, src)
            p20.dispense(vol, dst)
            p20.drop_tip()
        else:
            p300.pick_up_tip()
            p300.aspirate(vol, src)
            p300.dispense(vol, dst)
            p300.drop_tip()

    # Order: water, buffer, fwd primer, rev primer, polymerase
    components = [
        (liq_water, water_well, 150.15),   # water
        (liq_buffer, buffer_well, 143.0),  # buffer
        (liq_fwd, fwd_well, 14.3),         # fwd primer
        (liq_rev, rev_well, 14.3),         # rev primer
        (liq_polymerase, pol_well, 7.15)   # polymerase last
    ]
    for liq, src, vol in components:
        transfer_with_appropriate_pipette(vol, src, mm_well)
    # Mix master mix (use p300 for larger volume)
    p300.pick_up_tip()
    for _ in range(3):
        p300.aspirate(200, mm_well)
        p300.dispense(200, mm_well)
    p300.drop_tip()

    # Plate wells: samples in column A1-A12 row A, negative control at B1
    sample_dest_wells = [plate.wells_by_name()[f"A{col}"] for col in range(1, 13)]  # A1..A12
    control_dest_well = plate.wells_by_name()["B1"]  # B1

    # Distribute master mix to all wells (samples + control)
    all_dest_wells = sample_dest_wells + [control_dest_well]
    for well in all_dest_wells:
        p300.pick_up_tip()
        p300.aspirate(23, mm_well)
        p300.dispense(23, well)
        p300.drop_tip()

    # Add templates (2 ul each) to sample wells, water to control well, then mix
    for i, (name, liq) in enumerate(sample_liquids.items()):
        dest_well = sample_dest_wells[i]
        sample_well = tuberack[sample_well_names[i]]
        p20.pick_up_tip()
        p20.aspirate(2, sample_well)
        p20.dispense(2, dest_well)
        # Mix after addition: 5 cycles of 20 ul
        p20.mix(5, 20, dest_well)
        p20.drop_tip()

    # Negative control: add 2 ul water instead of template
    p20.pick_up_tip()
    p20.aspirate(2, water_well)
    p20.dispense(2, control_dest_well)
    p20.mix(5, 20, control_dest_well)
    p20.drop_tip()

    protocol.comment("PCR setup complete with negative control and mixing")
