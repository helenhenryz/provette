from provette.agent.prelint import prelint

FILE = """from opentrons import protocol_api

metadata = {"apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    tips = protocol.load_labware("opentrons_96_tiprack_200ul", 1)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 3)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])
    mm = protocol.define_liquid(name="master mix", description="mix")
    water = protocol.define_liquid("water", "diluent", "#aaaaaa")
    tubes["A1"].load_liquid("master mix", 500)
    tubes["A2"].load_liquid(liquid="water", volume=1000)
    tubes["A3"].load_liquid("unknown thing", 10)
"""


def test_the_four_repairs() -> None:
    lint = prelint(FILE)
    assert 'load_labware("opentrons_96_filtertiprack_200ul", 1)' in lint.text
    assert 'tubes["A1"].load_liquid(mm, 500)' in lint.text
    assert 'tubes["A2"].load_liquid(water, volume=1000)' in lint.text
    assert 'tubes["A3"].load_liquid("unknown thing", 10)' in lint.text  # nothing to map it to
    assert 'description="mix", display_color=' in lint.text
    assert lint.text.count("display_color") == 1  # water had a colour by position already
    kinds = [f.split(";")[0] for f in lint.fixes]
    assert len(lint.fixes) == 4
    assert any("opentrons_96_tiprack_200ul" in k for k in kinds)
    assert any("'master mix'" in f for f in lint.fixes) and any("'water'" in f for f in lint.fixes)


def test_a_clean_file_is_untouched() -> None:
    clean = FILE.replace("opentrons_96_tiprack_200ul", "opentrons_96_tiprack_300ul")
    clean = clean.replace('load_liquid("master mix", 500)', "load_liquid(mm, 500)")
    clean = clean.replace('load_liquid(liquid="water", volume=1000)', "load_liquid(water, 1000)")
    clean = clean.replace('description="mix")', 'description="mix", display_color="#ff0000")')
    lint = prelint(clean)
    assert lint.fixes == () and lint.text == clean


def test_a_missing_import_is_added_once() -> None:
    body = "metadata = {}\n\n\ndef run(protocol: protocol_api.ProtocolContext):\n    pass\n"
    lint = prelint(body)
    assert lint.text.startswith("from opentrons import protocol_api\n")
    assert prelint(lint.text).fixes == ()


def test_a_keyword_load_liquid_does_not_take_is_dropped() -> None:
    # e5 short-on-tips/dil-01: `ribbon=` cost every one of twenty drafts
    lint = prelint('    plate["A1"].load_liquid(mm, 100, ribbon="#ff0000")\n')
    assert lint.text == '    plate["A1"].load_liquid(mm, 100)\n'
    assert len(lint.fixes) == 1 and "'ribbon'" in lint.fixes[0]
    assert lint.fixes[0].startswith("load_liquid takes only (liquid, volume)")
    lint = prelint("well.load_liquid(liquid=mm, colour='red', volume=100, ribbon=[1, 2])\n")
    assert lint.text == "well.load_liquid(liquid=mm, volume=100)\n" and len(lint.fixes) == 2
    # the real keywords, and every other call, are left alone
    clean = ("well.load_liquid(liquid=mm, volume=100)\n"
             "p300.transfer(50, a, b, new_tip='always', ribbon=1)\n"
             "x = protocol.define_liquid(name='w', description='d', display_color='#123456')\n"
             "well.load_liquid(mm, 100)\n")  # fmt: skip
    assert prelint(clean).text == clean and prelint(clean).fixes == ()


def test_a_near_miss_labware_name_is_only_fixed_when_unambiguous() -> None:
    lint = prelint('x = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirtt", 1)\n')
    assert 'nest_96_wellplate_100ul_pcr_full_skirt"' in lint.text and len(lint.fixes) == 1
    lint = prelint('x = protocol.load_labware("some_plate_i_made_up", 1)\n')
    assert lint.fixes == ()
