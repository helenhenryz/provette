"""The numbers behind the methods page and About, computed from the evaluation's result files
at request time. Nothing on those pages is typed: every figure names the file it came from.

    GET /api/evidence

Sources (`eval/README.md`):

* The checks, `eval/checks/results/`: `correct.json` (the 34 correct protocols against their
  maps), `control.json` (each against a wrong map), `mutants.json` (the planted bugs),
  `hand.json` (prep sheets worked out by hand). The definitions are `eval/checks/tabulate.py`'s
  and `eval/checks/README.md`'s: a mutant that leaves the deck identical is equivalent; one the
  simulator passes that changes the deck and that nothing flags is a miss.
* The agent runs, the gallery's sets (`eval/agent/results/<set>/*/*/done.json`, named by
  PROVETTE_GALLERY_SETS). The funnel is `eval/agent/tabulate.py`'s, copied here.
* The baseline, `eval/baseline/results/super-rules-in-prompt`: the rules as text in the prompt,
  no checker, one draft each.
* The planner, `eval/planner/results/super/<id>.json`: the planner against the hand-written maps.
* The ledger, `eval/ledger/counts.json`: the tracer's record against `opentrons.cli analyze`,
  Opentrons' own reading of each run, over the public library; independent from API 2.14
  (D-10; `eval/ledger/build.py`).
* `eval/prices.json` for every dollar.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request

from api.episodes import Gallery, verified
from api.prices import Prices, model_label
from api.settings import Settings

router = APIRouter(prefix="/api", tags=["evidence"])

BASELINE_RUN = "super-rules-in-prompt"


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


# -- the checks ---------------------------------------------------------------------------------


def _nothing(r: dict[str, Any]) -> bool:
    """eval/checks/tabulate.py: a mutant no check flagged."""
    return bool(
        r["intent"] == "verified"
        and not r["accounting_flags"]
        and not r["prep_flags"]
        and not r["check_findings"]
    )


def checks_result(root: Path, repo: Path) -> dict[str, Any] | None:
    if not (root / "mutants.json").is_file():
        return None
    correct = _read(root / "correct.json")
    control = _read(root / "control.json")
    mutants = _read(root / "mutants.json")
    hand = _read(root / "hand.json")
    live = [r for r in mutants if r["simulator"] == "passed"]
    equivalent = [r for r in live if r.get("same_deck")]
    changing = [r for r in live if not r.get("same_deck")]
    missed = [r for r in changing if _nothing(r)]
    caught = [r for r in changing if not _nothing(r)]
    operators = {
        "a": "a volume halved, doubled or raised by 10%",
        "b": "the last item of a list dropped",
        "c": "sources reordered",
        "d": "drawn from the wrong liquid",
        "e": "a dispense sent to the trash",
    }
    by_operator = []
    for op, words in operators.items():
        mine = [r for r in mutants if r["operator"] == op]
        passed = [r for r in mine if r["simulator"] == "passed"]
        by_operator.append(
            {
                "operator": op,
                "words": words,
                "generated": len(mine),
                "pass_simulator": len(passed),
                "compare_mismatch": sum(r["intent"] == "mismatch" for r in passed),
                "cannot_check": sum(r["intent"] == "cannot_check" for r in passed),
                "accounting": sum(bool(r["accounting_flags"]) for r in passed),
                "prep": sum(bool(r["prep_flags"]) for r in passed),
                "check": sum(bool(r["check_findings"]) for r in passed),
                "nothing": sum(_nothing(r) for r in passed),
                # of those not flagged, the missed: samples swapping wells on a map that leaves
                # positions free; the rest leave the plate as the request allows
                "missed": sum(
                    _nothing(r) and not r.get("same_deck") and bool(r.get("layout_free"))
                    for r in passed
                ),
            }
        )
    return {
        "sources": [
            _rel(root / n, repo)
            for n in ("correct.json", "control.json", "mutants.json", "hand.json")
        ],
        "correct": {
            "protocols": len(correct),
            "verified": sum(r.get("exit_code") == 0 for r in correct),
            "wells": sum(int((r.get("intent") or {}).get("wells_total") or 0) for r in correct),
        },
        "control": {
            "protocols": len(control),
            "verified": sum(r.get("intent") == "verified" for r in control),
        },
        "mutants": {
            "generated": len(mutants),
            "pass_simulator": len(live),
            "equivalent": len(equivalent),
            "change_the_deck": len(changing),
            "caught": len(caught),
            "missed": len(missed),
            "missed_layout_swaps": sum(bool(r.get("layout_free")) for r in missed),
            "sample_lost_caught": sum(bool(r.get("sample_lost")) and not _nothing(r) for r in live),
            "sample_lost": sum(bool(r.get("sample_lost")) for r in live),
            "by_operator": by_operator,
        },
        "hand": {"protocols": len(hand), "agree": sum(bool(r.get("agree")) for r in hand)},
    }


# -- the agent runs and the baseline: the funnel, as eval/agent/tabulate.py defines it ---------


def _funnel(rows: list[dict[str, Any]]) -> dict[str, Any]:
    sim = [r for r in rows if (r.get("one_shot") or {}).get("simulator") == "passed"]
    clean = [
        r
        for r in sim
        if r["one_shot"].get("verify_exit") == 0 and r["one_shot"].get("check_exit") == 0
    ]
    problem = [r for r in sim if r not in clean]
    final_clean = [r for r in rows if verified(r)]
    repaired = [r for r in final_clean if r not in clean]
    return {
        "requests": len(rows),
        "pass_simulator_first": len(sim),
        "clean_first": len(clean),
        "problem_first": len(problem),
        "verified_end": len(final_clean),
        "repaired": len(repaired),
    }


def _usage(folder: Path) -> tuple[int, int]:
    tokens_in = tokens_out = 0
    for p in folder.glob("*/*/log.jsonl"):
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            usage = json.loads(line).get("usage") or {}
            tokens_in += int(usage.get("prompt_tokens") or 0)
            tokens_out += int(usage.get("completion_tokens") or 0)
    return tokens_in, tokens_out


def baseline(root: Path, repo: Path, prices: Prices) -> dict[str, Any] | None:
    """The rules as text in the prompt and no checker, one draft each: `eval/baseline/run.py`
    with `--rules-in-prompt --one-shot-only` (eval/baseline/README.md)."""
    folder = root / BASELINE_RUN
    done = sorted(folder.glob("*/*/done.json"))
    if not done:
        return None
    rows = [_read(p) for p in done]
    model = str(rows[0].get("model") or "")
    tokens_in, tokens_out = _usage(folder)
    # of the drafts the simulator passed: how many broke a rule the prompt had just stated (the
    # check exits 1 on an error or a warning), and how many missed the plate map
    sim = [r for r in rows if (r.get("one_shot") or {}).get("simulator") == "passed"]
    return {
        "run": BASELINE_RUN,
        "model": model,
        "model_label": model_label(model),
        **_funnel(rows),
        "broke_rule": sum(r["one_shot"].get("check_exit") != 0 for r in sim),
        "map_mismatch": sum(r["one_shot"].get("verify_exit") != 0 for r in sim),
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost_usd": prices.cost_usd(model, tokens_in, tokens_out),
        "source": _rel(folder, repo) + "/*/*/done.json",
    }


def agent_runs(gallery: Gallery, repo: Path) -> dict[str, Any]:
    """The gallery's result sets (PROVETTE_GALLERY_SETS), named by their directory, each with a
    row in eval/agent/README.md."""
    sets = []
    root = gallery.settings.episodes_dir
    named = set(gallery.settings.gallery_sets)
    for folder in sorted(p for p in root.iterdir() if p.is_dir()) if root.is_dir() else []:
        set_name = folder.name
        done = sorted(folder.glob("*/*/done.json"))
        if not done or set_name not in named:
            continue
        rows = [_read(p) for p in done]
        model = str(rows[0].get("model") or "")
        tokens_in = sum(int(r.get("tokens_in") or 0) for r in rows)
        tokens_out = sum(int(r.get("tokens_out") or 0) for r in rows)
        funnel = _funnel(rows)
        cost = gallery.prices.cost_usd(model, tokens_in, tokens_out)
        ids = {str(r.get("id") or "") for r in rows}
        harder = bool(ids) and all(i.startswith("hard-") for i in ids)
        sets.append(
            {
                "set": set_name,
                "run_label": gallery.run_label(set_name),
                "request_set": "the harder set" if harder else "the original set",
                "model": model,
                "model_label": model_label(model),
                **funnel,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "cost_usd": cost,
                # to the tenth of a cent, as eval/agent/README.md prints it, from the unrounded
                # quotient: 1.0081 / 33 = 0.03055 is $0.031, not $0.030
                "per_verified_usd": (
                    round(cost / funnel["verified_end"], 3)
                    if cost and funnel["verified_end"]
                    else None
                ),
                "stop_reasons": dict(Counter(str(r.get("stop_reason")) for r in rows)),
                "source": _rel(folder, repo) + "/*/*/done.json",
            }
        )
    return {"sets": sets}


def planner_result(root: Path, repo: Path) -> dict[str, Any] | None:
    files = sorted(p for p in root.glob("*.json") if not p.name.endswith(".platemap.json"))
    if not files:
        return None
    rows = [_read(p) for p in files]
    return {
        "requests": len(rows),
        "valid_map": sum(r.get("planned") is not None for r in rows),
        "agree": sum(bool((r.get("agreement") or {}).get("agree")) for r in rows),
        "verify": sum((r.get("verify") or {}).get("exit") == 0 for r in rows),
        "cost_usd": round(sum(float(r.get("cost_usd") or 0) for r in rows), 4),
        "tool_calls": [int(r.get("tool_calls") or 0) for r in rows],
        "source": _rel(root, repo) + "/<id>.json",
    }


def ledger_result(path: Path, repo: Path) -> dict[str, Any] | None:
    """`eval/ledger/counts.json`: the library protocols the simulator accepts, how many of them
    Opentrons' analysis agrees with the ledger on (and of those, how many are at API 2.14 or
    later, where the analysis is independent, D-10), and how many the replay exports."""
    if not path.is_file():
        return None
    c = _read(path)
    return {
        "library": int(c["library"]),
        "accepted": int(c["accepted"]),
        "compared": int(c["compared"]),
        "agree": int(c["agree"]),
        "independent": int(c["independent"]),
        "independent_agree": int(c["independent_agree"]),
        "exported": int(c["exported"]),
        "events": int(c["events"]),
        "source": _rel(path, repo),
    }


def evidence(settings: Settings, gallery: Gallery) -> dict[str, Any]:
    eval_root = settings.eval_dir
    repo = eval_root.parent
    return {
        "prices_read_on": gallery.prices.read_on,
        "prices_source": gallery.prices.source,
        "checks": checks_result(eval_root / "checks" / "results", repo),
        "agent": agent_runs(gallery, repo),
        "baseline": baseline(eval_root / "baseline" / "results", repo, gallery.prices),
        "planner": planner_result(eval_root / "planner" / "results" / "super", repo),
        "ledger": ledger_result(eval_root / "ledger" / "counts.json", repo),
    }


@router.get("/evidence")
def evidence_route(request: Request) -> dict[str, Any]:
    return evidence(request.app.state.settings, request.app.state.gallery)
