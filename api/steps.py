"""The model's work as readable steps, from an episode's `transcript.jsonl`.

One step per tool call (and one per turn that called nothing), with a title a first-year
biology student can read: "looked up the labware: plates", "computed a 12-point 1:2 dilution
series", "draft 2: the simulator rejected line 31 (a hint was given)", "draft 3: verified 12 of
12 wells, no biology problems". The frontend renders the list generically, so **a new tool
needs one describer here and nothing else**: add it to DESCRIBERS, keyed by the tool's name; a
tool with no describer is shown as "called <name>" with its arguments, never hidden.

Every step:

    {"turn": int, "kind": "tool" | "text" | "error", "tool": str | None,
     "title": str, "detail": str, "status": "ok" | "rejected" | "problem" | "info",
     "draft": int | None, "seconds": float | None, "tokens_out": int | None,
     "reasoning_chars": int, "reasoning": str, "arguments": str, "cut": bool, "continued": bool}

`reasoning` is the model's own thinking before the call, clipped to 4,000 characters: the
page folds it under the step. `arguments` is what the model sent the tool, as JSON, clipped
to 1,200 characters (a protocol's text is long); "" for a turn that called nothing. `report`,
on a run_checks step, is the verdict text the model received, whole (clipped at 6,000).

`status` colours the row: "ok" for a check that passed or a tool that answered, "rejected" for a
draft the simulator threw out, "problem" for a draft the checks failed, "info" for the rest.
`cut` is true when the model's turn hit the token cap (finish_reason "length"); `continued` when
the harness let the reasoning go on past its budget and the turn still produced its call
(`budget_continued` on the assistant message, since run 4).
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from typing import Any

Step = dict[str, Any]
Describer = Callable[[Mapping[str, Any], Mapping[str, Any]], tuple[str, str, str]]
# (arguments, result) -> (title, detail, status)


def _clip(text: str, n: int = 220) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[: n - 1] + "…"


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def checks_sentence(result: Mapping[str, Any]) -> tuple[str, str, str]:
    """(title, detail, status) for a run_checks-shaped result: what the checks said of a draft."""
    draft = result.get("draft")
    head = f"Draft {draft}: " if draft is not None else ""
    if result.get("simulator") == "timeout":
        # a slow or busy server, not a verdict on the draft: said as such, never as a rejection
        return (
            f"{head}the checks did not finish in time",
            "The server was too slow to finish the checks; nothing in the draft was judged.",
            "info",
        )
    if result.get("simulator") == "rejected":
        error = str(result.get("simulator_error") or "")
        line = error.split(":", 1)[0] if error.startswith("line ") else ""
        where = f" at {line}" if line else ""
        title = f"{head}the simulator rejected the file{where}"
        detail = _clip(error.split(":", 1)[1] if line else error, 300)
        if result.get("hint"):
            title += " (a hint was given)"
        if result.get("stuck"):
            title += "; the same error three times"
        return title, detail, "rejected"
    verify_exit = result.get("verify_exit")
    check_exit = result.get("check_exit")
    findings = list(result.get("findings") or [])
    verify_report = str(result.get("verify_report") or result.get("verify_text") or "")
    first = verify_report.splitlines()[0] if verify_report else ""
    if "VERIFIED" in first and "wells hold" in first:
        wells = first.split("wells hold")[0].split(".")[-1].strip()
        plate = f"verified {wells} wells"
    elif "MISMATCH" in first or "does not" in first or "do not" in first:
        plate = "the plate does not match the plate map"
    elif "CANNOT CHECK" in first.upper():
        plate = "the plate map could not be checked"
    elif verify_exit == 0:
        plate = "verified against the plate map"
    elif verify_exit is None:
        plate = "the simulator passed"
    else:
        plate = "not verified against the plate map"
    if verify_exit == 1 and "verified" in plate:
        plate += ", with a flag"
    if findings:
        by: dict[str, int] = {}
        for f in findings:
            by[f.get("severity", "note")] = by.get(f.get("severity", "note"), 0) + 1
        parts = ", ".join(_plural(n, s) for s, n in by.items())
        biology = f"{_plural(len(findings), 'biology problem')} ({parts})"
    elif check_exit == 0:
        biology = "no biology problems"
    else:
        biology = ""
    title = f"{head}{plate}" + (f", {biology}" if biology else "")
    status = "ok" if verify_exit == 0 and check_exit == 0 else "problem"
    detail = _clip(str(result.get("verdict") or ""), 300)
    if findings and not detail:
        detail = _clip("; ".join(str(f.get("title", "")) for f in findings), 300)
    return title, detail, status


def _clip_reasoning(text: str, n: int = 4000) -> str:
    text = text.strip()
    return text if len(text) <= n else text[: n - 1] + "…"


def _propose(args: Mapping[str, Any], result: Mapping[str, Any]) -> tuple[str, str, str]:
    """The planner handed a map in (provette/planner/tools.py, propose_platemap)."""
    if result.get("error") or result.get("rejected"):
        return (
            "Proposed a plate map; the checks refused it",
            _clip(str(result.get("error") or result.get("rejected") or ""), 300),
            "rejected",
        )
    raw = result.get("platemap")
    platemap: Mapping[str, Any] = raw if isinstance(raw, Mapping) else {}
    liquids = [str(row.get("name", "")) for row in platemap.get("liquids") or []]
    detail = f"{_plural(len(liquids), 'liquid')}: " + ", ".join(liquids[:12]) if liquids else ""
    return "Proposed the plate map", _clip(detail, 300), "ok"


def _platemap(args: Mapping[str, Any], result: Mapping[str, Any]) -> tuple[str, str, str]:
    names = list(result.get("liquid_names") or [])
    detail = f"{_plural(len(names), 'liquid')}: " + ", ".join(names[:12])
    if len(names) > 12:
        detail += ", …"
    return "Read the plate map", detail, "ok"


def _labware(args: Mapping[str, Any], result: Mapping[str, Any]) -> tuple[str, str, str]:
    kind = str(args.get("kind") or result.get("kind") or "")
    names = [str(row.get("load_name", "")) for row in result.get("labware") or []]
    title = f"Looked up the labware: {kind}" if kind else "Looked up the labware"
    return title, _clip(", ".join(names), 300), "ok"


def _dilution(args: Mapping[str, Any], result: Mapping[str, Any]) -> tuple[str, str, str]:
    points = args.get("points") or len(result.get("wells") or [])
    factor = args.get("factor")
    volume = args.get("final_volume_ul")
    title = f"Computed a {points}-point 1:{factor} dilution series"
    if volume:
        title += f" at {volume} µl per well"
    wells = result.get("wells") or []
    detail = "; ".join(
        f"well {w.get('well')}: {w.get('step_1_add_diluent_ul')} µl diluent + "
        f"{w.get('step_2_transfer_in_ul')} µl from {w.get('from')}"
        for w in wells[:3]
    )
    return title, _clip(detail, 300), "ok"


def _normalise(args: Mapping[str, Any], result: Mapping[str, Any]) -> tuple[str, str, str]:
    n = len(args.get("concentrations") or result.get("samples") or [])
    target = args.get("target")
    title = f"Computed the normalisation volumes for {_plural(n, 'sample')}"
    if target:
        title += f" to {target}"
    return title, _clip(json.dumps(result)[:300], 300), "ok"


def _master_mix(args: Mapping[str, Any], result: Mapping[str, Any]) -> tuple[str, str, str]:
    reactions = result.get("reactions") or args.get("reactions")
    overage = result.get("overage_fraction", args.get("overage_fraction"))
    title = f"Computed the master mix for {reactions} reactions"
    if overage is not None:
        title += f" with {round(float(overage) * 100)}% extra"
    return title, _clip(str(result.get("how") or ""), 300), "ok"


def _write(args: Mapping[str, Any], result: Mapping[str, Any]) -> tuple[str, str, str]:
    draft = result.get("draft")
    lines = result.get("lines")
    if result.get("error") or not result.get("stored", True):
        return (
            f"Draft {draft}: the file did not parse"
            if draft is not None
            else "The draft did not parse",
            _clip(str(result.get("error") or result.get("syntax_error") or "")),
            "rejected",
        )
    title = f"Wrote draft {draft}" + (f" ({_plural(int(lines), 'line')})" if lines else "")
    fixes = result.get("repaired_before_checking")
    if isinstance(fixes, list) and fixes:
        # provette/agent/prelint.py: known slips repaired before the checks, and said so
        title += ", repaired before checking"
        return title, "Repaired before checking: " + "; ".join(str(f) for f in fixes), "info"
    return title, "", "info"


def _submit(args: Mapping[str, Any], result: Mapping[str, Any]) -> tuple[str, str, str]:
    draft = result.get("draft")
    clean = result.get("verified_and_clean_at_last_check")
    title = f"Submitted draft {draft}" if draft is not None else "Submitted"
    status = "ok" if clean else "problem"
    return title, _clip(str(result.get("note") or "")), status


DESCRIBERS: dict[str, Describer] = {
    "platemap": _platemap,
    "labware": _labware,
    "dilution_series": _dilution,
    "normalise": _normalise,
    "master_mix": _master_mix,
    "write_protocol": _write,
    "propose_platemap": _propose,
    "run_checks": lambda args, result: checks_sentence(result),
    "submit": _submit,
}


def _arguments(call: Mapping[str, Any]) -> dict[str, Any]:
    raw = call.get("arguments")
    if isinstance(raw, Mapping):
        return dict(raw)
    try:
        parsed = json.loads(raw) if isinstance(raw, str) else {}
    except json.JSONDecodeError:
        return {"_raw": str(raw)[:200]}
    return parsed if isinstance(parsed, dict) else {}


def describe(name: str, args: Mapping[str, Any], result: Mapping[str, Any]) -> tuple[str, str, str]:
    if "error" in result and name not in ("write_protocol",):
        return (
            f"Called {name}, which answered with an error",
            _clip(str(result["error"]), 300),
            "problem",
        )
    describer = DESCRIBERS.get(name)
    if describer is None:
        return f"Called {name}", _clip(json.dumps(args), 300), "info"
    return describer(args, result)


def steps_from_transcript(turns: Sequence[Mapping[str, Any]]) -> list[Step]:
    steps: list[Step] = []
    for turn in turns:
        n = int(turn.get("turn", len(steps)))
        if "api_error" in turn:
            steps.append(
                {
                    "turn": n,
                    "kind": "error",
                    "tool": None,
                    "title": "The model's API returned an error; the loop waited and retried",
                    "detail": _clip(str(turn["api_error"]), 300),
                    "status": "problem",
                    "draft": None,
                    "seconds": turn.get("seconds"),
                    "tokens_out": None,
                    "reasoning_chars": 0,
                    "reasoning": "",
                    "arguments": "",
                    "cut": False,
                    "continued": False,
                }
            )
            continue
        assistant = turn.get("assistant") or {}
        usage = turn.get("usage") or {}
        common = {
            "turn": n,
            "seconds": turn.get("seconds"),
            "tokens_out": usage.get("completion_tokens"),
            "reasoning_chars": len(assistant.get("reasoning") or ""),
            "reasoning": _clip_reasoning(str(assistant.get("reasoning") or "")),
            "arguments": "",
            "cut": turn.get("finish_reason") == "length",
            "continued": bool(assistant.get("budget_continued")),
        }
        calls = list(assistant.get("tool_calls") or [])
        results = list(turn.get("tool_results") or [])
        if not calls and not results:
            content = str(assistant.get("content") or "")
            if content.strip():
                title = "Wrote a message instead of calling a tool"
                status = "info"
            elif common["cut"]:
                title = "The turn was cut at the token cap before the model produced anything"
                status = "problem"
            else:
                title = "An empty turn"
                status = "info"
            steps.append(
                {
                    **common,
                    "kind": "text",
                    "tool": None,
                    "title": title,
                    "detail": _clip(content, 300),
                    "status": status,
                    "draft": None,
                }
            )
            continue
        for i, call in enumerate(calls or [{"name": r.get("name")} for r in results]):
            name = str(call.get("name") or "")
            result_row = results[i] if i < len(results) else {}
            result = result_row.get("result") if isinstance(result_row, Mapping) else None
            result = result if isinstance(result, Mapping) else {}
            args = _arguments(call)
            title, detail, status = describe(name, args, result)
            draft = result.get("draft")
            step: Step = {
                **common,
                "arguments": _clip_reasoning(json.dumps(args, ensure_ascii=False), 1200),
                "report": _clip_reasoning(str(result.get("verdict") or ""), 6000)
                if name == "run_checks"
                else "",
                "kind": "tool",
                "tool": name,
                "title": title,
                "detail": detail,
                "status": status,
                "draft": int(draft) if isinstance(draft, int) else None,
            }
            steps.append(step)
            # write_protocol runs the checks itself and returns them under
            # `checks`: show them as the step they are, right after the draft.
            checks = result.get("checks")
            if isinstance(checks, Mapping):
                c_title, c_detail, c_status = checks_sentence(checks)
                steps.append(
                    {
                        **common,
                        "arguments": "",
                        "report": _clip_reasoning(str(checks.get("verdict") or ""), 6000),
                        "kind": "tool",
                        "tool": "run_checks",
                        "title": c_title,
                        "detail": c_detail,
                        "status": c_status,
                        "draft": checks.get("draft", step["draft"]),
                    }
                )
    return steps
