"""`provette view`'s page, as the product embeds it: the same export, the same script, with two
optional touches the product's frame asks for in the query string.

    ?theme=dark   the page's own colour tokens set to the product's dark values
    ?embed=1      no header, footer or prep sheet: the product's page has its own
    ?compact=1    the view's own compact mode (provette/view/replay.css): the product's type scale,
                  tighter margins, labware labels of at least 11 px; the page then posts its
                  height to the frame (provette/view/replay.js)

Nothing in `provette/view` changes: the page is rendered by `provette.view.page.render` and a
`<style>` block is appended before `</head>`. The deck, the liquids and the severities keep the
view's colours in both themes, because those are the replay's meaning.
"""

from __future__ import annotations

from typing import Any

from provette.view.page import render

DARK = """
:root, html.compact { --ink: #e8eaee; --muted: #9aa3b0; --line: #2a2f38; --paper: #0f1115;
  --panel: #171a20; --cur: #3a3410; --note: #7fb0ff; --ok: #3ecf8e; --error: #ff7b72;
  --warning: #f0a44a; }
.controls button { background: #171a20; border-color: #2a2f38; color: #e8eaee; }
.controls button:hover { background: #1f232b; }
.finding { background: #171a20; } .finding:hover { background: #1f232b; }
.finding.selected { outline-color: #e8eaee; }
#code .num { color: #6c7581; }
.prep tr.flag td { background: #3a2a12; }
.swatch.hatch { background: repeating-linear-gradient(45deg, #0072B2 0 3px, #171a20 3px 6px); }
.swatch.parked { background: repeating-linear-gradient(45deg, #8a6d00 0 2px, #171a20 2px 4px); }
.swatch.gone { background: #171a20; }
.slot { fill: #1f232b; stroke: #2a2f38; }
.slot-number { fill: #3a404b; }
.well-base { fill: #23272f; }
.lw-body { fill: #2b303a; stroke: #6c7581; }
.trash .lw-body { fill: #1f232b; }
.lw-label { fill: #e8eaee; stroke: #2b303a; }
.well-outline { stroke: #6c7581; }
.pipette-tip .tip-body { fill: #e8eaee; }
.tip-label { fill: #e8eaee; stroke: #0f1115; }
"""

EMBED = """
header, footer, .prep { display: none; }
main { padding-top: 10px; }
"""


def replay_page(
    export: dict[str, Any], theme: str | None = None, embed: bool = False, compact: bool = False
) -> str:
    page = render(export, compact=compact)
    extra = (DARK if theme == "dark" else "") + (EMBED if embed else "")
    if extra:
        page = page.replace("</head>", f"<style>{extra}</style>\n</head>", 1)
    return page
