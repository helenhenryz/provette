from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from api.settings import REPO, Settings

# The episodes the contract tests read: the agent runs of eval/agent/README.md, as they are.
SETS = ("super", "nano-best3", "super-hard", "nano-hard-best3")


def make_settings(tmp_path: Path, sets: tuple[str, ...] = SETS) -> Settings:
    return Settings(
        data_dir=tmp_path / "data",
        eval_dir=REPO / "eval",
        episodes_dir=REPO / "eval/agent/results",
        gallery_sets=sets,
        platemaps_dir=REPO / "eval/platemaps",
        requests_file=REPO / "eval/requests/requests.jsonl",
        prices_file=REPO / "eval/prices.json",
        docs_dir=REPO / "docs",
        coverage_file=REPO / "tests/api/fixtures/coverage.yaml",
        web_dir=None,
        api_key="",
        base_url="",
        judge_password="",
        daily_cap_usd=2.0,
    )


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return make_settings(tmp_path)


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as client:
        yield client
