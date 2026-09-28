from opentrons import protocol_api

metadata = {
    "protocolName": "PCR assembly (12 samples)",
    "author": "Assistant",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # ---- Modules & Labware ----
    # temperature module to keep reagents cold
    temp_mod = protocol.load_module("temperature module gen2", 1)
    tube_rack = temp_mod.load_labware(
        "opentrons_24_tuberack_nest_1.5ml_snapcap",   # 1.5 ml tubes
        "tubes"
    )
    # tip rack for the p20 (single‑channel)
    tiprack = protocol.load_labware("opentrons_96_tiprack_20ul", 3)

    # ---- Pipette ----
    p20 = protocol.load_instrument(
        "p20_single_gen2", "right", tip_racks=[tiprack]
    )

    # ---- Liquid definitions (must match exactly) ----
    liquids = {
        "sample 1": "#FF0000",
        "sample 2": "#00FF00",
        "sample 3": "#0000FF",
        "sample 4": "#FFFF00",
        "sample 5": "#FF00FF",
        "sample 6": "#00FFFF",
        "sample 7": "#800000",
        "sample 8": "#008000",
        "sample 9": "#000080",
        "sample 10": "#808000",
        "sample 11": "#800080",
        "sample 12": "#008080",
        "polymerase": "#FFFFFF",
        "fwd primer": "#FFA500",
        "rev primer": "#800080",
        "water": "#00BFFF",
        "buffer": "#32CD32",
    }

    def define_and_load(name, well, vol_ul):
        """Define a liquid (if not yet) and load it into a well."""
        protocol.define_liquid(
            name=name,
            description=f"{name} stock",
            display_color=liquids[name]
        )
        well.load_liquid(liquid=protocol.get_liquid_by_name(name), volume=vol_ul)

    # ---- Load stocks into the tube rack ----
    # Samples occupy A1‑A12
    for i in range(12):
        sample_name = f"sample {i+1}"
        define_and_load(sample_name, tube_rack[f"A{i+1}"], 200)  # 200 µL each

    # Reagents occupy B1‑B5
    define_and_load("polymerase",   tube_rack["B1"], 200)
    define_and_load("fwd primer",   tube_rack["B2"], 200)
    define_and_load("rev primer",   tube_rack["B3"], 200)
    define_and_load("water",        tube_rack["B4"], 1000)
    define_and_load("buffer",       tube_rack["B5"], 200)

    # Keep reagents cold
    temp_mod.set_temperature(4)          # avoid “temperature module never set” warning
    protocol.delay(seconds=2)            # give the block a moment to settle (simulation‑friendly)

    # ---- Transfer volumes per reaction ----
    V_WATER   = 10.5   # µL
    V_BUFFER  = 10.0   # µL
    V_FWD     = 1.0    # µL
    V_REV     = 1.0    # µL
    V_POLY    = 0.5    # µL
    V_SAMPLE  = 2.0    # µL

    # Destination wells (the sample tubes themselves will become the reaction vessels)
    reaction_wells = [tube_rack[f"A{i+1}"] for i in range(12)]

    def transfer_reagent(source_well, volume):
        """Aspirate from source_well and dispense the given volume into every reaction well."""
        p20.pick_up_tip()
        for dest in reaction_wells:
            p20.aspirate(volume, source_well)
            p20.dispense(volume, dest)
            # optional blow‑out to clear the tip
            p20.blow_out(dest)
        p20.drop_tip()

    # Order: water → buffer → primers → polymerase (to avoid enzyme‑before‑water warnings)
    transfer_reagent(tube_rack["B4"], V_WATER)   # water
    transfer_reagent(tube_rack["B5"], V_BUFFER)  # buffer
    transfer_reagent(tube_rack["B2"], V_FWD)     # forward primer
    transfer_reagent(tube_rack["B3"], V_REV)     # reverse primer
    transfer_reagent(tube_rack["B1"], V_POLY)    # polymerase
    # Finally add the template/sample (already present in the wells)
    # No transfer needed – the sample is already in its well.

    # Protocol ends here. All reactions are now assembled in tubes A1‑A12.
