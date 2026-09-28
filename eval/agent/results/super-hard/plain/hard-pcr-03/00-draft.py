import json
from opentrons import protocol_api

metadata = {"protocolName": "PCR setup 48 reactions", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Labware
    tuberack_comp = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 1)
    tuberack_temp1 = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    tuberack_temp2 = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3)
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 4)
    tiprack_20 = protocol.load_labware("opentrons_96_tiprack_20ul", 5)
    tiprack_300 = protocol.load_labware("opentrons_96_tiprack_300ul", 6)

    # Pipettes
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tiprack_20])
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tiprack_300])

    # Define liquids
    liquids = {}
    for i in range(1, 49):
        name = f"template {i}"
        liquids[name] = protocol.define_liquid(name=name, description=f"Template DNA {i}", display_color="#FF0000")
    liquids["fwd primer"] = protocol.define_liquid(name="fwd primer", description="Forward primer", display_color="#00FF00")
    liquids["rev primer"] = protocol.define_liquid(name="rev primer", description="Reverse primer", display_color="#0000FF")
    liquids["polymerase"] = protocol.define_liquid(name="polymerase", description="Taq polymerase", display_color="#FFA500")
    liquids["dntp"] = protocol.define_liquid(name="dntp", description="dNTP mix", display_color="#800080")
    liquids["buffer"] = protocol.define_liquid(name="buffer", description="5x buffer", display_color="#008000")
    liquids["water"] = protocol.define_liquid(name="water", description="Nuclease-free water", display_color="#00FFFF")

    # Load liquids into source wells with realistic starting volumes
    # Component tubes (rack slot 1)
    comp_map = {
        "buffer": "A1",
        "dntp": "A2",
        "polymerase": "A3",
        "fwd primer": "A4",
        "rev primer": "A5",
        "water": "A6"
    }
    for liq, well in comp_map.items():
        tuberack_comp[well].load_liquid(liquid=liquids[liq], volume=1500 if liq != "water" else 2000)

    # Template tubes (racks slot 2 and 3)
    temp_wells = [f"{row}{col}" for row in "ABCD" for col in range(1, 7)]  # A1..D6
    for i in range(1, 49):
        liq_name = f"template {i}"
        rack = tuberack_temp1 if i <= 24 else tuberack_temp2
        idx = (i-1) % 24
        well = temp_wells[idx]
        rack[well].load_liquid(liquid=liquids[liq_name], volume=50)

    # Master mix tube (use A1 of component rack after ensuring empty)
    mm_tube = tuberack_comp["A1"]
    # Ensure it's empty (we already loaded buffer there, need to move buffer elsewhere? Let's use A7 for MM)
    # Instead use A7 (but rack only up to D6). Let's use B1 for MM and move buffer to A1? Simpler: use B1 as MM and keep buffer in A1.
    mm_tube = tuberack_comp["B1"]
    mm_tube.load_liquid(liquid=protocol.define_liquid(name="master mix", description="Master mix", display_color="#FFFFFF"), volume=0)

    # Pool master mix
    # Component volumes to pool (from master_mix tool)
    pool_vols = {
        "buffer": 264.0,
        "dntp": 26.4,
        "polymerase": 13.2,
        "fwd primer": 66.0,
        "rev primer": 66.0,
        "water": 778.8
    }
    for liq, vol in pool_vols.items():
        src = tuberack_comp[comp_map[liq]]
        if vol >= 20:
            p300.pick_up_tip()
            p300.aspirate(vol, src)
            p300.dispense(vol, mm_tube)
            p300.drop_tip()
        else:
            p20.pick_up_tip()
            p20.aspirate(vol, src)
            p20.dispense(vol, mm_tube)
            p20.drop_tip()
    # Mix master mix
    p300.pick_up_tip()
    p300.aspirate(200, mm_tube)
    p300.dispense(200, mm_tube)
    p300.mix(5, 200, mm_tube)
    p300.drop_tip()

    # Distribute master mix to plate wells (first 48 wells)
    dest_wells = [f"{row}{col}" for row in "ABCD" for col in range(1, 7)]  # A1..D6 (24) need 48, actually need two rows? Let's do A1..H4? simpler: iterate 48 wells across plate.
    # Generate list of first 48 wells in column order
    all_wells = [f"{row}{col}" for col in range(1, 13) for row in "ABCDEFGH"]
    first_48 = all_wells[:48]
    p300.pick_up_tip()
    for well in first_48:
        p300.aspirate(23.0, mm_tube)
        p300.dispense(23.0, plate[well])
        # optional mix
        p300.mix(2, 20, plate[well])
    p300.drop_tip()

    # Add template (2 ul each)
    p20.pick_up_tip()
    for i, well in enumerate(first_48, start=1):
        liq_name = f"template {i}"
        rack = tuberack_temp1 if i <= 24 else tuberack_temp2
        idx = (i-1) % 24
        src_well = temp_wells[idx]
        p20.aspirate(2, rack[src_well])
        p20.dispense(2, plate[well])
    p20.drop_tip()
