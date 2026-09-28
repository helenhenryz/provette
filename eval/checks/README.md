# eval/checks/ — do the checks tell a right plate from a wrong one?

No model is called here. The protocols under [`protocols/`](protocols/) were written by us
before the checker existed, in a session that never saw Provette's code or checks, for the 17
requests that have a plate map, in two wordings (`plain/`, and `short-on-tips/` with "We are
short on tip racks this month: use as few tips as possible"). The plate maps (`eval/platemaps/`)
were written from the request text alone before any of these protocols was opened. So this
measures the checker, not a model.

## What is asked, and how

1. **Correct protocols against their own maps** (`run_correct.py`): `provette verify` on all 34.
   A correct protocol must verify, every expected well within tolerance, with no accounting or
   prep flag. `measure_tolerance.py` says how far the found amounts are from the maps.
2. **The same protocols against the wrong maps** (`control.py`): each plain protocol against the
   map of a different request, twice over. None may verify.
3. **The prep sheet by hand** (`run_hand.py`): the starting volume of every source well and the
   tip counts of ten protocols, worked out from the loop counts and constants in the source, the
   derivation in the file, against `provette/intent/prep.py`.
4. **Planted bugs** (`mutate.py`, `run_mutants.py`, `tabulate.py`): five mechanical edits on the
   syntax tree of the 17 plain protocols: **a** halve, double or raise by 10% a number that
   feeds a transfer volume; **b** drop the last item of a list, slice or range; **c** reverse or
   rotate the sources of a `zip` or a transfer; **d** draw from another declared liquid's well;
   **e** send the first or second execution of a dispense into the trash. At most 9 per edit per
   protocol, drawn with a fixed seed. A bug that leaves the deck exactly as it was is
   *equivalent* (there is nothing to catch); one that changes what a well holds, passes the
   simulator and is flagged by nothing is a *miss*.

```
env -u PYTHONPATH uv run python eval/checks/run_correct.py
env -u PYTHONPATH uv run python eval/checks/measure_tolerance.py
env -u PYTHONPATH uv run python eval/checks/control.py
env -u PYTHONPATH uv run python eval/checks/run_hand.py
env -u PYTHONPATH uv run python eval/checks/run_mutants.py
env -u PYTHONPATH uv run python eval/checks/tabulate.py
```

## The limit it is built to show

"Set up PCR reactions for 8 DNA samples" does not say which sample goes in which well. A plate
where samples 1 and 8 have changed places is *a* correct plate for that request; it is wrong only
against a layout sheet the request never mentioned. A map that leaves positions free therefore
verifies it, and says so with a note ("not in the order of their numbers"); a map that pins
positions catches it as a mismatch (D-27).

## Results

| question | result |
|---|---|
| correct protocols against their own maps | **34 of 34 verify**, 986 wells, no accounting or prep flag |
| how far from the maps | of 2,040 expected amounts, the furthest off is 0.0048 µl (0.10%), a normalisation volume rounded (`results/tolerance.json`) |
| the same protocols against the wrong maps | **0 of 34 verify** (33 cannot bind the map's liquids, 1 mismatch) |
| the prep sheet against one worked out by hand | **10 of 10 agree**, source well by source well and tip rack by tip rack |

The planted bugs (`results/table.txt`; the columns overlap: one bug can be flagged by several checks):

| planted bug | planted | passed the simulator | flagged | not flagged | of which nothing to catch | of which missed |
|---|---|---|---|---|---|---|
| a volume halved, doubled or raised by 10% | 108 | 85 | 83 | 2 | 2 | 0 |
| the last item of a list dropped | 31 | 29 | 29 | 0 | 0 | 0 |
| sources reordered | 47 | 38 | 16 | 22 | 6 | 16 |
| drawn from the wrong liquid | 16 | 16 | 16 | 0 | 0 | 0 |
| a dispense sent to the trash | 77 | 74 | 68 | 6 | 6 | 0 |
| **all** | **279** | **242** | **212** | **30** | **14** | **16** |

Of the 30 not flagged, 12 leave the deck exactly as it was and 2 more change nothing the request
asks about (which BSA standard of column 1 is declared where): 14 with nothing to catch. So of
the **228 bugs that change what a well holds, all passed by the simulator, 212 are caught**. The
16 that are not are one class: samples swapping wells on a plate whose map leaves positions
free, each of which gets the "not in the order of their numbers" note. Every bug that throws a
sample away is caught (31 of 31), with the sample's name and where it went. The plate-map
comparison flags every bug that is caught; the accounting, the prep sheet and the rules say why.

## What this does not show

* That models write these bugs: the protocols here are correct; the bugs were planted.
* Anything about physics: ideal mixing, exact volumes, no droplets. "Verified" means the logic
  delivers the plate.
* Small errors: the planted volumes are x0.5, x2 and +10%; nothing between the tolerance and 10%.
* The 13 requests without a map (bead clean-ups, washes, cell work), where the intent is about
  what is removed and when, not only what ends in a well.
