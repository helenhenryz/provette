# `provette/state` — where every liquid went

The trace says what the robot did. This module replays it and works out what
that did to the liquids: what is in every well and on every tip after each
step, where each liquid started, which step first carried it somewhere new,
and how long it sat at what temperature.

It is ordinary Python. It never imports Opentrons (a test checks), reads no
files, calls no model, and gives the same answer every time. It never decides
whether something is a *problem*: that is the rules' job. It only says what
happened, and how sure it is.

```python
from provette.model import Trace
from provette.state import replay

run = replay(Trace.load(path))
```

## The ideas, in bench terms

**Origin.** A well that already held liquid before the robot moved anything: a
sample tube, a reagent bottle. Every liquid on the deck is followed back to its
origin, and the origin's well is the liquid's id. There are two kinds.

* *Declared*: the protocol said what is in the well and how much
  (`load_liquid`). Only 11 of the 833 library protocols do.
* *Implicit*: the protocol said nothing, but at some point it asks the well
  for more liquid than the robot has put into it. **A well that gives more
  than it ever got was holding something.** A reagent tube the robot only
  draws from is the plain case. The commonest case in the library is a sample
  plate that arrives full: the robot adds 8 uL of reagent to a well and then
  mixes with 45 uL. We do not know the liquid's name or its volume, and the
  well is treated as an origin **from the start of the run**, including the
  steps before the one that gave it away (DECISIONS.md D-15).

**Two regimes.** "Gives more than it got" is applied in full only to a
protocol that declares *no* liquids, which is nearly all of the public library.
A protocol that declares liquids has told us what is on the deck: its other
wells start empty, and a well the robot filled with 30 uL and then asks for
40 uL is that protocol's own shortfall (`aspirate_exceeds_volume`), not a
hidden sample. The one exception is a well drawn from before the robot has put
anything in it at all, which held something whatever else was declared. Every
protocol our agent writes must declare its liquids, so there a shortfall stays
a finding.

The state never decides that two origins are "the same liquid", or what kind
of thing an origin is. That belongs to the manifest and the rules.

**Bulk and carry-over.** Material reaches a well in one of two ways. *Bulk*: it
was in the liquid the robot dispensed. *Carry-over*: it was only a film on a
tip that dipped into the well. A well that got something by carry-over and
later gets it in bulk is recorded as bulk.

A bulk arrival with a volume of `0.0` is a *trace*: the dispensed liquid came
from a well that itself only held a film of that material. It is how one dirty
tip in the master mix ends up, correctly, in every well the master mix goes to.

**Residue.** Everything that has wetted a tip, inside or out. A new tip has
none. A tip put back in the rack keeps its residue, and picking up that rack
position again gives the same dirty tip: "tip parking" is common in the public
library and is exactly where contamination hides. A tip dropped in the trash
is gone; if that rack position is picked up again it is a new tip.

**Contact.** A tip contaminates a well, and is contaminated by it, only when it
touches the liquid. When it does, residue flows both ways: the well gains
everything on the tip, the tip gains everything in the well. Deciding whether
it touched is the hard part, and is the next section.

**Certain and uncertain.** Sometimes the model cannot tell whether the tip
touched the liquid. It then assumes it may have, and marks everything that
follows from that as not certain (`certain=False`), so a rule can downgrade the
finding and say why. A later, certain, route to the same place upgrades it.

## The contact model

Liquid height comes from the well's geometry in the trace (`contact.py`). Where
the labware definition gives the well's real shape, the trace carries a small
volume-to-height table (`WellGeometry.height_at_ul`) and the height is read
off it; otherwise the height is volume divided by the well's cross-section, as
if the well were a straight-sided column. The tip height comes from the trace.
A tip at or below the surface, or within 0.1 mm above it, is touching.

Real wells are often conical or round at the bottom, so real liquid sits
*higher* than the column says. Without the table the column height is a
floor: "tip below the column height" is safe to call contact; "tip above it"
is not safe to call dry. With the table, or where the definition says the
bottom is flat (`bottom_shape`), the height **is** known and both calls are
safe. That asymmetry is behind several rows below.

