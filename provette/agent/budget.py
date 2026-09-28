"""The thinking budget for Nemotron 3 Nano: finish a turn cut in the middle of its reasoning.

Call 1 is the ordinary chat call (`provette.agent.llm.OpenAIChat`) with `max_tokens` set to the
budget. When it comes back with `finish_reason == "length"`, the model was still thinking: the
reply has the partial reasoning in `message.reasoning` and no tool call. Call 2, here, closes the
thinking for it (`.\\n</think>\\n\\n`), renders the whole conversation the way the server renders
it, and asks `/v1/completions` to carry on from there with the rest of the turn's tokens. NVIDIA's
tech report describes exactly this (arXiv 2512.20856, section 2.7): append `</think>` and the
model "will generate the response based on the partial thinking trace".

The completions endpoint returns text, so the tool call comes back in the chat template's own
format and `parse_completion` turns it into the OpenAI-shaped `tool_calls` the loop consumes.

The rendering is a hand-written copy of the model's chat template for the message shapes our
loop sends (system, user, assistant with or without tool calls, tool results) and for tool
schemas. The template itself is committed next to this file, in `nemotron3_nano/`, with a NOTE
naming its source; `tests/agent/test_budget.py` renders it with Jinja when jinja2 is available
and checks the two agree byte for byte.
"""

from __future__ import annotations

import json
import re
import urllib.request
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, Protocol

TEMPLATE_DIR = Path(__file__).resolve().parent / "nemotron3_nano"
IM_START = "<|im_start|>"
IM_END = "<|im_end|>"
GENERATION_PROMPT = IM_START + "assistant\n<think>\n"  # the template's, with thinking on
CLOSE_THINKING = "\n</think>\n\n"  # what we append after the partial reasoning and its full stop
TEMPERATURE = 0.6  # NVIDIA's settings for tool use on Nano, as in OpenAIChat
TOP_P = 0.95

# The template's fixed instruction after the tool list, verbatim.
TOOL_CALL_INSTRUCTIONS = (
    "\n\nIf you choose to call a function ONLY reply in the following format with NO suffix:"
    "\n\n<tool_call>\n<function=example_function_name>\n<parameter=example_parameter_1>\n"
    "value_1\n</parameter>\n<parameter=example_parameter_2>\nThis is the value for the second "
    "parameter\nthat can span\nmultiple lines\n</parameter>\n</function>\n</tool_call>\n\n"
    "<IMPORTANT>\nReminder:\n- Function calls MUST follow the specified format: an inner "
    "<function=...></function> block must be nested within <tool_call></tool_call> XML tags\n"
    "- Required parameters MUST be specified\n- You may provide optional reasoning for your "
    "function call in natural language BEFORE the function call, but NOT after\n- If there is "
    "no function call available, answer the question like normal with your current knowledge "
    "and do not tell the user about function calls\n</IMPORTANT>"
)

_TOOL_CALL = re.compile(
    r"<tool_call>\s*<function=([^>\n]+)>\n?(.*?)</function>\s*</tool_call>", re.S
)
_PARAMETER = re.compile(r"<parameter=([^>\n]+)>\n?(.*?)\n?</parameter>", re.S)
_THINK_BLOCK = re.compile(r"^\s*(?:<think>.*?)?</think>\s*", re.S)


class Endpoint(Protocol):
    """What `continue_after_cut` needs from a client: `OpenAIChat` has both."""

    base_url: str
    api_key: str


# ---------------------------------------------------------------------------------------------
# Rendering: the chat template, by hand, for the shapes our loop sends.


def _tojson(value: Any) -> str:
    """The `tojson` filter as transformers installs it: `json.dumps(ensure_ascii=False)`, so
    non-ASCII stays as is and `<` is not HTML-escaped (Jinja's own `tojson` would escape it)."""
    return json.dumps(value, ensure_ascii=False)


def _structured(value: Any) -> bool:
    """The template's `is mapping or (is sequence and is not string)`."""
    return isinstance(value, (Mapping, list, tuple))


