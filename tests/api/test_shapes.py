"""The newer shapes the loop writes: a best-of-N request (`chosen`), a repaired draft
(`repaired_before_checking`, `NN-draft.as-written.py`), and where the checks ran (`runner`)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from api.main import create_app
from api.settings import REPO, Settings
from api.steps import steps_from_transcript
from tests.api.conftest import make_settings

SOURCE = REPO / "eval/agent/results/super/plain/pcr-01"


def best_of_settings(tmp_path: Path) -> Settings:
    """A synthetic best-of-2 result set built from a real episode: candidate-1 is the chosen one."""
    root = tmp_path / "results" / "best" / "plain" / "pcr-01"
    for k in (0, 1):
        shutil.copytree(SOURCE, root / f"candidate-{k}")
        # only draft 1 carries a repair here, whatever the source episode's drafts did
        for repaired in (root / f"candidate-{k}").glob("*-draft.as-written.py"):
            repaired.unlink()
    done = json.loads((SOURCE / "done.json").read_text())
    (root / "candidate-1" / "01-draft.as-written.py").write_text(
        "# as the model wrote it\n" + (SOURCE / "01-draft.py").read_text()
    )
    done["runner"] = "nebius"
    done["candidates"] = [
        {
            "dir": "candidate-0",
            "verified": False,
            "stop_reason": "call budget",
            "tokens_in": 1,
            "tokens_out": 1,
        },
        {
            "dir": "candidate-1",
            "verified": True,
            "stop_reason": "submitted",
            "tokens_in": 1,
            "tokens_out": 1,
        },
    ]
    done["chosen"] = "candidate-1"
    (root / "done.json").write_text(json.dumps(done))
    base = make_settings(tmp_path, sets=("best",))
    return Settings(**{**base.__dict__, "episodes_dir": tmp_path / "results"})


def test_a_best_of_episode_reads_the_chosen_candidates_files(tmp_path: Path) -> None:
    with TestClient(create_app(best_of_settings(tmp_path))) as client:
        card = client.get("/api/episodes").json()["episodes"][0]
        assert card["candidates"] == {
            "n": 2,
            "verified": 1,
            "chosen": "candidate-1",
            "rows": [
                {
                    "dir": "candidate-0",
                    "verified": False,
                    "stop_reason": "call budget",
                    "tokens_in": 1,
                    "tokens_out": 1,
                },
                {
                    "dir": "candidate-1",
                    "verified": True,
                    "stop_reason": "submitted",
                    "tokens_in": 1,
                    "tokens_out": 1,
                },
            ],
        }
        assert card["runner"] == "nebius" and "Token Factory Sandbox" in card["runner_label"]
        assert "2 candidates ran at once" in card["outcome"]["sentence"]
        body = client.get("/api/episodes/best/plain/pcr-01").json()
        assert body["steps"][0]["title"] == "Read the plate map"
        rows = {d["n"]: d for d in body["draft_rows"]}
        assert rows[1]["repaired"] is True and rows[0]["repaired"] is False
        draft = client.get("/api/episodes/best/plain/pcr-01/drafts/1").json()
        assert draft["as_written"].startswith("# as the model wrote it")
        assert draft["text"] == (SOURCE / "01-draft.py").read_text()
        final = client.get("/api/episodes/best/plain/pcr-01/protocol.py").text
        assert final == (SOURCE / f"{body['final_draft']:02d}-draft.py").read_text()


def test_a_repaired_draft_is_a_step_that_says_so() -> None:
    turns = [
        {
            "turn": 0,
            "seconds": 1.0,
            "finish_reason": "tool_calls",
            "assistant": {
                "content": "",
                "reasoning": "",
                "tool_calls": [{"name": "write_protocol", "arguments": "{}"}],
            },
            "tool_results": [
                {
                    "name": "write_protocol",
                    "result": {
                        "stored": True,
                        "draft": 2,
                        "lines": 40,
                        "repaired_before_checking": [
                            "display_color given as an int",
                            "apiLevel raised to 2.20",
                        ],
                    },
                }
            ],
            "usage": {},
        }
    ]
    step = steps_from_transcript(turns)[0]
    assert step["title"] == "Wrote draft 2 (40 lines), repaired before checking"
    assert (
        step["detail"]
        == "Repaired before checking: display_color given as an int; apiLevel raised to 2.20"
    )


def test_the_runner_setting_is_reported(tmp_path: Path) -> None:
    base = make_settings(tmp_path)
    with TestClient(create_app(Settings(**{**base.__dict__, "runner": "nebius"}))) as client:
        status = client.get("/api/live").json()
        assert status["runner"] == "nebius" and "Token Factory Sandbox" in status["runner_label"]
        card = next(
            e
            for e in client.get("/api/episodes").json()["episodes"]
            if e["id"] == "super/plain/pcr-01"
        )
        assert card["runner"] == "local" and card["runner_label"] == "on the server"
