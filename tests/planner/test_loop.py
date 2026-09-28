"""The planning loop with a scripted model: the happy path, a refused proposal, the budgets,
a model that only talks, API errors. No network."""

from __future__ import annotations

import json
from typing import Any

import pytest

from provette.planner import loop as loop_module
from provette.planner.loop import PlanError, plan, plan_platemap, repair_message, repeated_refusal
from provette.planner.prompt import system_prompt
from tests.planner.test_tools import REQUEST, pcr_map


def call(name: str, arguments: Any = None, call_id: str | None = None) -> dict[str, Any]:
    return {
        "id": call_id or f"call_{name}",
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(arguments or {})},
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
        assert [t["function"]["name"] for t in tools][-1] == "propose_platemap"
        if not self.turns:
            raise AssertionError("the script ran out: the loop should have stopped")
        return self.turns.pop(0)


def test_system_prompt_is_the_assistant_line_then_the_sheet() -> None:
    text = system_prompt()
    assert text.startswith("You are a helpful assistant.\n\n")
    assert "propose_platemap" in text and '"order_hint": "index"' in text
    assert "lysate" in text and "Cherrypick" not in text  # the example is not a request of ours


def test_happy_path_calculator_then_proposal(tmp_path: Any) -> None:
    model = ScriptedModel(
        turn("", call("master_mix", {"components": {"mm": 20}, "reactions": 8})),
        turn("here", call("propose_platemap", {"platemap": pcr_map()})),
    )
    result = plan(REQUEST, "fake", "http://x", "", request_id="pcr-01", chat=model)
    assert result.stop_reason == "proposed" and result.platemap is not None
    assert result.platemap.id == "pcr-01" and result.error is None
    assert result.tool_calls == 2 and result.turns == 2
    assert result.tokens_in == 2000 and result.tokens_out == 200 and result.rejections == []
    called = [t["tool_calls"][0]["name"] for t in result.transcript]
    assert called == ["master_mix", "propose_platemap"]
    assert result.transcript[0]["reasoning"] == "hmm"
    last = model.seen[-1]
    assert [m["role"] for m in last] == ["system", "user", "assistant", "tool"]
    assert last[3]["tool_call_id"] == "call_master_mix" and "reasoning" not in last[2]
    assert last[1]["content"] == REQUEST


def test_a_refused_proposal_goes_back_and_the_next_one_is_taken() -> None:
    model = ScriptedModel(
        turn("", call("propose_platemap", {"platemap": pcr_map(volume=22)})),
        turn("", call("propose_platemap", {"platemap": pcr_map()})),
    )
    result = plan(REQUEST, chat=model)
    assert result.platemap is not None and result.tool_calls == 2
    assert len(result.rejections) == 1 and "22 ul of master_mix" in result.rejections[0]
    reply = json.loads(model.seen[1][-1]["content"])
    assert reply["accepted"] is False and reply["next"].startswith("Fix the plate map")


def test_the_same_refusal_twice_brings_a_repair_message_naming_the_field_and_the_liquids() -> None:
    """A map refused for the same reason twice: the message after the second refusal quotes
    the field to change and the liquids the map declares; after the first it does not."""
    bad = pcr_map()
    bad["variants"][0]["groups"][0]["members"][0] = {"master_mix": 20, "template@A1": 5}
    model = ScriptedModel(
        turn("", call("propose_platemap", {"platemap": bad})),
        turn("", call("propose_platemap", {"platemap": bad})),
        turn("", call("propose_platemap", {"platemap": pcr_map()})),
    )
    result = plan(REQUEST, chat=model)
    assert result.platemap is not None and len(result.rejections) == 2
    assert result.rejections[0] == result.rejections[1]
    # after the first refusal: only the tool's own answer
    assert model.seen[1][-1]["role"] == "tool"
    # after the second: the tool's answer, then the repair message
    after_second = model.seen[2]
    assert after_second[-2]["role"] == "tool" and after_second[-1]["role"] == "user"
    words = after_second[-1]["content"]
    assert words.startswith("The map was refused twice for the same reason: variant '8 reactions'")
    assert (
        "Change this field and only this field: variant '8 reactions', group 'reactions'." in words
    )
    assert "The liquids your map declares are: 'master_mix', 'sample_{i}'." in words
    assert "bind 'well'" in words and words.endswith(
        "send the whole map again with propose_platemap."
    )
    assert repeated_refusal(["a"]) is False and repeated_refusal(["a", "b"]) is False
    # a refusal that names no field speaks of the whole map
    assert "only this field: the plate map." in repair_message(
        "the platemap must be a JSON object", []
    )


