"""Every fixture of `tests/fixtures/protocols/` goes through `check`.

Most were written to exercise the tracer, not the rules, so what they give is frozen in
`tests/fixtures/rules/protocols/<name>.expected.json` and reviewed by eye. Two are the project's
reference pair and are asserted in full here.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from provette.check import CheckResult, check
from provette.trace import TraceError
from tests.rules.conftest import PROTOCOLS, RULE_FIXTURES, assert_matches_frozen

REJECTED = {"bad_protocol", "never_ends"}
ACCEPTED = sorted(p.stem for p in PROTOCOLS.glob("*.py") if p.stem not in REJECTED)
RACK = "2:opentrons_24_tuberack_nest_1.5ml_snapcap"
PLATE = "1:nest_96_wellplate_100ul_pcr_full_skirt"
SAMPLE_TUBES = ["B2", "B3", "B4", "B5", "B6", "C1", "C2"]


@pytest.mark.sim
@pytest.mark.parametrize("name", ACCEPTED)
def test_protocol_fixture(name: str, checked: Callable[[Path], CheckResult]) -> None:
    result = checked(PROTOCOLS / f"{name}.py")
    assert_matches_frozen(result, RULE_FIXTURES / "protocols" / f"{name}.expected.json")


@pytest.mark.sim
def test_the_clean_pcr_gives_nothing_but_the_missing_control_note(
    checked: Callable[[Path], CheckResult],
) -> None:
    """Clean of contamination: no error, no warning. The one note is NO-NEGATIVE-CONTROL: eight
    patient samples and a master mix with no no-template well, which MIQE asks for on every
    plate. The plate is what the request asked for, so it is a note, and the exit code is 0."""
    result = checked(PROTOCOLS / "pcr_clean.py")
    assert [(f.rule_id, f.severity) for f in result.findings] == [("NO-NEGATIVE-CONTROL", "note")]
    assert not result.failed


@pytest.mark.sim
def test_the_buggy_pcr(checked: Callable[[Path], CheckResult]) -> None:
    """Two findings, because two lines are wrong and two kinds of tube are spoiled.

    Line 32: the tip, wet with sample, goes into the master mix. Master mix drawn from then on
    takes the earlier samples into every later plate well: an error, seven wells downstream.
    Line 30: the same tip, now wet with master mix and the earlier samples, goes into the next
    patient's sample tube, and the sample it draws there goes into the plate. Also an error.

    The sample tubes are a finding of their own and not "downstream" of the master mix, because
    the tip carried the material into them itself: a fresh tip at line 32 alone would leave
    line 30 just as wrong. The seven plate wells are downstream of both, because either line
    alone would have spoiled them.
    """
    result = checked(PROTOCOLS / "pcr_buggy.py")
    # in file order: line 30, then line 32; the missing-control note comes after the errors
    tubes, master_mix = [f for f in result.findings if f.severity == "error"]
    assert (master_mix.rule_id, master_mix.severity, master_mix.certain) == (
        "CONTAM-STOCK",
        "error",
        True,
    )
    assert master_mix.line == 32
    assert 'rack["A1"]' in result.source_lines[master_mix.line - 1]
    assert [w.key for w in master_mix.wells] == [f"{RACK}[A1]"]
    assert master_mix.wells[0].liquid == "PCR master mix"
    plate_wells = [f"{PLATE}[A{n}]" for n in range(2, 9)]
    assert [w.key for w in master_mix.downstream.wells] == plate_wells
    assert len(master_mix.occurrences) == 8  # one finding for the whole loop
    assert "sample 1 (tube B1 in slot 2)" in master_mix.explanation

    assert (tubes.rule_id, tubes.severity, tubes.line) == ("CONTAM-STOCK", "error", 30)
    assert [w.key for w in tubes.wells] == [f"{RACK}[{t}]" for t in SAMPLE_TUBES]
    assert [w.key for w in tubes.downstream.wells] == plate_wells
    assert len(tubes.occurrences) == 7
    # no echo from other rules: the other findings are the same missing-NTC note as the clean
    # set-up gets, because this plate has no no-template well either, and the proposed declared
    # rule's note on the master-mix touch (a note, never more, while it is proposed)
    assert [(f.rule_id, f.severity) for f in result.findings] == [
        ("CONTAM-STOCK", "error"),
        ("CONTAM-STOCK", "error"),
        ("NO-SAMPLE-INTO-REAGENT-WELL", "note"),
        ("NO-NEGATIVE-CONTROL", "note"),
    ]


@pytest.mark.sim
def test_a_rejected_protocol_raises_the_simulators_error() -> None:
    with pytest.raises(TraceError) as caught:
        check(PROTOCOLS / "bad_protocol.py")
    assert caught.value.line == 15


@pytest.mark.sim
def test_a_protocol_that_never_ends_raises() -> None:
    with pytest.raises(TraceError):
        check(PROTOCOLS / "never_ends.py", timeout_s=5)
