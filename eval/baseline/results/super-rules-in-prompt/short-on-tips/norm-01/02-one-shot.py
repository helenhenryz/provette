from opentrons import protocol_api

metadata = {
    "protocolName": "DNA Normalization to 10 ng/ul",
    "author": "",
    "description": "Normalizes 24 DNA samples to 10 ng/ul in 50 ul total volume.",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # ----- Labware -----
    tiprack = protocol.load_labware('opentrons_96_tiprack_20ul', '1')
    src_plate = protocol.load_labware('nest_96_wellplate_200ul_flat', '2')
    dst_plate = protocol.load_labware('nest_96_wellplate_200ul_flat', '3')
    water_res = protocol.load_labware('nest_1_reservoir_195ml', '4')  # 195 mL reservoir

    # ----- Pipettes -----
    p20 = protocol.load_instrument('p20_single_gen2', 'right', tip_racks=[tiprack])

    # ----- Liquid definitions -----
    water = protocol.define_liquid(
        name="water",
        description="Nuclease-free water",
        display_color="#FFFFFF"
    )
    sample_liquids = {}
    sample_names = [f"sample {i}" for i in range(1, 25)]
    for name in sample_names:
        liq = protocol.define_liquid(
            name=name,
            description=f"DNA sample {name.split()[1]}",
            display_color="#FF0000"
        )
        sample_liquids[name] = liq

    # ----- Initial volumes -----
    # water reservoir: plenty for all reactions
    water_res["A1"].load_liquid(liquid=water, volume=2000)   # 2 mL

    # source samples: assume each well starts with 200 µL at given concentration
    conc_map = {
        "sample 1": 85,
        "sample 2": 120,
        "sample 3": 44,
        "sample 4": 67,
        "sample 5": 210,
        "sample 6": 95,
        "sample 7": 33,
        "sample 8": 150,
        "sample 9": 78,
        "sample 10": 60,
        "sample 11": 101,
        "sample 12": 55,
        "sample 13": 190,
        "sample 14": 72,
        "sample 15": 48,
        "sample 16": 130,
        "sample 17": 88,
        "sample 18": 25,
        "sample 19": 64,
        "sample 20": 110,
        "sample 21": 39,
        "sample 22": 175,
        "sample 23": 92,
        "sample 24": 58
    }
    for name, conc in conc_map.items():
        idx = int(name.split()[1]) - 1        # zero-based index
        col = idx % 12
        row = idx // 12
        well = f"{chr(65 + row)}{col + 1}"
        src_plate[well].load_liquid(liquid=sample_liquids[name], volume=200)

    # Helper to transfer a volume possibly >20 µL using p20 in multiple steps
    def transfer_volume(vol, source, dest):
        """Transfer vol µL from source to dest using p20, splitting if >20 µL."""
        while vol > 0:
            step = min(vol, 20.0)      # p20 max is 20 µL
            p20.aspirate(step, source)
            p20.dispense(step, dest)
            vol -= step

    # ----- Normalization -----
    target_conc = 10.0   # ng/ul
    final_vol = 50.0     # ul
    target_mass = target_conc * final_vol   # 500 ng per sample

    for i, name in enumerate(sample_names, start=1):
        conc = conc_map[name]
        vol_sample = target_mass / conc          # µL of sample needed
        vol_water = final_vol - vol_sample       # µL of water needed

        # Map well index to plate coordinates
        col = (i - 1) % 12
        row = (i - 1) // 12
        well_loc = f"{chr(65 + row)}{col + 1}"
        src_well = src_plate[well_loc]
        dst_well = dst_plate[well_loc]

        p20.pick_up_tip()

        # Add water first (to minimize carryover)
        if vol_water > 0:
            transfer_volume(vol_water, water_res["A1"], dst_well)

        # Then add sample
        if vol_sample > 0:
            transfer_volume(vol_sample, src_well, dst_well)

        p20.drop_tip()


if __name__ == "__main__":
    # Not required for opentrons_simulate, but allows direct execution.
    pass
