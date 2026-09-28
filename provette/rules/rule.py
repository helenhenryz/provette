"""What a rule is: a plain function over the trace and the state, plus what it rests on."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from provette.model import Trace
from provette.rules.finding import Finding, Source, Tier
from provette.state import Run

Check = Callable[[Trace, Run], list[Finding]]
Status = Literal["proposed", "adopted"]


class RuleWithoutSource(ValueError):
    """A rule was defined with nothing to rest on. It does not load (docs/rule-sources.md)."""


@dataclass(frozen=True)
class Rule:
    """A rule and its metadata. Making one with no `sources` raises `RuleWithoutSource`.

    `status` and `proposed_by` are the rulebook's status line as data. A rule written in Python
    is the team's and adopted; a declared rule (`declared/*.yaml`) says both in its file, and
    while it is `proposed` its findings are notes titled "(proposed) ...", so it can never
    block a submission (`provette.rules.declared`).
    """

    rule_id: str
    family: int  # the row of the family table in docs/rule-sources.md
    tier: Tier
    title: str
    description: str  # the rule in plain words, for the README table and for `--json`
    sources: tuple[Source, ...]
    check: Check
    status: Status = "adopted"
    proposed_by: str = "the team"

    def __post_init__(self) -> None:
        if not self.sources:
            raise RuleWithoutSource(
                f"{self.rule_id}: a rule without a source does not load. "
                "Find what it rests on, add it to docs/rule-sources.md, and cite it here."
            )
