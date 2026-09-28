"""Repairs of the slips a model makes again and again, made before the simulator sees a draft.

Read from 506 drafts in eval/agent: the same few slips cost the models a draft each time, and
none of them is a matter of judgement. A code editor would fix them on save; so does this.
Every repair is reported back to the model in words, so it learns the right form, and the
model's own text is kept beside the repaired file. Nothing here changes what a protocol does:
a name string becomes the object it names, an invented labware name becomes the real one it
was clearly meant to be, a missing colour or import is added, a keyword load_liquid does not
take is dropped (one episode spent all twenty drafts on `ribbon=`, because the simulator's
error named the tracer's wrapper and not the call). Anything less certain than that is left
alone and goes to the simulator, whose error carries a hint.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass

# Invented names seen in the transcripts, and the real name each stood for.
ALIASES = {
    "opentrons_96_tiprack_200ul": "opentrons_96_filtertiprack_200ul",
    "opentrons_24_tuberack_nest_1_5ml_snapcap": "opentrons_24_tuberack_nest_1.5ml_snapcap",
    "opentrons_12_tuberack_nest_1.5ml_snapcap": "opentrons_24_tuberack_nest_1.5ml_snapcap",
    "nest_96_aluminumblock_nest_wellplate_100ul": "opentrons_96_aluminumblock_nest_wellplate_100ul",
}
PALETTE = ("#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#17becf")

_DEFINE = re.compile(
    r"(?P<var>[A-Za-z_]\w*)\s*=\s*protocol\.define_liquid\(\s*(?:name\s*=\s*)?(?P<q>[\"'])"
    r"(?P<name>[^\"']+)(?P=q)"
)
_LOAD_STRING = re.compile(
    r"\.load_liquid\(\s*(?:liquid\s*=\s*)?(?P<q>[\"'])(?P<name>[^\"']+)(?P=q)"
)
_LOAD_NAME = re.compile(r"load_labware\(\s*(?P<q>[\"'])(?P<name>[^\"']+)(?P=q)")
_DEFINE_CALL = re.compile(r"define_liquid\((?P<args>[^()]*)\)")
_LOAD_CALL = re.compile(r"\.load_liquid\((?P<args>[^()]*)\)")
_KEYWORD = re.compile(r"^\s*(?P<kw>[A-Za-z_]\w*)\s*=(?!=)")
LOAD_LIQUID_ARGS = ("liquid", "volume")  # the whole signature, in the Opentrons API


@dataclass(frozen=True)
class Lint:
    text: str
    fixes: tuple[str, ...]  # one sentence each, for the model


def prelint(text: str) -> Lint:
    fixes: list[str] = []
    for step in (
        _liquid_objects,
        _load_liquid_keywords,
        _real_labware_names,
        _display_colours,
        _import,
    ):
        text, done = step(text)
        fixes.extend(done)
    return Lint(text, tuple(fixes))


def _liquid_objects(text: str) -> tuple[str, list[str]]:
    """`well.load_liquid("PBS", 100)` -> `well.load_liquid(pbs, 100)` when `pbs` was defined."""
    variables: dict[str, str] = {}
    for m in _DEFINE.finditer(text):
        variables.setdefault(m.group("name"), m.group("var"))
    fixes: list[str] = []

    def swap(m: re.Match[str]) -> str:
        name = m.group("name")
        if name not in variables:
            return m.group(0)
        var = variables[name]
        fixes.append(
            f"load_liquid was given the name string {name!r}; replaced with the object "
            f"`{var}` that define_liquid returned for it. Pass the object, not the name."
        )
        return f".load_liquid({var}"

    return _LOAD_STRING.sub(swap, text), fixes


def _split_arguments(args: str) -> list[str]:
    """Top-level comma split: a comma inside a string or a bracket does not separate."""
    parts: list[str] = []
    current: list[str] = []
    depth = 0
    quote: str | None = None
    for ch in args:
        if quote:
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append("".join(current))
            current = []
            continue
        current.append(ch)
    parts.append("".join(current))
    return parts


def _load_liquid_keywords(text: str) -> tuple[str, list[str]]:
    """`well.load_liquid(mm, 100, ribbon=...)` -> `well.load_liquid(mm, 100)`: only this call."""
    fixes: list[str] = []

    def drop(m: re.Match[str]) -> str:
        kept: list[str] = []
        dropped: list[str] = []
        for part in _split_arguments(m.group("args")):
            keyword = _KEYWORD.match(part)
            if keyword and keyword.group("kw") not in LOAD_LIQUID_ARGS:
                dropped.append(keyword.group("kw"))
            else:
                kept.append(part.strip())
        if not dropped:
            return m.group(0)
        for kw in dropped:
            fixes.append(
                f"load_liquid takes only (liquid, volume); there is no argument called {kw!r} "
                f"in the Opentrons API, so `{kw}=...` was removed from the call."
            )
        return f".load_liquid({', '.join(p for p in kept if p)})"

    return _LOAD_CALL.sub(drop, text), fixes


def _real_names() -> list[str]:
    from provette.agent.tools import LABWARE_FAMILIES  # tools imports this module; so, lazily

    return sorted({name for names in LABWARE_FAMILIES.values() for name in names})


def _real_labware_names(text: str) -> tuple[str, list[str]]:
    fixes: list[str] = []
    real_names = _real_names()

    def swap(m: re.Match[str]) -> str:
        name = m.group("name")
        if name in real_names:
            return m.group(0)
        real = ALIASES.get(name)
        if real is None:
            close = difflib.get_close_matches(name, real_names, n=2, cutoff=0.9)
            real = close[0] if len(close) == 1 else None
        if real is None:
            return m.group(0)
        fixes.append(f"There is no labware called {name!r}; replaced with {real!r}.")
        return f"load_labware({m.group('q')}{real}{m.group('q')}"

    return _LOAD_NAME.sub(swap, text), fixes


def _display_colours(text: str) -> tuple[str, list[str]]:
    fixes: list[str] = []
    count = 0

    def add(m: re.Match[str]) -> str:
        nonlocal count
        args = m.group("args")
        # a colour given by keyword, or as the third positional argument
        if "display_color" in args or len([a for a in args.split(",") if a.strip()]) >= 3:
            return m.group(0)
        colour = PALETTE[count % len(PALETTE)]
        count += 1
        sep = ", " if args.strip() else ""
        return f"define_liquid({args}{sep}display_color={colour!r})"

    out = _DEFINE_CALL.sub(add, text)
    if count:
        fixes.append(
            f"define_liquid needs a display_color; added one to {count} call"
            f"{'s' if count > 1 else ''}."
        )
    return out, fixes


def _import(text: str) -> tuple[str, list[str]]:
    if "protocol_api" in text and not re.search(
        r"^\s*from opentrons import .*protocol_api", text, re.M
    ):
        return "from opentrons import protocol_api\n" + text, [
            "`protocol_api` was used without being imported; added "
            "`from opentrons import protocol_api`."
        ]
    return text, []
