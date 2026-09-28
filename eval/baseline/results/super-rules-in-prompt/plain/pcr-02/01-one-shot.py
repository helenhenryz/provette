{
  "metadata": {
    "protocolName": "PCR setup: 24 genomic DNA samples → 25 µL reactions",
    "author": "",
    "description": "Aliquot master mix, water, and each DNA sample into a PCR plate to form 25 µL reactions using one tip per reaction.",
    "apiLevel": "2.19"
  },
  "protocols": [
    {
      "name": "PCSetup",
      "steps": []
    }
  ]
}
import sys
if False:
    # This placeholder keeps the syntax checker happy; real code follows below.
    pass

from opentrons import protocol_api

def run(protocol: protocol_api.ProtocolContext):
    # ---------- Labware ----------
    tiprack_20 = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    sample_rack = protocol.load_labware(
        "opentrons_24_tuberack_nest_1.5ml_snapcap", 2           # DNA samples
    )
    reagent_rack = protocol.load_labware(
        "opentrons_24_tuberack_nest_1.5ml_snapcap", 3           # master mix & water
    )
    plate = protocol.load_labware(
        "nest_96_wellplate_100ul_pcr_full_skirt", 4              # PCR plate
    )

    # ---------- Pipette ----------
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tiprack_20])

    # ---------- Liquids ----------
    master_mix = protocol.define_liquid(
        name="master mix",
        description="2× PCR master mix with primers",
        display_color="#FFAA00"
    )
    water = protocol.define_liquid(
        name="water",
        description="nuclease‑free water",
        display_color="#00AAFF"
    )
    sample_liquids = []
    for i in range(1, 25):
        liq = protocol.define_liquid(
            name=f"sample {i}",
            description=f"Genomic DNA sample {i}",
            display_color="#FF0000"
        )
        sample_liquids.append(liq)

    # Load liquids onto deck
    mm_well = reagent_rack.wells()[0]     # A1 – master mix
    water_well = reagent_rack.wells()[1]  # B1 – water
    mm_well.load_liquid(liquid=master_mix, volume=500)   # µL
    water_well.load_liquid(liquid=water, volume=500)

    for well, liq in zip(sample_rack.wells(), sample_liquids):
        well.load_liquid(liquid=liq, volume=50)           # µL each sample enough for 2 µL transfers

    # ---------- Parameters ----------
    MM_VOL = 12.5   # µL master mix per reaction
    WATER_VOL = 10.5  # µL water per reaction
    SAMPLE_VOL = 2.0   # µL DNA per reaction
    NUM_REACTIONS = len(sample_rack.wells())   # 24

    src_mm = mm_well
    src_water = water_well
    dna_srcs = sample_rack.wells()[:NUM_REACTIONS]
    destinations = plate.wells()[:NUM_REACTIONS]

    # ---------- Protocol ----------
    for idx in range(NUM_REACTIONS):
        dest = destinations[idx]
        src_dna = dna_srcs[idx]

        p20.pick_up_tip()
        # Master mix
        p20.aspirate(MM_VOL, src_mm)
        p20.dispense(MM_VOL, dest)
        # Water
        p20.aspirate(WATER_VOL, src_water)
        p20.dispense(WATER_VOL, dest)
        # DNA sample
        p20.aspirate(SAMPLE_VOL, src_dna)
        p20.dispense(SAMPLE_VOL, dest)
        p20.drop_tip()  # Return tip after completing this reaction

# End of protocol
```