| # | case | verdict | what moves | why |
|---|---|---|---|---|
| 1 | Aspirate that belongs to an `air_gap` call | no contact (`air_gap`) | air into the tip | An air gap is taken in air by definition. With dispenses from above, these were most of the 117-of-150 false alarms in D-12 |
| 2 | Aspirate with the tip at or above the well top | no contact (`tip_at_or_above_well_top`) | air into the tip | The hand-written air gap, `aspirate(10, well.top())`. Liquid cannot be above the top |
| 3 | Aspirate from a well known to be empty | no contact (`well_empty`) | air; anomaly `aspirate_from_empty_well` | There is nothing to touch. The well keeps its film: its provenance is not erased |
| 4 | Aspirate, tip at or below the modelled surface | contact (`tip_below_surface`) | liquid, ideally mixed | The column under-reports height, so this is safe |
| 5 | Aspirate of more than 0 uL from a well of unknown volume, below the top | contact (`draws_liquid_volume_unknown`) | liquid | A pipette that draws liquid has its tip in the liquid. This is what makes the 822 undeclared library protocols checkable at all |
| 6a | Aspirate of more than 0 uL, volume known, height known (a table or a flat bottom), tip *above* the surface but below the top | no contact (`tip_above_surface`) | air into the tip; the well keeps its liquid; anomaly `aspirate_above_liquid` | The pipette is sucking air: 2 ml in a 195 ml trough is 1.2 mm deep and falls below a tip at 1 mm after 46 draws of 18 uL. `SOURCE-TOO-SHALLOW` reports it |
| 6b | The same with the height *not* known (no table, bottom not flat), tip above the column height | **unknown** (`tip_above_column_height`) | liquid; anomaly `aspirate_above_liquid` | See "One departure from the brief" below |
| 7 | Dispense or blow-out with the tip at or above the well top | no contact | the liquid arrives in bulk; the tip gains nothing | The other half of D-12: filling many wells from above with one tip is clean |
| 8 | Dispense, volume known | compare the tip with the surface **after** the dispense, counting every channel of the event | bulk, plus residue both ways if contact | The surface rises to meet the tip. 10 uL into an empty PCR well leaves a tip at 1 mm dry; the next 40 uL wets it |
| 9 | Dispense into a well of unknown volume, below the top | **unknown** (`volume_unknown`) | the liquid certainly arrives; residue flows both ways marked uncertain | We cannot know where the surface is. No proof of contact exists as it does for an aspirate |
| 10 | Dispense, tip above the modelled surface | no contact (`tip_above_surface`) | bulk only | The plan's rule. **Under-reports** in conical wells that have no table; see below |
| 11 | `touch_tip` | no contact (`touches_wall_only`), recorded | nothing | It touches the wall above the liquid |
| 12 | `blow_out` | as a dispense of whatever liquid is left in the tip | | It pushes out what the tip holds and nothing more |
| 13 | No height in the trace, or no geometry | aspirate that draws: contact (`draws_liquid_height_unknown`); otherwise unknown (`no_height`, `no_geometry`) | | Same reasoning as rows 5 and 9 |
| 14 | No tip on the pipette | no contact (`no_tip`); anomaly | nothing | Nothing can move without a tip |

A mix is a run of aspirates and dispenses in one well and needs no rule of its
own.

### One departure from the brief (D-13), now only where the geometry is unknown

The brief for this module said that an aspirate whose tip is above the *known*
liquid height drew air and moved nothing. Built on the column alone, a protocol
that declares 20 uL of sample in a 1.5 mL tube and aspirates at the default
1 mm would move nothing at all, because a column 8.7 mm wide holds 20 uL at
0.34 mm. The real tube is conical: the definition's shape puts 20 uL at
2.25 mm, and the tip is in it. Every finding downstream of that sample would
have vanished, silently, and most to the protocols that declare their liquids
properly.

