"""The state replays a trace with no simulator installed (provette/state/README.md)."""

from __future__ import annotations

import subprocess
import sys


def test_importing_the_state_does_not_import_opentrons() -> None:
    # A fresh interpreter: in this process another test may already have imported opentrons.
    code = (
        "import sys, provette.state, provette.model\n"
        "bad = sorted(m for m in sys.modules if m == 'opentrons' or m.startswith('opentrons.'))\n"
        "assert not bad, bad\n"
    )
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
