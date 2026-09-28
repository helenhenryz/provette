"""The page in the product's frame: `render(data, compact=True)` opens in the compact mode,
the compact stylesheet holds the labels' size token, and the script posts the page's height
to its parent. String-level: no browser runs in the gate (the view is checked by hand in
headless Chrome; docs/ui-needs.md #3)."""

from __future__ import annotations

import re

from provette.view import export, render
from tests.view.test_export import hand_built


def test_compact_sets_the_class_the_stylesheet_keys_on() -> None:
    plain = render(export(hand_built()))
    compact = render(export(hand_built()), compact=True)
    assert '<html lang="en">' in plain and 'class="compact"' not in plain
    assert '<html lang="en" class="compact">' in compact
    # the same page otherwise: the compact rules ship in both, keyed on the class
    assert compact.replace(' class="compact"', "", 1) == plain


def test_the_compact_stylesheet_holds_the_labels_size_token() -> None:
    page = render(export(hand_built()), compact=True)
    assert re.search(r":root \{[^}]*--label-min-px: 0;", page)  # the deck's own 5 units by default
    assert re.search(r"html\.compact \{[^}]*--label-min-px: 11;", page)  # at least 11 px on screen
    assert "html.compact .lw-label" in page  # the halo over the wells
    assert "getPropertyValue('--label-min-px')" in page  # the script reads the token
    assert "window.addEventListener('resize', fitLabels)" in page


def test_the_page_honours_the_query_string_on_its_own() -> None:
    page = render(export(hand_built()))
    head = page.split("</head>", 1)[0]
    assert "compact=1" in head and 'classList.add("compact")' in head


def test_the_page_posts_its_height_to_the_frame() -> None:
    page = render(export(hand_built()), compact=True)
    assert "window.parent.postMessage({ type: 'provette:height', height: height }, '*')" in page
    assert "window.parent === window" in page  # and never when it is not in a frame
    assert "window.addEventListener('resize', queueHeight)" in page
    assert "new ResizeObserver(queueHeight).observe(document.body)" in page
