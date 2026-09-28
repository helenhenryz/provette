"""One chat completion with tools over the OpenAI API: the client the agent and the planner share.

A `Chat` is anything called as `chat(messages, tools)` that returns
`{"message": the assistant message dict, "usage": {...}, "finish_reason": str}`. `OpenAIChat`
is the network one; the tests pass a scripted function instead.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

Chat = Callable[[list[dict[str, Any]], list[dict[str, Any]]], dict[str, Any]]
SYSTEM = "You are a helpful assistant."  # what NVIDIA's model card and cookbook use
MAX_TOKENS_PER_TURN = 24000  # Nano's reasoning passes 16,000 on about one turn in eight


class OpenAIChat:
    """One chat completion with tools over the OpenAI API, with NVIDIA's settings for tool use
    on Nemotron 3: temperature 0.6, top_p 0.95, reasoning on (the default). The per-turn cap is
    24,000 tokens: Nano's reasoning goes past 16,000 on about one turn in eight."""

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str,
        timeout_s: float = 1800,
        max_tokens: int = MAX_TOKENS_PER_TURN,
        presence_penalty: float = 0.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout_s = timeout_s
        self.max_tokens = max_tokens
        self.presence_penalty = presence_penalty
        # NVIDIA's cards: Nano 0.6 / 0.95 for tool use; Super 1.0 / 0.95 "across all tasks"
        # (docs/harness-practices.md, row 4).
        self.temperature = 1.0 if "super" in model.lower() else 0.6

    def __call__(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> dict[str, Any]:
        body = json.dumps(
            {
                "model": self.model,
                "messages": messages,
                "tools": tools,
                "tool_choice": "auto",
                "temperature": self.temperature,
                "top_p": 0.95,
                "max_tokens": self.max_tokens,
                **({"presence_penalty": self.presence_penalty} if self.presence_penalty else {}),
            }
        ).encode()
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = "Bearer " + self.api_key
        request = urllib.request.Request(self.base_url + "/chat/completions", body, headers)
        with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
            reply = json.loads(response.read())
        choice = reply["choices"][0]
        return {
            "message": choice["message"],
            "usage": reply.get("usage") or {},
            "finish_reason": choice.get("finish_reason"),
        }


def describe_error(error: BaseException) -> str:
    """An API error as one line for a transcript: the HTTP status and the start of the body."""
    if isinstance(error, urllib.error.HTTPError):
        try:
            body = error.read().decode("utf-8", errors="replace")[:500]
        except OSError:
            body = ""
        return f"HTTP {error.code}: {body}"
    return f"{type(error).__name__}: {error}"
