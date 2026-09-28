# How Provette works, end to end

For demoing Provette and answering "why does it do that?". Every claim
names the file it was read from, in parentheses, so you can go and look; every number comes from a README or a `DECISIONS.md` row,
never from memory. Where something is not built, it says so. [`README.md`](../README.md) is the frame and
[`DECISIONS.md`](../DECISIONS.md) the reasons; this page is the mechanism.

## 1. What Provette is

Lab robots run Python scripts, and more of those scripts are written by language models. The robot's simulator checks the physics
(the arm can reach, a tip is on, the well will not overflow) and knows nothing about the liquids (`README.md`, lines 7 to 14).
Provette runs the protocol in that simulator, records every action, replays it as a ledger of what every well and tip holds, and holds
the result against a **plate map**: what every well should end up holding, approved by a person. Twelve deterministic checks read
the same ledger for the biology the simulator cannot see. An agent on Nemotron uses those checks the way a coding agent uses tests:
it writes, checks, repairs, and submits only what verified. The sentence everything is held against: **the simulator checks the
physics; Provette checks the experiment**; it checks the logic, not the physics; the checker is deterministic and the model is never
the judge (`README.md`; D-01, D-28).

## 2. The pipeline

```
request ──► plate map ──► model writes ──► simulator ──► trace ──► ledger ──► verify + check
              (planner,      (agent,        (Opentrons     (events)  (state)     (intent, rules)
               approved)      tools)         8.8.2)                                   │
                  ▲                                                                   ▼
                  └──────────── the model repairs ◄──── findings ◄────────────────────┘
                                       │
                                       ▼
                                submit ──► prep sheet, replay, run record
```

**Request.** A few sentences a scientist would write, with an `id` and a `technique` word (`eval/requests/README.md`;
`requests.jsonl`). They say nothing about tips, contamination, mixing or controls, because whether the writer thinks of those
unprompted is what is measured.

**Plate map.** The planner turns the request into a JSON plate map in the format of `provette/intent/spec.py` and a person approves it
before any protocol is written (`provette/planner/README.md`). It exists because a plate map is something a biologist reads and Python
is not (`provette/planner/README.md`), and because a map that pins every well is what makes swapped samples visible (D-27).

**The model writes.** One episode: the system prompt, the request, then a loop of tool calls until `submit` or a budget
(`provette/agent/loop.py`, `run_episode`). Tools, because a model handed a pasted report cannot do dilution arithmetic, renames
liquids, and answers "no margin" by re-declaring the same volume (`provette/agent/README.md`, opening).

**Simulator.** `opentrons==8.8.2` on Python 3.10 exactly: 9.x refuses every OT-2 protocol and 3.11+ breaks module loading below API
2.14 (D-04).

**Trace.** Every action becomes one `Event` with its source line (`provette/model.py`; `provette/trace/README.md`), checked against
Opentrons' own analysis of the same run, independent from API 2.14 (D-09, D-10; section 4).

**Ledger.** `provette/state` replays the trace: what is in every well and on every tip after every event, where it came from, whether
the tip touched the liquid (`provette/state/README.md`). Ordinary Python that never imports Opentrons and never decides whether
anything is a problem.

**Verify + check.** `verify` compares the ledger's end state with the plate map, accounts for every declared liquid, writes the prep
sheet and checks the labware suits the technique (`provette/intent/cli.py`, `verify_trace`); `check` runs the rules
(`provette/check.py`). Both are needed: a wrong volume or a missing well is seen only by the map, a used tip in a stock only by the
rules.

**The model repairs.** Every `write_protocol` returns the checks of that draft, so a draft is never left unchecked and a repair
costs one call (`provette/agent/tools.py`, `tool_write_protocol`).

**Submit.** `submit` records whether the last check of the current draft was clean; a draft the model never checked is checked by
the harness, so `done.json` always says how the submitted file really stood (`provette/agent/loop.py`, lines 305 to 315).

**Prep sheet, replay, run record.** The prep sheet comes from the same replay (`provette/intent/prep.py`); the deck replay is one JSON
export of the trace, the ledger and the findings (`provette/view/export.py`); the run record is the page that shows all of it
(`web/src/components/RunRecord.tsx`). The direction is D-28: the product is the feedback loop for protocols written by small open
models.

## 3. How we talk to the model

**The conversation.** The system prompt is four parts (`provette/agent/loop.py`, `system_prompt`): NVIDIA's "You are a helpful
assistant." (`provette/agent/llm.py`, `SYSTEM`); the reference sheet, which names the real pipettes, labware and modules and the shape
of a file, and says nothing about the biology (`eval/requests/reference.md`); the preamble's requirements
(`eval/requests/preamble.md`) with the liquid names the plate map needs, "Hand the file in with the write_protocol tool" in place of
"Output only the Python file", and the short-on-tips line in that condition; and the tools paragraph (`TOOLS_PARAGRAPH`): `platemap`
first, `labware` for every kind loaded, the calculators for arithmetic, read the `checks` every `write_protocol` returns, submit
only on `ready_to_submit`, never rename the liquids. The user message is the request. Sampling is NVIDIA's for tool use: temperature
0.6 on Nano and 1.0 on Super, top_p 0.95, reasoning on, 24,000 tokens a turn (`llm.py`, `OpenAIChat`; `docs/harness-practices.md`,
row 4).

**The seven tools** (`provette/agent/tools.py`, `SCHEMAS`; `provette/agent/README.md`, the table): `platemap()`, the exact liquid names,
the destination and what every well or group must hold; `labware(kind)`, real load names with well counts and maxima read from the
installed definitions, never typed; `dilution_series`, `normalise` and `master_mix`, the calculators of `provette/calc`;
`write_protocol(text)`, the whole file, stored and checked; `submit()`. A bad call comes back as `{"error": …}` and the episode goes
on (`Toolbox.call`). `run_checks` is no longer offered, because `write_protocol` checks every draft (`CALLABLE`).

