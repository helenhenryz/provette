"""The deck replay: one HTML page that plays a protocol back and shows the findings on the deck.

`provette view protocol.py --out replay.html`. See README.md in this folder.
"""

from provette.view.export import export, replay_deltas
from provette.view.page import render

__all__ = ["export", "render", "replay_deltas"]