Now the trace carries the definition's shape as a table for 73 of the 137
standard labware (every common plate, tube and reservoir) and the bottom shape
for the rest, and row 6a says what the table says: with 2 ml in a 195 ml
trough the tip at 1 mm is dry after 46 draws, and it draws air. Row 6b keeps
the departure for wells whose shape no definition gives: the liquid moves,
because the protocol asked for liquid from a well that holds some; the contact
is `unknown`; what follows is marked uncertain; and the anomaly is recorded.
A hand-written air gap a few millimetres inside a declared well
(`well.top(-2)`) is now, rightly, air.

### Known ways it is wrong

Under-reports contact (findings lost):

* Row 10, in conical and round-bottomed wells without a table: real liquid is
  higher than the column, so a low dispense we call dry may be wet.
* An undeclared well that never gives more than it got is taken to start
  **empty** (D-15). A plate that in truth already holds sample, to which
  reagent is only ever added, is judged against the added volume alone, and
  its samples have no identity. `replay(trace, implicit_origins=[...])` lets a
  caller who knows better (the manifest) say so.
* Droplets: a dispense from above can splash or leave a hanging drop that
  touches the next well. Not modelled.
* `touch_tip` in a well full enough to reach the touch height.

Over-reports origins:

* Removing supernatant, protocols often ask for more than is there, to be sure
  of getting it all. If the robot itself filled that well, and the protocol
  declares no liquids, we still conclude it
  "was holding something" and give it an identity of its own. The phantom
  origin's material then travels to wherever the supernatant goes, usually
  waste. We cannot tell this from a well that really arrived full.

Over-reports contact (false alarms, all marked uncertain except the last):

* Row 9, when the tip was in truth above the liquid of the unknown well.
* Row 6b, for a hand-written air gap just inside a declared well of unknown
  shape.
* Row 5, the same hand-written air gap inside an *undeclared* well: called
  contact, and certain. Air gaps at or above the top, and all `air_gap` calls,
  are handled.

## Other assumptions

| assumption | reason |
|---|---|
| A well mixes perfectly and instantly. Each aspirate takes every material in proportion | The simplest model that conserves volume. Whether a mix step really happened is a rule's question (family 3), not the state's |
| Carry-over has no volume (`0.0`) | The film on a tip is a fraction of a microlitre and unknowable. What matters is that it is there |
| The tip empties last-in, first-out. Liquid drawn onto liquid mixes into one layer; air stays a separate layer | An air gap sits at the tip opening and leaves first. Proportional emptying gets the volumes of a distribute with air gaps wrong |
| Aspirating more than a well holds takes what is there and the rest is air (anomaly `aspirate_exceeds_volume`). Dispensing more than the tip holds empties it (`dispense_exceeds_held`) | Volume is never invented. Real protocols do this; the replay must finish |
| A well over its maximum volume is recorded (`overflow`), once, when it first happens, and keeps the volume. For an implicit origin only what the robot has net put in is counted, not the lower bound on what it started with | Volume is never invented or lost. The lower bound rests on aspirates that may have drawn air (see "Over-reports origins"), so it proves nothing about overflow |
| A **declared** well asked for more than it holds is never made an implicit origin: it keeps the anomaly. That includes a well declared empty | The protocol said how much is there. Running short is then the protocol's bug, or its declaration's, and either is worth saying |
| Multi-channel: one event, one (tip, well) pair per channel, `volume_ul` each. Aspirates are judged against the surface as the event began, dispenses against the surface once every channel has dispensed. Residue is exchanged channel by channel in channel order | Channels move together. Several channels in one reservoir well is normal |
| A setpoint counts from the moment it is set. Ramp time, the thermocycler lid and `thermocycler_profile` steps are ignored (the last leaves an anomaly `profile_not_modelled`) | The trace carries no structured profile. Keeps the timeline honest about what it does not know |
| Seconds spent inside the tip count as time in the well the liquid came from | They are few |
| A well not in the deck header is created when first used, with no geometry (anomaly `well_not_on_deck`, once per well) | Nothing is dropped silently |