**What the model reads after `write_protocol`** (`tools.py`, `checks_for_model`). If the simulator rejected the file:
`simulator_error`, the offending line quoted from the draft, `verify_exit: 2`, `ready_to_submit: false`, a `verdict` saying nothing
else was checked, and a `hint` for the nine error kinds the transcripts showed again and again (an invented labware name gets the
real list, and so on); the same error kind three times in a row adds a `stuck` sentence asking for a different approach. If it
passed: `verify_exit`, `check_exit`, the two text reports cut at 6,000 characters and saying so (`REPORT_CHARS`), the findings as
rule, severity, line, title and fix, the declared liquids no word list knows (`unplaced_liquids`), and `ready_to_submit`, true only
when the simulator passed and both exits are 0 (`is_clean`). Older reports are collapsed to one line before sending (`loop.py`,
`for_sending`; `docs/harness-practices.md`, row 3); the transcript on disk keeps all.

**The pre-lint** (`provette/agent/prelint.py`). Before the simulator sees a draft, five repairs run and each is reported back in a
sentence: a name string in `load_liquid` becomes the object `define_liquid` returned; keywords `load_liquid` does not take are
dropped (one episode spent all twenty drafts on `ribbon=`); an invented labware name becomes the real one it was clearly meant to
be; a missing `display_color` and a missing import are added. The model's own text is kept as `NN-draft.as-written.py`. Nothing less
certain is touched: these slips cost a draft each time and none is a matter of judgement (docstring).

**The thinking budget.** When a turn ends with `finish_reason: length`, non-empty reasoning and no tool call, the loop closes the
thought with `</think>` and asks the completions endpoint for the answer, with 8,000 tokens for it (`loop.py`, lines 169 to 195;
`provette/agent/budget.py`; `provette/agent/README.md`, "The thinking budget"). Without it, Nano's misses are mostly turns cut
mid-thought.

**Stop rules and retries** (`loop.py`): `submit`; 25 tool calls; 100,000 completion tokens (the defaults, which Settings
changes: `api/run_settings.py`); a draft the checks reject is not taken as the answer before the third (D-32); three API errors in a row, with 5 s and
15 s of backoff; three turns with neither a tool call nor a code block. A fenced code block with no tool call is treated as
`write_protocol` on the longest block (`fenced_block`); a draft identical to the previous one is told so at once. `should_stop` is
asked before every model call and every tool call; the product's Stop button sets it and the record says "stopped"
(`STOPPED_BY_USER`; `api/live.py`, `Live.stop`).

**Best-of-N.** `eval/agent/run.py --candidates N` runs N episodes of one request at once and keeps the first that ended verified and
clean, else the one whose last checks got furthest; the cost recorded is the cost of all N (`best_of`). The checks judge the
candidates, not the model.

**The runners.** A `Runner` takes the draft text and the plate map and returns one dict: simulator passed or rejected, `verify_exit`
0 to 3, `check_exit`, the two reports, the findings (`provette/agent/runner.py`). Three share it (`provette/sandbox/README.md`): `local`
runs `verify --json`, `verify`, `check` and `check --json` as subprocesses in a temp dir with `PYTHONPATH` unset and a 600 s limit
reported to the model as a draft to rewrite with fewer steps (`provette/agent/local_runner.py`); `docker`, a container with no
network; `nebius`, one disposable Token Factory Sandbox per check, 14.4 s a round trip against 5.7 s in process, five at once in
11.6 s (D-35). The deployment runs `local` because it depends on nothing outside the Machine; `nebius` is one environment variable
away (D-37).

**The planner's loop** (`provette/planner/loop.py`, `plan`). The same chat client and its own sheet (`provette/planner/prompt.py`: the
format, seven rules, one worked example that is none of our requests). Five tools: the three calculators, `labware`,
`propose_platemap` (`provette/planner/README.md`). The model never computes a number: every volume must be written in the request or
returned by a calculator, and `propose_platemap` refuses any other. A proposal is validated with `platemap_from_dict` and the error
goes back; a refusal repeated twice gets a message quoting the field to change and the liquids the map declares (`repair_message`).
Budgets: 12 tool calls, 40,000 completion tokens, two idle turns; a budget that runs out is a `PlanError`, never a guessed map. The
one repair the tool makes is a single missing `]`, and it says so (D-29).

**The deployment's guards.** Every write on a person's behalf (a plan, a run, a taught word, a source, a saved rule, a failed-run
record) sends `X-Judge-Password`, compared in constant time (`api/auth.py`). The live flow spends at most `PROVETTE_DAILY_CAP_USD` a
UTC day, $2.00 by default, from the model's usage fields at list prices; a plan is estimated at $0.01 and a run at $0.10 before it
starts, and past the cap the route answers 503 with a sentence (`api/ledger.py`; `deploy/README.md`, "The daily cap"). Two runs at
once, and up to four plans on threads of their own, so a plan never waits behind two runs; six plans
and three runs per address in ten minutes (`api/live.py`).

**What the model is never allowed to do: judge.** It names liquids, writes protocols and patches them from a report (D-01, D-28).
The verdict is `is_clean` over the runner's exit codes; every badge, rail row and finding on the pages is drawn from `verify` and
`check` JSON, and the model's words appear only inside the model's-work fold (`web/src/components/RunRecord.tsx`).

## 4. The simulator and the two readings

Opentrons' simulator checks that the script can run: the labware exists, the pipette can reach, the volumes fit the tip. It does not
track liquids: it passes a serial dilution at half the volume, a master mix at fifteen times the volume, and one tip carrying
samples back into the shared reagent (`README.md`, lines 7 to 14).

**The broker tap** (`provette/trace/README.md`, "How the broker tap works"). Every API call announces itself on an internal broker
before and after; `provette/trace/_worker.py` replaces `LegacyBroker.publish`, and for each message walks the Python stack for the
protocol's line and frames, reads the pipette, location and volume, and turns the location into wells and a tip height from the
simulator's own coordinates. Liquids are declared, not moved, so the worker also wraps the `load_liquid` calls. It runs in a child
process, because a protocol is somebody else's code. An 8-channel action is expanded to the wells every channel enters (D-11).

