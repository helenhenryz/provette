from opentrons import protocol_api

metadata = {
    "protocolName": "SDS-PAGE Sample Prep",
    "author": "Assistant",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # ----- Labware -----
    tip20 = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    tuberack_dye = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    src_samples = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 3)
    dst_mix = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 4)

    # ----- Pipettes -----
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tip20])

    # ----- Liquids -----
    dye = protocol.define_liquid(name="dye", description="4x SDS loading dye", display_color="#FF0000")
    tuberack_dye["A1"].load_liquid(liquid=dye, volume=500)  # excess dye

    # Define each sample liquid individually
    sample_names = [f"sample {i}" for i in range(1, 13)]
    sample_liquids = {}
    for name in sample_names:
        liq = protocol.define_liquid(
            name=name,
            description=f"Protein sample {name.split()[-1]}",
            display_color="#00FF00"
        )
        sample_liquids[name] = liq

    # Load the source plate with each sample (enough volume for aspirate)
    for idx, name in enumerate(sample_names):
        well = src_samples.wells()[idx]  # A1, A2, ..., H12 sequentially
        well.load_liquid(liquid=sample_liquids[name], volume=200)  # ample volume

    # ----- Protocol Steps -----
    for i in range(len(sample_names)):
        src_well = src_samples.wells()[i]
        dst_well = dst_mix.wells()[i]

        p20.pick_up_tip()
        # Take 15 µL protein sample
        p20.aspirate(15, src_well)
        p20.dispense(dst_well)
        # Add 5 µL dye
        p20.aspirate(5, tuberack_dye["A1"])
        p20.dispense(dst_well)
        # Optional mixing could be added here if desired
        p20.drop_tip()

if __name__ == "__main__":
    # Allow running the script directly for testing (not used by Opentrons)
    pass
