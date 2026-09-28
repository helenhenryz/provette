"""The prompt's preamble and reference sheet are read from PROVETTE_EVAL_DIR when it is set: the
image keeps eval/ under /srv, not beside the code, and the first live run on the deployment
failed on `/src/eval/requests/preamble.md` before this was so."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CODE = (
    "from provette.agent import loop\n"
    "print(loop.REQUESTS)\n"
    "print(len(loop.system_prompt({'liquids': [], 'variants': []}, 'plain')))\n"
)


def _in_fresh_process(env: dict[str, str]) -> list[str]:
    done = subprocess.run(
        [sys.executable, "-c", CODE],
        capture_output=True,
        text=True,
        check=True,
        env={**{k: v for k, v in os.environ.items() if k != "PYTHONPATH"}, **env},
        cwd=REPO,
    )
    return done.stdout.strip().splitlines()


def test_the_prompt_reads_the_preamble_from_the_eval_dir_the_environment_names(
    tmp_path: Path,
) -> None:
    elsewhere = tmp_path / "eval" / "requests"
    elsewhere.mkdir(parents=True)
    for name in ("preamble.md", "reference.md"):
        shutil.copy(REPO / "eval/requests" / name, elsewhere / name)
    where, length = _in_fresh_process({"PROVETTE_EVAL_DIR": str(tmp_path / "eval")})
    assert where == str(elsewhere)
    assert int(length) > 100
    # without the setting, the checkout's own
    where, _ = _in_fresh_process({"PROVETTE_EVAL_DIR": ""})
    assert where == str(REPO / "eval/requests")
