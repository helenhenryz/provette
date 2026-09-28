"""The second source: Opentrons' own protocol analysis, reduced to its liquid operations.

`opentrons.cli analyze --json-output` is what the Opentrons App runs before it lets you start
a protocol. It knows nothing of Provette's broker tap, so where the two agree we have read the
simulator correctly. It gives no source lines, which is why it is the check and not the trace.
"""

from __future__ import annotations

import json
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from provette.trace._run import TraceError, run_python

LiquidOpName = Literal["pick_up_tip", "drop_tip", "aspirate", "dispense", "blow_out"]


@dataclass(frozen=True)
class LiquidOp:
    """One liquid or tip step of the analysis.

    `labware_load_name` is the labware's load name, or the name of the deck area ("fixedTrash")
    for a step done over the trash. `slot` is where that labware was FIRST loaded, to match
    `WellKey.labware_id`; it is None over the trash. `well` is None over the trash.
    """

    op: LiquidOpName
    labware_load_name: str | None
    slot: str | None
    well: str | None
    volume_ul: float | None


# commandType -> (op, whether the command names its own labware and well)
COMMANDS: dict[str, tuple[LiquidOpName, bool]] = {
    "pickUpTip": ("pick_up_tip", True),
    "dropTip": ("drop_tip", True),
    "dropTipInPlace": ("drop_tip", False),
    "aspirate": ("aspirate", True),
    "aspirateInPlace": ("aspirate", False),
    "airGapInPlace": ("aspirate", False),
    "dispense": ("dispense", True),
    "dispenseInPlace": ("dispense", False),
    "blowout": ("blow_out", True),
    "blowOutInPlace": ("blow_out", False),
}


def analyze_protocol(
    path: Path, *, labware_dirs: Sequence[Path] = (), timeout_s: float = 120
) -> list[LiquidOp]:
    """Analyse `path` with `opentrons.cli analyze` and return its liquid operations in order."""
    path = path.resolve()
    labware_files = sorted(str(f.resolve()) for d in labware_dirs for f in d.glob("*.json"))
    with tempfile.TemporaryDirectory(prefix="provette-analyze-") as tmp:
        workdir = Path(tmp)
        out = workdir / "analysis.json"
        arguments = ["-m", "opentrons.cli", "analyze", "--json-output", str(out)]
        done = run_python(
            [*arguments, str(path), *labware_files], workdir=workdir, timeout_s=timeout_s
        )
        if done.returncode != 0 or not out.is_file():
            raise TraceError("opentrons.cli analyze failed:\n" + done.stderr[-2000:])
        analysis = json.loads(out.read_text(encoding="utf-8"))
    if analysis.get("result") != "ok":
        details = "; ".join(str(e.get("detail")) for e in analysis.get("errors", []))
        raise TraceError(f"opentrons.cli analyze: {details or analysis.get('result')}")
    return reduce_analysis(analysis)


def reduce_analysis(analysis: dict[str, Any]) -> list[LiquidOp]:
    """The analysis command list as `LiquidOp`s.

    An "in place" command names no labware: it acts wherever the pipette already is. We follow
    each pipette through every command that does name a place (including plain moves), so an in
    place command gets the place of the command before it.
    """
    module_slot: dict[str, str] = {}
    labware: dict[str, tuple[str, str | None]] = {}  # labwareId -> (load name, first slot)
    place: dict[str, tuple[str | None, str | None, str | None]] = {}  # pipetteId -> where
    ops: list[LiquidOp] = []
    for item in analysis.get("labware", []):
        # Below API 2.14 the fixed trash is a labware that no command loads. It never moves.
        if item["id"] == "fixedTrash":
            labware[item["id"]] = (item["loadName"], _slot(item["location"], {}, {}))
    for command in analysis["commands"]:
        kind, params = command["commandType"], command.get("params", {})
        result = command.get("result") or {}
        if kind == "loadModule":
            module_slot[result["moduleId"]] = params["location"]["slotName"]
        elif kind == "loadLabware":
            slot = _slot(params["location"], module_slot, labware)
            labware[result["labwareId"]] = (params["loadName"], slot)

        pipette = params.get("pipetteId")
        if pipette is None:
            continue
        if "labwareId" in params and "wellName" in params:
            load_name, slot = labware[params["labwareId"]]
            place[pipette] = (load_name, slot, params["wellName"])
        elif "addressableAreaName" in params:
            place[pipette] = (params["addressableAreaName"], None, None)
        if kind in COMMANDS:
            op, _ = COMMANDS[kind]
            where = place.get(pipette, (None, None, None))
            ops.append(LiquidOp(op, *where, volume_ul=params.get("volume")))
    return ops


def _slot(
    location: Any, module_slot: dict[str, str], labware: dict[str, tuple[str, str | None]]
) -> str | None:
    if isinstance(location, dict):
        if "slotName" in location:
            return str(location["slotName"])
        if "moduleId" in location:
            return module_slot.get(location["moduleId"])
        if "labwareId" in location:  # on an adapter
            return labware[location["labwareId"]][1]
    return None  # "offDeck"
