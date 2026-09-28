"""Run `api.worker analyse` in a subprocess, with a timeout, a cache, and a bound on how many
simulations run at once.

The cache key is the checker's source, the protocol text and the plate map: the same three
always give the same analysis (the checker is deterministic), so a gallery episode is analysed
once and every visitor after that reads the file. The cache lives under the data directory
(`.data/cache` locally, the volume in production).

The bound is one semaphore for the whole process (`slot`): a check, a gallery episode's first
analysis and a rule preview all take a slot, so a burst of visitors cannot start more simulator
subprocesses than the machine has memory for (each peaks at about 140 MB on the largest
episode, measured in the container; `deploy/README.md`).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import subprocess
import sys
import tempfile
import threading
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

TIMEOUT_S = 360  # above the worker's own simulator limit (api/worker.py, SIMULATOR_S)
log = logging.getLogger(__name__)

# Simulator subprocesses at once, process-wide (PROVETTE_ANALYSES_AT_ONCE; 2 fits a 1 GB machine
# beside two live runs), and how long a request waits for a slot before it is told to retry.
AT_ONCE = max(1, int(os.environ.get("PROVETTE_ANALYSES_AT_ONCE", "2")))
WAIT_S = 30.0
_slots = threading.BoundedSemaphore(AT_ONCE)


class AnalysisError(RuntimeError):
    """The worker did not return an analysis (a timeout, or a crash): not a verdict."""


@contextmanager
def slot(what: str = "analyses") -> Iterator[None]:
    """One of the `AT_ONCE` simulation slots, waited for up to `WAIT_S`; `AnalysisError` when
    none frees up in time (the route answers 503 and the page says to try again)."""
    if not _slots.acquire(timeout=WAIT_S):
        raise AnalysisError(
            f"{AT_ONCE} {what} are running already and none finished in {WAIT_S:.0f} s; "
            "try again in a moment."
        )
    try:
        yield
    finally:
        _slots.release()


def checker_digest(extra_files: Sequence[Path] = ()) -> str:
    """A digest of provette's source and data files: a cached analysis is only as good as the
    checker that made it, so the key changes whenever the checker does (a new rule, a new field,
    a word taught to roles.yaml). The word lists, the sources and the declared rules are read
    from wherever the process has them (`PROVETTE_ROLES_FILE`, `PROVETTE_SOURCES_FILE`,
    `PROVETTE_DECLARED_DIR`: the volume, in production). About 200 files, a few milliseconds."""
    import provette
    from provette.rules import declared, roles, sources

    root = Path(provette.__file__).parent
    h = hashlib.sha256()
    for pattern in ("*.py", "*.yaml"):  # the code, and the word lists and declared rules it reads
        for path in sorted(root.rglob(pattern)):
            h.update(path.read_bytes())
    live = [roles.ROLES_FILE, sources.SOURCES_FILE, *sorted(declared.DECLARED_DIR.glob("*.yaml"))]
    for path in [*live, *extra_files]:  # the live files, wherever they are kept
        if path.is_file():
            h.update(path.read_bytes())
    return h.hexdigest()[:12]


def key_of(
    protocol_text: str, platemap: dict[str, Any] | None, extra_files: Sequence[Path] = ()
) -> str:
    h = hashlib.sha256()
    h.update(checker_digest(extra_files).encode("ascii"))  # each time: a taught word changes it
    h.update(b"\0")
    h.update(protocol_text.encode("utf-8"))
    h.update(b"\0")
    if platemap is not None:
        h.update(json.dumps(platemap, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    return h.hexdigest()[:32]


def analyse(
    protocol_text: str,
    platemap: dict[str, Any] | None,
    cache_dir: Path | None = None,
    timeout_s: float = TIMEOUT_S,
    roles_file: Path | None = None,
    sources_file: Path | None = None,
) -> dict[str, Any]:
    """The analysis dict `api.worker.analyse` returns, from the cache when it is there.
    `roles_file` is the word lists' file when it is not the shipped one (PROVETTE_ROLES_FILE), and
    `sources_file` the sources' (PROVETTE_SOURCES_FILE); the worker reads both."""
    extra = [p for p in (roles_file, sources_file) if p]
    cached = cache_dir / f"{key_of(protocol_text, platemap, extra)}.json" if cache_dir else None
    if cached is not None and cached.is_file():
        loaded: dict[str, Any] = json.loads(cached.read_text(encoding="utf-8"))
        return loaded
    with tempfile.TemporaryDirectory(prefix="provette-api-") as tmp:
        work = Path(tmp)
        protocol = work / "protocol.py"
        protocol.write_text(protocol_text, encoding="utf-8")
        args = [sys.executable, "-m", "api.worker", "analyse", str(protocol)]
        if platemap is not None:
            (work / "platemap.json").write_text(json.dumps(platemap), encoding="utf-8")
            args += ["--platemap", str(work / "platemap.json")]
        env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
        env["OT_API_CONFIG_DIR"] = str(work / "ot-config")
        if roles_file:
            env["PROVETTE_ROLES_FILE"] = str(roles_file)
        if sources_file:
            env["PROVETTE_SOURCES_FILE"] = str(sources_file)
        try:
            with slot():
                done = subprocess.run(
                    args, cwd=work, env=env, capture_output=True, text=True, timeout=timeout_s
                )
        except subprocess.TimeoutExpired as error:
            raise AnalysisError(f"the analysis took longer than {timeout_s:.0f} s") from error
    if done.returncode != 0:
        if "SimulatorTimeout" in done.stderr:
            # a slow or busy machine, not the protocol: say so, and cache nothing
            raise AnalysisError(
                "The checks did not finish in time; the server is busy. Try again in a minute."
            )
        # The last line of stderr is the sentence the worker chose to end on; the whole of it
        # goes to the log, not to the page.
        tail = done.stderr.strip().splitlines()[-1:] or ["no output"]
        log.error("the analysis worker failed (exit %s):\n%s", done.returncode, done.stderr)
        raise AnalysisError(f"the analysis failed: {tail[0]}")
    result: dict[str, Any] = json.loads(done.stdout)
    if cached is not None:
        cached.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = cached.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(result, separators=(",", ":")), encoding="utf-8")
        tmp_path.replace(cached)
    return result
