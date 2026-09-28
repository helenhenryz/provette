# WHAT THIS TESTS (should FIRE, as a warning)
# A normalisation: 24 DNA samples, 2 to 20 ul each, into 30 to 48 ul of water so that every
# well ends at 50 ul. The DNA goes in last, nothing mixes the wells, and the run ends. DNA under
# water in a small well stays under the water, so the plate is not normalised. The DNA is a
# sample, so nothing later in the workflow will mix it: a warning. The seven wells whose DNA is
# 15 ul or more (30% of the well) are left out: an addition that big mixes as it lands.
from opentrons import protocol_api

metadata = {"protocolName": "DNA normalisation, never mixed", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 2)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3)
    tips300 = protocol.load_labware("opentrons_96_tiprack_300ul", 4)
    tips20 = protocol.load_labware("opentrons_96_tiprack_20ul", 5)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips300])
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips20])

    water = protocol.define_liquid("nuclease-free water", "diluent", "#1f77b4")
    reservoir["A1"].load_liquid(water, 5000)
    dna_ul = [2 + (i * 18) // 23 for i in range(24)]  # 2 to 20 ul, by concentration
    for i, tube in enumerate(tubes.wells()[:24]):
        dna = protocol.define_liquid(f"DNA {i + 1}", "genomic DNA to normalise", "#d62728")
        tube.load_liquid(dna, 100)

    wells = plate.wells()[:24]
    p300.pick_up_tip()
    for well, ul in zip(wells, dna_ul):
        p300.aspirate(50 - ul, reservoir["A1"])
        p300.dispense(50 - ul, well)
    p300.drop_tip()
    for tube, well, ul in zip(tubes.wells()[:24], wells, dna_ul):
        p20.transfer(ul, tube, well, new_tip="always")
