from opentrons import protocol_api

metadata = {
    "protocolName": "Seed 96-well plate with three cell lines",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    tubes = protocol.load_labware("opentrons_15_tuberack_falcon_15ml_conical", 2)
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)
    
    # Define liquids
    line1 = protocol.define_liquid("line 1", "Cell line 1 suspension", "#FF0000")
    line2 = protocol.define_liquid("line 2", "Cell line 2 suspension", "#00FF00")
    line3 = protocol.define_liquid("line 3", "Cell line 3 suspension", "#0000FF")
    
    # Load liquids into source tubes
    tubes["A1"].load_liquid(liquid=line1, volume=5000)
    tubes["A2"].load_liquid(liquid=line2, volume=5000)
    tubes["A3"].load_liquid(liquid=line3, volume=5000)
    
    # Load pipette
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])
    
    # Seed plate
    for col in range(1,13):
        if col <= 4:
            source = tubes["A1"]
        elif col <= 8:
            source = tubes["A2"]
        else:
            source = tubes["A3"]
        for row in ["A","B","C","D","E","F","G","H"]:
            well_name = row + str(col)
            p300.pick_up_tip()
            p300.aspirate(100, source)
            p300.dispense(100, plate[well_name])
            p300.drop_tip()
