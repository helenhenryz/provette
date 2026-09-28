# The rulebook

The biology in Provette is governed by this page, and it is ours. Every
rule below says what it checks, what it rests on, and the numbers that decide when it
speaks. The numbers are yours to change: each one is a named constant at the top of the
rule's file, and the last section says how to change one safely.

This page is the rules as they stand, written from the rules themselves,
[`rule-sources.md`](rule-sources.md) and [`detection-catalogue.md`](detection-catalogue.md).
Every rule here is **adopted**; a rule we reject or re-number gets that written in its status
line, with the reason.

**A rule you can write without code.** Three kinds of rule are *declared*: a small YAML
file under `provette/rules/declared/`, one per rule, saying its shape ("a tip that has
been in a sample must not go into a reagent well", "a well this full must not be
mixed", "the enzyme goes in after the water"), its numbers, its severity, one paragraph
of why, the fix, its sources and who proposed it. ENZYME-BEFORE-DILUENT below is one;
`NO-SAMPLE-INTO-REAGENT-WELL` is a worked example left in the folder as *proposed*. A
proposed rule runs on every draft but only ever makes a **note** titled "(proposed) ...",
so it cannot block anything until you adopt it by writing the date into its file. How to
write one, and the three shapes and their fields, are in
[`provette/rules/README.md`](../provette/rules/README.md), "Declared rules".

What every rule has in common: Provette replays the protocol and knows what is in every
well and on every tip after every step. A rule reads that replay and reports a
*finding*: the line of the protocol, the wells, a sentence anyone in the lab can
read, and a severity. **Error** means the plate must be redone. **Warning** means a
result will be biased. **Note** means advice. A finding is *certain* when the replay
knows the tip touched the liquid; when it could not tell (the well's volume was
unknown), the finding is one level lower and says so. Rules that need to know what a
liquid *is* read the name the protocol gave it, through the word lists in
`provette/rules/roles.yaml`, a file of plain words, one per line, which you also own: add a
word under its list and no code changes. A name the lists cannot place changes nothing,
the finding says so, and the report ends by naming the liquid ("I do not know what
'lysozyme' is") and asking you which list it belongs in.

The library counts below are from the public Opentrons protocol library (833 protocols
written by other people, 787 of which Provette can check) and from the drafts our models
wrote in `eval/agent`; they say how often a rule speaks, which is what a number changes.

## CONTAM-STOCK — a used tip went into a stock

**The rule.** A stock is a tube or reservoir that held liquid before the robot started
and that the protocol draws from. If a tip that has been in some other liquid dips into
a stock, a little of that liquid stays behind, and every later draw from the stock
carries it to every well the stock feeds. One sample in the shared master mix is the
mistake this project began with.

**What it rests on.** Lab Manager: liquid left on a tip is carried to the next place the
tip goes. Promega: "Use individual pipette tips for all additions, being careful not to
cross-contaminate the samples." Illumina: "Change the tips for each sample." Hampel and
colleagues, a clinical lab on a liquid handler: 1 to 5% of wells next to a strong
positive came up contaminated, and 0.11% of 45,665 tests were false positives, every one
beside a strong positive.

**The numbers you own.** This rule has no threshold: a touch is a touch. What you own is
the severity table in `rule-sources.md` ("what may be carried into what") and the word
lists behind it: a *carrier* (water, PBS, buffer, medium) carried anywhere is a note; a
*sample* keeps the structural severity (error if the stock is drawn from again and the
trace spreads, warning otherwise); a *reagent* carried into a sample or another reagent
is at most a warning. Adding a word to a list changes which severity a named liquid
gets. The case it exists for is a diluent tip entering the stock it is about to dilute,
which is routine at the bench: a note, never a block; a sample carried anywhere stays an error.
Library: 247 of 787 protocols, 97 at error.

**What it does not fire on, and why.** Two liquids declared under the same name (water
from two tubes is still water). A liquid the protocol also puts into the stock on
purpose. One line that sends one tip into several undeclared stocks (one reagent split
over reservoir channels): a note, because the rule cannot tell that from eight patient
samples, and a protocol that declares its liquids can.

*Proposed by the team; adopted.*

## CONTAM-WELL — a used tip carried liquid into wells it was never meant for

**The rule.** A tip that has been in liquid X touches the liquid of a well that the
protocol never, at any point, means to hold X. So X was never meant to be there. It is
what happens when one tip adds a reagent to a row of different samples and dips into
each: every well gets a little of the wells before it.

**What it rests on.** The same sources as CONTAM-STOCK. Artel: "unwanted residual
reagents could be carried over and contaminate subsequent transfer steps."

**The numbers you own.** No threshold; the severity table and the role word lists, as
above. The base severity is a warning, because without knowing what the wells hold the
rule cannot say how bad the mix-up is; a sample-into-sample carry stays a warning, a
carrier becomes a note. Library: 37 of 787 protocols.

**What it does not fire on, and why.** Replicates that hold the same liquids. A serial
dilution done with one tip (the liquid is carried down the row on purpose). Mixing in a
well the tip has just dispensed into. One tip filling many wells from above the liquid.
A first version of this rule flagged 117 of 150 library protocols; these four exclusions
are what made it usable.

*Proposed by the team; adopted.*

## MIX-BEFORE-DRAW — liquid drawn from a well that was not mixed after an addition

**The rule.** A well already holds liquid, the protocol adds a different liquid to it,
and later draws liquid out again without mixing in between. Two liquids layered in a
small well do not mix on their own, so what the tip draws is not at the concentration the
author calculated, and in a dilution series every later step inherits the error.

**What it rests on.** Integra: mix after every transfer, "about 5 cycles at about 80%
of the volume". Svec and colleagues used a fresh tip at every step of a dilution series.
Artel: reagents "not well mixed ... will be very different from the assumed theoretical
concentration levels".

**The numbers you own.**

| constant | value | what it means | raising it | lowering it |
|---|---|---|---|---|
| `WHOLE_WELL` | 0.9 | a draw of this share of the well takes everything, so layering cannot matter | more draws count as "took it all" and go unreported | a wash that removes 85% of a well starts to fire |
| `SAME_SHARE` | 0.01 | two compositions are the same if every share agrees this closely (a top-up of the same liquid is not an addition) | fewer top-ups count as additions | a top-up with a slightly different mix starts to fire |

Library: 162 of 787 protocols; no library serial dilution lacks a mix (0 of 16), so the
library findings are other shapes. In model-written serial dilutions it is the commonest
finding, which is what it is for.

**What it does not fire on, and why.** An empty well (nothing to layer). The same liquid
topped up. A draw that takes nearly all of the well. Everything drawn going to the
trash, where concentration does not matter.

*Proposed by the team; adopted.*

## PIPETTE-RANGE — a pipette asked for less than its minimum

**The rule.** Every pipette has a range. Below its minimum it cannot draw the volume, or
draws it so inaccurately that the number in the script is fiction; a P300 asked for
5 µl may deliver anything. The simulator passes the move, the volumes add up on paper,
and the plate map is satisfied, which is why this rule exists.

**What it rests on.** Opentrons' pipette specifications (P20: 1 to 20 µl, P300: 20 to
300, P1000: 100 to 1000). Integra and BRAND: work at 35 to 100% (or 30 to 100%) of the
nominal volume.

**The numbers you own.** None: the minimum comes from the pipette's definition and an
aspirate below it is an error. There is no "legal but low" tier at a share of nominal,
because drawing exactly the minimum (20 µl of master mix with a
P300) is what real protocols do and it fired on every one. Library: 127 of 787.

**What it does not fire on, and why.** Air gaps (not liquid). A mix is judged like any
aspirate. A distribute is judged on its one big aspirate, not on the parts it dispenses.

*Proposed by the team; adopted.*

## WELL-CAPACITY — more liquid than the well holds

**The rule.** Every labware definition states a maximum for its wells, and that number
is the maker's *working volume*, not the rim: by the same definition's shape the NEST
"100 µl" PCR well holds about 217 µl to the rim, the "200 µl" flat well 368, the
1.5 ml tube 1,898. Past the rim, liquid runs into the neighbours and onto the deck;
between the stated maximum and the rim it climbs the wall, wets the seal, and spills
when a tip mixes it. The plate map still verifies either way, because the volumes add up
on paper.

**What it rests on.** The Opentrons labware schema ("Total well, tube, or tip volume in
microliters"). LabOP, on protocol languages: "checking whether a protocol might add
more liquid to a container than it can hold" is the first semantic check. A practitioner
who overflowed a PCR well with 180 to 200 µl of ethanol (labautomation.io 3683). The
library flood read: of 123 protocols over a stated maximum, 117 were under
the rim and 6 spilled, which is why the rim and not the stated maximum decides the
severity.

**The numbers you own.**

| constant | value | what it means | raising it | lowering it |
|---|---|---|---|---|
| `MIX_SHARE` | 0.9 | a mix stroke in a well this full (of the rim when known, else of the stated maximum) pushes liquid out: warning | fewer brim warnings; a well mixed at 92% full goes unreported | wells at 80% start to warn |
| `STROKE_SHARE` | 0.1 | a stroke smaller than this share of the well spills nothing, so the brim warning stays silent | small strokes in full wells stop warning | tiny strokes in full wells warn (MIX-TOO-WEAK already covers them) |
| `SLACK_SHARE` | 0.01 | within this share of the limit nothing is said (rounding) | a well 3% over goes unreported | float rounding starts to fire |
| `SLACK_UL` | 1.0 | or within this many microlitres | same | same |
| `EXEMPT_WORDS` | waste, trash | labware whose label or name has these words is meant to be filled | more names exempt | fewer |
| `SINK_WORDS` | reservoir, tube | a well in labware named like this that is only ever poured into and never drawn from is a sink, whatever it is called | more labware kinds can be sinks | fewer |

Severities: past the rim, error; past the stated maximum but under the rim, or with no
rim known (every custom definition), warning with both numbers in the text; a
declaration above what the well holds, note.

**What it does not fire on, and why.** Waste and trash labware. Sinks. A well within the
slack. A definition with no stated maximum. A mixing stroke under a tenth of the well.

*Proposed by the team; adopted.*

## SOURCE-TOO-SHALLOW — the pipette aspirated above the liquid

**The rule.** Opentrons aspirates 1 mm above the bottom of a well unless told otherwise.
In a tube that is fine: the cone lifts even 20 µl above the tip. In a wide flat vessel it
is not: 2 ml of master mix in the 195 ml reservoir is 1.2 mm deep, and after 46 draws of
18 µl the surface is below the tip, so the other 50 draws are air and 50 wells get no
mix. The simulator says nothing, and the "would run dry" check counts microlitres, not
millimetres.

**What it rests on.** Opentrons: "the pipette will aspirate from a default position 1 mm
above the bottom center of that well". Artel: "maintain a tip depth of about 2–3 mm
below the surface of a reagent reservoir"; "Pipetting errors may occur if reagent
continues to be removed and tip heights are not being compensated." Gilson's immersion
table (2 to 3 mm for 1 to 100 µl). Integra: a standard reservoir's dead volume was
260 µl, 23% of a plate's master mix. A qPCR lab whose negative controls came up positive
after "aspirating air" (labautomation.io 7592).

**The numbers you own.** The rule fires, as an error, when the tip is above the surface
and the surface is known exactly, which the labware definition's shape gives.

| constant | value | what it means | raising it | lowering it |
|---|---|---|---|---|
| `HAND_AIR_GAP_SHARE` | 0.5 | an aspirate this far up the well, or higher, is an air gap written by hand and not judged | a hand air gap at 60% of the depth starts to fire | an aspirate at 40% of the depth passes as an air gap |
| `NO_MARGIN` (in `provette/intent/prep.py`) | 0.9 | a well drawn down past this share of the most it held is the prep sheet's flag, not this rule's | | | On the library it can only test the 8 protocols that declare their liquids; 2 fire, each a
real air draw.

**What it does not fire on, and why.** An `air_gap`, or an aspirate in the top half of
the well, or an aspirate above the liquid that the same tip follows at once with a real
draw from the same well (all air gaps by hand). A well whose shape is unknown (the replay
calls the contact uncertain and the rule stays silent rather than guess). A protocol that
declares no liquids: a well the robot filled may have arrived full. A well that holds
less than the draw asks for, or is running out: the prep sheet already says so.
`well.bottom(x)` with the tip below the surface.

*Proposed by the team; adopted.*

## COLD-MODULE-NEVER-SET — a temperature module was loaded but never set

**The rule.** A temperature module sits at room temperature until the protocol calls
`set_temperature`, which waits until the block gets there. Authors load one because the
request said "on a cold block", put the enzyme or the cells on it, and forget the call;
the robot runs the whole protocol with the module off, and the person setting up the deck
sees a module and assumes it is cold.

**What it rests on.** Opentrons: "the robot won't begin performing other protocol steps
until the Temperature Module reaches the target temperature"; "Your robot will not
automatically deactivate the Temperature Module at the end of a protocol." NEB: "We
recommend assembling all reaction components on ice." Thermo: "Set up PCR on ice."

**The numbers you own.**

| constant | value | what it means | raising it | lowering it |
|---|---|---|---|---|
| `COLD_CELSIUS` | 10.0 | a module set only after its liquids were used counts as a forgotten cold block when the late setting is at or below this; above it, the author meant an incubation | a 15 °C late setting counts as forgotten | a 4 °C late setting counts as an incubation |

Library: 48 of 787 protocols. In the reads that set the cold line, most modules that were set
only after their liquids were used were set warm, and every one read was a planned incubation,
which is why the cold line exists.

**What it does not fire on, and why.** A module set before the first use of anything on
it, at any temperature. A module used first and then set warm (an incubation). A module
with nothing on it, or with labware nobody pipettes from or into. A thermocycler (its
block is set by a profile) and a heater-shaker (nothing is meant to be held cold on it).
The catalogue's error for "the request asked for a cold block and there is none" waits
for the plate map to carry that fact.

*Proposed by the team; adopted.*

## MIX-TOO-WEAK — mixing too weak to stir the well

*The finding's title carries its numbers: "Mixing too weak to stir well A1 in slot 3: 3 × 5 ul
in 25 ul", "Too few strokes to mix …: 2 × …", "A mix stroke as big as the well …", or "A pipette
too small to mix …".*

**The rule.** A mix is only a mix if the stroke moves most of the well. Two strokes of
10 µl in a 505 µl deep well mix nothing, and a 20 µl stroke in a 20 µl well draws air
from the bottom and foams the liquid. The rule looks at every run of mixing strokes in a
well of known volume and says when the stroke is too small, the strokes too few, or the
stroke the whole well.

**What it rests on.** Integra: dynamic mixing is "aspirating and dispensing >80 % of the
total ... volume, repeated 5 times". Beckman: "Mix with a tip volume just slightly below
the total well volume." Esca Automation: "3 mixes yielded 11.8% CV while 20 mixes yielded
1.7% CV." A dairy QC lab: 800 µl "is not going to be anywhere close to be able to mix
20mL of sample, regardless of the number of mixing cycles" (labautomation.io 3654).

**The numbers you own.**

| constant | value | what it means | raising it | lowering it |
|---|---|---|---|---|
| `MIN_WORK` | 2.0 | the mixing work: strokes × the stroke's share of the well (or of the pipette's maximum, where the well holds more than the pipette can draw); under this the strokes move too little in all | 10 strokes at 25% (2.5) start to fire | 3 strokes at 50% (1.5) start to pass |
| `MIN_STROKES` | 3 | fewer strokes than this do not mix a well | one-stroke mixes after a dispense start to pass | two-stroke mixes start to pass |
| `CAP_SHARE` | 0.2 | a pipette whose maximum is under this share of the well cannot mix it, whatever the count (a P20 in a 505 µl deep well) | a P300 in a 1 ml tube starts to fire | a P20 in 150 µl starts to pass |
| `GOOD_SHARE` | 0.8 | what the fix suggests (Integra's "over 80%") | the advice only | the advice only |
| `GOOD_STROKES` | 5 | what the fix suggests | the advice only | the advice only |

The work clause replaced a plain "under half the well" line after the library read: of
twenty findings read under the old line, five false alarms were mixes
at 36 to 48% with 4 to 10 strokes, which do mix (work 1.4 to 4.8), and every real one
had work under 2. A single stroke in a stock immediately before drawing from it is a
prime, not a mix, and is excluded.

**What it does not fire on, and why.** A well of unknown volume. A well holding one
liquid (the pre-wet of a tip in a reagent trough), unless a second liquid arrives later
with no other mix. A stock the protocol only draws from (mixing a stock is resuspension).

*Proposed by the team; adopted.*

## UNMIXED-AT-END — a well was never mixed after its last addition

**The rule.** When a small volume is dropped into a larger one, the two sit in layers:
2 µl of template under 18 µl of master mix, 5 µl of loading dye on 15 µl of protein,
3 µl of DNA under 47 µl of water. Nothing in a small well mixes them on its own.
MIX-BEFORE-DRAW catches the case where the protocol draws from the layered well; this rule
catches the case where the protocol simply ends. A PCR plate is usually vortexed and spun
before cycling, so there it is a note; a normalisation that is not mixed is not
normalised, so where the last addition is a sample it is a warning.

**What it rests on.** Artel, as for MIX-BEFORE-DRAW. Illumina, normalising libraries:
"gently pipette contents up and down 10 times to mix thoroughly". Thermo PowerTrack:
"The reaction plate was not mixed well" as a cause of variable replicates.

**The numbers you own.**

| constant | value | what it means | raising it | lowering it |
|---|---|---|---|---|
| `MIXES_ON_ENTRY` | 0.3 | an addition of this share of the well, or more, mixes as it lands, so it needs no stroke | a 40% addition counts as layered | a 20% addition counts as mixed on entry |
| `MIX_WORDS` | master mix, mix, SYBR, Taq, polymerase, qPCR, PCR | a well holding a liquid named like this is a PCR well: note, not warning | more liquids make a well "PCR" | fewer |
| `WASTE_WORDS`, `SINK_WORDS` | as in WELL-CAPACITY | labware that is only ever poured into is not judged | | |
| `GOOD_SHARE`, `GOOD_STROKES` | 0.8, 5 | the advice in the fix | | |

The default is a note: a PCR plate is usually vortexed and spun before cycling. A normalisation
or a pool whose last addition is a sample is a warning, because nothing after it will ever mix
it.

**What it does not fire on, and why.** A well drawn from after the addition
(MIX-BEFORE-DRAW's). An addition of 30% or more. A top-up of a liquid the well already
holds. A well of unknown volume. A well whose last addition was followed by a mixing
stroke. Trash, waste and sinks. A blow-out is neither an addition nor a mix.

*Proposed by the team; adopted.*

## ENZYME-BEFORE-DILUENT — an enzyme was added before the water

**The rule.** Enzymes are shipped in 50% glycerol and are meant to be the last thing into
a reaction, after the water and the buffer have brought the well to the right dilution.
An enzyme dropped into 2 µl of neat 10x buffer, or into a dry well, meets ten times the
salt it should: restriction enzymes cut at the wrong places (star activity) and
polymerases start on mis-primed template. Every `clone-01` and `pcr-07` draft from every
model did this: buffer, enzyme, plasmid, water.

**What it rests on.** Thermo: "Ensure that the restriction enzyme is the final component
added to the reaction mix"; "Add DNA polymerase last to the reaction mixture". NEB's Q5
manual and Promega's GoTaq bulletin give the same order in their set-up tables. Thermo and
Promega: star activity above 5% glycerol (Promega: many enzymes tolerate 10%).

**The numbers you own.**

| constant | value | what it means | raising it | lowering it |
|---|---|---|---|---|
| `share` (in `provette/rules/declared/ENZYME-BEFORE-DILUENT.yaml`; the rule is declared, shape `add_after`) | 0.5 | the share of its final water and buffer a well must already hold when the enzyme goes in | water first and buffer after the enzyme starts to fire | an enzyme into a nearly dry well starts to pass |
| `_ADD_LAST` (in `roles.py`) | enzyme, polymerase, Taq, ligase, BsaI, restriction, reverse transcriptase, RT, master mix | the liquids that go in last | | |
| `_ADD_FIRST` (in `roles.py`) | water, H2O, buffer, diluent, TE, Tris, medium | the liquids that go in first | | |
| `HALF` | 0.5 | the share of its final water and buffer a well must already hold when the enzyme goes in | water first and buffer after the enzyme starts to fire | an enzyme into a nearly dry well starts to pass |
| `add_last` (in `roles.yaml`) | enzyme, polymerase, Taq, ligase, BsaI, restriction, reverse transcriptase, RT, master mix | the liquids that go in last | | |
| `add_first` (in `roles.yaml`) | water, H2O, buffer, diluent, TE, Tris, medium | the liquids that go in first | | |

The library declares no liquids, so the rule is silent there.

**What it does not fire on, and why.** An enzyme that is the last addition. A well that
already held half its final diluent. An enzyme arriving inside a master mix made in
another tube. A master mix that is itself the bulk of the reaction (a 2x mix followed by
the sample). A well whose final volume is unknown. A protocol that declares no liquids.

*Proposed by the team; adopted.*

## NO-NEGATIVE-CONTROL — no no-template control on a PCR plate

**The rule.** A PCR or qPCR plate needs one well with everything except the template: if
that well lights up, a reagent is contaminated or the primers pair with each other, and
every other well's signal is in doubt. A standard curve needs a blank, and an RT-qPCR
plate needs a well without the reverse transcriptase. The requests never ask for these,
so a model rarely adds them; every finding is a note, advice to the writer and
to the person approving the plate map.

**What it rests on.** MIQE 2009, an essential item: "NTCs should be included on each
plate or batch of samples." Thermo Maxima: "The NTC reaction contains all components
except template DNA." Bio-Rad: "you should always prepare a no-template control for your
PCR assays to verify that no contamination has occurred." Qiagen: "A no RT control ...
should be included when performing gene expression analysis." Bustin 2025: MIQE
"compliance remains patchy".

**The numbers you own.**

| constant | value | what it means | raising it | lowering it |
|---|---|---|---|---|
| `MIN_REACTION_WELLS` | 4 | fewer reaction wells is not a plate worth a control | small plates go unreported | a two-well test asks for an NTC |
| `MIN_SERIES_LEVELS` | 4 | a sample at this many levels falling by one constant factor is a standard curve, so a blank is expected | | |
| `MIN_LEVELS_WITH_CARRIER` | 3 | or at this many distinct concentrations diluted with a carrier | | |
| `SERIES_TOLERANCE` | 0.05 | levels, and the factor between them, are the same within this | | |
| `mix`, `rt` (in `roles.yaml`) | master mix, mix, SYBR, Taq, polymerase, qPCR, PCR; RT, reverse transcriptase, RTase | the words that make a plate a PCR plate, and a reagent an RT | | |


**What it does not fire on, and why.** A plate with fewer than four reaction wells. A
plate that has the control (a well of mix and water, or mix alone; a film of sample left
by a tip does not unmake it). A one-step RT mix whose own name has the RT word (the
control would need a different mix, which the rule cannot see). A protocol that declares
no liquids.

*Proposed by the team; adopted.*

## How to change a number

1. Open the rule's file under `provette/rules/` and change the constant at the top (for a
   declared rule, the field in its `declared/<RULE-ID>.yaml`). Word lists live in
   `provette/rules/roles.py`. Write the reason in the comment next to it, in one line.
1. Open the rule's file under `provette/rules/` and change the constant at the top. Word
   lists live in `provette/rules/roles.yaml`: add a word as one line under its list (the
   note at the top of the file shows the shape), or let the product add it when a report
   says "I do not know what ... is". Write the reason in the comment next to it, in
   one line.
2. Regenerate the frozen expectations of the fixtures:
   `PROVETTE_REGEN=1 env -u PYTHONPATH uv run pytest tests/rules`. Then read every
   `.expected.json` that changed (`git diff tests/fixtures/rules`): each fixture's first
   line says whether it should fire, and a number that turns a near miss into a finding,
   or the other way round, is the number telling you something.
3. Run `make check` and read the exit code. Exit 0 is the gate.
4. Run the rule over the drafts and the library before trusting it
   (`env -u PYTHONPATH uv run provette check <protocol> --json`; the corpus runner in
   `provette/corpus/README.md` does the whole library). A rule that floods is worse than no
   rule: PIPETTE-RANGE's low tier was deleted for exactly that.
5. Write it down where the next person will look: the new value and its reason in this
   page's table for the rule, the source that justifies it in `rule-sources.md` if it is
   new, and one line in `DECISIONS.md` if it changes what a finding means. Then update
   the rule's status line here.
