from opentrons import protocol_api

metadata = {
    "protocolName": "Bradford assay duplicate",
    "author": "Assistant",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.protocol_api.ProtocolContext):
    # ---- Labware -------------------------------------------------
    tips_20 = protocol.load_labware("opentrons_96_tiprack_20ul", 1)   # for sample transfers
    tips_300 = protocol.load_labware("opentrons_96_tiprack_300ul", 2)  # for Bradford reagent
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)   # flat 96‑well plate
    tuberack1 = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 4)
    tuberack2 = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 5)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 6)    # Bradford reagent

    # ---- Liquid definitions ---------------------------------------
    # Define liquids exactly as requested
    liquids_spec = [
        ("bradford", "#FF0000"),
        ("standard 1", "#FF7F00"),
        ("standard 2", "#FFFF00"),
        ("standard 3", "#00FF00"),
        ("standard 4", "#00FFFF"),
        ("standard 5", "#0000FF"),
        ("standard 6", "#8B00FF"),
        ("standard 7", "#FF00FF"),
        ("standard 8", "#FF00BF"),
        ("sample 1", "#A52A2A"),
        ("sample 2", "#DEB887"),
        ("sample 3", "#ADFF2F"),
        ("sample 4", "#7FFF00"),
        ("sample 5", "#00FA9A"),
        ("sample 6", "#00CED1"),
        ("sample 7", "#1E90FF"),
        ("sample 8", "#0000CD"),
        ("sample 9", "#4B0082"),
        ("sample 10", "#8A2BE2"),
        ("sample 11", "#2F4F4F"),
        ("sample 12", "#D2691E"),
        ("sample 13", "#5F9EA0"),
        ("sample 14", "#FFFFFF"),
        ("sample 15", "#C0C0C0"),
        ("sample 16", "#FFD700"),
        ("sample 17", "#FFA500"),
        ("sample 18", "#FF4500"),
        ("sample 19", "#8B0000"),
        ("sample 20", "#006400")
    ]

    # Create liquid objects
    liquid_map = {}
    for name, colour in liquids_spec:
        liquid_map[name] = protocol.define_liquid(name=name,
                                                 description=f"{name} liquid",
                                                 display_color=colour)

    # ---- Load liquids onto deck ------------------------------------
    # Sample tubes (20 samples)
    sample_tubes = list(tuberack1.wells()) + list(tuberack2.wells())  # 48 wells total
    for idx, name in enumerate([n for n, _ in liquids_spec if n.startswith("sample")]):
        tube = sample_tubes[idx]
        tube.load_liquid(liquid=liquid_map[name], volume=1000)  # 1 mL per sample tube

    # Standard liquids – already present in the plate (8 wells)
    std_wells = [plate[f"A{i+1}"] for i in range(8)]            # A1–A8
    std_names = [n for n, _ in liquids_spec if n.startswith("standard")]
    for well, name in zip(std_wells, std_names):
        well.load_liquid(liquid=liquid_map[name], volume=50)    # modest start volume

    # ---- Helper: ordered list of all plate wells ------------------
    all_wells = []
    for row in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        for col in range(1, 13):
            if len(all_wells) >= 96:
                break
            well_id = f"{row}{col}"
            all_wells.append(plate[well_id])
        if len(all_wells) >= 96:
            break

    # Remove the standard wells from the pool that will receive samples
    std_set = set(std_wells)
    sample_candidates = [w for w in all_wells if w not in std_set]

    # First 40 candidates → duplicate locations for the 20 samples
    sample_locations = sample_candidates[:40]                     # exactly 40 wells

    # ---- Sample transfer (p20) ------------------------------------
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips_20])
    p20.pick_up_tip()
    for i in range(20):
        src_tube = sample_tubes[i]                                 # tube for this sample
        dst1 = sample_locations[2 * i]
        dst2 = sample_locations[2 * i + 1]
        p20.aspirate(10, src_tube)                                # 5 µL per well
        p20.dispense(5, dst1)
        p20.dispense(5, dst2)
    p20.drop_tip()

    # ---- Bradford reagent addition (p300) -------------------------
    p300 = protocol.load_instrument("p300_single_gen2", "left", tip_racks=[tips_300])
    p300.pick_up_tip()
    reagent_src = reservoir["A1"]                                   # first channel, 15 mL
    targets = sorted(set(std_wells) | set(sample_locations),
                     key=lambda w: (w[0], int(w[1:])))
    for well in targets:
        p300.aspirate(250, reagent_src)
        p300.dispense(250, well)
    p300.drop_tip()


## End of protocol ##
