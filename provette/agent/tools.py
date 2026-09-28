"""The seven tools the model has, as OpenAI function schemas plus their Python implementations.

The model sees the schemas in `SCHEMAS`; the loop calls `Toolbox.call(name, arguments)`, which
returns a JSON-serialisable dict for every call, including a wrong tool name and bad arguments
(an `error` key, never an exception). One `Toolbox` is one episode: it holds the plate map,
the runner the checks run on, the current draft and the result of the last `run_checks`, and it
writes every draft and every check result under `out_dir` as `NN-draft.py` and `NN-checks.json`.

The tool descriptions are written for a small model: when to call the tool, what it returns.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from opentrons_shared_data import labware as shared_labware

from provette.agent.prelint import prelint
from provette.agent.runner import Runner
from provette.calc import dilution_series, master_mix, normalise
from provette.intent.labware import need_of

REPORT_CHARS = 6000  # each text report the model reads is cut here, and says so

# The load names the reference sheet (eval/requests/reference.md) offers, by kind. The numbers
# come from the installed Opentrons definitions at call time, never from here.
LABWARE_FAMILIES: dict[str, tuple[str, ...]] = {
    "plate": (
        "nest_96_wellplate_100ul_pcr_full_skirt",
        "biorad_96_wellplate_200ul_pcr",
        "nest_96_wellplate_200ul_flat",
        "corning_96_wellplate_360ul_flat",
        "nest_96_wellplate_2ml_deep",
        "usascientific_96_wellplate_2.4ml_deep",
        "corning_384_wellplate_112ul_flat",
    ),
    "tubes": (
        "opentrons_24_tuberack_nest_1.5ml_snapcap",
        "opentrons_24_tuberack_nest_2ml_snapcap",
        "opentrons_15_tuberack_falcon_15ml_conical",
        "opentrons_6_tuberack_falcon_50ml_conical",
        "opentrons_10_tuberack_falcon_4x50ml_6x15ml_conical",
    ),
    "tips": (
        "opentrons_96_tiprack_20ul",
        "opentrons_96_tiprack_300ul",
        "opentrons_96_tiprack_1000ul",
        "opentrons_96_filtertiprack_20ul",
        "opentrons_96_filtertiprack_200ul",
        "opentrons_96_filtertiprack_1000ul",
    ),
    "reservoir": ("nest_12_reservoir_15ml", "nest_1_reservoir_195ml"),
    "module_block": (
        "opentrons_24_aluminumblock_nest_1.5ml_snapcap",
        "opentrons_96_aluminumblock_generic_pcr_strip_200ul",
        "opentrons_96_aluminumblock_nest_wellplate_100ul",
    ),
}
MODULES = (
    "temperature module gen2",
    "magnetic module gen2",
    "thermocyclerModuleV2",
    "heaterShakerModuleV1",
)

SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "platemap",
            "description": (
                "Call this first, before writing anything. It returns the plate map: the exact "
                "liquid names the protocol must use in define_liquid, the destination labware, "
                "and what every well (or every group of wells) must hold at the end, in "
                "microlitres of each starting liquid. The checks compare the finished plate "
                "against this, so the protocol must deliver exactly these amounts."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "labware",
            "description": (
                "Call this to get the real load names for one kind of labware, with how many "
                "wells each has and the most one well can hold in microlitres (for tip racks, "
                "the tip size). Use only names it returns: an invented name makes the simulator "
                "reject the protocol. kind is one of plate, tubes, tips, reservoir, module_block."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "kind": {
                        "type": "string",
                        "enum": ["plate", "tubes", "tips", "reservoir", "module_block"],
                        "description": "plate: 96- and 384-well plates. tubes: tube racks. "
                        "tips: tip racks. reservoir: troughs. module_block: aluminium "
                        "blocks that sit on a temperature module, and the module names.",
                    }
                },
                "required": ["kind"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "dilution_series",
            "description": (
                "Call this for any serial dilution (1:2, 1:10, a standard curve) instead of "
                "working out the volumes yourself. It returns, for each well in order: how much "
                "diluent to add, how much to transfer in (from the stock for well 1, from the "
                "previous well after that), how much to remove from the last well, and what "
                "each well then holds. Write the protocol to do exactly those transfers, in "
                "that order, mixing after each transfer."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "stock_concentration": {
                        "type": "number",
                        "description": "The stock's concentration in any unit (use 1 if "
                        "unknown; the answer is then relative).",
                    },
                    "points": {"type": "integer", "description": "How many wells (points)."},
                    "factor": {
                        "type": "number",
                        "description": "2 for a 1:2 series, 10 for a 1:10 series.",
                    },
                    "final_volume_ul": {
                        "type": "number",
                        "description": "What every well must hold at the end, in ul.",
                    },
                    "first_point_is_stock": {
                        "type": "boolean",
                        "description": "true if the first well is undiluted stock (a curve "
                        "'from 2 mg/ml down'); false if the first well is already 1:factor.",
                    },
                    "remove_excess": {
                        "type": "boolean",
                        "description": "true (default) to take the extra carry out of the "
                        "last well so it holds the final volume like the others.",
                    },
                },
                "required": [
                    "stock_concentration",
                    "points",
                    "factor",
                    "final_volume_ul",
                    "first_point_is_stock",
                ],  # fmt: skip
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "normalise",
            "description": (
                "Call this when samples of different concentrations must be brought to one "
                "target concentration in one final volume. Give the concentrations in the order "
                "of the request; it returns, for each sample, how many ul of sample and how "
                "many of diluent to put in its well, and a warning where the volume is below "
                "what the pipette can move or the sample is too dilute to reach the target."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "concentrations": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "One concentration per sample, in the request's order.",
                    },
                    "target": {"type": "number", "description": "The target concentration."},
                    "final_volume_ul": {"type": "number", "description": "Final volume per well."},
                    "min_pipette_ul": {
                        "type": "number",
                        "description": "The smallest volume the pipette can move (1 for a p20).",
                    },
                },
                "required": ["concentrations", "target", "final_volume_ul"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "master_mix",
            "description": (
                "Call this when several reagents go into every reaction and you will pool them "
                "first. Give the ul of each component per reaction and the number of reactions; "
                "it returns how much of each to pool (with overage), the total, and the volume "
                "to dispense per reaction."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "components": {
                        "type": "object",
                        "additionalProperties": {"type": "number"},
                        "description": "Component name -> ul per reaction.",
                    },
                    "reactions": {"type": "integer", "description": "How many reactions."},
                    "overage_fraction": {
                        "type": "number",
                        "description": "Extra to make, as a fraction: 0.1 is 10% (the default).",
                    },
                },
                "required": ["components", "reactions"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_protocol",
            "description": (
                "Call this to hand in the protocol: the WHOLE Python file as one string, every "
                "time (not a diff, not a fragment). It stores the draft and returns the line "
                "count, and the checks (simulator, plate map, biology) of that draft, the "
                "same as run_checks returns."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "The complete Python file."}
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "submit",
            "description": (
                "Call this to finish, only when the last checks said ready_to_submit is "
                "true (simulator passed, verify_exit 0, check_exit 0). If after several "
                "attempts the draft still fails, call it anyway with your best draft: the "
                "record shows how it stood."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

TOOL_NAMES = tuple(schema["function"]["name"] for schema in SCHEMAS)
# run_checks is no longer offered to the model (write_protocol checks every draft) but a model
# that calls it anyway, or a test, still gets the checks.
CALLABLE = (*TOOL_NAMES, "run_checks")


def liquid_names(platemap: Mapping[str, Any]) -> list[str]:
    """The names the writer must give its liquids, so that the plate map can find them.

    The same rule as eval/baseline/run.py: an indexed liquid `sample_{i}` becomes "sample 1",
    "sample 2", ...; a named liquid `master_mix` becomes "master mix". By-well liquids get no name
    here: the protocol declares whatever is in each source well.
    """
    names: list[str] = []
    for liquid in platemap["liquids"]:
        if liquid["bind"] == "indexed":
            stem = liquid["name"].split("_")[0]
            word = next(
                (w for w in (stem, "sample") if re.search(liquid["pattern"], f"{w} 1")), None
            )
            if word is None:
                raise ValueError(f"{platemap['id']}: no name fits {liquid['pattern']}")
            names += [f"{word} {i}" for i in range(1, liquid["count"] + 1)]
        elif liquid["bind"] == "name":
            name = liquid["name"].replace("_", " ")
            if not re.search(liquid["pattern"], name):
                raise ValueError(f"{platemap['id']}: {name!r} does not match {liquid['pattern']}")
            names.append(name)
    return names


class Toolbox:
    """One episode's tools and state. `call` never raises for what the model sends."""

    def __init__(
        self, platemap: Mapping[str, Any], runner: Runner, out_dir: Path, min_drafts: int = 0
    ) -> None:
        self.platemap = dict(platemap)
        # A submit while the checks still report problems is refused until this many drafts were
        # written (0: every submit is taken, as the evaluation ran). The product's live flow sets
        # 3: a model that submits its first failing draft is sent back to repair it (D-32).
        self.min_drafts = min_drafts
        self.runner = runner
        self.out_dir = out_dir
        self.draft: str | None = None
        self.draft_number = -1  # the NN of the current draft
        self.last_checks: dict[str, Any] | None = None  # the runner's dict, untruncated
        self.checks_of_draft = -1  # which draft `last_checks` is about
        self.check_results: list[dict[str, Any]] = []  # every run_checks, in order
        self.submitted = False

    # -- dispatch ------------------------------------------------------------------------------

    def call(self, name: str, arguments: Mapping[str, Any] | str | None) -> dict[str, Any]:
        """Run one tool. A bad name, bad JSON, wrong arguments: an `error` key, never a raise."""
        if name not in CALLABLE:
            return {
                "error": f"there is no tool named {name!r}. The tools are: {', '.join(TOOL_NAMES)}."
            }
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments) if arguments.strip() else {}
            except json.JSONDecodeError as error:
                return {
                    "error": f"the arguments were not valid JSON ({error}). Send a JSON object."
                }
        if arguments is None:
            arguments = {}
        if not isinstance(arguments, Mapping):
            return {"error": "the arguments must be a JSON object with the named parameters."}
        try:
            result: dict[str, Any] = getattr(self, f"tool_{name}")(**arguments)
            return result
        except TypeError as error:
            return {"error": f"wrong arguments for {name}: {error}. Check the parameter names."}
        except (ValueError, KeyError) as error:
            return {"error": f"{name}: {error}"}

    # -- the plate map -------------------------------------------------------------------------

    def tool_platemap(self) -> dict[str, Any]:
        pm = self.platemap
        variants = pm["variants"]
        shown = variants[0]
        out: dict[str, Any] = {
            "id": pm["id"],
            **({"technique": _technique_line(pm["technique"])} if pm.get("technique") else {}),
            "liquid_names": liquid_names(pm),
            "liquid_names_rule": (
                "Use these exact strings as the name in define_liquid, one liquid each. "
                "Other liquids (a waste, an extra buffer) may have any name."
            ),
            "destination": _destination(pm),
        }
        if len(variants) > 1:
            out["readings"] = (
                f"The request can be read in {len(variants)} ways and any one is accepted. "
                f"Shown below is one of them: '{shown['name']}'. The notes say what else is "
                "accepted."
            )
        if any(liquid["bind"] == "well" for liquid in pm["liquids"]):
            out["source_wells_rule"] = (
                "Some liquids are 'whatever is in well X of the source plate': declare a liquid "
                "in every source well the protocol draws from (any name, one per well, e.g. "
                "'source B3'); the check follows what was in that well."
            )
        if shown["pinned"]:
            out["wells"] = _describe_pinned(pm, shown["pinned"])
        if shown["groups"]:
            out["groups"] = [_describe_group(pm, g) for g in shown["groups"]]
        if pm.get("notes"):
            out["notes"] = list(pm["notes"])
        if pm.get("discard_intended"):
            out["may_be_thrown_away"] = [_declared_name(pm, x) for x in pm["discard_intended"]]
        out["amounts_rule"] = (
            "Amounts are microlitres of each STARTING liquid in the well after ideal mixing. A "
            "well of a dilution that holds 50 ul drug + 50 ul pbs got there by transfers; write "
            "the transfers, and declare the drug and the pbs in their source wells."
        )
        return out

    # -- labware -------------------------------------------------------------------------------

    def tool_labware(self, kind: str) -> dict[str, Any]:
        if kind not in LABWARE_FAMILIES:
            raise ValueError(f"kind must be one of {', '.join(LABWARE_FAMILIES)}, not {kind!r}")
        rows = [labware_row(name, kind) for name in LABWARE_FAMILIES[kind]]
        out: dict[str, Any] = {"kind": kind, "labware": rows}
        if kind == "module_block":
            out["modules"] = list(MODULES)
            out["modules_rule"] = (
                'module = protocol.load_module("temperature module gen2", slot); '
                "block = module.load_labware(load_name). A block on a module takes the module's "
                "slot, not one of its own."
            )
        out["rule"] = "Use these load names exactly as written."
        return out

    # -- arithmetic ----------------------------------------------------------------------------

    def tool_dilution_series(
        self,
        stock_concentration: float,
        points: int,
        factor: float,
        final_volume_ul: float,
        first_point_is_stock: bool,
        remove_excess: bool = True,
    ) -> dict[str, Any]:
        series = dilution_series(
            float(stock_concentration),
            int(points),
            float(factor),
            float(final_volume_ul),
            bool(first_point_is_stock),
            bool(remove_excess),
        )
        # One move per well: what comes IN. The move out of well i is the move into well i+1,
        # so it is not listed twice (a draft that did both emptied the first well).
        wells = [
            {
                "well": p["well_index"],
                "step_1_add_diluent_ul": _r(p["diluent_ul"]),
                "step_2_transfer_in_ul": _r(p["transfer_in_ul"]),
                "from": p["transfer_from"],
                "step_3": "mix",
                "then_holds_ul": _r(p["holds_ul"] + p["transfer_out_ul"]),
                "ends_holding_ul": _r(p["holds_ul"]),
                "of_which_stock_ul": _r(p["stock_ul"]),
                "concentration": _r(p["concentration"]),
                "dilution": p["dilution"],
            }
            for p in series
        ]
        last = series[-1]
        return {
            "wells": wells,
            "last_well_remove_to_waste_ul": _r(last["transfer_out_ul"]),
            "stock_needed_ul": _r(series[0]["transfer_in_ul"]),
            "diluent_needed_ul": _r(sum(p["diluent_ul"] for p in series)),
            "how": (
                "Pick up a tip. For each well in order: add the diluent, then transfer in "
                "from the source named (the stock for well 1, the previous well after that), "
                "then mix. That transfer is the only move between wells: never also move "
                "liquid on out of a well, because the next well's transfer_in already takes it. "
                f"At the end remove {_r(last['transfer_out_ul'])} ul from the last well to a "
                "waste well or the trash. The plate map's amounts per well (so much stock, so "
                "much diluent) are what each well ends holding after these transfers "
                "(ends_holding_ul, of_which_stock_ul); do not pipette those amounts directly. "
                "Declare more stock and diluent than is needed: a tube cannot be emptied to "
                "the last drop."
            ),
        }

    def tool_normalise(
        self,
        concentrations: Sequence[float],
        target: float,
        final_volume_ul: float,
        min_pipette_ul: float = 1.0,
    ) -> dict[str, Any]:
        rows = normalise(
            [float(c) for c in concentrations],
            float(target),
            float(final_volume_ul),
            float(min_pipette_ul),
        )
        return {
            "samples": [
                {
                    "sample": row["index"],
                    "concentration": row["concentration"],
                    "sample_ul": _r(row["sample_ul"]),
                    "diluent_ul": _r(row["diluent_ul"]),
                    "warning": row["warning"],
                }
                for row in rows
            ],
            "diluent_needed_ul": _r(sum(row["diluent_ul"] for row in rows)),
            "how": (
                "Put the diluent into every destination well first (one tip is fine for a "
                "diluent going into empty wells), then each sample with a fresh tip. Use the "
                "volumes as given, to two decimals; do not round them up to a pipette minimum."
            ),
        }

    def tool_master_mix(
        self, components: Mapping[str, float], reactions: int, overage_fraction: float = 0.1
    ) -> dict[str, Any]:
        mix = master_mix(
            {str(k): float(v) for k, v in components.items()},
            int(reactions),
            float(overage_fraction),
        )
        return {
            "reactions": mix["reactions"],
            "overage_fraction": mix["overage_fraction"],
            "components": [
                {
                    "name": c["name"],
                    "ul_per_reaction": c["ul_per_reaction"],
                    "ul_to_pool": _r(c["ul_to_pool"]),
                }
                for c in mix["components"]
            ],  # fmt: skip
            "total_pooled_ul": _r(mix["total_ul"]),
            "dispense_per_reaction_ul": _r(mix["per_reaction_ul"]),
            "how": (
                "Pool the components into one tube, mix, then dispense "
                f"{_r(mix['per_reaction_ul'])} ul into each reaction. Declare each component "
                "with more than ul_to_pool in its tube."
            ),
        }

    # -- the draft and the checks --------------------------------------------------------------

    def tool_write_protocol(self, text: str) -> dict[str, Any]:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("text must be the whole Python file, and it was empty")
        raw = text if text.endswith("\n") else text + "\n"
        lint = prelint(raw)  # the slips a model repeats, repaired and reported (prelint.py)
        # the same file again after the checks timed out is what the model was asked to do
        timed_out = (self.last_checks or {}).get("simulator") == "timeout"
        same_as_before = self.draft is not None and lint.text == self.draft and not timed_out
        self.draft = lint.text
        self.draft_number += 1
        self.out_dir.mkdir(parents=True, exist_ok=True)
        (self.out_dir / f"{self.draft_number:02d}-draft.py").write_text(
            self.draft, encoding="utf-8"
        )
        if lint.fixes:
            (self.out_dir / f"{self.draft_number:02d}-draft.as-written.py").write_text(
                raw, encoding="utf-8"
            )
        out: dict[str, Any] = {
            "stored": True,
            "draft": self.draft_number,
            "lines": self.draft.count("\n"),
        }
        if lint.fixes:
            out["repaired_before_checking"] = list(lint.fixes)
        if same_as_before:
            # OpenHands' stuck detector counts the same action repeated; ours says so at once.
            out["same_as_previous_draft"] = (
                "This file is identical to the previous draft, so the checks will say the same. "
                "Change something before handing it in again."
            )
        try:
            compile(self.draft, "protocol.py", "exec")
        except SyntaxError as error:
            out["syntax_error"] = f"line {error.lineno}: {error.msg}"
            out["next"] = "The file does not parse. Fix the syntax and call write_protocol again."
            return out
        # The checks run here, on every draft: a model that writes draft after draft without
        # checking (seen in five of six Super failures, eval/agent) now cannot, and a round trip
        # is saved on every draft.
        out["checks"] = self.tool_run_checks()
        out["next"] = (
            "Read `checks`. If ready_to_submit is true, call submit; otherwise fix what it "
            "names and call write_protocol again with the whole file."
        )
        return out

    def tool_run_checks(self) -> dict[str, Any]:
        if self.draft is None:
            return {
                "error": "there is no draft yet: call write_protocol with the whole file first.",
                "ready_to_submit": False,
            }
        result = dict(self.runner.run_checks(self.draft, self.platemap))
        if result.get("simulator") == "timeout":
            # a slow or busy machine, not the draft: try once more before saying anything
            result = dict(self.runner.run_checks(self.draft, self.platemap))
        result["draft"] = self.draft_number
        self.last_checks = result
        self.checks_of_draft = self.draft_number
        self.check_results.append(result)
        (self.out_dir / f"{self.draft_number:02d}-checks.json").write_text(
            json.dumps(result, indent=1), encoding="utf-8"
        )
        shown = checks_for_model(result)
        line = _line_of(result.get("simulator_error", ""))
        if line and self.draft is not None:
            lines = self.draft.splitlines()
            if 0 < line <= len(lines):
                shown["offending_line"] = f"{line}: {lines[line - 1].strip()}"
        repeats = self._same_error_streak()
        if repeats >= 3:
            # Five of Super's six failures hit one simulator error five or six times in a row,
            # rewriting the same line each time. Say so, and ask for a different approach.
            shown["stuck"] = (
                f"This is the same simulator error {repeats} times in a row. Rewriting the same "
                "line is not working: change the approach. Read the hint again, call labware "
                "for the labware at that line, and use the simplest API call that does the job "
                "(a transfer() with new_tip='always' instead of hand-written pick_up_tip, "
                "aspirate, dispense, drop_tip)."
            )
        return shown

    def _same_error_streak(self) -> int:
        """How many of the latest checks in a row were the same simulator error."""
        streak = 0
        last: str | None = None
        for result in reversed(self.check_results):
            if result.get("simulator") == "timeout":
                break  # a slow machine is not an error the model keeps making
            error = _error_kind(result.get("simulator_error", ""))
            if not error or (last is not None and error != last):
                break
            last = error
            streak += 1
        return streak

    def tool_submit(self) -> dict[str, Any]:
        ready = self.last_checks is not None and is_clean(self.last_checks)
        stale = self.draft is not None and self.checks_of_draft != self.draft_number
        drafts = self.draft_number + 1
        if self.draft is not None and not ready and not stale and drafts < self.min_drafts:
            # not taken: the checks still report problems and the model has tries left
            return {
                "submitted": False,
                "refused": (
                    f"Not submitted: the checks of draft {self.draft_number} still report problems "
                    "(ready_to_submit is false). Read verify_report and the findings of the last "
                    "write_protocol result, fix the file, and call write_protocol with the whole "
                    "file again. Submit is taken when ready_to_submit is true, or after "
                    f"{self.min_drafts} drafts."
                ),
            }
        self.submitted = True
        return {
            "submitted": True,
            "draft": self.draft_number if self.draft is not None else None,
            "verified_and_clean_at_last_check": ready and not stale,
            "note": (
                "no draft was ever written"
                if self.draft is None
                else "the current draft was never checked"
                if stale
                else "verified and clean"
                if ready
                else "submitted with problems still reported"
            ),
        }


