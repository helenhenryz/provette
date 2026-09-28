# `provette/intent` — does the protocol make the plate that was asked for?

`provette check` looks for biology bugs nobody asked about (a dirty tip in a stock).
`provette verify` answers the other question: the scientist says what each well
should end up holding, and the replay proves or disproves that the script
delivers it.

```
provette verify protocol.py --platemap platemap.json [--json]
```

Exit 0: every well verified and nothing flagged. 1: a mismatch or a flag. 2: the
simulator rejected the protocol. 3: the plate map could not be checked against
this protocol (a liquid or the destination plate could not be found). **3 is not
a pass**, and the report says so.

## The parts

| module | question | how |
|---|---|---|
| `spec.py` | what is a plate map? | frozen dataclasses, JSON in and out, validation with a message that names the field. The format is described at the top of the file |
| `bind.py` | which declared liquid is "sample 3"? | a regex per logical liquid against the names given to `define_liquid`; a capture group for the sample number; or "whatever is declared in well B3 of the source plate" |
| `compare.py` | does each well hold what the map says? | per well, the volume of each starting liquid (the replay's atoms, summed per logical liquid) against the map, within `tolerance_ul`. Position-free groups are matched as a multiset |
| `accounting.py` | where did every declared liquid end up? | delivered where the map wants it, left in its tube, in other wells, or lost (thrown away in a tip, or put in the trash). A sample that loses a whole dose, or ends somewhere the map does not list, is flagged |
| `prep.py` | what must be on the deck at the start? | per source well, the deepest the replay draws it down, against what is declared: "would run dry", "no margin" (over 90%), "draws air" (a well the robot filled is asked for more than it got); and the tips per rack |
| `report.py`, `cli.py` | | the text a student reads, the JSON, the command |

## What it may be relied on for, and what not

* It checks **logic, not physics**: what goes where, and how much, under ideal
  mixing. Not whether 0.5 ul of glycerol stock is pipetted accurately.
* A plate map that leaves positions free cannot see two samples swapping wells:
  every well still holds "one sample plus mix". The `order_hint` gives a note
  when the samples are not in the order of their numbers; it is not a mismatch.
* Volumes come from what the protocol **declares**. If a protocol declares less
  than it uses, the replay runs the tube dry, the late wells come up short, and
  both `compare` and `prep` say so. If the declaration is the thing that is
  wrong, the fix is the declaration.
* "draws air" counts every short draw, so a mix repeated five times in a well
  that is short is counted five times: the flag is right, the number is an upper
  bound.
* Matching a position-free group is exact-signature first, then nearest well (by
  shared liquids, samples first) to explain what is wrong. That was enough for
  every case in `eval/checks/`; it is not an optimal assignment, and two wells that
  are each wrong in the same liquid may be explained the other way round.

Measured in [`eval/checks/`](../../eval/checks/README.md).
