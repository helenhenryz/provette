from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from provette.corpus.library import discover
from provette.corpus.prepare import PreparedProtocol, prepare


def _get_values(prepared: PreparedProtocol) -> Callable[..., list[Any]]:
    """Execute only the prepended header and hand back its `get_values`."""
    lines = Path(prepared.path).read_text(encoding="utf-8").splitlines(keepends=True)
    scope: dict[str, Any] = {}
    exec("".join(lines[: prepared.line_offset]), scope)
    function: Callable[..., list[Any]] = scope["get_values"]
    return function


def test_defaults_for_every_field_type(make_folder: Callable[..., Path], tmp_path: Path) -> None:
    fields = [
        {"type": "int", "name": "samples", "label": "n", "default": 96},
        {"type": "float", "name": "volume", "label": "v", "default": 12.5},
        {"type": "str", "name": "name", "label": "s", "default": "it's \"quoted\""},
        {"type": "string", "name": "other", "label": "s", "default": ""},
        {"type": "textFile", "name": "csv", "label": "f", "default": "well,vol\nA1,5\nB1,7\n"},
        {"type": "dropDown", "name": "mount", "label": "m",
         "options": [{"label": "Right", "value": "right"}, {"label": "Left", "value": "left"}]},
        {"type": "dropDown", "name": "park", "label": "p",
         "options": [{"label": "No", "value": False}, {"label": "Yes", "value": True}]},
        {"type": "dropDown", "name": "nothing", "label": "n",
         "options": [{"label": "None", "value": None}]},
    ]  # fmt: skip
    [protocol] = discover(make_folder(fields=fields))
    prepared = prepare(protocol, tmp_path / "out")
    names = [f["name"] for f in fields]
    expected = [96, 12.5, 'it\'s "quoted"', "", "well,vol\nA1,5\nB1,7\n", "right", False, None]
    assert _get_values(prepared)(*names) == expected
    assert _get_values(prepared)("volume") == [12.5]
    assert prepared.values == dict(zip(names, expected, strict=True))


def test_line_offset_maps_back_to_the_original(
    make_folder: Callable[..., Path], tmp_path: Path
) -> None:
    [protocol] = discover(make_folder())
    prepared = prepare(protocol, tmp_path / "out")
    original = protocol.source.read_text(encoding="utf-8").splitlines()
    written = Path(prepared.path).read_text(encoding="utf-8").splitlines()
    assert prepared.line_offset > 0
    assert len(written) == len(original) + prepared.line_offset
    for number, line in enumerate(written, start=1):
        mapped = prepared.original_line(number)
        if number <= prepared.line_offset:
            assert mapped is None
        else:
            assert mapped is not None and original[mapped - 1] == line
    assert prepared.original_line(prepared.line_offset + 1) == 1


def test_multiline_default_does_not_move_the_offset(
    make_folder: Callable[..., Path], tmp_path: Path
) -> None:
    short = [{"type": "textFile", "name": "csv", "label": "f", "default": "a"}]
    long = [{"type": "textFile", "name": "csv", "label": "f", "default": "a\nb\nc\nd\n"}]
    [first] = discover(make_folder("one", fields=short))
    second = next(p for p in discover(make_folder("two", fields=long)) if p.slug == "two")
    out = tmp_path / "out"
    assert prepare(first, out).line_offset == prepare(second, out).line_offset


def test_no_fields_json_is_copied_unchanged(
    make_folder: Callable[..., Path], tmp_path: Path
) -> None:
    [protocol] = discover(make_folder(fields=None, source="x = 1\n"))
    prepared = prepare(protocol, tmp_path / "out")
    assert prepared.line_offset == 0 and prepared.values == {}
    assert Path(prepared.path).read_text(encoding="utf-8") == "x = 1\n"
    assert prepared.original_line(1) == 1


def test_overrides(make_folder: Callable[..., Path], tmp_path: Path) -> None:
    [protocol] = discover(make_folder())
    prepared = prepare(protocol, tmp_path / "out", overrides={"tip_reuse": "never"})
    assert _get_values(prepared)("volume", "tip_reuse") == [50.0, "never"]
    assert prepared.values == {"volume": 50.0, "tip_reuse": "never"}
    with pytest.raises(ValueError, match="no parameter named tip_reuze"):
        prepare(protocol, tmp_path / "out", overrides={"tip_reuze": "never"})


def test_round_trips_as_a_plain_dict(make_folder: Callable[..., Path], tmp_path: Path) -> None:
    [protocol] = discover(make_folder(labware_dir="labware"))
    prepared = prepare(protocol, tmp_path / "out")
    row = prepared.to_dict()
    assert row["slug"] == "synthetic" and row["labware_dir"].endswith("labware")
    assert row["path"] == str(tmp_path / "out" / "synthetic" / "synthetic.ot2.apiv2.py")
    assert PreparedProtocol.from_dict(row) == prepared