# -------------------------------------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------------------------------------


def is_clean(checks: Mapping[str, Any]) -> bool:
    """The runner's verdict: simulator passed, every well verified, no error or warning."""
    return (
        checks.get("simulator") == "passed"
        and checks.get("verify_exit") == 0
        and checks.get("check_exit") == 0
    )


def checks_for_model(result: Mapping[str, Any]) -> dict[str, Any]:
    """The runner's dict as the model reads it: reports truncated, the JSON report left out."""
    out: dict[str, Any] = {"draft": result.get("draft"), "simulator": result["simulator"]}
    if result["simulator"] == "timeout":
        out["ready_to_submit"] = False
        out["verdict"] = (
            "The checks did not finish in time on this machine. That is a limit of the server, "
            "not a finding about your draft: nothing in it was judged. Call write_protocol again "
            "with the same whole file to check it again; do not change it for this."
        )
        return out
    if result["simulator"] != "passed":
        error = result.get("simulator_error", "")
        out["simulator_error"] = error
        out["verify_exit"] = 2
        out["ready_to_submit"] = False
        out["verdict"] = (
            "The simulator rejected the file, so nothing else was checked. Fix the error at the "
            "line named, then call write_protocol with the whole file: it checks the draft."
        )
        missing = re.search(r'Labware "([^"]+)" not found', error)
        no_well = re.search(r"KeyError.*?'([A-Z]\d{1,2})'", error)
        # The tracer wraps load_liquid, so the error names `_install.<locals>.load_liquid`;
        # the model must see the API's name, or it does not know which call is meant.
        unexpected = re.search(
            r"([\w.<>]+)\(\) got an unexpected keyword argument '([^']+)'", error
        )
        if missing:
            out["hint"] = (
                f"There is no labware called {missing.group(1)!r}. The real load names are: "
                + ", ".join(name for names in LABWARE_FAMILIES.values() for name in names)
                + "."
            )
        elif no_well:
            out["hint"] = (
                f"{no_well.group(1)!r} is not a well of the labware used at that line. "
                "The wells of each labware: " + well_ranges() + "."
            )
        elif "Arc out of bounds" in error:
            out["hint"] = (
                "The pipette cannot arc over something on the deck: labware on a module is "
                "too tall. On a temperature module load only the aluminium blocks "
                "(opentrons_24_aluminumblock_nest_1.5ml_snapcap, "
                "opentrons_96_aluminumblock_generic_pcr_strip_200ul, "
                "opentrons_96_aluminumblock_nest_wellplate_100ul), never a tube rack; measured: "
                "a 24-tube rack on the module fails this way, the block does not."
            )
        elif "TipAttachedError" in error:
            out["hint"] = (
                "pick_up_tip was called while a tip was already on the pipette. Call drop_tip "
                "(or return_tip) before the next pick_up_tip, or use transfer(..., "
                "new_tip='always') and let it manage tips."
            )
        elif "InvalidAspirateVolumeError" in error or "only 0.0 is available in the tip" in error:
            out["hint"] = (
                "The volume does not fit the tip, or the tip is empty: a p20 tip holds 20 ul, a "
                "p300 tip 300 ul, a p1000 tip 1000 ul. Split a big transfer into repeats of at "
                "most the tip's volume (transfer() does this by itself), and never dispense more "
                "than was aspirated."
            )
        elif "Invalid source for multichannel" in error or "multichannel" in error.lower():
            out["hint"] = (
                "An 8-channel pipette can only work on a column of a 96-well plate (address it "
                "by its top well, e.g. plate['A1']), a 384-well plate, or a reservoir well. It "
                "cannot pick single tubes of a tube rack: use a single-channel pipette for those."
            )
        elif "has no attribute" in error and "protocol_api" in error:
            out["hint"] = (
                "That name does not exist in the Opentrons API. Use only what the reference "
                "sheet shows: load_labware, load_module, load_instrument, define_liquid, "
                "load_liquid, pick_up_tip, aspirate, dispense, mix, blow_out, drop_tip, "
                "return_tip, transfer, distribute, consolidate, delay, comment."
            )
        elif "'str' object has no attribute '_id'" in error:
            out["hint"] = (
                "load_liquid was given a name string. Pass the object that define_liquid "
                "returned: mm = protocol.define_liquid(name=...); well.load_liquid(liquid=mm, "
                "volume=...)."
            )
        elif unexpected:
            function = unexpected.group(1).rsplit(".", 1)[-1]
            keyword = unexpected.group(2)
            signature = " load_liquid takes (liquid, volume)." if function == "load_liquid" else ""
            out["hint"] = (
                f"{function}() takes only the arguments the Opentrons API documents, and "
                f"{keyword!r} is not one of them.{signature} Drop the {keyword}=... argument "
                "from that call."
            )
        return out
    out["verify_exit"] = result["verify_exit"]
    out["check_exit"] = result["check_exit"]
    out["verify_report"], cut_v = _truncate(result.get("verify_text", ""))
    out["check_report"], cut_c = _truncate(result.get("check_text", ""))
    if cut_v or cut_c:
        out["truncated"] = "a report was cut at about 6,000 characters; the start is what matters"
    out["findings"] = [
        {k: f.get(k) for k in ("rule_id", "severity", "line", "title", "fix")}
        for f in result.get("findings", [])
    ]
    # Declared liquids no word list knows (`provette verify --json`, "unplaced_liquids"): one
    # sentence each, so the model sees what the checks could not grade. Not a failure.
    unplaced = (result.get("verify") or {}).get("unplaced_liquids") or []
    if unplaced:
        out["unplaced_liquids"] = [u.get("sentence") or u.get("name") for u in unplaced]
    ready = is_clean(result)
    out["ready_to_submit"] = ready
    if ready:
        out["verdict"] = "Simulator passed, every well verified, no biology problem. Call submit."
    else:
        problems = []
        if result["verify_exit"] == 1:
            problems.append(
                "verify_exit 1: a well does not hold what the plate map says, or a FLAG"
            )
        elif result["verify_exit"] == 3:
            problems.append("verify_exit 3: the plate map could not be checked (read the report)")
        if result["check_exit"] != 0:
            problems.append("check_exit 1: a biology problem (see findings and check_report)")
        out["verdict"] = (
            "Not ready: " + "; ".join(problems) + ". Read the reports, fix the file, call "
            "write_protocol with the whole file: it checks the draft again."
        )
    return out


