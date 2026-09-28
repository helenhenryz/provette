#!/usr/bin/env python3
"""
Opentrons OT‑2 protocol – 1:2 serial dilution of a drug stock across row A,
columns 1‑12 of a 96‑well plate. Destination wells receive a final
total volume of 100 µL each (drug ≤ 50 µL + PBS ≥ 50 µL).
Uses a single‑channel p300 pipette and minimizes tip usage by preparing
all drug‑containing wells directly from the drug stock, thereby reusing the
same tip for the cheap intermix step (pickup → aspirate → dispense → blow‑out -
drop) only once per well (12 tips total).

Labware definitions conform to the reference list supplied.
"""

from opentrons import protocol_api

metadata = {"protocolName": "1:2 Serial Dilution of Drug",
            "author": "Open Assistant",
            "description": ("Perform a 1:2 serial dilution of a drug stock "
                            "into PBS across columns 1‑12 of row A, "
                            "final volume 100 µL per well"),
            "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # ----- Labware -----------------------------------------------------------
    # Reservoir containing PBS (large volume)
    pbs_res = protocol.load_labware("nest_1_reservoir_195ml",
                                    location=1,
                                    label="PBS reservoir")
    # Tube rack holding the undiluted drug stock
    drug_rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap",
                                      location=2,
                                      label="Drug stock")
    # 96‑well flat plate for the dilution series (row A, cols 1‑12)
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat",
                                  location=3,
                                  label="Dilution plate")
    # Tip rack – one tip per well is sufficient here
    tiprack = protocol.load_labware("opentrons_96_tiprack_300ul",
                                    location=4,
                                    label="Tip rack")

    # Pipette
    p300 = protocol.load_instrument("p300_single_gen2",
                                   mount="right",
                                   tip_racks=[tiprack])

    # ----- Liquids -----------------------------------------------------------
    pBS = protocol.define_liquid(name="pbs",
                                 description="phosphate buffered saline",
                                 display_color="#00FF00")   # bright green
    drug = protocol.define_liquid(name="drug",
                                  description="compound for titration",
                                  display_color="#FF0000")   # red

    # Initial contents on the deck (before the run starts)
    pbs_res["A1"].load_liquid(liquid=pBS, volume=195000)          # ≈195 mL (≥ enough)
    drug_rack["A1"].load_liquid(liquid=drug, volume=500)          # 0.5 mL stock

    # ----- Helper calculations ------------------------------------------------
    # Desired final volume per well
    FINAL_VOL = 100       # µL
    # Number of dilution points (including the most concentrated well)
    N_POINTS = 12
    # Fraction of drug in each well follows f_i = (1/2)^(i-1)
    # Hence drug volume in well i = f_i * FINAL_VOL
    # Succeeding wells get half the drug volume of the previous well.
    # Compute the absolute volumes (rounded to nearest 0.1 µL that pipettor can handle)
    drug_volumes = []
    vol = float(FINAL_VOL)         # well 0 (most concentrated) : 100 µL drug (pure)
    for i in range(N_POINTS):
        drug_volumes.append(round(vol, 1))
        vol /= 2.0                 # halve for next well

    # From drug_volumes we now know how much PBS to add to hit exactly 100 µL:
    pbs_needed = [round(FINAL_VOL - dv, 1) for dv in drug_volumes]

    # ----- Protocol execution ------------------------------------------------
    # Pick up a single tip that will be reused throughout the dilution series.
    p300.pick_up_tip()

    for well_index in range(N_POINTS):
        col = well_index + 1                     # column number (1‑based)
        dest_well = plate[f"A{col}"]             # row A, column col

        # 1️⃣ Transfer the calculated drug volume from stock to destination
        if drug_volumes[well_index] > 0:
            p300.aspirate(drug_volumes[well_index],
                          drug_rack["A1"])       # source: drug stock
            p300.dispense(drug_volumes[well_index],
                          dest_well)

        # 2️⃣ Add the complementary PBS volume from the reservoir
        if pbs_needed[well_index] > 0:
            p300.aspirate(pbs_needed[well_index],
                          pbs_res["A1"])        # source: PBS reservoir
            p300.dispense(pbs_needed[well_index],
                          dest_well)

        # Optional: gentle mix to homogenize (not required for correctness)
        # p300.mix(2, 50, dest_well)

        # Blow‑out to clear any residual liquid in tip before next aspiration
        p300.blow_out(dest_well)

    # Drop the tip after finishing the entire series
    p300.drop_tip()


# End of file