### Unknown volumes, and hindsight

An implicit origin has no known volume, but it has a floor. If a run takes
300 uL out, puts 50 back and takes 30 out, the well held at least 300 uL at the
start: the floor is the deepest the well is ever drawn below its starting
level.

`replay` runs the trace twice. The first pass only looks for implicit origins:
it starts every undeclared well empty, and the moment one is asked for more
than it has been given, marks it and lets its balance go negative. The second
pass is the result: it starts every marked well, from event 0, as an origin of
unknown volume with the deepest point as its floor. So
`WellState.min_volume_ul` is a true lower bound at every step and reaches
exactly zero at the deepest point.

Both passes move exactly the same volumes. Before a well is marked it gave no
more than it had, so nothing was held back; after, it is unknown in both. That
is why the second pass never finds a new origin, and why an undeclared well
never produces `aspirate_exceeds_volume` or `aspirate_from_empty_well`: those
now mean a *declared* well ran short.

**This is hindsight, and it has a price.** What step 5 says about a well can
depend on step 50 proving the well held something: the dispense at step 5 is
judged `unknown` rather than measured against a surface computed from a false
zero. So replaying the first *n* events does **not** always give the first *n*
steps of the full replay: the short replay may not know yet. What holds, and
is tested:

* told the whole run's implicit origins (`implicit_origins=`), the first *n*
  events replay to exactly the first *n* steps, and end in exactly the state
  `well_before(n)` remembers;
* untold, a prefix finds a subset of the whole run's implicit origins, never
  one the whole run lacks;
* no verdict, arrival or step depends on the *floor*.

The first pass follows volumes only, no atoms, so it costs little.

Amounts of a material are `None` when they cannot be known: the origin's own
liquid in a well of unknown volume, and everything drawn from such a well once
other liquid has been dispensed into it. Liquid drawn from an implicit origin
that holds nothing else in bulk *is* known: all of it is that origin.

## What the rules use

`replay(trace, implicit_origins=()) -> Run`. Everything is a frozen value;
nothing needs copying. `implicit_origins` names wells to treat as holding an
unknown liquid from the start whatever the trace shows.

| | |
|---|---|
| `run.origins[well] -> Origin` | `kind` ("declared" or "implicit"), `loads`, `liquid_name`, `initial_volume_ul`, `min_initial_volume_ul`, `first_drawn_event` (the first aspirate that drew liquid from it, or `None`; an implicit origin may be dispensed into before that) |
| `run.steps[i] -> Step` | what event *i* did: `op`, `t_s`, `contacts` (one `Contact` per channel for aspirate, dispense, blow_out, touch_tip), `arrivals` |
| `Contact` | `tip`, `well`, `verdict`, `reason`, `tip_height_mm`, `surface_mm`, and the `liquid_ul` and `air_ul` that really moved |
| `run.arrivals`, `Arrival` | **the raw material of every contamination rule.** `atom` reached `well` at `event_index`, as `mode` "bulk" or "carryover", `certain` or not, on `via_tip`, which last met it in `source_well`. Logged when a material first reaches a well, and again if it improves (carry-over to bulk, uncertain to certain) |
| `run.downstream(atom)` | the first arrival of that origin's material in every well it reached |
| `run.first_arrival(atom, well)` | one of those, or `None` |
| `run.wells[well] -> WellState` | final state: `volume_ul` (or `None`), `min_volume_ul`, `received_liquid`, and `atoms[atom] -> Presence(volume_ul, mode, certain, since_event)` |
| `run.well_before(well, i)` | the same, as it was just before event *i*. `run.history[well]` is the list of (event, state after it) behind it. A stored state's `atoms` is a read-only mapping rebuilt from the well's log when looked at (see "How it stays fast"); use it as the `dict` it stands for |
| `run.tips[tip] -> TipState` | every tip ever used: `status` ("in_use", "parked", "dropped"), `layers`, `residue[atom] -> Residue(source_well, since_event, certain)`. For a dropped tip, the residue it left with |
| `run.anomalies` | odd things that are not errors, with event, well, tip and amount. Never raised |
| `run.time_of(i)`, `run.end_s` | the clock before event *i*, and after the last |
| `run.labware_temperature(labware_id, start_s, end_s)` | `TempInterval(start_s, end_s, celsius)`; `celsius=None` means ambient |
| `run.material_temperature(atom, well, before_event)` | the intervals that material lived through: in its origin, then each well on the way, then `well` |
| `seconds_at_or_above(intervals, celsius, ambient_celsius)` | the rule says what ambient is; the state does not guess |