def well_ranges() -> str:
    """'A1..D6 (4 rows x 6 columns): opentrons_24_tuberack_...; A1..H12 (...): ...' from the
    installed definitions, one entry per distinct well layout."""
    by_layout: dict[str, list[str]] = {}
    for kind, names in LABWARE_FAMILIES.items():
        for name in names:
            by_layout.setdefault(labware_row(name, kind)["well_names"], []).append(name)
    return "; ".join(f"{layout}: {', '.join(names)}" for layout, names in by_layout.items())


def _truncate(text: str) -> tuple[str, bool]:
    if len(text) <= REPORT_CHARS:
        return text, False
    return text[:REPORT_CHARS] + "\n[... cut here ...]", True


def _r(value: float) -> float:
    return round(value, 2)


def labware_row(load_name: str, kind: str) -> dict[str, Any]:
    # Version 1 exists for every load name here; wells and volumes are the same in every
    # installed version of these 23 definitions (checked on opentrons 8.8.2).
    definition = shared_labware.load_definition(load_name, 1)
    wells = definition["wells"]
    ordering = definition["ordering"]
    rows, columns = len(ordering[0]), len(ordering)
    volumes: dict[float, list[str]] = {}
    for column in ordering:
        for well in column:
            volumes.setdefault(wells[well]["totalLiquidVolume"], []).append(well)
    max_ul: Any
    if len(volumes) == 1:
        max_ul = next(iter(volumes))
    else:
        max_ul = {f"{v:g} ul": ", ".join(names) for v, names in volumes.items()}
    row: dict[str, Any] = {
        "load_name": load_name,
        "display_name": definition["metadata"]["displayName"],
        "wells": len(wells),
        "well_names": f"{ordering[0][0]}..{ordering[-1][-1]} ({rows} rows x {columns} columns)",
    }
    if kind == "tips":
        row["tip_ul"] = max_ul
        row["fits"] = {
            20: "p20_single_gen2, p20_multi_gen2",
            200: "p300_single_gen2, p300_multi_gen2",
            300: "p300_single_gen2, p300_multi_gen2",
            1000: "p1000_single_gen2",
        }.get(int(max_ul), "")
    else:
        row["max_ul_per_well"] = max_ul
    return row