**The analysis cross-check.** `opentrons.cli analyze --json-output` is what the Opentrons App runs before a protocol may start;
`provette/trace/analyze.py` runs it and `cross_check` compares every pick-up, aspirate, dispense, blow-out and drop, one to one and in
order, on op, labware, well and volume ("The second source"). Why both: the broker gives line numbers and heights in one pass but is
marked legacy; the analysis is an official schema with no line numbers; each catches a misreading of the other (D-09). Below API
2.14 the analysis is built from the same broker messages, so there the check tests our reading of them (D-10). The two readings
agree on 788 of 788 public protocols, and on 16 of 16 at API 2.14 or later, where they are
independent (`eval/ledger/README.md`; `provette/trace/README.md`).

**A trace event** (`provette/model.py`, `Event`): its index; `op` (the liquid and tip primitives, the time and environment ops, or
`other` so nothing is dropped); the line and the stack of protocol frames; the enclosing call (`transfer`, `mix`, `air_gap`…); one
`Target` (tip, well) per channel; the volume per channel; the tip height above the well bottom; an estimated clock; the simulator's
own text. The header carries every labware with each well's geometry, the pipettes with their ranges, and the declared liquids
(`Deck`).

## 5. The ledger

`provette/state` replays the trace and says what happened, never whether it is a problem (`provette/state/README.md`). Per well: the
volume (or `None` when it cannot be known) and a lower bound, and for every material present a `Presence`: its volume, whether it
arrived in **bulk** (in the liquid dispensed) or as **carry-over** (a film left by a tip), whether that is certain, and since which
event. Per tip: its status (in use, parked in its rack, dropped), its layers, and its residue: everything that has wetted it. Every
material is followed back to its **origin**, the well that held it before the robot moved anything: declared by `load_liquid`, or
implicit when a well gives more than it ever got, which must have been holding something (D-15, D-16). Provenance is the list of
`Arrival`s: which material reached which well at which event, by which tip, from which well. Time at temperature is a timeline per
labware from `set_temperature` and `deactivate` events ("What the rules use").

**Contact.** A tip contaminates a well, and is contaminated by it, only when it touches the liquid; then residue flows both ways.
The liquid's height comes from the definition's shape, sampled by the tracer into a volume-to-height table
(`provette/trace/_geometry.py`; `provette/model.py`, `WellGeometry`) and interpolated (`provette/state/contact.py`, `surface_mm`); a
loaded version with no shape borrows the newest version's (D-14). Without a table the height is volume over cross-section, a
straight column, which is a floor: real cones lift the liquid higher. A tip within 0.1 mm of the surface is touching
(`CONTACT_TOLERANCE_MM`). The cases are the table in `state/README.md`, "The contact model".

**"Film" and "uncertain".** A film is carry-over: volume `0.0`, because the film on a tip is a fraction of a microlitre and
unknowable, and what matters is that it is there ("Other assumptions"). A bulk arrival of `0.0` is a trace: the dispensed liquid
came from a well that itself held only a film, which is how one dirty tip in the master mix reaches every well the mix goes to.
Uncertain (`certain=False`) means the presence rests on a contact the model could not decide, usually an unknown volume; the model
assumes contact may have happened and marks everything downstream, so a rule can lower the finding and say why; a later certain
route upgrades it.

**Dry wells and over-draws.** An aspirate from a well known to be empty draws air and moves nothing; the well keeps its film, so its
provenance is not erased (`contact.py`, `aspirate_contact`, `well_empty`). Aspirating more than a well holds takes what is there and
the rest is air (`aspirate_exceeds_volume`); dispensing more than a tip holds empties it. Volume is never invented, because the
replay must finish and the prep sheet counts the air drawn as the shortfall (`provette/intent/prep.py`, `needed_volumes`). With a
known shape and a tip above the surface, the pipette draws air and the well keeps its liquid (D-13).

**What it does not track.** The physics: droplets, splashes, a hanging drop, viscosity, evaporation, whether a mix really mixed; a
well mixes perfectly and instantly ("Known ways it is wrong"). Modules with nothing on them, the thermocycler's programme steps and
the lid are not modelled ("What this module needs from the trace").

## 6. The plate map

In first principles: for one destination labware, how many microlitres of each **starting** liquid every well should hold once the
run is over, as if every well mixed perfectly; a master mix pooled on the deck still resolves to so-many microlitres of buffer,
enzyme and water per well (`provette/intent/spec.py`, docstring). It is written from the request, never from the protocol.

**The fields** (`spec.py`): `liquids`, each with a `name`, a `role` (sample or reagent), a `bind` (`name`: a regex over the declared
names; `indexed`: `stem_{i}` with one capture group for the sample number, a `count`, and `index` "number" or "any"; `well`:
`stem@{well}`, whatever the protocol declares in that well of the source plate) and its `pattern`; `destination`, `auto` or a regex
on the labware's label; `variants`, one reading of the request each, any of which verifies, each with `pinned` wells and `groups` of
members that may sit in any wells or any `within` a set, with `position` `free` or `same_as_source` and an `order_hint` of `index`
that gives a note, not a mismatch, when numbered samples are out of order; `discard_intended`; `notes`, one sentence per choice the
request left open; `technique`, optional. An amount is microlitres or `"declared"` (the well started with it and must keep all of
it). Validation names the field that is wrong (`validate`).

**What `verify` does with it** (`provette/intent/cli.py`, `verify_trace`; `provette/intent/README.md`). `compare` reads each well from
the ledger, sums the origins bound to each logical liquid, and matches within 2% or 0.06 µl, capped at 10% under 0.6 µl
(`provette/intent/compare.py`, `tolerance_ul`); position-free groups match as a multiset; a liquid the map names that no declaration
matches is "cannot check", exit 3, not a pass. `account` says where every declared liquid ended: delivered, left in its tube,
elsewhere, or lost in a tip or the trash; a sample that loses a whole dose or lands where the map does not list it is a flag, less
than a dose a note (`provette/intent/accounting.py`). `prep_sheet` gives, per source well, the deepest the replay draws it below its
start plus any air drawn short, against what was declared: `would_run_dry`, `no_margin` past 90% (`provette/intent/prep.py`,
`NO_MARGIN`), `draws_air`; and the tips per rack. `labware_for_technique` warns when the technique needs a kind of plate the
destination is not (`provette/intent/labware.py`). Exit 0 only when every well verified and nothing flagged; 1 on a mismatch, a flag
or a labware warning; 2 rejected; 3 the map could not be checked.

