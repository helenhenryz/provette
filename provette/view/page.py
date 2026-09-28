"""The HTML page: one file, everything inline. `render(data) -> str`.

The layout, top to bottom: the verdict; the deck with the controls and the close-up beside
it; the code panel, the findings and the legend; the prep sheet; the footer. The skeleton is
`page.html`, the style `replay.css` and the script `replay.js`, all next to this file and
pasted in, so the script can be parsed on its own with `node --check`.
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).parent

FOOTER = (
    "This checks the logic of the protocol: what goes where, and how much. It does not check "
    "the physics: whether a viscous liquid is pipetted accurately, or a drop stays on a tip."
)

FLAG_WORDS = {
    "would_run_dry": "WOULD RUN DRY",
    "no_margin": "NO MARGIN",
    "draws_air": "DRAWS AIR",
}


def render(data: dict[str, Any], compact: bool = False) -> str:
    """The whole page as a string. `data` is what `export` returns. `compact` is the product's
    frame: the page opens in its compact mode (replay.css, "compact") without waiting for the
    query string; `?compact=1` on the file does the same."""
    payload = json.dumps(data, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
    script = (HERE / "replay.js").read_text(encoding="utf-8").replace("</script", "<\\/script")
    style = (HERE / "replay.css").read_text(encoding="utf-8")
    page = (HERE / "page.html").read_text(encoding="utf-8")
    # The data and the script go in last: nothing is substituted inside them.
    for token, text in (
        ("__HTML_CLASS__", ' class="compact"' if compact else ""),
        ("__TITLE__", html.escape(data["protocol"])),
        ("__VERDICT__", _verdict(data["summary"])),
        ("__DECK_TABLE__", _deck_table(data)),
        ("__PREP__", _prep(data.get("verify"))),
        ("__FOOTER__", html.escape(FOOTER)),
        ("__CSS__", style),
        ("__DATA__", payload),
        ("__JS__", script),
    ):
        page = page.replace(token, text)
    return page


def _verdict(summary: dict[str, Any]) -> str:
    counts = summary["counts"]
    check_class = "bad" if counts["error"] or counts["warning"] else "ok"
    parts = [
        f'<span class="sim">{html.escape(summary["simulator"])}</span>',
        f'<span class="check {check_class}">{html.escape(summary["check"])}</span>',
    ]
    if summary["verify"]:
        ok = "ok" if summary["verify"].startswith("VERIFIED") else "bad"
        parts.append(f'<span class="check {ok}">{html.escape(summary["verify"])}</span>')
    return "".join(parts)


def _deck_table(data: dict[str, Any]) -> str:
    rows = []
    for lw in data["deck"]["labware"]:
        what = "the trash" if lw["is_trash"] else lw["name"]
        extra = ""
        if lw["is_tiprack"]:
            extra = " (tips)"
        elif lw["module"]:
            extra = f" on a {html.escape(str(lw['module']))}"
        note = "" if lw["measured"] else " - well positions are a guess"
        rows.append(
            f"<tr><td>slot {html.escape(lw['slot'])}</td>"
            f"<td>{html.escape(what)}{extra}{note}</td></tr>"
        )
    for p in data["pipettes"]:
        channels = f"{p['channels']} channel{'s' if p['channels'] != 1 else ''}"
        rows.append(
            f"<tr><td>{html.escape(p['mount'])} pipette</td>"
            f"<td>{html.escape(p['name'])} ({channels})</td></tr>"
        )
    return f'<table class="prep-table"><tbody>{"".join(rows)}</tbody></table>'


def _prep(verify: dict[str, Any] | None) -> str:
    if verify is None:
        return ""
    head = (
        "<tr><th>slot</th><th>labware</th><th>well</th><th>liquid</th>"
        "<th>load at least (µl)</th><th>declared (µl)</th><th></th></tr>"
    )
    rows = []
    for line in verify["prep"]["lines"]:
        declared = "-" if line["declared_ul"] is None else f"{line['declared_ul']:.1f}"
        flag = FLAG_WORDS.get(line["flag"], "") if line["flag"] else ""
        if not flag and line.get("already_in_plate"):
            flag = f"already in the plate: {line['declared_ul']:.1f} declared, nothing drawn"
        rows.append(
            f'<tr class="{"flag" if line["flag"] else ""}"><td>{html.escape(line["slot"])}</td>'
            f"<td>{html.escape(line['labware'])}</td><td>{html.escape(line['well'])}</td>"
            f"<td>{html.escape(line['liquid'])}</td>"
            f'<td class="num">{line["needed_ul"]:.1f}</td><td class="num">{declared}</td>'
            f"<td>{html.escape(flag)}</td></tr>"
        )
    flags = "".join(f"<div>{html.escape(f)}</div>" for f in verify["flags"])
    note = "'Load at least' is what the robot draws. Add the dead volume of your tube or reservoir."
    return (
        '<section class="prep">\n'
        "  <h2>Prep sheet: what to put on the deck before the run</h2>\n"
        f"  <table>{head}{''.join(rows)}</table>\n"
        f'  <div class="flags">{flags}</div>\n'
        f'  <div class="key">{note}</div>\n'
        "  <details><summary>The full report, as <code>provette verify</code> prints it</summary>\n"
        f"  <pre>{html.escape(verify['text'])}</pre></details>\n"
        "</section>"
    )
