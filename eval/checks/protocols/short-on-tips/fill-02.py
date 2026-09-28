from opentrons import protocol_api

metadata = {
    "protocolName": "Aliquot 50 ul protein stock into 48 PCR strip tubes",
    "description": "From a 15 ml tube into strip tubes on an aluminium block. 1 tip in total.",
}
requirements = {"robotType": "OT-2", "apiLevel": "2.19"}

N = 48
VOL = 50


def run(protocol: protocol_api.ProtocolContext):
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 4)
    rack = protocol.load_labware("opentrons_15_tuberack_falcon_15ml_conical", 1, "Protein stock")
    block = protocol.load_labware("opentrons_96_aluminumblock_generic_pcr_strip_200ul", 2, "Strip tubes")
    p300 = protocol.load_instrument("p300_single_gen2", "left", tip_racks=[tips])

    stock = rack["A1"]
    protein = protocol.define_liquid("Protein stock", "Protein stock solution", "#ff7f0e")
    stock.load_liquid(protein, 3000)  # 48 x 50 = 2.4 ml + 20 ul kept in the tip + dead volume

    dests = block.wells()[:N]  # columns 1-6

    # Same liquid into empty tubes -> one tip. Slow flow and no blow-out into
    # the tubes to avoid foaming the protein.
    p300.flow_rate.aspirate = 50
    p300.flow_rate.dispense = 50
    p300.pick_up_tip()
    extra = 20  # kept in the tip for accuracy, returned to the stock each round
    per_round = 5
    for k in range(0, N, per_round):
        group = dests[k:k + per_round]
        p300.aspirate(VOL * len(group) + extra, stock.bottom(3))
        protocol.delay(seconds=1)
        for w in group:
            p300.dispense(VOL, w.bottom(2))
            protocol.delay(seconds=0.5)
        p300.dispense(extra, stock.bottom(3))
    p300.drop_tip()