def _technique_line(technique: str) -> str:
    """The technique word of the request, and the kind of plate it needs when the table says."""
    need = need_of(technique)
    if need is None or need.destination is None:
        return technique
    kinds = {
        "pcr": "a PCR plate or PCR strips",
        "flat": "a flat plate",
        "deep": "a deep-well plate",
    }
    wanted = " or ".join(kinds.get(kind, kind) for kind in need.destination)
    return f"{technique}: the destination must be {wanted} (the checks flag any other kind)"


def _destination(pm: Mapping[str, Any]) -> str:
    dest = pm.get("destination", {"select": "auto"})
    if dest.get("select") == "regex":
        return (
            f"the labware whose name or label matches /{dest['pattern']}/ (give it a label "
            "that does, in load_labware(..., label=...))"
        )
    return "the labware the transfers end in (the plate or tube the request names)"


def _declared_name(pm: Mapping[str, Any], logical: str) -> str:
    """The logical name as the protocol will write it: 'sample_3' -> 'sample 3'."""
    for liquid in pm["liquids"]:
        stem = liquid["name"].replace("_{i}", "").replace("@{well}", "")
        if liquid["bind"] == "indexed" and re.fullmatch(re.escape(stem) + r"_\d+", logical):
            word = next(
                (
                    w
                    for w in (stem.split("_")[0], "sample")
                    if re.search(liquid["pattern"], f"{w} 1")
                ),
                stem,
            )
            return f"{word} {logical.rsplit('_', 1)[1]}"
        if liquid["bind"] == "well" and re.fullmatch(re.escape(stem) + r"@[A-Z]\d{1,2}", logical):
            return f"from well {logical.split('@')[1]} of the source plate"
        if liquid["bind"] == "name" and logical == liquid["name"]:
            return logical.replace("_", " ")
    return logical


