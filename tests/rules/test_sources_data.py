"""The sources as data: `sources.yaml` is what `sources.py` exposes, the Python rules and the
declared rules cite the same registry, a missing key is refused at import by name, and
`sources_edit.add_source` appends an entry without losing a comment.

Every test that writes goes through a copy of the file under `tmp_path` and a monkeypatched
`sources.SOURCES_FILE` (what `PROVETTE_SOURCES_FILE` sets for a process); the shipped file is
never written, and the registry is reloaded from it after.
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
import yaml

from provette.rules import RULES, declared, sources, sources_edit
from provette.rules.finding import Source
from provette.rules.sources import SourcesFileError, load_sources
from provette.rules.sources_edit import SourcesEditError, add_source, all_sources

NEW = (
    "MY_LAB_MANUAL",
    "My lab's manual, page 12: keep the enzyme on ice",
    "https://example.org/m.pdf",
)


@pytest.fixture
def scratch_sources(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """A copy of sources.yaml the tests may write; the shipped registry comes back afterwards."""
    copy = tmp_path / "sources.yaml"
    copy.write_text(sources.SOURCES_FILE.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(sources, "SOURCES_FILE", copy)
    sources.reload()
    yield copy
    monkeypatch.undo()
    sources.reload()


# -- the file --------------------------------------------------------------------------------


def test_the_file_is_the_registry_and_every_key_is_a_module_attribute() -> None:
    in_file = load_sources()
    assert in_file and in_file == sources.SOURCES
    for key, source in in_file.items():
        assert getattr(sources, key) == source and isinstance(source, Source)
    assert sources.THERMO_T4_LIGASE.url.startswith("https://")
    assert all_sources() == {k: {"name": s.name, "url": s.url} for k, s in in_file.items()}
    assert list(all_sources()) == list(in_file)  # file order


def test_the_file_opens_with_a_note_to_its_owners() -> None:
    head = sources.SOURCES_FILE.read_text(encoding="utf-8").splitlines()[:4]
    assert all(line.startswith("#") for line in head)
    assert "No programming is needed" in " ".join(head)


def test_the_declared_rules_check_against_the_same_registry() -> None:
    assert declared.SOURCES is sources.SOURCES
    assert "THERMO_RESTRICTION_ENZYMES" in declared.SOURCES


def test_every_rule_cites_a_source_the_file_holds() -> None:
    known = set(sources.SOURCES.values())
    for rule in RULES:
        assert rule.sources and set(rule.sources) <= known, rule.rule_id


def test_a_key_the_file_does_not_hold_is_refused_by_name() -> None:
    missing, lower = "NOT_IN_THE_FILE", "not_a_key"
    with pytest.raises(SourcesFileError, match=missing):
        getattr(sources, missing)
    with pytest.raises(AttributeError):
        getattr(sources, lower)


def test_a_rule_citing_a_missing_key_stops_the_import_with_the_key_name(tmp_path: Path) -> None:
    """The real thing: a process whose sources file lacks a key a Python rule cites."""
    without = {k: v for k, v in yaml.safe_load(sources.SOURCES_FILE.read_text()).items()}
    del without["THERMO_T4_LIGASE"]
    short = tmp_path / "sources.yaml"
    short.write_text(yaml.safe_dump(without), encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env["PROVETTE_SOURCES_FILE"] = str(short)
    done = subprocess.run(
        [sys.executable, "-c", "import provette.rules"], env=env, capture_output=True, text=True
    )
    assert done.returncode != 0
    assert "SourcesFileError" in done.stderr and "THERMO_T4_LIGASE" in done.stderr


@pytest.mark.parametrize(
    ("text", "why"),
    [
        ("- just a list\n", "one entry per source"),
        ("lower_case: {name: x, url: https://x}\n", "not a source name"),
        ("A_KEY: https://x\n", "exactly `name` and `url`"),
        ("A_KEY: {name: x}\n", "exactly `name` and `url`"),
        ("A_KEY: {name: x, url: https://x, extra: 1}\n", "exactly `name` and `url`"),
        ("A_KEY: {name: '', url: https://x}\n", "one line of text"),
        ("A_KEY: {name: x, url: ftp://x}\n", "http:// or https://"),
        ("A_KEY: {name: x, url: ''}\n", "http:// or https://"),
    ],
)
def test_a_file_of_the_wrong_shape_is_refused(tmp_path: Path, text: str, why: str) -> None:
    bad = tmp_path / "sources.yaml"
    bad.write_text(text, encoding="utf-8")
    with pytest.raises(SourcesFileError, match=why):
        load_sources(bad)


def test_reload_from_another_file_changes_the_registry(scratch_sources: Path) -> None:
    scratch_sources.write_text(
        "ONLY_ONE:\n  name: the one source\n  url: https://example.org/one\n", encoding="utf-8"
    )
    sources.reload()
    assert list(sources.SOURCES) == ["ONLY_ONE"]
    assert Source("the one source", "https://example.org/one") == sources.ONLY_ONE
    assert declared.SOURCES == sources.SOURCES


# -- adding a source -------------------------------------------------------------------------


def test_add_source_appends_at_the_end_keeps_comments_and_reloads(scratch_sources: Path) -> None:
    before = scratch_sources.read_text(encoding="utf-8")
    key, name, url = NEW
    add_source(f" {key} ", f" {name} ", f" {url} ")
    after = scratch_sources.read_text(encoding="utf-8")
    # every line that was there is still there, in order; three lines were added at the end
    assert after.startswith(before)
    added = after[len(before) :].splitlines()
    assert added == [f"{key}:", f'  name: "{name}"', f'  url: "{url}"']
    assert after.count("#") == before.count("#")
    # the registry knows it: as an attribute, as data, and for a declared rule
    assert getattr(sources, key) == Source(name, url)
    assert list(all_sources())[-1] == key and all_sources()[key] == {"name": name, "url": url}
    assert key in declared.SOURCES
    assert load_sources(scratch_sources)[key] == Source(name, url)


def test_add_source_quotes_what_yaml_would_misread(scratch_sources: Path) -> None:
    add_source("ODD_ONE", 'yes: a "quoted" name, with #hash and a colon', "https://x.org/a?b=1&c=2")
    assert load_sources(scratch_sources)["ODD_ONE"] == Source(
        'yes: a "quoted" name, with #hash and a colon', "https://x.org/a?b=1&c=2"
    )


def test_add_source_to_a_file_without_a_final_newline(scratch_sources: Path) -> None:
    scratch_sources.write_text(scratch_sources.read_text(encoding="utf-8").rstrip("\n"))
    add_source(*NEW)
    assert load_sources(scratch_sources)[NEW[0]] == Source(NEW[1], NEW[2])


@pytest.mark.parametrize(
    ("key", "name", "url", "why"),
    [
        ("", "a name", "https://x.org", "key\\) is empty"),
        ("my_lab", "a name", "https://x.org", "not a source key"),
        ("MY LAB", "a name", "https://x.org", "not a source key"),
        ("1ST_LAB", "a name", "https://x.org", "not a source key"),
        ("MY_LAB_", "a name", "https://x.org", "not a source key"),
        ("MY_LAB", "", "https://x.org", "name is empty"),
        ("MY_LAB", "two\nlines", "https://x.org", "one line"),
        ("MY_LAB", "a name", "", "url is empty"),
        ("MY_LAB", "a name", "ftp://x.org", "not a link"),
        ("MY_LAB", "a name", "www.x.org", "not a link"),
        ("MY_LAB", "a name", "https://x.org/a b", "not a link"),
        ("THERMO_T4_LIGASE", "again", "https://x.org", "already a source"),
    ],
)
def test_add_source_refuses(scratch_sources: Path, key: str, name: str, url: str, why: str) -> None:
    before = scratch_sources.read_text(encoding="utf-8")
    registry = dict(sources.SOURCES)
    with pytest.raises(SourcesEditError, match=why):
        add_source(key, name, url)
    assert scratch_sources.read_text(encoding="utf-8") == before
    assert registry == sources.SOURCES


def test_the_shipped_file_is_untouched_by_these_tests() -> None:
    assert sources_edit.all_sources() == {
        k: {"name": s.name, "url": s.url} for k, s in load_sources(sources.SOURCES_FILE).items()
    }
    assert NEW[0] not in sources.SOURCES and "ODD_ONE" not in sources.SOURCES
