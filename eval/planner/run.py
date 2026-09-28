"""The planner: can the model propose the plate map, and does the map it proposes hold up?

For each of the 17 requests that have a hand-written plate map (`eval/platemaps/`), the
planner (`provette.planner`) proposes one from the request text alone, and the proposal is held
against two things:

1. the hand-written map, structurally (`provette.planner.agree`): does it validate; are the
   logical liquids and their roles the same; does every expected well hold the same amounts,
   within `tolerance_ul`; are the same positions pinned and the same constraints on the free
   ones;
2. the correct protocol that verifies against the hand-written map
   (`eval/checks/protocols/plain/<id>.py`): `provette verify` with the PLANNED map. A planned map
   that is right verifies it too; one that is wrong does not.

It plans as the product does (`allow_decline`): a real request the planner calls "not a request"
is counted, so the run also says how often that happens.

    set -a; . ~/.config/provette/token-factory.env; set +a
    env -u PYTHONPATH uv run python eval/planner/run.py --model nvidia/nemotron-3-super-120b-a12b \\
        --out eval/planner/results/super --ids pcr-01 dil-01

Everything is written under --out/<id>.json (the planned map, the transcript, the agreement,
the verify report, the token counts and the cost at list price); a request with a result is
skipped unless --force. The planned map alone goes to --out/<id>.platemap.json, so
`provette verify` can be run on it by hand. Prices as eval/agent/tabulate.py lists them.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from provette.intent.cli import verify
from provette.intent.report import report_text
from provette.intent.spec import dump_platemap, platemap_from_dict
from provette.planner import DEFAULT_MODEL, plan
from provette.planner.agree import agree
from provette.trace import TraceError

ROOT = Path(__file__).resolve().parents[2]
REQUESTS = ROOT / "eval" / "requests" / "requests.jsonl"
PLATEMAPS = ROOT / "eval" / "platemaps"
PILOT = ROOT / "eval" / "checks" / "protocols" / "plain"
PRICES = {  # substring of the model id -> (prompt, completion) USD per 1M tokens
    "ltra": (1.0, 3.0),
    "uper": (0.3, 0.9),
    "ano": (0.06, 0.24),
}


def price_for(model: str) -> tuple[float, float]:
    return next((price for key, price in PRICES.items() if key in model), (0.0, 0.0))


def requests_with_maps() -> dict[str, dict[str, Any]]:
    """id -> the request row (`request`, `technique`) for every request with a hand-written map."""
    rows = [json.loads(line) for line in REQUESTS.read_text(encoding="utf-8").splitlines() if line]
    return {r["id"]: r for r in rows if (PLATEMAPS / f"{r['id']}.json").exists()}


def run_one(request_id: str, row_in: dict[str, Any], model: str, base_url: str, api_key: str,
            out: Path) -> dict[str, Any]:  # fmt: skip
    request = row_in["request"]
    result = plan(
        request,
        model,
        base_url,
        api_key,
        request_id=request_id,
        technique=row_in.get("technique"),
        allow_decline=True,
    )
    prompt_price, completion_price = price_for(model)
    row: dict[str, Any] = {
        "id": request_id,
        "model": model,
        "stop_reason": result.stop_reason,
        "declined": result.declined,
        "tool_calls": result.tool_calls,
        "turns": result.turns,
        "tokens_in": result.tokens_in,
        "tokens_out": result.tokens_out,
        "cost_usd": round(
            result.tokens_in * prompt_price / 1e6 + result.tokens_out * completion_price / 1e6, 4
        ),
        "seconds": result.seconds,
        "rejections": result.rejections,
        "repairs": result.repairs,
        "error": result.error,
        "planned": None,
        "agreement": None,
        "verify": None,
        "transcript": result.transcript,
    }
    if result.platemap is None:
        return row
    row["planned"] = dump_platemap(result.platemap)
    (out / f"{request_id}.platemap.json").write_text(
        json.dumps(row["planned"], indent=1) + "\n", encoding="utf-8"
    )
    return score(row)


def score(row: dict[str, Any]) -> dict[str, Any]:
    """Hold the planned map against the hand-written one and the correct protocol (no network)."""
    if row["planned"] is None:
        return row
    request_id = row["id"]
    planned = platemap_from_dict(row["planned"])
    reference = platemap_from_dict(json.loads((PLATEMAPS / f"{request_id}.json").read_text()))
    row["agreement"] = agree(planned, reference)
    try:
        verification = verify(PILOT / f"{request_id}.py", planned)
        row["verify"] = {"exit": verification.exit_code, "text": report_text(verification)}
    except TraceError as error:
        row["verify"] = {"exit": 2, "text": f"simulator rejected the protocol: {error}"}
    return row


def table(rows: list[dict[str, Any]]) -> str:
    def yes(value: Any) -> str:
        return "yes" if value else "NO"

    lines = [
        "| id | valid | liquids | amounts | positions | verify | calls | tokens out | $ |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        a = r.get("agreement")
        v = r.get("verify")
        lines.append(
            f"| {r['id']} | {yes(r['planned'])} | "
            + (f"{yes(a['liquids']['agree'])} | {yes(a['amounts']['agree'])} | "
               f"{yes(a['positions']['agree'])} | " if a else "- | - | - | ")
            + (f"exit {v['exit']} | " if v else "- | ")
            + f"{r['tool_calls']} | {r['tokens_out']} | {r['cost_usd']:.3f} |"
        )  # fmt: skip
    n = len(rows)
    valid = sum(1 for r in rows if r["planned"])
    agree_all = sum(1 for r in rows if r.get("agreement") and r["agreement"]["agree"])
    verified = sum(1 for r in rows if r.get("verify") and r["verify"]["exit"] == 0)
    cost = sum(r["cost_usd"] for r in rows)
    lines.append(
        f"\n{valid} of {n} valid; {agree_all} of {n} agree with the hand-written map on liquids, "
        f"amounts and positions; {verified} of {n} planned maps verify the correct protocol; "
        f"${cost:.2f} in all, ${cost / max(n, 1):.3f} per plan."
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--base-url", default=os.environ.get("PROVETTE_BASE_URL", ""))
    parser.add_argument("--out", type=Path, default=ROOT / "eval" / "planner" / "results" / "super")
    parser.add_argument("--ids", nargs="*", help="which requests (default: all 17)")
    parser.add_argument("--force", action="store_true", help="re-plan requests that have a result")
    parser.add_argument(
        "--rescore",
        action="store_true",
        help="recompute the agreement and the verify result from the stored maps; no network",
    )
    args = parser.parse_args()
    if not args.base_url and not args.rescore:
        print("No endpoint: pass --base-url or set PROVETTE_BASE_URL.", file=sys.stderr)
        return 2
    api_key = os.environ.get("PROVETTE_API_KEY", "")
    requests = requests_with_maps()
    ids = args.ids or list(requests)
    args.out.mkdir(parents=True, exist_ok=True)
    rows = []
    for request_id in ids:
        path = args.out / f"{request_id}.json"
        if path.exists() and args.rescore:
            row = score(json.loads(path.read_text(encoding="utf-8")))
            path.write_text(json.dumps(row, indent=1) + "\n", encoding="utf-8")
            rows.append(row)
            continue
        if path.exists() and not args.force:
            rows.append(json.loads(path.read_text(encoding="utf-8")))
            continue
        row = run_one(request_id, requests[request_id], args.model, args.base_url, api_key,
                      args.out)  # fmt: skip
        path.write_text(json.dumps(row, indent=1) + "\n", encoding="utf-8")
        rows.append(row)
        a, v = row["agreement"], row["verify"]
        outcome = f"agree {a['agree']}; verify exit {v['exit']}" if a and v else str(row["error"])
        print(
            f"{request_id}: {row['stop_reason']}, {row['tool_calls']} calls, "
            f"{row['tokens_out']} tokens out, ${row['cost_usd']:.3f}; {outcome}",
            flush=True,
        )
    text = table(rows)
    print("\n" + text)
    (args.out / "summary.md").write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
