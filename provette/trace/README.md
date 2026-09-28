# provette/trace

Runs an Opentrons protocol under the simulator (`opentrons==8.8.2`) and writes
down everything it did: one `provette.model.Event` per step, with the line of the
protocol that caused it. The result is a `provette.model.Trace`. Everything after
this module (state, rules, report) reads the trace and never touches Opentrons.

```python
from provette.trace import trace_protocol, analyze_protocol, cross_check

trace = trace_protocol(Path("protocol.py"))  # source 1: the broker tap
ops = analyze_protocol(Path("protocol.py"))  # source 2: Opentrons' own analysis
assert cross_check(trace, ops) == []  # they must tell the same story
```

```
provette trace protocol.py                  # one readable line per event
provette trace protocol.py --out t.jsonl    # the trace as JSON Lines
provette trace protocol.py --cross-check    # exit 1 if the two sources disagree
provette trace protocol.py --labware-dir D  # custom labware definitions (*.json) in D
```

Exit codes: 0 fine, 1 the sources disagree, 2 the simulator rejected the
protocol.

## What may be relied on

* Every broker message becomes an event. One that is not a liquid, tip or
  environment step has `op == "other"` and keeps the broker's name in `raw_op`.
  Nothing is dropped.
* `line` is the innermost line of the protocol file that was running, so a step
  made inside a helper function points into the helper; `stack` is the whole
  chain of protocol frames, outermost first (`["run:32", "with_fresh_tip:21",
  "add_and_mix:14"]`).
* `targets` lists one entry per tip that is really on the pipette and really
  over a well (see "Multi-channel pipettes"). `Target.tip` is the rack well the
  tip came from.
* `labware_id` is `"<slot>:<load_name>"`, fixed the first time the labware is
  seen. After `move_labware` it stays the original id, and a `move_labware`
  event says the plate moved. Two labware that would share an id stop the run
  with a `TraceError`.
* `height_mm` is the tip's height above the bottom of the well, from the
  simulator's own coordinates.
* `t_est_s` is Opentrons' duration estimate summed over everything before the
  event. It is an estimate: it counts pipetting, delays, thermocycler and
  temperature-module waits, and counts a heater-shaker wait as zero.
* Tracing the same file twice gives equal traces (tested).
* Tracing costs about twice a plain simulation (measured on a 25,000-step
  library protocol: 9 s plain, 17 s traced).
* `trace_protocol` and `analyze_protocol` raise `TraceError` if the simulator
  rejects the protocol or does not finish within `timeout_s`. `str(error)` is
  the simulator's sentence; `error.line` is the protocol line it names.
* For all thirteen fixtures in `tests/fixtures/protocols/` that the simulator
  accepts, `cross_check` is empty. This is the cross-check of D-09 (`DECISIONS.md`)
  and runs in `make check`.

## How the broker tap works

Every call in the Opentrons Python API (`aspirate`, `transfer`,
`set_temperature`...) announces itself twice on an internal "broker": a
*before* message and an *after* message. High-level calls nest: a `transfer`
announces itself, then each `pick_up_tip`, `aspirate` and `dispense` inside it
announces itself, then the `transfer` announces that it is over.

`_worker.py` replaces `LegacyBroker.publish` with a function that reads each
message and passes it on. For each *before* message it:

1. walks up the Python call stack and keeps the frames that belong to the
   protocol file: that gives `line` and `stack`;
2. looks at which high-level calls have begun and not ended: that gives
   `parent` (`distribute` and `consolidate` are built on `transfer` inside
   Opentrons, and the parent is the one the author wrote);
3. reads the pipette, the location and the volume from the message, and turns
   the location into wells and a height;
4. for module and `move_labware` messages, which carry only text, reads the
   module object, the temperature or the labware from the arguments of the API
   method that published the message (one more stack frame up).

Liquids are declared, not moved, so the broker never mentions them. The worker
wraps `Well.load_liquid`, `Labware.load_liquid`, `Labware.load_liquid_by_well`
and `Labware.load_empty` (all four exist in 8.8.2) and records the line of
each. `load_empty` is recorded as a load of 0 µL with an empty liquid name.

