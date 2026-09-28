"""The image installs the project as a wheel and runs `python -m api.worker` from a temporary
directory, so `api` must be a package of the wheel. Locally the editable install hides a miss
(the project root is on the path); this pins it. Measured: without it every
analysis in the container failed with "No module named 'api'"."""

from __future__ import annotations

import re

from api.settings import REPO


def test_the_wheel_ships_the_api_package() -> None:
    text = (REPO / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r"^packages = \[(.*?)\]", text, flags=re.M)
    assert m, "the hatch packages line is missing"
    assert '"api"' in m.group(1) and '"provette"' in m.group(1)