Following `Arrival.source_well` backwards from any material in any well always
ends at that material's origin. A property test holds the state to that.

## How it is tested

`tests/state/` builds traces by hand (`builder.py`); no simulator is needed.

* `test_scenarios.py`: exact expected arrivals for the buggy and the clean PCR
  set-up, filling from above, air gaps, serial dilution down one row and two,
  tip parking, implicit origins, uncertainty, eight channels, every anomaly.
* `test_properties.py`: hypothesis streams of 12 to 60 legal events. Volume is
  conserved at every prefix; provenance only grows; a fresh tip carries nothing;
  the replay is deterministic, and a prefix told the run's implicit origins
  replays to a prefix and ends in the state `well_before(i)` remembers; an
  undeclared well never runs short, and one that is not an origin really never
  gave more than it got; every material in every well walks back through
  arrivals to its origin; fresh tips plus dispensing from above give no
  carry-over at all.
* `test_digests.py`: a digest of everything a `Run` says, for 26 hand-built
  traces, frozen with the replay as it was before it was made fast. Any
  change to any result fails it.
* `test_temperature.py`, `test_imports.py`.

Seventeen hand-made faults in the module (a parked tip that forgets, a first-in
first-out tip, ignoring the air gap, the surface taken before the dispense, an
off-by-one in `well_before`, ...) each made the suite fail. The faults and the
tests were written in the same session, so that is a check that the tests have
teeth, not independent evidence.

## How it stays fast

Measured on the library's heaviest protocol (`5520f0`, 25,188 events): one set
of eight tips changes the medium on six plates of 384 wells, into one shared
waste trough. By the model, and in truth, every well ends up with a trace of
every well before it: 2,317 origins and **5.8 million arrivals**. Replaying it
took about 20 minutes (120 s for the first 8,000 events, growing with the
square); it now takes under 9 s, and every result is the same.

| what was slow | what is done instead (`working.py`) |
|---|---|
| Every action looked at every atom of the tip and of the well, and copied them: events x atoms, with atoms growing as the run goes on | Wells and tips are worked on in place. Each keeps the sets the questions are asked of (certain atoms, bulk atoms, atoms with a volume) and a version number per set; "is this set inside that one?" is answered once per pair of versions. An action that brings nothing new costs a few lookups. Traces (volume 0.0) are never recomputed: nothing times zero is zero |
| Hashing a `WellKey` is Python code, and ran hundreds of millions of times | Atoms are numbered inside the replay |
| A copy of the well's atoms was stored after every event: gigabytes | A well keeps a log of changes to its atoms. A stored `WellState` holds a position in the log, and its `atoms` are rebuilt when looked at (the last 256 looked at are kept) |
| The first pass did everything twice | It follows volumes only |
| Python's cycle collector re-walked millions of values that hold no cycles: a third of the time | Paused during `replay` |

What is left is the size of the answer: about 1.4 microseconds per arrival.
A run's time is now roughly (events) + (arrivals), and arrivals can grow with
the square of the number of origins when one tip visits them all. The next 12
heaviest library protocols (up to 32,000 events, up to 97,000 arrivals) replay
in 0.2 to 1.0 s. `5520f0` needs 2.4 GB of memory, nearly all of it the 5.8
million `Arrival`s and the wells' logs.

Anything that walks `run.history` or calls `well_before` for every event and
then walks its atoms does events x atoms work of its own, however fast the
replay is.

