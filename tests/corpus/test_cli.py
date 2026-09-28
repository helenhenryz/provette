from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from provette import cli
from provette.corpus import cli as corpus_cli
from tests.corpus.conftest import REPO_ROOT


def test_run_list_and_summary_through_the_provette_command(
    make_folder: Callable[..., Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    make_folder("one")
    checkout = make_folder("two", readme="## Categories\n* Sample Prep\n")
    monkeypatch.chdir(REPO_ROOT)
    monkeypatch.setattr(corpus_cli, "fetch", lambda: checkout)  # no network in this test
    monkeypatch.setattr(corpus_cli, "RUNS_DIR", tmp_path / "runs")

    assert cli.main(["corpus", "list", "--category", "sample prep"]) == 0
    assert capsys.readouterr().out.split("\t")[0] == "two"

    worker = "tests.corpus.workers_for_tests:echo"
    assert cli.main(["corpus", "run", "--worker", worker, "--jobs", "2", "--slug", "one"]) == 0
    assert "ran 1, skipped 0" in capsys.readouterr().out
    assert cli.main(["corpus", "run", "--worker", worker, "--jobs", "2"]) == 0
    assert "ran 1, skipped 1" in capsys.readouterr().out
    assert (tmp_path / "runs" / "prepared" / "two" / "two.ot2.apiv2.py").is_file()

    assert cli.main(["corpus", "summary", str(tmp_path / "runs" / "echo.jsonl")]) == 0
    assert "2 protocols" in capsys.readouterr().out
    assert cli.main(["corpus", "run", "--slug", "nope"]) == 2
