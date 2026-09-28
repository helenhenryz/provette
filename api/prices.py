"""What an episode cost, from the token counts the API reported and `eval/prices.json`.

The prices are Token Factory's own, read from its `/v1/models` on the day in the file; nothing
here types a number. A model the file does not list costs `None`, and the page says so.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_LABEL = re.compile(
    r"nemotron[-_]?(3(?:[._]5)?)[-_]?(nano|super|ultra|lightning)[-_]?(\d+b)?", re.I
)


class Prices:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.read_on: str | None = None
        self.source: str | None = None
        self.models: dict[str, dict[str, Any]] = {}
        if path.is_file():
            row = json.loads(path.read_text(encoding="utf-8"))
            self.read_on = row.get("read_on")
            self.source = row.get("source")
            self.models = dict(row.get("models") or {})

    def cost_usd(self, model: str, tokens_in: int, tokens_out: int) -> float | None:
        price = self.models.get(model)
        if price is None:
            return None
        return round(
            tokens_in * float(price["input_per_million_usd"]) / 1e6
            + tokens_out * float(price["output_per_million_usd"]) / 1e6,
            4,
        )


def model_label(model: str) -> str:
    """'nvidia/nemotron-3-super-120b-a12b' -> 'Nemotron 3 Super 120B'; anything else as it is."""
    m = _LABEL.search(model)
    if not m:
        return model
    version = m.group(1).replace("_", ".")
    size = f" {m.group(3).upper()}" if m.group(3) else ""
    return f"Nemotron {version} {m.group(2).capitalize()}{size}"