## What the anomalies mean in the public library

Measured on 782 library protocols, then read event by event in 40 of them. Nothing from
the library is copied here; each pattern that
changed the model is rebuilt by hand in `tests/state/test_scenarios.py`.

| anomaly | what was behind it | verdict |
|---|---|---|
| `aspirate_exceeds_volume` (257 protocols), `aspirate_from_empty_well` (129) | A plate or tube that arrives holding liquid nobody declared: reagent added, then a larger mix or a supernatant removal (`26a414`, `1adec6-4`, `0b97ae`, `657ee9`, `6b9ee3`, `089108`, `7e4c3e-6`) | **The model was wrong.** Now an implicit origin. In the 40, one protocol keeps the anomaly, and rightly: it *declares* a reservoir well and then uses 100 uL more than it declared (`79e9a1-cleanup`) |
| `aspirate_above_liquid` (286) | In 7 of the 17 sampled protocols it was the same undeclared plates, and is gone. The rest: 10 to 60 uL in a conical PCR well or tube, mixed at 1 to 5 mm (`00f7b1_part3`, `7aa3fd-library-pooling`, `3607d5-4`). The straight column puts 10 uL at 0.4 mm; in the real cone it is millimetres deep. One is real: a mix 1 mm below the *top* of a tube holding 7 uL (`2c81c0`) | Was our geometry, not the protocol; measured before the trace carried the well's shape. Now the anomaly comes with a certain verdict (`tip_above_surface`) where the shape is known, and `SOURCE-TOO-SHALLOW` reports only those, in protocols that declare their liquids |
| `overflow` (129) | Not waste containers: in only 2 of 23 protocols was the overflowing well a waste-like container, a beaker and a reservoir well (`422b1e`, `295c73`). The rest are working plates: 150 to 200 uL washes into a PCR plate whose stated maximum is 100 uL (`79e9a1-cleanup`, `5c7384`), 250 uL into a 200 uL plate (`1adec6-2`), deep-well plates filled step after step with the removal done by hand off the robot (`07ad5f`, `089108`). Some of it is the library's default parameter values. Our own inflation (one note per dispense, and overflow inferred from an implicit origin's floor: `swift-2s-turbo-pt3`) is fixed | Real, or a labware maximum more cautious than the plastic. A note at most |
| `tip_dropped_with_liquid` (77) | Deliberate: an extra 20 uL drawn so the last well gets a full dose, thrown away with the tip (`2aee74-48-2`); 1000 uL drawn, 500 used (`272c63`, `017860`). One is the trace: an 8-channel pipette dispensing onto a one-well labware is listed as one tip, so seven keep their liquid (`6a77d9`) | Real and harmless, except the trace case |
| `dispense_exceeds_held` (41) | The trace again: an 8-channel aspirate from a 24-tube rack or an 8-well strip is listed with 4 tips or 1, the dispense with 8 (`6d7eb7`, `checkit`, `21e4d8-pt1`). And an idiom: "dispense 300" to empty a tip holding 40 (`1c086c`) | Trace expansion (D-11) to fix in `provette/trace`; the idiom is harmless |

## What this module needs from the trace

Written here because `provette/model.py` is the contract.

1. ~~The well's bottom shape, or a volume-to-height table.~~ Delivered
   (`WellGeometry.bottom_shape`, `height_at_ul`, from the labware definition's
   `wellBottomShape` and `innerLabwareGeometry`; `provette/trace/_geometry.py`).
   Row 6b and the under-reporting of row 10 remain only for wells whose shape
   no definition gives.
2. **Structured thermocycler profiles and lid temperature**, for time at
   temperature inside a thermocycler.
3. **The same tips on both sides of a multi-channel move.** When an 8-channel
   pipette works on labware with fewer than eight rows, the trace lists a
   different number of tips for the aspirate and the dispense (see the table
   above). The state then sees tips that dispense liquid they never drew.
4. **Where `move_labware` moved it to.** Until then a labware keeps the
   temperature timeline of the `labware_id` it started with.
