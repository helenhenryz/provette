"""One episode: the model writes a protocol with tools, checks it, repairs it, and submits.

`run_episode` sends the reference sheet and the requirements as the system prompt and the
request as the user message, then loops: the model answers, its tool calls are run through
`provette.agent.tools.Toolbox`, the results go back, until it calls `submit` or a budget runs out.
Everything is written under `out_dir`:

    transcript.jsonl   every turn: what the model said, what it called, what came back, tokens
    log.jsonl          one slim line per turn with the token usage (eval/agent/tabulate.py reads it)
    NN-draft.py        every draft, in order
    NN-checks.json     the runner's full result for draft NN
    done.json          the summary (the same keys eval/baseline/run.py writes, plus this loop's own)

The model is never the judge. Whether the episode ended verified is read from the runner's last
result on the submitted draft, and if the model submitted a draft it never checked, the harness
checks it, so `done.json` always says how the submitted file really stood.
"""

from __future__ import annotations

import json
import os
import re
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from provette.agent.budget import continue_after_cut
from provette.agent.llm import SYSTEM, Chat, OpenAIChat, describe_error
from provette.agent.runner import Runner
from provette.agent.tools import SCHEMAS, Toolbox, is_clean, liquid_names

ROOT = Path(__file__).resolve().parents[2]
# The preamble and the reference sheet the prompt is built from live under eval/requests of
# a checkout; the image keeps eval/ elsewhere and says where with PROVETTE_EVAL_DIR (the same
# setting the API reads), so the path is read here at import, as the rules read theirs. The
# first live run on the deployment failed on this: `/src/eval/requests/preamble.md`.
REQUESTS = Path(os.environ.get("PROVETTE_EVAL_DIR") or ROOT / "eval") / "requests"
TIPS_LINE = "- We are short on tip racks this month: use as few tips as possible."
TOOLS_PARAGRAPH = "\n".join(
    [
        "You have tools; work through them.",
        "- platemap: call it first. It gives the exact liquid names and what every well must hold.",
        "- labware(kind): the real load names and well names. Call it for every kind you load "
        "(plate, tubes, tips, reservoir) and use only names and wells it returns.",
        "- dilution_series, normalise, master_mix: the arithmetic, done for you. Call them for "
        "any serial dilution, normalisation or pooled mix instead of working the numbers out "
        "yourself, and write the protocol to do exactly the transfers they return.",
        "- write_protocol(text): hand in the WHOLE Python file as one string. It runs the "
        "simulator, the plate-map check and the contamination check on it and returns them "
        "as `checks`.",
        "- submit(): finish.",
        "Rules: read the `checks` that write_protocol returns before writing again. Submit "
        "only when they report ready_to_submit true (simulator passed, verify_exit 0, "
        "check_exit 0). Fix what they name; do not rename the liquids. If you cannot get "
        "there after several tries, submit your best draft. Keep your reasoning short and act "
        "through the tools.",
    ]
)

# The chat call (`Chat`, `OpenAIChat`) lives in provette.agent.llm; the planner uses it too.
MAX_TOOL_CALLS = 25  # an episode's budget of tool calls
MAX_COMPLETION_TOKENS = 100000  # and of the model's output tokens, reasoning included
MIN_DRAFTS = 3  # a rejected draft is not taken as the answer before this many (D-32)
CONTINUE_TOKENS = 8000  # what a cut turn may still spend on the answer (a file is 4,000 to 6,000)
API_ERRORS_TO_STOP = 3
BACKOFF_S = (5.0, 15.0)
IDLE_TURNS_TO_STOP = 3  # turns in a row with neither a tool call nor a code block
STOPPED_BY_USER = "stopped by the user"  # the stop_reason when `should_stop` says so


