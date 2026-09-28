"""One real plan against the hosted model. Runs only with PROVETTE_NETWORK=1 and the endpoint in
the environment (`set -a; . ~/.config/provette/token-factory.env; set +a`); it costs a few cents."""

from __future__ import annotations

import os

import pytest

from provette.planner import DEFAULT_MODEL, plan

pytestmark = pytest.mark.skipif(
    os.environ.get("PROVETTE_NETWORK") != "1" or not os.environ.get("PROVETTE_BASE_URL"),
    reason=(
        "set PROVETTE_NETWORK=1 and PROVETTE_BASE_URL/PROVETTE_API_KEY to run against the endpoint"
    ),
)

REQUEST = (
    "Set up PCR reactions for 8 DNA samples in a 96-well PCR plate. Each reaction is 20 ul of "
    "master mix plus 5 ul of sample. The master mix is in a 1.5 ml tube and the samples are in "
    "1.5 ml tubes."
)


def test_the_hosted_model_proposes_a_valid_map_for_a_simple_pcr() -> None:
    result = plan(
        REQUEST,
        os.environ.get("PROVETTE_MODEL", DEFAULT_MODEL),
        os.environ["PROVETTE_BASE_URL"],
        os.environ.get("PROVETTE_API_KEY", ""),
        request_id="pcr-01",
    )
    assert result.platemap is not None, result.error
    assert result.tool_calls <= 12 and result.tokens_out < 40000
    wells = [w for v in result.platemap.variants[:1] for g in v.groups for w in g.members]
    wells += list(result.platemap.variants[0].pinned.values())
    assert len(wells) == 8
    assert all(sorted(w.values()) == [5, 20] for w in wells)
