from opentrons import protocol_api

metadata = {
    "protocolName": "PCR Setup for 8 Samples",
    "author": "",
    "description": "Distribute master mix and 8 samples to a 96‑well PCR plate.",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # --- Labware ------------------------------------------------------------
    tiprack = protocol.load_labware('opentrons_96_tiprack_20ul', '1')
    tuberack = protocol.load_labware('opentrons_24_tuberack_nest_1.5ml_snapcap', '2')
    plate = protocol.load_labware('nest_96_wellplate_100ul_pcr_full_skirt', '3')

    # --- Liquids -----------------------------------------------------------
    # Master mix
    master_mix = protocol.define_liquid(
        name="master mix",
        description="PCR master mix",
        display_color="#FFD700"
    )
    # Samples
    samples = {}
    colors = [
        "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728",
        "#9467bd",   "#8c564b", "#e377c2",  "#7f7f7f"
    ]
    for i in range(1, 9):
        nm = f"sample {i}"
        clr = colors[i-1]
        liq = protocol.define_liquid(
            name=nm,
            description=f"DNA sample {i}",
            display_color=clr
        )
        samples[nm] = liq

    # Initial loading of liquids in tubes
    mw_src = tuberack["A1"]
    mw_src.load_liquid(master_mix, volume=600)          # generous excess

    # Prepare lists for sample sources and destinations
    # Generate position list for tuberack (rows A-D, cols 1-6)
    tube_pos = [f"{r}{c}" for r in "ABCD" for c in range(1, 7)]
    neat_samples_orders = tube_pos[1:9]                 # A2‑A6, B1‑B3
    plat_epos = [f"{r}{c}" for r in "ABCD" for c in range(1, 7)]  # same scheme for plate
    rxn_wells = plat_epos[1:9]                          # matched to samples

    # Pipette
    p20 = protocol.load_instrument('p20_single_gen2', 'right',
                                   tip_racks=[tiprack])

    # ---- Distribute master mix (one tip) ----------------------------------
    p20.pick_up_tip()
    for dest in rxn_wells:
        p20.aspirate(20, mw_src)
        p20.dispense(20, plate[dest])
        # Optional: side‑blow to clear any hanging droplet
        p20.blow_out(plate[dest].top())
    p20.drop_tip()

    # ---- Add each sample (fresh tip per sample) ---------------------------
    for src_name in neat_samples_orders:
        src_well = tuberack[src_name]
        dst_well = plate[rxn_wells[neat_samples_orders.index(src_well)]]  # find matching index
        # Simple direct zip: rebuild pairing using enumerate
        # Implement more clear loop below:
        pass
# Unfortunately need corrected loop – rewrite below:

def run(protocol: protocol_api.protocolapi.ProtocolContext):
    ...

Instead rewrite better...


from opentrons import protocol_api

metadata = {
    "protocolName": "PCR Setup for 8 Samples",
    "author": "",
    "description": "Distribute master mix and 8 samples to a 96‑well PCR plate.",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Labware ---------------------------------------------------------------
    tiprack = protocol.load_labware('opentrons_96_tiprack_20ul', '1')
    tuberack = protocol.load_labware('opentrons_24_tuberack_nest_1.5ml_snapcap', '2')
    plate = protocol.load_labware('nest_96_wellplate_100ul_pcr_full_skirt', '3')

    # Liquids ---------------------------------------------------------------
    master_mix = protocol.define_liquid(
        name="master mix",
        description="PCR master mix",
        display_color="#FFD700"
    )

    samples = {}
    palette = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728",
               "#9467bd",  "#8c564b", "#e377c2", "#7f7f7f"]
    for i in range(1, 9):
        name = f"sample {i}"
        liq = protocol.define_liquid(
            name=name,
            description=f"DNA sample {i}",
            display_color=palette[i-1]
        )
        samples[name] = liq

    # Load liquids into tubes ------------------------------------------------
    mw_tube = tuberack["A1"]
    mw_tube.load_liquid(master_mix, volume=600)   # ample excess

    # Prepare source/destination lists ---------------------------------------
    # Positions in the tuberack/reagent plate: rows A‑D, cols 1‑6
    tube_positions = [f"{r}{c}" for r in "ABCD" for c in range(1, 7)]

    master_src = tube_positions[0]       # A1
    sample_src_positions = tube_positions[1:9]   # A2‑A6, B1‑B3

    # Corresponding reaction wells on the PCR plate
    reaction_wells = [
        f"{r}{c}"
        for r in "ABCD"
        for c in range(1, 7)
    ][1:9]                               # same slice as samples

    # Instrument -------------------------------------------------------------
    p20 = protocol.load_instrument('p20_single_gen2', 'right',
                                   tip_racks=[tiprack])

    # ---- Distribute master mix (reuse one tip) -----------------------------
    p20.pick_up_tip()
    for well in reaction_wells:
        p20.aspirate(20, mw_tube)
        p20.dispense(20, plate[well])
        p20.blow_out(plate[well].top())   # keep tip clean for next aliquot
    p20.drop_tip()

    # ---- Add each sample (new tip each time) -------------------------------
    for src_pos, dst_well in zip(sample_src_positions, reaction_wells):
        p20.pick_up_tip()
        src_well = tuberack[src_pos]
        p20.aspirate(5, src_well)
        p20.dispense(5, plate[dst_well])
        p20.drop_tip()
