from opentrons import protocol_api

metadata = {
    "protocolName": "Bradford assay duplicate",
    "author": "Assistant",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # ------- Labware -------------------------------------------------
    tips_20 = protocol.load_labware("opentrons_96_tiprack_20ul", 1)      # for 5 µL samples
    tips_300 = protocol.load_labware("opentrons_96_tiprack_300ul", 2)    # for Bradford reagent
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)     # flat 96‑well plate
    tuberack1 = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 4)
    tuberack2 = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 5)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 6)       # Bradford reagent

    # ------- Liquid definitions ---------------------------------------
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
        ("sample 1", "#A52A2A"), ("sample 2", "#DEB887"), ("sample 3", "#ADFF2F"),
        ("sample 4", "#7FFF00"), ("sample 5", "#00FA9A"), ("sample 6", "#00CED1"),
        ("sample 7", "#1E90FF"), ("sample 8", "#0000CD"), ("sample 9", "#4B0082"),
        ("sample 10", "#8A2BE2"), ("sample 11", "#2F4F4F"), ("sample 12", "#D2691E"),
        ("sample 13", "#5F9EA0"), ("sample 14", "#FFFFFF"), ("sample 15", "#C0C0C0"),
        ("sample 16", "#FFD700"), ("sample 17", "#FFA500"), ("sample 18", "#FF4500"),
        ("sample 19", "#8B0000"), ("sample 20", "#006400")
    ]

    liquid_map = {}
    for name, colour in liquids_spec:
        liquid_map[name] = protocol.define_liquid(
            name=name,
            description=f"{name} liquid",
            display_color=colour
        )

    # ------- Load liquids onto deck ------------------------------------
    # Samples: 20 tubes, 1 mL each
    sample_tubes = list(tuberack1.wells()) + list(tuberack2.wells())
    for idx, name in enumerate([n for n, _ in liquids_spec if n.startswith("sample")]):
        sample_tubes[idx].load_liquid(liquid=liquid_map[name], volume=1000)

    # Standards: already in plate wells A1–A8 (~50 µL each)
    std_wells = [plate[f"A{i+1}"] for i in range(8)]
    std_names = [n for n, _ in liquids_spec if n.startswith("standard")]
    for well, name in zip(std_wells, std_names):
        well.load_liquid(liquid=liquid_map[name], volume=50)

    # All plate wells in deterministic order
    all_wells = []
    for row in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        for col in range(1, 13):
            if len(all_wells) >= 96:
                break
            all_wells.append(plate[f"{row}{col}"])
        if len(all_wells) >= 96:
            break

    std_set = set(std_wells)
    sample_targets = [w for w in all_wells if w not in std_set][:40]  # 40 spots for duplicates

    # ------- Transfer samples (p20) ------------------------------------
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips_20])
    p20.pick_up_tip()               # keep a single tip throughout
    for i in range(20):
        src = sample_tubes[i]
        dst1 = sample_targets[2 * i]
        dst2 = sample_targets[2 * i + 1]
        p20.aspirate(10, src)        # 5 µL for each replicate
        p20.dispense(5, dst1)
        p20.dispense(5, dst2)        # tip ends empty each loop
    p20.drop_tip()

    # ------- Add Bradford reagent (p300) -------------------------------
    p300 = protocol.load_instrument("p300_single_gen2", "left", tip_racks=[tips_300])
    p300.pick_up_tip()
    reagent_source = reservoir["A1"]
    # Wells to receive reagent: standards + sample duplicates
    reagent_wells = sorted(set(std_wells) | set(sample_targets),
                           key=lambda w: (w[0], int(w[1:])))
    for well in reagent_wells:
        p300.aspirate(250, reagent_source)
        p300.dispense(250, well)
    p300.drop_tip()

# End of protocol
