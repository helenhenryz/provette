"""The methods page's numbers, computed from eval/'s result files, pinned to the READMEs' prose.

No number is typed here: each is computed from the result files, as the page computes it, and the
README must say the same. If a file and its README drift apart, this fails before the page can
contradict eval/.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.settings import REPO


def readme(name: str) -> str:
    """The README's Results section: the numbers live there, the method above it."""
    text = (REPO / "eval" / name / "README.md").read_text(encoding="utf-8")
    return text[text.index("## Results") :]


def row(text: str, start: str) -> str:
    """The table row of a README that starts with `start`."""
    return next(line for line in text.splitlines() if line.startswith(start))


@pytest.fixture(scope="module")
def body(tmp_path_factory: pytest.TempPathFactory) -> dict:  # type: ignore[type-arg]
    from api.main import create_app
    from tests.api.conftest import make_settings

    with TestClient(create_app(make_settings(tmp_path_factory.mktemp("data")))) as client:
        data: dict = client.get("/api/evidence").json()  # type: ignore[type-arg]
        return data


def test_the_checks_match_their_readme(body: dict) -> None:  # type: ignore[type-arg]
    e, text = body["checks"], readme("checks")
    c = e["correct"]
    assert f"**{c['verified']} of {c['protocols']} verify**, {c['wells']} wells" in text
    assert f"**{e['control']['verified']} of {e['control']['protocols']} verify**" in text
    assert f"**{e['hand']['agree']} of {e['hand']['protocols']} agree**" in text
    m = e["mutants"]
    changes = m["change_the_deck"] - (m["missed"] - m["missed_layout_swaps"])
    assert f"{changes} bugs that change what a well holds" in text
    assert f"{m['caught']} are caught" in text
    assert f"({m['sample_lost_caught']} of {m['sample_lost']})" in text
    none_to_catch = sum(op["nothing"] - op["missed"] for op in m["by_operator"])
    assert (
        f"| **{m['generated']}** | **{m['pass_simulator']}** | **{m['caught']}** | "
        f"**{m['pass_simulator'] - m['caught']}** | **{none_to_catch}** | "
        f"**{m['missed_layout_swaps']}** |"
    ) in text
    for op in m["by_operator"]:
        flagged = op["pass_simulator"] - op["nothing"]
        assert (
            f"| {op['words']} | {op['generated']} | {op['pass_simulator']} | {flagged} | "
            f"{op['nothing']} | {op['nothing'] - op['missed']} | {op['missed']} |"
        ) in text
    assert "eval/checks/results/mutants.json" in e["sources"]


def test_the_agent_runs_match_their_readme(body: dict) -> None:  # type: ignore[type-arg]
    text = readme("agent")
    sets = {s["set"]: s for s in body["agent"]["sets"]}
    assert set(sets) == {"super", "nano-best3", "super-hard", "nano-hard-best3"}
    for name, s in sets.items():
        line = row(text, f"| `results/{name}` |")
        assert f"**{s['verified_end']} of {s['requests']}**" in line, name
        assert f"{s['clean_first']} of {s['requests']}" in line, name
        assert f"${s['cost_usd']:.2f}" in line, name
        assert f"${s['per_verified_usd']:.3f}" in line, name
    assert sets["super-hard"]["request_set"] == "the harder set"
    assert sets["super"]["request_set"] == "the original set"


def test_the_baseline_matches_its_readme(body: dict) -> None:  # type: ignore[type-arg]
    b, text = body["baseline"], readme("baseline")
    assert (
        row(text, "| **verified and clean** |")
        == f"| **verified and clean** | **{b['verified_end']}** |"
    )
    assert (
        row(text, "| passed the simulator |")
        == f"| passed the simulator | {b['pass_simulator_first']} |"
    )
    assert f"${b['cost_usd']:.2f}" in text
    assert (
        row(text, "| of those, broke a rule it had just been told")
        == "| of those, broke a rule it had just been told (an error or a warning) | "
        f"{b['broke_rule']} |"
    )
    assert (
        row(text, "| of those, a plate map mismatch |")
        == f"| of those, a plate map mismatch | {b['map_mismatch']} |"
    )
    assert b["model_label"] == "Nemotron 3 Super 120B"
    assert b["source"] == "eval/baseline/results/super-rules-in-prompt/*/*/done.json"


def test_the_planner_matches_its_readme(body: dict) -> None:  # type: ignore[type-arg]
    p, text = body["planner"], readme("planner")
    line = row(text, "| `results/super` |")
    assert f"| {p['valid_map']} of {p['requests']} | {p['agree']} |" in line
    assert f"**{p['verify']} of {p['requests']}**" in line
    assert f"${p['cost_usd']:.2f}" in line


def test_the_ledger_matches_its_readme(body: dict) -> None:  # type: ignore[type-arg]
    g, text = body["ledger"], readme("ledger")
    assert f"Of **{g['library']}** library protocols" in text
    assert f"accept **{g['accepted']}**" in text
    assert f"On **{g['agree']} of {g['compared']}**" in text
    assert f"over {g['events']:,} recorded events" in text
    assert f"**{g['independent_agree']} of {g['independent']}** of them" in text
    assert f"**{g['exported']} of {g['accepted']}**" in text
    assert row(text, "| in the library |") == f"| in the library | {g['library']} |"
    assert (
        row(text, "| Opentrons' analysis agrees with the ledger |")
        == f"| Opentrons' analysis agrees with the ledger | {g['agree']} of {g['compared']} |"
    )
    assert (
        row(text, "| of those, a fully independent reading")
        == "| of those, a fully independent reading (API 2.14 and later) | "
        f"{g['independent_agree']} of {g['independent']} |"
    )
    assert g["source"] == "eval/ledger/counts.json"


def test_only_the_gallery_sets_are_computed(tmp_path: Path) -> None:
    """The methods page computes the sets the gallery shows, and nothing else under results/."""
    from api.main import create_app
    from tests.api.conftest import make_settings

    with TestClient(create_app(make_settings(tmp_path, sets=("super",)))) as client:
        names = [s["set"] for s in client.get("/api/evidence").json()["agent"]["sets"]]
    assert names == ["super"]