def _amount(pm: Mapping[str, Any], logical: str, amount: Any) -> str:
    name = _declared_name(pm, logical)
    if amount == "declared":
        return f"all of the {name} already in the well (the volume it was declared with)"
    return f"{_ul(float(amount))} {name}"


def _ul(volume: float) -> str:
    return f"{volume:.2f}".rstrip("0").rstrip(".") + " ul"


def _contents(pm: Mapping[str, Any], contents: Mapping[str, Any]) -> str:
    """'20 ul master mix + 5 ul sample 3'; many indexed liquids at one volume are compressed."""
    runs: dict[tuple[str, Any], list[int]] = {}
    for logical, amount in contents.items():
        m = re.fullmatch(r"(.+)_(\d+)", logical)
        if m and pm_spec_indexed(pm, logical):
            runs.setdefault((m.group(1), amount), []).append(int(m.group(2)))
    parts: list[str] = []
    done: set[tuple[str, Any]] = set()
    for logical, amount in contents.items():
        m = re.fullmatch(r"(.+)_(\d+)", logical)
        key = (m.group(1), amount) if m else None
        if key is not None and key in runs and len(runs[key]) > 2:
            if key not in done:
                done.add(key)
                stem, indices = key[0], runs[key]
                first = _declared_name(pm, f"{stem}_{min(indices)}")
                last = _declared_name(pm, f"{stem}_{max(indices)}")
                parts.append(f"{_ul(float(amount))} each of {first} to {last} ({len(indices)})")
        else:
            parts.append(_amount(pm, logical, amount))
    return " + ".join(parts)


