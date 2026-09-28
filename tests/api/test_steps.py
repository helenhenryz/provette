"""The steps a transcript becomes, on hand-built turns: every shape the loop writes."""

from __future__ import annotations

from api.steps import checks_sentence, steps_from_transcript


def _turn(n: int, calls: list[dict], results: list[dict], **extra: object) -> dict:
    return {
        "turn": n,
        "seconds": 1.5,
        "finish_reason": "tool_calls",
        "assistant": {"content": "", "reasoning": "x" * 100, "tool_calls": calls},
        "tool_results": results,
        "usage": {"completion_tokens": 42},
        **extra,
    }


def test_a_rejected_draft_names_the_line_and_the_hint() -> None:
    title, detail, status = checks_sentence(
        {
            "draft": 3,
            "simulator": "rejected",
            "simulator_error": "line 31: KeyError [line 31]: 'A7'",
            "hint": "'A7' is not a well of the labware used at that line.",
        }
    )
    assert title == "Draft 3: the simulator rejected the file at line 31 (a hint was given)"
    assert "KeyError" in detail
    assert status == "rejected"


def test_a_verified_draft_counts_wells_and_problems() -> None:
    title, _, status = checks_sentence(
        {
            "draft": 2,
            "simulator": "passed",
            "verify_exit": 0,
            "check_exit": 1,
            "verify_report": (
                "protocol.py: VERIFIED against plate map dil-01. "
                "12 of 12 wells hold what the plate map says."
            ),
            "findings": [{"severity": "warning", "title": "A used tip went into a stock"}],
        }
    )
    assert title == "Draft 2: verified 12 of 12 wells, 1 biology problem (1 warning)"
    assert status == "problem"


def test_every_turn_shape_becomes_a_step() -> None:
    turns = [
        _turn(
            0,
            [{"name": "platemap", "arguments": "{}"}],
            [{"name": "platemap", "result": {"liquid_names": ["a", "b"]}}],
        ),
        _turn(
            1,
            [{"name": "new_tool", "arguments": '{"x": 1}'}],
            [{"name": "new_tool", "result": {"y": 2}}],
        ),
        _turn(
            2,
            [{"name": "write_protocol", "arguments": '{"text": "..."}'}],
            [
                {
                    "name": "write_protocol",
                    "result": {
                        "stored": True,
                        "draft": 0,
                        "lines": 10,
                        "checks": {
                            "draft": 0,
                            "simulator": "rejected",
                            "simulator_error": "line 2: E",
                        },
                    },
                }
            ],
        ),
        {"turn": 3, "api_error": "HTTP 502", "seconds": 5.0},
        _turn(4, [], [], finish_reason="length"),
        _turn(
            5,
            [{"name": "labware", "arguments": "not json"}],
            [{"name": "labware", "result": {"error": "arguments are not JSON"}}],
        ),
    ]
    steps = steps_from_transcript(turns)
    titles = [s["title"] for s in steps]
    assert titles == [
        "Read the plate map",
        "Called new_tool",
        "Wrote draft 0 (10 lines)",
        "Draft 0: the simulator rejected the file at line 2",
        "The model's API returned an error; the loop waited and retried",
        "The turn was cut at the token cap before the model produced anything",
        "Called labware, which answered with an error",
    ]
    assert steps[1]["detail"] == '{"x": 1}'
    assert steps[3]["status"] == "rejected" and steps[3]["draft"] == 0
    assert steps[5]["cut"] is True
    assert all(
        {"turn", "kind", "tool", "title", "detail", "status", "draft"} <= set(s) for s in steps
    )
