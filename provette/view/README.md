# `provette/view` — the deck replay

One web page that plays a protocol back on the robot's deck, step by step, and
shows where the biology goes wrong. It is what a person opens after `check`
and `verify` have run, and it is the demo.

```
provette view protocol.py --out replay.html
provette view protocol.py --platemap map.json --out replay.html   # adds verify and the prep sheet
provette view protocol.py --labware-dir my_labware/ --out replay.html
```

The result is one HTML file with everything inside it: no library, no network,
no build step. It opens offline in any current browser. Exit codes: 0 written,
2 the simulator rejected the protocol, 3 the plate map could not be read.

## What the page shows

**The verdict**, at the top: "The Opentrons simulator (8.8.2) passed this
protocol. Provette found 2 biology problems (2 errors)." and, with a plate map,
"VERIFIED: 8 of 8 wells hold what plate map pcr-01 says" or the mismatch
count.

**The deck**, seen from above: the twelve slots of the OT-2 in their real
layout (1 to 3 at the front, 10 and 11 at the back, the trash in 12), each
loaded labware drawn with its real wells, at the positions in its labware
definition, and labelled with its slot number and the name the author gave it
(or its display name). A tip rack shows its tips: dark for a fresh tip, empty
once it has been used and thrown away, hatched for a used tip put back in the
rack.

**The scrubber**: play and pause, one step back or forward, a slider, a speed
control; the arrow keys step, space plays, Home and End jump. At each step the
page says what happened in one line ("Step 6 of 34, line 30, at 0:08: aspirate
10 µl from tube B2 in slot 2, tip A1"), says what the tip holds and what it has
touched, and marks the line in the protocol's source, shown in a panel below.

**What the wells hold.** Every well is drawn filled to a height for its volume:
in the product's replay (`web/src/replay/`) the height the ledger's own table
gives it (see "The well's shape" below), and in this standalone page the volume
over the well's maximum. The colour says where the liquid started: each origin
(a tube or well that held liquid before the robot moved anything) gets a
colour of its own, listed in the legend with the liquid's declared name, or
"the liquid from tube B1 in slot 2" when the protocol declared nothing. A well
holding liquid from several origins shows stacked bands, each as tall as its
share of the volume (ideal mixing). A liquid that is only present as the film a
used tip left behind (carry-over) has no volume, so it is drawn as hatched
stripes in its colour over the well: that is what contamination looks like as
it spreads. Anything the model is not certain of (the tip may or may not have
touched the liquid) is drawn faint. Hover a well to read all of this in words.

**The tip** is drawn above the well the pipette is in, with the residue it
carries as bands, so you can watch a dirty tip enter the stock. An 8-channel
pipette shows eight.

**The close-up**: a large drawing of one labware, following the pipette (or
pinned by clicking a labware on the deck), since a 96-well plate is small on
the deck.

**The findings**: the list `provette check` prints, with severity, title,
explanation and fix. Click one and the scrubber jumps to the step that did the
damage, the affected wells get a red outline, the wells the damage later
reached get a fainter orange one, and the line is marked in the code. With a
plate map, the wells that do not hold what the map says are listed after the
findings; clicking one jumps to the end of the run.

**The prep sheet**, with a plate map: the same table `provette verify` prints
(what to load where, how much at least, what was declared, and the flags), the
tip count, and the full verify report as the terminal would print it.

**The footer**: this checks the logic of the protocol, not the physics.

A link can name a moment: `replay.html#step=12` opens at step 12,
`replay.html#finding=1` opens on the first finding.

## How it is built

```
provette/view/geometry.py   slot and well positions in mm, from the Opentrons definitions
provette/view/export.py     CheckResult (+ Verification) -> one JSON object
provette/view/page.py       the JSON pasted into page.html with replay.css and replay.js
provette/view/cli.py        `provette view`
```

`export` turns the trace, the replayed state and the findings into one JSON
object; `render` pastes it into the page template together with the style and
the script. The Python side does all the reading and all the words; the script
only draws. The script is a plain file, so `node --check` parses it in the
tests.

### In the product's frame

The product's replay is its own React component now (`web/src/replay/`, fed by the same
export); this page is what the product's "open the replay" link serves in a new tab, with
`?compact=1` (and `?embed=1`, `?theme=dark`, which `api/replay_page.py` answers). The
`provette:height` message it posts was for the earlier iframe and nothing listens to it now. Compact is the page's own mode, in `replay.css` under
`html.compact` and set by `render(data, compact=True)` or by the query string alone: the
product's type scale and colour tokens, tighter margins, and labware labels drawn at no less
than 11 px on screen. A label is drawn in the deck's own units (5 mm, about 8 px in the frame), so
`fitLabels` in `replay.js` works out how many units 11 px is from how wide the deck is drawn,
cuts a label the labware cannot hold at that size, and does it again on resize; the full name is
in the table below the deck and in the close-up's title. In a frame the page also posts
`{type: "provette:height", height}` to its parent once laid out, on resize and whenever its
height changes (a taller close-up, the prep sheet unfolded), so the frame can be that tall
instead of guessing.

### Where the positions come from

The trace carries each well's depth, shape, diameter and maximum volume, but
not where the well is on the plate. `geometry.py` reads that from the labware
definition: the custom folders given with `--labware-dir` first, then every
version of the definition shipped in `opentrons_shared_data`, newest first, and
takes the first whose wells match the trace's geometry exactly (same names,
depth, volume, diameter or sides). If none matches, the wells are laid out on a
regular grid from their names and the page says on the labware that "well
positions are a guess". The slots come from the OT-2 deck definition
(`ot2_standard`, version 5). The trash is a bin that rises above slot 12; it is
drawn as slot 12's box.

