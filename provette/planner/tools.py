"""The five tools the planner has: the three calculators, the labware sheet, and `propose_platemap`.

The model sees the schemas in `SCHEMAS`; the loop calls `Toolbox.call(name, arguments)`, which
returns a JSON-serialisable dict for every call (an `error` key for a wrong name or bad
arguments, never an exception). One `Toolbox` is one episode: it remembers every number the
request or a calculator gave, and `propose_platemap` refuses a map whose volumes came from
anywhere else. That is how "the model never computes a number" is enforced rather than asked.

The calculators are the same functions the agent's tools call (`provette.calc`); what comes back
here is shaped for writing a plate map (what each well ENDS holding, split into stock and
diluent) rather than for writing the transfers.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

from provette.agent.tools import LABWARE_FAMILIES, labware_row
from provette.calc import dilution_series, master_mix, normalise
from provette.intent.spec import PlateMap, PlateMapError, platemap_from_dict

NUMBER_TOLERANCE = 1e-3  # a volume is "one the model was given" within this
_NUMBER = re.compile(r"\d+(?:\.\d+)?")

SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "labware",
            "description": (
                "Call this when the request names labware and you need to know its wells "
                "(a 24-tube rack has A1..D6, a 96-well plate A1..H12, a 12-channel reservoir "
                "A1..A12) or how much a well holds. kind is one of plate, tubes, tips, "
                "reservoir, module_block."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "kind": {
                        "type": "string",
                        "enum": ["plate", "tubes", "tips", "reservoir", "module_block"],
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
                "Call this for any serial dilution or standard curve (1:2, 1:10, ...) instead "
                "of working the volumes out yourself. It returns, for each point in order from "
                "the most concentrated: what the well ends holding, and how much of that is the "
                "original stock and how much is diluent after ideal mixing. Those two numbers "
                "(of_which_stock_ul, of_which_diluent_ul) are what the plate map lists for the "
                "well. Call it twice if the request is ambiguous (first point neat or already "
                "diluted; last well keeps its excess or not) and put each reading in its own "
                "variant."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "stock_concentration": {
                        "type": "number",
                        "description": "The stock's concentration in any unit (1 if unknown).",
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
                        "'from 2 mg/ml down'); false if the first well is already 1:factor "
                        "('a 1:2 serial dilution of a stock').",
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
                "of the request; it returns, for each sample, the ul of sample and the ul of "
                "diluent its well ends holding. Copy those into the plate map as given."
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
                "Call this when the request gives a master mix as its components per reaction "
                "and you need the total per reaction or the volume to pool. The plate map still "
                "lists each component per well (a master mix pooled on the deck resolves to so "
                "many ul of each component); this tool only adds them up for you."
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
            "name": "propose_platemap",
            "description": (
                "Call this to hand in the plate map, as one JSON object in the format of the "
                "system prompt (liquids, destination, variants, discard_intended, notes; id and "
                "request are filled in for you). It is validated: if something is wrong it "
                "returns the error and you fix the map and call again; if it is valid the job "
                "is done. Every volume in it must be a number from the request or from a "
                "calculator result, copied as given."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "platemap": {
                        "type": "object",
                        "description": "The whole plate map as a JSON object.",
                    }
                },
                "required": ["platemap"],
            },
        },
    },
]

TOOL_NAMES = tuple(schema["function"]["name"] for schema in SCHEMAS)

# Offered with `plan(..., allow_decline=True)`, as the product and its evaluation plan; without
# it the planner has only the tools above.
DECLINE_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "not_a_request",
        "description": (
            "Call this ONLY when the message asks for no liquid handling at all (a question, "
            "a greeting, a chat, a task that is not moving liquids between labware). If it "
            "names any liquid, labware or volume, plan it instead, however unclear. The reason "
            "is one short sentence the person will read."
        ),
        "parameters": {
            "type": "object",
            "properties": {"reason": {"type": "string", "description": "One sentence: why."}},
            "required": ["reason"],
        },
    },
}
CALCULATORS = ("dilution_series", "normalise", "master_mix")


class Toolbox:
    """One episode's tools and state. `call` never raises for what the model sends."""

    def __init__(
        self,
        request_id: str,
        request: str,
        technique: str | None = None,
        *,
        allow_decline: bool = False,
    ) -> None:
        self.request_id = request_id
        self.allow_decline = allow_decline
        self.declined: str | None = None  # the model's reason, once it says this is no request
        self.request = request
        self.technique = technique  # the request's technique word, copied into the map
        self.numbers: set[float] = {float(m) for m in _NUMBER.findall(request)}
        self.proposed: PlateMap | None = None  # set once a valid map is handed in
        self.rejections: list[str] = []  # every reason a proposal was refused, in order
        self.repairs: list[str] = []  # every JSON string a closing bracket was added to
        self.last_liquids: list[str] = []  # the liquid names of the last proposal, refused or not

    # -- dispatch ------------------------------------------------------------------------------

    def call(self, name: str, arguments: Mapping[str, Any] | str | None) -> dict[str, Any]:
        """Run one tool. A bad name, bad JSON, wrong arguments: an `error` key, never a raise."""
        names = TOOL_NAMES + (("not_a_request",) if self.allow_decline else ())
        if name not in names:
            return {"error": f"there is no tool named {name!r}. The tools are: {', '.join(names)}."}
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
        except TypeError as error:
            return {"error": f"wrong arguments for {name}: {error}. Check the parameter names."}
        except (ValueError, KeyError) as error:
            return {"error": f"{name}: {error}"}
        if name in CALCULATORS:
            self._remember(result)
        return result

    def _remember(self, value: Any) -> None:
        """Every number a calculator returned may be copied into the map."""
        if isinstance(value, bool):
            return
        if isinstance(value, (int, float)):
            self.numbers.add(float(value))
        elif isinstance(value, Mapping):
            for item in value.values():
                self._remember(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                self._remember(item)

    # -- labware -------------------------------------------------------------------------------

    def tool_labware(self, kind: str) -> dict[str, Any]:
        if kind not in LABWARE_FAMILIES:
            raise ValueError(f"kind must be one of {', '.join(LABWARE_FAMILIES)}, not {kind!r}")
        return {"kind": kind, "labware": [labware_row(n, kind) for n in LABWARE_FAMILIES[kind]]}

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
        wells = [
            {
                "point": p["well_index"],
                "dilution": p["dilution"],
                "ends_holding_ul": _r(p["holds_ul"]),
                "of_which_stock_ul": _r(p["stock_ul"]),
                "of_which_diluent_ul": _r(p["holds_ul"] - p["stock_ul"]),
            }
            for p in series
        ]
        last = series[-1]
        return {
            "wells": wells,
            "reading": {
                "first_point_is_stock": bool(first_point_is_stock),
                "remove_excess": bool(remove_excess),
                "last_well_holds_ul": _r(last["holds_ul"]),
            },
            "how_to_use": (
                "For each point, the well's contents in the plate map are of_which_stock_ul of "
                "the stock liquid and of_which_diluent_ul of the diluent (leave the diluent out "
                "where it is 0). Copy the numbers as given."
            ),
        }

    def tool_normalise(
        self, concentrations: Sequence[float], target: float, final_volume_ul: float
    ) -> dict[str, Any]:
        rows = normalise([float(c) for c in concentrations], float(target), float(final_volume_ul))
        return {
            "samples": [
                {
                    "sample": row["index"],
                    "concentration": row["concentration"],
                    "sample_ul": _r(row["sample_ul"]),
                    "diluent_ul": _r(row["diluent_ul"]),
                    **({"warning": row["warning"]} if row["warning"] else {}),
                }
                for row in rows
            ],
            "how_to_use": (
                "Sample i's well holds sample_ul of sample i and diluent_ul of the diluent. "
                "Copy the numbers as given, to four decimals."
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
            "how_to_use": (
                "The plate map lists each component per well at its ul_per_reaction, not the "
                "pooled total."
            ),
        }

    # -- the proposal --------------------------------------------------------------------------

    def tool_not_a_request(self, reason: str = "") -> dict[str, Any]:
        """The model says the message asks for no liquid handling; the episode ends, no map."""
        self.declined = " ".join(str(reason).split())[:300] or "It asks for no liquid handling."
        return {"ok": True}

    def tool_propose_platemap(self, platemap: Mapping[str, Any] | str) -> dict[str, Any]:
        repaired: str | None = None
        if isinstance(platemap, str):
            try:
                platemap, repaired = loads_closing_brackets(platemap)
            except json.JSONDecodeError as error:
                return self._refuse(
                    f"the platemap was sent as a string and it is not valid JSON ({error}). "
                    "Send it as a JSON object (the value of 'platemap' is the map itself, not "
                    "a string containing it), and write every member out: there is no "
                    "shorthand for repetition."
                )
            if repaired:
                self.repairs.append(repaired)
        if not isinstance(platemap, Mapping):
            return self._refuse("the platemap must be a JSON object")
        liquids = platemap.get("liquids")
        self.last_liquids = [
            str(item.get("name")) for item in (liquids if isinstance(liquids, list) else [])
            if isinstance(item, Mapping) and item.get("name")
        ]  # fmt: skip
        row = {**platemap, "id": self.request_id, "request": self.request}
        if self.technique is not None:
            row["technique"] = self.technique
        try:
            candidate = platemap_from_dict(row)
        except PlateMapError as error:
            return self._refuse(str(error))
        except (AttributeError, ValueError, TypeError) as error:
            return self._refuse(f"the plate map is not in the format described: {error}")
        # The writer is told to declare each liquid by the name this map gives it
        # (provette.agent.tools.liquid_names); a name its own pattern does not match passes here
        # and stops the run the moment it starts. Refused now, so the planner repairs it.
        from provette.agent.tools import liquid_names

        try:
            liquid_names(row)
        except (ValueError, KeyError) as error:
            return self._refuse(
                f"{error}. A protocol declares each liquid by its name (underscores as spaces), "
                "so the name must be one its own pattern matches: rename the liquid to fit the "
                "pattern, or widen the pattern to fit the name."
            )
        foreign = self.foreign_amounts(candidate)
        if foreign:
            listed = ", ".join(f"{amount:g} ul of {logical} ({where})" for where, logical, amount
                               in foreign[:6])  # fmt: skip
            return self._refuse(
                f"these volumes come neither from the request nor from a calculator result: "
                f"{listed}. Volumes are copied, never computed: use the number as the request "
                "writes it, or call dilution_series, normalise or master_mix and copy its result."
            )
        self.proposed = candidate
        out = {
            "accepted": True,
            "liquids": len(candidate.liquids),
            "variants": len(candidate.variants),
            "note": "The plate map is valid and has been recorded. You are done.",
        }
        if repaired:
            out["repaired"] = repaired
        return out

    def _refuse(self, reason: str) -> dict[str, Any]:
        self.rejections.append(reason)
        return {
            "accepted": False,
            "error": reason,
            "next": "Fix the plate map and call propose_platemap again with the whole map.",
        }

    def foreign_amounts(self, platemap: PlateMap) -> list[tuple[str, str, float]]:
        """(where, logical liquid, amount) for every amount the model was never given."""
        out: list[tuple[str, str, float]] = []
        for variant in platemap.variants:
            for well, contents in variant.pinned.items():
                out += self._foreign(f"variant {variant.name!r}, well {well}", contents)
            for group in variant.groups:
                for member in group.members:
                    out += self._foreign(f"variant {variant.name!r}, group {group.name!r}", member)
        return out

    def _foreign(self, where: str, contents: Mapping[str, Any]) -> list[tuple[str, str, float]]:
        out = []
        for logical, amount in contents.items():
            if amount == "declared":
                continue
            value = float(amount)
            if not any(abs(value - known) <= NUMBER_TOLERANCE for known in self.numbers):
                out.append((where, logical, value))
        return out


def loads_closing_brackets(text: str, attempts: int = 4) -> tuple[Any, str | None]:
    """`json.loads`, forgiving one kind of slip: a closing bracket left out before a comma.

    Nemotron, sending a long map as a string, writes `... "order_hint": "index"}]}, "notes"`
    where a `]` should close `variants` before the comma, then re-sends the same text. The
    structure is not in doubt (the next key belongs to the level above), so the bracket is put
    in and the repair is reported. Anything else still raises `json.JSONDecodeError`.
    """
    repaired: list[str] = []
    for _ in range(attempts):
        try:
            return json.loads(text), ("; ".join(repaired) or None)
        except json.JSONDecodeError as error:
            comma = _last_comma_before(text, error.pos)
            closer = _innermost_closer(text, comma) if comma is not None else None
            if closer is None:
                raise
            repaired.append(f"inserted {closer!r} at character {comma}")
            text = text[:comma] + closer + text[comma:]
    return json.loads(text), "; ".join(repaired)


def _last_comma_before(text: str, position: int) -> int | None:
    """The last comma outside a string before `position`, or None."""
    last = None
    in_string = escaped = False
    for index, char in enumerate(text[:position]):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif char == ",":
            last = index
    return last


def _innermost_closer(text: str, position: int) -> str | None:
    """The bracket that would close the innermost open one at `position`, or None at depth 0."""
    stack: list[str] = []
    in_string = escaped = False
    for char in text[:position]:
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif char in "[{":
            stack.append("]" if char == "[" else "}")
        elif char in "]}" and stack:
            stack.pop()
    return stack[-1] if stack else None


def _r(value: float) -> float:
    return round(value, 4)
