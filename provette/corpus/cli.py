"""`provette corpus ...`: fetch the Opentrons protocol library, list it, run it, summarise a run."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from provette.corpus.library import CACHE_DIR, DEFAULT_CHECKOUT, LIBRARY_COMMIT, discover, fetch
from provette.corpus.prepare import prepare
from provette.corpus.runner import run_corpus
from provette.corpus.summary import render, summarise

DEFAULT_WORKER = "provette.corpus.workers:simulate_worker"
RUNS_DIR = CACHE_DIR / "corpus"


def _default_out(worker: str) -> Path:
    return RUNS_DIR / f"{worker.rpartition(':')[2]}.jsonl"


def _fetch(args: argparse.Namespace) -> int:
    checkout = fetch()
    print(f"{checkout} is at {LIBRARY_COMMIT}: {len(discover(checkout))} protocols")
    return 0


def _list(args: argparse.Namespace) -> int:
    wanted = args.category.casefold() if args.category else None
    for protocol in discover(fetch()):
        if wanted is None or wanted in (c.casefold() for c in protocol.categories):
            print(f"{protocol.slug}\t{protocol.api_level}\t{'; '.join(protocol.categories)}")
    return 0


def _run(args: argparse.Namespace) -> int:
    protocols = discover(fetch())
    if args.slug:
        missing = sorted(set(args.slug) - {p.slug for p in protocols})
        if missing:
            print(f"not in the library: {', '.join(missing)}")
            return 2
        protocols = [p for p in protocols if p.slug in args.slug]
    if args.limit is not None:
        protocols = protocols[: args.limit]
    out_path = args.out or _default_out(args.worker)
    prepared = [prepare(p, RUNS_DIR / "prepared") for p in protocols]
    result = run_corpus(
        prepared,
        args.worker,
        jobs=args.jobs,
        timeout_s=args.timeout,
        out_path=out_path,
        force=args.force,
    )
    print(
        f"ran {result.ran}, skipped {result.skipped} already in {out_path}, "
        f"in {result.seconds} s: {result.by_status}\n"
    )
    print(render(summarise(out_path)))
    return 0


def _summary(args: argparse.Namespace) -> int:
    print(render(summarise(args.file or _default_out(DEFAULT_WORKER))))
    return 0


def register(sub: Any) -> None:
    corpus = sub.add_parser("corpus", help="the public Opentrons protocol library")
    commands = corpus.add_subparsers(dest="corpus_command", required=True)

    p = commands.add_parser("fetch", help=f"check the library out under {DEFAULT_CHECKOUT}")
    p.set_defaults(func=_fetch)

    p = commands.add_parser("list", help="slug, apiLevel and categories of every protocol")
    p.add_argument("--category", help="only protocols in this top-level category")
    p.set_defaults(func=_list)

    p = commands.add_parser("run", help="run a worker over the library, one JSON line each")
    p.add_argument("--worker", default=DEFAULT_WORKER, help="package.module:function")
    p.add_argument("--jobs", type=int, default=4)
    p.add_argument("--timeout", type=float, default=120.0, help="seconds per protocol")
    p.add_argument("--limit", type=int, help="only the first N protocols, by slug")
    p.add_argument("--slug", action="append", help="only this protocol; may be repeated")
    p.add_argument("--force", action="store_true", help="start the results file again")
    p.add_argument("--out", type=Path, help="default: .cache/corpus/<worker function>.jsonl")
    p.set_defaults(func=_run)

    p = commands.add_parser("summary", help="counts from a results file")
    p.add_argument("file", type=Path, nargs="?")
    p.set_defaults(func=_summary)
