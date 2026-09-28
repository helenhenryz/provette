from opentrons import protocol_api

metadata = {
    "protocolName": "Bradford assay for 20 protein samples (duplicate)",
    "apiLevel": "2.19"
}


def run(protocol: protocol_api.ProtocolContext):
    # ------------------------------------------------------------
    # Load labware
    # ------------------------------------------------------------
    # Tips
    tips_20 = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    tips_300 = protocol.load_labware("opentrons_96_tiprack_300ul", 2)

    # Samples (1.5 ml tubes)
    tube_rack = protocol.load_labware(
        "opentrons_24_tuberack_nest_1.5ml_snapcap", 3
    )

    # Bradford reagent reservoir
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 4)

    # Destination plate (deep well to safely hold 250 µl+sample)
    plate = protocol.load_labware("usascientific_96_wellplate_2.4ml_deep", 5)

    # ------------------------------------------------------------
    # Define liquids (all liquids on deck at start)
    # ------------------------------------------------------------
    # Use a simple colour (the exact colour is not checked by the simulator)
    colour = "#000000"

    liquids = {
        "bradford": colour,
        # BSA standards already present in the plate
        "standard 1": colour,
        "standard 2": colour,
        "standard 3": colour,
        "standard 4": colour,
        "standard 5": colour,
        "standard 6": colour,
        "standard 7": colour,
        "standard 8": colour,
        # 20 protein samples
        **{f"sample {i}": colour for i in range(1, 21)}
    }

    # Store the Liquid objects returned by define_liquid
    liquid_def = {}
    for name, col in liquids.items():
        liquid_def[name] = protocol.define_liquid(
            name=name, description="", display_color=col
        )

    # ------------------------------------------------------------
    # Map each defined liquid to a concrete well on the deck
    # ------------------------------------------------------------
    # Bradford reagent → reservoir well A1
    bradford_well = reservoir["A1"]

    # Standards → column 0 (first column) rows A‑H of the plate
    std_wells = {}
    for i in range(8):
        name = f"standard {i + 1}"
        well_name = f"{chr(ord('A') + i)}1"
        std_wells[name] = plate[well_name]

    # Samples → tube rack positions (A1‑B1‑C1‑…‑D6)
    tube_positions = [
        f"{chr(ord('A') + r)}{c + 1}"
        for c in range(6)          # columns 1‑6
        for r in range(4)          # rows A‑D
    ]
    sample_wells = {}
    for i in range(1, 21):
        name = f"sample {i}"
        tube_name = tube_positions[i - 1]
        sample_wells[name] = tube_rack[tube_name]

    # ------------------------------------------------------------
    # Prepare lists of destination wells for samples (duplicates)
    # ------------------------------------------------------------
    # Columns > 0 are free for the duplicate wells (skip column 0 which holds standards)
    candidate_dest_wells = []
    for col in range(1, 12):                # columns 2‑12 (index 1‑11)
        for row in "ABCDEFGH":              # rows A‑H
            candidate_dest_wells.append(f"{row}{col + 1}")

    # Track where each sample will go (two replicates)
    sample_tasks = []   # (source_well, dest_well, volume)
    duplicate_wells = []  # all wells that receive a sample (for reagent addition)

    for samp_num in range(1, 21):
        src = sample_wells[f"sample {samp_num}"]
        for _ in range(2):                     # duplicate
            dest_name = candidate_dest_wells.pop(0)
            dest = plate[dest_name]
            sample_tasks.append((src, dest, 5))
            duplicate_wells.append(dest)

    # ------------------------------------------------------------
    # Pipettes
    # ------------------------------------------------------------
    p20 = protocol.load_instrument(
        "p20_single_gen2", "right", tip_racks=[tips_20]
    )
    p300 = protocol.load_instrument(
        "p300_single_gen2", "left", tip_racks=[tips_300]
    )

    # ------------------------------------------------------------
    # Step 1: Transfer 5 µl of each sample to its two replicate wells
    # ------------------------------------------------------------
    for src, dst, vol in sample_tasks:
        p20.pick_up_tip()
        p20.aspirate(vol, src)
        p20.dispense(vol, dst)
        p20.drop_tip()

    # ------------------------------------------------------------
    # Step 2: Add 250 µl of Bradford reagent to every used well
    # (standards + all sample duplicate wells)
    # ------------------------------------------------------------
    used_wells = list(std_wells.values()) + duplicate_wells
    for well in used_wells:
        p300.pick_up_tip()
        p300.aspirate(250, bradford_well)
        p300.dispense(250, well)
        p300.drop_tip()
