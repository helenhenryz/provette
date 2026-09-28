"""Make a library protocol runnable: give it the `get_values` function its source expects.

A library protocol reads its user-facing parameters with `get_values("name", ...)`, a function
the Opentrons website injects. The library's own build tool (`protolib/parse/parseOT2v2.py`)
prepends one that returns the defaults from `fields.json`; this does the same, with the option
of overriding individual values, and remembers how far it pushed the source down the file.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from provette.corpus.library import LibraryProtocol, default_value

_HEADER = """\
def get_values(*names):
    _values = {values!r}
    return [_values[name] for name in names]


"""


@dataclass(frozen=True)
class PreparedProtocol:
    """A runnable copy of a library protocol. This, as a plain dict, is what a worker receives."""

    slug: str
    path: str  # the prepared copy, under `.cache/`
    original_path: str  # the library's own file
    labware_dir: str | None
    line_offset: int  # lines prepended: prepared line = original line + line_offset
    values: dict[str, Any]  # what `get_values` returns, overrides applied
    api_level: str | None
    categories: list[str]

    def original_line(self, prepared_line: int) -> int | None:
        """The line of the original source for a line of the prepared file.

        None for a line inside the prepended `get_values`, which has no original.
        """
        return original_line(prepared_line, self.line_offset)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(row: dict[str, Any]) -> PreparedProtocol:
        return PreparedProtocol(**row)


def original_line(prepared_line: int, line_offset: int) -> int | None:
    return prepared_line - line_offset if prepared_line > line_offset else None


def prepare(
    protocol: LibraryProtocol, out_dir: Path, overrides: dict[str, object] | None = None
) -> PreparedProtocol:
    """Write `<out_dir>/<slug>/<original file name>` with `get_values` prepended.

    `out_dir` must be under `.cache/` when used on the real library (DECISIONS.md D-05).
    A protocol with no `fields.json` is copied unchanged, with a line offset of 0. An override
    that names a parameter the protocol does not have is an error, not a silent no-op.
    """
    source = protocol.source.read_text(encoding="utf-8", errors="replace")
    values: dict[str, Any] = {}
    if protocol.fields_json is not None:
        fields = json.loads(protocol.fields_json.read_text(encoding="utf-8"))
        values = {f["name"]: default_value(f) for f in fields}
    unknown = sorted(set(overrides or {}) - set(values))
    if unknown:
        raise ValueError(f"{protocol.slug} has no parameter named {', '.join(unknown)}")
    values.update(overrides or {})

    header = _HEADER.format(values=values) if protocol.fields_json is not None else ""
    target = out_dir / protocol.slug / protocol.source.name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(header + source, encoding="utf-8")
    return PreparedProtocol(
        slug=protocol.slug,
        path=str(target),
        original_path=str(protocol.source),
        labware_dir=str(protocol.labware_dir) if protocol.labware_dir else None,
        line_offset=header.count("\n"),
        values=values,
        api_level=protocol.api_level,
        categories=protocol.categories,
    )
