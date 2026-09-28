"""One planning episode: the model reads the request, calls the calculators, proposes the map.

`plan` sends the planner's sheet as the system prompt and the request as the user message,
then loops: the model answers, its tool calls run through `provette.planner.tools.Toolbox`, the
results go back, until `propose_platemap` accepts a map or a budget runs out. What comes back
is a `Planning`: the map (or none), why it stopped, and the token counts the API reported.

A budget that runs out is a failure, never a guess: `plan_platemap` raises `PlanError` and the
caller gets no map at all.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from provette.agent.llm import Chat, OpenAIChat, describe_error
from provette.intent.spec import PlateMap
from provette.planner.prompt import system_prompt
from provette.planner.tools import DECLINE_SCHEMA, SCHEMAS, Toolbox

DEFAULT_MODEL = "nvidia/nemotron-3-super-120b-a12b"
MAX_TOOL_CALLS = 12
MAX_COMPLETION_TOKENS = 40000
API_ERRORS_TO_STOP = 3
BACKOFF_S = (5.0, 15.0)
IDLE_TURNS_TO_STOP = 2  # turns in a row with no tool call
STOPPED_BY_USER = "stopped by the user"  # the stop_reason when `should_stop` says so
NOT_A_REQUEST = "not a request"  # the stop_reason when the model calls not_a_request


class PlanError(RuntimeError):
    """The planner could not produce a valid plate map. The message says why."""


@dataclass
class Planning:
    """What one episode produced. `platemap` is None unless the model's map was accepted."""

    request_id: str
    request: str
    model: str
    platemap: PlateMap | None
    stop_reason: str
    tool_calls: int
    turns: int
    tokens_in: int
    tokens_out: int
    seconds: float
    rejections: list[str] = field(default_factory=list)  # each refused proposal's reason
    declined: str | None = None  # the model's one sentence, when it said this is no request
    repairs: list[str] = field(default_factory=list)  # closing brackets the tool put in
    transcript: list[dict[str, Any]] = field(default_factory=list)

    @property
    def error(self) -> str | None:
        if self.platemap is not None:
            return None
        last = f" Last refusal: {self.rejections[-1]}" if self.rejections else ""
        if self.declined:
            return f"not a request: {self.declined}"
        return f"no plate map: {self.stop_reason}.{last}"


