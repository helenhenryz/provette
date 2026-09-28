# eval/planner/ — can the model propose the plate map?

The 17 hand-written plate maps of [`eval/platemaps/`](../platemaps/build.py), reproduced from
their requests alone by [`provette/planner`](../../provette/planner/README.md), and every
difference read. The planner works as it does in the product: 12 tool calls and 40,000 tokens a
plan, and it may call `not_a_request` (D-33), so a real request it turns away is counted.

`run.py` plans each request, then holds the planned map against two things: the hand-written
map, structurally (`provette.planner.agree`: liquids and roles, amounts within `tolerance_ul`,
pinned against free), and the correct protocol for that request
(`eval/checks/protocols/plain/<id>.py`), with `provette verify` run on the planned map. A
planned map that is right verifies it; one that is wrong does not. `--rescore` recomputes both
from the stored maps without the network. The run is repeated three times, because one plan per
request says little about variance.

```
env -u PYTHONPATH uv run python eval/planner/run.py --out eval/planner/results/super
env -u PYTHONPATH uv run python eval/planner/run.py --out eval/planner/results/super-run2
env -u PYTHONPATH uv run python eval/planner/run.py --out eval/planner/results/super-run3
```

Each `results/<dir>/<id>.json` holds the planned map, the transcript, every refusal and repair,
the agreement, the `verify` report and the token counts; `<id>.platemap.json` is the planned map
alone; `summary.md` is the printed table. The Methods page quotes `results/super`.

## Results

| run | valid map | agrees with the hand-written map | **verifies the correct protocol** | cost |
|---|---|---|---|---|
| `results/super` | 16 of 17 | 11 | **14 of 17** | $0.10 |
| `results/super-run2` | 17 of 17 | 13 | **15 of 17** | $0.08 |
| `results/super-run3` | 16 of 17 | 12 | **14 of 17** | $0.13 |

Across the 51 plans the planner never called a real request "not a request". The maps that do
not verify, every one read:

* **fill-02, every run: a miscount.** "48 aliquots" came out as 55 members; `verify` finds 48 of
  55 wells right and says so. The planner miscounts when it writes a long list out.
* **pool-01, every run: pooling misread.** The 48 libraries were put one to a well instead of all
  48 into the one pool tube; `verify` finds 0 of 48 wells right.
* **elisa-01 (run 1) and pcr-03 (run 3): no map.** Each used its 12 tool calls without handing a
  valid map in, so there is nothing to verify and the page says the planner stopped.

Every wrong map fails `verify` against a correct protocol, which is what the check is for (D-29);
a person approves the map before anything is written.
