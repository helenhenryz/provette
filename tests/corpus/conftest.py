"""Shared by the corpus tests: the `network` marker, and a library folder written from scratch.

Nothing here is copied from the Opentrons library, which has no license (DECISIONS.md D-05).
The synthetic folders only imitate its layout.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

PROTOCOL = """\
metadata = {"protocolName": "Synthetic", "apiLevel": "2.13"}


def run(ctx):
    [volume, reuse] = get_values("volume", "tip_reuse")
    plate = ctx.load_labware("nest_96_wellplate_200ul_flat", "1")
    tips = ctx.load_labware("opentrons_96_tiprack_300ul", "2")
    pipette = ctx.load_instrument("p300_single_gen2", "right", tip_racks=[tips])
    pipette.transfer(volume, plate["A1"], plate["B1"])
"""

FIELDS: list[dict[str, Any]] = [
    {"type": "float", "label": "Volume (ul)", "name": "volume", "default": 50.0},
    {
        "type": "dropDown",
        "label": "Tip Usage Strategy",
        "name": "tip_reuse",
        "options": [{"label": "New tip", "value": "always"}, {"label": "Reuse", "value": "never"}],
    },
]

README = """\
# Synthetic

## Categories
* PCR
\t* qpcr setup

## Description
Made up.
"""


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "network: needs the internet or the real library; set PROVETTE_NETWORK=1"
    )


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    if os.environ.get("PROVETTE_NETWORK") == "1":
        return
    skip = pytest.mark.skip(reason="needs the network: set PROVETTE_NETWORK=1")
    for item in items:
        if "network" in item.keywords:
            item.add_marker(skip)


@pytest.fixture
def make_folder(tmp_path: Path) -> Callable[..., Path]:
    """Write `protocols/<slug>/` in a synthetic checkout and return the checkout."""

    def make(
        slug: str = "synthetic",
        *,
        source: str = PROTOCOL,
        fields: list[dict[str, Any]] | None = FIELDS,
        readme: str | None = README,
        labware_dir: str | None = None,
        markers: tuple[str, ...] = (),
    ) -> Path:
        folder = tmp_path / "checkout" / "protocols" / slug
        folder.mkdir(parents=True)
        (folder / f"{slug}.ot2.apiv2.py").write_text(source, encoding="utf-8")
        if fields is not None:
            (folder / "fields.json").write_text(json.dumps(fields), encoding="utf-8")
        if readme is not None:
            (folder / "README.md").write_text(readme, encoding="utf-8")
        if labware_dir:
            (folder / labware_dir).mkdir()
        for marker in markers:
            (folder / marker).touch()
        return tmp_path / "checkout"

    return make
