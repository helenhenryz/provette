from opentrons import protocol_api

metadata = {"protocolName": "Serial Dilution", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 3)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 4)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    drug_liquid = protocol.define_liquid(name="drug", description="drug stock", display_color="#FF0000")
    pbs_liquid = protocol.define_liquid(name="pbs", description="phosphate buffered saline", display_color="#0000FF")

    tubes["A1"].load_liquid(liquid=drug_liquid, volume=1000)
    reservoir["A1"].load_liquid(liquid=pbs_liquid, volume=1500)

    p300.pick_up_tip()
    source = tubes["A1"]

    for i in range(12):
        well = plate[f"A{i+1}"]
        p300.aspirate(100, reservoir["A1"])
        p300.dispense(100, well)
        p300.aspirate(100, source)
        p300.dispense(100, well)
        p300.mix(20, 5)
        if i < 11:
            source = well

    p300.aspirate(100, plate["A12"])
    p300.drop_tip()
