"""Run a worker over many prepared protocols, in parallel, one JSON line per protocol.

Every protocol runs in its own Python process, because a protocol is untrusted code and the
simulator patches globals; the process is killed, with anything it started, when it outlives
the timeout. The parent only waits on those processes, so its pool is made of threads.

A worker is named "package.module:function". It receives a `PreparedProtocol` as a plain dict
and returns a JSON-serialisable dict, its payload. If it raises, the protocol is an error.

The child process is `python -m provette.corpus.child`.
"""

from __future__ import annotations

import contextlib
import importlib
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
from collections import Counter
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from provette.corpus.prepare import PreparedProtocol

_LINE = re.compile(r"\[line (\d+)\]")  # how the simulator names the protocol line that raised

Worker = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class CorpusResult:
    out_path: Path
    ran: int  # protocols run this time
    skipped: int  # already in `out_path`, left alone
    by_status: dict[str, int]  # of the ones run this time: ok, error, timeout
    seconds: float


def load_worker(dotted: str) -> Worker:
    module_name, _, function_name = dotted.partition(":")
    if not function_name:
        raise ValueError(f"a worker is named 'package.module:function', got {dotted!r}")
    worker: Worker = getattr(importlib.import_module(module_name), function_name)
    return worker


def done_slugs(out_path: Path) -> set[str]:
    if not out_path.is_file():
        return set()
    with out_path.open(encoding="utf-8") as fh:
        return {json.loads(line)["slug"] for line in fh if line.strip()}


def first_line(text: str) -> str:
    lines = text.strip().splitlines()
    return lines[0][:300] if lines else ""


def _run_one(prepared: PreparedProtocol, worker: str, timeout_s: float) -> dict[str, Any]:
    started = time.monotonic()
    row: dict[str, Any] = {
        "slug": prepared.slug,
        "status": "error",
        "seconds": 0.0,
        "error_class": None,
        "error_message": None,
        "error_line": None,  # in the original source, when the simulator names a line
        "api_level": prepared.api_level,
        "categories": prepared.categories,
        "payload": None,
    }
    with tempfile.TemporaryDirectory(prefix="provette-corpus-") as tmp:
        result_file = Path(tmp) / "result.json"
        child = subprocess.Popen(
            [sys.executable, "-m", "provette.corpus.child", worker, str(result_file)],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,  # its own process group, so the timeout can kill all of it
        )
        try:
            _, stderr = child.communicate(json.dumps(prepared.to_dict()), timeout=timeout_s)
        except subprocess.TimeoutExpired:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(child.pid, signal.SIGKILL)
            child.communicate()
            row.update(status="timeout", error_class="Timeout", error_message=f"{timeout_s:g} s")
        else:
            if result_file.is_file():
                row.update(json.loads(result_file.read_text(encoding="utf-8")))
                named = _LINE.search(row["error_message"] or "")
                if named:
                    row["error_line"] = prepared.original_line(int(named.group(1)))
            else:  # the child died before it could report: a crash, or an os._exit
                last = stderr.strip().splitlines()[-1:] or [f"exit code {child.returncode}"]
                row.update(error_class="Crash", error_message=last[0][:300])
    row["seconds"] = round(time.monotonic() - started, 2)
    return row


def run_corpus(
    protocols: Sequence[PreparedProtocol],
    worker: str,
    *,
    jobs: int,
    timeout_s: float,
    out_path: Path,
    force: bool = False,
) -> CorpusResult:
    """Run `worker` over `protocols`, appending one JSON line to `out_path` as each finishes.

    Resumable: a slug already in `out_path` is skipped, unless `force`, which starts the file
    again. Lines are in order of completion, not of input.
    """
    started = time.monotonic()
    load_worker(worker)  # fail now, once, rather than once per protocol
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if force:
        out_path.unlink(missing_ok=True)
    done = done_slugs(out_path)
    todo = [p for p in protocols if p.slug not in done]
    by_status: Counter[str] = Counter()
    with (
        out_path.open("a", encoding="utf-8") as out,
        ThreadPoolExecutor(max_workers=jobs) as pool,
    ):
        futures = [pool.submit(_run_one, p, worker, timeout_s) for p in todo]
        for future in as_completed(futures):
            row = future.result()
            by_status[row["status"]] += 1
            out.write(json.dumps(row) + "\n")
            out.flush()
    return CorpusResult(
        out_path=out_path,
        ran=len(todo),
        skipped=len(protocols) - len(todo),
        by_status=dict(by_status),
        seconds=round(time.monotonic() - started, 1),
    )
