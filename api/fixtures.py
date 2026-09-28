"""Freeze the API's answers for one episode, for the web rendering tests.

    uv run python -m api.fixtures tests/web/fixtures

Writes episodes.json, episode-<id>.json, analysis-<id>.json and rules.json from the same code
the server runs, without a server, and analysis-dil-series.json: the replay tests' export, of the
committed test protocol `tests/fixtures/protocols/dil_series.py` against the dil-01 plate map, so
those tests do not move when the evaluation is run again. Re-run it when the contract changes, and
read the diff.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from api.analysis import analyse
from api.main import create_app
from api.settings import REPO, settings_from_env

EPISODE = "super/plain/dil-03"


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    out = Path(args[0] if args else "tests/web/fixtures")
    out.mkdir(parents=True, exist_ok=True)
    short = EPISODE.rsplit("/", 1)[1]
    settings = settings_from_env()
    with TestClient(create_app(settings)) as client:
        for name, path in (
            ("episodes.json", "/api/episodes"),
            (f"episode-{short}.json", f"/api/episodes/{EPISODE}"),
            (f"analysis-{short}.json", f"/api/episodes/{EPISODE}/analysis"),
            ("rules.json", "/api/rules"),
        ):
            body = client.get(path).json()
            (out / name).write_text(json.dumps(body, separators=(",", ":")), encoding="utf-8")
            print(f"wrote {out / name}")
    protocol = (REPO / "tests/fixtures/protocols/dil_series.py").read_text(encoding="utf-8")
    platemap = json.loads((REPO / "eval/platemaps/dil-01.json").read_text(encoding="utf-8"))
    series = analyse(protocol, platemap)
    (out / "analysis-dil-series.json").write_text(
        json.dumps(series, separators=(",", ":")), encoding="utf-8"
    )
    print(f"wrote {out / 'analysis-dil-series.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
