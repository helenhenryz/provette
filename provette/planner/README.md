# provette/planner — a model proposes the plate map, a person approves it

The first stage of the pipeline in [`docs/how-it-works.md`](../../docs/how-it-works.md): the scientist describes the
experiment in a sentence or two, and a plate map comes back, in the format of
[`provette/intent/spec.py`](../intent/spec.py), for them to read and approve before any
protocol is written. Until now the 17 plate maps of `eval/platemaps/` were written by
hand; this is the module that writes one from the request.

    provette plan "Set up PCR reactions for 8 DNA samples ..." [--out map.json]
    plan_platemap(request_text, model, base_url, api_key) -> PlateMap

The endpoint comes from `PROVETTE_BASE_URL` and `PROVETTE_API_KEY` (`set -a;
. ~/.config/provette/token-factory.env; set +a`); the default model is
`nvidia/nemotron-3-super-120b-a12b`.

## The rules of the design

* **The model never computes a number.** Its tools are the three calculators of
  [`provette/calc/`](../calc/) (`dilution_series`, `normalise`, `master_mix`, the same
  functions the hand-written maps and the agent's tools use), the `labware` sheet, and
  `propose_platemap`. Every volume in a proposed map must be a number written in the
  request or returned by a calculator: `propose_platemap` reads the request for its
  numbers, remembers every number a calculator returned, and refuses a map with a
  volume from anywhere else (`tests/planner/test_tools.py`). That is the rule enforced,
  not asked.
* **Positions are pinned only where the request pins them** ("the matching well", "row
  G", "column 12", "consecutive wells from A1", a dilution "across one row"); otherwise
  the wells are a position-free group, with `order_hint: "index"` where sample 1, 2, 3
  would naturally be laid down in order. Liquids bind by regex, one per logical liquid,
  indexed liquids with a capture group and a count, exactly as
  [`eval/platemaps/build.py`](../../eval/platemaps/build.py) writes them.
* **A choice the request leaves open is written down.** Every note says where an
  ambiguous choice came from ("the request does not say which row; row A chosen"), and a
  request with two defensible readings gets one variant per reading.
* **`propose_platemap` validates with `platemap_from_dict`** and returns the validation
  error to the model, which fixes the map and calls again. A budget that runs out (12
  tool calls, 40,000 completion tokens) is an error, never a guessed map: `plan_platemap`
  raises `PlanError`, and `plan` returns a `Planning` with `platemap` None and the reason.
* **A message that is not a request ends without a map** (`plan(..., allow_decline=True)`,
  which the product and the evaluation both use): the model may call `not_a_request` with one
  sentence, and `Planning.declined` holds it. Without the flag neither the tool nor its
  paragraph of the prompt is offered (D-33).
* **The chat call is the agent's.** `provette/agent/llm.py` holds `OpenAIChat` (NVIDIA's
  settings for tool use on Nemotron 3: temperature 0.6, top_p 0.95, reasoning on) and
  both loops use it.

## What is in this directory

| file | what it is |
|---|---|
| [`prompt.py`](prompt.py) | the planner's sheet: the format, the rules above, one worked example that is none of our requests |
| [`tools.py`](tools.py) | the five tools: schemas, implementations, the number rule, and the one JSON repair (below) |
| [`loop.py`](loop.py) | `plan` and `plan_platemap`: the episode, the budgets, the transcript |
| [`agree.py`](agree.py) | how far a proposed map agrees with a reference one: liquids, amounts within `tolerance_ul`, positions |
| [`cli.py`](cli.py) | `provette plan` |
| [`../../eval/planner/run.py`](../../eval/planner/run.py) | the evaluation: plans the 17 requests that have a hand-written map, compares, and runs `provette verify` with the planned map against the correct protocol |

## How it is measured

`eval/planner/` plans the 17 requests that have a hand-written map, three times, and holds each
planned map against the hand-written one and against a correct protocol for the request; every
difference is read and classified in [`eval/planner/README.md`](../../eval/planner/README.md).

**The JSON slip.** Sending a long map, Super may write it as a JSON string and drop the `]` that
closes `variants` before `, "discard_intended"`. `propose_platemap` closes that one bracket, says
so in the tool's reply and in `Planning.repairs`, and refuses anything else (D-29).

Tests: `tests/planner/` (the proposal's validation path and the number rule on
hand-built dicts, the bracket repair, the loop with a scripted model, the agreement on
the frozen maps; a network test that runs only with `PROVETTE_NETWORK=1`).
