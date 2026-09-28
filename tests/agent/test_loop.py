"""The loop with a scripted model: bookkeeping, the code-block fallback, bad calls, budgets.

No network and no simulator: the model is a list of assistant messages played in order, and the
runner says what it is told.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from provette.agent import loop as loop_module
from provette.agent.loop import fenced_block, run_episode, system_prompt

ROOT = Path(__file__).parents[2]
PLATEMAP = ROOT / "eval" / "platemaps" / "pcr-01.json"
REQUEST = {"id": "pcr-01", "request": "Set up PCR reactions for 8 DNA samples."}
FILE = "from opentrons import protocol_api\n\ndef run(protocol):\n    pass\n"

CLEAN = {"simulator": "passed", "simulator_error": "", "verify_exit": 0, "verify_text": "ok",
         "verify": {}, "check_exit": 0, "check_text": "clean", "findings": [],
         "seconds": 0.1}  # fmt: skip
DIRTY = {**CLEAN, "verify_exit": 1, "verify_text": "MISMATCH: well A1 expected 5 ul sample 1"}


class ScriptedRunner:
    """Returns the next result in its script, then the last one for ever."""

    name = "scripted"

    def __init__(self, *results: dict[str, Any]) -> None:
        self.results = list(results)
        self.calls = 0

    def run_checks(self, protocol_text: str, platemap_json: dict[str, Any]) -> dict[str, Any]:
        self.calls += 1
        return dict(self.results.pop(0) if len(self.results) > 1 else self.results[0])

    def close(self) -> None:
        pass


def call(name: str, arguments: Any = None, call_id: str | None = None) -> dict[str, Any]:
    return {
        "id": call_id or f"call_{name}",
        "type": "function",
        "function": {
            "name": name,
            "arguments": arguments if isinstance(arguments, str) else json.dumps(arguments or {}),
        },
    }


def turn(content: str = "", *calls: dict[str, Any], tokens: int = 100) -> dict[str, Any]:
    message: dict[str, Any] = {"role": "assistant", "content": content, "reasoning": "hmm"}
    if calls:
        message["tool_calls"] = list(calls)
    return {
        "message": message,
        "usage": {"prompt_tokens": 1000, "completion_tokens": tokens},
        "finish_reason": "tool_calls" if calls else "stop",
    }


class ScriptedModel:
    def __init__(self, *turns: dict[str, Any]) -> None:
        self.turns = list(turns)
        self.seen: list[list[dict[str, Any]]] = []

    def __call__(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> dict[str, Any]:
        self.seen.append([dict(m) for m in messages])
        assert tools and tools[0]["function"]["name"] == "platemap"
        if not self.turns:
            raise AssertionError("the script ran out: the loop should have stopped")
        return self.turns.pop(0)


def episode(model: ScriptedModel, runner: Any, out: Path, **kw: Any) -> dict[str, Any]:
    return run_episode(REQUEST, PLATEMAP, runner, "fake-model", "http://x", "", out, "plain",
                       chat=model, **kw)  # fmt: skip


# ------------------------------------------------------------------------------------------------


def test_system_prompt_carries_the_reference_the_requirements_and_the_tools() -> None:
    platemap = json.loads(PLATEMAP.read_text())
    plain = system_prompt(platemap, "plain")
    assert plain.startswith("You are a helpful assistant.\n\nReference")
    assert '"master mix", "sample 1"' in plain and "Output only" not in plain
    assert (
        "write_protocol tool" in plain and "read the `checks` that write_protocol returns" in plain
    )
    assert not plain.rstrip().endswith("Request:")
    tips = system_prompt(platemap, "short-on-tips")
    assert "as few tips as possible" in tips and "as few tips" not in plain


def test_fenced_block_takes_the_longest_block_and_drops_thinking() -> None:
    text = (
        "<think>```python\nno\n```</think>Here:\n```python\nx = 1\n```\nand\n```\ny = 2\nz = 3\n```"
    )
    assert fenced_block(text) == "y = 2\nz = 3\n"
    assert fenced_block("no code here") is None


def test_happy_path_write_check_submit(tmp_path: Path) -> None:
    model = ScriptedModel(
        turn("", call("platemap")),
        turn("", call("write_protocol", {"text": FILE})),  # write_protocol checks the draft
        turn("done", call("submit")),
    )
    runner = ScriptedRunner(CLEAN)
    s = episode(model, runner, tmp_path)
    assert s["stop_reason"] == "submitted" and s["submitted"] and s["submitted_clean"]
    assert s["tool_calls"] == 3 and s["drafts"] == 1 and s["checks"] == 1 and s["turns"] == 3
    assert s["one_shot"] == {"simulator": "passed", "verify_exit": 0, "check_exit": 0,
                             "findings": [], "draft": 0}  # fmt: skip
    assert s["loop"] == {**s["one_shot"], "rounds": 0}
    assert s["tokens_in"] == 3000 and s["tokens_out"] == 300
    assert s["final_draft_checked_by_harness"] is False and runner.calls == 1
    assert {"id", "condition", "model", "one_shot", "loop"} <= set(s)
    assert json.loads((tmp_path / "done.json").read_text()) == s
    assert (tmp_path / "00-draft.py").read_text() == FILE
    assert json.loads((tmp_path / "00-checks.json").read_text())["draft"] == 0
    rows = [json.loads(line) for line in (tmp_path / "transcript.jsonl").read_text().splitlines()]
    assert [r["turn"] for r in rows] == [0, 1, 2]
    assert rows[1]["assistant"]["reasoning"] == "hmm"
    assert [t["name"] for t in rows[1]["assistant"]["tool_calls"]] == ["write_protocol"]
    assert rows[1]["tool_results"][0]["result"]["checks"]["ready_to_submit"] is True
    log = [json.loads(line) for line in (tmp_path / "log.jsonl").read_text().splitlines()]
    assert log[1]["usage"]["completion_tokens"] == 100 and log[1]["tools"] == ["write_protocol"]
    # what the model saw on its last turn: the tool results went back under their call ids
    last = model.seen[-1]
    assert [m["role"] for m in last] == [
        "system",
        "user",
        "assistant",
        "tool",
        "assistant",
        "tool",
    ]
    assert last[3]["tool_call_id"] == "call_platemap" and last[2]["reasoning"] == "hmm"
    assert json.loads(last[5]["content"])["checks"]["verdict"].startswith("Simulator passed")


def test_repair_round_one_shot_is_the_first_check_loop_the_last(tmp_path: Path) -> None:
    model = ScriptedModel(
        turn("", call("write_protocol", {"text": FILE})),
        turn("", call("write_protocol", {"text": FILE + "# fixed\n"})),
        turn("", call("submit")),
    )
    s = episode(model, ScriptedRunner(DIRTY, CLEAN), tmp_path)
    assert s["one_shot"]["verify_exit"] == 1 and s["one_shot"]["draft"] == 0
    assert s["loop"]["verify_exit"] == 0 and s["loop"]["draft"] == 1 and s["loop"]["rounds"] == 1
    assert s["drafts"] == 2 and s["submitted_clean"]


def test_code_block_instead_of_the_tool_is_stored_and_the_model_is_told(tmp_path: Path) -> None:
    model = ScriptedModel(
        turn("Here is the protocol:\n```python\n" + FILE + "```"),
        turn("", call("submit")),
    )
    s = episode(model, ScriptedRunner(CLEAN), tmp_path)
    assert s["drafts"] == 1 and s["tool_calls"] == 2 and s["submitted_clean"]
    assert (tmp_path / "00-draft.py").read_text() == FILE
    nudge = model.seen[1][-1]
    assert (
        nudge["role"] == "user" and "instead of calling the write_protocol tool" in nudge["content"]
    )
    rows = [json.loads(line) for line in (tmp_path / "transcript.jsonl").read_text().splitlines()]
    assert rows[0]["tool_results"][0]["name"] == "write_protocol (from a code block)"


def test_malformed_arguments_and_invented_tools_come_back_as_errors(tmp_path: Path) -> None:
    model = ScriptedModel(
        turn(
            "",
            call("labware", "{kind: plate", "c1"),
            call("teleport", {}, "c2"),
            call("write_protocol", {"txt": FILE}, "c3"),
        ),  # fmt: skip
        turn("", call("submit")),
    )
    s = episode(model, ScriptedRunner(CLEAN), tmp_path)
    assert s["tool_calls"] == 4 and s["drafts"] == 0 and s["submitted"] and not s["submitted_clean"]
    assert (
        s["one_shot"]["simulator"] == "never checked" and s["loop"]["simulator"] == "never checked"
    )
    replies = [json.loads(m["content"]) for m in model.seen[1] if m["role"] == "tool"]
    assert "not valid JSON" in replies[0]["error"]
    assert "no tool named 'teleport'" in replies[1]["error"]
    assert "wrong arguments for write_protocol" in replies[2]["error"]


def test_a_dirty_draft_submitted_anyway_is_recorded_as_not_clean(tmp_path: Path) -> None:
    model = ScriptedModel(
        turn("", call("write_protocol", {"text": FILE})),
        turn("", call("write_protocol", {"text": FILE + "# v2\n"})),
        turn("", call("submit")),
    )
    runner = ScriptedRunner(CLEAN, DIRTY)
    s = episode(model, runner, tmp_path)
    assert runner.calls == 2 and s["final_draft_checked_by_harness"] is False
    assert s["one_shot"]["verify_exit"] == 0 and s["loop"]["verify_exit"] == 1
    assert s["submitted"] and not s["submitted_clean"]


def test_an_unchecked_draft_is_judged_by_the_harness(tmp_path: Path) -> None:
    """write_protocol checks every draft it can parse; one that does not parse is stored
    unchecked, and a submit then gets the harness's own check."""
    model = ScriptedModel(
        turn("", call("write_protocol", {"text": FILE})),
        turn("", call("write_protocol", {"text": "def run(protocol:\n"})),
        turn("", call("submit")),
    )
    runner = ScriptedRunner(CLEAN, DIRTY)
    s = episode(model, runner, tmp_path)
    assert runner.calls == 2 and s["final_draft_checked_by_harness"] is True
    assert s["submitted"] and not s["submitted_clean"]
    assert json.loads((tmp_path / "01-checks.json").read_text())["by_harness"] is True


