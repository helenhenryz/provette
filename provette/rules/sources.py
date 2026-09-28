"""The sources rules cite, read from `sources.yaml` next to this file: every entry is a row of
docs/rule-sources.md, and we own the file.

A rule written in Python cites one as an attribute of this module, as it always has:

    from provette.rules import sources
    Rule(..., sources=(sources.THERMO_T4_LIGASE,))

A declared rule cites the key by name in its `sources` list. Both read the same registry,
`SOURCES` below, filled from the file when this module is imported. A key the file does not
hold raises `SourcesFileError` at the rule's import, naming the key, so a rule never runs on
a source it cannot show. `reload()` reads the file again (`sources_edit.add_source` calls it
after appending an entry); `PROVETTE_SOURCES_FILE` names another file to read, for a test's copy.

To add a source: add it to docs/rule-sources.md, with what it says, then to `sources.yaml`
(the file's top comment shows the three lines), or through the product's rule form.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml

from provette.rules.finding import Source

SOURCES_FILE = Path(
    os.environ.get("PROVETTE_SOURCES_FILE") or Path(__file__).with_name("sources.yaml")
)

KEY_PATTERN = re.compile(r"[A-Z][A-Z0-9]*(_[A-Z0-9]+)*")
URL_PATTERN = re.compile(r"https?://\S+")

# The registry: every source in the file, by its key, in file order. `declared.py` checks a
# declared rule's `sources` against it; `reload()` refills it in place, so every reference to
# it sees an added source.
SOURCES: dict[str, Source] = {}


class SourcesFileError(ValueError):
    """`sources.yaml` is not a file of sources, or a rule cites a key it does not hold."""


def load_sources(path: Path | None = None) -> dict[str, Source]:
    """Every source in the file, by key, in file order. Raises SourcesFileError on a bad shape:
    the message names the file and the entry."""
    where = path or SOURCES_FILE
    loaded: Any = yaml.safe_load(where.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise SourcesFileError(f"{where} must hold one entry per source, named in capitals")
    sources: dict[str, Source] = {}
    for key, fields in loaded.items():
        if not isinstance(key, str) or not KEY_PATTERN.fullmatch(key):
            raise SourcesFileError(f"{where}: {key!r} is not a source name (capitals and _)")
        if not isinstance(fields, dict) or set(fields) != {"name", "url"}:
            raise SourcesFileError(f"{where}: {key} must have exactly `name` and `url`")
        name, url = fields["name"], fields["url"]
        if not isinstance(name, str) or not name.strip() or "\n" in name.strip():
            raise SourcesFileError(f"{where}: {key}: `name` must be one line of text")
        if not isinstance(url, str) or not URL_PATTERN.fullmatch(url.strip()):
            raise SourcesFileError(f"{where}: {key}: `url` must start with http:// or https://")
        sources[key] = Source(name.strip(), url.strip())
    return sources


def reload(path: Path | None = None) -> None:
    """Read the file (`SOURCES_FILE` unless a path is given) and use its sources from now."""
    loaded = load_sources(path)
    SOURCES.clear()
    SOURCES.update(loaded)
    globals().update(loaded)  # `sources.THERMO_T4_LIGASE`, as the Python rules cite them


def __getattr__(name: str) -> Source:
    """A key the file does not hold: raised where a rule cites it, with the key's name."""
    if KEY_PATTERN.fullmatch(name):
        raise SourcesFileError(
            f"{name} is not a source in {SOURCES_FILE}: add it there (see the top of the file, "
            f"and docs/rule-sources.md) before a rule cites it"
        )
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


reload()
