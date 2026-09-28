"""The baseline: a model writing protocols without the checks in its loop.

For every request that has a plate map, in each condition, the model writes a protocol:

  1. one shot, with the simulator's errors fed back (up to SIM_TRIES): the simulator-only baseline;
  2. then `provette verify` and `provette check` judge what it wrote;
  3. then the verifier in the loop: both reports are fed back, up to LOOP_ROUNDS.

The model is reached over the OpenAI chat API, which Ollama and Nebius Token Factory both serve,
so the model is two values: --base-url and --model (and PROVETTE_API_KEY in the environment if the
server wants one). Everything is written under --out: every protocol of every round, the reports,
and one JSON line per step in log.jsonl. Nothing here decides whether a finding is real: a person
reads the failures afterwards.

    set -a; . ~/.config/provette/token-factory.env; set +a
    env -u PYTHONPATH uv run python eval/baseline/run.py \
        --model nvidia/nemotron-3-super-120b-a12b --rules-in-prompt --one-shot-only \
        --out eval/baseline/results/super-rules-in-prompt

The baseline "the rules as text, no checker" (eval/baseline/README.md): `--rules-in-prompt` puts
every rule the checker grades by into the system prompt, in words, and `--one-shot-only` skips
the repair rounds, so the one-shot verdict is the whole result. The draft is still graded by
`provette verify` and `provette check`, exactly as the loop runs are.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

from provette.intent.labware import RULE_ID as LABWARE_RULE_ID
from provette.rules import RULES

ROOT = Path(__file__).resolve().parents[2]
REQUESTS = ROOT / "eval" / "requests"
PLATEMAPS = ROOT / "eval" / "platemaps"
SIM_TRIES = 3
LOOP_ROUNDS = 5
TIPS_LINE = "- We are short on tip racks this month: use as few tips as possible."


def liquid_names(platemap: dict[str, Any]) -> list[str]:
    """Names the writer must give its liquids, so that the plate map can find them."""
    names: list[str] = []
    for liquid in platemap["liquids"]:
        if liquid["bind"] == "indexed":
            stem = liquid["name"].split("_")[
                0
            ]  # "sample_{i}" -> "sample", "colony_{i}" -> "colony"
            word = next(
                (w for w in (stem, "sample") if re.search(liquid["pattern"], f"{w} 1")), None
            )
            if word is None:
                raise SystemExit(f"{platemap['id']}: no name fits {liquid['pattern']}")
            names += [f"{word} {i}" for i in range(1, liquid["count"] + 1)]
        elif liquid["bind"] == "name":
            names.append(liquid["name"].replace("_", " "))
    for liquid, name in zip(
        [x for x in platemap["liquids"] if x["bind"] == "name"],
        [n for n in names if not re.fullmatch(r"[a-z]+ \d+", n)],
        strict=False,
    ):
        if not re.search(liquid["pattern"], name):
            where, pattern = platemap["id"], liquid["pattern"]
            raise SystemExit(f"{where}: the name {name!r} does not match {pattern}")
    return names


def prompt_for(request: dict[str, str], platemap: dict[str, Any], condition: str) -> str:
    preamble = (REQUESTS / "preamble.md").read_text(encoding="utf-8").rstrip()
    if condition == "short-on-tips":
        preamble = preamble.replace("- Output only", TIPS_LINE + "\n- Output only")
    names = ", ".join(f'"{n}"' for n in liquid_names(platemap))
    naming = (
        f"- Name the liquids exactly like this in define_liquid: {names}. "
        "Any other liquid you need may have any name."
    )
    preamble = preamble.replace("- The protocol must pass", naming + "\n- The protocol must pass")
    reference = (REQUESTS / "reference.md").read_text(encoding="utf-8").rstrip()
    return f"{reference}\n\n{preamble}\n{request['request']}\n"


SYSTEM = "You are a helpful assistant."  # what NVIDIA's model card and cookbook use

# The twelfth check is not in RULES: it runs inside `provette verify`, because it needs the plate
# map's technique (provette/intent/labware.py). Its words here follow the row in
# provette/rules/README.md; the eleven others are read from RULES at run time.
LABWARE_RULE_LINE = (
    f"- The destination is the wrong kind of plate for the technique ({LABWARE_RULE_ID}): "
    "PCR setup, qPCR setup, cloning, transformation and gel samples need a PCR plate or PCR "
    "strips; ELISA, Bradford, protein and cell assays and cell culture need a flat or deep-well "
    "plate. An enzyme, polymerase, ligase or master mix for PCR-class work belongs in a tube, "
    "not in a reservoir channel."
)
NO_CHECKER_LINE = "Nothing will check the draft for you; satisfy every rule yourself."


def rules_section() -> str:
    """The rules the checker grades by, as text: what `--rules-in-prompt` adds to the system prompt.

    Every rule in RULES as "- <title>: <description>", plus the verify-side labware check, so the
    model is told the twelve as they stand. The sentence at the end is the point of the baseline:
    the model is told the rules and gets no report.
    """
    # a proposed rule is not a requirement yet (provette/rules/README.md, "Declared rules")
    lines = [f"- {r.title}: {r.description}" for r in RULES if r.status == "adopted"]
    lines.append(LABWARE_RULE_LINE)
    return "Rules this protocol must satisfy\n\n" + "\n".join(lines) + "\n\n" + NO_CHECKER_LINE


def system_prompt(rules_in_prompt: bool) -> str:
    return SYSTEM + ("\n\n" + rules_section() if rules_in_prompt else "")


def chat(
    base_url: str, model: str, messages: list[dict[str, str]], thinking: str, system: str = SYSTEM
) -> tuple[str, dict[str, Any]]:
    """One chat completion, with the sampling NVIDIA recommends for Nemotron 3.

    Reasoning on: temperature 1.0, top_p 1.0, a large max_tokens (the model card says 10,000 or
    more). Reasoning off: greedy. The reasoning trace comes back in a separate field on Token
    Factory and inside <think> tags on Ollama; either way `content` is the answer.
    """
    request: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "system", "content": system}, *messages],
    }
    if thinking == "off":
        request.update(temperature=0.0, max_tokens=12000)
        request["chat_template_kwargs"] = {"enable_thinking": False}
    else:
        request.update(temperature=1.0, top_p=1.0, max_tokens=24000)
    body = json.dumps(request).encode()
    headers = {"Content-Type": "application/json"}
    if os.environ.get("PROVETTE_API_KEY"):
        headers["Authorization"] = "Bearer " + os.environ["PROVETTE_API_KEY"]
    request = urllib.request.Request(base_url.rstrip("/") + "/chat/completions", body, headers)
    with urllib.request.urlopen(request, timeout=1800) as response:
        reply = json.loads(response.read())
    return reply["choices"][0]["message"].get("content") or "", reply.get("usage", {})


def code_from(reply: str) -> str:
    """The Python file in a reply: reasoning blocks dropped, the longest fenced block kept."""
    reply = re.sub(r"<think>.*?</think>", "", reply, flags=re.S)
    blocks = re.findall(r"```(?:python|py)?\s*\n(.*?)```", reply, flags=re.S)
    return (max(blocks, key=len) if blocks else reply).strip() + "\n"


def provette(*args: str) -> tuple[int, str]:
    done = subprocess.run(
        [sys.executable, "-m", "provette.cli", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=600,
        env={k: v for k, v in os.environ.items() if k != "PYTHONPATH"},
    )
    # paths relative to the repository, so a traceback in the report names no one's machine
    return done.returncode, (done.stdout + done.stderr).strip().replace(f"{ROOT}/", "")


def judge(protocol: Path, platemap: Path) -> dict[str, Any]:
    verify_exit, verify_text = provette("verify", str(protocol), "--platemap", str(platemap))
    if verify_exit == 2:
        return {"simulator": "rejected", "verify_exit": 2, "verify_text": verify_text}
    check_exit, check_text = provette("check", str(protocol))
    _, check_json = provette("check", str(protocol), "--json")
    try:
        findings = json.loads(check_json)["findings"]
    except (json.JSONDecodeError, KeyError):
        findings = []
    return {
        "simulator": "passed",
        "verify_exit": verify_exit,  # 0 verified, 1 mismatch or flag, 3 cannot check
        "verify_text": verify_text,
        "check_exit": check_exit,  # 0 clean, 1 an error or a warning
        "check_text": check_text,
        "findings": [
            {k: f[k] for k in ("rule_id", "severity", "certain", "line", "title")} for f in findings
        ],
    }


def run_one(
    args: argparse.Namespace, request: dict[str, str], platemap_path: Path, condition: str
) -> None:
    out = Path(args.out) / condition / request["id"]
    if (out / "done.json").exists() and not args.force:
        return
    out.mkdir(parents=True, exist_ok=True)
    platemap = json.loads(platemap_path.read_text(encoding="utf-8"))
    messages = [{"role": "user", "content": prompt_for(request, platemap, condition)}]
    log = (out / "log.jsonl").open("w", encoding="utf-8")
    summary: dict[str, Any] = {
        "id": request["id"],
        "condition": condition,
        "model": args.model,
        "thinking": args.thinking,
        "rules_in_prompt": args.rules_in_prompt,
        "one_shot_only": args.one_shot_only,
    }
    system = system_prompt(args.rules_in_prompt)
    verdict: dict[str, Any] = {}
    step = 0

    def write(phase: str) -> dict[str, Any]:
        nonlocal step
        started = time.time()
        reply, usage = chat(args.base_url, args.model, messages, args.thinking, system)
        protocol = out / f"{step:02d}-{phase}.py"
        protocol.write_text(code_from(reply), encoding="utf-8")
        messages.append({"role": "assistant", "content": "```python\n" + code_from(reply) + "```"})
        result = judge(protocol, platemap_path)
        row = {"step": step, "phase": phase, "seconds": round(time.time() - started, 1)}
        log.write(json.dumps({**row, "usage": usage, **result}) + "\n")
        log.flush()
        step += 1
        return result

    # 1. the simulator-only baseline
    for _ in range(SIM_TRIES):
        verdict = write("one-shot")
        if verdict["simulator"] == "passed":
            break
        messages.append(
            {
                "role": "user",
                "content": "opentrons_simulate rejected the protocol:\n\n"
                + verdict["verify_text"][-3000:]
                + "\n\nFix it and output the whole Python file again.",
            }
        )
    summary["one_shot"] = {k: verdict.get(k) for k in ("simulator", "verify_exit", "check_exit")}
    summary["one_shot"]["findings"] = verdict.get("findings", [])
    summary["one_shot"]["steps"] = step

    # 2. the verifier in the loop. With --one-shot-only there are no rounds, and `loop` repeats
    # the one-shot verdict, so tabulate.py's "verified in the end" is the one-shot count.
    rounds = 0
    while (
        not args.one_shot_only
        and rounds < LOOP_ROUNDS
        and summary["one_shot"]["simulator"] == "passed"
        and (
            verdict["simulator"] != "passed"
            or verdict["verify_exit"] != 0
            or verdict["check_exit"] != 0
        )
    ):
        if verdict["simulator"] != "passed":
            messages.append(
                {
                    "role": "user",
                    "content": "opentrons_simulate rejected the protocol:\n\n"
                    + verdict["verify_text"][-3000:]
                    + "\n\nFix it and output the whole Python file again.",
                }
            )
            verdict = write("loop")
            rounds += 1
            continue
        feedback = "A checker replayed the protocol and followed every liquid.\n\n"
        if verdict["verify_exit"] != 0:
            feedback += "Against the plate map:\n" + verdict["verify_text"][:5000] + "\n\n"
        if verdict["check_exit"] != 0:
            feedback += "Biology problems:\n" + verdict["check_text"][:5000] + "\n\n"
        feedback += "Fix the protocol and output the whole Python file again."
        messages.append({"role": "user", "content": feedback})
        verdict = write("loop")
        rounds += 1
    summary["loop"] = {k: verdict.get(k) for k in ("simulator", "verify_exit", "check_exit")}
    summary["loop"]["findings"] = verdict.get("findings", [])
    summary["loop"]["rounds"] = rounds
    (out / "done.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    log.close()
    one, loop = summary["one_shot"], summary["loop"]
    print(
        f"{condition:14} {request['id']:10} one-shot sim={one['simulator']:8} "
        f"verify={one['verify_exit']} check={one['check_exit']}   "
        f"loop({rounds}) verify={loop['verify_exit']} check={loop['check_exit']}",
        flush=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.environ.get("PROVETTE_BASE_URL"))
    parser.add_argument("--model", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--conditions", nargs="+", default=["plain", "short-on-tips"])
    parser.add_argument("--ids", nargs="*")
    parser.add_argument("--thinking", choices=["on", "off"], default="on")
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--rules-in-prompt",
        action="store_true",
        help="put the rules the checker grades by into the system prompt, in words",
    )
    parser.add_argument(
        "--one-shot-only",
        action="store_true",
        help="skip the repair rounds: the one-shot verdict is the result",
    )
    args = parser.parse_args()
    requests = [
        json.loads(line)
        for line in (REQUESTS / "requests.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    for condition in args.conditions:
        for request in requests:
            platemap = PLATEMAPS / f"{request['id']}.json"
            if platemap.exists() and (not args.ids or request["id"] in args.ids):
                try:
                    run_one(args, request, platemap, condition)
                except Exception as error:  # one bad request must not end the run
                    print(f"{condition:14} {request['id']:10} FAILED: {error!r}", flush=True)


if __name__ == "__main__":
    main()
