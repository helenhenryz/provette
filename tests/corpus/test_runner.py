from __future__ import annotations

import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from provette.corpus.library import discover
from provette.corpus.prepare import PreparedProtocol, prepare
from provette.corpus.runner import run_corpus
from provette.corpus.summary import failure_reason, render, summarise
from tests.corpus.conftest import REPO_ROOT

WORKERS = "tests.corpus.workers_for_tests"


@pytest.fixture(autouse=True)
def _from_the_repo_root(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(REPO_ROOT)  # the child imports `tests.corpus...` from its working directory


@pytest.fixture
def prepared(make_folder: Callable[..., Path], tmp_path: Path) -> list[PreparedProtocol]:
    for slug in ("one", "two", "three"):
        checkout = make_folder(slug)
    return [prepare(p, tmp_path / "out") for p in discover(checkout)]


def _rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_ok_rows_carry_the_payload(prepared: list[PreparedProtocol], tmp_path: Path) -> None:
    out = tmp_path / "runs" / "echo.jsonl"
    result = run_corpus(prepared, f"{WORKERS}:echo", jobs=3, timeout_s=60, out_path=out)
    assert (result.ran, result.skipped, result.by_status) == (3, 0, {"ok": 3})
    rows = {row["slug"]: row for row in _rows(out)}
    assert set(rows) == {"one", "two", "three"}
    row = rows["two"]
    assert row["status"] == "ok" and row["error_class"] is None and row["error_message"] is None
    assert row["payload"] == {"slug": "two", "values": {"volume": 50.0, "tip_reuse": "always"}}
    assert row["api_level"] == "2.13" and row["categories"] == ["PCR"]
    assert row["seconds"] > 0


def test_a_worker_that_raises_is_an_error(prepared: list[PreparedProtocol], tmp_path: Path) -> None:
    out = tmp_path / "raises.jsonl"
    result = run_corpus(prepared[:1], f"{WORKERS}:raises", jobs=1, timeout_s=60, out_path=out)
    assert result.by_status == {"error": 1}
    [row] = _rows(out)
    assert row["status"] == "error" and row["payload"] is None
    assert row["error_class"] == "ValueError"
    assert row["error_message"] == "first line of the message"


def test_system_exit_and_a_dead_child_are_errors(
    prepared: list[PreparedProtocol], tmp_path: Path
) -> None:
    run_corpus(prepared[:1], f"{WORKERS}:exits", jobs=1, timeout_s=60, out_path=tmp_path / "a")
    [row] = _rows(tmp_path / "a")
    assert (row["status"], row["error_class"]) == ("error", "SystemExit")
    run_corpus(prepared[:1], f"{WORKERS}:dies", jobs=1, timeout_s=60, out_path=tmp_path / "b")
    [row] = _rows(tmp_path / "b")
    assert (row["status"], row["error_class"]) == ("error", "Crash")
    assert row["error_message"] == "exit code 7"


def test_a_worker_that_sleeps_is_killed_at_the_timeout(
    prepared: list[PreparedProtocol], tmp_path: Path
) -> None:
    out = tmp_path / "sleepy.jsonl"
    started = time.monotonic()
    result = run_corpus(prepared, f"{WORKERS}:sleepy", jobs=3, timeout_s=1.5, out_path=out)
    assert time.monotonic() - started < 30  # the worker would sleep for 60
    assert result.by_status == {"timeout": 3}
    assert {(r["status"], r["error_class"], r["error_message"]) for r in _rows(out)} == {
        ("timeout", "Timeout", "1.5 s")
    }


def test_a_rerun_skips_what_is_done_unless_forced(
    prepared: list[PreparedProtocol], tmp_path: Path
) -> None:
    out = tmp_path / "counted.jsonl"
    worker = f"{WORKERS}:counts_calls"

    def calls() -> int:
        return len(list((tmp_path / "out").glob("*/ran-*")))

    first = run_corpus(prepared[:2], worker, jobs=2, timeout_s=60, out_path=out)
    assert (first.ran, first.skipped, calls()) == (2, 0, 2)
    second = run_corpus(prepared, worker, jobs=2, timeout_s=60, out_path=out)
    assert (second.ran, second.skipped, calls()) == (1, 2, 3)
    assert sorted(r["slug"] for r in _rows(out)) == ["one", "three", "two"]
    third = run_corpus(prepared, worker, jobs=2, timeout_s=60, out_path=out, force=True)
    assert (third.ran, third.skipped, calls()) == (3, 0, 6)
    assert len(_rows(out)) == 3


def test_an_unknown_worker_fails_before_anything_runs(
    prepared: list[PreparedProtocol], tmp_path: Path
) -> None:
    with pytest.raises(AttributeError):
        run_corpus(prepared, f"{WORKERS}:missing", jobs=1, timeout_s=5, out_path=tmp_path / "x")
    with pytest.raises(ValueError, match="package.module:function"):
        run_corpus(prepared, "no_colon", jobs=1, timeout_s=5, out_path=tmp_path / "x")
    assert not (tmp_path / "x").exists()


@pytest.mark.sim
def test_simulate_worker_and_the_original_error_line(
    make_folder: Callable[..., Path], tmp_path: Path
) -> None:
    broken = "metadata = {'apiLevel': '2.13'}\n\n\ndef run(ctx):\n    get_values('volume')\n    ctx.load_labware('no_such_labware', '1')\n"  # noqa: E501
    make_folder("broken", source=broken)
    protocols = [prepare(p, tmp_path / "out") for p in discover(make_folder("good"))]
    out = tmp_path / "sim.jsonl"
    run_corpus(
        protocols, "provette.corpus.workers:simulate_worker", jobs=2, timeout_s=120, out_path=out
    )
    rows = {row["slug"]: row for row in _rows(out)}
    assert rows["good"]["status"] == "ok" and rows["good"]["payload"]["commands"] > 0
    assert rows["broken"]["status"] == "error"
    assert rows["broken"]["error_line"] == 6  # in the original, not the prepared copy
    assert failure_reason(rows["broken"]["error_class"], rows["broken"]["error_message"]) == (
        "custom labware missing"
    )


@pytest.mark.parametrize(
    ("error_class", "message", "reason"),
    [
        ("Timeout", "120 s", "timeout"),
        ("ExceptionInProtocolError", "KeyError [line 31]: <PipetteTipType.t20: 20>",
         "PipetteTipType KeyError"),
        ("ExceptionInProtocolError", "LabwareHeightError [line 61]: The rack is too tall",
         "labware too tall"),
        ("ExceptionInProtocolError", "FileNotFoundError [line 40]: Unable to find a labware",
         "custom labware missing"),
        ("ExceptionInProtocolError", "ValueError [line 79]: Cannot specify blowout location when "
         "using api version below 2.8, current version is 2.7", "apiLevel too low"),
        ("ExceptionInProtocolError", "AttributeError [line 50]: 'Well' object has no attribute "
         "'_impl'", "private or removed API internals"),
        ("ModuleNotFoundError", "No module named 'opentrons.protocol_api.contexts'",
         "private or removed API internals"),
        ("ExceptionInProtocolError", 'NoSuchModuleError [line 45]: Could not find a module with '
         'model "MagneticModuleModel.MAGNETIC_V2"', "module lookup broken by Python 3.11+"),
        ("ExceptionInProtocolError", "TypeError [line 82]: location should be a Location", "other"),
    ],
)  # fmt: skip
def test_failure_reason(error_class: str, message: str, reason: str) -> None:
    assert failure_reason(error_class, message) == reason


def test_summarise_and_render(tmp_path: Path) -> None:
    def row(slug: str, status: str, api: str, cats: list[str], cls: str | None = None,
            message: str | None = None) -> dict[str, Any]:  # fmt: skip
        return {"slug": slug, "status": status, "seconds": 1.5, "error_class": cls,
                "error_message": message, "api_level": api, "categories": cats,
                "payload": None}  # fmt: skip

    rows = [
        row("a", "ok", "2.9", ["PCR"]),
        row("b", "ok", "2.13", ["PCR", "Sample Prep"]),
        row("c", "error", "2.13", ["Sample Prep"], "ExceptionInProtocolError",
            "AttributeError [line 5]: 'Well' object has no attribute '_impl'"),
        row("d", "timeout", "2.9", [], "Timeout", "120 s"),
    ]  # fmt: skip
    out = tmp_path / "run.jsonl"
    out.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    summary = summarise(out)
    assert summary["total"] == 4
    assert summary["by_status"] == {"ok": 2, "error": 1, "timeout": 1}
    assert summary["failures"] == {"private or removed API internals": ["c"], "timeout": ["d"]}
    assert summary["by_category"]["PCR"] == {"ok": 2, "total": 2}
    assert summary["by_category"]["Sample Prep"] == {"ok": 1, "total": 2}
    assert summary["by_category"]["(none)"] == {"ok": 0, "total": 1}
    assert list(summary["by_api_level"]) == ["2.9", "2.13"]  # numeric order, not text order
    assert summary["by_api_level"]["2.9"] == {"ok": 1, "total": 2}
    text = render(summary)
    assert "4 protocols" in text and "private or removed API internals" in text
    json.dumps(summary)  # the summary itself is plain data
