from opentrons import protocol_api

metadata = {
    "protocolName": "DNA Sample Normalization",
    "author": "Assistant",
    "description": "Normalize 24 DNA samples to 10 ng/ul in 50 ul total volume.",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # ------------------- Labware Setup ----------------------------------------
    # Slot 1: water reservoir
    reservoir = protocol.load_labware('nest_12_reservoir_15ml', 1)
    # Slot 2: source plate with original samples
    src_plate = protocol.load_labware('nest_96_wellplate_200ul_flat', 2)
    # Slot 3: destination plate for normalized samples
    dst_plate = protocol.load_labware('nest_96_wellplate_200ul_flat', 3)

    # ------------------- Instrument & Tips ------------------------------------
    # p20 single for transferring sample volumes (1‑20 µl)
    p20 = protocol.load_instrument('p20_single_gen2', 'right',
                                   tip_racks=[protocol.load_labware('opentrons_96_tiprack_20ul', 4)])
    # p300 single for adding water (≥20 µl)
    p300 = protocol.load_instrument('p300_single_gen2', 'left',
                                    tip_racks=[protocol.load_labware('opentrons_96_tiprack_300ul', 5)])

    # ------------------- Liquid Definitions -----------------------------------
    # Water as responsible for dilution
    water = protocol.define_liquid(
        name='water',
        description='Nuclease-free water',
        display_color='#FFFFFF'
    )
    # Define each individual sample liquid
    sample_names = [
        f'sample {i}' for i in range(1, 25)
    ]
    sample_liquids = {}
    for sn in sample_names:
        sample_liquids[sn] = protocol.define_liquid(
            name=sn,
            description=f'DNA sample {sn.split()[1]}',
            display_color='#FF0000'  # red placeholder – colour not critical
        )

    # ------------------- Initial Liquid Loading -------------------------------
    # Water – enough for all reactions plus excess (~2 mL)
    water_volume_total = 2000   # µL
    reservoir['A1'].load_liquid(liquid=water, volume=water_volume_total)

    # Samples – give each source well a realistic starting volume (200 µL)
    start_vol_per_sample = 200   # µL
    for idx, sn in enumerate(sample_names):
        row = chr(ord('A') + idx // 12)          # A‑H
        col = (idx % 12) + 1                     # 1‑12
        well_src = src_plate[f'{row}{col}']
        well_src.load_liquid(liquid=sample_liquids[sn], volume=start_vol_per_sample)

    # ------------------- Normalization Calculations ---------------------------
    target_conc = 10          # ng/ul
    target_vol = 50           # ul
    required_mass = target_conc * target_vol   # 500 ng

    # Given concentrations (ng/ul) for samples 1‑24
    concs = [
        85, 120, 44, 67, 210, 95, 33, 150,
        78, 60, 101, 55, 190, 72, 48, 130,
        88, 25, 64, 110, 39, 175, 92, 58
    ]

    # Prepare lists of sample and water volumes per well
    sample_vols = []   # µL to transfer from source
    water_vols = []    # µL of water to add
    for c in concs:
        v_sample = required_mass / c          # µL of this sample needed
        v_water = target_vol - v_sample       # rest made up with water
        sample_vols.append(v_sample)
        water_vols.append(v_water)

    # Work iteratively over the first 24 wells of the plates
    cols = [str(c) for c in range(1, 13)]
    rows = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
    well_order = [r + c for r in rows for c in cols][:24]

    for i, well in enumerate(well_order):
        src_well = src_plate[well]
        dst_well = dst_plate[well]
        samp_vol = sample_vols[i]
        wat_vol = water_vols[i]

        # ----- Transfer sample volume using p20 -----
        p20.pick_up_tip()
        p20.aspirate(samp_vol, src_well)
        p20.dispense(samp_vol, dst_well)
        p20.blow_out(dst_well)      # optional, helps clear tip
        p20.drop_tip()

        # ----- Add water using p300 -----
        p300.pick_up_tip()
        p300.aspirate(wat_vol, reservoir['A1'])
        p300.dispense(wat_vol, dst_well)
        p300.blow_out(dst_well)
        p300.drop_tip()