All of this happens in a child process (`python -m provette.trace._worker`): the
tap changes classes for the whole process, and a protocol is somebody else's
code. The child gets a throw-away `OT_API_CONFIG_DIR`, so nothing is written to
`~/.opentrons`.

### Broker name to `op`

| broker name (`command.` + ...) | `op` | filled in |
|---|---|---|
| `PICK_UP_TIP` | `pick_up_tip` | targets (tip = well) |
| `DROP_TIP`, `DROP_TIP_IN_DISPOSAL_LOCATION` | `drop_tip` | targets; `returned=True` when the tip lands in a tip rack |
| `ASPIRATE` | `aspirate` | targets, volume, height |
| `AIR_GAP` with nothing nested (API 2.22 and later) | `other`, then an `aspirate` with `parent="air_gap"`, `raw_op="command.AIR_GAP"` | targets = the pipette's last well, volume, height |
| `DISPENSE`, `DISPENSE_IN_DISPOSAL_LOCATION` | `dispense` | targets, volume, height |
| `BLOW_OUT`, `BLOW_OUT_IN_DISPOSAL_LOCATION` | `blow_out` | targets, height |
| `TOUCH_TIP` | `touch_tip` | targets = the named or last well; height = well depth + `v_offset` |
| `DELAY` | `delay` | `duration_s` |
| `PAUSE` | `pause` | message in `detail` |
| `TEMPDECK_SET_TEMP`, `THERMOCYCLER_SET_BLOCK_TEMP`, `THERMOCYCLER_START_SET_BLOCK_TEMP`, `HEATER_SHAKER_SET_TARGET_TEMPERATURE` | `set_temperature` | `celsius`, `module`, `labware_id` |
| `TEMPDECK_DEACTIVATE`, `THERMOCYCLER_DEACTIVATE`, `THERMOCYCLER_DEACTIVATE_BLOCK`, `HEATER_SHAKER_DEACTIVATE_HEATER` | `deactivate` | `module`, `labware_id` |
| `THERMOCYCLER_EXECUTE_PROFILE`, `THERMOCYCLER_START_EXECUTE_PROFILE` | `thermocycler_profile` | `module`, `labware_id`; the steps are in `detail` |
| `THERMOCYCLER_OPEN`, `THERMOCYCLER_CLOSE`, `HEATER_SHAKER_OPEN_LABWARE_LATCH`, `HEATER_SHAKER_CLOSE_LABWARE_LATCH` | `lid` | `detail` starts with `open:` or `close:`, then the simulator's text |
| `MOVE_LABWARE` | `move_labware` | `labware_id` (the original id); the new slot is in `detail` |
| everything else: `TRANSFER`, `DISTRIBUTE`, `CONSOLIDATE`, `MIX`, `AIR_GAP`, `RETURN_TIP`, `MOVE_TO`, `HOME`, `COMMENT`, `MAGDECK_ENGAGE`, `THERMOCYCLER_SET_LID_TEMP`, the heater-shaker's shaking, the waits... | `other` | `module` and `labware_id` when a module published it |

The thermocycler's *lid* temperature and the heater-shaker's *shaking* are
`other` on purpose: `set_temperature` and `deactivate` mean the temperature the
samples sit at.

### Where things go when there is no labware

From API 2.16 the trash is not a labware but a deck area. A tip dropped, or
liquid dispensed or blown out, over it gets the target well
`"12:fixedTrash"[A1]`, and the deck header gets a row for it with no wells.
Below 2.16 the trash is an ordinary labware, `12:opentrons_1_trash_1100ml_fixed`,
and is listed like any other.

## The second source: `analyze_protocol`

`opentrons.cli analyze --json-output` is what the Opentrons App runs before a
protocol may start. `analyze.py` runs it in a child process and keeps these
commands, in order, as `LiquidOp(op, labware_load_name, slot, well, volume_ul)`:

