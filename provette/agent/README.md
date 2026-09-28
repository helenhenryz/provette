# provette/agent — the loop where a model writes a protocol with tools

This is the "model writes" stage of the pipeline in
[`docs/how-it-works.md`](../../docs/how-it-works.md), as an agent. A model handed
the reports as pasted messages cannot do the dilution arithmetic, renames the
liquids, loses a repair to the simulator, and answers "no margin" by re-declaring
the same volume. So here the model gets **tools** for exactly those things, and it
runs the checks itself. The model is still never the judge: every `write_protocol`
runs the simulator, `provette verify` and `provette check` through a
[`Runner`](runner.py), and what comes back is what decides.

## What is in this directory

| file | what it is |
|---|---|
| [`runner.py`](runner.py) | **the contract**: a `Runner` takes a draft and a plate map, runs every check, returns one dict. Read-only for this module; the sandbox implements it too |
| [`local_runner.py`](local_runner.py) | `LocalRunner`: the checks as subprocesses on this machine, in a temp dir. For development. A draft runs with this machine's privileges, so untrusted drafts belong in the sandbox (`provette.sandbox`, built separately) |
| [`tools.py`](tools.py) | the seven tools: their OpenAI function schemas and their Python implementations, in one `Toolbox` per episode |
| [`loop.py`](loop.py) | `run_episode`: the system prompt, the chat call, the tool loop, the stop rules, the record on disk |
| [`../calc/`](../calc/) | the arithmetic the tools call: `dilution_series`, `normalise`, `master_mix`. The plate maps in `eval/platemaps/build.py` are written from the same functions |
| [`../../eval/agent/run.py`](../../eval/agent/run.py) | runs the loop over the 17 requests that have a plate map; `eval/agent/tabulate.py` reads the results unchanged |

## The tools

| tool | when the model calls it | what comes back |
|---|---|---|
| `platemap()` | first, before writing | the exact liquid names for `define_liquid`, the destination, and what every well (or group of wells) must hold in microlitres of each starting liquid. Built from the plate map JSON; compact (under 4,000 characters for every map) |
| `labware(kind)` | to pick labware; kind is plate, tubes, tips, reservoir or module_block | the real load names of the families the reference sheet offers, read from the installed Opentrons definitions: wells, well names, the most a well holds; tip size for tip racks; the module names for module_block |
| `dilution_series(stock_concentration, points, factor, final_volume_ul, first_point_is_stock, remove_excess)` | for any serial dilution | per well, in order: diluent to add, volume to transfer in and from where, volume to carry out, what the well then holds and how much of it is stock, the concentration |
| `normalise(concentrations, target, final_volume_ul, min_pipette_ul)` | to bring samples to one concentration | per sample: sample ul, diluent ul, and a warning below the pipette's minimum or below the target |
| `master_mix(components, reactions, overage_fraction)` | to pool reagents | per component, the volume to pool; the total; the volume to dispense per reaction |
| `write_protocol(text)` | to hand in the whole file | the draft number and line count; a syntax error if the file does not parse; otherwise **the checks of that draft**: the runner's result as the model reads it (`simulator` passed or rejected with the error and line, `verify_exit`, `check_exit`, the two text reports cut at about 6,000 characters, the findings, `ready_to_submit` and a one-line `verdict`), so a draft is never left unchecked and a round trip is saved. Added after the Super run: five of its six failures wrote draft after draft without checking |
| `submit()` | when `ready_to_submit` is true, or after several tries with the best draft | whether the last check of the current draft was verified and clean |

Every tool returns a dict. A tool the model invents, arguments that are not JSON,
or the wrong parameter names come back as `{"error": ...}` and the episode goes on.

## The episode

System prompt: "You are a helpful assistant.", the reference sheet
(`eval/requests/reference.md`), the preamble's requirements
(`eval/requests/preamble.md`, with the liquid-naming line and, in the
short-on-tips condition, the extra line, exactly as `eval/baseline/run.py` builds
them) with "output only the Python file" replaced by "hand it in with
`write_protocol`", and a paragraph naming the tools and the rules: read the checks
that every `write_protocol` returns; submit only when they report `ready_to_submit`; if
that cannot be reached after several tries, submit the best draft. User message:
the request. Sampling is NVIDIA's for tool use on Nemotron 3: temperature 0.6 on Nano and
1.0 on Super, top_p 0.95, reasoning on, 24,000 tokens per turn (`llm.py`).

**Stop rules.** The episode ends on the first of: `submit`; 25 tool calls
(`max_tool_calls`); 100,000 completion tokens (`max_completion_tokens`; both are the
defaults Settings can change, `api/run_settings.py`); a rejected draft is not taken as the
answer before the third (`min_drafts`, D-32); three
API errors in a row (with 5 s and 15 s of backoff between them); three turns in a
row where the model neither calls a tool nor pastes a code block.

**When the model does not use the tools.** A reply with a fenced code block and
no tool call is treated as `write_protocol` on the longest block (it counts as a
tool call) and the model is told to use the tool. A reply with neither is
answered with a reminder of the tools.

**The judgement is the runner's.** `done.json` carries the keys `eval/baseline/run.py`
writes, so `eval/agent/tabulate.py` tabulates a results directory unchanged: `one_shot`
is the result of the checks on the model's first draft; `loop` is the
result on the submitted draft. If the model submitted a draft it never checked,
the harness checks it (`final_draft_checked_by_harness: true`), so the record
says how the submitted file really stood. Also recorded: `tool_calls`, `turns`,
`drafts`, `checks`, `submitted`, `submitted_clean`, `stop_reason`, `tokens_in`,
`tokens_out`, `seconds`.

