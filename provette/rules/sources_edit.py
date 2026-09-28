"""Adding a source: what the product calls when a datasheet is not in the list.

    from provette.rules import sources_edit
    sources_edit.all_sources()   # {"THERMO_T4_LIGASE": {"name": ..., "url": ...}, ...}
    sources_edit.add_source("MY_LAB_MANUAL", "My lab's manual: keep the enzyme on ice", "https://...")

`add_source` appends one entry (three lines) to the end of `sources.yaml`, keeping every
comment and every other entry as it is (a line-based append, not a YAML round trip, because a
round trip drops our comments), then reloads the registry so the running process,
and the rule form's validation, know the key at once. It refuses a key that is not capitals
and underscores, a key the file already holds, an empty name, a url that does not start with
http:// or https://, and any field that is not one line.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from provette.rules import sources
from provette.rules.sources import KEY_PATTERN, URL_PATTERN


class SourcesEditError(ValueError):
    """The source cannot be added; the message says why, in plain words."""


def all_sources() -> dict[str, dict[str, str]]:
    """Every source as the file holds it, by key, in file order: {"name": ..., "url": ...}."""
    return {
        key: {"name": source.name, "url": source.url}
        for key, source in sources.load_sources(sources.SOURCES_FILE).items()
    }


def add_source(key: str, name: str, url: str) -> None:
    """Append the source to `sources.SOURCES_FILE` and reload the registry."""
    path = sources.SOURCES_FILE
    key, name, url = _clean(key, name, url, path)
    text = path.read_text(encoding="utf-8")
    if text and not text.endswith("\n"):
        text += "\n"
    text += _entry(key, name, url)
    _check(text, key, name, url, path)  # the file it would become parses, and holds the entry
    path.write_text(text, encoding="utf-8")
    sources.reload()


def _clean(key: str, name: str, url: str, path: Path) -> tuple[str, str, str]:
    key, name, url = key.strip(), name.strip(), url.strip()
    if not key:
        raise SourcesEditError("the source's name (its key) is empty")
    if not KEY_PATTERN.fullmatch(key):
        raise SourcesEditError(
            f"{key!r} is not a source key: use capitals, digits and underscores, like MY_LAB_MANUAL"
        )
    if not name:
        raise SourcesEditError("say what the source is: its name is empty")
    if "\n" in name or "\r" in name:
        raise SourcesEditError("a source's name is one line")
    if not url:
        raise SourcesEditError("the url is empty")
    if not URL_PATTERN.fullmatch(url) or any(c.isspace() for c in url):
        raise SourcesEditError(f"{url!r} is not a link: it must start with http:// or https://")
    if key in sources.load_sources(path):
        raise SourcesEditError(f"{key} is already a source in {path.name}")
    return key, name, url


def _entry(key: str, name: str, url: str) -> str:
    """The three lines, the values quoted the way YAML needs."""
    return f"{key}:\n  name: {_quoted(name)}\n  url: {_quoted(url)}\n"


def _quoted(value: str) -> str:
    return yaml.safe_dump(value, default_style='"', allow_unicode=True, width=10_000).strip()


def _check(text: str, key: str, name: str, url: str, path: Path) -> None:
    try:
        loaded = yaml.safe_load(text)
    except yaml.YAMLError as error:
        raise SourcesEditError(f"adding {key} would make {path} unreadable: {error}") from error
    entry = loaded.get(key) if isinstance(loaded, dict) else None
    if entry != {"name": name, "url": url}:
        raise SourcesEditError(f"could not add {key} to {path}")
