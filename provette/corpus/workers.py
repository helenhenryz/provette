"""Workers for `run_corpus`. Each takes a `PreparedProtocol` as a dict and returns a payload.

A worker runs inside a process of its own (see `runner`), so it may patch what it likes.
"""

from __future__ import annotations

import io
import logging
import os
import tempfile
from collections.abc import Iterable
from pathlib import Path
from typing import Any


def simulate_worker(prepared: dict[str, Any]) -> dict[str, Any]:
    """Does the protocol pass the Opentrons simulator? Raises whatever the simulator raises."""
    with tempfile.TemporaryDirectory(prefix="provette-ot-config-") as config_dir:
        # Must be set before `opentrons` is imported: it reads and writes its config on import,
        # and twelve simulators sharing ~/.opentrons is not something we want to find out about.
        os.environ["OT_API_CONFIG_DIR"] = config_dir
        from opentrons import simulate

        logging.disable(logging.CRITICAL)
        path = Path(prepared["path"])
        labware_dir = prepared["labware_dir"]
        run_log, _bundle = simulate.simulate(
            io.StringIO(path.read_text(encoding="utf-8")),
            file_name=path.name,
            custom_labware_paths=[labware_dir] if labware_dir else [],
            propagate_logs=False,
        )
        return {"commands": len(run_log)}


def trace_worker(prepared: dict[str, Any]) -> dict[str, Any]:
    """Trace the protocol from both sources, replay it, and count what the state machine saw.

    This is the library's view of validation layer 2 (do the two sources agree?) and the raw
    material for the contact model's error budget (how often is a verdict `unknown`?).
    """
    from collections import Counter

    from provette.state import replay
    from provette.trace import TraceError, analyze_protocol, cross_check, trace_protocol

    path = Path(prepared["path"])
    labware_dirs = [Path(prepared["labware_dir"])] if prepared["labware_dir"] else []
    trace = trace_protocol(path, labware_dirs=labware_dirs)
    try:
        disagreements: list[str] | None = cross_check(
            trace, analyze_protocol(path, labware_dirs=labware_dirs)
        )
    except TraceError as error:
        disagreements = None
        analyze_error = str(error)[:300]
    else:
        analyze_error = ""
    run = replay(trace)
    stock_hits = {  # a well the protocol drew from, which received another origin's material
        (a.well, a.atom) for a in run.arrivals if a.well in run.origins and a.atom != a.well
    }
    return {
        "events": len(trace.events),
        "ops": dict(Counter(e.op for e in trace.events)),
        "declared_loads": len(trace.deck.liquid_loads),
        "origins": len(run.origins),
        "arrivals": len(run.arrivals),
        "carryover_certain": sum(a.mode == "carryover" and a.certain for a in run.arrivals),
        "carryover_uncertain": sum(a.mode == "carryover" and not a.certain for a in run.arrivals),
        "stocks_hit": len({well for well, _ in stock_hits}),
        "stocks_hit_certain": len(
            {a.well for a in run.arrivals if (a.well, a.atom) in stock_hits and a.certain}
        ),
        "contacts": dict(Counter(c.verdict for s in run.steps for c in s.contacts)),
        "contact_reasons": dict(Counter(c.reason for s in run.steps for c in s.contacts)),
        "anomalies": dict(Counter(x.kind for x in run.anomalies)),
        "cross_check": None if disagreements is None else len(disagreements),
        "cross_check_first": (disagreements or [""])[0][:300],
        "analyze_error": analyze_error,
    }


def check_worker(prepared: dict[str, Any]) -> dict[str, Any]:
    """Run `provette check` on the protocol: the findings as JSON, with counts by rule and severity.

    Lines are mapped back to the library's own file (the prepared copy has `get_values`
    prepended); a line inside that prepended header maps to None.
    """
    import re
    from collections import Counter

    from provette.check import check
    from provette.corpus.prepare import original_line
    from provette.report.json import counts

    labware_dirs = [Path(prepared["labware_dir"])] if prepared["labware_dir"] else []
    result = check(Path(prepared["path"]), labware_dirs=labware_dirs, timeout_s=600)
    offset = prepared["line_offset"]

    def mapped(line: int | None) -> int | None:
        return None if line is None else original_line(line, offset)

    def in_text(text: str) -> str:
        return re.sub(r"\bline (\d+)", lambda m: f"line {mapped(int(m.group(1)))}", text)

    def in_frame(frame: str) -> str:
        function, _, line = frame.rpartition(":")
        return f"{function}:{mapped(int(line))}" if line.isdigit() else frame

    findings = []
    for finding in result.findings:
        row = finding.to_json()
        row["line"] = mapped(finding.line)
        row["stack"] = [in_frame(frame) for frame in finding.stack]
        row["explanation"] = in_text(finding.explanation)
        row["fix"] = in_text(finding.fix)
        for occurrence in row["occurrences"]:
            occurrence["line"] = mapped(occurrence["line"])
        findings.append(row)
    return {
        "events": len(result.trace.events),
        "declared_loads": len(result.trace.deck.liquid_loads),
        **counts(result.findings),
        "by_rule_and_severity": dict(Counter(f"{f.rule_id}:{f.severity}" for f in result.findings)),
        "findings": findings,
    }


