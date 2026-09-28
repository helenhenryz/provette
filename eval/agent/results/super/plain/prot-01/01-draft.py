import opentrons
from opentrons import protocol_api

metadata = {"protocolName": "Prepare SDS-PAGE samples", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Labware
    tiprack = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    source_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 2)  # protein samples
    dest_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 3)  # for gel samples
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 4)  # dye tube

    # Liquids
    dye = protocol.define_liquid(name="dye", description="4x loading dye", display_color="#FF0000")
    sample_liquids = []
    for i in range(1, 13):
        liq = protocol.define_liquid(name=f"sample {i}", description=f"Protein sample {i}", display_color="#00FF00")
        sample_liquids.append(liq)
        source_well = source_plate.wells_by_name()[f"A{i}"]
        source_well.load_liquid(liq, volume=100)  # realistic starting volume

    # dye in tube
    dye_well = tuberack.wells_by_name()["A1"]
    dye_well.load_liquid(dye, volume=500)  # enough for 12*5 ul

    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tiprack])

    for i in range(12):
        p20.pick_up_tip()
        src = source_plate.wells_by_name()[f"A{i+1}"]
        dst = dest_plate.wells_by_name()[f"A{i+1}"]
        # add dye first (shared reagent)
        p20.aspirate(5, dye_well)
        p20.dispense(5, dst)
        # add sample
        p20.aspirate(15, src)
        p20.dispense(15, dst)
        # mix to ensure homogeneity
        p20.mix(3, 20, dst)
        p20.drop_tip()
