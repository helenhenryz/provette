"""Declared rules: a YAML file loads into RULES, a bad file fails with the file and the field,
and a proposed rule can never block."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from provette.check import CheckResult
from provette.rules import RULES
from provette.rules.declared import (
    DECLARED_DIR,
    SOURCES,
    DeclaredRuleError,
    build,
    load_file,
    load_rules,
    preview,
    save,
    validate,
)
from tests.rules.conftest import RULE_FIXTURES

DROP = object()  # in a test's change: leave the field out
GOOD: dict[str, Any] = {
    "id": "NO-SAMPLE-INTO-STOCK",
    "shape": "no_carry_over",
    "title": "A tip that had been in a sample went into a stock",
    "severity": "error",
    "carried_role": "sample",
    "into_role": "stock",
    "why": "A sample in a shared tube reaches every well the tube reaches.",
    "fix": "Use a fresh tip at line {line}.",
    "sources": ["LAB_MANAGER_CARRY_OVER"],
    "proposed_by": "a student",
    "status": "proposed",
    "adopted_on": None,
}


def test_every_file_in_the_directory_loads_and_is_in_rules() -> None:
    files = sorted(DECLARED_DIR.glob("*.yaml"))
    assert files, "no declared rules"
    by_id = {rule.rule_id: rule for rule in RULES}
    for path in files:
        declared = load_file(path)
        assert declared.id == path.stem
        rule = by_id[declared.id]
        assert rule.status == declared.status
        assert rule.proposed_by == declared.proposed_by
        assert rule.sources == declared.sources
    # declared rules come after the Python rules, in file order
    assert [r.rule_id for r in RULES][-len(files) :] == [p.stem for p in files]


def test_enzyme_before_diluent_is_declared_and_adopted() -> None:
    rule = next(r for r in RULES if r.rule_id == "ENZYME-BEFORE-DILUENT")
    assert rule.status == "adopted" and rule.proposed_by == "the team"
    assert rule.tier == "role" and rule.family == 7
    assert len(rule.sources) == 4


def test_python_rules_are_adopted_by_default() -> None:
    contam = next(r for r in RULES if r.rule_id == "CONTAM-STOCK")
    assert contam.status == "adopted" and contam.proposed_by == "the team"


def test_the_registry_is_the_sources_module() -> None:
    assert "THERMO_RESTRICTION_ENZYMES" in SOURCES and "LAB_MANAGER_CARRY_OVER" in SOURCES


def test_a_good_rule_validates() -> None:
    rule = validate(GOOD, "NO-SAMPLE-INTO-STOCK.yaml")
    assert rule.tier == "role" and rule.family == 1
    assert rule.sources == (SOURCES["LAB_MANAGER_CARRY_OVER"],)
    built = build(rule)
    assert built.rule_id == "NO-SAMPLE-INTO-STOCK" and built.status == "proposed"
    assert "sample" in built.description and "Proposed by a student" in built.description


@pytest.mark.parametrize(
    ("change", "field", "words"),
    [
        ({"shape": "no_carry_ever"}, "shape", "one of no_carry_over"),
        ({"why": DROP}, "why", "missing"),
        ({"severity": "fatal"}, "severity", "one of error, warning, note"),
        ({"sources": []}, "sources", "at least one source"),
        ({"sources": ["MY_LAB_MANUAL"]}, "sources", "not a name in provette/rules/sources.yaml"),
        ({"status": "maybe"}, "status", "one of proposed, adopted"),
        ({"status": "adopted"}, "adopted_on", "when it was adopted"),
        ({"adopted_on": "2026-09-23"}, "adopted_on", "no adoption date yet"),
        ({"adopted_on": "yesterday"}, "adopted_on", "YYYY-MM-DD"),
        ({"into_role": "any_well"}, "into_role", "one of stock"),
        ({"carried_role": DROP}, "carried_role", "missing"),
        ({"share": 0.9}, "share", "not a field of a no_carry_over rule"),
        ({"id": "no sample"}, "id", "capitals"),
    ],
)
def test_a_bad_file_names_the_file_and_the_field(
    change: dict[str, Any], field: str, words: str
) -> None:
    data = {k: v for k, v in {**GOOD, **change}.items() if v is not DROP}
    with pytest.raises(DeclaredRuleError) as caught:
        validate(data, "NO-SAMPLE-INTO-STOCK.yaml")
    message = str(caught.value)
    assert message.startswith("NO-SAMPLE-INTO-STOCK.yaml: field '" + field + "'"), message
    assert words in message, message


def test_shape_fields_are_checked() -> None:
    full = {
        **GOOD,
        "shape": "full_well_not_mixed",
        "share": 1.5,
        "stroke_share": 0.1,
    }
    del full["carried_role"], full["into_role"]
    with pytest.raises(DeclaredRuleError, match="field 'share': must be a number between 0 and 1"):
        validate(full, "x.yaml")
    after = {**GOOD, "shape": "add_after", "first": "add_first", "last": "add_first"}
    del after["carried_role"], after["into_role"]
    with pytest.raises(DeclaredRuleError, match="field 'half_clause': missing"):
        validate(after, "x.yaml")
    after["half_clause"] = True
    with pytest.raises(DeclaredRuleError, match="field 'last': must differ"):
        validate(after, "x.yaml")


def test_a_bad_file_on_disk_fails_loudly_with_its_name(tmp_path: Path) -> None:
    (tmp_path / "BAD-RULE.yaml").write_text("id: BAD-RULE\nshape: add_after\n", encoding="utf-8")
    with pytest.raises(DeclaredRuleError, match=r"BAD-RULE\.yaml: field 'title': missing"):
        load_rules(tmp_path)
    (tmp_path / "BAD-RULE.yaml").write_text("- a list\n", encoding="utf-8")
    with pytest.raises(DeclaredRuleError, match=r"BAD-RULE\.yaml: the file must be a mapping"):
        load_rules(tmp_path)
    save(GOOD, tmp_path)  # a good one, under the wrong name
    (tmp_path / "BAD-RULE.yaml").write_text(
        (tmp_path / "NO-SAMPLE-INTO-STOCK.yaml").read_text(encoding="utf-8"), encoding="utf-8"
    )
    with pytest.raises(DeclaredRuleError, match=r"BAD-RULE\.yaml: field 'id': must be the file"):
        load_rules(tmp_path)


def test_an_id_that_is_already_a_rule_does_not_load(tmp_path: Path) -> None:
    save({**GOOD, "id": "CONTAM-STOCK"}, tmp_path)
    with pytest.raises(DeclaredRuleError, match="CONTAM-STOCK is already a rule"):
        load_rules(tmp_path, taken=["CONTAM-STOCK"])


def test_save_writes_a_file_that_loads_back(tmp_path: Path) -> None:
    path = save(GOOD, tmp_path)
    assert path == tmp_path / "NO-SAMPLE-INTO-STOCK.yaml"
    again = load_file(path)
    assert again == validate(GOOD)
    text = path.read_text(encoding="utf-8")
    assert text.startswith("id: NO-SAMPLE-INTO-STOCK\nshape: no_carry_over\n")
    with pytest.raises(DeclaredRuleError, match="field 'severity'"):
        save({**GOOD, "severity": "bad"}, tmp_path)


@pytest.mark.sim
def test_a_proposed_rule_reports_notes_that_never_block(
    checked: Callable[[Path], CheckResult],
) -> None:
    fixture = RULE_FIXTURES / "NO-SAMPLE-INTO-REAGENT-WELL"
    fires = checked(fixture / "fires_one_tip_adds_samples_to_mix_wells.py")
    found = [f for f in fires.findings if f.rule_id == "NO-SAMPLE-INTO-REAGENT-WELL"]
    assert found and all(f.severity == "note" for f in found)
    assert all(f.title.startswith("(proposed) A tip that had been in a sample") for f in found)
    assert f"line {found[0].line}" in found[0].fix  # the {line} placeholder was filled
    # the same protocol under the same rule adopted: a warning, and a plain title
    adopted = load_file(DECLARED_DIR / "NO-SAMPLE-INTO-REAGENT-WELL.yaml")
    data = {**adopted.to_data(), "status": "adopted", "adopted_on": "2026-09-23"}
    as_adopted = preview(data, fixture / "fires_one_tip_adds_samples_to_mix_wells.py")
    assert [f.severity for f in as_adopted] == ["warning"]
    assert as_adopted[0].title == "A tip that had been in a sample went into a reagent"
    assert as_adopted[0].fingerprint == found[0].fingerprint
    # and a blocking check is one with an error or a warning from some other rule
    only_notes = [f for f in fires.findings if f.severity == "note"]
    assert only_notes and not any(
        f.rule_id == "NO-SAMPLE-INTO-REAGENT-WELL" and f.severity != "note" for f in fires.findings
    )


@pytest.mark.sim
def test_full_well_not_mixed_reads_the_well_capacity_fixture() -> None:
    data = {
        "id": "NO-MIX-WHEN-FULL",
        "shape": "full_well_not_mixed",
        "title": "Mixing in a nearly full well",
        "severity": "warning",
        "share": 0.9,
        "stroke_share": 0.1,
        "why": "A mixing stroke pushes air and the tip into the well, and a full well spills.",
        "fix": "Mix with a smaller stroke, or leave more room in {wells}.",
        "sources": ["OPENTRONS_LABWARE_SCHEMA"],
        "proposed_by": "a student",
        "status": "adopted",
        "adopted_on": "2026-09-23",
    }
    folder = RULE_FIXTURES / "WELL-CAPACITY"
    fired = preview(data, folder / "fires_mixing_a_nearly_full_well.py")
    assert [f.severity for f in fired] == ["warning"]
    assert fired[0].rule_id == "NO-MIX-WHEN-FULL" and fired[0].tier == "structural"
    assert "the well can take" in fired[0].explanation and fired[0].explanation.endswith("spills.")
    assert not preview(data, folder / "near_miss_deep_well_filled_without_mixing.py")
    data["share"] = 0.99
    assert not preview(data, folder / "fires_mixing_a_nearly_full_well.py")