def test_call_budget_stops_the_episode(tmp_path: Path) -> None:
    model = ScriptedModel(*[turn("", call("labware", {"kind": "plate"})) for _ in range(10)])
    s = episode(model, ScriptedRunner(CLEAN), tmp_path, max_tool_calls=3)
    assert s["stop_reason"] == "call budget" and s["tool_calls"] == 3 and not s["submitted"]


def test_token_budget_stops_the_episode(tmp_path: Path) -> None:
    model = ScriptedModel(
        *[turn("", call("labware", {"kind": "tips"}), tokens=5000) for _ in range(9)]
    )
    s = episode(model, ScriptedRunner(CLEAN), tmp_path, max_completion_tokens=12000)
    assert s["stop_reason"] == "token budget" and s["turns"] == 3 and s["tokens_out"] == 15000


def test_a_model_that_only_talks_is_nudged_then_stopped(tmp_path: Path) -> None:
    model = ScriptedModel(turn("I would write..."), turn("Sure."), turn("OK."), turn("more"))
    s = episode(model, ScriptedRunner(CLEAN), tmp_path)
    assert s["stop_reason"] == "model stopped using tools" and s["turns"] == 3
    assert model.seen[1][-1]["content"].startswith("You called no tool.")


def test_three_api_errors_stop_the_episode_with_backoff(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    slept: list[float] = []
    monkeypatch.setattr(loop_module.time, "sleep", slept.append)

    class Broken:
        def __call__(self, messages: Any, tools: Any) -> dict[str, Any]:
            raise OSError("connection refused")

    s = run_episode(REQUEST, PLATEMAP, ScriptedRunner(CLEAN), "m", "http://x", "", tmp_path,
                    "plain", chat=Broken())  # fmt: skip
    assert s["stop_reason"] == "api errors" and s["turns"] == 0 and slept == [5.0, 15.0]
    rows = [json.loads(line) for line in (tmp_path / "transcript.jsonl").read_text().splitlines()]
    assert len(rows) == 3 and rows[0]["api_error"] == "OSError: connection refused"


def test_one_api_error_is_retried(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(loop_module.time, "sleep", lambda s: None)
    good = ScriptedModel(turn("", call("submit")))
    failed = {"n": 0}

    def flaky(messages: Any, tools: Any) -> dict[str, Any]:
        if failed["n"] == 0:
            failed["n"] += 1
            raise ValueError("bad json")
        return good(messages, tools)

    s = run_episode(REQUEST, PLATEMAP, ScriptedRunner(CLEAN), "m", "http://x", "", tmp_path,
                    "plain", chat=flaky)  # fmt: skip
    assert s["stop_reason"] == "submitted" and s["turns"] == 1


def test_older_check_reports_are_collapsed_in_what_is_sent() -> None:
    from provette.agent.loop import for_sending

    inner = {"simulator": "passed", "verify_exit": 1, "check_exit": 0, "ready_to_submit": False}
    checks = {"checks": {**inner, "verify_report": "x" * 5000}, "draft": 0}
    messages = [
        {"role": "system", "content": "s"},
        {"role": "user", "content": "u"},
        {"role": "assistant", "content": "", "tool_calls": []},
        {
            "role": "tool",
            "tool_call_id": "a",
            "content": json.dumps(checks),
            "_tool": "write_protocol",
        },
        {
            "role": "tool",
            "tool_call_id": "b",
            "content": json.dumps({"kind": "plate"}),
            "_tool": "labware",
        },
        {
            "role": "tool",
            "tool_call_id": "c",
            "content": json.dumps({**checks, "draft": 1}),
            "_tool": "write_protocol",
        },
    ]
    sent = for_sending(messages)
    assert all("_tool" not in m for m in sent)
    assert "collapsed" in sent[3]["content"] and "x" * 100 not in sent[3]["content"]
    assert sent[4]["content"] == json.dumps({"kind": "plate"})
    assert "x" * 100 in sent[5]["content"]  # the latest report stays whole
    assert messages[3]["content"] != sent[3]["content"]  # the transcript's copy is untouched


def test_collapse_reasoning_keeps_only_the_latest_turns_thought() -> None:
    from provette.agent.loop import for_sending

    messages = [
        {"role": "system", "content": "s"},
        {"role": "assistant", "content": "", "reasoning": "first thought", "tool_calls": []},
        {"role": "tool", "tool_call_id": "a", "content": "{}", "_tool": "labware"},
        {"role": "assistant", "content": "", "reasoning": "second thought", "tool_calls": []},
    ]
    kept = [m.get("reasoning") for m in for_sending(messages)]
    assert kept == [None, "first thought", None, "second thought"]
    sent = for_sending(messages, collapse_reasoning=True)
    assert [m.get("reasoning") for m in sent] == [None, None, None, "second thought"]
    assert messages[1]["reasoning"] == "first thought"  # the transcript's copy is untouched


def test_a_turn_cut_in_its_reasoning_is_continued_on_the_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A reply with finish_reason 'length', reasoning and no answer is finished by a second call
    on /v1/completions (provette.agent.budget); the loop consumes the tool call it yields."""
    from provette.agent import budget

    def fake_post(client: Any, body: dict[str, Any], timeout_s: float) -> dict[str, Any]:
        assert "<think>" in body["prompt"] and body["prompt"].rstrip().endswith("</think>")
        return {
            "choices": [
                {
                    "text": "<tool_call>\n<function=platemap>\n</function>\n</tool_call>",
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 500, "completion_tokens": 20},
        }

    monkeypatch.setattr(budget, "post_completion", fake_post)
    cut = {
        "message": {"role": "assistant", "content": "", "reasoning": "We need the plate map"},
        "usage": {"prompt_tokens": 1000, "completion_tokens": 24000},
        "finish_reason": "length",
    }
    model = ScriptedModel(cut, turn("", call("write_protocol", {"text": FILE})),
                          turn("", call("submit")))  # fmt: skip
    s = episode(model, ScriptedRunner(CLEAN), tmp_path)
    assert s["submitted_clean"] and s["tokens_out"] == 24000 + 20 + 100 + 100
    rows = [json.loads(line) for line in (tmp_path / "transcript.jsonl").read_text().splitlines()]
    first = rows[0]["assistant"]
    assert [t["name"] for t in first["tool_calls"]] == ["platemap"]
    assert first["reasoning"].endswith(".") and first.get("budget_continued") is True