def plan(
    request: str,
    model: str = DEFAULT_MODEL,
    base_url: str = "",
    api_key: str = "",
    *,
    request_id: str = "planned",
    technique: str | None = None,
    chat: Chat | None = None,
    max_tool_calls: int = MAX_TOOL_CALLS,
    max_completion_tokens: int = MAX_COMPLETION_TOKENS,
    should_stop: Callable[[], bool] | None = None,
    allow_decline: bool = False,
) -> Planning:
    """Run one planning episode. `chat` replaces the network call (a scripted model in tests).

    `technique` is the request's technique word when the caller has one (`requests.jsonl`);
    it is written into the map as given and the model is not asked for it. `should_stop` is
    asked before every model call and before every tool call; when it says yes the episode
    ends with stop_reason `STOPPED_BY_USER` and whatever was done so far. `allow_decline` (the
    product and its evaluation) offers the not_a_request tool: a message that asks for no
    liquid handling then ends with stop_reason `NOT_A_REQUEST` and no map, instead of an
    invented one.
    """
    started = time.time()
    toolbox = Toolbox(request_id, request, technique, allow_decline=allow_decline)
    schemas = SCHEMAS + [DECLINE_SCHEMA] if allow_decline else SCHEMAS
    ask: Chat = chat or OpenAIChat(base_url, model, api_key)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt(decline=allow_decline)},
        {"role": "user", "content": request},
    ]
    transcript: list[dict[str, Any]] = []
    tool_calls = tokens_in = tokens_out = 0
    api_errors = idle_turns = turn = 0
    stop_reason: str | None = None
    while stop_reason is None:
        if should_stop is not None and should_stop():
            stop_reason = STOPPED_BY_USER
            break
        if tool_calls >= max_tool_calls:
            stop_reason = "call budget"
            break
        if tokens_out >= max_completion_tokens:
            stop_reason = "token budget"
            break
        try:
            reply = ask(messages, schemas)
        except (OSError, ValueError, KeyError, IndexError, TypeError) as error:
            api_errors += 1
            transcript.append({"turn": turn, "api_error": describe_error(error)})
            if api_errors >= API_ERRORS_TO_STOP:
                stop_reason = "api errors"
                break
            time.sleep(BACKOFF_S[min(api_errors - 1, len(BACKOFF_S) - 1)])
            continue
        api_errors = 0
        message = reply.get("message") or {}
        usage = reply.get("usage") or {}
        tokens_in += int(usage.get("prompt_tokens") or 0)
        tokens_out += int(usage.get("completion_tokens") or 0)
        content = message.get("content") or ""
        calls = [c for c in (message.get("tool_calls") or []) if c.get("function")]
        assistant: dict[str, Any] = {"role": "assistant", "content": content}
        if calls:
            assistant["tool_calls"] = [
                {
                    "id": c.get("id") or f"call_{turn}_{n}",
                    "type": "function",
                    "function": {
                        "name": c["function"].get("name") or "",
                        "arguments": c["function"].get("arguments") or "{}",
                    },
                }
                for n, c in enumerate(calls)
            ]
        messages.append(assistant)
        results: list[dict[str, Any]] = []
        if calls:
            idle_turns = 0
            for call in assistant["tool_calls"]:
                if should_stop is not None and should_stop():
                    stop_reason = STOPPED_BY_USER
                    break
                name = call["function"]["name"]
                result = toolbox.call(name, call["function"]["arguments"])
                tool_calls += 1
                messages.append(
                    {"role": "tool", "tool_call_id": call["id"], "content": json.dumps(result)}
                )
                results.append({"name": name, "result": result})
                if toolbox.proposed is not None:
                    stop_reason = "proposed"
                    break
                if toolbox.declined is not None:
                    stop_reason = NOT_A_REQUEST
                    break
        else:
            idle_turns += 1
            if idle_turns >= IDLE_TURNS_TO_STOP:
                stop_reason = "model stopped using tools"
            else:
                cut = reply.get("finish_reason") == "length"
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Your answer was cut off at the token limit. Reason less. "
                            if cut
                            else "You called no tool. "
                        )
                        + "Hand the map in with the propose_platemap tool, as one JSON object."
                        + (
                            " If the message asks for no liquid handling, call not_a_request."
                            if allow_decline
                            else ""
                        ),
                    }
                )
        if repeated_refusal(toolbox.rejections):
            # The same refusal twice in a row: the model is not reading it. Say in the next
            # message what to change and what the map declares, so the third try differs.
            messages.append(
                {
                    "role": "user",
                    "content": repair_message(toolbox.rejections[-1], toolbox.last_liquids),
                }
            )
        transcript.append(
            {
                "turn": turn,
                "finish_reason": reply.get("finish_reason"),
                "content": content,
                "reasoning": message.get("reasoning") or message.get("reasoning_content"),
                "tool_calls": [
                    {"id": c["id"], **c["function"]} for c in assistant.get("tool_calls", [])
                ],
                "tool_results": results,
                "usage": usage,
            }
        )
        turn += 1
    return Planning(
        request_id=request_id,
        request=request,
        model=model,
        platemap=toolbox.proposed,
        stop_reason=stop_reason,
        tool_calls=tool_calls,
        turns=turn,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        seconds=round(time.time() - started, 1),
        rejections=list(toolbox.rejections),
        declined=toolbox.declined,
        repairs=list(toolbox.repairs),
        transcript=transcript,
    )


def repeated_refusal(rejections: list[str]) -> bool:
    """Did the last two proposals come back with the same refusal, word for word?"""
    return len(rejections) >= 2 and rejections[-1] == rejections[-2]


def repair_message(refusal: str, liquids: list[str]) -> str:
    """The message after a refusal repeated itself: the field to change, quoted from the
    refusal (its "where" clause: the variant, the group or the well, the liquid it names),
    and the liquids the map declares, so the model can see the mismatch on one line."""
    where, _, problem = refusal.partition(": ")
    # the validator's clauses name the field ("variant 'x', group 'y'", "liquid 'z'",
    # "destination"); any other refusal is about the map as a whole
    named = problem and where.startswith(("variant ", "liquid ", "destination", "discard_intended"))
    field = where if named else "the plate map"
    declared = ", ".join(repr(name) for name in liquids) or "none"
    return (
        f"The map was refused twice for the same reason: {refusal} "
        f"Change this field and only this field: {field}. "
        f"The liquids your map declares are: {declared}. "
        "Every liquid a well holds must be one of those (or 'stem_{i}' / 'stem@{well}' "
        "declared with bind 'indexed' / 'well'); either declare the missing liquid or use "
        "a declared name. Then send the whole map again with propose_platemap."
    )


def plan_platemap(
    request: str,
    model: str = DEFAULT_MODEL,
    base_url: str = "",
    api_key: str = "",
    *,
    request_id: str = "planned",
    technique: str | None = None,
    chat: Chat | None = None,
) -> PlateMap:
    """The plate map the model proposes for `request`, or `PlanError`; never a guessed map."""
    result = plan(
        request, model, base_url, api_key, request_id=request_id, technique=technique, chat=chat
    )
    if result.platemap is None:
        raise PlanError(result.error or "no plate map")
    return result.platemap