**Without a map** only `check` runs and the rail's Plate map row reads "none given" (`web/src/components/ChecksList.tsx`). The prep
sheet is still computed for every protocol the simulator passes, because it needs only the trace and the run (`api/worker.py`,
docstring), and feeds the rail's **Stocks** row: "N would run dry", "N with no margin", "enough declared", or "none declared" when
the protocol has no `load_liquid` (`ChecksList.tsx`, `stocksState`).

## 7. The twelve checks

A rule is a plain function `(trace, run) -> list[Finding]` with an id, a family, a tier (structural: true whatever the liquids are;
role: needs the word lists), a description, a status, and its sources; a rule with no source does not load (`provette/rules/rule.py`).
The rules that run are the ten in Python plus the declared files (`provette/rules/__init__.py`, `RULES`); the twelfth,
LABWARE-FOR-TECHNIQUE, runs in `verify`. One finding per root cause: a loop that puts one dirty tip into eight tubes is one finding
with eight occurrences (`provette/rules/README.md`). Thresholds and what changing each does: `docs/rulebook.md`; sources:
`docs/rule-sources.md`.

**CONTAM-STOCK** (`provette/rules/contam_stock.py`). A tip that has been in another liquid touches the liquid of a stock (a well that
held liquid from the start and is drawn from). Error if the stock is drawn from again and the trace reaches wells it was never meant
for, warning otherwise; then graded by what was carried (D-20): a carrier is a note, a sample keeps the structural severity, a
reagent into a sample or reagent is at most a warning. Silent on two liquids declared under the same name and on a liquid the
protocol puts into the stock on purpose; one tip into several undeclared stocks on one line is a note (D-19). Title: "A used tip
went into a stock".

**CONTAM-WELL** (`contam_well.py`). A tip carries liquid X into a well the protocol never, at any point, means to hold X. Warning,
graded by role. A first version flagged 117 of 150 library protocols, so it is silent on replicates holding the same liquids, a
serial dilution with one tip, mixing in a well the tip just dispensed into, and one tip filling many wells from above (D-12). Title:
"A used tip carried sample 3 into well B2 in slot 1 it was never meant for" (the liquid carried, then the well or the count).

**MIX-BEFORE-DRAW** (`mix_before_draw.py`). A well holds liquid, a different liquid is added, and liquid is later drawn out with no
mix between. Warning. `WHOLE_WELL` 0.9: a draw of that share takes everything, so layering cannot matter; `SAME_SHARE` 0.01: a
top-up of the same liquid is not an addition. Silent on an empty well and on draws that all go to the trash.

**MIX-TOO-WEAK** (`mix_too_weak.py`). A run of strokes that cannot mix the well: the mixing work (strokes × stroke/well) under
`MIN_WORK` 2.0, fewer than `MIN_STROKES` 3, a stroke of the whole well, or a pipette whose maximum is under `CAP_SHARE` 0.2 of the
well. Warning; the 2.0 and 3 come from a flood read of twenty library findings, where every false alarm was 36 to 48% of the well
repeated 4 to 10 times (docstring). Silent on unknown volume, one liquid (a pre-wet), a stock only drawn from, and a prime (one
stroke, then a draw from the same well). **Why the title reads as it does**: it carries its numbers so the line reads on its own in
a list, the strongest reason first, the well or the count of wells, then strokes × stroke in what the well held (`_title`): "Mixing
too weak to stir well A1 in slot 3: 3 × 5 ul in 25 ul", "Too few strokes to mix …: 2 × …", "A mix stroke as big as the well …", "A
pipette too small to mix …" (`docs/rulebook.md`). The same rule holds for every title: CONTAM-WELL names the liquid
and the well, MIX-BEFORE-DRAW the lines added at and drawn at, UNMIXED-AT-END the liquid and its share, PIPETTE-RANGE the volume and
the minimum, WELL-CAPACITY the amounts against the rim or the rating. Units in titles are `ul`, as protocols write them.

**PIPETTE-RANGE** (`pipette_range.py`). An aspirate below the pipette's minimum, from its definition: error. No threshold to own; a
legal-but-low tier at 35% of nominal was tried and deleted because drawing exactly the minimum is what real protocols do
(`docs/rulebook.md`). Air gaps are not judged. Title: "0.5 ul is below what the p300_single_gen2 can measure (20 ul at least)".

**WELL-CAPACITY** (`well_capacity.py`). Past the rim by the definition's shape: error; past the maker's stated maximum but under the
rim, or no rim known: warning with both numbers; a mix stroke of `STROKE_SHARE` 0.1 or more in a well `MIX_SHARE` 0.9 full: warning;
a declaration above what the well holds: note. The rim decides because 117 of 123 library crossings of the stated maximum were under
it (D-21). Exempt: waste and trash labware, and sinks (reservoirs and tubes only ever poured into); within 1% or 1 µl nothing is
said; a pause before the crossing is named, because a plate emptied by hand there is something the script cannot show.

**SOURCE-TOO-SHALLOW** (`source_too_shallow.py`). The tip aspirates above the liquid in a well whose shape is known, so it draws
air: error, one per line, with the wells that got air. Silent on air gaps by hand (an aspirate in the top half, `HAND_AIR_GAP_SHARE`
0.5, or one followed at once by a real draw from the same well), on an unknown shape, on a protocol that declares no liquids, and on
a well that is simply running out, which is the prep sheet's flag. The case: 2 ml in the 195 ml trough is below a tip at 1 mm after
46 draws of 18 µl (D-13).

**COLD-MODULE-NEVER-SET** (`cold_module.py`). Labware on a temperature module is used before the module is ever set: warning, once
per labware, naming the liquids. A later setting at `COLD_CELSIUS` 10.0 or below counts as forgotten and the finding says at which
line; a later warm setting is a planned incubation, because 12 of the 16 library protocols that set late set warm. Thermocyclers and
heater-shakers are not judged.