| `commandType` | `LiquidOp.op` |
|---|---|
| `pickUpTip` | `pick_up_tip` |
| `dropTip`, `dropTipInPlace` | `drop_tip` |
| `aspirate`, `aspirateInPlace`, `airGapInPlace` | `aspirate` |
| `dispense`, `dispenseInPlace` | `dispense` |
| `blowout`, `blowOutInPlace` | `blow_out` |

An "in place" command names no labware; it acts where the pipette already is.
`reduce_analysis` follows each pipette through every command that names a well
or a deck area, plain moves included, and gives an in-place command the place
of the command before it. That is how an air gap (`moveToWell`,
`prepareToAspirate`, `airGapInPlace`) gets a well, and how a tip dropped in the
trash (`moveToAddressableAreaForDropTip`, `dropTipInPlace`) gets
`labware_load_name="fixedTrash"`. `slot` is the slot the labware was first
loaded in, to match `labware_id`. Seen in our fixtures: every command in the
table except `aspirateInPlace`, which we have not managed to provoke.

`cross_check` compares, one to one and in order, every `pick_up_tip`,
`aspirate`, `dispense`, `blow_out` and `drop_tip`: the op, the labware's load
name and first slot, the well, and for aspirates and dispenses the volume
(tolerance 1e-6 µL). For an 8-channel event it compares the first target's
well, which is the well the analysis names. When fewer tips than channels are
in play the first target is no longer the named well, and only the labware is
compared.

Two differences between the sources are legitimate, and `cross_check`
reconciles them (both were found by running it over the public library):

* **A step of 0 µL.** `dispense(pipette.current_volume, well)` with an empty
  tip, or any dispense from an empty tip, sends the tip into the well and moves
  nothing. The trace keeps the event, because the tip did touch the well. The
  analysis has either only a plain move (below API 2.14, when 0 was asked for)
  or the same step: as 0 µL from 2.14, and below 2.14 with whatever volume was
  asked for. A 0 µL event is matched with the next analysis operation when that
  operation fits it and does not fit the event after it; otherwise it is passed
  over.
* **A dispense of more than the tip holds.** Up to API 2.16 the robot dispenses
  what it holds (from 2.17 it is an error), while the broker announces the
  volume asked for. The trace records what the tip held
  (`min(asked, pipette.current_volume)`); the simulator's text in `detail`
  keeps what was asked. From 2.14 the analysis also says what the tip held
  (measured: 90, not 200). Below 2.14 the analysis is built from the broker and
  repeats the 200, so there an analysis volume *larger* than the trace's, on a
  dispense, is not a disagreement.

An action that names no place (`aspirate(30)` after a `move_to`, `mix`,
`blow_out()`) needs no reconciling: the broker message carries the pipette's
current location, and the trace has the well and the height (fixture
`odd_volumes.py`).

**How independent is it?** At API level 2.14 and above the analysis comes from
the Protocol Engine's command list, which shares nothing with the broker. Below
2.14 Opentrons builds the analysis *from the same broker messages* (its
"legacy command mapper"), so there the cross-check tests our reading of the
messages, not the messages.

## Multi-channel pipettes (DECISIONS.md D-11)

The simulator names one well per action: the one under the pipette's first
channel. `_channels.py` works out the rest from the labware definition. The
tips of an 8-channel pipette are 9 mm apart in a line from the back of the deck
to the front. For each channel, take the named well's centre, move 9 mm towards
the front per channel, and see which well of the definition lies under that
point.

| labware | sent to | the eight tips enter |
|---|---|---|
| 96-well plate or tip rack (wells 9 mm apart) | A1 | A1, B1, C1 ... H1 |
| 384-well plate (4.5 mm apart) | A1 / B1 | A1, C1 ... O1 / B1, D1 ... P1 |
| 12-column reservoir (quirk `centerMultichannelOnWells`: the robot centres the row of tips on the well) | A1 | A1, eight times |

