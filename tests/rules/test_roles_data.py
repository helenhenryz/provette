"""The word lists as data: `roles.yaml` is what `roles.py` matches with, an unplaced liquid is
named, and `roles_edit.add_word` teaches a word without losing a comment.

Every test that writes goes through a copy of the file under `tmp_path` and a monkeypatched
`roles.ROLES_FILE`; the real file is never written, and the lists are reloaded from it after.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from provette.model import Deck, Labware, LiquidLoad, Trace, WellKey
from provette.rules import roles, roles_edit
from provette.rules.roles import (
    LIST_NAMES,
    RolesFileError,
    entry_pattern,
    is_placed,
    load_lists,
    role_of,
    unplaced,
)
from provette.rules.roles_edit import RolesEditError, add_word, lists


@pytest.fixture
def scratch_roles(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """A copy of roles.yaml the tests may write; the real lists come back afterwards."""
    copy = tmp_path / "roles.yaml"
    copy.write_text(roles.ROLES_FILE.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(roles, "ROLES_FILE", copy)
    roles.reload()
    yield copy
    monkeypatch.undo()
    roles.reload()


# -- the file --------------------------------------------------------------------------------


def test_the_file_holds_the_seven_lists_and_the_module_uses_them() -> None:
    lists_in_file = load_lists()
    assert tuple(lists_in_file) == LIST_NAMES
    assert all(lists_in_file[name] for name in LIST_NAMES)
    assert roles.lists() == lists_in_file
    assert lists() == lists_in_file
    assert "water" in lists_in_file["carrier"] and "enzyme" in lists_in_file["add_last"]


def test_the_file_opens_with_a_note_to_its_owners() -> None:
    head = roles.ROLES_FILE.read_text(encoding="utf-8").splitlines()[:4]
    assert all(line.startswith("#") for line in head)
    assert "No programming is needed" in " ".join(head)


def test_a_plain_entry_is_a_whole_word_and_a_slashed_one_is_a_pattern() -> None:
    assert entry_pattern("master mix") == r"\bmaster\ mix\b"
    assert entry_pattern("/\\bcells?\\b/") == r"\bcells?\b"


@pytest.mark.parametrize(
    "text",
    [
        "- just a list\n",
        "sample: water\n",
        "sample: [water]\nsomething_else: [x]\n",
        "sample: [1, 2]\n",
    ],
)
def test_a_file_of_the_wrong_shape_is_refused(tmp_path: Path, text: str) -> None:
    bad = tmp_path / "roles.yaml"
    bad.write_text(text, encoding="utf-8")
    with pytest.raises(RolesFileError):
        load_lists(bad)


def test_reload_from_another_file_changes_the_answer(scratch_roles: Path) -> None:
    assert role_of("lysozyme") is None
    scratch_roles.write_text(
        "sample: []\nreagent: [lysozyme]\ncarrier: []\nadd_last: []\nadd_first: []\n"
        "mix: []\nrt: []\n",
        encoding="utf-8",
    )
    roles.reload()
    assert role_of("lysozyme") == "reagent"
    assert role_of("water") is None  # the carrier list of this file is empty
    assert not is_placed("water")


# -- unplaced liquids ------------------------------------------------------------------------


def _trace(*loads: LiquidLoad) -> Trace:
    labware = [Labware("plate", "corning_96", "plate", "2", False, None, None, {})]
    deck = Deck("p.py", "2.15", "8.8.2", labware, [], list(loads))
    return Trace(deck, [])


def _load(name: str, well: str, line: int | None, description: str | None = None) -> LiquidLoad:
    return LiquidLoad(WellKey("plate", well), name, description, 100.0, line)


def test_unplaced_names_each_unknown_liquid_once_with_its_wells_and_first_line() -> None:
    trace = _trace(
        _load("water", "A1", 10),
        _load("lysozyme", "B1", 21),
        _load("lysozyme", "C1", 22),
        _load("lysozyme", "C1", 23),
        _load("", "D1", 24),  # load_empty is not a liquid
        _load("X", "E1", 25, "the PCR master mix"),  # placed by its description
        _load("Y", "F1", 26, "no idea"),
    )
    found = unplaced(trace)
    assert [(u.name, u.wells, u.line) for u in found] == [
        ("lysozyme", ("B1 in slot 2", "C1 in slot 2"), 21),
        ("Y", ("F1 in slot 2",), 26),
    ]
    assert found[0].sentence == (
        "I do not know what 'lysozyme' is (declared at line 21): tell me whether it is a sample, "
        "a reagent, a carrier, an enzyme to add last, or a diluent to add first, and the checks "
        "that grade by what was carried will use it."
    )
    assert found[1].description == "no idea"
    assert found[0].to_json() == {
        "name": "lysozyme",
        "description": None,
        "wells": ["B1 in slot 2", "C1 in slot 2"],
        "line": 21,
        "sentence": found[0].sentence,
    }


def test_a_liquid_in_the_order_or_control_lists_only_is_placed() -> None:
    # "restriction" is in add_last and in no role list; "qpcr" is in mix only
    assert role_of("restriction") is None and is_placed("restriction")
    assert role_of("qpcr") is None and is_placed("qpcr")
    assert unplaced(_trace(_load("restriction", "A1", 1), _load("qPCR", "A2", 2))) == []


# -- adding a word ---------------------------------------------------------------------------


def test_add_word_appends_under_the_list_keeps_comments_and_reloads(scratch_roles: Path) -> None:
    before = scratch_roles.read_text(encoding="utf-8")
    assert role_of("lysozyme") is None
    add_word("reagent", "  lysozyme ")
    after = scratch_roles.read_text(encoding="utf-8")
    # every line that was there is still there, in order; one line was added
    kept = [line for line in after.splitlines() if line != "  - lysozyme"]
    assert kept == before.splitlines()
    assert after.count("#") == before.count("#")
    # it went in at the end of the reagent list, before the carrier list
    lines = after.splitlines()
    at = lines.index("  - lysozyme")
    assert lines[at - 1] == "  - spri"
    assert lines.index("carrier:") > at
    # the lists in use know it, and the file reads back with it
    assert role_of("lysozyme") == "reagent"
    assert lists()["reagent"][-1] == "lysozyme"
    assert load_lists(scratch_roles)["reagent"][-1] == "lysozyme"


def test_add_word_to_the_last_list_in_the_file(scratch_roles: Path) -> None:
    add_word("rt", "superscript")
    assert roles.is_rt_word("SuperScript II")
    assert scratch_roles.read_text(encoding="utf-8").rstrip().endswith("  - superscript")


def test_add_word_quotes_what_yaml_would_misread(scratch_roles: Path) -> None:
    add_word("carrier", "yes")
    add_word("carrier", "buffer: 10x")
    assert load_lists(scratch_roles)["carrier"][-2:] == ["yes", "buffer: 10x"]
    assert role_of("YES") == "carrier"


@pytest.mark.parametrize(
    ("list_name", "word", "why"),
    [
        ("enzymes", "lysozyme", "no list called"),
        ("reagent", "", "empty"),
        ("reagent", "   ", "empty"),
        ("reagent", "Water\nbuffer", "one line"),
        ("reagent", "# a comment", "comment"),
        ("carrier", "Water", "already in the carrier list"),
        ("sample", "/(unclosed/", "not a pattern"),
    ],
)
def test_add_word_refuses(scratch_roles: Path, list_name: str, word: str, why: str) -> None:
    before = scratch_roles.read_text(encoding="utf-8")
    with pytest.raises(RolesEditError, match=why):
        add_word(list_name, word)
    assert scratch_roles.read_text(encoding="utf-8") == before


def test_the_real_file_is_untouched_by_these_tests() -> None:
    assert roles_edit.lists() == load_lists(roles.ROLES_FILE)
    assert "lysozyme" not in roles_edit.lists()["reagent"]
