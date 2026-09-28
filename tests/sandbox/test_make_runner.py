"""`make_runner`: names resolve lazily, and a missing piece says which."""

from __future__ import annotations

import importlib.util

import pytest

from provette.sandbox import RUNNERS, make_runner
from provette.sandbox.docker_runner import SandboxError, docker_usable
from provette.sandbox.nebius_runner import SandboxError as NebiusSandboxError
from provette.sandbox.nebius_runner import package_tarball


def test_unknown_name() -> None:
    with pytest.raises(ValueError, match="unknown runner"):
        make_runner("cloud")
    assert RUNNERS == ("local", "docker", "nebius")


def test_local_runner_is_guarded() -> None:
    if importlib.util.find_spec("provette.agent.local_runner") is None:
        with pytest.raises(RuntimeError, match="local runner .* is not available"):
            make_runner("local")
    else:
        assert make_runner("local").name == "local"


def test_docker_without_docker_is_a_clear_error() -> None:
    if docker_usable():
        pytest.skip("Docker is usable here; the error path needs it absent")
    with pytest.raises(SandboxError, match="not usable"):
        make_runner("docker")


def test_nebius_without_key_is_a_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PROVETTE_API_KEY", raising=False)
    with pytest.raises(NebiusSandboxError, match="PROVETTE_API_KEY"):
        make_runner("nebius")


def test_package_tarball_is_deterministic() -> None:
    tar_a, digest_a = package_tarball()
    tar_b, digest_b = package_tarball()
    assert digest_a == digest_b and len(digest_a) == 12
    assert tar_a == tar_b
    assert len(tar_a) < 2_000_000, "the source tarball stays small enough to upload per build"