def _extra_keys(fields: Any, handled: tuple[str, ...]) -> str:
    """The template's `render_extra_keys` macro: every key not handled, as `\\n<key>value</key>`."""
    if not isinstance(fields, Mapping):
        return ""
    out = []
    for key, value in fields.items():
        if key in handled:
            continue
        text = _tojson(value) if _structured(value) else str(value)
        out.append(f"\n<{key}>{text}</{key}>")
    return "".join(out)


def render_tools(tools: list[dict[str, Any]]) -> str:
    """The `# Tools` block the template puts in the system message, for OpenAI-shaped schemas."""
    parts = ["# Tools\n\nYou have access to the following functions:\n\n<tools>"]
    for schema in tools:
        tool = schema.get("function", schema)
        parts.append(f"\n<function>\n<name>{tool['name']}</name>")
        if "description" in tool:
            parts.append(f"\n<description>{str(tool['description']).strip()}</description>")
        parts.append("\n<parameters>")
        parameters = tool.get("parameters")
        if isinstance(parameters, Mapping) and isinstance(parameters.get("properties"), Mapping):
            for name, fields in parameters["properties"].items():
                parts.append(f"\n<parameter>\n<name>{name}</name>")
                if "type" in fields:
                    parts.append(f"\n<type>{fields['type']}</type>")
                if "description" in fields:
                    parts.append(
                        f"\n<description>{str(fields['description']).strip()}</description>"
                    )
                if "enum" in fields:
                    parts.append(f"\n<enum>{_tojson(fields['enum'])}</enum>")
                parts.append(_extra_keys(fields, ("name", "type", "description", "enum")))
                parts.append("\n</parameter>")
        parts.append(_extra_keys(parameters, ("type", "properties", "required")))
        if isinstance(parameters, Mapping) and "required" in parameters:
            parts.append(f"\n<required>{_tojson(parameters['required'])}</required>")
        parts.append("\n</parameters>")
        parts.append(_extra_keys(tool, ("type", "name", "description", "parameters")))
        parts.append("\n</function>")
    parts.append("\n</tools>")
    parts.append(TOOL_CALL_INSTRUCTIONS)
    return "".join(parts)


def _arguments(call: Mapping[str, Any]) -> dict[str, Any]:
    """The call's arguments as a dict: vLLM `json.loads` the OpenAI string before rendering."""
    function = call.get("function", call)
    arguments = function.get("arguments")
    if isinstance(arguments, str):
        try:
            loaded = json.loads(arguments)
        except ValueError:
            loaded = {}
        return dict(loaded) if isinstance(loaded, Mapping) else {}
    return dict(arguments) if isinstance(arguments, Mapping) else {}


def _render_tool_calls(calls: list[Mapping[str, Any]]) -> str:
    out = []
    for call in calls:
        function = call.get("function", call)
        out.append(f"<tool_call>\n<function={function.get('name', '')}>\n")
        for name, value in _arguments(call).items():
            text = _tojson(value) if _structured(value) else str(value)
            out.append(f"<parameter={name}>\n{text}\n</parameter>\n")
        out.append("</function>\n</tool_call>\n")
    return "".join(out)


