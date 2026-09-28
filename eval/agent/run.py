"""The agent runs: a model writes each protocol with tools, checks it, repairs it, submits.

The requests with a plate map, in the conditions given; the model works through
`provette.agent.loop.run_episode` with the product's settings (`api/run_settings.py`): it reads
the plate map, gets the labware names and the arithmetic from tools, hands in drafts, runs the
checks itself and decides when to submit. The checks run through a runner: `--runner local`
is this machine; `--runner sandbox` is a Nebius Token Factory Sandbox (`provette.sandbox`).

    set -a; . ~/.config/provette/token-factory.env; set +a
    env -u PYTHONPATH uv run python eval/agent/run.py \\
        --model nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B --out eval/agent/results/nano \\
        --conditions plain --ids pcr-01 dil-01 norm-01

Everything is written under --out/<condition>/<id>/; a request with a done.json is skipped
unless --force. `eval/agent/tabulate.py` reads the results unchanged.
"""

from __future__ import annotations

import argparse
import functools
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from http.client import IncompleteRead, RemoteDisconnected
from pathlib import Path
from typing import Any

from provette.agent.loop import MAX_COMPLETION_TOKENS, MAX_TOOL_CALLS, MIN_DRAFTS, run_episode
from provette.agent.runner import Runner

ROOT = Path(__file__).resolve().parents[2]
REQUESTS = ROOT / "eval" / "requests"
PLATEMAPS = ROOT / "eval" / "platemaps"


def make_runner(name: str) -> Runner:
    if name == "local":
        from provette.agent.local_runner import LocalRunner

        return LocalRunner()
    if name == "sandbox":
        from provette.sandbox import make_runner as sandbox_runner  # a Token Factory Sandbox

        return sandbox_runner("nebius")
    raise SystemExit(f"unknown runner {name!r}")


def verified(summary: dict[str, Any]) -> bool:
    loop = summary["loop"]
    return (
        loop.get("simulator") == "passed"
        and loop.get("verify_exit") == 0
        and loop.get("check_exit") == 0
    )


def best_of(episode: Any, out: Path, n: int) -> dict[str, Any]:
    """Run `n` episodes of the same request at once and keep the one the checks accept.

    The verifier is the judge: the first candidate that ends verified and clean is chosen;
    failing that, the one whose last checks got furthest. `done.json` at `out` is the chosen
    candidate's summary plus every candidate's verdict and the tokens of all of them, so the
    cost of the request is the cost of all n episodes, never of the winner alone.
    """
    out.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=n) as pool:
        runs = list(pool.map(lambda k: episode(out_dir=out / f"candidate-{k}"), range(n)))

    def rank(s: dict[str, Any]) -> tuple[int, int, int]:
        loop = s["loop"]
        return (
            int(verified(s)),
            int(loop.get("simulator") == "passed"),
            -int(loop.get("verify_exit") or 9) - int(loop.get("check_exit") or 9),
        )

    chosen = max(range(n), key=lambda k: rank(runs[k]))
    summary = dict(runs[chosen])
    summary["candidates"] = [
        {
            "dir": f"candidate-{k}",
            "verified": verified(s),
            "stop_reason": s.get("stop_reason"),
            "tokens_in": s.get("tokens_in", 0),
            "tokens_out": s.get("tokens_out", 0),
        }
        for k, s in enumerate(runs)
    ]
    summary["chosen"] = f"candidate-{chosen}"
    summary["tokens_in"] = sum(s.get("tokens_in", 0) for s in runs)
    summary["tokens_out"] = sum(s.get("tokens_out", 0) for s in runs)
    (out / "done.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.environ.get("PROVETTE_BASE_URL"))
    parser.add_argument("--model", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--conditions", nargs="+", default=["plain", "short-on-tips"])
    parser.add_argument("--ids", nargs="*")
    parser.add_argument("--runner", choices=["local", "sandbox"], default="local")
    parser.add_argument("--max-tool-calls", type=int, default=MAX_TOOL_CALLS)
    parser.add_argument("--max-completion-tokens", type=int, default=MAX_COMPLETION_TOKENS)
    parser.add_argument("--min-drafts", type=int, default=MIN_DRAFTS)
    parser.add_argument(
        "--candidates",
        type=int,
        default=1,
        help="run this many episodes at once and keep the one the checks accept (best-of-N)",
    )
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--collapse-reasoning",
        action="store_true",
        help="send the model only its latest turn's reasoning, not every earlier turn's",
    )
    parser.add_argument("--requests", type=Path, default=REQUESTS, help="dir with requests.jsonl")
    parser.add_argument("--platemaps", type=Path, default=PLATEMAPS, help="dir with <id>.json maps")
    args = parser.parse_args()
    if not args.base_url:
        raise SystemExit("--base-url, or PROVETTE_BASE_URL in the environment")
    api_key = os.environ.get("PROVETTE_API_KEY", "")
    requests = [
        json.loads(line)
        for line in (args.requests / "requests.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    runner = make_runner(args.runner)
    try:
        for condition in args.conditions:
            for request in requests:
                platemap = args.platemaps / f"{request['id']}.json"
                if not platemap.exists() or (args.ids and request["id"] not in args.ids):
                    continue
                out = Path(args.out) / condition / request["id"]
                if (out / "done.json").exists() and not args.force:
                    continue
                episode = functools.partial(
                    run_episode,
                    request,
                    platemap,
                    runner,
                    args.model,
                    args.base_url,
                    api_key,
                    condition=condition,
                    max_tool_calls=args.max_tool_calls,
                    max_completion_tokens=args.max_completion_tokens,
                    min_drafts=args.min_drafts,
                    collapse_reasoning=args.collapse_reasoning,
                )
                try:
                    for attempt in range(3):  # a dropped connection is retried, not recorded
                        try:
                            if args.candidates > 1:
                                s = best_of(episode, out, args.candidates)
                            else:
                                s = episode(out_dir=out)
                            break
                        except (OSError, IncompleteRead, RemoteDisconnected) as error:
                            if attempt == 2:
                                raise
                            print(f"{condition:14} {request['id']:10} retry: {error!r}", flush=True)
                            time.sleep(30)
                except Exception as error:  # one bad request must not end the run
                    print(f"{condition:14} {request['id']:10} FAILED: {error!r}", flush=True)
                    continue
                one, loop = s["one_shot"], s["loop"]
                print(
                    f"{condition:14} {request['id']:10} first sim={one['simulator']:8} "
                    f"verify={one['verify_exit']} check={one['check_exit']}   "
                    f"last verify={loop['verify_exit']} check={loop['check_exit']}   "
                    f"calls={s['tool_calls']} drafts={s['drafts']} "
                    f"{'submitted' if s['submitted'] else s['stop_reason']}"
                    f"{' CLEAN' if s['submitted_clean'] else ''}  "
                    f"tokens {s['tokens_in']}/{s['tokens_out']}",
                    flush=True,
                )
    finally:
        runner.close()


if __name__ == "__main__":
    main()