def export_worker(prepared: dict[str, Any]) -> dict[str, Any]:
    """Run the replay export (`provette view`'s JSON) on the protocol and measure what it holds:
    what the deck replay can draw of this protocol, and what it has to guess.

    The numbers behind docs/replay-support.md. Raises whatever the simulator or the export
    raises, so a protocol the export cannot handle is an error row with the exception's name.
    """
    import json

    from provette.check import check
    from provette.view.export import export

    labware_dirs = [Path(prepared["labware_dir"])] if prepared["labware_dir"] else []
    result = check(Path(prepared["path"]), labware_dirs=labware_dirs, timeout_s=600)
    data = export(result, labware_dirs=labware_dirs)
    payload = measure_export(data, (event.module for event in result.trace.events))
    payload["export_bytes"] = len(json.dumps(data, separators=(",", ":")))
    return payload


def measure_export(
    data: dict[str, Any], event_modules: Iterable[str | None] = ()
) -> dict[str, Any]:
    """What one export holds, as counts the sweep tabulates.

    `event_modules` is the `module` of every trace event: the export does not carry it, and it
    is the only place a module with nothing on it (a temperature module kept warm and never
    loaded) leaves a mark. The rest counts what the page has to draw without knowing: a
    labware whose well positions are on a grid because no definition matched (`unmatched`;
    the page says "well positions are a guess"), a well with no height table (drawn as a
    straight column), a labware in a place the deck does not name (`off_deck`, drawn at the
    origin), a well an event names that no labware row holds (`orphan_wells`), an event the
    tracer could only pass on (`passed_on`).
    """
    from collections import Counter

    from provette.view.export import replay_deltas

    slots = {slot["id"] for slot in data["deck"]["slots"]}
    labware = []
    unmatched: list[str] = []
    wells_without_shape = 0
    off_deck: list[str] = []
    for row in data["deck"]["labware"]:
        wells = row["wells"]
        no_shape = sum(1 for well in wells.values() if well["height_at_ul"] is None)
        wells_without_shape += no_shape
        first = next(iter(wells.values()), None)
        labware.append(
            {
                "id": row["id"],
                "slot": row["slot"],
                "load_name": row["load_name"],
                "module": row["module"],
                "is_tiprack": row["is_tiprack"],
                "is_trash": row["is_trash"],
                "kind": row["kind"],
                "measured": row["measured"],
                "wells": len(wells),
                "shape": None if first is None else first["shape"],
                "bottom": None if first is None else first["bottom"],
                "wells_without_shape": no_shape,
            }
        )
        if wells and not row["measured"]:
            unmatched.append(row["load_name"])
        if row["slot"] not in slots:
            off_deck.append(row["id"])
    ids = {row["id"] for row in data["deck"]["labware"]}
    orphan_wells = sum(1 for key in data["wells"] if key[: key.rindex("[")] not in ids)
    final = replay_deltas(data)["wells"]
    bands = [band for row in final.values() for band in row[2]]
    return {
        "events": len(data["events"]),
        "ops": dict(Counter(event["op"] for event in data["events"])),
        "passed_on": sum(
            event["text"] == "another action the simulator reported" for event in data["events"]
        ),
        "pipettes": data["pipettes"],
        "labware": labware,
        "modules": sorted({row["module"] for row in labware if row["module"]}),
        "event_modules": sorted({module for module in event_modules if module}),
        "trash": sorted({row["load_name"] for row in labware if row["is_trash"]}),
        "unmatched": sorted(set(unmatched)),
        "wells_without_shape": wells_without_shape,
        "off_deck": off_deck,
        "orphan_wells": orphan_wells,
        "origins": len(data["origins"]),
        "origins_declared": sum(1 for origin in data["origins"] if origin["declared"]),
        "bands": len(bands),
        "bands_unknown_volume": sum(1 for band in bands if band[1] is None),
        "bands_uncertain": sum(1 for band in bands if band[3] == 0),
        "wells_named": len(data["wells"]),
        "findings": len(data["findings"]),
    }