def _assistant(message: Mapping[str, Any], keep_thinking: bool) -> str:
    """One assistant turn as the template renders it. `keep_thinking` is false for turns before
    the last user message, whose reasoning the template drops (`truncate_history_thinking`)."""
    reasoning = message.get("reasoning_content")
    if reasoning is None:
        reasoning = message.get("reasoning")  # Token Factory's name for it in replies
    raw = message.get("content") or ""
    if isinstance(reasoning, str) and reasoning.strip():
        content = f"<think>\n{reasoning}\n</think>\n{raw}"
    else:
        content = str(raw)
        if "<think>" not in content and "</think>" not in content:
            content = "<think></think>" + content
    calls = [c for c in (message.get("tool_calls") or []) if isinstance(c, Mapping)]
    if calls:
        out = IM_START + "assistant\n"
        if content.strip():
            if keep_thinking:
                out += content.strip() + "\n"
            else:
                c = content
                if "</think>" in c:
                    c = c.split("</think>")[-1]
                elif "<think>" in c:
                    c = c.split("<think>")[0]
                out += "<think></think>" + c.strip() + "\n"
        else:
            out += "<think></think>"
        return out + _render_tool_calls(calls) + IM_END + "\n"
    if keep_thinking:
        return IM_START + "assistant\n" + content.strip() + IM_END + "\n"
    c = content
    if "<think>" in c and "</think>" in c:
        c = "<think></think>" + c.split("</think>")[-1]
    c = c.strip()
    return IM_START + "assistant\n" + c + IM_END + "\n"


def render(
    messages: list[dict[str, Any]], tools: list[dict[str, Any]], add_generation_prompt: bool = True
) -> str:
    """The string the server tokenizes for a chat call: the model's chat template applied to
    `messages` and `tools`, with thinking on and old reasoning dropped (the template's defaults),
    ending with the generation prompt `<|im_start|>assistant\\n<think>\\n` when asked."""
    if messages and messages[0].get("role") == "system":
        system = str(messages[0].get("content") or "")
        rest = messages[1:]
    else:
        system = ""
        rest = messages
    out = IM_START + "system\n" + system
    if tools:
        if system:
            out += "\n\n"
        out += render_tools(tools)
    out += IM_END + "\n"
    last_user = max((i for i, m in enumerate(rest) if m.get("role") == "user"), default=-1)
    for index, message in enumerate(rest):
        role = message.get("role")
        if role == "assistant":
            out += _assistant(message, keep_thinking=index >= last_user)
        elif role in ("user", "system"):
            out += f"{IM_START}{role}\n{message.get('content')}{IM_END}\n"
        elif role == "tool":
            if index > 0 and rest[index - 1].get("role") != "tool":
                out += IM_START + "user\n"
            out += f"<tool_response>\n{message.get('content')}\n</tool_response>\n"
            last = index == len(rest) - 1
            if last or rest[index + 1].get("role") != "tool":
                out += IM_END + "\n"
        else:
            out += f"{IM_START}{role}\n{message.get('content')}{IM_END}\n"
    if add_generation_prompt:
        out += GENERATION_PROMPT
    return out


def close_reasoning(partial_reasoning: str) -> str:
    """The partial reasoning with a full stop on its last line: what the assistant message
    carries as `reasoning` after the continuation."""
    return partial_reasoning.rstrip() + "."


def render_continuation(
    messages: list[dict[str, Any]], tools: list[dict[str, Any]], partial_reasoning: str
) -> str:
    """The prompt for `/v1/completions`: exactly what the server rendered for call 1, then the
    reasoning the model produced before the cut, closed with `.\\n</think>\\n\\n`, and nothing
    after it, so the model continues with its answer (the tool call)."""
    return render(messages, tools) + close_reasoning(partial_reasoning) + CLOSE_THINKING


# ---------------------------------------------------------------------------------------------
# Parsing: the template's tool-call text back into OpenAI-shaped tool calls.


def _convert(value: str, kind: str | None) -> Any:
    """A parameter value with the type its schema declares; the text itself when it does not fit."""
    try:
        if kind == "integer":
            return int(value)
        if kind == "number":
            try:
                return int(value)
            except ValueError:
                return float(value)
        if kind == "boolean":
            if value.strip().lower() in ("true", "false"):
                return value.strip().lower() == "true"
            return value
        if kind in ("object", "array"):
            return json.loads(value)
    except ValueError:
        return value
    return value


def _parameter_types(tools: list[dict[str, Any]] | None) -> dict[str, dict[str, str]]:
    types: dict[str, dict[str, str]] = {}
    for schema in tools or []:
        tool = schema.get("function", schema)
        properties = (tool.get("parameters") or {}).get("properties") or {}
        types[tool["name"]] = {
            name: str(fields["type"])
            for name, fields in properties.items()
            if isinstance(fields, Mapping) and "type" in fields
        }
    return types


