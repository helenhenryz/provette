from opentrons import protocol_api

metadata = {
    "protocolName": "PCR Set-up for 8 Samples",
    "author": "",
    "description": "Aliquot master mix and 8 samples into a 96‑well PCR plate using minimal tips.",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # ---------- Labware ----------
    tiprack = protocol.load_labware('opentrons_96_tiprack_20ul', '1')
    tuberack = protocol.load_labware('opentrons_24_tuberack_nest_1.5ml_snapcap', '2')
    plate = protocol.load_labware('nest_96_wellplate_100ul_pcr_full_skirt', '3')

    # ---------- Liquids ----------
    mm = protocol.define_liquid(
        name="master mix",
        description="PCR master mix",
        display_color="#FFD700"
    )
    sample_colors = [
        "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728",
        "#9467bd",  "#8c564b", "#e377c2",  "#7f7f7f"
    ]
    samples = {}
    for i in range(1, 9):
        name = f"sample {i}"
        liq = protocol.define_liquid(
            name=name,
            description=f"DNA sample {i}",
            display_color=sample_colors[i-1]
        )
        samples[name] = liq

    # ---------- Load initial liquids ----------
    master_tube = tuberack["A1"]
    master_tube.load_liquid(mm, volume=600)      # sufficient excess

    # ---------- Position lists ----------
    tube_cols = [f"{r}{c}" for r in "ABCD" for c in range(1, 7)]   # A1‑D6
    master_pos = tube_cols[0]                                    # A1
    sample_src_pos = tube_cols[1:9]                              # A2‑A6, B1‑B3
    rxn_wells = tube_cols[1:9]                                   # corresponding plate wells

    # ---------- Pipette ----------
    p20 = protocol.load_instrument('p20_single_gen2', 'right',
                                   tip_racks=[tiprack])

    # ----- Distribute master mix (reuse one tip) -----
    p20.pick_up_tip()
    for well in rxn_wells:
        p20.aspirate(20, master_tube)
        p20.dispense(20, plate[well])
        p20.blow_out(plate[well].top())
    p20.drop_tip()

    # ----- Add each sample (fresh tip per sample) -----
    for src_pos, dst_well in zip(sample_src_pos, rxn_wells):
        p20.pick_up_tip()
        src_well = tuberack[src_pos]
        p20.aspirate(5, src_well)
        p20.dispense(5, plate[dst_well])
        p20.drop_tip()
