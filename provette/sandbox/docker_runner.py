"""`DockerRunner`: the checks in a local container built from `docker/Dockerfile`.

    runner = DockerRunner()                     # image provette-checks:dev
    result = runner.run_checks(text, platemap)  # the dict of provette/agent/runner.py

Each call gets a fresh temporary folder bind-mounted at /work, no network, a hard limit of
300 seconds, and the container is removed afterwards. A failure of the container itself (no
Docker, no image, killed on time, result.json missing) raises `SandboxError`; a failure of
the protocol is reported in the dict, never raised.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any

from provette.sandbox.entrypoint import PLATEMAP, PROTOCOL, RESULT

DEFAULT_IMAGE = "provette-checks:dev"
TIMEOUT_S = 300.0


class SandboxError(RuntimeError):
    """The sandbox itself failed: not the protocol, the thing meant to run it."""


def docker_usable(docker: str = "docker") -> bool:
    """True if `docker info` succeeds for this user, without sudo."""
    if shutil.which(docker) is None:
        return False
    try:
        done = subprocess.run(
            [docker, "info"], capture_output=True, text=True, timeout=30, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return done.returncode == 0


def image_present(image: str, docker: str = "docker") -> bool:
    done = subprocess.run(
        [docker, "image", "inspect", image], capture_output=True, text=True, check=False
    )
    return done.returncode == 0


class DockerRunner:
    name = "docker"

    def __init__(
        self, image: str = DEFAULT_IMAGE, *, timeout_s: float = TIMEOUT_S, docker: str = "docker"
    ) -> None:
        self.image = image
        self.timeout_s = timeout_s
        self.docker = docker
        if not docker_usable(docker):
            raise SandboxError(
                f"{docker!r} is not usable here (not installed, or the daemon refuses this "
                "user); build the image with docker/Dockerfile on a machine that has Docker"
            )
        if not image_present(image, docker):
            raise SandboxError(
                f"the image {image!r} is not present: run "
                "`docker build -t provette-checks:dev -f docker/Dockerfile .` first"
            )

    def run_checks(self, protocol_text: str, platemap_json: dict[str, Any]) -> dict[str, Any]:
        with tempfile.TemporaryDirectory(prefix="provette-docker-") as tmp:
            work = Path(tmp)
            os.chmod(work, 0o777)  # the container writes result.json as root
            (work / PROTOCOL).write_text(protocol_text, encoding="utf-8")
            (work / PLATEMAP).write_text(json.dumps(platemap_json), encoding="utf-8")
            name = f"provette-{uuid.uuid4().hex[:12]}"
            command = [
                self.docker,
                "run",
                "--rm",
                "--name",
                name,
                "--network",
                "none",
                "-v",
                f"{work}:/work",
                self.image,
            ]
            try:
                done = subprocess.run(
                    command, capture_output=True, text=True, timeout=self.timeout_s, check=False
                )
            except subprocess.TimeoutExpired as error:
                subprocess.run([self.docker, "rm", "-f", name], capture_output=True, check=False)
                raise SandboxError(
                    f"the container did not finish within {self.timeout_s:g} s and was removed"
                ) from error
            if done.returncode != 0:
                raise SandboxError(
                    f"the container exited with {done.returncode}:\n{done.stderr[-2000:]}"
                )
            result_path = work / RESULT
            if not result_path.is_file():
                raise SandboxError("the container finished but wrote no result.json")
            result: dict[str, Any] = json.loads(result_path.read_text(encoding="utf-8"))
            return result

    def close(self) -> None:
        """Nothing is held between runs: every container is removed when its run ends."""
