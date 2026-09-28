"""The day's spend on live model calls, in one JSON file on the volume.

    {"2026-09-23": 0.41, ...}   USD per UTC day, from the API's usage fields at list prices

The cap (`PROVETTE_DAILY_CAP_USD`) turns the live flow off for the day with a sentence, rather
than letting a loop run up a bill. An episode costs a few cents; the cap is against loops.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path

log = logging.getLogger(__name__)


def today() -> str:
    return time.strftime("%Y-%m-%d", time.gmtime())


class Ledger:
    def __init__(self, path: Path, cap_usd: float) -> None:
        self.path = path
        self.cap_usd = cap_usd
        self._lock = threading.Lock()

    def _read(self) -> dict[str, float]:
        if not self.path.is_file():
            return {}
        try:
            row = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            # An unreadable ledger counts as nothing spent today; the log says the cap is blind.
            log.warning(
                "the spend ledger %s could not be read (%s); today counts from 0", self.path, error
            )
            return {}
        return {k: float(v) for k, v in row.items()}

    def spent_today(self) -> float:
        with self._lock:
            return round(self._read().get(today(), 0.0), 4)

    def remaining(self) -> float:
        return round(max(self.cap_usd - self.spent_today(), 0.0), 4)

    def add(self, usd: float) -> float:
        """Record a spend; returns the day's total."""
        with self._lock:
            rows = self._read()
            rows[today()] = round(rows.get(today(), 0.0) + max(usd, 0.0), 6)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(rows, indent=1), encoding="utf-8")
            tmp.replace(self.path)
            return rows[today()]

    def allows(self, estimate_usd: float) -> bool:
        return self.spent_today() + estimate_usd <= self.cap_usd
