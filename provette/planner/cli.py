"""`provette plan "<request>" [--out map.json]`: propose the plate map for a request.

The model and the endpoint come from --model, --base-url and the environment (PROVETTE_BASE_URL,
PROVETTE_API_KEY; `set -a; . ~/.config/provette/token-factory.env; set +a` exports both). The map
is printed as JSON, or written to --out; the token counts go to stderr. Exit 0 with a map,
1 when the planner could not produce one (the reason is printed; no map is guessed).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from provette.intent.spec import dump_platemap
from provette.planner.loop import DEFAULT_MODEL, plan


def _command(args: argparse.Namespace) -> int:
    base_url = args.base_url or os.environ.get("PROVETTE_BASE_URL", "")
    if not base_url:
        print("No endpoint: pass --base-url or set PROVETTE_BASE_URL.", file=sys.stderr)
        return 1
    result = plan(
        args.request,
        args.model,
        base_url,
        os.environ.get("PROVETTE_API_KEY", ""),
        request_id=args.id,
        technique=args.technique,
    )
    print(
        f"{result.model}: {result.tool_calls} tool calls, {result.tokens_in} prompt and "
        f"{result.tokens_out} completion tokens, {result.seconds} s, stopped: {result.stop_reason}",
        file=sys.stderr,
    )
    if result.platemap is None:
        print(result.error, file=sys.stderr)
        return 1
    text = json.dumps(dump_platemap(result.platemap), indent=1) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"wrote {args.out}", file=sys.stderr)
    else:
        sys.stdout.write(text)
    return 0


def register(sub: Any) -> None:
    p = sub.add_parser("plan", help="propose the plate map for a request, for a person to approve")
    p.add_argument("request", help="the request, in the scientist's words")
    p.add_argument("--out", type=Path, help="write the map here instead of printing it")
    p.add_argument("--model", default=DEFAULT_MODEL, help=f"the model id (default {DEFAULT_MODEL})")
    p.add_argument("--base-url", help="the OpenAI-compatible endpoint (default PROVETTE_BASE_URL)")
    p.add_argument("--id", default="planned", help="the map's id (default 'planned')")
    p.add_argument(
        "--technique",
        help="the request's technique word ('PCR setup', 'ELISA'), written into the map",
    )
    p.set_defaults(func=_command)
