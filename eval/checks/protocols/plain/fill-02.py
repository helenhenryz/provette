import math
from opentrons import protocol_api

metadata = {
    "protocolName": "Aliquot protein stock: 50 ul into 48 PCR strip tubes",
    "author": "Lab",
    "description": "50 ul aliquots of a protein stock from a 15 ml tube into 48 strip tubes on an aluminium block.",
}
requirements = {"robotType": "OT-2", "apiLevel": "2.19"}

N_TUBES = 48
ALIQUOT = 50
START_VOL = 3000  # ul in the 15 ml tube (2.4 ml needed)


def run(protocol: protocol_api.ProtocolContext):
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    rack = protocol.load_labware("opentrons_15_tuberack_falcon_15ml_conical", 2, "Protein stock")
    block = protocol.load_labware(
        "opentrons_96_aluminumblock_generic_pcr_strip_200ul", 3, "PCR strip tubes on aluminium block")

    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    stock = rack["A1"]
    protein = protocol.define_liquid("Protein stock", "Protein stock solution", "#2CA02C")
    stock.load_liquid(protein, START_VOL)

    dests = block.wells()[:N_TUBES]  # columns 1-6

    # Track the liquid level in the 15 ml conical so the tip stays just below the surface
    remaining = START_VOL

    def aspirate_height(vol_ul):
        cone_vol, cone_h = 1500.0, 22.0          # approximate conical bottom
        if vol_ul <= cone_vol:
            h = cone_h * (vol_ul / cone_vol) ** (1 / 3)
        else:
            h = cone_h + (vol_ul - cone_vol) / (math.pi * 7.4 ** 2)
        return max(1.5, h - 8)

    # Same liquid into empty tubes: one tip, slow pipetting and no mixing to avoid foaming
    p300.pick_up_tip()
    for d in dests:
        remaining -= ALIQUOT
        p300.aspirate(ALIQUOT, stock.bottom(aspirate_height(remaining)), rate=0.5)
        protocol.delay(seconds=1)
        p300.touch_tip(stock, v_offset=-3, speed=30)
        p300.dispense(ALIQUOT, d.bottom(2), rate=0.5)
        protocol.delay(seconds=1)
        p300.blow_out(d.top(-3))
    p300.drop_tip()

    protocol.comment("Done. Cap the strip tubes.")
