# WHAT THIS TESTS (should NOT fire)
# A normalisation: 24 genomic DNA samples each go into water so that every well ends at 20 ul,
# a different DNA volume for each. There is no master mix, no polymerase and no reaction on
# this plate, so it is not a PCR plate and needs no no-template control; and each DNA is at one
# concentration in one well, so there is no dilution series to want a blank either.
from opentrons import protocol_api

metadata = {"protocolName": "normalisation of 24 DNAs into water", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 3)
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips])

    water = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 4)
    diluent = protocol.define_liquid("water", "nuclease-free water", "#1f77b4")
    water["A1"].load_liquid(diluent, 1000)
    samples = []
    for n in range(1, 25):
        dna = protocol.define_liquid(f"genomic DNA {n}", f"genomic DNA sample {n}", "#d62728")
        tubes.wells()[n - 1].load_liquid(dna, 40)
        samples.append(tubes.wells()[n - 1])

    wells = plate.wells()[:24]
    dna_ul = [2 + (n % 9) for n in range(24)]

    p20.pick_up_tip()
    for well, volume in zip(wells, dna_ul):
        p20.aspirate(20 - volume, water["A1"])
        p20.dispense(20 - volume, well)
    p20.drop_tip()

    for source, well, volume in zip(samples, wells, dna_ul):
        p20.pick_up_tip()
        p20.aspirate(volume, source)
        p20.dispense(volume, well)
        p20.mix(3, 10, well)
        p20.drop_tip()