**UNMIXED-AT-END** (`unmixed_at_end.py`). The run ends with a well holding two liquids whose last addition was under
`MIXES_ON_ENTRY` 0.3 of the well and nothing mixed or drew from it after. Warning when the last addition was a sample (nothing else
will ever mix it); note otherwise, because a PCR plate is usually vortexed (`MIX_WORDS`). Silent on top-ups, unknown volumes, waste
and sinks.

**ENZYME-BEFORE-DILUENT** (`provette/rules/declared/ENZYME-BEFORE-DILUENT.yaml`, shape `add_after`). An add-last liquid (enzyme,
polymerase, master mix) goes into a well before its add-first liquid (water, buffer), when the well held under `share` 0.5 of its
final diluent. Warning; role tier; silent when no liquids are declared, when the enzyme arrives inside a master mix, or when the mix
is itself the bulk of the reaction. The proof that a Python rule re-expressed as data passes the same fixtures (D-22).

**NO-NEGATIVE-CONTROL** (`negative_control.py`). A PCR plate (a mix-word reagent and samples together in at least
`MIN_REACTION_WELLS` 4 wells) with no well of mix and no sample; a series of `MIN_SERIES_LEVELS` 4 levels falling by a constant
factor within `SERIES_TOLERANCE` 0.05, or 3 with a carrier, with no diluent-only blank; an RT reagent reaching the reactions with no
no-RT well. Every finding is a note, because the requests never asked for controls (docstring). Silent with no declared liquids.

**LABWARE-FOR-TECHNIQUE** (`provette/intent/labware.py`; runs in `verify`). The map's `technique` needs a class of destination (PCR,
flat, deep) the verified destination is not, by load name: warning, once. An enzyme or mix declared in a reservoir for a PCR-class
technique whose request says "tube" or names a temperature: note. Silent with no technique, a technique not in its table, or a load
name that says nothing.

**Declared rules** (`provette/rules/declared.py`; `rules/README.md`, "Declared rules"). A rule can be a YAML file in one of three
shapes: `no_carry_over` (`carried_role`, `into_role`), `full_well_not_mixed` (`share`, `stroke_share`), `add_after` (`first`,
`last`, `half_clause`, `share`). Every field is checked at import and a broken file stops the import by file and field. A rule with
`status: proposed` runs on every check but every finding it makes is a **note** titled "(proposed) …", because `provette check` exits
1 only on an error or a warning and the agent's readiness reads that exit code: a first rule may flood harmlessly and be
watched on real drafts before anyone trusts it; adopting is writing `adopted` and the date into the file, a commit on `main` (D-23).
The form always writes `proposed`; `NO-SAMPLE-INTO-REAGENT-WELL.yaml` is the worked example.

**Roles as data** (`provette/rules/roles.yaml`; `roles.py`). Seven lists of plain words, one per line: `sample`, `reagent`, `carrier`
(read in that order), `add_last`, `add_first`, `mix`, `rt`; a word matches as a whole word in any case. Read once at import; the
product reloads after a word is added. A name no list places is reported as *unplaced* ("I do not know what 'lysozyme' is") and the
finding keeps its structural severity (`roles_basis: none`), never a guess (D-24). The product's card offers five answers and writes
the word to the file (`web/src/components/UnplacedLiquids.tsx`).

**Sources as data** (`provette/rules/sources.yaml`): every row of `docs/rule-sources.md` as a key with a name and a URL; Python rules
cite the keys too, so a rule citing an unknown key does not load. The rule form can add one (`api/declared.py`).

**Coverage** (`provette/rules/coverage.yaml`). Per technique word, and a `default`: `checked`, `not_checked` (real mistakes from the
catalogue, with their N-numbers, that no rule looks at) and `physics`. Shown beside every verdict as "Not checked · N for qPCR" and
on `/rules#coverage`; "not checked" is its own state and never a tick, because a "verified" with no list beside it reads as "nothing
is wrong", which is false for a bead cleanup or an ELISA (D-25). Silence is not safety.

## 8. The findings and how they are shown

**The fields** (`provette/rules/finding.py`, `Finding`): `rule_id`, `family`, `tier`, `severity` (error: the plate must be redone;
warning: a result will be biased; note: advice; `docs/rulebook.md`), `certain`, `roles_basis`, `title`, `explanation`, `fix`,
`line`, `stack`, `occurrences`, `wells`, `downstream` (every well the damage later reached), `sources`, `fingerprint`. **Severity vs
certainty**: an uncertain finding is one level lower and says so (`lower`); the lozenge shows both
(`web/src/components/vocabulary.tsx`). The fingerprint hashes the rule, the text of the root line and the wells, never the line
number, so our triage labels survive edits elsewhere. The explanation and the fix are in plain lab words
(`CONTRIBUTING.md`, "The voice"); a declared rule's explanation is the facts followed by its `why` paragraph.

**The rail** (`web/src/components/ChecksList.tsx`), rows the way GitHub draws a checks list: *Plate map* "18 of 18 wells" green or
red, "could not be checked", "none given", or "not checked" when rejected; *Biology* the counts by severity or "no problems";
*Stocks* the prep sheet's flags as one state; *Simulator* "passed" or "rejected at line N", the version on hover; *Not checked* a
fold with the technique's lines, a "Write a rule for one of these" button, how many checks ran, and the physics line. While a run
goes the rows read "draft 2 · checking…" and fill in per draft (`LiveRows`).

**Findings in the rail** (`RunRecord.tsx`): one row each with the lozenge, the title, the line, the wells in short form, "runs in
verify" for a labware finding; a click seeks the code to the line and the replay to the event with the wells outlined (`seek`); a
chevron opens the card in place with the explanation, the fix, the occurrences, the downstream count and "rests on"
(`web/src/components/Findings.tsx`, `FindingCard`).

