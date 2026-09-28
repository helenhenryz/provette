"""The `docker` and `network` markers for the sandbox tests, and the fixture paths.

`docker` tests run only where `docker info` succeeds and the image is built; `network` tests
only with PROVETTE_NETWORK=1 and PROVETTE_API_KEY set (load ~/.config/provette/token-factory.env).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PROTOCOLS = REPO_ROOT / "tests" / "fixtures" / "protocols"
PLATEMAPS = REPO_ROOT / "eval" / "platemaps"


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "docker: needs a usable Docker and the provette-checks image"
    )
    config.addinivalue_line(
        "markers", "network: needs the Nebius sandbox service; set PROVETTE_NETWORK=1 and the key"
    )


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    from provette.sandbox.docker_runner import DEFAULT_IMAGE, docker_usable, image_present

    docker_ok = docker_usable() and image_present(DEFAULT_IMAGE)
    network_ok = os.environ.get("PROVETTE_NETWORK") == "1" and bool(
        os.environ.get("PROVETTE_API_KEY")
    )
    skip_docker = pytest.mark.skip(reason="needs Docker and `docker build -t provette-checks:dev`")
    skip_network = pytest.mark.skip(reason="needs the network: set PROVETTE_NETWORK=1 and the key")
    for item in items:
        if "docker" in item.keywords and not docker_ok:
            item.add_marker(skip_docker)
        if "network" in item.keywords and not network_ok:
            item.add_marker(skip_network)