def system_prompt(platemap: Mapping[str, Any], condition: str) -> str:
    """The reference sheet and the preamble's requirements, as eval/baseline/run.py builds them,
    with the tools in place of 'output only the Python file'."""
    preamble = (REQUESTS / "preamble.md").read_text(encoding="utf-8").rstrip()
    if condition == "short-on-tips":
        preamble = preamble.replace("- Output only", TIPS_LINE + "\n- Output only")
    names = ", ".join(f'"{n}"' for n in liquid_names(platemap))
    naming = (
        f"- Name the liquids exactly like this in define_liquid: {names}. "
        "Any other liquid you need may have any name."
    )
    preamble = preamble.replace("- The protocol must pass", naming + "\n- The protocol must pass")
    preamble = preamble.replace(
        "- Output only the Python file.",
        "- Hand the file in with the write_protocol tool, as one string; never paste it as text.",
    )
    preamble = preamble.replace("for the request below.", "for the request in the user's message.")
    preamble = preamble.removesuffix("Request:").rstrip()
    reference = (REQUESTS / "reference.md").read_text(encoding="utf-8").rstrip()
    return f"{SYSTEM}\n\n{reference}\n\n{preamble}\n\n{TOOLS_PARAGRAPH}"


def fenced_block(text: str) -> str | None:
    """The longest fenced code block in a reply, or None: the model pasted a file as text."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    blocks = re.findall(r"```(?:python|py)?\s*\n(.*?)```", text, flags=re.S)
    return max(blocks, key=len).strip() + "\n" if blocks else None


def run_episode(
    request: Mapping[str, str],
    platemap_path: Path,
    runner: Runner,
    model: str,
    base_url: str,
    api_key: str,
    out_dir: Path,
    condition: str,
    max_tool_calls: int = MAX_TOOL_CALLS,
    max_completion_tokens: int = MAX_COMPLETION_TOKENS,
    chat: Chat | None = None,
    thinking_budget: bool = True,
    collapse_reasoning: bool = False,
    should_stop: Callable[[], bool] | None = None,
    min_drafts: int = 0,
) -> dict[str, Any]:
    """Run one request to the end and return the summary that is also written to done.json.

    `chat` replaces the network call (a scripted model in the tests); by default it is
    `OpenAIChat(base_url, model, api_key)`. `should_stop` is asked before every model call and
    before every tool call (a write_protocol call is a check); when it says yes the episode
    ends with stop_reason `STOPPED_BY_USER`, the drafts so far judged as on any other end.
    `min_drafts` refuses a submit the checks reject until that many drafts were written
    (`Toolbox`; 0 as the evaluation ran, 3 in the product's live flow).
    """
    started = time.time()
    out_dir.mkdir(parents=True, exist_ok=True)
    platemap = json.loads(platemap_path.read_text(encoding="utf-8"))
    toolbox = Toolbox(platemap, runner, out_dir, min_drafts=min_drafts)
    ask: Chat = chat or OpenAIChat(base_url, model, api_key)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt(platemap, condition)},
        {"role": "user", "content": request["request"]},
    ]
    tool_calls = 0
    tokens_in = tokens_out = 0
    api_errors = idle_turns = turn = 0
    stop_reason: str | None = None
    with (
        (out_dir / "transcript.jsonl").open("w", encoding="utf-8") as transcript,
        (out_dir / "log.jsonl").open("w", encoding="utf-8") as log,
    ):
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
            turn_started = time.time()
            try:
                reply = ask(for_sending(messages, collapse_reasoning), SCHEMAS)
            except (OSError, ValueError, KeyError, IndexError, TypeError) as error:
                # URLError and HTTPError are OSErrors; a timeout is one too
                api_errors += 1
                row: dict[str, Any] = {"turn": turn, "api_error": describe_error(error)}
                transcript.write(json.dumps(row) + "\n")
                transcript.flush()
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
            cut_reasoning = message.get("reasoning") or message.get("reasoning_content") or ""
            if (
                reply.get("finish_reason") == "length"
                and cut_reasoning
                and not (message.get("tool_calls") or message.get("content"))
                and thinking_budget
            ):
                # The turn was all reasoning and ran out. Close the thought and let the model
                # finish the answer (NVIDIA's budget control; docs/harness-practices.md row 1).
                try:
                    reply = continue_after_cut(
                        (base_url, api_key),
                        model,
                        for_sending(messages, collapse_reasoning),
                        SCHEMAS,
                        cut_reasoning,
                        CONTINUE_TOKENS,
                    )
                except (OSError, ValueError, KeyError, IndexError, TypeError) as error:
                    transcript.write(
                        json.dumps({"turn": turn, "budget_error": describe_error(error)}) + "\n"
                    )
                else:
                    message = reply.get("message") or {}
                    more = reply.get("usage") or {}
                    tokens_in += int(more.get("prompt_tokens") or 0)
                    tokens_out += int(more.get("completion_tokens") or 0)
                    usage = {**usage, "continued": more}
            content = message.get("content") or ""
            calls = [c for c in (message.get("tool_calls") or []) if c.get("function")]
            assistant: dict[str, Any] = {"role": "assistant", "content": content}
            if message.get("reasoning"):
                # Echoed so the model builds on its own last thought (harness-practices, row 2).
                # Measured on run 4: the endpoint keeps every echoed turn's reasoning in the
                # prompt, which is most of the prompt by the tenth turn; `collapse_reasoning`
                # sends only the latest turn's (for_sending). The transcript keeps them all.
                assistant["reasoning"] = message["reasoning"]
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
                        {
                            "role": "tool",
                            "tool_call_id": call["id"],
                            "content": json.dumps(result),
                            "_tool": name,  # stripped before sending; used to collapse old reports
                        }
                    )
                    results.append({"name": name, "result": result})
                    if name == "submit" and toolbox.submitted:
                        stop_reason = "submitted"
                        break
            else:
                block = fenced_block(content)
                if block:
                    idle_turns = 0
                    result = toolbox.call("write_protocol", {"text": block})
                    tool_calls += 1
                    results.append({"name": "write_protocol (from a code block)", "result": result})
                    messages.append(
                        {
                            "role": "user",
                            "content": "You pasted the file as text instead of calling the "
                            f"write_protocol tool. I stored it anyway: {json.dumps(result)}. "
                            "From now on hand the file in with write_protocol, which checks "
                            "it for you.",
                        }
                    )
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
                                + "Use the tools: platemap, then write_protocol with the whole "
                                "file (it checks it), then submit.",
                            }
                        )
            row = {
                "turn": turn,
                "seconds": round(time.time() - turn_started, 1),
                "finish_reason": reply.get("finish_reason"),
                "assistant": {
                    "content": content,
                    "reasoning": message.get("reasoning") or message.get("reasoning_content"),
                    "budget_continued": bool(message.get("budget_continued")),
                    "tool_calls": [
                        {"id": c["id"], **c["function"]} for c in assistant.get("tool_calls", [])
                    ],
                },
                "tool_results": results,
                "usage": usage,
            }
            transcript.write(json.dumps(row) + "\n")
            transcript.flush()
            log.write(
                json.dumps(
                    {
                        "turn": turn,
                        "seconds": row["seconds"],
                        "usage": usage,
                        "tools": [r["name"] for r in results],
                    }
                )
                + "\n"
            )
            log.flush()
            turn += 1

    # The submitted draft, judged by the harness if the model never checked it.
    final_checks: dict[str, Any] | None = toolbox.last_checks
    checked_by_harness = False
    if toolbox.draft is not None and toolbox.checks_of_draft != toolbox.draft_number:
        final_checks = dict(runner.run_checks(toolbox.draft, platemap))
        final_checks["draft"] = toolbox.draft_number
        final_checks["by_harness"] = True
        checked_by_harness = True
        (out_dir / f"{toolbox.draft_number:02d}-checks.json").write_text(
            json.dumps(final_checks, indent=1), encoding="utf-8"
        )
    first_checks = toolbox.check_results[0] if toolbox.check_results else final_checks
    if final_checks is not None and final_checks.get("simulator") == "passed":
        _write_replay(out_dir / f"{toolbox.draft_number:02d}-draft.py", platemap_path, out_dir)
    summary: dict[str, Any] = {
        "id": request["id"],
        "condition": condition,
        "model": model,
        "runner": runner.name,
        "one_shot": _verdict(first_checks),
        "loop": {**_verdict(final_checks), "rounds": max(len(toolbox.check_results) - 1, 0)},
        "tool_calls": tool_calls,
        "turns": turn,
        "drafts": toolbox.draft_number + 1,
        "checks": len(toolbox.check_results),
        "submitted": toolbox.submitted,
        "submitted_clean": (
            toolbox.submitted and final_checks is not None and is_clean(final_checks)
        ),
        "final_draft_checked_by_harness": checked_by_harness,
        "stop_reason": stop_reason,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "seconds": round(time.time() - started, 1),
    }
    # Written whole then renamed into place: a reader that polls for done.json (the live
    # page's stream) never sees a half-written file.
    tmp = out_dir / "done.json.part"
    tmp.write_text(json.dumps(summary, indent=1), encoding="utf-8")
    tmp.replace(out_dir / "done.json")
    return summary


def _verdict(checks: Mapping[str, Any] | None) -> dict[str, Any]:
    if checks is None:
        return {"simulator": "never checked", "verify_exit": None, "check_exit": None,
                "findings": [], "draft": None}  # fmt: skip
    return {
        "simulator": checks.get("simulator"),
        "verify_exit": checks.get("verify_exit"),
        "check_exit": checks.get("check_exit"),
        "findings": [
            {k: f.get(k) for k in ("rule_id", "severity", "certain", "line", "title")}
            for f in checks.get("findings", [])
        ],
        "draft": checks.get("draft"),
    }


def _write_replay(draft: Path, platemap_path: Path, out_dir: Path) -> None:
    """Leave `replay.html` next to the episode: the deck replay of the final draft.

    A person opens it to watch what the protocol does; it is also what the demo shows. It is
    made after the episode, from the same trace `run_checks` used, and a failure to make it
    never fails the episode.
    """
    from provette.view.cli import build  # the view is optional at import time

    try:
        (out_dir / "replay.html").write_text(build(draft, platemap_path), encoding="utf-8")
    except Exception as error:  # noqa: BLE001 - a replay is a courtesy, not a result
        (out_dir / "replay.error.txt").write_text(
            f"The deck replay could not be made: {error}", encoding="utf-8"
        )


def for_sending(
    messages: list[dict[str, Any]], collapse_reasoning: bool = False
) -> list[dict[str, Any]]:
    """What the model is sent: every message, with the check reports older than the latest
    collapsed to one line (SWE-agent collapses observations older than the last few to a line;
    harness-practices, row 3), and, with `collapse_reasoning`, the reasoning of every assistant
    turn but the latest dropped. The transcript on disk keeps every report and thought in full."""
    latest = max(
        (i for i, m in enumerate(messages) if m.get("_tool") in ("write_protocol", "run_checks")),
        default=-1,
    )
    last_assistant = max(
        (i for i, m in enumerate(messages) if m.get("role") == "assistant"), default=-1
    )
    out = []
    for i, m in enumerate(messages):
        if "_tool" not in m:
            if collapse_reasoning and m.get("role") == "assistant" and i < last_assistant:
                m = {k: v for k, v in m.items() if k != "reasoning"}
            out.append(m)
            continue
        sent = {k: v for k, v in m.items() if k != "_tool"}
        if m["_tool"] in ("write_protocol", "run_checks") and i < latest:
            sent["content"] = json.dumps(_one_line(m["content"]))
        out.append(sent)
    return out


def _one_line(content: str) -> dict[str, Any]:
    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        return {"collapsed": content[:200]}
    checks = result.get("checks", result)
    return {
        "collapsed": "an earlier draft's checks, kept short",
        "draft": result.get("draft", checks.get("draft")),
        "simulator": checks.get("simulator"),
        "verify_exit": checks.get("verify_exit"),
        "check_exit": checks.get("check_exit"),
        "ready_to_submit": checks.get("ready_to_submit"),
    }
