# `provette/rules` — the biology checks

`provette check protocol.py` runs every rule in `RULES` over the trace and the replayed
state and prints what it found, in words anyone in the lab can read. A
rule is a plain function `(trace, run) -> list[Finding]` with an id, a family, a tier,
a description, a status (adopted, or proposed: see "Declared rules" below), who
proposed it, and **its sources: a rule without a source does not load**
(`docs/rule-sources.md` is where a rule starts). A rule is written in Python, or
*declared* in a small YAML file under [`declared/`](declared/) without any code.

```
uv run provette check protocol.py          # the report
uv run provette check protocol.py --json   # the same, as data, with every rule's description
```

Exit 0 when nothing of severity error or warning was found; 1 otherwise; 2 when the
simulator rejected the protocol.

## The rules

| rule | fires when | severity | tier | status |
|---|---|---|---|---|
| `CONTAM-STOCK` | a tip that has been in another liquid touches the liquid of a **stock** (a well that held liquid from the start and that the protocol draws from) | error if the stock is drawn from again and the trace reaches wells it was never meant for; warning otherwise; then graded by what was carried (below) | structural | adopted |
| `CONTAM-WELL` | a tip that has been in a liquid touches the liquid of a well into which the protocol never transfers that liquid on purpose | warning; graded by what was carried | structural | adopted |
| `MIX-BEFORE-DRAW` | a well that holds liquid receives a different liquid, and liquid is later drawn out of it with no mixing in between | warning | structural | adopted |
| `MIX-TOO-WEAK` | a run of mixing strokes that cannot mix the well: a mix counts only if the strokes together move about two wells' worth of liquid (the number is in the rulebook), there are at least three of them, and no stroke is the whole well or more; when the well holds more than the pipette can draw the strokes are measured against the pipette instead, and a pipette that cannot draw a fifth of the well fires whatever the count, with the fix naming a bigger one. Silent on a well holding one liquid (a pre-wet), on a stock only drawn from, and on a prime (one stroke, then a draw from the same well with the same tip) | warning | structural | adopted |
| `PIPETTE-RANGE` | an aspirate asks a pipette for less than its minimum volume | error | structural | adopted |
| `WELL-CAPACITY` | a dispense takes a well past its rim, by the labware definition's shape (error); past the maker's stated maximum but under the rim, or where no rim is known (warning); a mix in a well 90% full or more (warning); a well declared to start with more liquid than it holds (note). Waste and trash labware, and reservoirs, tubes, beakers, bottles, troughs or containers only ever poured into, are exempt (a plate never is: a destination plate is only ever poured into too). When a pause comes between the well's last draw and the crossing, the finding says so, because a plate emptied by hand or on a washer there is something the script cannot show | error / warning / note | structural | adopted |
| `SOURCE-TOO-SHALLOW` | an aspirate's tip is above the liquid in a well whose shape is known (the definition's volume-to-height table, or a flat bottom), so the pipette draws air and every well filled from it is short; silent where the shape is unknown, in a protocol that declares no liquids, for an air gap (an `air_gap` call, an aspirate in the top half of the well, or an aspirate at any height that the same tip follows at once with another draw from the same well, whether or not that one reaches the liquid), when the well holds no more than the draw asks for, or when it is simply running out (both the prep sheet's flag) | error | structural | adopted |
| `COLD-MODULE-NEVER-SET` | labware sits on a temperature module, and liquid is drawn from or put into it before the protocol ever sets the module's temperature (the block is at room temperature until it is set); once per labware, and if a cold setting (10 C or below) comes later the finding says at which line. A module used first and then set warm, to 37 C say, is a planned incubation and is left alone, as are thermocyclers, heater-shakers and untouched labware | warning | structural | adopted |
| `ENZYME-BEFORE-DILUENT` | a well receives an enzyme, polymerase or master mix straight from its stock, and the water or buffer that makes the dilution comes afterwards, when the well held less than half of its final water and buffer at the time. Silent when no liquids are declared, when the enzyme arrives inside a master mix made in another tube, or when the mix is itself the bulk of the reaction | warning | role | adopted (declared, `declared/ENZYME-BEFORE-DILUENT.yaml`) |
| `UNMIXED-AT-END` | the run ends with a well holding two or more different liquids, the last one added was under 30% of the well, and nothing mixed the well or drew from it afterwards (a draw is `MIX-BEFORE-DRAW`'s). Warning when the liquid added last is a sample, because nothing else will mix it; note otherwise, because a PCR plate is often vortexed before use. Silent on a top-up of the same liquid, an unknown volume, waste or trash labware, and a reservoir channel only ever poured into | warning / note | structural | adopted |
| `NO-NEGATIVE-CONTROL` | a PCR or qPCR plate has no well holding the mix and no sample (the no-template control); the plate counts as a PCR plate when a master mix or polymerase and samples end up together in at least four wells; a dilution series of one sample has no well of diluent without sample (the blank); a reverse transcriptase reaches the reaction wells and no well has the same contents without it (the no-RT control). Silent when no liquids are declared, under four reaction wells, and when the control exists | note | role | adopted |
| `NO-SAMPLE-INTO-REAGENT-WELL` (declared, `declared/NO-SAMPLE-INTO-REAGENT-WELL.yaml`) | a tip that has been in a sample touches the liquid of a well holding a reagent (a master mix tube, or a plate well the mix was handed out to) into which the protocol never transfers that sample on purpose; the same touch CONTAM-STOCK or CONTAM-WELL grades by role, named for the reagent well | warning when adopted; **a note titled "(proposed) ..." while proposed** | role | proposed by "example", the worked example of the declared form |
| `LABWARE-FOR-TECHNIQUE` (**runs in verify, needs the plate map**; `provette/intent/labware.py`) | the plate map's `technique` (copied from the request) needs a kind of destination the verified destination is not, by its load name: PCR setup, qPCR setup, Cloning, Transformation and Protein (gel samples) need a PCR plate or strips; ELISA, Bradford, protein and cell assays and cell culture need a flat or deep-well plate (warning, once per destination). An enzyme, polymerase, ligase or master mix declared in a reservoir channel for a PCR-class technique whose request says "tube" or names a temperature (note, on the `load_liquid` line). Silent with no technique, for a technique not in the table, for a load name that says nothing, and for a carrier in a reservoir | warning / note | structural (warning) / role (note) | adopted (verify) |

"Structural" means the rule needs no knowledge of what the liquids are: it is true
whatever they are. Every finding says whether it is **certain** (the replay knows the
tip touched the liquid) or not (the well's volume was unknown), and an uncertain
finding is reported one level lower.

**What was carried decides how much it matters (D-20).** A carrier (water, PBS,
buffer, medium) carried anywhere is a note; a sample keeps the structural severity; a
reagent carried into a sample or another reagent is at most a warning. The roles come
from the name the protocol gives in `define_liquid`, matched against the word lists in
[`roles.yaml`](roles.yaml): seven lists of plain words (sample, reagent, carrier; add_last
and add_first for the order of addition; mix and rt for the controls), one word per line,
which we own and edit without touching code. [`roles.py`](roles.py)
reads the file once at import and answers `role_of`, `order_of`, `is_mix_word` and
`is_rt_word`; [`roles_edit.py`](roles_edit.py) adds a word for the product
(`add_word`, `lists`). The severity table is in `docs/rule-sources.md`. A name the lists
cannot place changes nothing, the finding says so (`roles_basis: none`), and `provette
check` and `provette verify` list it under `unplaced_liquids` ("I do not know what
'lysozyme' is") so a person can teach it.

**One finding per root cause.** A loop that puts the same dirty tip into eight tubes
is one finding with eight occurrences, not eight findings. The root is the moment a
tip leaves material where it does not belong; everything that later flows out of that
well is *downstream* of the root and listed with it. The fingerprint of a finding is a
hash of the rule, the text of the root line and the wells, so it survives edits
elsewhere in the file; our triage labels key on it.

## Declared rules

A rule does not have to be code. If what you want to say is one of three *shapes*, you
write it as a small YAML file under [`declared/`](declared/), one rule per file, named
after its id, and `provette.rules` reads it in beside the Python rules the next time
anything runs. The engine is [`declared.py`](declared.py); the fields are documented at
the top of that file and every one is checked when the file is read: a missing field, a
severity that is not `error`, `warning` or `note`, a shape that does not exist, or a
source name that is not in [`sources.yaml`](sources.yaml) stops the import and says which
file and which field, so a broken rule never runs half-way.

The three shapes, in words:

| shape | says | its fields |
|---|---|---|
| `no_carry_over` | a tip that has been in a liquid of one kind must not go into a well of another kind | `carried_role`: sample, reagent, carrier or any; `into_role`: stock, sample_well, reagent_well or any |
| `full_well_not_mixed` | a well this full must not be mixed | `share`: how full, as a share of what the well holds (0.9 is nine tenths); `stroke_share`: the smallest mixing stroke that counts, as a share of the well |
| `add_after` | one kind of liquid must go in after another | `first` and `last`: `add_first`, `add_last` (the word lists in `roles.py`), or a role; `half_clause`: true to stay silent when the well already held half its final `first` liquid, or when the `last` liquid is the bulk of the reaction (a 2x master mix); `share`: that half, 0.5 unless you say otherwise |

`no_carry_over` reads the same carry-over facts as CONTAM-STOCK and CONTAM-WELL, so a
touch it reports is one they saw too; what a declared rule adds is the name and the
words for the case we care about. `full_well_not_mixed` is WELL-CAPACITY's
mixing tier with the numbers in the file. `add_after` is ENZYME-BEFORE-DILUENT's shape:
that rule *is* a declared rule now, `declared/ENZYME-BEFORE-DILUENT.yaml`, and its
fixtures pass with the same lines, wells and fingerprints they had when it was Python.

The whole of it, for the example rule:

```yaml
id: NO-SAMPLE-INTO-REAGENT-WELL
shape: no_carry_over
title: A tip that had been in a sample went into a reagent
severity: warning
carried_role: sample
into_role: reagent_well
why: >
  A reagent is shared: the master mix, the enzyme or the primer in that well goes into
  every reaction on the plate. A tip that has been in one sample leaves a little of it in
  the next liquid it touches, so a sample carried into a reagent well turns up in every
  well that reagent reaches, and a no-template control can no longer be trusted.
fix: >
  Use a fresh tip for each sample at line {line}, or add the reagent to the wells first,
  while the tip is clean, and the samples afterwards with a fresh tip each.
sources:
  - LAB_MANAGER_CARRY_OVER
  - WHO_MASTER_MIX
proposed_by: example
status: proposed
adopted_on: null
```

`why` is one paragraph you would say to anyone in the lab; the finding's explanation
is the facts (the line, the wells, what the tip carried) followed by it. `fix` may use
`{line}`, `{wells}` and `{liquids}`. `sources` are keys of `sources.yaml`, which is
`docs/rule-sources.md` as data (the Python rules cite the same keys, as `sources.THERMO_T4_LIGASE`;
the product's rule form can add one, `sources_edit.py`): a rule with no source does not load,
declared or not.

**The status rule.** A rule with `status: proposed` runs on every protocol like any
other, but everything it finds is a **note** titled "(proposed) ...". `provette check`
exits 1 only on an error or a warning, and the agent's `ready_to_submit`, `verify` and
the regrade all read that exit code, so a proposed rule can never block a draft: you
see what it would say, on real drafts, before anyone has to trust it. Adopting it is
changing `status` to `adopted` and writing the date in `adopted_on`; an adopted rule
fires at the severity in its file. A proposed rule has `adopted_on: null`, and the
engine refuses the other combinations.

**How to add one.**

1. Copy the file above (or any file in `declared/`) to `declared/<YOUR-RULE-ID>.yaml`
   and edit it: the id (capitals and dashes, and it must equal the file name), the
   shape and its fields, the words, your name in `proposed_by`, `status: proposed`.
2. Write the protocols that show it, the way every rule has them:
   `tests/fixtures/rules/<YOUR-RULE-ID>/fires_*.py` (at least two) and `near_miss_*.py`
   (at least three), each with a first line that says in plain words what it tests.
3. `PROVETTE_REGEN=1 env -u PYTHONPATH uv run pytest tests/rules` freezes what the rule
   found next to each fixture; read every `.expected.json` it wrote. A fires fixture
   must show your rule (as a note, while it is proposed); a near miss must not.
4. `make check`, and read the exit code. Exit 0 is the gate.
5. Add the rule to the table above and to `docs/rulebook.md`; if its source is new, to
   `docs/rule-sources.md` and `sources.yaml` first.

For the product's rule form, `declared.py` has `validate(data, name)` (the checks, as a
function), `save(data)` (validate, then write the file) and `preview(rule, protocol)`
(run one rule, saved or not, on one protocol and get its findings).

## How to add a rule in Python

1. Find what it rests on and add a row to `docs/rule-sources.md`. If there is no
   source, there is no rule yet. If the rule is one of the three shapes above, declare
   it instead of writing code.
2. Write it in words at the top of a new module, the way the existing ones do: what
   happens, why it matters to the experiment, what it does not fire on.
3. Write the protocols first: at least two under
   `tests/fixtures/rules/<RULE-ID>/fires_*.py` that must produce the finding, and three
   `near_miss_*.py` that must not. The first line of each says, in plain words, what it
   tests and whether it should fire. Realistic protocols a student would recognise.
4. Write the function over `facts_of(trace, run)` (`common.py`: moves, strokes,
   roots, consequences, stocks, roles, words for wells) and register it in `RULES`.
5. `PROVETTE_REGEN=1 uv run pytest tests/rules` freezes the expected findings next to
   each fixture; read every regenerated file before trusting it.
6. Run it over the correct protocols (`eval/checks/`, all 34 must still verify), the agent
   runs' drafts and the public library (`eval/audit/`), and read what it fires on. A rule that floods is worse than no rule: the legal-but-low tier
   of `PIPETTE-RANGE` was tried and deleted for exactly that.

## Known blind spots

* Stocks are recognised structurally: a well that held liquid from the start and is
  drawn from. A plate that arrives full of samples and is only ever drawn from is a
  set of stocks; one the robot fills first is not.
* Where the replay could not tell whether a tip touched the liquid (unknown volumes, a
  well whose shape no labware definition gives), the finding is uncertain and one level
  lower, never silent. `SOURCE-TOO-SHALLOW` is the exception: an uncertain air draw is
  not reported at all, because most of them were the straight-column model's doing.
* Time at temperature, order of addition, missing controls and bead-cleanup steps
  are in `docs/rule-sources.md` and not yet rules.
* The roles word lists (`roles.yaml`) know English laboratory names. A protocol that
  calls its liquids A, B and C gets structural severity only, and the report names
  each such liquid as unplaced.