**The teaching cards.** The unplaced-liquid card sits between Checks and Findings with its five answers; after an answer the checks
run again, because the analysis cache key digests the word lists (`api/analysis.py`, `checker_digest`). "Did this run work?" sits
under Findings: Yes, or No with two sentences, saved as one JSON row (`web/src/components/OutcomeForm.tsx`; `api/outcomes.py`) and
listed on `/rules#failures` with "Start a rule from this" (`RuleForm.tsx`, `?from=`).

## 9. The product, page by page

Routes: `web/README.md`; the component vocabulary: `web/src/components/vocabulary.tsx`; how the pages look and read, with the
principles and their sources: `docs/design.md`. The pages are for a working lab scientist and are terse; the sentence "Provette
checks the logic of a protocol, not the physics." is said once, on About, and as the physics line inside the Not-checked fold
(`web/src/components/Shell.tsx`, `DISCLAIMER`).

**The frame** (`web/src/components/Shell.tsx`, `History.tsx`), in the pattern people know from chat apps: one sidebar holds
everything. **New run** first, then **Check a protocol** and the reading pages (Examples, Rules, Methods, About), then the history
of this deployment (runs, plans that did not become a run, checks) newest first, one line each with its mark in the state's colour (a dot for a run, a page for a check, a plate for a plan), read from
`GET /api/runs`, `/api/plans` and `/api/checks` and refreshed while something runs. Each line has a "⋯" menu: Pin keeps it at the
top in this browser only, and Delete asks in a dialog, then calls `DELETE` on the same address (behind the judge key; a run still
going must be stopped first) (`web/src/components/History.tsx`); the version, the judge key and Settings sit at
its foot. The key opens a dialog over the page (a sheet from the bottom on a phone) that checks the password with
`POST /api/judge` before keeping it, so a wrong one is said at once (`web/src/components/JudgeDialog.tsx`; `api/auth.py`).
Settings (`web/src/components/Settings.tsx`) is a dialog: General holds the theme (this browser's, dark until changed), and Runs and
plans the five budgets of `api/run_settings.py` (tool calls and tokens per run and per plan, drafts before giving up), whose
defaults are the constants the code runs with; a change needs the judge key, holds for everyone on the deployment from the next
job, and Reset to defaults removes it. The spend cap and the rate limits are not there: they stay in the environment. A page has
no bar on a desktop. On a phone the sidebar is a drawer, and a slim bar carries the menu, the name and a new run.

**`/` Write** (`web/src/pages/Home.tsx`). The greeting in the middle of the page, the composer under it (the request, and inside
it a technique select, the model that writes, and a round send button that asks for the judge key if missing, then
`POST /api/plans` and moves to the plan), three example chips under that from `/api/live`'s requests. A message with no lab
word and no amount in it ("What is the purpose of life?") is refused before any model is called (`provette/planner/gate.py`,
generous on purpose: every request on file passes, `tests/planner/test_gate.py`); the page says so and offers Send anyway. On a
phone the composer is pinned to the bottom of the screen.

**`/plan/:id`** (`web/src/pages/Plan.tsx`). The planner's turns stream over server-sent events (`api/live.py`, `plan_events`) into
the stage as they land; when a map is proposed the stage becomes the plate (Wells or Numbers, each well's sum) and the planner's
work folds; Stop asks the loop to stop before its next model call; the map is editable well by well
(`web/src/components/PlateMapEditor.tsx`); Approve posts it to `POST /api/runs`. Why there is no map is said in plain words:
the tries and the last refusal (`noMapWords`). The planner is also offered `not_a_request`: a message that asks for no liquid
handling ends there, with the model's one sentence and no map, instead of an invented one; "plan it anyway" plans it without that
tool (D-33).

**`/runs/:id`, `/episodes/…`, `/check/:id`: the run record** (`RunRecord.tsx`). The header: crumbs or the stepper, the request, the
badge (Verified · Not verified · Running · Checked) with the full sentence in its popover, a stop-reason chip, the meta row. The
stage: Replay (default once it lands; 3D on a desktop that can draw it and 2D on a phone, a view the reader picks remembered,
and "show in the replay" on a finding opens the plate in 2D; `web/src/lib/replayView.ts`), Plate map (the intent grid with verify rings, Numbers, the planner's notes),
Protocol · n (the code review, `web/src/components/CodeReview.tsx`), Prep sheet (per slot, with Print). The tab and the step live in
the URL hash (`#protocol`, `#step=212`). Under the stage: the model's work fold, a timeline with one row per tool call and each
draft a checkpoint with its own Simulator / Plate map / Biology rows (`web/src/components/Timeline.tsx`; `api/steps.py`, one
describer per tool); "Where every liquid ended up"; Download the protocol `.py`, Copy link, JSON. The rail: section 8. A live run
shows the timeline in the stage and the checks filling in the rail, then swaps to the replay when it ends; the URL never changes.

**`/examples`** (`web/src/pages/Gallery.tsx`). The evaluation's agent runs as examples: the request as written, one card a request
with a row per model (Super, Nano best of 3), a "harder" tag on the fifteen harder requests, filtered by technique, the count on each
filter. The sets are `PROVETTE_GALLERY_SETS` (`api/settings.py`). The numbers across them and the second wording are on Methods and
in `eval/`; a person's own runs are in the sidebar.

**`/check`, `/check/:id`** (`web/src/pages/Check.tsx`; `api/checks.py`). No model: paste, choose or drop a `.py` (a `.json` dropped
with it is the map; a `.py` with no `def run(` is not a protocol and is not taken, here and in `api/checks.py`,
`protocol_problem`), pick an example map or paste one, one button, the result kept at a shareable URL under `<data>/checks/<id>/`.
The example is `tests/fixtures/protocols/pcr_buggy.py` with `pcr-01`'s map: "a PCR set-up with bugs planted on purpose. The
simulator passes it; the checks do not." Twenty checks a minute per address, and the process-wide simulation slots
(`api/analysis.py`, `slot`). The tab remembers one check, not a history (`web/src/lib/api.ts`, `checkMemory`; `sessionStorage`,
like the judge key): the composer's draft survives a tab switch, a posted check's id is kept, the **Check** tab and `/check` open
that result, "Check another" in its header opens the composer (`/check?new`) and clears nothing, and a remembered id that 404s
falls through to the composer silently and is forgotten.

**`/rules`** (`web/src/pages/Knows.tsx`). Four tabs kept in the hash: Rules (one row each, the paragraph and sources behind a
chevron), Words (the seven lists, an add-a-word input each), Coverage (per technique), Failures (the failed-run records, each with
"Start a rule from this"). **`/rules/new`** (`RuleForm.tsx`): the sentence with blanks at the top ("A tip that touched [a sample]
must never go into [a stock]"), the shape chosen by its sentence, the fields, a source picker that can add one, a preview on one
episode's final draft (`POST /api/rules/preview`, in the worker subprocess), "the file this writes" under a fold, and Save as
proposed.

**`/methods`** (`web/src/pages/How.tsx`; `api/evidence.py`): how the checks work, then four questions, each answered in a sentence with its table, every
number computed from a file under `eval/` when the page loads, the files named under each table, each pinned to the README by
`tests/api/test_evidence.py`. **`/about`** (`web/src/pages/About.tsx`): in our own words, what it does, the harness around the
model, what we found (from the same evidence as Methods), what it does not do, what we built, what it runs on, the licence.

**The replay** (`web/src/replay/`). Only what the ledger knows is drawn: the export's wells, origins, events and per-event deltas
(`provette/view/export.py`; `state.ts`). *Continuous motion* (`timeline.ts`): every event gets a duration from its kind and the
distance travelled; an event is a travel (rise to the clearance height, move, descend to the liquid's level, never under 1 mm from
the bottom: `actionHeight`) and an action (`ACTION_S`); the pipette is eased between known positions and the wells the event changes
are interpolated between the state before and after (`lerpRow`); a mix stroke in the same well has no travel; the 8-channel over a
trough is spread 9 mm apart along y, centred on the well as the robot does (`channelOffsets`, `centerMultichannelOnWells`); the bin
counts tips dropped and microlitres blown into it; a dry draw (an aspirate from a well the ledger had at 0 µl) reads "drew nothing:
A1 in slot 8 is empty" and marks the scrubber in the warning tone (`state.ts`, `dryDraw`; `Controls.tsx`, `dry`). Nothing else
moves: no droplets, no splash, no meniscus. *2D conventions* (`state.ts`, `Deck2D.tsx`): a well under 1 ml holding anything is drawn
at least a quarter full (`MIN_FILL`, `MIN_FILL_UNDER_UL`), a drawing rule like a map's minimum line width; a trough or a bigger tube
draws its true level, because there the level is the point; with the height table the fill is the ledger's own height, else volume
over the rated maximum (`wellFill`); a band's gradient (`SHADE`) is a convention and no claim; hatched stripes are "film only";
faint is uncertain; "not tracked" is a well the ledger has no state for, distinct from empty (`Replay.tsx`, legend). *3D*
(`Deck3D.tsx`): every labware at its real footprint, wells in the outline the height table gives them, the liquid cut off at the
table's height for its volume, coloured by share; the lighting and the gloss are convention, and the file says so: "The shading is
convention, like the choice of a lathe … A sheen says nothing about the liquid; a meniscus or a slosh would, so neither is drawn."
*Not drawn*, with counts and why (`docs/replay-support.md`): module bodies and the thermocycler lid (the trace records a module only
as the `module` of the labware on it), the thermocycler's programme, custom labware heights; every OT-2 protocol the tracer accepts
exports (787 of the 788 it accepts; `docs/replay-support.md`).

## 10. The evidence

Every run is described in its README under `eval/` ([`eval/README.md`](../eval/README.md)), and every number the pages show is
computed from its files (`api/evidence.py`) and pinned to its README (`tests/api/test_evidence.py`).

* **The checks** (`eval/checks/README.md`): 34 correct protocols against their own maps and against the wrong ones; the prep sheet
  against one worked out by hand; bugs planted with five mechanical edits, each counted as caught, missed or equivalent. The maps
  were written from the request text before any protocol was opened. A sample swap on a plate whose map leaves positions free is
  the limit of such a map (D-27).
* **The agent** (`eval/agent/README.md`): Super and Nano (best of 3) on the 34 requests and the 15 harder ones, with the checks as
  tools and the product's settings; every episode that did not verify is read.
* **The baseline** (`eval/baseline/README.md`): the twelve rules in the prompt and no checker, the same requests, one draft (D-30).
* **The planner** (`eval/planner/README.md`): the 17 plate maps proposed from the requests, three runs, held against the hand-written
  maps and a known-correct protocol (D-29).
* **The library audit** (`eval/audit/README.md`): the eleven map-free rules over the public library; counts of findings, not of
  problems, until the triage sheet is read.
* **The replay sweep** (`docs/replay-support.md`): every protocol of the library through the replay export.

**The wording rules the pages follow.** The claim is "with Provette in the loop, an open Nemotron model writes protocols that verify, which told the
rules alone it does not", resting on the loop, with the baseline quoted beside it as evidence for the loop and never as a page about the
model's mistakes (D-30). Never "no engineer needed": for the techniques the checks cover a biologist who does not program works on
their own; for a new procedure they are told what was not checked and can teach the checker; a run the loop cannot repair needs one
person per lab who reads code, who gets a two-line note (D-31). Numbers only from `eval/`, computed from files and pinned by tests.

## 11. How it runs

**The CLI** (`provette/cli.py`): `provette trace` (`--cross-check` exits 1 on a disagreement), `provette check protocol.py [--json]` (exit
0 clean, 1 an error or warning, 2 rejected), `provette verify protocol.py --platemap map.json [--json]`, `provette view … --out
replay.html` (one self-contained page), `provette plan "<request>"`, `provette corpus fetch|list|run|summary` (the public library at a
pinned commit, never committed: D-05). `--labware-dir` takes custom definitions.

**The API** (`api/README.md`): FastAPI, one router per job, wrapping the pipeline and never reimplementing it; every analysis is a
subprocess with a 180 s timeout, cached by the checker's digest, the protocol and the map (`api/analysis.py`); `/api/episodes…` the
gallery, `POST /api/checks` the checker, `/api/plans` and `/api/runs` the live flow with SSE streams, and one route each for the
rules, roles, coverage, declared rules, outcomes, evidence and documents; `/health`.

**The dev server**: `cd web && npm ci && npm run build`, then `sh deploy/dev-api.sh` on `:8765`; or `PROVETTE_WEB_DIR=web/dist env -u
PYTHONPATH uv run uvicorn api.main:app --port <n>` (`README.md`, "Try it"). The live flow needs `PROVETTE_API_KEY`, `PROVETTE_BASE_URL`
and `PROVETTE_JUDGE_PASSWORD`; without them the gallery and the checker work and `/api/live` says the flow is off. Every setting:
`deploy/README.md`, "Every setting"; `.env.example`.

**The image and the deployment** (`deploy/README.md`; `docs/deploy.md`): one image from `docker/api.Dockerfile` (the API, the
built pages, `opentrons` 8.8.2, `eval/` read-only), one always-on Fly.io Machine with one volume at `/data` holding the live
episodes, the checks, the cache, the spend ledger, the outcomes and the three files a person edits from the pages, seeded on first
boot and never overwritten after (D-36, D-37). One command once three files exist: `deploy/fly-up.sh`, reading
`~/.config/provette/fly.env`, `judge.env` and `token-factory.env`; `--dry-run` prints what it will do; `deploy/smoke.sh <url>` is the 31-route smoke test.

**The gate**: `make check` (lint, strict types, the Python suite; read the exit code, never the output), `make check-web`, `make
check-all` for both; `make hooks` runs it before every push; there is no hosted CI (`CONTRIBUTING.md`, "The gate"; `Makefile`).

## 12. The honest list

* **Modules are not drawn**: the trace records a module only as the `module` of the labware on it; no body, no thermocycler lid, an
  empty module not at all (`docs/replay-support.md`, "Modules"; `provette/state/README.md`, "What this module needs from the trace").
* **Custom labware has no height table**: drawn as a straight column; the contact model's height there is a floor, so a low dispense
  we call dry may be wet (`docs/replay-support.md`; `state/README.md`, row 10).
* **No labware upload on Check**: a protocol with its own definition is refused by the simulator there; `provette view --labware-dir`
  takes the folder (`docs/replay-support.md`).
* **Flex** is out of scope: it needs `opentrons` 9.x (D-07); JSON protocols and run-time parameters were not tried
  (`provette/trace/README.md`, "Known gaps"). The 30 library protocols that use private internals are skipped (D-06).
* **The judge key lives in `sessionStorage`**: it survives a reload, not a closed tab, so a shared machine does not keep it
  (`web/src/lib/api.ts`, `judge`). `/api/docs` is off unless `PROVETTE_API_DOCS=1`, which the dev server sets
  (`api/settings.py`).
* **The runs the loop does not close** need one person per lab who reads code; each one is read in `eval/agent/README.md` (D-31).
* **What the physics leaves unchecked**: every technique's `physics` lines in `provette/rules/coverage.yaml`: the delivered volume,
  drops, films, foam, evaporation, a tip brushing a cell layer; and anything that happens at a pause, off the robot (`default`).
* **The catalogue's other rows are not rules**: bead cleanup steps, component fractions, settled suspensions, replicates, volatile
  liquids and the rest of N9 to N18 (`docs/detection-catalogue.md`; `coverage.yaml`, `not_checked`).
* **Roles are English word lists**: liquids called A, B and C get structural severity only and are reported unplaced
  (`provette/rules/README.md`, "Known blind spots"); the library declares liquids in 11 of 833 protocols, so the role rules are silent
  there (`eval/audit/README.md`).
* **The planner** was tested on Super only, and a wrong map is caught by `verify` rather than prevented
  (`eval/planner/README.md`). **Nobody outside the team has judged a finding** (`eval/audit/README.md`,
  "Why the headline waits").
* **Nano's cut turns are expensive**: the continuation re-sends the whole conversation each time a turn is cut, and best of 3
  multiplies it (`provette/agent/README.md`).

## If a judge asks…

1. *Is the model grading itself?* No: the verdict is the runner's exit codes over `verify` and `check`, and an unchecked submitted
   draft is checked by the harness (`tools.py`, `is_clean`; `loop.py`, lines 305 to 315).
2. *Why not just tell the model the rules?* Told the twelve rules with no checker, the model still breaks them; with the checks
   in the loop it gets there (`eval/baseline/README.md` beside `eval/agent/README.md`; D-30).
3. *How do you know the trace is right?* Opentrons' own analysis of every run must agree with it, and does on 788 of 788 public protocols (16 of 16 at API 2.14 or later, where it is fully independent)
   (`provette/trace/README.md`; D-09).
4. *Does it cry wolf?* 34 of 34 correct protocols verify with no false mismatch, and every rule was flood-read over the library
   before it landed (`eval/checks/README.md`; `eval/audit/README.md`).
5. *What can't it see?* The physics, and every "not checked" line beside the verdict (`provette/rules/coverage.yaml`; D-25).
6. *Why is that carry-over only a note?* Severity follows what was carried: a carrier is a note, a sample keeps the structural
   severity (D-20; `docs/rule-sources.md`, "what may be carried into what").
7. *Why does the replay show a quarter-full well for 10 µl?* A drawing floor under 1 ml so the liquid is visible; troughs draw their
   true level; hover for the number (`web/src/replay/state.ts`, `MIN_FILL`).
8. *Where do the numbers on the pages come from?* Computed from files under `eval/` at request time and pinned to the READMEs by
   `tests/api/test_evidence.py` (`api/evidence.py`).
9. *Can a biologist add a rule without code?* A YAML file in one of three shapes, or the form; it runs as a note until adopted by a
   commit (`provette/rules/declared.py`; D-22, D-23).
10. *What happens when it gets stuck?* The record says where it stopped and the checks say what still fails; every such run in the
    evaluation is read (D-31; `eval/agent/README.md`).