def test_plan_platemap_returns_the_map_or_raises_never_guesses() -> None:
    good = ScriptedModel(turn("", call("propose_platemap", {"platemap": pcr_map()})))
    assert plan_platemap(REQUEST, chat=good).liquids[0].name == "master_mix"
    bad = ScriptedModel(
        turn("", call("propose_platemap", {"platemap": pcr_map(volume=22)})),
        turn("I give up."),
        turn("Really."),
    )
    with pytest.raises(PlanError, match="model stopped using tools.*22 ul of master_mix"):
        plan_platemap(REQUEST, chat=bad)


def test_call_budget_stops_the_episode_without_a_map() -> None:
    model = ScriptedModel(*[turn("", call("labware", {"kind": "plate"})) for _ in range(20)])
    result = plan(REQUEST, chat=model, max_tool_calls=3)
    assert result.stop_reason == "call budget" and result.tool_calls == 3
    assert result.platemap is None and result.error == "no plate map: call budget."


def test_token_budget_stops_the_episode() -> None:
    model = ScriptedModel(
        *[turn("", call("labware", {"kind": "tips"}), tokens=5000) for _ in range(9)]
    )
    result = plan(REQUEST, chat=model, max_completion_tokens=12000)
    assert result.stop_reason == "token budget" and result.turns == 3
    assert result.tokens_out == 15000 and result.platemap is None


def test_a_model_that_only_talks_is_nudged_once_then_stopped() -> None:
    model = ScriptedModel(turn("I would..."), turn("Sure."), turn("more"))
    result = plan(REQUEST, chat=model)
    assert result.stop_reason == "model stopped using tools" and result.turns == 2
    assert model.seen[1][-1]["content"].startswith("You called no tool.")


def test_three_api_errors_stop_the_episode_with_backoff(monkeypatch: pytest.MonkeyPatch) -> None:
    slept: list[float] = []
    monkeypatch.setattr(loop_module.time, "sleep", slept.append)

    def broken(messages: Any, tools: Any) -> dict[str, Any]:
        raise OSError("connection refused")

    result = plan(REQUEST, chat=broken)
    assert result.stop_reason == "api errors" and result.turns == 0 and slept == [5.0, 15.0]
    assert result.transcript[0]["api_error"] == "OSError: connection refused"


def test_one_api_error_is_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(loop_module.time, "sleep", lambda s: None)
    good = ScriptedModel(turn("", call("propose_platemap", {"platemap": pcr_map()})))
    failed = {"n": 0}

    def flaky(messages: Any, tools: Any) -> dict[str, Any]:
        if failed["n"] == 0:
            failed["n"] += 1
            raise ValueError("bad json")
        return good(messages, tools)

    assert plan(REQUEST, chat=flaky).stop_reason == "proposed"


def test_the_technique_threads_through_plan_to_the_map() -> None:
    model = ScriptedModel(turn("here", call("propose_platemap", {"platemap": pcr_map()})))
    result = plan(REQUEST, chat=model, request_id="pcr-01", technique="PCR setup")
    assert result.platemap is not None and result.platemap.technique == "PCR setup"
    assert plan_platemap(REQUEST, chat=ScriptedModel(
        turn("here", call("propose_platemap", {"platemap": pcr_map()}))
    ), technique="ELISA").technique == "ELISA"  # fmt: skip


class DecliningModel:
    """Says the message is not a request, on the first turn; records the tools it was offered."""

    def __init__(self) -> None:
        self.tools: list[str] = []

    def __call__(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> dict[str, Any]:
        self.tools = [t["function"]["name"] for t in tools]
        return turn("", call("not_a_request", {"reason": "It is a question about life."}))


def test_planning_can_say_not_a_request_and_invents_no_map() -> None:
    model = DecliningModel()
    result = plan("What is the purpose of life?", chat=model, allow_decline=True)
    assert result.stop_reason == "not a request" and result.platemap is None
    assert result.declined == "It is a question about life."
    assert result.error == "not a request: It is a question about life."
    assert model.tools[-1] == "not_a_request" and result.tool_calls == 1


def test_without_allow_decline_the_planner_has_neither_the_tool_nor_the_paragraph() -> None:
    """`plan` without `allow_decline` offers neither not_a_request nor its paragraph."""
    assert "not_a_request" not in system_prompt()
    assert "not_a_request" in system_prompt(decline=True)
    model = ScriptedModel(
        turn("", call("not_a_request", {"reason": "x"})),
        turn("", call("propose_platemap", {"platemap": pcr_map()})),
    )
    result = plan(REQUEST, chat=model)
    assert result.platemap is not None and result.declined is None
    first_reply = json.loads(model.seen[1][-1]["content"])
    assert "no tool named 'not_a_request'" in first_reply["error"]
