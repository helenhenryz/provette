"""The thinking-budget continuation: rendering, parsing, the second call, and one live run.

No network unless PROVETTE_NETWORK=1. The rendering is checked against the model's own chat
template, rendered with Jinja the way transformers does, when jinja2 happens to be importable
(`uv run --with jinja2 pytest tests/agent/test_budget.py`); otherwise that test is skipped.
"""

from __future__ import annotations

import json
import os
from typing import Any

import pytest

from provette.agent import budget
from provette.agent.budget import (
    CLOSE_THINKING,
    TEMPLATE_DIR,
    continue_after_cut,
    parse_completion,
    render,
    render_continuation,
)
from provette.agent.tools import SCHEMAS

LABWARE = next(s for s in SCHEMAS if s["function"]["name"] == "labware")
SYSTEM = "You are a helpful assistant."
CONVERSATION: list[dict[str, Any]] = [
    {"role": "system", "content": SYSTEM},
    {"role": "user", "content": "Load a 96-well plate. Look up its load name first."},
    {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": "call_0_0",
                "type": "function",
                "function": {"name": "labware", "arguments": json.dumps({"kind": "plate"})},
            }
        ],
    },
    {"role": "tool", "tool_call_id": "call_0_0", "content": json.dumps({"rows": [{"n": 96}]})},
    {"role": "user", "content": "Now write it."},
]
PARTIAL = "The user wants a plate. I have the load name, so I should call write_protocol"


def positions(text: str, *markers: str) -> list[int]:
    found = [text.find(m) for m in markers]
    assert all(p >= 0 for p in found), [m for m, p in zip(markers, found, strict=True) if p < 0]
    return found


# --- rendering -------------------------------------------------------------------------------


def test_render_continuation_has_the_markers_in_order() -> None:
    text = render_continuation(CONVERSATION[:2], [LABWARE], PARTIAL)
    order = positions(
        text,
        "<|im_start|>system\n" + SYSTEM,
        "# Tools\n\nYou have access to the following functions:\n\n<tools>",
        "<name>labware</name>",
        '<enum>["plate", "tubes", "tips", "reservoir", "module_block"]</enum>',
        '<required>["kind"]</required>',
        "<IMPORTANT>",
        "<|im_end|>\n<|im_start|>user\nLoad a 96-well plate. Look up its load name first.",
        "<|im_start|>assistant\n<think>\n" + PARTIAL,
        "." + CLOSE_THINKING,
    )
    assert order == sorted(order)
    assert text.endswith(PARTIAL + ".\n</think>\n\n")
    assert text.count("<|im_start|>assistant") == 1


def test_render_tool_call_history_in_the_template_format() -> None:
    text = render(CONVERSATION, [LABWARE])
    assert (
        "<|im_start|>assistant\n<think></think>\n<tool_call>\n<function=labware>\n"
        "<parameter=kind>\nplate\n</parameter>\n</function>\n</tool_call>\n<|im_end|>\n"
        '<|im_start|>user\n<tool_response>\n{"rows": [{"n": 96}]}\n</tool_response>\n<|im_end|>\n'
        "<|im_start|>user\nNow write it.<|im_end|>\n<|im_start|>assistant\n<think>\n"
    ) in text
    assert text.endswith("<|im_start|>assistant\n<think>\n")


def test_render_keeps_reasoning_after_the_last_user_and_drops_older() -> None:
    old = {"role": "assistant", "content": "first", "reasoning_content": "old thoughts"}
    new = {"role": "assistant", "content": "second", "reasoning": "new thoughts"}
    text = render(
        [CONVERSATION[0], CONVERSATION[1], old, CONVERSATION[4], new],
        [],
        add_generation_prompt=False,
    )
    assert "<|im_start|>assistant\n<think></think>\nfirst<|im_end|>\n" in text
    assert "old thoughts" not in text
    assert "<|im_start|>assistant\n<think>\nnew thoughts\n</think>\nsecond<|im_end|>\n" in text


