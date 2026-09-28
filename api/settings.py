"""Everything the API reads from its environment, in one place.

PROVETTE_DATA_DIR        where live episodes, the index and the analysis cache live (a volume)
PROVETTE_EVAL_DIR        the evaluation directory (eval/), read-only in the image; the four
                       settings below default to paths under it
PROVETTE_EPISODES_DIR    the pre-run episodes the gallery shows
PROVETTE_GALLERY_SETS    which result sets under it the gallery and the methods page show,
                       comma-separated (the four runs of eval/agent/README.md by default)
PROVETTE_PLATEMAPS_DIR   the hand-written plate maps the pre-run episodes were run against
PROVETTE_REQUESTS_FILE   the requests (jsonl: id, technique, request)
PROVETTE_PRICES_FILE     list prices per model (eval/prices.json)
PROVETTE_DOCS_DIR        the docs the product renders (docs/: the rulebook, the learning guide)
PROVETTE_COVERAGE_FILE   what the checks cover per technique (provette/rules/coverage.yaml)
PROVETTE_DECLARED_DIR    where the form saves declared rules (provette/rules/declared/)
PROVETTE_ROLES_FILE      the word lists a taught word is written to (provette/rules/roles.yaml)
PROVETTE_SOURCES_FILE    the sources an added source is written to (provette/rules/sources.yaml)
PROVETTE_WEB_DIR         the built pages to serve (web/dist); unset in API-only tests
PROVETTE_API_KEY         Token Factory key; the live flows are off without it
PROVETTE_BASE_URL        Token Factory endpoint
PROVETTE_JUDGE_PASSWORD  the password in front of the live flow; unset means the flow is off
PROVETTE_DAILY_CAP_USD   the day's spend cap for live episodes (default 2.00)
PROVETTE_RUNNER          where a live draft's checks run: local (default, fastest), nebius (a Token
                       Factory Sandbox, about 14 s a check) or docker; provette.sandbox.make_runner
PROVETTE_EXAMPLE_PROTOCOL the protocol the check page offers to try (tests/fixtures/protocols/
                       pcr_buggy.py; the image keeps a copy, since the tests are not in it)
PROVETTE_ANALYSES_AT_ONCE simulator subprocesses at once, process-wide (default 2; api/analysis.py)
PROVETTE_SANDBOX_PROJECT the Token Factory project id for the nebius runner (discovered otherwise)
PROVETTE_API_DOCS        "1" serves FastAPI's route documentation at /api/docs (the dev server
                       sets it); unset, as deployed, the page is off

The deployment's values, and what each one means for the machine, are in deploy/README.md.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
# The four runs of eval/agent/README.md: each model on the 34 requests and on the 15 harder
# ones; Nano best of 3.
DEFAULT_SETS = "super,nano-best3,super-hard,nano-hard-best3"


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    eval_dir: Path
    episodes_dir: Path
    gallery_sets: tuple[str, ...]
    platemaps_dir: Path
    requests_file: Path
    prices_file: Path
    docs_dir: Path
    web_dir: Path | None
    api_key: str
    base_url: str
    judge_password: str
    daily_cap_usd: float
    runner: str = "local"
    coverage_file: Path = REPO / "provette/rules/coverage.yaml"
    declared_dir: Path = REPO / "provette/rules/declared"
    roles_file: Path | None = None  # None: provette.rules.roles.ROLES_FILE as shipped
    sources_file: Path | None = None  # None: provette.rules.sources.SOURCES_FILE as shipped
    example_protocol: Path = REPO / "tests/fixtures/protocols/pcr_buggy.py"
    api_docs: bool = False  # /api/docs and /api/openapi.json; off unless asked for

    @property
    def request_sets(self) -> tuple[tuple[Path, Path], ...]:
        """Every (requests.jsonl, plate-map directory) pair an episode's request may come from:
        eval/requests with eval/platemaps, then every eval/requests-* directory, which holds
        its own maps beside its requests.jsonl (eval/requests-hard)."""
        pairs = [(self.requests_file, self.platemaps_dir)]
        for folder in sorted(self.eval_dir.glob("requests-*")):
            if (folder / "requests.jsonl").is_file():
                pairs.append((folder / "requests.jsonl", folder))
        return tuple(pairs)

    @property
    def cache_dir(self) -> Path:
        return self.data_dir / "cache"

    @property
    def live_enabled(self) -> bool:
        """The live flows need a key and a password; the gallery and the checker need neither."""
        return bool(self.api_key and self.base_url and self.judge_password)


def _path(name: str, default: Path) -> Path:
    value = os.environ.get(name)
    return Path(value) if value else default


def settings_from_env() -> Settings:
    web = os.environ.get("PROVETTE_WEB_DIR")
    sets = os.environ.get("PROVETTE_GALLERY_SETS", DEFAULT_SETS)
    eval_dir = _path("PROVETTE_EVAL_DIR", REPO / "eval")
    return Settings(
        data_dir=_path("PROVETTE_DATA_DIR", REPO / ".data"),
        eval_dir=eval_dir,
        episodes_dir=_path("PROVETTE_EPISODES_DIR", eval_dir / "agent/results"),
        gallery_sets=tuple(s.strip() for s in sets.split(",") if s.strip()),
        platemaps_dir=_path("PROVETTE_PLATEMAPS_DIR", eval_dir / "platemaps"),
        requests_file=_path("PROVETTE_REQUESTS_FILE", eval_dir / "requests/requests.jsonl"),
        prices_file=_path("PROVETTE_PRICES_FILE", eval_dir / "prices.json"),
        docs_dir=_path("PROVETTE_DOCS_DIR", REPO / "docs"),
        coverage_file=_path("PROVETTE_COVERAGE_FILE", REPO / "provette/rules/coverage.yaml"),
        declared_dir=_path("PROVETTE_DECLARED_DIR", REPO / "provette/rules/declared"),
        roles_file=Path(os.environ["PROVETTE_ROLES_FILE"])
        if os.environ.get("PROVETTE_ROLES_FILE")
        else None,
        sources_file=Path(os.environ["PROVETTE_SOURCES_FILE"])
        if os.environ.get("PROVETTE_SOURCES_FILE")
        else None,
        web_dir=Path(web) if web else None,
        api_key=os.environ.get("PROVETTE_API_KEY", ""),
        base_url=os.environ.get("PROVETTE_BASE_URL", ""),
        judge_password=os.environ.get("PROVETTE_JUDGE_PASSWORD", ""),
        daily_cap_usd=float(os.environ.get("PROVETTE_DAILY_CAP_USD", "2.00")),
        runner=os.environ.get("PROVETTE_RUNNER", "local"),
        example_protocol=_path(
            "PROVETTE_EXAMPLE_PROTOCOL", REPO / "tests/fixtures/protocols/pcr_buggy.py"
        ),
        api_docs=os.environ.get("PROVETTE_API_DOCS", "") == "1",
    )
