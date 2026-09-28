import opentrons
from opentrons import protocol_api

metadata = {"protocolName": "PCR setup from separate components", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Define liquids
    buffer_liq = protocol.define_liquid(name="buffer", description="assay buffer", display_color="#0000FF")
    polymerase_liq = protocol.define_liquid(name="polymerase", description="Taq polymerase", display_color="#FF0000")
    fwd_liq = protocol.define_liquid(name="fwd primer", description="Forward primer", display_color="#00FF00")
    rev_liq = protocol.define_liquid(name="rev primer", description="Reverse primer", display_color="#FFFF00")
    water_liq = protocol.define_liquid(name="water", description="Nuclease-free water", display_color="#FFFFFF")
    sample_liquids = {}
    for i in range(1, 13):
        name = f"sample {i}"
        liq = protocol.define_liquid(name=name, description=f"Template sample {i}", display_color="#FFA500")
        sample_liquids[name] = liq

    # Load modules and labware
    temp_mod = protocol.load_module("temperature module gen2", "1")
    aluminum_block = temp_mod.load_labware("opentrons_24_aluminumblock_nest_1.5ml_snapcap")
    tiprack_20 = protocol.load_labware("opentrons_96_tiprack_20ul", "2")
    tiprack_300 = protocol.load_labware("opentrons_96_tiprack_300ul", "3")
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", "4")

    # Assign locations in aluminum block
    buffer_loc = aluminum_block["A1"]
    polymerase_loc = aluminum_block["A2"]
    fwd_loc = aluminum_block["A3"]
    rev_loc = aluminum_block["A4"]
    water_loc = aluminum_block["A5"]
    master_mix_loc = aluminum_block["A6"]  # tube for pooling
    # Sample locations: B1-B6 and C1-C6 (12 wells)
    sample_locs = []
    for row in ("B", "C"):
        for col in range(1, 7):
            sample_locs.append(aluminum_block[f"{row}{col}"])
    assert len(sample_locs) == 12

    # Load liquids into source wells with realistic starting volumes (<=1500 ul)
    buffer_loc.load_liquid(liquid=buffer_liq, volume=1500)
    polymerase_loc.load_liquid(liquid=polymerase_liq, volume=200)
    fwd_loc.load_liquid(liquid=fwd_liq, volume=200)
    rev_loc.load_liquid(liquid=rev_liq, volume=200)
    water_loc.load_liquid(liquid=water_liq, volume=1500)
    for i, (name, loc) in enumerate(zip([f"sample {i+1}" for i in range(12)], sample_locs), start=1):
        loc.load_liquid(liquid=sample_liquids[name], volume=50)

    # Prepare master mix (pool components)
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tiprack_20])
    p300 = protocol.load_instrument("p300_single_gen2", "left", tip_racks=[tiprack_300])

    # Buffer (large volume) with p300
    p300.pick_up_tip()
    p300.aspirate(132, buffer_loc)
    p300.dispense(132, master_mix_loc)
    p300.drop_tip()

    # Polymerase (small) with p20, fresh tip
    p20.pick_up_tip()
    p20.aspirate(6.6, polymerase_loc)
    p20.dispense(6.6, master_mix_loc)
    p20.drop_tip()

    # Fwd primer
    p20.pick_up_tip()
    p20.aspirate(13.2, fwd_loc)
    p20.dispense(13.2, master_mix_loc)
    p20.drop_tip()

    # Rev primer
    p20.pick_up_tip()
    p20.aspirate(13.2, rev_loc)
    p20.dispense(13.2, master_mix_loc)
    p20.drop_tip()

    # Water (large) with p300
    p300.pick_up_tip()
    p300.aspirate(138.6, water_loc)
    p300.dispense(138.6, master_mix_loc)
    p300.drop_tip()

    # Mix master mix
    p20.pick_up_tip()
    p20.mix(5, 150, master_mix_loc)
    p20.drop_tip()

    # Set temperature to cold (optional)
    temp_mod.set_temperature(4)
    # Distribute master mix to plate wells (A1..A12)
    p300.pick_up_tip()
    for col in range(1, 13):
        well = plate[f"A{col}"]
        p300.aspirate(23, master_mix_loc)
        p300.dispense(23, well)
        p300.blow_out(well)
    p300.drop_tip()

    # Add 2 ul sample to each well (p20)
    for i in range(12):
        p20.pick_up_tip()
        p20.aspirate(2, sample_locs[i])
        p20.dispense(2, plate[f"A{i+1}"])
        p20.mix(2, 20, plate[f"A{i+1}"])  # mix 20ul volume
        p20.drop_tip()

    # Deactivate temperature module
    temp_mod.deactivate()
