# What the deck replay draws, measured on the public library

Measured on the public Opentrons protocol library at the pinned commit
(`provette/corpus/library.py`; 833 protocols, all written for the OT-2 by people who are not
us). Every protocol went through the tracer with its cross-check
(`provette.corpus.workers:trace_worker`) and through the replay export
(`provette.corpus.workers:export_worker`, the JSON `provette view` and the product's pages draw
from). The raw rows are a result over library files we do not commit (D-05), so they are not in
the repository. To measure again:

```
env -u PYTHONPATH uv run provette corpus run --worker provette.corpus.workers:trace_worker --jobs 10
env -u PYTHONPATH uv run provette corpus run --worker provette.corpus.workers:export_worker --jobs 10
```

## The table

| step | protocols | of |
|---|---|---|
| in the library | 833 | |
| the simulator and the tracer accept | 788 | 833 |
| Opentrons' analysis agrees with the ledger (D-09) | 788 | 788 |
| of those, a fully independent reading: API 2.14 and later (D-10) | 16 | 16 |
| the export succeeds | 787 | 788 |

The 45 the tracer refuses are not the replay's fault: 28 reach into private or removed internals
of an older Opentrons, 4 use a tip type the 8.8 simulator lacks, 3 declare an API level too low, 2
name a labware no definition covers, 2 load labware too tall for the deck, and 6 others. One
protocol the tracer accepts, `5520f0`, does not export within the sweep's time limit.

What the export holds: median 423 events, 95th percentile 4,615, the largest 31,994 (`2a370c`,
a 9 MB export). An 8-channel pipette in 512 protocols; no pipette at all in 7 (they run a
module, or nothing). A magnetic module in 238, a temperature module 237, a thermocycler 73, a
heater-shaker 9.

## What it draws

Every labware at its real footprint with its wells where its definition puts them: none of
the 787 falls back to the guessed grid ("well positions are a guess"), because the library
ships a definition for every custom labware and the export reads that folder. Every liquid
the run knows, coloured by where it started, at the height the ledger's own table gives it
(`provette/view/README.md`, "The well's shape") when the definition has one; the tips in
their racks, in use, put back or gone; the pipette, single or 8-channel, with what it holds;
the bin with the tips dropped in it and the volume blown into it. A 384-well plate draws in
both views with its row and column labels, and the close-up follows the pipette to it.

## What it does not draw, and why

Each with its count, what it looks like on the page when it happens, and what would make it
drawn. None of these is a wrong drawing: it is a place where the page has less than the truth.

**A well with no height table** (513 protocols; a custom definition, or a shipped one such as
`opentrons_96_aluminumblock_nest_wellplate_100ul`). A definition written
by hand carries no inner geometry, and some shipped ones do not either. On the page: the well
is a straight column and the liquid is drawn as the volume over the maker's rated maximum, so
20 µl in a conical tube sits as a thin band at the bottom rather than in the point. To draw
it right: a table for that definition (D-14 lends the newest shipped shape to a standard
labware; a custom one would need its shape declared or measured).

**A liquid nothing declared** (779 protocols; 8 of the 787 declare any liquid). The library
mostly declares no liquids, so a well the
robot draws from holds an unknown amount. On the page: the well shows "not tracked" in the
legend's sense, drawn at least a quarter full, and hovering it says "at least N µl". To draw
it: `load_liquid` in the protocol, or a plate map.

**Modules** (238 magnetic, 237 temperature, 73 thermocycler, 9 heater-shaker; 25 more
protocols run a module with nothing loaded on it). The trace records a module only as the
`module` of the labware on it, and never records one with nothing on it. On the page: the
labware sits in the slot's box like any plate; no module body, no thermocycler lid, and the
three other slots the thermocycler covers look empty (`010526` shows it). A module with
nothing on it is not there at all, and its events read as one line ("Engaging Magnetic
Module", "set the temperature module to 4 °C"). To draw them: the trace would record every
loaded module with its model and slot, and the page would carry a footprint per model. A
design decision, not built here.

**The thermocycler's programme, the lid, and time at temperature.** A profile is one event
("run a thermocycler programme (its steps are not modelled)"); the lid's opening and closing
are one line each (75 protocols move it). Nothing is drawn.

**A protocol that moves nothing** (13 protocols, 19 with no well named: a cherry-pick with
no CSV given, a module-only run). On the page: the deck as loaded and "No events: the
protocol moved nothing." That is the truth of the run, not a gap.

**A contact the model could not decide** (90 protocols): the liquid is drawn faint, as the
state's README says. Not a gap in the drawing; a gap in what can be known from the trace.

**Custom labware on the product's check page.** Most library protocols that use custom labware
ship its definition beside the script. `provette view --labware-dir` and this sweep read that
folder; the product's check page takes only the protocol text, so such a protocol is refused by the
simulator there ("Unable to find a labware") and never reaches the replay. A data path (a
labware upload beside the protocol), not built here.

**Out of scope.** The Flex deck: the export draws the OT-2's twelve slots (`ot2_standard`),
and no protocol in the library at this commit declares a Flex (`robotType`). `move_labware`
would not move the drawing (D-09); no library protocol uses it.