**On disk**, per request: `transcript.jsonl` (every turn: the model's content,
its reasoning, its tool calls, every tool result, the token usage),
`log.jsonl` (one slim line per turn with the usage, for `tabulate.py`),
`NN-draft.py` and `NN-checks.json` for every draft, and `done.json`.

## How to run it

```
set -a; . ~/.config/provette/token-factory.env; set +a     # PROVETTE_API_KEY, PROVETTE_BASE_URL
env -u PYTHONPATH uv run python eval/agent/run.py \
    --model nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B \
    --out eval/agent/results/nano --conditions plain --ids pcr-01 dil-01 norm-01
env -u PYTHONPATH uv run python eval/agent/tabulate.py eval/agent/results/nano
```

`--runner local` (the default) runs the checks on this machine; `--runner
sandbox` needs `provette.sandbox` and fails with a clear message without it. A
request with a `done.json` is skipped unless `--force`. `--base-url` defaults to
`PROVETTE_BASE_URL`.

Tests: `tests/calc/` checks the arithmetic against the frozen plate maps;
`tests/agent/` checks every tool on the maps, the local runner on a fixture
protocol (`@pytest.mark.sim`), and the loop with a scripted model (the fenced-block
fallback, malformed calls, every budget) without the network.

## Known gaps

* The one-tip-through-everything and "no margin" findings that end an episode on the budget are
  warnings the report itself calls harmless to that run; severity follows what was carried (D-20).
* `log.jsonl` duplicates the usage that is in `transcript.jsonl`, so that
  `eval/agent/tabulate.py` reads it unchanged.

## The thinking budget (Nano): finishing a turn that was cut

`budget.py`. Without it, most of Nano's misses are turns cut at the 24,000-token
per-turn cap while the model is still thinking, so the turn ends with no tool call. NVIDIA's tech report (arXiv 2512.20856, section 2.7) says the
models are trained for this: append `</think>` to a partial thinking trace and
the model answers from what it has. `docs/harness-practices.md`, row 1.

**Two calls.** Call 1 is the chat call as today, with `max_tokens` = the budget.
If it stops on its own, nothing changes. If `finish_reason` is `length`, Token
Factory returns the partial reasoning in `message.reasoning` and no tool call.
Call 2 is `continue_after_cut(client, model, messages, tools, reasoning,
max_tokens)`: it renders the conversation exactly as the server rendered it for
call 1, appends the reasoning the model produced, closes it with `.\n</think>\n\n`,
and sends the string to `POST /v1/completions` (temperature 0.6, top_p 0.95, stop
at `<|im_end|>`). The completion is text, so the tool call comes back in the chat
template's own format and `parse_completion` turns it into the OpenAI-shaped
`tool_calls` the loop consumes (ids `call_budget_1`, ...; values typed by the
schemas). The reply has the `Chat` shape, `{"message", "usage", "finish_reason"}`,
and the message carries `reasoning` (the partial one with its full stop) and
`budget_continued: True`. No state: one render, one request, one parse.

**Where the template comes from.** `nemotron3_nano/chat_template.jinja` and
`tokenizer_config.json` are the model's public tokenizer files, fetched unchanged
(the NOTE there names the URLs and the licence). `render()` is a hand-written copy
of that template for the shapes our loop sends: system, user, assistant with or
without tool calls, tool results, and the tool schemas; it does what vLLM does
before rendering (loads each tool call's `arguments` from its JSON string) and
what the template does (keeps reasoning only after the last user message). Neither
jinja2 nor transformers is a dependency, so the copy is checked three ways:
`tests/agent/test_budget.py` renders the real template with Jinja the way
transformers does and compares byte for byte (12 conversations, run with
`uv run --with jinja2 pytest tests/agent/test_budget.py`; skipped otherwise);
transformers 5.17's own `render_jinja_template` gave the same string on 18
conversations; and on Token Factory itself the chat endpoint's `prompt_tokens`
equalled the completions endpoint's for our rendered string, 433 and 1,733, on a
two-message conversation and on a five-message one with a tool call, a tool
result and all eight schemas of the time. transformers' `continue_final_message=True` would
end the prompt at `</think>`; ours ends `</think>\n\n`, which is what the model
emits itself before its answer.

**Measured live on Nano.** A chat call with `max_tokens` 200 on "load
a 96-well PCR plate; look up the load name with the labware tool first" was cut
(454 in, 200 out, `finish_reason` `length`, reasoning "We need to use the labware
tool to get the real load name ... The description says "real load names for one
kind of labware, with how many wells each has and the"). The continuation with
2,000 tokens took 657 prompt tokens (454 + the 200 + the closing) and answered in
24 tokens, `finish_reason` `stop`: exactly one `<tool_call>` block, parsed to
`labware` with `{"kind": "plate"}` and empty content. The whole exercise, probes
included, was 5,443 prompt and 228 completion tokens on Nano.

**Gaps.** The loop calls this where `finish_reason == "length"` and the reasoning is
non-empty (`loop.py`), and the evaluation runs Nano with it on. The `network` mark is
not registered in `pyproject.toml`, so pytest warns about it. `render()` covers the
shapes our loop sends and the template's defaults (thinking on, old reasoning
dropped); a message with list-shaped content, or `enable_thinking: false`, is not
rendered. A malformed tool call in the continuation comes back as plain content,
which the loop treats as an idle turn. This measured only that a cut turn yields a
parsed tool call; the verified counts are in `eval/agent/README.md`.