def pm_spec_indexed(pm: Mapping[str, Any], logical: str) -> bool:
    for liquid in pm["liquids"]:
        if liquid["bind"] == "indexed":
            stem = liquid["name"].replace("_{i}", "")
            if re.fullmatch(re.escape(stem) + r"_\d+", logical):
                return True
    return False


def _shape(pm: Mapping[str, Any], contents: Mapping[str, Any], well: str | None = None) -> str:
    """The contents with sample numbers and well names replaced, to find wells that look alike."""
    text = _contents(pm, contents)
    if well is not None:
        text = text.replace(
            f"from well {well} of the source plate", "from the same-named well of the source plate"
        )
    return re.sub(r"\b([a-z]+) \d+\b", r"\1", text)


def _describe_pinned(pm: Mapping[str, Any], pinned: Mapping[str, Mapping[str, Any]]) -> Any:
    shapes: dict[str, list[str]] = {}
    for well, contents in pinned.items():
        shapes.setdefault(_shape(pm, contents, well), []).append(well)
    if len(shapes) == 1 and len(pinned) > 3:
        shape, wells = next(iter(shapes.items()))
        return {
            "every_well": f"{wells[0]} to {wells[-1]} ({len(wells)} wells, positions fixed)",
            "each_holds": shape,
        }
    return {well: _contents(pm, contents) for well, contents in pinned.items()}


