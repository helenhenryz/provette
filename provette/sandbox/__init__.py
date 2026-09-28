"""Where a draft protocol is run: this machine, a local Docker container, or a Nebius sandbox.

    from provette.sandbox import make_runner
    runner = make_runner("docker")          # "local" | "docker" | "nebius"
    result = runner.run_checks(protocol_text, platemap_json)
    runner.close()

Every runner satisfies `provette.agent.runner.Runner`. What they do and what was measured is in
`provette/sandbox/README.md`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from provette.agent.runner import Runner

RUNNERS = ("local", "docker", "nebius")


def make_runner(name: str) -> Runner:
    """A runner by name. Each is imported only when asked for, so a missing one costs nothing."""
    if name == "local":
        try:
            from provette.agent.local_runner import LocalRunner
        except ImportError as error:
            raise RuntimeError(
                "the local runner (provette.agent.local_runner.LocalRunner) is not available: "
                f"{error}. It is built by the agent-loop work; use 'docker' or 'nebius' meanwhile."
            ) from error
        return LocalRunner()
    if name == "docker":
        from provette.sandbox.docker_runner import DockerRunner

        return DockerRunner()
    if name == "nebius":
        from provette.sandbox.nebius_runner import NebiusRunner

        return NebiusRunner()
    raise ValueError(f"unknown runner {name!r}: choose one of {', '.join(RUNNERS)}")
