"""What the deployment relies on (deploy/README.md): the files a student edits from the pages
are read from wherever PROVETTE_ROLES_FILE, PROVETTE_SOURCES_FILE and PROVETTE_DECLARED_DIR point,
by a fresh process (every check is a subprocess), and the analysis cache key changes when one
of them does; and the simulation slots bound how many analyses run at once."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from api import analysis
from api.settings import REPO

SHIPPED = REPO / "provette/rules"


def _in_fresh_process(env: dict[str, str], code: str) -> str:
    done = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True,
        env={**{k: v for k, v in os.environ.items() if k != "PYTHONPATH"}, **env},
        cwd=REPO,
    )
    return done.stdout.strip()


def test_a_fresh_process_reads_the_three_files_from_the_environment(tmp_path: Path) -> None:
    live = tmp_path / "rules"
    (live / "declared").mkdir(parents=True)
    shutil.copy(SHIPPED / "roles.yaml", live / "roles.yaml")
    shutil.copy(SHIPPED / "sources.yaml", live / "sources.yaml")
    for path in (SHIPPED / "declared").glob("*.yaml"):
        shutil.copy(path, live / "declared" / path.name)
    env = {
        "PROVETTE_ROLES_FILE": str(live / "roles.yaml"),
        "PROVETTE_SOURCES_FILE": str(live / "sources.yaml"),
        "PROVETTE_DECLARED_DIR": str(live / "declared"),
    }
    out = _in_fresh_process(
        env,
        "from provette.rules import declared, roles, sources, RULES\n"
        "print(roles.ROLES_FILE); print(sources.SOURCES_FILE); print(declared.DECLARED_DIR)\n"
        "print(sum(1 for r in RULES if r.rule_id in {p.stem for p in "
        "declared.DECLARED_DIR.glob('*.yaml')}))",
    )
    lines = out.splitlines()
    assert lines[:3] == [
        str(live / "roles.yaml"),
        str(live / "sources.yaml"),
        str(live / "declared"),
    ]
    assert int(lines[3]) == len(list((live / "declared").glob("*.yaml")))
    # Without the variables, the shipped files: what a checkout runs.
    out = _in_fresh_process(
        {},
        "from provette.rules import declared, roles;"
        " print(roles.ROLES_FILE, declared.DECLARED_DIR)",
    )
    assert out == f"{SHIPPED / 'roles.yaml'} {SHIPPED / 'declared'}"


def test_the_cache_key_follows_the_live_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from provette.rules import declared

    live = tmp_path / "declared"
    live.mkdir()
    monkeypatch.setattr(declared, "DECLARED_DIR", live)
    before = analysis.key_of("print(1)", None)
    shutil.copy(next((SHIPPED / "declared").glob("*.yaml")), live / "NEW-RULE.yaml")
    assert analysis.key_of("print(1)", None) != before, (
        "a rule saved to the volume must miss the cache"
    )


def test_more_analyses_than_slots_wait_then_are_told_to_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(analysis, "_slots", threading.BoundedSemaphore(1))
    monkeypatch.setattr(analysis, "WAIT_S", 0.2)
    with analysis.slot():
        started = time.time()
        with pytest.raises(analysis.AnalysisError, match="try again"), analysis.slot():
            pass
        assert time.time() - started >= 0.2
    with analysis.slot():  # released
        pass