def _describe_group(pm: Mapping[str, Any], group: Mapping[str, Any]) -> dict[str, Any]:
    members = group["members"]
    out: dict[str, Any] = {"name": group["name"], "wells": len(members)}
    if group.get("position") == "same_as_source":
        out["where"] = "each in the well with the same name as the well its sample started in"
    elif group.get("within"):
        within = group["within"]
        out["where"] = f"any of {within[0]}..{within[-1]} ({len(within)} wells)"
    else:
        out["where"] = "any wells of the destination"
    if group.get("order_hint") == "index":
        out["order"] = "in number order (1, 2, 3, ...), reading down the columns or along the rows"
    shapes = {_shape(pm, m) for m in members}
    if len(shapes) == 1 and len(members) > 1:
        out["each_holds"] = next(iter(shapes))
        counts: dict[str, int] = {}
        for m in members:
            for logical in m:
                if pm_spec_indexed(pm, logical):
                    counts[_declared_name(pm, logical)] = (
                        counts.get(_declared_name(pm, logical), 0) + 1
                    )
        if counts:
            per = sorted(set(counts.values()))
            names = list(counts)
            out["samples"] = f"{names[0]} to {names[-1]}" + (
                f", each in {per[0]} wells" if per != [1] else ", one well each"
            )
    else:
        out["members"] = [_contents(pm, m) for m in members]
    return out


def _error_kind(error: str) -> str:
    """The simulator error with its line number removed, so 'the same error' can be counted."""
    return re.sub(r"line \d+", "line N", error).split("):")[-1].strip()[:120]


def _line_of(error: str) -> int | None:
    m = re.search(r"line (\d+)", error)
    return int(m.group(1)) if m else None
