# eval/agent/ — Nemotron writing protocols with the checks as its tools

The model gets a request and its plate map, and works through the loop in `provette/agent`
([README](../../provette/agent/README.md)): it reads the plate map, looks up the labware, calls a
calculator for any arithmetic, hands in drafts, runs the checks itself, repairs from their
report, and submits. It works with the product's settings (`api/run_settings.py`): 25 tool
calls and 100,000 completion tokens an episode, and a draft the checks reject is not taken as the
answer before the third (D-32). Nemotron runs on Nebius Token Factory; the checks run on this
machine (`--runner local`) or in a Token Factory Sandbox (`--runner sandbox`).

**Verified and clean** means the last checked draft passed the simulator, every well of the plate
map, the sample accounting and the prep sheet, and none of the twelve rules fired with an error or a warning. The
first draft is judged the same way, which is the "on its own" column: what the model writes
before any report comes back.

## The runs

| set | model | requests | how |
|---|---|---|---|
| `results/super` | Nemotron 3 Super 120B | the 17 with a map, in both wordings: 34 | one episode each |
| `results/nano-best3` | Nemotron 3 Nano 30B | the same 34 | best of 3: three episodes at once, the checks pick the one that verified (`--candidates 3`); the cost is all three |
| `results/super-hard` | Super | the 15 of `eval/requests-hard/` | one episode each |
| `results/nano-hard-best3` | Nano | the same 15 | best of 3 |
| `results/super-sandbox` | Super | three requests, plain | every check in a Token Factory Sandbox |

```
env -u PYTHONPATH uv run python eval/agent/run.py --model nvidia/nemotron-3-super-120b-a12b \
    --out eval/agent/results/super
env -u PYTHONPATH uv run python eval/agent/run.py --model nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B \
    --out eval/agent/results/nano-best3 --candidates 3
env -u PYTHONPATH uv run python eval/agent/run.py --model nvidia/nemotron-3-super-120b-a12b \
    --out eval/agent/results/super-hard --requests eval/requests-hard \
    --platemaps eval/requests-hard --conditions plain
env -u PYTHONPATH uv run python eval/agent/run.py --model nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B \
    --out eval/agent/results/nano-hard-best3 --requests eval/requests-hard \
    --platemaps eval/requests-hard --conditions plain --candidates 3
env -u PYTHONPATH uv run python eval/agent/run.py --model nvidia/nemotron-3-super-120b-a12b \
    --out eval/agent/results/super-sandbox --conditions plain --ids pcr-01 dil-01 norm-01 \
    --runner sandbox
env -u PYTHONPATH uv run python eval/agent/tabulate.py eval/agent/results/*
```

Each episode is written under `results/<set>/<condition>/<id>/`: every draft, every check, the
transcript and `done.json`. The run also leaves a `replay.html` beside each; it is not kept in
the repository (the app draws the replay from the episode, and `provette view` makes the page). The Examples page shows the first four sets as they are.

## Results

| set | model | verified and clean | on its own (first draft) | cost | per verified protocol |
|---|---|---|---|---|---|
| `results/super` | Super 120B, 34 requests | **31 of 34** (91%) | 1 of 34 | $1.35 | $0.044 |
| `results/super-hard` | Super 120B, 15 harder | **12 of 15** (80%) | 2 of 15 | $1.16 | $0.097 |
| `results/nano-best3` | Nano 30B, best of 3, 34 requests | **25 of 34** (74%) | 0 of 34 | $4.90 | $0.196 |
| `results/nano-hard-best3` | Nano 30B, best of 3, 15 harder | **8 of 15** (53%) | 0 of 15 | $2.30 | $0.287 |
| `results/super-sandbox` | Super 120B, 3 requests, checks in a Sandbox | 2 of 3 | 0 of 3 | $0.27 | $0.134 |

The same model with the rules written into its prompt and no checker verifies 7 of 34
(`eval/baseline/README.md`). The first draft is rough because in the loop the model writes fast
and leans on the checks; what counts is where the loop ends.

**Every episode that did not verify, read.**

*Super, 34 requests (3):* `plain/pcr-04`, three extra wells of master mix and water past the
plate map (18 of 21 wells right); `short-on-tips/dil-01`, a serial dilution at half the volume
asked, still wrong after 16 drafts; `short-on-tips/pcr-04`, the map verifies but the prep sheet
flags wells the robot draws from after emptying them ("draws air").

*Super, harder set (3):* `hard-bca-01`, 84 of 96 wells right and two mixes too weak, after 18
drafts; `hard-dil-02`, the map verifies but the sample accounting finds the compounds in wells
the map does not list; `hard-qpcr-01`, the map verifies and a used tip still goes into a stock
(a `CONTAM-STOCK` warning) when the 25 tool calls run out.

*Nano, 34 requests (9):* eight end on the token budget, reasoning past the 100,000 tokens an
episode may spend: `dil-03` and `short-on-tips/dil-01` (a dilution series never right, or a
simulator error never repaired), `elisa-01` (a simulator error never repaired),
`fill-01` twice (a mix too weak; the reservoir drawn with no margin), `short-on-tips/brad-01`,
`short-on-tips/pcr-04` and `short-on-tips/pcr-07` (wells wrong, with a used tip into a stock or
a trough drawn above its liquid). `plain/dil-01` submitted a series with 1 of 12 wells right.

*Nano, harder set (7):* four end on the token budget (`hard-elisa-01`, `hard-mic-01`,
`hard-pcr-01`, `hard-pcr-03`) and three submitted a draft that still fails: `hard-bca-01` (95 of
96 wells, a used tip into a stock, a volume below the pipette's range), `hard-dil-01` (the map
verifies; the samples also end in wells the map does not list) and `hard-dil-02` (the series
wrong, drawn above the liquid).

*Sandbox (1):* `dil-01` verifies its map but ends on the tool-call budget with a weak mix and a
well at its brim.

So Super's misses are plate-map layouts the loop did not close, prep-sheet and accounting flags,
and one carry-over warning left standing when its calls ran out; Nano's are mostly reasoning
length: it runs out of tokens before the loop closes. Every episode's drafts, checks and
transcript are in its folder, and the Examples page replays them.

## What this does not show

* Physics: the checks judge the logic of a protocol, not whether a viscous liquid pipettes
  accurately.
* That a person would accept every verified protocol: the checks are ours, and the plate maps
  were written by us.