**A channel over no well.** The tips on a pipette do not change between
pick-up and drop, so every aspirate, dispense, blow-out, touch-tip and drop
lists one target per tip, in channel order. Usually each channel is over a
well. Sometimes it is not: sent to tube A1 of a 24-tube rack (tubes 19 mm
apart, tips 9 mm apart), tips 1, 3, 5, 7 enter tubes A1 to D1 and tips 2, 4, 6,
8 come down between tubes; a flat "surface" labware drawn as one 4.5 mm well
has only the first tip over it; so does a plate when the pipette is sent to row
E. Published protocols do all three, and the simulator books the whole action
to the named well without complaint. The trace books such a channel to **the
well the protocol named**: it is what the simulator does with the liquid, each
tip's volume still adds up for the state machine, and it errs towards
reporting contact rather than hiding it. Picking up tips is the exception and
stays purely geometric: a channel over no rack position picks up no tip (this
is how partial pickups are done on the old API). With only some nozzles active
(`configure_nozzle_layout`) the active nozzles are read from the engine's
nozzle map, so a single-nozzle pickup gives one target (tested at API 2.27).
The old engine has no nozzle map, and there all channels are active.

**Tips that are not there.** The simulator lets an 8-channel pipette pick up a
rack column from which the single-channel pipette has already taken tips
(measured at API 2.11 and 2.27: no error). The worker keeps its own record of
which rack wells have had their tip taken, and of tips returned to the rack, so
such a pickup lists only the tips that are there, and later events list only
the wells those tips enter. A returned tip that is picked up again keeps its
identity, the rack well: it is a used tip.

**Racks that a person refills.** The robot cannot see a rack, and protocols
refill them in two ways. `tiprack.reset()` and `pipette.reset_tipracks()` say
so, and the worker wraps them: every tip of that rack is there again. The
other way says nothing: the protocol pauses ("replace the tips") and then
picks up from a position it has already emptied, and the simulator lets it.
When *every* tip a pickup reaches for is already gone, the worker takes the
rack as refilled, because a pipette that came up with nothing could not do the
pipetting that follows. So the same tip id (`3:opentrons_96_tiprack_300ul[A1]`)
can be picked up twice with a throw-away in between: the second one is a new
tip. Before this was handled, 103 of 782 library protocols lost every target
after their first refill.

## The two engines

Below API 2.14 the simulator runs its old engine; from 2.14 the Protocol
Engine. The same tap works on both. What differs, and is handled:

| | below 2.14 | 2.14 and above |
|---|---|---|
| trash | a labware with one well | from 2.16 a deck area; `*_IN_DISPOSAL_LOCATION` messages |
| air gap | `AIR_GAP` wraps an `ASPIRATE` | from 2.22 `AIR_GAP` stands alone; we emit the aspirate |
| nozzle map | none: all channels always active | read from the engine (tested at 2.27) |
| labware definitions | an older version of some (NEST PCR plate depth 14.78 mm) | the newest (14.7 mm) |
| analysis | built from the broker | independent |

The fixture `legacy_api.py` was also traced at 2.9, 2.14, 2.15, 2.16 and 2.20
by hand, each with an empty cross-check.

**Python is pinned to 3.10.** `opentrons==8.8.2` cannot load any module (temperature,
magnetic, thermocycler) below API 2.14 on Python 3.11 or later: it formats an enum
into a file name, and Python changed how that prints (measured on 3.10, 3.11, 3.12).
Most of the public library is below 2.14, so the project runs on 3.10 and carries
no repair (DECISIONS.md D-04).

## Known gaps

* `transfer_with_liquid_class` and its siblings could not be traced: the
  built-in liquid classes refuse OT-2 pipettes. If one runs, the broker may
  show it as a single `other` event with no primitives inside; the cross-check
  would then fail, which is the intended alarm.
* The thermocycler profile's steps and a block temperature's hold time are only
  in `detail` (and in the jump of `t_est_s`); the contract has no field for
  them. Magnet engage and disengage are `other` events.
* `Target.well` over the trash is a made-up well name (`A1`) on a deck area
  that has no wells.
* The tip record assumes every rack starts full, and cannot see a rack that was
  refilled silently while some of the tips a pickup reaches for were still there:
  that pickup is reported as partial.
* Flex protocols, JSON protocols and run-time parameters were not tried.
* If a protocol file has the same name as a file inside the `opentrons`
  package, frames inside that package are still excluded, but a second user
  file of the same name in another directory would be counted as protocol
  lines.