### The well's shape

Every well row carries, beside its outline (`shape`, `d` or `w` and `h`, `depth`,
`max`), two fields from the trace's `WellGeometry` (`provette/model.py`): `bottom`,
the definition's word for the bottom of the well ("flat", "u", "v", or null when
the definition says nothing), and `height_at_ul`, the ledger's own table of
`[µl, mm]` rows rising from `[0, 0]` to the brim, worked out by the tracer from
the definition's `innerLabwareGeometry` (D-14: the newest version of a standard
labware lends its shape), or null when no definition gives the shape. It is the
same table the state's contact model and SOURCE-TOO-SHALLOW compute with
(`provette.state.contact.surface_mm`): straight lines between rows, the brim's
height past the last row. The product's replay draws the liquid at that height
(`state.ts` `heightAt`, `wellFill`) and turns the well's outline from the table
read the other way (`scene.ts` `unitProfile`: the slope of the table over a slice,
µl per mm, is the well's cross-section there), so a 20 µl drop sits in the point
of a V-bottom well. The `schema_version` is 2 since these fields were added;
a reader of a schema 1 export finds them absent and falls back to
the volume over the maximum. `replay.js`, this page's own script, does not read
them yet.

Every event also carries `mount`, the pipette that acts (`"left"` or `"right"`, or null for
a delay or a module step), from the trace's own `Event.mount`; the `schema_version` is 3 since
it was added. The product's 3D replay reads it to put each pipette on its own mount and lower
only the one that works; a reader of an older export finds it absent and draws the first
pipette as the one that works.

### How the deltas work

A page that stored every well after every event would be events x wells in
size. Instead it stores, for every event, only the wells whose contents changed
at that event, straight from `run.history`, with the well's new volume and its
band list: `[origin, volume_ul, mode, certain]` per origin present, mode 0 for
liquid pipetted in and 1 for carry-over, volume `null` when it cannot be known.
The state before any event (`initial`) is the origins with their declared
volumes. The script rebuilds the state at position *p* by applying the deltas
of events 0 to *p*-1 to the initial state, keeps a full copy every 50 events
so that seeking is fast, and while playing applies one delta per step.

The same delta holds the tip-rack positions whose status changed (picked up,
put back, thrown away) and the tips whose residue changed. Residue is derived
from the run's contacts by the state's own rule (a tip gains everything in a
well it touched; a parked tip keeps it; a dropped tip is gone) rather than
re-run, and a test holds it to `run.tips`. The volume a tip holds after each
event sits on the event row, since it changes at nearly every step.

`export.replay_deltas` applies the deltas in Python exactly as the script does.
The tests hold its answer to `run.wells` at the end and to
`run.well_before(well, p)` at every position for a hand-built trace and at
several positions for the two PCR fixtures. That is the test that the script's
logic is right, since the script does the same thing; the script itself is
parsed, not executed, in the tests.

### The colour rules

* One colour per origin, in the order the replay found them: twelve
  colour-blind-safe colours first (Okabe-Ito, then Tableau), then hues spaced
  by the golden angle.
* Solid band: liquid that was pipetted in; its height is its share of the
  well's volume. A bulk arrival of unknown amount shares the height equally.
* Hatched stripes in the origin's colour: only a film from a used tip, no
  volume. Drawn over the liquid, or over the bottom third of an empty well.
* Faint (45 % opacity): the presence rests on a contact the model could not
  decide (`certain=False`).
* A dotted outline: the well's volume is not known (an undeclared well the
  robot drew from); the fill shows the lower bound.
* Severity colours: red for an error, orange for a warning, blue for a note;
  the finding's wells are outlined red, the wells it reached later orange and
  dashed.

## What is not shown

Measured on the public library: every protocol the tracer accepts exports but one, which
runs past the sweep's time limit; what the page has to guess or
leave out, with counts, is in [`docs/replay-support.md`](../../docs/replay-support.md).

* **Physics.** Nothing about how a liquid behaves: no droplets, no meniscus,
  no accuracy. In this standalone page fill heights are volume over the well's
  maximum, not the real height in a conical well; the product's replay uses the
  well's own table ("The well's shape").
* **A channel over no well.** When an 8-channel pipette works on labware with
  fewer than eight rows the trace lists the tips that entered wells; the
  others are not drawn.
* **Modules' footprints.** Labware on a module is drawn in the module's slot at
  the slot's corner; the module's own offset and, for a thermocycler, the
  slots it covers are not drawn. `move_labware` does not move the drawing.
* **What is inside the tip**, beyond its volume and residue: the layers are
  not drawn.
* **Time at temperature** and thermocycler programmes.

## Size and speed, measured

`provette view`, simulator included:

| protocol | events | page | time |
|---|---|---|---|
| `tests/fixtures/protocols/pcr_buggy.py` with `eval/platemaps/pcr-01.json` | 34 | 99 KB | 1.0 s |

Nearly all of the time is the simulator; `export` and `render` take under
0.02 s for these. Two library traces, exported without the simulator: 1,985 events and 3,779 arrivals gave 1.9 MB in 0.19 s; 2,715
events and 1,924 arrivals gave 2.3 MB in 0.32 s. The size grows with the number
of (event, well changed) pairs times the wells' band lists; the heaviest
library protocol (25,188 events, 5.8 million arrivals) would not fit in a page
and was not tried.

Both demo pages were opened in headless Chrome (`google-chrome --headless=new`)
with console logging on: no console messages, and screenshots at the first
finding show the deck, the outlined wells, the marked line, the close-up and
the prep sheet as described above. The tests parse the script with
`node --check` and check that the page loads nothing from outside itself.