def parse_completion(text: str, tools: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """The completion's text as `{"content": str, "tool_calls": [...]}`.

    Tool calls are the template's `<tool_call><function=NAME><parameter=ARG>value</parameter>
    ...</function></tool_call>` blocks, returned in the OpenAI shape with `arguments` a JSON
    string and ids `call_budget_1`, `call_budget_2`, ... Values are typed by the schemas when
    `tools` is given (integer, number, boolean, object, array), strings otherwise. What is not a
    well-formed tool call stays in `content`; a malformed one gives content only.
    """
    types = _parameter_types(tools)
    body = _THINK_BLOCK.sub("", text, count=1)
    calls: list[dict[str, Any]] = []
    for match in _TOOL_CALL.finditer(body):
        name = match.group(1).strip()
        arguments = {
            p.group(1).strip(): _convert(p.group(2), types.get(name, {}).get(p.group(1).strip()))
            for p in _PARAMETER.finditer(match.group(2))
        }
        calls.append(
            {
                "id": f"call_budget_{len(calls) + 1}",
                "type": "function",
                "function": {"name": name, "arguments": json.dumps(arguments, ensure_ascii=False)},
            }
        )
    content = _TOOL_CALL.sub("", body).strip()
    return {"content": content, "tool_calls": calls}


# ---------------------------------------------------------------------------------------------
# The second call.


def post_completion(
    client: Endpoint | tuple[str, str], body: dict[str, Any], timeout_s: float
) -> dict[str, Any]:
    """`POST /v1/completions` on the client's endpoint and the parsed JSON reply."""
    if isinstance(client, tuple):
        base_url, api_key = client
    else:
        base_url, api_key = client.base_url, client.api_key
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = "Bearer " + api_key
    request = urllib.request.Request(
        base_url.rstrip("/") + "/completions", json.dumps(body).encode(), headers
    )
    with urllib.request.urlopen(request, timeout=timeout_s) as response:
        reply: dict[str, Any] = json.loads(response.read())
    return reply


def continue_after_cut(
    client: Endpoint | tuple[str, str],
    model: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    partial_reasoning: str,
    max_tokens: int,
    post: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Finish a turn whose chat call was cut at `finish_reason == "length"`.

    `client` is the `OpenAIChat` in use (its `base_url` and `api_key` are read) or a
    `(base_url, api_key)` pair; `messages` are the ones call 1 was sent (without the cut reply);
    `partial_reasoning` is `message.reasoning` from the cut reply; `max_tokens` is what is left
    of the turn. Returns the same shape as a `Chat` call, `{"message", "usage", "finish_reason"}`,
    where the message is `{"role": "assistant", "content", "tool_calls", "reasoning",
    "budget_continued": True}`: the reasoning is the partial one with its full stop, the tool
    calls are parsed from the completion's text, and `content` is any plain text around them.
    `post` replaces the HTTP call in tests. No state: one render, one request, one parse.
    """
    prompt = render_continuation(messages, tools, partial_reasoning)
    body = {
        "model": model,
        "prompt": prompt,
        "max_tokens": max_tokens,
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
        "stop": [IM_END],
    }
    if post is None:
        timeout_s = float(getattr(client, "timeout_s", 1800.0))
        reply = post_completion(client, body, timeout_s)
    else:
        reply = post(body)
    choice = (reply.get("choices") or [{}])[0]
    parsed = parse_completion(str(choice.get("text") or ""), tools)
    message: dict[str, Any] = {
        "role": "assistant",
        "content": parsed["content"],
        "tool_calls": parsed["tool_calls"],
        "reasoning": close_reasoning(partial_reasoning),
        "budget_continued": True,
    }
    return {
        "message": message,
        "usage": reply.get("usage") or {},
        "finish_reason": choice.get("finish_reason"),
    }
