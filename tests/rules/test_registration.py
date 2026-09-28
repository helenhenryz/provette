"""A rule without a source does not load; and every source a rule cites is on the sources page."""

from __future__ import annotations

from pathlib import Path

import pytest

from provette.rules import RULES, Rule, RuleWithoutSource

SOURCES_PAGE = Path(__file__).parent.parent.parent / "docs" / "rule-sources.md"


def test_a_rule_without_a_source_does_not_load() -> None:
    with pytest.raises(RuleWithoutSource, match="NO-BASIS"):
        Rule(
            rule_id="NO-BASIS",
            family=1,
            tier="structural",
            title="A hunch",
            description="Somebody felt this was bad.",
            sources=(),
            check=lambda trace, run: [],
        )


def test_every_cited_source_is_on_the_sources_page() -> None:
    page = SOURCES_PAGE.read_text(encoding="utf-8")
    for rule in RULES:
        assert rule.sources
        for source in rule.sources:
            assert source.url in page, f"{rule.rule_id} cites {source.url}, not in rule-sources.md"


def test_rule_ids_are_unique() -> None:
    ids = [rule.rule_id for rule in RULES]
    assert len(ids) == len(set(ids))