def test_render_matches_the_chat_template_rendered_by_jinja() -> None:
    """The hand-written renderer against the real template, rendered the way transformers does
    (and vLLM through it): sandboxed, trim_blocks, lstrip_blocks, `tojson` without HTML escaping,
    tool-call arguments loaded from their JSON string first."""
    pytest.importorskip("jinja2")
    from jinja2.ext import loopcontrols
    from jinja2.sandbox import ImmutableSandboxedEnvironment

    env = ImmutableSandboxedEnvironment(
        trim_blocks=True, lstrip_blocks=True, extensions=[loopcontrols]
    )
    env.filters["tojson"] = lambda x, **kw: json.dumps(x, ensure_ascii=False, **kw)
    template = env.from_string((TEMPLATE_DIR / "chat_template.jinja").read_text(encoding="utf-8"))

    def server_side(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out = json.loads(json.dumps(messages))
        for m in out:
            for call in m.get("tool_calls") or []:
                call["function"]["arguments"] = json.loads(call["function"]["arguments"])
        return list(out)

    conversations = [
        CONVERSATION[:2],
        CONVERSATION,
        CONVERSATION[:4],
        [
            *CONVERSATION,
            {"role": "assistant", "content": "I will.", "reasoning_content": "thinking here"},
            {"role": "user", "content": "go"},
            {"role": "assistant", "content": "", "tool_calls": CONVERSATION[2]["tool_calls"]},
            {"role": "tool", "tool_call_id": "call_0_0", "content": "r1"},
            {"role": "tool", "tool_call_id": "call_0_0", "content": "r2"},
        ],
        [{"role": "user", "content": "no system"}],
    ]
    for tools in ([], [LABWARE], SCHEMAS):
        for messages in conversations:
            for generation in (True, False):
                expected = template.render(
                    messages=server_side(messages),
                    tools=tools,
                    add_generation_prompt=generation,
                    bos_token="<s>",
                    eos_token="<|im_end|>",
                )
                assert render(messages, tools, add_generation_prompt=generation) == expected


# --- parsing ---------------------------------------------------------------------------------


def test_parse_a_well_formed_tool_call_with_a_multiline_value() -> None:
    file = "from opentrons import protocol_api\n\ndef run(protocol):\n    pass\n"
    text = (
        "I will hand the file in now.\n<tool_call>\n<function=write_protocol>\n"
        f"<parameter=text>\n{file}\n</parameter>\n</function>\n</tool_call>\n"
    )
    parsed = parse_completion(text, SCHEMAS)
    assert parsed["content"] == "I will hand the file in now."
    assert len(parsed["tool_calls"]) == 1
    call = parsed["tool_calls"][0]
    assert call["id"] == "call_budget_1"
    assert call["type"] == "function"
    assert call["function"]["name"] == "write_protocol"
    assert json.loads(call["function"]["arguments"]) == {"text": file}


def test_parse_types_values_by_the_schema() -> None:
    text = (
        "<tool_call>\n<function=dilution_series>\n<parameter=stock_conc>\n100\n</parameter>\n"
        "<parameter=factor>\n2.5\n</parameter>\n<parameter=steps>\n8\n</parameter>\n"
        "</function>\n</tool_call>"
    )
    schema = {
        "type": "function",
        "function": {
            "name": "dilution_series",
            "parameters": {
                "type": "object",
                "properties": {
                    "stock_conc": {"type": "number"},
                    "factor": {"type": "number"},
                    "steps": {"type": "integer"},
                    "note": {"type": "string"},
                },
            },
        },
    }
    arguments = json.loads(
        parse_completion(text, [schema])["tool_calls"][0]["function"]["arguments"]
    )
    assert arguments == {"stock_conc": 100, "factor": 2.5, "steps": 8}
    untyped = json.loads(parse_completion(text)["tool_calls"][0]["function"]["arguments"])
    assert untyped == {"stock_conc": "100", "factor": "2.5", "steps": "8"}


def test_parse_two_calls_and_a_stray_think_close() -> None:
    text = (
        "</think>\n\n<tool_call>\n<function=platemap>\n</function>\n</tool_call>\n"
        "<tool_call>\n<function=labware>\n<parameter=kind>\ntips\n</parameter>\n</function>\n"
        "</tool_call>"
    )
    parsed = parse_completion(text, SCHEMAS)
    assert [c["function"]["name"] for c in parsed["tool_calls"]] == ["platemap", "labware"]
    assert [c["id"] for c in parsed["tool_calls"]] == ["call_budget_1", "call_budget_2"]
    assert json.loads(parsed["tool_calls"][0]["function"]["arguments"]) == {}
    assert parsed["content"] == ""


def test_parse_a_malformed_tool_call_is_content_only() -> None:
    text = "Let me call it.\n<tool_call>\n<function=labware>\n<parameter=kind>\nplate\n"
    assert parse_completion(text, SCHEMAS) == {"content": text.strip(), "tool_calls": []}
    no_function = "<tool_call>\nlabware(kind=plate)\n</tool_call>"
    assert parse_completion(no_function) == {"content": no_function, "tool_calls": []}


def test_parse_plain_text() -> None:
    assert parse_completion("Here is the plan: load the plate.") == {
        "content": "Here is the plan: load the plate.",
        "tool_calls": [],
    }
    assert parse_completion("") == {"content": "", "tool_calls": []}


# --- the second call, with the HTTP call replaced ----------------------------------------------


def test_continue_after_cut_renders_posts_and_parses() -> None:
    seen: list[dict[str, Any]] = []

    def post(body: dict[str, Any]) -> dict[str, Any]:
        seen.append(body)
        return {
            "choices": [
                {
                    "text": "<tool_call>\n<function=labware>\n<parameter=kind>\nplate\n"
                    "</parameter>\n</function>\n</tool_call>",
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 500, "completion_tokens": 30, "total_tokens": 530},
        }

    reply = continue_after_cut(
        ("https://example.test/v1", "k"), "nano", CONVERSATION[:2], [LABWARE], PARTIAL, 2000, post
    )
    body = seen[0]
    assert body["model"] == "nano"
    assert body["max_tokens"] == 2000
    assert (body["temperature"], body["top_p"], body["stop"]) == (0.6, 0.95, ["<|im_end|>"])
    assert body["prompt"] == render_continuation(CONVERSATION[:2], [LABWARE], PARTIAL)
    message = reply["message"]
    assert message["role"] == "assistant"
    assert message["budget_continued"] is True
    assert message["reasoning"] == PARTIAL + "."
    assert message["content"] == ""
    assert message["tool_calls"][0]["function"] == {
        "name": "labware",
        "arguments": '{"kind": "plate"}',
    }
    assert reply["usage"]["completion_tokens"] == 30
    assert reply["finish_reason"] == "stop"


def test_continue_after_cut_reads_the_endpoint_from_a_chat_client() -> None:
    class Client:
        base_url = "https://example.test/v1"
        api_key = "k"
        timeout_s = 5.0

    captured: dict[str, Any] = {}

    def fake_post(client: Any, body: dict[str, Any], timeout_s: float) -> dict[str, Any]:
        captured.update(base_url=client.base_url, timeout=timeout_s)
        return {"choices": [{"text": "plain answer", "finish_reason": "stop"}], "usage": {}}

    original = budget.post_completion
    budget.post_completion = fake_post  # type: ignore[assignment]
    try:
        reply = continue_after_cut(Client(), "nano", CONVERSATION[:2], [], "thought", 10)
    finally:
        budget.post_completion = original
    assert captured == {"base_url": "https://example.test/v1", "timeout": 5.0}
    assert reply["message"]["content"] == "plain answer"
    assert reply["message"]["tool_calls"] == []


# --- live, once --------------------------------------------------------------------------------


@pytest.mark.network
@pytest.mark.skipif(os.environ.get("PROVETTE_NETWORK") != "1", reason="PROVETTE_NETWORK=1 to run")
def test_live_cut_then_continue_on_nano() -> None:
    """A chat call cut at 200 tokens, then the continuation with 2,000: a tool call comes back.
    Needs PROVETTE_API_KEY and PROVETTE_BASE_URL
    (set -a; . ~/.config/provette/token-factory.env)."""
    from provette.agent.llm import OpenAIChat

    model = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"
    client = OpenAIChat(
        os.environ["PROVETTE_BASE_URL"], model, os.environ["PROVETTE_API_KEY"], 300, 200
    )
    messages = [
        {"role": "system", "content": SYSTEM},
        {
            "role": "user",
            "content": "I need to load a 96-well PCR plate on an Opentrons OT-2. Before writing "
            "anything, look up the real load name with the labware tool.",
        },
    ]
    first = client(messages, [LABWARE])
    assert first["finish_reason"] == "length"
    reasoning = first["message"].get("reasoning") or first["message"].get("reasoning_content")
    assert reasoning
    assert not first["message"].get("tool_calls")

    reply = continue_after_cut(client, model, messages, [LABWARE], reasoning, 2000)
    print(json.dumps({"first_usage": first["usage"], "second": reply}, indent=1))
    assert reply["message"]["budget_continued"] is True
    calls = reply["message"]["tool_calls"]
    assert calls, reply
    assert calls[0]["function"]["name"] == "labware"
    assert json.loads(calls[0]["function"]["arguments"]) == {"kind": "plate"}
