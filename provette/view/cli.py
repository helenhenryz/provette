"""`provette view protocol.py [--platemap map.json] --out replay.html`: the deck replay page.

Exit codes: 0 the page was written, 2 the simulator rejected the protocol, 3 the plate map
could not be read.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from provette.check import check
from provette.intent.cli import verify_trace
from provette.intent.spec import PlateMapError, load_platemap
from provette.trace import TraceError
from provette.view.export import export
from provette.view.page import render


def build(protocol: Path, platemap: Path | None = None, labware_dirs: tuple[Path, ...] = ()) -> str:
    """The page for `protocol`. Raises TraceError, OSError or PlateMapError."""
    result = check(protocol, labware_dirs=labware_dirs)
    verification = None
    if platemap is not None:
        verification = verify_trace(result.trace, result.run, load_platemap(platemap))
    return render(export(result, verification, labware_dirs))


def _command(args: argparse.Namespace) -> int:
    try:
        page = build(args.protocol, args.platemap, tuple(args.labware_dir or ()))
    except TraceError as error:
        where = f" (line {error.line})" if error.line is not None else ""
        print(f"The Opentrons simulator rejected {args.protocol.name}{where}:\n  {error}")
        return 2
    except (OSError, PlateMapError) as error:
        print(f"Cannot read the plate map {args.platemap}: {error}")
        return 3
    args.out.write_text(page, encoding="utf-8")
    print(f"Wrote {args.out} ({args.out.stat().st_size / 1024:.0f} KB). Open it in a browser.")
    return 0


def register(sub: Any) -> None:
    p = sub.add_parser("view", help="write a web page that replays the protocol on the deck")
    p.add_argument("protocol", type=Path)
    p.add_argument("--platemap", type=Path, help="the plate map (JSON): adds verify and prep")
    p.add_argument("--labware-dir", type=Path, action="append", help="custom labware (*.json)")
    p.add_argument("--out", type=Path, required=True, help="where to write the HTML file")
    p.set_defaults(func=_command)
