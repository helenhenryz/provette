"""The baseline harness's prompt: `--rules-in-prompt` tells the model the twelve rules, in words."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from provette.rules import RULES

ROOT = Path(__file__).parents[2]
_spec = importlib.util.spec_from_file_location(
    "baseline_run", ROOT / "eval" / "baseline" / "run.py"
)
assert _spec and _spec.loader
run = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(run)


def test_rules_section_lists_the_twelve_rules_as_they_stand() -> None:
    section = run.rules_section()
    lines = [line for line in section.splitlines() if line.startswith("- ")]
    adopted = [rule for rule in RULES if rule.status == "adopted"]
    assert len(lines) == len(adopted) + 1, "the adopted rules and the verify-side labware check"
    assert len(adopted) == 11
    for rule in adopted:
        assert f"- {rule.title}: {rule.description}" in lines
    assert not any("(proposed)" in line or "NO-SAMPLE-INTO-REAGENT-WELL" in line for line in lines)
    assert any("LABWARE-FOR-TECHNIQUE" in line for line in lines)
    assert section.startswith("Rules this protocol must satisfy")
    assert section.endswith("Nothing will check the draft for you; satisfy every rule yourself.")


def test_system_prompt_gains_the_section_only_when_asked() -> None:
    plain = run.system_prompt(False)
    assert plain == run.SYSTEM and "Rules this protocol" not in plain
    with_rules = run.system_prompt(True)
    assert with_rules.startswith(run.SYSTEM)
    assert run.rules_section() in with_rules
