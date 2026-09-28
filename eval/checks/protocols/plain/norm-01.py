from opentrons import protocol_api

metadata = {
    "protocolName": "DNA normalization - 24 samples to 10 ng/ul in 50 ul",
    "author": "Lab",
    "description": "Adds water, then the calculated volume of each sample, into a new plate.",
}
requirements = {"robotType": "OT-2", "apiLevel": "2.19"}

CONCENTRATIONS = [
    85, 120, 44, 67, 210, 95, 33, 150, 78, 60, 101, 55,
    190, 72, 48, 130, 88, 25, 64, 110, 39, 175, 92, 58,
]  # ng/ul, sample 1..24
TARGET_CONC = 10   # ng/ul
FINAL_VOL = 50     # ul


def run(protocol: protocol_api.ProtocolContext):
    # Labware
    source_plate = protocol.load_labware("biorad_96_wellplate_200ul_pcr", 1, "Source DNA plate")
    dest_plate = protocol.load_labware("biorad_96_wellplate_200ul_pcr", 2, "Normalized DNA plate")
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 3, "Water reservoir")
    tips300 = protocol.load_labware("opentrons_96_filtertiprack_200ul", 4)
    tips20 = protocol.load_labware("opentrons_96_filtertiprack_20ul", 5)

    p300 = protocol.load_instrument("p300_single_gen2", "left", tip_racks=[tips300])
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips20])

    water = reservoir["A1"]

    # Samples 1-24 are in column order: A1-H1, A2-H2, A3-H3; same wells in the new plate
    source_wells = source_plate.wells()[: len(CONCENTRATIONS)]
    dest_wells = dest_plate.wells()[: len(CONCENTRATIONS)]

    # Volumes
    sample_vols = [round(TARGET_CONC * FINAL_VOL / c, 2) for c in CONCENTRATIONS]
    water_vols = [round(FINAL_VOL - v, 2) for v in sample_vols]
    for c, v in zip(CONCENTRATIONS, sample_vols):
        if c < TARGET_CONC or v > FINAL_VOL:
            raise ValueError(f"Sample at {c} ng/ul is too dilute to normalize to {TARGET_CONC} ng/ul")

    # Liquids
    water_liq = protocol.define_liquid(
        name="Nuclease-free water", description="Diluent", display_color="#AEC7E8"
    )
    water.load_liquid(water_liq, volume=5000)
    for i, (well, conc) in enumerate(zip(source_wells, CONCENTRATIONS)):
        shade = format(30 + i * 9, "02X")
        liq = protocol.define_liquid(
            name=f"DNA sample {i + 1}",
            description=f"DNA sample {i + 1}, {conc} ng/ul",
            display_color=f"#{shade}B0{shade}",
        )
        well.load_liquid(liq, volume=40)

    # 1. Water first (30-47.6 ul), one tip since destination wells are empty
    p300.pick_up_tip()
    for vol, well in zip(water_vols, dest_wells):
        p300.aspirate(vol, water.bottom(2))
        p300.dispense(vol, well.bottom(1))
        p300.blow_out(well.top(-2))
    p300.drop_tip()

    # 2. Samples (2.4-20 ul), fresh tip each, mix into the water
    for i, (vol, src, dest) in enumerate(zip(sample_vols, source_wells, dest_wells)):
        protocol.comment(
            f"Sample {i + 1} ({CONCENTRATIONS[i]} ng/ul): {vol} ul DNA + {water_vols[i]} ul water -> {dest.well_name}"
        )
        p20.pick_up_tip()
        p20.aspirate(vol, src.bottom(1), rate=0.5)
        p20.dispense(vol, dest.bottom(1), rate=0.5)
        p20.mix(5, 20, dest.bottom(1))
        p20.blow_out(dest.top(-2))
        p20.drop_tip()

    protocol.comment("Normalization complete: 24 samples at 10 ng/ul in 50 ul.")
