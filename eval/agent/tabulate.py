"""Tabulate one or more result directories: the funnel, the repair rate, tokens and dollars.

    env -u PYTHONPATH uv run python eval/agent/tabulate.py eval/baseline/results/*

Prices come from eval/prices.json, as Token Factory listed them; local runs cost nothing and are
shown at the hosted price of the same family for comparison, marked with "~".
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PRICES_FILE = Path(__file__).resolve().parents[1] / "prices.json"


def price_for(model: str) -> tuple[float, float]:
    """(prompt, completion) USD per million tokens, from eval/prices.json; a local Ollama tag is
    priced as the hosted model of the same family, for comparison only."""
    prices = json.loads(PRICES_FILE.read_text())["models"]
    key = model
    if model not in prices:
        wanted = "nano" if "nano" in model.lower() else "super" if "super" in model.lower() else ""
        key = next((k for k in prices if wanted and wanted in k.lower()), "")
    if key not in prices:
        return (0.0, 0.0)
    return (prices[key]["input_per_million_usd"], prices[key]["output_per_million_usd"])


def tabulate(root: Path) -> None:
    rows = [json.loads(p.read_text()) for p in sorted(root.glob("*/*/done.json"))]
    if not rows:
        return
    model = rows[0]["model"]
    local = "local" in root.name
    prompt_price, completion_price = price_for(model)
    tokens_in = tokens_out = 0
    if all("tokens_in" in r for r in rows):
        # the tool-calling agent sums its own tokens (a best-of-N episode sums its candidates)
        tokens_in = sum(r["tokens_in"] for r in rows)
        tokens_out = sum(r["tokens_out"] for r in rows)
    else:
        for p in sorted(root.glob("*/*/log.jsonl")):
            for line in p.read_text().splitlines():
                usage = json.loads(line).get("usage", {})
                tokens_in += usage.get("prompt_tokens", 0)
                tokens_out += usage.get("completion_tokens", 0)
    dollars = tokens_in * prompt_price / 1e6 + tokens_out * completion_price / 1e6
    sim = [r for r in rows if r["one_shot"]["simulator"] == "passed"]
    clean = [
        r for r in sim if r["one_shot"]["verify_exit"] == 0 and r["one_shot"]["check_exit"] == 0
    ]
    problem = [r for r in sim if r not in clean]
    # Verified at the end: the last checked draft passed everything. In the message loop that
    # can only follow a simulator-passing first draft; the tool-calling agent also repairs
    # first drafts the simulator rejected, so count from the end, not from the funnel.
    final_clean = [
        r
        for r in rows
        if r["loop"]["simulator"] == "passed"
        and r["loop"]["verify_exit"] == 0
        and r["loop"]["check_exit"] == 0
    ]
    repaired = [r for r in final_clean if r not in clean]
    end_clean = len(final_clean)
    print(f"{root.name}  ({model})")
    print(
        f"  requests {len(rows)}; pass the simulator {len(sim)}; clean one-shot {len(clean)}, "
        f"a problem {len(problem)}; repaired by the loop {len(repaired)} "
        f"(of {len(problem) + (len(rows) - len(sim))} that were not clean at first)"
    )
    print(
        f"  end-to-end verified and clean: {end_clean} of {len(rows)} "
        f"({100 * end_clean / len(rows):.0f}%); one-shot alone: {len(clean)} of {len(rows)}"
    )
    print(
        f"  tokens in {tokens_in:,} out {tokens_out:,}; "
        f"cost {'~' if local else ''}${dollars:.2f} total, "
        f"{'~' if local else ''}${dollars / max(end_clean, 1):.3f} per verified protocol"
    )


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        tabulate(Path(arg))
