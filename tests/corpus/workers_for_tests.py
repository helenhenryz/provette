"""Workers the runner tests name by dotted path. They run in a child process."""

from __future__ import annotations

import os
import time
from typing import Any


def echo(prepared: dict[str, Any]) -> dict[str, Any]:
    return {"slug": prepared["slug"], "values": prepared["values"]}


def sleepy(prepared: dict[str, Any]) -> dict[str, Any]:
    time.sleep(60)
    return {}


def raises(prepared: dict[str, Any]) -> dict[str, Any]:
    raise ValueError("first line of the message\nsecond line")


def exits(prepared: dict[str, Any]) -> dict[str, Any]:
    raise SystemExit(3)


def dies(prepared: dict[str, Any]) -> dict[str, Any]:
    os._exit(7)


def counts_calls(prepared: dict[str, Any]) -> dict[str, Any]:
    """Leaves one file per call next to the prepared protocol, so a test can count the runs."""
    folder = os.path.dirname(prepared["path"])
    open(os.path.join(folder, f"ran-{time.monotonic_ns()}"), "w").close()
    return {}
