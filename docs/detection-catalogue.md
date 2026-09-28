# Detection catalogue — what Provette should detect, ranked

The question: which mistakes in
liquid-handling robot protocols happen in practice, ruin or bias an experiment, pass
the simulator, and can be seen by a deterministic replay of the script plus the names
of its liquids? Every row below rests on a page that was opened, and every source is also a row in
[`rule-sources.md`](rule-sources.md).

**How it was made.** Six streams: practitioner forums (50 pages,
mostly labautomation.io threads and Opentrons documentation); liquid-handling vendors
and metrology (30 pages: Opentrons, Artel, Tecan, Integra, Eppendorf, Sartorius,
Gilson, ISO 8655); assay vendors (40 pages and manuals: NEB, Thermo Fisher, Promega,
Qiagen, Illumina, Beckman, Bio-Rad); the literature (40 papers and standards: MIQE,
the LLM-protocol benchmarks, carry-over and mislabelling studies); Nemotron's own
drafts, written with the checks as tools while the rules were being designed (36 final drafts
read by hand as a biologist would, and 59 replayed by script); and the public Opentrons protocol library (833 protocols, scanned for the
patterns below). Reddit, the Opentrons support centre, Hamilton's site and NEB's HTML
pages could not be opened by any route; what they would have added is listed at the
end.

**Two things a judge should know first.** Five of the seventeen protocols that Super
submitted as verified in those drafts would fail as experiments before any physics is
considered, and no check today sees any of them: a master mix drawn from a trough
whose surface falls below the tip halfway through the plate, a dilution series that overflows its plate at every step,
an enzyme kept warm in a trough and added into neat buffer, and a flat culture plate
used as the PCR plate three times. The top of the table is those. And every paper that
adds a deterministic gate to an LLM-written protocol reports the ungated pass rate at a
third or less of the gated one (ProtoPilot 35.0% against 96.6%; on the OT-2 32.4%
against 88.2%), which is the published version of what `eval/baseline` and `eval/agent` measure.

## How the ranking works

Each row gets three scores, and the rank is their product.

| score | frequency | harm | detectability |
|---|---|---|---|
| 3 | seen in a tenth or more of the drafts we read, or the library, or called common by a source with a number | ruins the experiment or a sample: the plate must be redone | from the trace, the state and the declared liquid names alone, certain |
| 2 | seen a few times, or documented by a vendor without a rate | biases a result that will still be read | needs the plate map, a number from a datasheet, or a small addition to the trace that the labware definitions already supply |
| 1 | seen once, or plausible and unmeasured | wastes reagent or time; a note | needs information nobody records in a protocol |
| 0 | — | — | cannot be seen from a script: physics |

"Drafts" means the 36 final Nemotron drafts read by hand (17 Super plain, 12 Nano plain, 7
Super short-on-tips) and, where a number is given "of 59", every final draft of that
set the replay could run. "Library" means the 833 public Opentrons protocols.

## The map: every check, ranked

Rows marked **exists** are checks Provette runs today; they are scored the same way so
the table is one map. Tier: *structural* needs no knowledge of what the liquids are;
*role* uses the declared names through our word lists; *map* needs the
plate map.

| # | id | the mistake, in one sentence | how often, and where that comes from | what it does to the experiment | what the replay needs | tier | severity | score |
|---|---|---|---|---|---|---|---|---|
| 1 | `CONTAM-STOCK` **exists** | A used tip goes into a stock tube and the stock is then handed out to every well | 30 of 34 first drafts written without the loop had a carry-over finding; 242 of 787 library protocols (92 at error); 1 to 5% of wells next to a strong positive contaminated on a Bravo (Hampel 2024) | one sample in the shared mix reaches the whole plate | already tracked | structural, graded by role | error / warning | 27 |
| 2 | plate map (`verify`) **exists** | A liquid lands in the wrong well, at the wrong volume, or a step is left out | 5 of the 8 serious mistakes read in those first drafts were seen only by the map; 46% of transcriptomics datasets hold a mislabelled sample (Toker 2016); clinical mislabels 0.4 to 1 per 1000 (Hawker 2014) | the wrong answer for that well, silently | the plate map | map | error | 27 |
| 3 | **N1 `WELL-CAPACITY`** | A dispense takes a well past what the plastic holds; or a `load_liquid` declares more than the well can hold | 1 of 59 drafts over the maximum (200 µl in a 100 µl PCR well, submitted as verified); 4 more at the brim while mixing; 7 of 59 declare more than the well holds; 134 of 787 library protocols overflow at least once, 64 of them with a custom labware definition whose maximum is probably nominal | liquid spills over the rim into neighbours; the prep sheet asks for an impossible load | already tracked (`WellGeometry.max_volume_ul`) | structural | error over the maximum, warning at the brim during a mix, note for a declaration | 18 |
| 4 | **N2 `SOURCE-TOO-SHALLOW`** | The tip aspirates at 1 mm above the bottom, but the liquid in a flat trough or plate does not reach 1 mm, so the pipette draws air | 7 of 64 final drafts and 13 of 102 drafts written without the loop on the built rule, every one real, including Super's verified `pcr-03` (2 ml of master mix in a 195 ml trough is 1.17 mm deep by the definition's geometry; after 46 of the 96 draws the surface is under the 1 mm tip and the other 50 draw air) | every well short of the reagent; the whole plate wrong, and the 90% margin check silent at 60 to 86% | the well's volume-to-height model; the pinned labware definitions carry it (`innerLabwareGeometry` in 123 of 253, every common one) | structural | error | 18 |
| 5 | **N3 `COLD-MODULE-NEVER-SET`** | A temperature module is loaded, liquids sit on it and are used, and nothing ever sets its temperature; or the request asked for a cold block and none is loaded | 9 of 36 drafts (7 loaded and never set; 2 with the cold block asked for and absent); 60 of the 228 library protocols that handle liquid on a temperature module never set it (some are test-mode flags left on) | the enzyme or cells the author meant to keep cold sit at room temperature for the run | already tracked (module on the labware, `set_temperature` events); the plate map for "asked for" | structural (module) / map (asked for) | warning; error when the map asked for a setpoint | 18 |
| 6 | **N4 `NO-NEGATIVE-CONTROL`** | A PCR or qPCR plate has no well with master mix and no template (and a standard curve has no blank) | 14 of 36 drafts (10 PCR plates with no NTC, 4 curves with no blank); MIQE marks the NTC essential and Bustin 2025 calls compliance "patchy" | contamination and primer-dimer cannot be told from signal; the run cannot be published to MIQE | roles from the declared names | role | note (the request did not ask for one) | 18 |
| 7 | **N5 `LABWARE-FOR-TECHNIQUE`** | The destination is the wrong kind of plate for the technique: a flat culture plate as the PCR plate, a PCR plate as the ELISA plate, an enzyme in a 15 ml reservoir | 9 of 36 drafts (6 flat plates as "PCR plate", 1 PCR plate as ELISA plate, 3 enzymes in troughs) | the plate cannot go in a thermocycler or a reader; the reaction is never run | the technique word from the request (`requests.jsonl` has it; the plate map should carry it) and the labware's load name | map | warning | 18 |
| 8 | **N6 `UNMIXED-AT-END`** | A well gets a small addition on top of a larger one, nothing mixes it, and the run ends | 20 of 36 drafts: 2 µl of template under 18 µl of mix, 5 µl of dye on 15 µl of sample, DNA under water in a normalisation | what is in the well is not at the concentration calculated; a normalisation is not normalised | already tracked; this is `MIX-BEFORE-DRAW` with "the run ends" as the draw | structural | note; warning when the last addition is a sample or the well is a normalisation or gel sample | 18 |
| 9 | `MIX-BEFORE-DRAW` **exists** | Liquid is drawn from a well that was never mixed after a different liquid was added | fired on the dilution series at every model size, without the loop; 162 of 787 library protocols; no library serial dilution lacks a mix (0 of 16), so the library hits are other shapes | the dilution factor is wrong and compounds down the series | already tracked | structural | warning | 18 |
| 10 | `PIPETTE-RANGE` **exists** | A pipette is asked for less than its minimum | one otherwise clean draft asked a P300 for 5 µl; a third of Nano's plans; 127 of 787 library protocols | the volume cannot be measured; the simulator passes it | already tracked | structural | error | 18 |
| 11 | sample accounting (`verify`) **exists** | A sample is thrown away in a tip or the trash | 31 of 31 planted losses caught; 2 of 36 drafts drop excess in the tip | the sample is gone | already tracked | map | flag | 18 |
| 12 | prep sheet (`verify`) **exists** | A source is drawn below what was declared, or within 10% of it | fired rightly on `fill-01` and `elisa-01` in the drafts | the last wells get air | already tracked, but by ratio not by height (row 4 is the fix) | map | flag | 18 |
| 13 | **N7 `ENZYME-BEFORE-DILUENT`** | An enzyme, polymerase, ligase or master mix is dispensed into a well before the water or buffer that should dilute it | 8 of 36 drafts (enzyme into neat 10x buffer before the water in every `clone-01`; polymerase before water in every `pcr-07`) | star activity and mis-priming: the enzyme meets undiluted buffer or glycerol; NEB and Thermo say add it last | roles from the declared names | role | warning | 12 |
| 14 | **N8 `MIX-TOO-WEAK`** | A mix stroke is a small fraction of the well, or too few strokes, or the whole well | 7 of 36 drafts (2 strokes of 10 µl in 505 µl; 30 µl strokes in 200 µl; a 20 µl stroke in a 20 µl well); Integra says over 80% of the volume, 5 times; 3 mixes gave 11.8% CV against 1.7% with 20; 104 of 833 library protocols mix with under half the well's volume, 92 with fewer than 3 strokes (many are tip pre-wets, so the rule needs the well to be a reaction) | the well is not homogeneous; a serial dilution inherits the error | already tracked (stroke volume against the well's volume at that moment) | structural | warning | 12 |
| 15 | **N9 `BEAD-CLEANUP-STEPS`** | Supernatant removed before the beads have settled, fewer than two ethanol washes, beads over-dried, elution too short, or the whole eluate transferred | not in the evaluation requests (no bead request has a plate map); 23 library protocols remove supernatant within a second of engaging the magnet (26 within 30 s), though some of those are test-mode defaults; NGS labs report 10 to 30% lower yield on the robot than by hand and name these steps | DNA lost with the supernatant or left on the beads | roles (beads, ethanol) and the magnet engage events, which the trace keeps as `other` events | role | warning; error for supernatant removed with the magnet off | 12 |
| 16 | **N10 `COMPONENT-FRACTION`** | A reaction component is out of its allowed share: enzyme over 10% of a digest (glycerol over 5%), template over 40% of a PCR, undiluted cDNA over 10% of a qPCR, DNA over 25% of a digest | Without the loop: polymerase silently doubled by every size on `pcr-07`; the vendor limits are on every enzyme page | star activity, inhibition, wrong quantification | roles and the volumes, which the state has | role | warning | 12 |
| 17 | **N11 `NO-MASTER-MIX`** | The same three or more reagents are pipetted one by one into four or more reaction wells instead of once into a mix; or a sub-microlitre enzyme volume goes straight into a reaction | `pcr-07` at every size assembles 12 reactions from 6 components (the request asks for it); Promega: sub-microlitre enzyme "nearly impossible", make a master mix | tube-to-tube variation; enzyme amounts off by a lot | roles | role | note | 12 |
| 18 | **N12 `SUSPENSION-SETTLED`** | Cells, bacteria or beads are drawn from a tube long after the last mix | a dairy QC lab's second sample "always too high" (labautomation.io 3654); Integra's cell-seeding note mixes 30 times; Thermo: resuspend before every dispense series | the later wells get more (or fewer) cells than the earlier ones | roles (cells, culture, beads) and the clock, which the state has; the settling time is a decision, no source gives one | role | warning | 12 |
| 19 | **N13 `TIP-RACK-MISMATCH`** | A pipette is given a tip rack its definition does not list; or an 8-channel pipette is sent into labware without eight rows | 1 of 36 drafts (a P20 with a 300 µl rack, passed by the simulator); one Super one-shot sent an 8-channel P300 into a 24-tube rack; 10 library protocols aspirate at a negative height, below the well floor of stock labware | the run cannot physically happen as written | already tracked (the pipette definitions carry `defaultTipracks`; D-11 expands multi-channel targets) | structural | error | 9 |
| 20 | **N14 `REPLICATES`** | A qPCR sample or a standard-curve point is in fewer than three wells; an ELISA sample in fewer than two | 4 curves and every single-well ELISA in the drafts; Bio-Rad and Thermo say triplicate, MIQE asks for the number | the plate cannot show its own noise | the plate map (the request decides) | map | note | 8 |
| 21 | **N15 `BLOW-OUT-INTO-STOCK`** | A blow-out is aimed at a stock the protocol draws from again, or at a reaction well that already holds liquid | 2 of 36 drafts (96 blow-outs into the LB reservoir; into the master mix after 96 dispenses); 48 library protocols blow out into a stock after pre-mixing it, deliberately and with a clean tip; a clinical lab traced NTC contamination to a hard-coded blow-out | aerosol into the stock; bubbles in a 20 µl reaction | already tracked (`blow_out` events with their well) | structural | note; warning when the stock feeds the plate | 6 |
| 22 | **N16 `TIME-SPREAD`** | A time-critical reagent (enzyme, substrate, stop solution) reaches the first and last well minutes apart | every single-channel plate: `pcr-03` spreads the master mix over 28 minutes; Eppendorf names it for plate assays | the first and last wells react for different times | roles and the clock | role | note | 6 |
| 23 | **N17 `VOLATILE-OR-VISCOUS`** | Ethanol moved with no air gap; glycerol or master mix with no pause after aspirating | no volatile liquid in the evaluation requests; 74 of the 163 library protocols that name ethanol move it with no air gap; Eppendorf, Sartorius, Integra and Opentrons' own liquid classes all name it | drips on the deck; short volumes | roles (ethanol, glycerol, DMSO, Tween) | role | note | 6 |
| 24 | **N18 `THERMOCYCLER-LID`** | A profile runs with no lid temperature set; `block_max_volume` smaller than the wells hold | none of the 17 requests cycles on the deck; Opentrons documents both | condensation changes concentrations; holds start before the liquid is at temperature | already tracked (`lid`, `thermocycler_profile` events) | structural | note | 6 |
| 25 | **N19 `PRE-WET-AND-FIRST-ALIQUOT`** | A fresh tip multi-dispenses with no pre-wet, or the first shot of a distribute lands in a sample well with no disposal volume | Artel: the first and last dispense "commonly" differ; Sartorius: skipping the pre-wet is "common practice" for master mix; 6 library protocols distribute with a tip that dips into wells already holding liquid, one of them water through antibody dilutions | the first well short by the film volume | already tracked | structural | note | 6 |
| 26 | **N20 `CLOSER-PIPETTE-LOADED`** | 100 µl moved with the P1000 while a P300 is on the other mount | Sartorius measured 0.69% against 1.70% CV for the same 100 µl of ethanol | worse precision than the deck could give | already tracked | structural | note | 6 |
| 27 | **N21 `ENZYME-TIME-AT-AMBIENT`** | A ligase, non-hot-start polymerase, reverse transcriptase or restriction enzyme sits off a cold module for long | 0 of 59 drafts over 30 minutes (the evaluation requests are short); no vendor gives hours, only "keep on ice"; the numbers that exist say a week for restriction enzymes and 72 h for an assembled SYBR plate | activity lost; for a hot-start mix, nothing | already tracked (`material_temperature`); the threshold needs a datasheet, and there is none for the enzymes that matter | role | note | 4 |
| 28 | **N22 `SHAKER-TOO-FAST`** | A heater-shaker set above about 20 g | an NGS lab saw droplets cross wells from about 20 g and "catastrophic" contamination at 25 g | wells contaminate each other | the shaker's rpm (an `other` event) and the orbit radius | structural | warning | 4 |
| 29 | **N23 `HOT-NEIGHBOUR`** | A very strong positive sits next to a negative control | 0.11% false positives in 45,665 tests, every one next to a Cq 18 positive (Hampel 2024) | the negative reads positive | the plate map and a "strong positive" role | map | note | 4 |
| 30 | **N24 `OPEN-PLATE-DELAY`** | A plate sits open on the deck through a long delay | 0 of 59 drafts delay 10 minutes; 83 library protocols wait 10 minutes or more on an open deck, every one read a deliberate incubation; over 8% loss in 7 days in an incubator, 35% less growth in edge wells (Mansoury 2021) | evaporation, edge effect | the delay is in the trace; whether the plate is sealed is not, and no room-temperature per-hour rate was found | structural | note | 2 |
| 31 | **N25 `MODULE-LEFT-ON`** | The run ends with a module still heating or cooling | Opentrons: "Your robot will not automatically deactivate the Temperature Module" | samples cook after the run | already tracked | structural | note | 3 |
| 32 | low-end volume (35% of nominal) **rejected** | A legal volume below 35% of the pipette's nominal | Integra and BRAND say 35 to 100% | worse precision | already tracked | structural | — | tried and deleted: it fired on every master mix drawn at the minimum (journal, 2026-09-22) |
| 33 | simulator **exists** | Unknown labware, a tip overfilled, a dispense larger than the aspirate (API 2.17 and later), a slot conflict | what every LLM-protocol paper's first gate catches; ABC-Bench: wrong labware strings are the commonest LLM error | the run cannot start | — | — | rejected | — |

Rows 3 to 8 are the top of what does not exist yet; rows 13 and 14 follow. Those eight
are specified at the end of this page.

## The rows in full

For each new row: the checkable statement with its numbers, the source as opened, and
the fixtures a builder would write. Where a number is a decision and not a source, it
says so.

### N1 `WELL-CAPACITY`

*Checkable.* After every dispense, the well's volume against the labware definition's
`totalLiquidVolume` ("Total well, tube, or tip volume in microliters", the labware
schema). Over it: error, once per well, at the first event that crosses. At 90% or
more while a mix stroke runs in the well: warning (the stroke's air and the tip's own
displacement push it over). A `load_liquid` above the maximum: note, because the prep
sheet cannot be followed. The state already records `overflow`, once per well.

*Numbers.* From the definitions in the pinned `opentrons` 8.8.2: NEST 100 µl PCR plate
100 µl; NEST 200 µl flat 200 µl; Corning 360 µl flat 360 µl; PCR strips on the
aluminium block 200 µl; NEST 1.5 ml tube 1500 µl. These are the makers' totals, not
working volumes, so a finding over them is not cautious.

*Source.* The labware schema
([Opentrons/opentrons, shared-data labware schema 2](https://raw.githubusercontent.com/Opentrons/opentrons/edge/shared-data/labware/schemas/2.json));
the practitioner who overflowed a PCR well with 180 to 200 µl of ethanol and asked
for liquid-level following, which the OT-2 does not have
([labautomation.io 3683](https://labautomation.io/t/ot-2-moving-the-pipette-along-the-z-axis-and-pipetting-the-same-time-is-it-possible/3683));
LabOP naming "whether a protocol might add more liquid to a container than it can
hold" as the first semantic check a protocol language needs
([Bartley et al. 2023](https://jakebeal.github.io/Publications/JETC23-LabOP.pdf)).
The library's 129 overflowing protocols were read in the state README: real, or a
labware maximum more cautious than the plastic.

*Fixtures.* Fires: a 1:2 series that puts 200 µl into a 100 µl PCR plate (the Nemotron
`dil-01` shape). Fires: 350 µl standards mixed with 150 µl strokes in a 360 µl well
(warning). Fires: 500 µl declared in a 200 µl flat well (note). Near miss: the same
series in a 200 µl plate. Near miss: a deep-well plate filled to 1.9 ml of 2 ml with no
mix. Near miss: a waste reservoir over its maximum (a labware whose label or load name
says waste is exempt).

### N2 `SOURCE-TOO-SHALLOW`

*Checkable.* At every aspirate, the liquid's height in the source against the tip's
height. Opentrons aspirates "from a default position 1 mm above the bottom center of
that well". If the height of the volume left in the well is below the tip, the
pipette draws air. Error when it is certain; the volume drawn is then air in the
state, and every downstream well is short. The rule must not fire where the height is
not known well enough: today the state models every well as a straight column, which
under-reports height in conical wells (state README, "one departure"). The pinned
labware definitions carry `innerLabwareGeometry`, a section-by-section shape
(conical, spherical, cuboidal) for 123 of 253 definitions, including every plate,
tube and reservoir the drafts use; the trace should carry it, and the state
compute height from it. Until then the rule may fire only where the column is exact:
`wellBottomShape` "flat" (56 definitions), and it must stay uncertain elsewhere.

*Numbers.* From the definitions' inner geometry, which the built rule reads (both
reservoirs narrow toward the floor, so the top cross-section understates the depth):
NEST 12-channel reservoir, 500 µl is 1.69 mm deep, 300 µl 1.22 mm, 184 µl 0.87 mm,
130 µl 0.69 mm. NEST 195 ml reservoir, 2 ml is 1.17 mm, 1.17 ml 0.90 mm. NEST 200 µl
flat plate, 20 µl is 0.63 mm, 10 µl 0.31 mm, 5 µl 0.16 mm. NEST 1.5 ml tube, 5 µl is
1.02 mm and 2 µl 0.61 mm. The NEST 100 µl PCR plate lifts 10 µl to 2.14 mm. Artel: keep the tip "about 2–3 mm below the surface"; Gilson's
table gives 2 to 3 mm of immersion for 1 to 100 µl.

*Source.* [Opentrons, Liquid Control (default 1 mm)](https://docs.opentrons.com/v2/basic_commands/liquids.html);
the labware definitions in the pinned package (`opentrons_shared_data`, schema 2,
`innerLabwareGeometry`, `wellBottomShape`);
[Artel, Automated liquid handlers as sources of error](https://www.bioprocessintl.com/assays/automated-liquid-handlers-as-sources-of-error)
("Pipetting errors may occur if reagent continues to be removed and tip heights are
not being compensated"); the [Gilson Guide to Pipetting](https://solutions.pipette.com/wp-content/uploads/Gilson-Guide-to-Pipetting.pdf);
a qPCR lab whose negative controls came up positive after an 18 plus 18 µl double
elution "aspirating air" ([labautomation.io 7592](https://labautomation.io/t/aspiration-dispense-liquid-class-incompatibity/7592));
Integra's 260 µl dead volume in a standard reservoir, 23% of a plate's master mix
([Integra, divided reservoir](https://www.integra-biosciences.com/global/en/applications/minimizing-dead-volume-during-qpcr-set-divided-reservoir-assist-plus-pipetting-robot)).

*Fixtures.* Fires: 2 ml of master mix declared in a 195 ml reservoir, 96 draws of 18 µl.
Fires: 180 µl of PCR mix in a 15 ml channel (0.86 mm) drawn at the default height. Near miss: the
same mix in a 1.5 ml tube (conical: uncertain, so silent until the geometry lands).
Near miss: 1.2 ml of PBS in a 15 ml channel, 12 draws of 100 µl (the last draw is at
0 µl left: that is the prep sheet's flag, not this one). Near miss: a reservoir drawn
with `well.bottom(0.3)`.

### N3 `COLD-MODULE-NEVER-SET`

*Checkable.* A labware sits on a temperature module (the deck header says so), a
liquid on it is drawn from or dispensed into, and no `set_temperature` for that
module precedes the use: warning. If the plate map or the request names a setpoint
("reagents on a temperature module at 4 C", "on a cold block") and the run has no
module, or one that is never set: error. Separately, a `set_temperature` that comes
after the liquids have already been used is the same finding with the line of the
first use.

*Numbers.* The module holds 4 to 95 °C. No number is needed: a module never set is at
room temperature.

*Source.* [Opentrons, Temperature Module](https://docs.opentrons.com/v2/modules/temperature_module.html)
("the robot won't begin performing other protocol steps until the Temperature Module
reaches the target temperature"; the robot "will not automatically deactivate" it);
[Thermo Fisher, PCR troubleshooting](https://www.thermofisher.com/us/en/home/life-science/cloning/cloning-learning-center/invitrogen-school-of-molecular-biology/pcr-education/pcr-reagents-enzymes/pcr-troubleshooting.html)
("Set up PCR on ice"); the [NEB Q5 kit manual](https://www.neb.com/-/media/nebus/files/manuals/manuale0555.pdf)
("assembling all reaction components on ice"); [Thermo T4 DNA ligase](https://documents.thermofisher.com/TFS-Assets/LSG/manuals/MAN0011987_T4_DNA_Ligase_5_Weiss_1000_Weiss_U_UG.pdf).

*Fixtures.* Fires: the `pcr-07` shape, a module loaded, components on it, never
set. Fires: `clone-01` with the reagents in a reservoir and the request saying 4 °C
(error, from the map). Near miss: `set_temperature(4)` before the first aspirate.
Near miss: a module loaded with nothing used on it. Near miss: a module used only for
the destination plate after the run, set at the end for a hold.

### N4 `NO-NEGATIVE-CONTROL`

*Checkable.* The plate is a PCR or qPCR plate: some declared liquid's name matches the
reagent words for a mix (master mix, SYBR, polymerase, Taq, qPCR) and it is dispensed
into wells that also receive a sample-role liquid. If no destination well ends holding
that mix and no sample-role liquid, note: "no no-template control". For a standard
curve or a dilution series (a sample-role liquid reaching wells in a geometric series
of amounts), if no well holds only the diluent, note: "no blank". For RT-qPCR (a
liquid whose name says RT, reverse transcriptase), if no sample well lacks it, note:
"no no-RT control". The plate map may say controls are not wanted; then silent.

*Numbers.* MIQE: NTC "should be included on each plate or batch of samples". Bio-Rad
and Thermo: at least three replicates of each control. No omission rate exists in the
literature.

*Source.* [MIQE 2009](https://www.gene-quantification.de/miqe-bustin-et-al-clin-chem-2009.pdf)
(Table 1, "Results for NTCs — E"); [MIQE 2.0](https://academic.oup.com/clinchem/article/71/6/634/8119148);
[Bustin 2025](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC12154065/fullTextXML)
("compliance remains patchy"); [Qiagen, PCR controls](https://www.qiagen.com/en-us/knowledge-and-support/knowledge-hub/bench-guide/pcr/reference-genes-and-controls/pcr-controls);
[Bio-Rad Real-Time PCR Applications Guide](https://www.bio-rad.com/webroot/web/pdf/lsr/literature/Bulletin_5279.pdf);
[Maxima SYBR manual](https://assets.fishersci.com/TFS-Assets/LSG/manuals/MAN0012933_Maxima_SYBR_Green_qPCR_Master_ROX_Sol__k0251_UG.pdf)
("The NTC reaction contains all components except template DNA").

*Fixtures.* Fires: 6 cDNA samples in triplicate, 18 wells, nothing else (the Nemotron
`pcr-04` shape). Fires: a BSA curve with no water-only well. Near miss: the same plate
with one well of mix plus water. Near miss: a plate where the sample wells are a
colony PCR and one well gets mix only. Near miss: a normalisation (no mix-role
liquid anywhere).

### N5 `LABWARE-FOR-TECHNIQUE`

*Checkable.* The technique word of the request (PCR setup, qPCR setup, ELISA, Cell
culture, and so on, as `requests.jsonl` records it; the plate map should carry it)
against the class of the destination labware, read from its load name: `pcr` or
`strip` (a PCR plate or strips), `flat` (a flat plate), `deep` (a deep-well plate),
`reservoir`, `tuberack`. PCR, qPCR, cloning, digest and gel-sample destinations must
be PCR plates or strips; ELISA and Bradford must be flat plates; culture must be flat
or deep. A source the request calls "a tube" that is a reservoir: note. Opentrons
raises nothing for an odd pairing: "It's your responsibility to ensure the labware
and module combinations you load together work together."

*Numbers.* None.

*Source.* [Opentrons, Module setup](https://docs.opentrons.com/v2/modules/setup.html)
("The API generally won't raise a warning or error if you load an unusual
combination, like placing a tube rack on a Thermocycler"); the thermocycler page
loads only `opentrons_96_wellplate_200ul_pcr_full_skirt`
([Opentrons, Thermocycler](https://docs.opentrons.com/v2/modules/thermocycler.html));
ABC-Bench, where wrong labware identifiers were the commonest LLM error
([Liu et al. 2026](https://arxiv.org/html/2606.11150v1)).

*Fixtures.* Fires: colony PCR into `nest_96_wellplate_200ul_flat`. Fires: 40 sera into
a 100 µl PCR plate called the ELISA plate. Near miss: PCR into the NEST 100 µl PCR
plate. Near miss: a Bradford into a Corning flat plate. Near miss: a cherry-pick with
no technique class (silent).

### N6 `UNMIXED-AT-END`

*Checkable.* At the end of the run, a well that received two or more different
liquids, whose last addition was under 30% of the well's volume at that moment, that
has no mix stroke after that addition and is never drawn from. Note. Warning when the
last addition is a sample-role liquid or the technique is normalisation, a gel sample
or a Bradford, where nothing off the robot will mix it. Silent when the well is drawn
from later (`MIX-BEFORE-DRAW` owns that) or when the last addition is 30% or more (a
large addition mixes on entry, the same threshold the existing rule's `WHOLE_WELL`
reasoning uses).

*Numbers.* 30% is a decision; the sources give the principle, not a fraction. Integra's
serial-dilution note mixes over 80% of the volume five times; Artel: reagents "not
well mixed ... will be very different from the assumed theoretical concentration".

*Source.* [Artel, sources of error](https://www.bioprocessintl.com/assays/automated-liquid-handlers-as-sources-of-error);
[Integra, three serial-dilution protocols](https://www.integra-biosciences.com/global/en/applications/3-simple-and-proven-automation-protocols-serial-dilutions-assist-plus-pipetting-robot);
[Illumina, normalising library concentrations](https://support.illumina.com/ko-kr/bulletins/2017/03/best-practices-for-manually-normalizing-library-concentrations.html)
("gently pipette contents up and down 10 times to mix thoroughly");
[Thermo PowerTrack user guide](https://documents.thermofisher.com/TFS-Assets/LSG/manuals/MAN0018825_PowerTrackSYBRGreenMasterMix_UG.pdf)
("The reaction plate was not mixed well" as a cause of replicate variability).

*Fixtures.* Fires: 24 DNAs into water, no mix, run ends (warning). Fires: 2 µl of
template under 18 µl of mix, run ends (note). Near miss: the same with
`mix_after=(3, 15)`. Near miss: 100 µl of buffer into 100 µl of sample (50%: silent).
Near miss: a well that is drawn from afterwards (the other rule's).

### N7 `ENZYME-BEFORE-DILUENT`

*Checkable.* In one destination well, a liquid whose role is *add last* (enzyme,
polymerase, ligase, restriction enzyme, master mix, reverse transcriptase) arrives in
bulk before a liquid whose role is *add first* (water, buffer, diluent, medium) that
arrives later. Warning, once per line, with every well it did it to. Silent when the
enzyme is the last thing added, when it arrives in a master mix already made, or when
the well already held the diluent.

*Numbers.* Thermo: "Ensure that the restriction enzyme is the final component added";
"Add DNA polymerase last". NEB and Promega say the same in their set-up tables.

*Source.* [Thermo, 7 common issues with restriction digestion](https://www.thermofisher.com/us/en/home/brands/thermo-scientific/molecular-biology/molecular-biology-learning-center/molecular-biology-resource-library/spotlight-articles/7-common-issues-with-restriction-digestion-reactions-and-how-to-avoid-them.html);
[Thermo PCR troubleshooting](https://www.thermofisher.com/us/en/home/life-science/cloning/cloning-learning-center/invitrogen-school-of-molecular-biology/pcr-education/pcr-reagents-enzymes/pcr-troubleshooting.html);
[Promega restriction enzyme resource](https://www.promega.com/resources/guides/nucleic-acid-analysis/restriction-enzyme-resource/);
[Promega GoTaq technical bulletin](https://worldwide.promega.com/-/media/files/resources/protocols/technical-bulletins/0/gotaq-pcr-core-systems-protocol.pdf).

*Fixtures.* Fires: buffer, enzyme, plasmid, water (the `clone-01` order). Fires:
buffer mix, polymerase, primers, water, template. Near miss: water, buffer, plasmid,
enzyme. Near miss: a master mix made in a tube (water, buffer, enzyme) then handed
out. Near miss: an enzyme into a well that already holds 12 µl of water.

### N8 `MIX-TOO-WEAK`

*Checkable.* At every mix (a `mix` call, or `mix_before` / `mix_after`, or by hand: an
aspirate whose liquid goes straight back into the same well), the stroke volume
against the well's volume at that moment, and the number of strokes. Warning when the
stroke is under 50% of the well, or there are fewer than 3 strokes, or the stroke is
the whole well or more (the tip draws air at the bottom and foams). Once per line.
Silent for a well of unknown volume.

*Numbers.* Integra: "aspirating and dispensing >80 % of the total ... volume, repeated
5 times"; Beckman: "Mix with a tip volume just slightly below the total well volume";
"3 mixes yielded 11.8% CV while 20 mixes yielded 1.7% CV"; "800uL is not going to be
anywhere close to be able to mix 20mL of sample, regardless of the number of mixing
cycles". The 50% and 3 are decisions below the vendors' 80% and 5, so that the rule
does not flood.

*Source.* [Integra, three serial-dilution protocols](https://www.integra-biosciences.com/global/en/applications/3-simple-and-proven-automation-protocols-serial-dilutions-assist-plus-pipetting-robot);
[Beckman AMPure XP instructions](https://research.fredhutch.org/content/dam/research/hahn/methods/Agencourt%20AMPure%20XP.pdf);
[Esca Automation, serial dilution](https://escaautomation.substack.com/p/serial-dilution-a-classic-technique);
[labautomation.io 3654, how to mix a bacteria sample](https://labautomation.io/t/how-to-mix-bacteria-sample-enough/3654).

*Fixtures.* Fires: `mix_after=(2, 10)` in a 505 µl deep well. Fires: `mix(3, 20)` in a
20 µl well. Near miss: `mix(5, 150)` in 200 µl. Near miss: `mix(3, 80)` in 100 µl.
Near miss: a mix in an undeclared well of unknown volume.

### N9 to N25, briefly

* **N9 `BEAD-CLEANUP-STEPS`.** Opentrons: "The recommended attraction time is 5
  minutes for liquid volumes up to 50 µL and 7 minutes for volumes greater than 50 µL"
  ([Magnetic Module](https://docs.opentrons.com/v2/modules/magnetic_module.html)).
  Beckman: 2 minutes on the magnet, "Wait for the solution to clear", "Leave 5 μL of
  supernatant behind", two washes of 200 µl 70% ethanol for 30 seconds, "do not over
  dry", 40 µl elution mixed 10 times for 2 minutes
  ([AMPure XP](https://research.fredhutch.org/content/dam/research/hahn/methods/Agencourt%20AMPure%20XP.pdf)).
  NEB: "at least 5 minutes", 80% ethanol "freshly prepared", "Air dry the beads for up
  to 5 minutes ... Do not overdry", elute at least 2 minutes and transfer less than the
  eluate ([NEBNext Ultra II](https://www.neb.com/-/media/nebus/files/manuals/manuale7645.pdf)).
  Where the sources disagree (dry time: Illumina's 2011 guide says at least 15
  minutes, its current pages say up to 5) the rule checks for a dry step, not its
  length. Practitioners: "manual ... yields 10-30% more DNA ... compared to the
  robot"; "Try to elute for 5 min, 1 min seems to be rather short"
  ([labautomation.io 3525](https://labautomation.io/t/manual-vs-automated-dna-clean-up-with-magnetic-beads/3525)).
  Fixtures: supernatant removed 30 s after engage (fires); one ethanol wash (fires);
  whole 17 µl eluate moved (fires); the AMPure sequence as written (near miss); a wash
  with the magnet off followed by a mix, which is a resuspension (near miss).
* **N10 `COMPONENT-FRACTION`.** Enzyme over 10% of a digest, so glycerol over 5%
  ([Thermo](https://www.thermofisher.com/us/en/home/technical-resources/technical-reference-library/cloning-technical-support-center/restriction-cloning/restriction-enzyme-cloning-troubleshooting.html),
  [Promega](https://www.promega.com/resources/pubhub/enotes/what-can-i-do-to-prevent-star-activity-in-my-restriction-enzyme-digestions/)
  "many have normal specificity at glycerol concentrations as high as 10%"); DNA over
  25% of a digest (Thermo); template up to 40% of a PCR, undiluted cDNA no more than
  10% of a qPCR ([Qiagen, Critical factors](https://www.gene-quantification.de/qiagen-qpcr-sample-assay-tech-guide-2010.pdf)),
  or 20% (Thermo real-time troubleshooting); an RT reaction no more than 50 µl. Fixtures:
  3 µl of enzyme in a 20 µl digest (fires); 5 µl of cDNA in 20 µl of qPCR (fires); 1 µl
  in 20 (near miss).
* **N11 `NO-MASTER-MIX`.** "Accurate dispensing of submicroliter (<1µl) volumes of
  enzyme solutions in 50% glycerol is nearly impossible. We strongly recommend the use
  of reaction master mixes" ([Promega GoTaq](https://worldwide.promega.com/-/media/files/resources/protocols/technical-bulletins/0/gotaq-pcr-core-systems-protocol.pdf));
  "prepare master mixes for replicate reactions whenever possible ... include 10%
  overage" ([Bio-Rad](https://www.bio-rad.com/webroot/web/pdf/lsr/literature/Bulletin_5279.pdf),
  [PowerTrack](https://documents.thermofisher.com/TFS-Assets/LSG/manuals/MAN0018825_PowerTrackSYBRGreenMasterMix_UG.pdf));
  the WHO row already in `rule-sources.md`. The request `pcr-07` asks for 0.5 µl of
  polymerase per reaction, so this is advice to the person, not a defect: note.
* **N12 `SUSPENSION-SETTLED`.** "the bacteria cells settle down to the bottom"
  ([labautomation.io 3654](https://labautomation.io/t/how-to-mix-bacteria-sample-enough/3654));
  "resuspend the cells well before dispensing them" ([Thermo, primary cell culture troubleshooting](https://www.thermofisher.com/us/en/home/technical-resources/technical-reference-library/cell-culture-support-center/primary-cell-culture-support/primary-cell-culture-support-troubleshooting.html));
  beads "Shake the reagent well before use" (Beckman), "vortex the beads until they are
  well dispersed" ([Illumina TruSeq best practices](https://support.illumina.com/content/dam/illumina-support/documents/documentation/chemistry_documentation/samplepreps_truseq/TruSeq_SamplePrep_Best_Practices_Guide_15025666_A.pdf)).
  No source gives the minutes; we decide (5 minutes is what a bench protocol
  would say).
* **N13 `TIP-RACK-MISMATCH`.** The pipette definitions list the racks each pipette
  accepts (`defaultTipracks`: the P20 GEN2 lists the 10 and 20 µl racks only); Opentrons:
  "Do not use tips with a higher capacity than the pipette maximum volume"
  ([pipette characteristics](https://docs.opentrons.com/v2/pipettes/characteristics.html)).
  Measured: the simulator passed a P20 with a 300 µl rack (a Super draft).
* **N14 `REPLICATES`.** "We recommend running all samples in triplicate"
  ([Bio-Rad](https://www.bio-rad.com/webroot/web/pdf/lsr/literature/Bulletin_5279.pdf));
  "Four replicates of each reaction are recommended" (PowerTrack); ELISA "in duplicate
  or triplicate" ([Thermo TR0065](https://documents.thermofisher.com/TFS-Assets/LSG/Application-Notes/TR0065-ELISA-guide.pdf));
  MIQE: "Number and stage ... of technical replicates — E". A plate-map statement.
* **N15 `BLOW-OUT-INTO-STOCK`.** A hard-coded blow-out was the cause of NTC
  contamination in a clinical lab ([labautomation.io 7281](https://labautomation.io/t/liquid-handling-proof-of-no-contamination/7281));
  Opentrons documents `blowout_location="source well"` and that the default location
  "will shift away from the trash" when the tip already holds liquid
  ([complex command parameters](https://docs.opentrons.com/v2/complex_commands/parameters.html));
  Eppendorf: "Be careful not to bring air bubbles into the sample when performing a
  blow-out at the liquid surface" ([Eppendorf FAQ](https://www.eppendorf.com/us-en/lab-academy/life-science/microbiology/liquid-handling-faq/)).
* **N16 `TIME-SPREAD`.** "potential time gradients between the first and last sample
  can skew the results" ([Eppendorf white paper 35](https://www.eppendorf.com/product-media/doc/en/192416/Liquid-Handling_White-Paper_035_Multipette-E3-E3x_Xplorer-plus_epMotion-96_Five-Challenges-Plate-Assays-Be-Mastered-Right-Choice-Pipetting-Tool.pdf)).
* **N17 `VOLATILE-OR-VISCOUS`.** Opentrons' own liquid classes give the numbers: a
  viscous liquid retracts at 4 to 10 mm/s with a delay after aspirating, a volatile one
  takes an air gap of up to 12 µl ([liquid class definitions](https://docs.opentrons.com/python-api/liquid-classes/definitions/));
  Eppendorf: pre-wet 3 times for 70% ethanol, 5 to 8 times above
  ([Eppendorf, volatile liquids](https://www.eppendorf.com/us-en/lab-academy/life-science/cell-biology/how-to-stop-dripping-when-pipetting-volatile-liquids));
  Tecan: 50% glycerol at 10 µl/s with a 500 to 2000 ms delay
  ([Tecan, viscous liquids](https://www.tecan.com/knowledge-portal/troubleshooting-pipetting-viscous-liquids));
  Opentrons' app note measured drops and dead volume at default speeds
  ([Viscous liquid handling on the OT-2](https://insights.opentrons.com/hubfs/Applications/General%20liquid%20handling/Viscous%20Liquid%20Handling%20App%20Note.pdf)).
* **N18 `THERMOCYCLER-LID`.** "Temperature profiles only control the temperature of
  the block ... You should set a lid temperature before executing the profile"
  ([Opentrons, Thermocycler](https://docs.opentrons.com/v2/modules/thermocycler.html)).
* **N19 `PRE-WET-AND-FIRST-ALIQUOT`.** "It is common for the first and/or last
  dispense to transfer slightly different volumes" (Artel); "the common practice has
  been to pipette Master mixes without pre-wetting" ([Sartorius, qPCR master mix](https://www.sartorius.com/download/846530/pipette-pcr-in-qpcr-results-application-note-en-l-sartorius-1--data.pdf));
  Hamilton: "it is recommended to pre-wet the tip prior to or during the first
  aspiration" ([labautomation.io 1874](https://labautomation.io/t/mixing-and-bubbles-pre-wetting-tip-in-serum-and-associated-problems/1874));
  Integra: "discard the first and the last aliquot when repeat dispensing"
  ([Integra, pipetting tips](https://www.integra-biosciences.com/united-states/en/pipetting-tips)).
* **N20 `CLOSER-PIPETTE-LOADED`.** "choose a pipette with a nominal volume ... that is
  closest to the volume to be pipetted" ([Sartorius application guide](https://www.sartorius.com/resource/blob/1085646/d4bf11ef41cbbc9c7ebdcc88ecea4846/how-to-pipette-challenging-liquids-application-guide-en-l-sa-1--data.pdf)).
* **N21 `ENZYME-TIME-AT-AMBIENT`.** Restriction enzymes: "23 different restriction
  enzymes held at room temperature for one week ... all enzymes retained significant
  activity" ([Clark et al. 2000](https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:10997268));
  an assembled SYBR plate: "up to 8 hours" ([PowerTrack](https://documents.thermofisher.com/TFS-Assets/LSG/manuals/MAN0018825_PowerTrackSYBRGreenMasterMix_UG.pdf))
  or 72 hours ([PowerUp](https://www.thermofisher.com/us/en/home/life-science/pcr/real-time-pcr/reagents-kits/sybr-green-master-mixes/powerup.html));
  T4 ligase "temperature-sensitive" above 37 °C with no hours given
  ([Thermo, optimize your ligation](https://www.thermofisher.com/us/en/home/brands/thermo-scientific/molecular-biology/molecular-biology-learning-center/molecular-biology-resource-library/spotlight-articles/optimize-dna-ligase.html));
  hot-start Taq is "completely inactive at room temperature"
  ([Thermo-Start Taq](https://documents.thermofisher.com/TFS-Assets/LSG/manuals/MAN0013315_ThermoStart_TaqDNAPolymerase_AB0908_UG.pdf)).
  The numbers say a run of an hour is safe for every enzyme a source covers; this
  family stays low until a source gives hours for ligase or a reverse transcriptase.
* **N22 `SHAKER-TOO-FAST`.** "I've only truly seen issues when the rcf gets above
  ~20xg" ([labautomation.io 6666](https://labautomation.io/t/orbital-shaking-and-cross-contamination/6666)).
* **N23 `HOT-NEIGHBOUR`.** "All 3 false positives were adjacent to true positives
  with N1 and N2 Cq values ≤18" ([Hampel et al. 2024](https://academic.oup.com/jalm/article/9/4/716/7632639)).
* **N24 `OPEN-PLATE-DELAY`.** "over 8% observed with a standard 96-well plate" in
  seven days ([Lab News](https://www.labnews.co.uk/article/2028052/beating_the_edge_effect));
  outer wells "35% lower metabolic activity" ([Mansoury et al. 2021](https://pmc.ncbi.nlm.nih.gov/articles/PMC8024881/));
  Thermo's edge-effect note and the 36-perimeter-well practice
  ([Thermo COL31874](https://documents.thermofisher.com/TFS-Assets/LCD/Application-Notes/COL31874-EDGE-App-Note.pdf)).
* **N25 `MODULE-LEFT-ON`.** [Opentrons, Temperature Module](https://docs.opentrons.com/v2/modules/temperature_module.html).

### What the existing checks already cover, that the sources asked for

Several warnings in the sources are met by construction and need no rule. Provette
replays the simulator's own primitives, so a `mix_after` that `distribute()` ignores,
a `blowout_location` that is dropped without `blow_out=True`, and the disposal volume
`distribute()` takes on every refill are seen as what actually happened, not as what
the author wrote ([Opentrons, complex command parameters](https://docs.opentrons.com/v2/complex_commands/parameters.html)).
`new_tip="always"` on a `distribute()` still uses one tip for every source, and that
is `CONTAM-STOCK`. A loop that puts every volume into every well, the one published
wrong-well bug in the Opentrons library's issues
([Opentrons/Protocols 2070](https://github.com/Opentrons/Protocols/issues/2070)), is a
plate-map mismatch. Index cross-contamination between pooled libraries is
`CONTAM-STOCK` with the library as a sample.

## What a script cannot show: physics

Every report says the checker checks the logic and not the physics. This is the
physics, as the sources describe it, so the sentence has content.

| effect | who says so | why the script cannot show it |
|---|---|---|
| The volume actually delivered: a drop hanging on a 20 µl tip that "represents about half the volume inside the pipette"; 2 to 3 µl left in the corners of a well; −27.85% at 2 µl on an untuned Biomek | [Justen](https://www.lennijusten.com/blog/serial-dilution/), [labautomation.io 6684](https://labautomation.io/t/aspirating-all-most-liquid-from-96-well-plate-wells-opentrons-flex/6684), [Artel on a Biomek](https://www.bioprocessonline.com/doc/optimizing-accuracy-performance-on-a-beckman-coulter-biomek-using-the-artel-mvs-0001) | needs a balance or a dye; the script gives the requested volume |
| Films, foam and bubbles: detergents that "stick to the inside of a pipet tip", protein that foams at blow-out, a master mix with over 10% CV at 13.5 µl | [Eppendorf FAQ](https://www.eppendorf.com/us-en/lab-academy/life-science/microbiology/liquid-handling-faq/), [labautomation.io 2117](https://labautomation.io/t/difficulties-optimizing-aliquoting-pcr-master-mix/2117) | a pressure curve or a camera; the script can only show an absent delay or air gap |
| Drips in transit: "droplets fall from pipette tips onto the deck", volatile liquids that expand the air cushion | [Artel](https://www.bioprocessintl.com/assays/automated-liquid-handlers-as-sources-of-error), [Eppendorf](https://www.eppendorf.com/us-en/lab-academy/life-science/cell-biology/how-to-stop-dripping-when-pipetting-volatile-liquids) | vapour pressure and temperature; the precondition (no air gap) is row 23 |
| Splash and aerosol: a blow-out that sprayed a plate; droplets thrown between wells above about 20 g of shaking | [labautomation.io 7281](https://labautomation.io/t/liquid-handling-proof-of-no-contamination/7281), [6666](https://labautomation.io/t/orbital-shaking-and-cross-contamination/6666) | the event is visible (rows 21, 28); the spray is not |
| Whether a mix homogenised the well; whether beads clumped "over 6-8h of handling" | [Artel](https://www.bioprocessintl.com/assays/automated-liquid-handlers-as-sources-of-error), [labautomation.io 270](https://labautomation.io/t/streptavidin-magnetic-bead-handling/270) | the replay knows the strokes and the clock, not the result |
| The tip touching a cell pellet or a coated surface; a magnet up to 1 mm off | [labautomation.io 4326](https://labautomation.io/t/washing-cells-without-disturbing-pellet/4326), [Opentrons Magnetic Module](https://docs.opentrons.com/v2/modules/magnetic_module.html) | manufacturing variance and the position of a pellet |
| Evaporation and the edge effect: the numbers are for days in an incubator, none for an hour on a deck | [Lab News](https://www.labnews.co.uk/article/2028052/beating_the_edge_effect), [Mansoury 2021](https://pmc.ncbi.nlm.nih.gov/articles/PMC8024881/), [Hambidge 2026](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC13261617/fullTextXML) | humidity, lid, airflow; the replay gives only elapsed open time |
| Carry-over that happens even with a clean protocol: 0.470% index hopping, residue on standard tips, aerosol in a pipette cone | [van der Valk 2020](https://www.biorxiv.org/content/10.1101/179028v3.full), [Shakeri 2022](https://www.nature.com/articles/s41598-022-18756-x), [Eppendorf FAQ](https://www.eppendorf.com/us-en/lab-academy/life-science/microbiology/liquid-handling-faq/) | chemistry of the plastic and the sequencer; the replay covers only tip paths |
| Hardware: clots, a tip not picked up, worn seals under-dispensing 2 to 6 µl of 10, a flow rate the firmware ignored, a tube that holds 4.2 ml not 5.3 | [Tecan Cavro](https://www.tecan.com/blog/cavro-adp-detect-bringing-a-sixth-sense-to-pipetting), [labautomation.io 2933](https://labautomation.io/t/checking-dispensing-volume/2933), [6694](https://labautomation.io/t/controlling-flow-rate-when-aspirating-by-meniscus/6694), [4393](https://labautomation.io/t/venus-insufficient-liquid-error/4393) | the simulator models none of these |
| Every ISO 8655 statement: a pipette is adjusted for water at 20 °C and nothing else without adjustment | [ISO 8655-2:2022](https://cdn.standards.iteh.ai/samples/68797/22112a5d4edc44e8b371f0d3db6ef112/ISO-8655-2-2022.pdf) | a calibration property |

The practitioners' deepest objection to AI-written methods is this list
(`pain-points.md`). The sentence in every report, "it checks the logic, not the
physics", now has a table behind it.

## What we looked for and could not find

Each of these needs a source before it can be a number in a rule.

* **Hours at room temperature for T4 DNA ligase, Taq, a reverse transcriptase or an
  RNase inhibitor.** Every vendor page says "keep on ice"; Youngblom 2003 (BioTechniques
  34:264) is the paper that measured it and could not be opened by any route; NEB's
  FAQ pages return 403. What exists: restriction enzymes a week (Clark 2000), an
  assembled SYBR plate 8 to 72 hours (Thermo), one reverse transcriptase a week
  (Bioline, vendor).
* **A per-hour evaporation rate for an open plate at room temperature.** Only 7-day
  incubator numbers and vial headspace numbers.
* **How many minutes cells or beads take to settle in a tube** before a dispense series
  becomes uneven. Only "immediately" and "resuspend before use".
* **A measured carry-over fraction per reused disposable tip** on an OT-2 class
  machine. The nearest: 2.3 to 5.3% of adjacent wells on a Bravo checkerboard.
* **A rate of wrong-well placement during manual setup in a research lab.** Only
  clinical mislabel rates and transcriptomics misannotation.
* **An omission rate for NTC or no-RT controls in published qPCR.** Bustin says
  "patchy" and gives no number.
* **A per-category count of errors in LLM-written Opentrons code.** ProtoPilot, ABC-Bench
  and PRISM give pass rates and name the classes; none counts them.
* **An ELISA "do not let the plate dry" threshold in minutes**, and a "plate not sealed"
  primitive: sealing is a human step the script cannot show.
* **The Opentrons dead-volume article** ("What are dead volumes, and how do I reduce
  them?"): the support centre is a JavaScript shell to every fetch. Integra's 260 µl in a
  standard reservoir and Hamilton's "add 2 mL" forum advice stand in.
* **Reddit** (r/labrats, r/Opentrons): blocked to every route tried. A person with a
  browser could cover it in ten minutes.
* **Hamilton's own guides** and **NEB's HTML pages**: Cloudflare. NEB's manuals as PDF
  were reachable and are what is cited.
* **Glycerol tolerance of PCR** (the 5 and 10% figures are all for digests); a **light
  exposure limit for SYBR mixes**; a **maximum digest time in hours** ("overnight" is
  the risk and 16 hours is an assay definition).

Filled since `rule-sources.md` was first written: how many minutes magnetic
beads take to settle (Opentrons: 5 and 7 minutes); a plain sentence to change tips
between samples ("Use individual pipette tips for all additions", Promega GoTaq;
"Change the tips for each sample", Illumina TruSeq); a room-temperature limit for
restriction enzymes (a week, Clark 2000).

## Specifications for the top eight

Written the way `provette/rules/README.md` asks: the rule in words (what happens, why
it matters to the experiment, what it does not fire on), the finding it produces, the
sources it cites (rows of `rule-sources.md`), the fixtures, and what it needs from the
state or the trace. No code. Every fixture is a protocol a student would recognise;
its first line says what it tests and whether it fires. Each rule is one root cause
per finding, grouped by the line that did it, as the existing rules are. The flood
test at the end of each is the number the builder should expect over the library and
the drafts; a rule that fires far above it is wrong, not the library.

Common to all eight: `facts_of(trace, run)` gives moves, strokes, draws, stocks and
roles; `run.well_before(well, i)` gives a well's volume and atoms before event *i*;
`trace.deck.labware[...].wells[name]` gives `max_volume_ul`, `depth_mm` and the
cross-section; roles come from `facts.role(atom)` and are `None` for an undeclared
or unplaced name, in which case a role-tier rule is silent and says nothing.

### 1. `WELL-CAPACITY`

*Title.* A well was filled past what it can hold.

*In words.* Every well has a maximum, from its labware definition ("Total well, tube,
or tip volume in microliters"). The simulator does not check it: a protocol can put
200 µl into a 100 µl PCR well and pass. When a dispense takes a well over that maximum
the liquid runs over the rim, into the neighbouring wells and onto the deck, and what
the plate map then verifies is a plate that does not exist. When a well is at nine
tenths or more of its maximum and a mix stroke runs in it, the tip's own volume and
the air it pushes out spill it the same way. And when a `load_liquid` declares more
than the well can hold, the prep sheet asks the person for something they cannot do,
and the "would run dry" check is fooled by the declaration.

Three findings, one root cause each:

* **error**, `overflow`: the first event that takes a well's volume above
  `max_volume_ul`. The state already records the anomaly `overflow`, once per well,
  with `amount_ul` over the limit. Group by the line, list every well that line
  overflowed, with the peak volume and the maximum.
* **warning**, `brim`: a mix stroke (a `Move` in `facts.strokes`) in a well whose
  volume before the stroke is at 90% or more of the maximum, and which did not
  already overflow. Group by the mix's line.
* **note**, `declared`: a `LiquidLoad` whose `volume_ul` is above the well's
  `max_volume_ul`. Group by the load's line. The explanation says the declared
  volume, the maximum and that the prep sheet cannot be followed as written.

*What it does not fire on.* A labware whose label or load name contains "waste" or
"trash" (an overflowing waste trough is the library's normal). A well of unknown
volume (an implicit origin), because the state counts only what the robot net put in.
A well whose overflow the state inferred from an implicit origin's floor (the README
says that inference is no longer made; the rule should still read only the anomaly).
The brim warning does not fire for a mix whose stroke volume is under 10% of the well
(a 10 µl stroke in a 500 µl deep well spills nothing; that mix is `MIX-TOO-WEAK`'s).
Nothing fires for a custom labware definition whose maximum is 0 or missing.

*Certain.* Always: volumes are known exactly for every declared well and every well
the robot filled.

*Fix text.* "Use a plate whose wells hold at least N µl (the NEST 200 µl flat plate,
the Corning 360 µl plate, a deep-well plate), or lower the volumes so the well never
holds more than N µl." For the note: "Declare no more than N µl in this well, or move
the liquid to a tube."

*Sources.* Well capacity (the labware schema; labautomation.io 3683; LabOP).

*Fixtures.*

```
fires_dilution_series_overflows_pcr_plate.py    # FIRES, error: 1:2 series, 200 ul in a 100 ul PCR plate at every step
fires_standards_at_the_brim_while_mixing.py     # FIRES, warning: 350 ul in a 360 ul Corning well, mixed with 150 ul strokes
fires_declared_500ul_in_200ul_flat_well.py      # FIRES, note: load_liquid(500) into nest_96_wellplate_200ul_flat
near_miss_same_series_in_200ul_plate.py         # does NOT fire: the same series in a 200 ul plate, peak 200
near_miss_deep_well_filled_to_1900_of_2000.py   # does NOT fire: 95% full, never mixed
near_miss_waste_trough_over_its_maximum.py      # does NOT fire: a labware labelled "liquid waste" overflows
```

*What it needs.* Nothing new. The overflow anomaly and `max_volume_ul` exist.

*Flood test.* Library: 134 of 787 traced protocols carry an overflow anomaly, 64 with
custom labware; read the ten worst by event count before trusting the rule (the
corpus notes say the definitions, not the protocols, are often wrong there). If the
error floods on custom definitions, downgrade to warning when the labware is custom.
Drafts: 1 error (a Super draft), 4 brim warnings, 7 notes, of 59.

*Library flood test, on the built rule.*
The checker was run over all 833 library protocols (787 check, 45 fail to trace, 1
times out) and the rule fires on 134: 123 with an error, 17 with a warning, 1 with a
note. Every one of the 134 was then replayed and each overflowing labware classified
against two numbers: the definition's stated maximum, and the **brim** of the well
computed from the definition's own inner geometry (the sum of its conical, spherical
and cuboidal sections). The ten worst by event count were read line by line.

The fact that decides it: **the stated maximum is the maker's working volume, not the
rim.** By its own geometry the NEST "100 µl" PCR plate holds about 217 µl to the rim,
the Bio-Rad "200 µl" PCR plate 231, the NEST "200 µl" flat plate 368, the Corning
"360 µl" plate 366, the generic PCR strips 332, the NEST 1.5 ml tube 1898, the 2 ml deep
well 2260. So "over the stated maximum" and "over the brim" are two different things,
and the library shows both.

| class of the worst labware in the protocol | protocols | what it is |
|---|---|---|
| stock labware, over the stated maximum but under the brim | 62 | 130 to 200 µl of wash or beads in a NEST 100 µl PCR plate, mostly bead cleanups (`0ba998-4` is Illumina's own DNA-prep cleanup at 130 µl; `5c7384` and `5c7384-hhu` the SP3 proteomics manual at up to 200; `14b685`, `49de51-pt2`, `onsite-ganda-4` at 170 to 180); 216 µl in a Bio-Rad 200 µl plate (`pcr_prep_part_2`); a few tubes and reservoirs. Over what the maker rates, under what the plastic holds: a warning, not an error |
| custom labware definition, no inner geometry | 37 | `74312c` a PCB board rated 2 µl a well, filled with 10; `7f0f89` a 216-well cartridge rated 85 µl, filled to 160; `0e7175-pt2` and `2cc59d` Greiner and Costar ELISA plates rated 200 µl, filled to 250 to 300 (those plates hold about 350); `1adec6-7` a ProcartaPlex plate rated 340 µl at 475 with twelve pauses for off-robot washes; `43d313-part-2` a twin.tec plate at 200.4 of 200 (rounding). The rated number is nominal in every one read: the definition is the author's guess, not the plastic |
| stock labware, within 1% of the stated maximum | 10 | 15,021 to 15,140 µl into a 15 ml reservoir channel used as a sink (`5f791f` "reagent reservoir", `295c73`, `6030b7`): arithmetic, not a spill |
| waste-labelled | 11 | already exempt by the rule's label words; the replay still records them |
| stock labware, over the brim | 7 | **real, six of them**: 250 µl of reagent onto 250 µl of sample in a Corning 360 µl plate (`1dbc24`, `3e3c9d-protocols-adding-wistd-water`, peak 500); Illumina's Nextera Flex cleanup moving 125 µl into a Bio-Rad PCR well already holding 145 (`nextera-flex-library-prep-cleanup-libraries`, 270); 300 µl and 340 µl into Bio-Rad PCR wells (`04f4e7`, `0e525c`); a crystallisation screen at 2900 µl in a 2.4 ml deep well (`38efd4`). The seventh, `0ff0c3`, is a 195 ml reservoir used as the trash under a variable called `trash`, 53 µl over: a sink with no waste word in its label |
| stock labware, no inner geometry | 7 | the NEST 100 µl plate on the aluminium block adapter (`opentrons_96_aluminumblock_nest_wellplate_100ul`, 110 to 200 µl), one 22 ml reservoir, one flat-bottom adapter: the adapter definitions carry no geometry, the plate they hold does |

Of the 134, 38 have a custom definition for the overflowing well; the other 96 are stock.
The seven over the brim are all stock labware. No custom-labware case can be judged
against a brim, because no shipped custom definition in these 134 carries inner
geometry.

*What this says about the severity.* As built, the error fires on 123 library
protocols and six of them spill. The answer to the question asked (should the error
drop to a warning on custom labware) is yes, and the same for stock labware between
the stated maximum and the brim:

* **error** only when the well's volume is over its brim, computed from the definition's
  inner geometry; that needs the geometry in the trace, the same addition
  `SOURCE-TOO-SHALLOW` needs (`WellGeometry.brim_ul`, computed at trace time). On the
  library that is 6 protocols, every one read as real.
* **warning** when the volume is over the stated maximum but the brim is unknown
  (every custom definition without geometry: 37) or not reached (62), with the
  explanation saying both numbers: "N µl in a well the maker rates at 100 µl; the
  plastic holds about 217 µl to the rim, and a mix or a seal will spill it". The
  existing brim-while-mixing warning then does its work at 90% of the *brim*, not of
  the stated maximum.
* **silent** within 1% or 1 µl of the maximum (rounding, and 13 reservoir sinks), and
  for a well that is only ever dispensed into and never drawn from in a reservoir or
  tube labware (a sink: `0ff0c3`'s `trash`, `5f791f`'s "reagent reservoir"), whatever
  its label. The label words stay as a second exemption.

On the drafts this moves Super's `dil-01` from error to warning (200 µl in the
NEST 100 µl plate is under its 217 µl brim), and the brim-while-mixing warning still
fires on it (200 of 217 with 150 µl strokes); the two other warnings and seven notes
stand. Until the trace carries the geometry, the honest interim is the warning for
every over-maximum case with the stated number in the text, and no error at all: an
error that is wrong 117 times in 123 on the public library would be read as noise.

*Verdicts on the rerun audit (main at 2e80a64, the rim rule as built).* The audit under
the eleven map-free rules fires past the rim in 27 protocols (37 findings), not the 7 the
first read predicted: that read used hand sums, and the rule reads the well's history.
Every one of the 27 was replayed on `main` and the error well's volume history printed
from the state, event by event, before the verdict. The lesson is the one the leading
session drew from `0ba998-4` (130 → 145 → 270 → 300 in a NEST 100 µl well): the hand
numbers were low, and the rule's numbers stand.

| verdict | n | protocols, with the peak the state reaches |
|---|---|---|
| **real, by the protocol's own arithmetic**; the state and the rim both right | 14 | `04f4e7` 300 µl and `0e525c` 340 µl into Bio-Rad PCR wells (rim 231); `1dbc24` and `3e3c9d-protocols-adding-wistd-water` 500 µl into Corning 360 wells (rim 366); `nextera-flex-library-prep-cleanup-libraries` 270 into a Bio-Rad PCR well; `0ba998-4` 300 into a NEST 100 µl well (rim 217); `38efd4` 3,400 µl into a 2.4 ml deep well (rim 2,442); `08878b` 275 into a Bio-Rad PCR well; `21e4d8-pt3` 300 into a NEST 100 µl well used as a pool; `4ee4d6-part2` 237 into a NEST 100 µl well on the magnet; `2bdff3` 2,560 µl pooled into a 1.5 ml tube (rim 1,898); `gna_octea` 360 into a Bio-Rad PCR well; `51df08` 503 into a 330 µl slide well filled twice before it is emptied; and `1fcf02`, the best find of the read: `p300.blow_out()` with no location after a 27 µl dispense from a 300 µl aspirate, so the other 273 µl go into a 138 µl 384-well (rim 166). The state is right about that: a blow-out is a dispense of what the tip holds, where the tip is |
| **real by the file as shipped**, but the volumes are the library's default parameters, which put deep-well volumes in the wrong plate | 7 | `0aee8a` (the IC-50 series: 1,760 to 20,240 µl into NEST 100 µl PCR wells, the plate being a parameter); `1ef67e` (95 ml of diluent built in a 15 ml tube); `226d24` (40.6 ml of master mix pooled into one 15 ml reservoir channel); `058124` (3,200 µl in a 2 ml deep well); `06e5b6` (1,170 µl in a 140 µl crystallisation reservoir and 12 µl in a 3.9 µl drop well); `00a577` (750 µl of elution into a NEST 100 µl well, the same wells hit three times); `063611` (1,250 µl into a custom cap rated 1,000). The rule is right about the file; whether anyone runs the defaults is the audit README's caveat 1 |
| **emptied off the robot**: a filter plate drained by vacuum or a bead plate washed on a plate washer, in a step the script cannot show; the state is right about what the robot poured | 4 | `089108` (a miniprep filter plate, 2,680 µl over 1,215), `0f5c31` (a Pall 350 µl filter plate, 2,523), `1adec6-7` (a ProcartaPlex bead plate, 1,095, with twelve pauses), `0e7175-pt2` (a Luminex bead plate, 485) |
| **a sink the exemption misses** | 1 | `422b1e`: a custom beaker used as the titration waste, 12 ml into 11.5, only ever dispensed into, named `custom_beaker` with neither "waste" nor a sink word |
| **the definition is not a well** | 1 | `6a77d9`: 1,280 µl deposited onto a "custom surface" whose definition says 20 µl and whose shape gives 8 |

So 21 of 27 are what the protocol as shipped would do, 14 of them at any parameter
setting. Two changes follow. Sinks should be recognised by use, not by name: a labware
that is only ever dispensed into and never drawn from is a sink whatever its load name
(`422b1e`), which also covers the reservoir-as-trash case in the first read. And a well
that overflows only across a `pause` (the four filter and washer plates all pause before
the next addition) could carry one sentence in the finding: "a pause comes before the
next addition; if the wells are emptied by hand there, nothing spills". The four are not
false alarms of the arithmetic, and the rule cannot know what a person does at a pause,
so that sentence is the honest form.

### 2. `SOURCE-TOO-SHALLOW`

*Title.* The pipette aspirated above the liquid.

*In words.* Opentrons aspirates 1 mm above the bottom of a well unless the protocol
says otherwise. Whether the tip is in the liquid depends on how deep the liquid is,
and that depends on the well's shape: 500 µl is 0.84 mm deep in a channel of the NEST
12-well reservoir, 2 ml is 0.26 mm in the 195 ml trough, 10 µl is 0.27 mm in a flat
96-well. A tip above the surface draws air, the destination gets nothing, and the
"would run dry" check does not notice because it counts microlitres, not millimetres:
Super's verified `pcr-03` draws its master mix 96 times from a puddle it cannot reach
while that check sees 86% used and says nothing. Practitioners call this the
commonest cause of a plate with empty wells, and vendors say to keep the tip 2 to 3
mm under the surface.

The finding: **error**, at the first aspirate whose tip height is above the liquid's
surface, in a well whose surface height is known. Group by the line; list every well
it drew air from, the depth of the liquid at that moment and the tip's height; count
the occurrences (the 96 draws are one finding). Say which destination wells got air
instead of liquid (the recipients of those draws, from `facts.recipients`).

*What it does not fire on.* An aspirate that belongs to an `air_gap`, or with the tip
at or above the well top (those are air on purpose; the state already says
`air_gap` and `tip_at_or_above_well_top`). A well of unknown volume (an implicit
origin). A draw of 0 µl. A well whose surface height is not known well enough: today
that is every well, because the state models a straight column and the true surface
in a conical or round-bottomed well is higher (state README, "one departure"). So the
rule fires only where the height is exact, and stays silent, not uncertain, elsewhere.

*Certain.* Always, when it fires: the rule fires only on an exact height.

*Fix text.* "Load at least N µl of {liquid} in {well} so the surface reaches the tip
(1 mm needs N µl in this well), or aspirate lower with `well.bottom(0.5)`, or move the
liquid to a narrower container (a 1.5 ml tube holds 500 µl 8 mm deep)."

*Sources.* Liquid height at the tip (Opentrons liquid control; Artel; Gilson; Integra's
dead volume; Eppendorf; labautomation.io 7592; Tecan).

*Fixtures.*

```
fires_master_mix_puddle_in_195ml_trough.py      # FIRES: 2 ml declared in nest_1_reservoir_195ml, 96 draws of 18 ul at the default height
fires_enzyme_500ul_in_12_channel_reservoir.py   # FIRES: 500 ul in a nest_12_reservoir_15ml channel, 12 draws of 1 ul at 1 mm
near_miss_same_mix_in_1_5ml_tube.py             # does NOT fire: 2 ml in a 15 ml conical tube (height not exact: silent)
near_miss_pbs_drawn_down_to_the_last_well.py    # does NOT fire: 1.2 ml in a channel, 12 draws of 100 ul; the twelfth is the prep sheet's flag
near_miss_reservoir_drawn_at_bottom_0_3.py      # does NOT fire: 500 ul in a channel drawn with well.bottom(0.3)
```

*What it needs.* Two additions to the trace contract, both from data the pinned
labware definitions already carry. (1) `WellGeometry.bottom_shape`: the definition's
`groups[].metadata.wellBottomShape` ("flat", "u", "v", or missing; 56 of 253
definitions are flat). (2) `WellGeometry.sections`: the definition's
`innerLabwareGeometry` for the well, a list of sections from the bottom up, each with
its shape (conical, spherical, cuboidal) and its dimensions, present in 123 of 253
definitions and in every plate, tube and reservoir the drafts use. Then a
`height_of(volume_ul)` on `WellGeometry` that integrates the sections when they exist
and falls back to the column when the bottom is flat; "known exactly" means one of
those two. The state's contact model uses the same function, which also removes the
`tip_above_column_height` unknown (row 6 of its table) for those wells. Until the
trace carries the sections, the rule may ship with the flat-bottom fallback only: the
two fires fixtures above are rectangular reservoirs whose definitions are cuboidal
sections with a flat floor, so they fire either way.

*Library and draft flood test, on the built rule.* The rule is silent on protocols that declare no liquids, so the library
flood is the 8 declared protocols that check (of the 11 that declare); it fires in 4:
`04bec0` (4 findings), `052d03` (6), `05fb0f` (2), `0be1bf` (3). Read line by line:

* **Real, by the declared volume:** `04bec0` distributes water with the tip hard-coded
  at `bottom(40)` of a 50 ml tube declared to hold 9.9 ml, and draws LDS at
  `bottom(50)` from 3.8 ml; its `mix(10, 60, d.bottom(5.5))` runs in a tube holding 40
  µl (a mixing stroke in air, which the rule words as one). `052d03` mixes and draws at
  5 to 7 mm in Bio-Rad PCR wells holding 20 µl (3.5 mm). `0be1bf` draws 15 µl at 3 mm
  from a tube holding 15 (1.9 mm). Eight of the fifteen findings.
* **A hand-written air gap the exclusion misses:** `052d03` line 322,
  `p20.aspirate(2, s.bottom(5))  # pre-airgap`, taken at 5 mm of a 14.6 mm well, below
  the "top half" line, immediately followed by the real draw from the same well with
  the same tip. One finding, a false alarm.
* **The prep sheet's flags, reported twice:** `05fb0f` declares 98 µl in a one-well
  reservoir and draws all 98, then 190 more; `0be1bf` draws 0.6 µl from a tube
  declared at 1 µl and 0.25 µl from one at 0 µl. The declaration is short, and the
  "would run dry" and "no margin" flags already say so; six findings.

Over the drafts the rule is clean: **7 of 64 final drafts and 13 of 102 drafts written without
the loop fire, every one read as a real air draw**, and none is a false alarm.
The shapes: 10 to 20 µl of libraries, samples or glycerol stocks declared in a flat
200 µl plate and drawn at 1 mm (0.16 to 0.63 mm deep: `pool-01` at every size,
`fill-01`, `prot-01`, `pcr-03` and `pcr-06` at Ultra); a reservoir declared at 2 ml
and drawn until the surface passes under the tip (`pcr-03`, `dil-01`, `pcr-06`,
`norm-01`: the 195 ml trough at 1.0 to 1.2 ml left, 0.82 to 0.90 mm); 184 µl of
water left in a 12-channel reservoir (0.87 mm). Three cases the hand read expected
are rightly silent: 500 and 300 µl in the 12-channel reservoir stand 1.69 and 1.22 mm
deep by the geometry, above the tip.

*Is the silence on undeclared protocols right?* Yes. A well the robot fills in a
protocol that declares nothing may have arrived holding sample (D-15), so its surface
is unknown and a finding would be a guess; the state already marks those contacts
uncertain. The cost is that the library cannot flood-test the rule, and 4 of 8
declared protocols is the whole sample; the model-written drafts, which all declare, are
the real test, and there the rule is exact. Two changes from the read: **exclude a
draw from a well holding less than the draw** (the prep sheet's flag, `05fb0f`,
`0be1bf`), and **treat an aspirate immediately followed by a liquid aspirate from the
same well with the same tip as an air gap by hand** at any height (`052d03`), instead
of the top-half line alone.

*Flood test.* Library: the state's `aspirate_above_liquid` anomaly is in 126 protocols,
most of them hand-written air gaps inside a well (`top(-2)`) and conical wells; with
exact heights and the exclusions above the rule should fire on a small fraction of
those. Read twenty. Drafts: 7 of 36 drafts by hand (the corpus notes name them:
a Super draft of `pcr-03`, `clone-01`; a Nano draft of `pcr-02`, `pcr-06`,
`pool-01`, and the end of `dil-01` and `norm-01`); three of those seven (500 µl and 300
µl in a 12-channel reservoir) were hand estimates from the channel's top cross-section
and are wrong: by the geometry they stand 1.69 and 1.22 mm deep, above the tip. The
built rule's own count is in the flood test below.

*Verdicts on the rerun audit (main at 2e80a64).* The rule fires in 4 of the 8 library
protocols that declare their liquids, 11 findings; each was replayed on `main` and the
contact record printed (tip height, surface height from the definition's shape, the
well's volume before the draw).

| verdict | n | findings |
|---|---|---|
| **real, by the protocol's own numbers**: the tip is above a surface the definition gives exactly | 8 | `04bec0` lines 115, 156, 158: water drawn at `bottom(40)` from a 50 ml tube holding 9.9 ml (26.4 mm), LDS at `bottom(50)` from 3.8 ml (15.3 mm), heights hard-coded for fuller tubes; `052d03` lines 275, 276, 323: an 8-channel P300 mixing and drawing at 5 mm in Bio-Rad PCR wells holding 20 µl (3.2 mm); `05fb0f` line 132: 98 µl declared in a one-well reservoir, 0.01 mm deep; `0be1bf` line 234: 15 µl drawn at 3 mm from a tube where it stands 2.1 mm (the author's own rule, 3 mm for anything over 10 µl) |
| **an air gap by hand the exclusion misses** | 1 | `052d03` line 322: `p20.aspirate(2, s.bottom(5))  # pre-airgap`, taken at 5 mm and followed at once by the real draw at the same height; the exclusion asks the following draw to reach the liquid, and here it does not either, so both fire. The first was meant to be air and says so |
| **the prep sheet's flag, said twice** | 2 | `0be1bf` lines 334 and 377: the last 0.6 µl and the last 0.25 µl of tubes declared at exactly what the run needs, drawn at 0.5 and 1 mm where they stand 0.28 and 0.18 mm. The exclusion covers a well holding *less* than the draw; these hold exactly the draw |

Two small changes follow: the last-draw exclusion should read "holds no more than the
draw asks for", and the hand-air-gap exclusion should accept a following draw from the
same well with the same tip whether or not that draw reaches the liquid, since the
first aspirate of the pair is the air gap either way. With those, 8 of 11 stand, all
real, and the rule is exact on every declared protocol in the library and every model-written
draft.

### 3. `COLD-MODULE-NEVER-SET`

*Title.* A temperature module was loaded but never set.

*In words.* A temperature module is at room temperature until the protocol calls
`set_temperature`, which waits until the module gets there. Authors load one because
the request said "on a cold block" or "at 4 °C", put the enzyme or the cells on it,
and forget the call; the robot then runs the whole protocol with the module off. The
person setting up the deck sees a module and assumes it is cold. Every enzyme
datasheet says set up on ice or on a cold block; a module that is loaded and never set
is the exact opposite of what the author meant.

Two findings:

* **warning**, `never_set`: a labware sits on a temperature module (its `Labware.module`
  names a temperature module), a liquid on it is aspirated or dispensed at event *i*,
  and no `set_temperature` event for that module precedes *i*. Group by the labware;
  the line is the first such aspirate or dispense; list the liquids on it by name and
  role. If a `set_temperature` comes later, say at which line, and that the liquids
  had already been used by then.
* **error**, `asked_and_absent`: the plate map (or, until the map carries it, the
  request text the map records) says a source is on a temperature module, a cold
  block, ice, or at a temperature at or below 10 °C, and either no temperature module
  is loaded or the one loaded is never set. The wells are the sources the map names.

*What it does not fire on.* A module set before the first use of anything on it, at
any temperature. A module with nothing on it, or with labware nobody touches. A
thermocycler (its block is set by a profile; that is `THERMOCYCLER-LID`'s). A
heater-shaker used only to shake (no liquid is meant to be held cold on it). A module
that is set after the last use of its labware, when nothing was drawn from or
dispensed into that labware before the call.

*Certain.* Always.

*Fix text.* "Call `temp_module.set_temperature(4)` before the first transfer from
{labware}, and `temp_module.deactivate()` at the end." For the error: "The request puts
{liquids} on a cold block; load a temperature module in a free slot, put {labware} on
it and set it to 4 °C before the first transfer."

*Sources.* Cold module (Opentrons temperature module); Thermal lability (Thermo,
NEB, Promega); Order of addition (NEB Q5 manual "on ice").

*Fixtures.*

```
fires_module_loaded_components_used_never_set.py   # FIRES, warning: 12 PCRs from components on a module that is never set
fires_request_says_4C_reagents_in_reservoir.py     # FIRES, error: plate map notes "on a temperature module at 4 C"; no module loaded (needs the map)
fires_set_after_the_enzyme_was_used.py             # FIRES, warning: set_temperature(4) called after all twelve digests are assembled
near_miss_set_to_4_before_first_transfer.py        # does NOT fire: set_temperature(4), then the transfers
near_miss_module_with_untouched_labware.py         # does NOT fire: a module and a block nobody pipettes from
near_miss_thermocycler_profile_only.py             # does NOT fire: a thermocycler with a profile and no temperature module
```

*What it needs.* Nothing new for the warning: `Labware.module` and `set_temperature`
events with `module` and `labware_id` are in the trace. For the error: a field on the
plate map, `sources: [{liquid, cold: true}]` or a temperature per source liquid,
which the planner fills from the request's words ("cold block", "on ice", "at 4 C",
"temperature module"). Until it exists, the error clause is not built and the
warning stands alone.

*Library flood test, on the built rule.* Over
the 787 library protocols that check, the rule fires in 63: 47 where the module is
never set, 16 where it is set only after liquids on it were used. The spec predicted
60 of 228. Eighteen of the 63 carry test-mode flags in the shipped file (`TEST_MODE_TEMP
= True` gates the `set_temperature` call), so the file as shipped runs warm and the
finding is right about the file, not about the author's bench. Ten were read:

| read as | n | which |
|---|---|---|
| never set, and the labware holds reagents or samples the author meant cold | 5 | `0d868e-part2` (TruSeq mRNA reagents on the module), `111210-part-8` and `111210-part-10` (QIAact cleanup reagent), `516336-part-2` (ONT ligation), `00f7b1_part8` (NEBNext; `TEST_MODE = False`, and still no setpoint) |
| never set, the module used as a plate holder | 2 | `019a7d_part_2` (two modules, one set to 4 then 42 °C, the other never, holding the 96-well destination), `43d313-part-7` ("Place a fresh 200 uL PCR plate on the temperature module": a stand) |
| test-mode default | 2 | `030dd8-synthesize`, `030dd8-amplify2` (`TEST_MODE_TEMP = True`) |
| set after use, and rightly so | 1 | `407d5e`: liquids assembled on the module at room temperature, then `set_temperature(37)` for the incubation. Twelve of the 16 "set after use" protocols set only a warm temperature afterwards |

*What this says.* The never-set clause is sound: 7 of 8 non-test cases read are a
module that was loaded for a reason and never set, and the two plate-holder cases are
still worth a warning (a person seeing a module assumes it is doing something). The
**set-after-use clause should fire only when the later setpoint is 10 °C or below**: a
warm setpoint after the liquids went on is an incubation the author planned, and it
is 12 of the 16. Test-mode flags cannot be seen by the rule and should not be; the
finding is correct for the file as it would run.

*Flood test.* Library: 60 of the 228 protocols that handle liquid on a temperature
module never set it, some through test-mode flags left on in the shipped file; read
ten and expect a mix of real omissions and modules used as plain holders. Drafts: 7 of 36
drafts (a Super draft of `pcr-04`, `pcr-07`, `fill-02`; a Nano draft of `clone-01`,
`fill-02`, `pcr-04`; a Super draft of `clone-01`).

### 4. `NO-NEGATIVE-CONTROL`

*Title.* No no-template control on a PCR plate.

*In words.* A PCR or qPCR plate needs one well with everything except the template:
if that well lights up, a reagent is contaminated or the primers dimerise, and every
other well's signal is in doubt. MIQE lists it as essential on every plate; every
master-mix manual says the same. A standard curve needs a blank (diluent only), and
an RT-qPCR plate a well without the reverse transcriptase. The evaluation requests never
ask for these, so the models never add them: 10 of 10 PCR and qPCR drafts had no NTC.
This rule is advice to the writer and the person approving the plate map, not a
defect against the map, so it is a note.

The plate is a PCR plate when a declared liquid is a reagent whose name or description
matches a mix word (`master mix`, `mastermix`, `mix`, `sybr`, `taq`, `polymerase`,
`qpcr`, `pcr`) and that liquid ends in bulk in at least four destination wells that
also hold a sample-role liquid in bulk.

Three findings, each a **note**, one per plate:

* `no_ntc`: no destination well ends holding the mix liquid in bulk and no
  sample-role liquid at all (a well with mix and water is an NTC; a well with mix
  alone is one too).
* `no_blank`: a sample-role liquid reaches at least four wells in amounts that fall by
  a constant factor (within 5%) from well to well, or the same liquid reaches wells at
  three or more distinct concentrations by dilution with a carrier, and no destination
  well ends holding only carrier-role liquid.
* `no_rt_control`: a reagent whose name or description contains `rt`, `reverse
  transcript` or `rtase` reaches the sample wells, and no well holds the same
  composition without it.

*What it does not fire on.* A plate map whose notes say controls are not wanted, or
that lists the controls' wells (then it is the map's job). A plate with fewer than
four reaction wells. Colony PCR into wells that receive the mix and a colony (a
sample): fires, because the convention holds. A plate where the mix is dispensed
first into the NTC well and the sample wells later: silent (the NTC exists). A
normalisation or a pooling (no mix-role liquid): silent. Any protocol that declares
no liquids: silent, `roles_basis: none`.

*Certain.* Always; `roles_basis: declared`.

*Fix text.* "Add one well (three for qPCR) with N µl of {mix} and M µl of water in
place of template, and tell the plate map where it is." For the blank: "Add a well of
{diluent} alone." For the RT: "Add one well per sample without {rt}."

*Sources.* PCR controls (MIQE 2009 and 2.0; Bustin 2025; Qiagen; Bio-Rad; Thermo
Maxima).

*Fixtures.*

```
fires_qpcr_six_samples_in_triplicate_no_ntc.py    # FIRES, note: 6 cDNAs x 3 with SYBR mix, 18 wells, nothing else
fires_bsa_standard_curve_no_blank.py              # FIRES, note: 8 points of BSA in water, no water-only well
near_miss_same_qpcr_with_one_ntc_well.py          # does NOT fire: the same plate plus one well of mix and water
near_miss_colony_pcr_with_mix_only_well.py        # does NOT fire: 16 colonies and a 17th well of mix alone
near_miss_normalisation_no_mix_liquid.py          # does NOT fire: 24 DNAs into water, no reagent
```

*What it needs.* Nothing new; the roles word lists gain the mix and RT words above
(we own them). A plate-map field `controls: none` or `controls: [wells]`
to silence it, when the planner learns to propose controls.

*Flood test.* Library: the rule needs declared liquids and only 11 protocols declare
any, so it will barely fire there; that is expected. Drafts: 14 of 36 drafts, all
Super's and Nano's PCR, qPCR, colony PCR and standard-curve drafts.

### 5. `LABWARE-FOR-TECHNIQUE`

*Title.* The wrong kind of plate for this technique.

*In words.* A PCR reaction assembled in a flat culture plate cannot go into a
thermocycler; an ELISA in a PCR plate cannot be coated or read; an enzyme in a 15 ml
reservoir is a millimetre of liquid at room temperature. Opentrons raises nothing:
"It's your responsibility to ensure the labware and module combinations you load
together work together." The plate map verifies what each well holds, not what plate
it is, so `select: auto` accepted a flat plate as the PCR plate in three of Super's
verified drafts. The request always says the technique, and the technique decides
the plate.

The technique comes from the request (`requests.jsonl` has `technique`; the plate
map should carry it as `technique`). The labware class comes from the load name:
`pcr` or `strip` or `aluminumblock_generic_pcr` (PCR); `flat` (flat plate); `deep`
(deep well); `reservoir` (trough); `tuberack` or `tube` (tubes); anything else is
unclassed and silent.

| technique word | destination must be | a source called "a tube" or "on ice" must not be |
|---|---|---|
| PCR setup, qPCR setup, Cloning, Transformation, Protein (gel samples) | PCR | reservoir |
| ELISA, Bradford assay, Cell assay, Cell culture | flat or deep | — |
| Serial dilution, Normalization, Pooling, Cherrypicking, Plate filling, Bead cleanup, Nucleic acid extraction | any | — |

The finding: **warning**, `wrong_destination`, once per destination labware: the
technique, the labware's display name and load name, and why (a flat plate does not
fit a thermocycler; a PCR plate is not coated). **note**, `reagent_in_trough`: a
reagent-role liquid (enzyme, polymerase, ligase, master mix) declared in a reservoir
when the request says "tube" or names a temperature; the line is the `load_liquid`.

*What it does not fire on.* A technique not in the table, or a plate map with no
technique. A destination the map calls the destination but which is only an
intermediate (the map's `destination` is the one it verifies; only that one is
checked). Custom labware whose load name says nothing. A reservoir holding a
carrier-role liquid (water, PBS, buffer: that is what troughs are for).

*Certain.* Always; `roles_basis: declared` for the note.

*Fix text.* "Load `nest_96_wellplate_100ul_pcr_full_skirt` (or the 200 µl PCR plate,
or strips on the aluminium block) as the destination; a flat plate cannot go in a
thermocycler." For the note: "Put {enzyme} in a tube on the block, not in a reservoir
channel: 500 µl in a channel is 0.8 mm deep and warm."

*Sources.* Labware for the technique (Opentrons module setup and thermocycler;
ABC-Bench).

*Fixtures.*

```
fires_colony_pcr_in_flat_plate.py               # FIRES, warning: technique PCR setup, destination nest_96_wellplate_200ul_flat
fires_elisa_in_pcr_plate.py                     # FIRES, warning: technique ELISA, 100 ul sera into nest_96_wellplate_100ul_pcr_full_skirt
fires_enzyme_declared_in_reservoir.py           # FIRES, note: technique Cloning, "enzyme" load_liquid in nest_12_reservoir_15ml, request says tubes at 4 C
near_miss_pcr_in_pcr_plate.py                   # does NOT fire: PCR setup into the NEST 100 ul PCR plate
near_miss_bradford_in_corning_flat.py           # does NOT fire: Bradford into corning_96_wellplate_360ul_flat
near_miss_cherrypick_any_plate.py               # does NOT fire: Cherrypicking, no plate class required
```

*What it needs.* `technique` on the plate map (copied from the request by the
planner), and the rule reads it from the map handed to `verify`; when `provette check`
runs without a map, the rule is silent. The technique-to-class table lives in the
rule module and we own it.

*Flood test.* Library: no technique field, so silent; the README categories could
stand in for a one-off measurement (129 PCR protocols) but that is not the rule. Drafts:
9 of 36 drafts (the corpus notes list them).

### 6. `UNMIXED-AT-END`

*Title.* A well was never mixed after its last addition.

*In words.* When a small volume is dropped into a larger one, the two sit in layers:
2 µl of template under 18 µl of master mix, 5 µl of loading dye on 15 µl of protein,
3 µl of DNA under 47 µl of water. Nothing in a small well mixes them on its own.
`MIX-BEFORE-DRAW` catches the case where the protocol draws from the layered well;
this rule catches the case where the protocol simply ends. For a PCR plate the
person may vortex and spin before cycling, so that is a note; for a normalisation, a
gel sample, a Bradford well or a pool, nothing else will ever mix it, and a
normalisation that is not mixed is not normalised: a warning.

The finding, one per root line: at the end of the run, a well that holds two or
more different liquids in bulk, whose last bulk arrival was a dispense of less than
30% of the well's volume after that dispense, with no mix stroke (`facts.strokes`)
in that well after that dispense, and with no draw from the well after it. Group by
the line of the last dispense; list the wells; say what was added on what.
**warning** when the last addition is a sample-role liquid, or the technique (from
the map) is Normalization, Protein, Bradford assay or Pooling; **note** otherwise.

*What it does not fire on.* A well drawn from after the addition (the other rule's).
A last addition of 30% or more of the well (it mixes on entry: the same reasoning as
`MIX-BEFORE-DRAW`'s whole-well threshold). A well that received the same liquid twice
(a top-up). A well of unknown volume. A well whose last addition was followed by a
`mix`, `mix_after`, or an aspirate-and-return with the same tip. A well where
everything ends in the trash or a waste labware. A dispense from above the liquid
does not count as mixing, and a `blow_out` into the well does not either.

*Certain.* Always.

*Fix text.* "Mix {well} after line N: `mix_after=(5, V)` on the transfer, or
`pipette.mix(5, V, well)`, with V about 80% of the well's volume."

*Sources.* Unmixed at the end (Artel; Illumina normalisation; Thermo PowerTrack);
Serial dilution mixing (Integra).

*Fixtures.*

```
fires_normalisation_dna_under_water_never_mixed.py   # FIRES, warning: 24 DNAs of 2 to 20 ul into 30 to 48 ul of water, run ends
fires_template_into_master_mix_no_mix.py             # FIRES, note: 2 ul of template on 18 ul of mix in 8 wells, run ends
fires_loading_dye_onto_protein_no_mix.py             # FIRES, warning: 5 ul of 4x dye on 15 ul of sample (technique Protein)
near_miss_same_normalisation_with_mix_after.py       # does NOT fire: mix_after=(5, 30) on the DNA transfer
near_miss_equal_volumes_layered.py                   # does NOT fire: 100 ul of buffer onto 100 ul of sample (50%)
near_miss_layered_then_drawn.py                      # does NOT fire: the well is drawn from later (MIX-BEFORE-DRAW's)
```

*What it needs.* Nothing new. The technique on the map (as in rule 5) raises the
severity; without it the sample-role clause alone decides.

*Flood test.* Library: no number was measured for this shape; run it and read twenty;
expect PCR set-ups to dominate at note level. If notes flood the agent loop, keep the
warning clause and drop the note, as `PIPETTE-RANGE`'s low tier was dropped. Drafts: 20 of
36 drafts, which is why the default is a note.

### 7. `ENZYME-BEFORE-DILUENT`

*Title.* An enzyme was added before the water.

*In words.* Enzymes are shipped in 50% glycerol and are meant to be the last thing
into a reaction, after the water and the buffer have made the well the right
dilution: "Ensure that the restriction enzyme is the final component added"; "Add
DNA polymerase last". An enzyme dropped into 2 µl of neat 10x buffer, or into a dry
well, meets ten times the salt it should, and restriction enzymes cut at the wrong
places (star activity) while polymerases start on mis-primed template. Every
`clone-01` and `pcr-07` draft from every model did this: buffer, enzyme, plasmid,
water.

The finding, one per root line: a destination well receives in bulk a liquid whose
role is *add last* (a reagent whose name or description matches `enzyme`,
`polymerase`, `taq`, `ligase`, `bsai`, `restriction`, `reverse transcript`, `rt`,
`master mix`, `mastermix`) at event *i*, and later receives in bulk a liquid whose
role is *add first* (a carrier whose name matches `water`, `h2o`, `buffer`,
`diluent`, `te`, `tris`, `medium`) at event *j > i*, where before *i* the well held
less than half of its final volume of add-first liquid. **warning**; group by the
line of the enzyme's dispense; list the wells and the diluent that came after.

*What it does not fire on.* An enzyme that is the last addition. An enzyme added to a
well that already holds at least half its final diluent (the water went in first,
the buffer after: fine). An enzyme that arrives inside a master mix already made in
another well (the arrival's source well is not the enzyme's origin). A master mix
that is itself the diluent (a 2x mix with primers: the request's mix is the bulk; if
a sample arrives after it, that is not this rule). A well whose final volume is
unknown. A protocol that declares no liquids: silent, `roles_basis: none`.

*Certain.* Always; `roles_basis: declared`.

*Fix text.* "Reorder the additions to {well}: water, buffer, {sample}, then {enzyme}
last; or make a master mix of water, buffer and enzyme in one tube and hand it out."

*Sources.* Order of addition (Thermo; Promega; NEB Q5 manual; Qiagen).

*Fixtures.*

```
fires_digest_buffer_enzyme_plasmid_water.py     # FIRES: 12 digests assembled as buffer, enzyme, plasmid, water
fires_pcr_polymerase_before_water.py            # FIRES: buffer mix, polymerase, primers, water, template
near_miss_water_buffer_plasmid_enzyme.py        # does NOT fire: the textbook order
near_miss_master_mix_made_then_shared.py        # does NOT fire: water, buffer, enzyme into one tube, then 12 aliquots plus plasmid
near_miss_enzyme_into_well_holding_water.py     # does NOT fire: 12 ul of water first, then buffer, plasmid, enzyme
```

*What it needs.* Two new lists in `roles.py`, *add last* and *add first*, drawn from
the existing reagent and carrier lists as above; we own them.

*Flood test.* Library: silent (undeclared liquids). Drafts: 8 of 36 drafts, six of them
`clone-01` and `pcr-07` at every size and condition.

### 8. `MIX-TOO-WEAK`

*Title.* Mixing too weak to stir well A1 in slot 3: 3 × 5 ul in 25 ul (the reason first, then
the numbers; "Too few strokes to mix …", "A mix stroke as big as the well …", "A pipette too
small to mix …").

*In words.* A mix is only a mix if the stroke moves most of the well: Integra's
serial-dilution protocols draw over 80% of the volume five times, Beckman says "a
tip volume just slightly below the total well volume", and a dairy lab found 800 µl
"not anywhere close" to mixing 20 ml however many times it cycled. Two strokes of
10 µl in a 505 µl deep well (`fill-01`, every model) mix nothing; a 20 µl stroke in a
20 µl well (`prot-01`) draws air from the bottom and foams the dye. Three mixes gave
11.8% CV where twenty gave 1.7%.

The finding, one per mix line: a run of mix strokes in one well by one tip
(consecutive `Move`s in `facts.strokes` with the same well and tip, uninterrupted by
any other move of that tip), where the well's volume before the first stroke is known
and any of: the stroke volume is under 50% of that volume; there are fewer than 3
strokes; the stroke volume is at or above 100% of that volume. **warning**; list the
wells, the stroke volume, the well volume and the count; say which of the three it
was.

*What it does not fire on.* A well of unknown volume. A stroke in a well that holds
only one liquid (a pre-wet of the tip in a reagent trough, which the library does
often with one stroke: `mix(1, 200, ethanol)`), unless the well later receives a
second liquid and no other mix follows. A stroke in a stock the protocol only draws
from (same reason: mixing a stock is resuspension, and the rule for beads and cells
is `SUSPENSION-SETTLED`). A stroke whose volume is capped by the pipette's maximum
when the well holds more than that maximum (a P300 cannot draw 80% of 500 µl; then
the test is 50% of the pipette's maximum and at least 3 strokes). Mixing by
`mix_before` in the source of a transfer is judged the same way as any stroke.

*Certain.* Always.

*Fix text.* "Mix {well} with about 80% of its volume (V µl) at least 5 times:
`mix(5, V, well)`. A stroke of the whole well draws air; use no more than 90%."

*Sources.* Serial dilution mixing (Integra; Beckman AMPure; Esca; labautomation.io
3654; Artel).

*Fixtures.*

```
fires_two_strokes_of_10ul_in_500ul_deep_well.py    # FIRES: LB plus 5 ul of stock, mix_after=(2, 10)
fires_whole_well_stroke_in_20ul.py                 # FIRES: mix(3, 20) in a 20 ul gel sample
fires_thirty_ul_strokes_in_200ul_series.py         # FIRES: mix(5, 30) at every step of a 1:2 series in 200 ul
near_miss_five_strokes_of_150_in_200.py            # does NOT fire: mix(5, 150) in 200 ul
fires_p20_three_strokes_in_505ul.py                # FIRES: mix_after=(3, 10) with a P20 in 505 ul: the pipette is under a fifth of the well
near_miss_three_strokes_of_80_in_100.py            # does NOT fire: mix(3, 80) in 100 ul, over the floor (work 2.4)
near_miss_ten_strokes_of_45_percent.py             # does NOT fire: mix(10, 100) in 220 ul, work 4.5: small strokes, many times
near_miss_prime_before_draw.py                     # does NOT fire: one stroke in a tube, then a draw from it with the same tip
near_miss_pre_wet_stroke_in_ethanol_trough.py      # does NOT fire: mix(1, 200) in the ethanol reservoir before a wash
near_miss_p300_in_a_full_deep_well.py              # does NOT fire: mix(5, 250) in 1.5 ml, capped by the pipette
```

*What it needs.* Nothing new. As built, the under-half clause is a mixing-work clause:
strokes times the share of the well each stroke moves must reach 2.0 (three strokes of
half the well is 1.5 and fires; three of 80% is 2.4 and does not, nor ten of 45% at
4.5); a pipette whose maximum is under
a fifth of the well fires whatever the count, with the fix naming the smallest OT-2
pipette that can mix it; and a single stroke followed at once by a draw from the same
well with the same tip is a prime, not judged. The 2.0 and 3 were set by reading twenty
findings from the library flood, where every false alarm was a stroke of 36 to 48% of
the well repeated 4 to 10 times; we may raise them.

*Library flood test, on the built rule.*
Over the 787 library protocols that check, the rule fires 169 times in 106 protocols
(the spec predicted 104 by replay). By kind: a stroke under half of the well 51
findings in 42 protocols; fewer than 3 strokes 20 in 14; a stroke of the whole well
35 in 22; and under the pipette-cap clause 63 in 46 (36 under-half, 27 fewer-than-3).
Twenty were read against their source and README, eight under-half, four whole-well,
four fewer-than-3, three capped, one other.

| read as | n | what they are |
|---|---|---|
| real | 9 | `2cc59d` mixes 300 µl in a 300 µl ELISA well (5 strokes of the whole well); `1adec6` `mix_after=(4, 20)` in 20 µl; `058124` fifteen 200 µl strokes in 200 µl at 1 mm; `0be1bf` 240 µl strokes in 230 µl; `4568fa-2` one 80 µl stroke in 100 µl at two dilution steps (the mix count is a parameter defaulting to 1); `3955db` one stroke in a 650 µl pool; `5f37a2` 5 strokes of 50 µl in 360 µl with a P300; `0aa51a` 5 strokes of 5 µl in 12 to 20 µl of oligo |
| borderline | 4 | `211fe1` 3 strokes of 7 µl in 15 to 20 µl (35 to 47%); `33b12a` 2 strokes of 10 in 15 (rehydrating a lyophilised mix); `0aee8a` twice, 5 strokes of 100 µl in 1.8 and 2.6 ml tubes with a P300 (the cap clause; a scientist would want more) |
| false alarm | 5 | all "under half" at 36 to 48% with 4 to 10 strokes: `4ee4d6` 10 strokes of 100 in 276 µl, `0edc68` 10 of 50 in 110 and 10 of 100 in 210, `08bbaf` 5 of 100 in 214, `4b4a80` 4 of 108 in 225. Ten strokes at 45% mix a well; the 50% line alone calls them weak |
| idiom | 2 | `69486f` one 5 µl stroke after dispensing 5 µl of pool, a tip rinse; `022548` one 43 µl stroke in an 8 ml master mix immediately before drawing from it, a prime of the tip (the cap clause turns it into a finding) |

Across all 51 under-half findings the shares and counts split: 16 are at 40% or more
with 5 or more strokes (the false-alarm shape), 8 at 25 to 40% with 5 or more, and
27 have fewer than 5 strokes or under 25%.

*What this says about the thresholds.*

* **Under half, with many strokes, is not weak.** Fire the under-half clause only when
  the mixing work is small: strokes × share under 2.5 (10 strokes at 45% is 4.5,
  silent; 3 at 35% is 1.05, fires; 5 at 25% is 1.25, fires; 5 at 48% is 2.4, fires,
  which a scientist would accept as a borderline note). That removes the 16
  false-alarm-shaped findings and keeps every real one read. Alternatively lower the
  share line to 35% when there are 5 or more strokes.
* **The prime and the rinse are idioms**, not mixes: a single stroke in a stock
  immediately before an aspirate from it with the same tip (`022548`), and a single
  stroke in a destination immediately after dispensing into it and before the tip is
  dropped (`69486f`). Exclude the first (a prime, which vendors recommend); keep the
  second as it is, because one stroke after a dispense is what `mix_after=(1, v)`
  does and it is weak.
* **The pipette-cap clause is right for a P300 in a tube and wrong for a P20 in a
  deep well.** As built, a P20 mixing a 505 µl well is judged against half of 20 µl, so
  `mix_after=(3, 10)` in 505 µl passes the share test and only the count clause can
  fire; with 3 strokes it is silent though it mixes nothing (the `fill-01` shape with
  one more stroke). Tighten: when the pipette's maximum is under a fifth of the well
  (P20 in anything over 100 µl, P300 in anything over 1.5 ml), no stroke it can make
  will mix the well, so fire whatever the count, with the fix "mix with the P300" or
  "mix with the P1000". Between a fifth and the whole, keep the clause as built. That
  keeps `0aee8a` (P300 in 1.8 ml, 300 of 1760 is 17%: fires, borderline-real) and
  `5f37a2` (P300 in 360 µl: as built).

Drafts: 7 of 36 drafts by hand; the built rule's own count over those finals was not
re-run here.

*Flood test.* Library: 104 of 833 protocols mix with under half the well's volume by
replay and 92 use fewer than 3 strokes in the source, many of them single-stroke
pre-wets in troughs, which the exclusions above remove; read twenty. Drafts: 7 of 36
drafts (a Super draft of `fill-01`, `prot-01`; a Nano draft of `dil-01`,
`pcr-07`; a Super draft of `fill-01`, `dil-03`, `clone-01`).

### The next four, in one paragraph each

**`TIP-RACK-MISMATCH`** (structural, error). A pipette's `tip_racks` includes a rack
whose load name is not in the pipette definition's `defaultTipracks` (the P20 GEN2
lists only the 10 and 20 µl racks); or a multi-channel pipette targets a labware
whose rows are fewer than its channels (the trace's D-11 expansion gives fewer
targets than channels); or an aspirate is at a negative height (below the well floor)
on stock labware. The simulator passed all three. Needs the pipette definitions in the
trace header (`Pipette.default_tipracks`) and the rack's load name. Fires:
`brad-01/05` of the short-on-tips set. Near miss: a P300 with the 200 µl filter rack.

**`BEAD-CLEANUP-STEPS`** (role, warning; error for supernatant removed with the
magnet off). A liquid whose role is beads (`beads`, `ampure`, `spri`, `magnet`)
reaches a well on a magnetic module. Then, in order: an aspirate from that well of
more than a third of its volume before the first engage of that module, or less than
2 minutes (Beckman) after it, is `settle`; fewer than two arrivals of an ethanol-role
liquid between the first supernatant removal and the arrival of a carrier-role
elution liquid is `washes`; an elution liquid arriving while the magnet is still
engaged (no disengage after the last wash) is `elution_on_magnet`; an aspirate from
the eluted well of the whole volume is `beads_carried`. The engage and disengage are
`other` events whose `detail` names them; the trace should promote them to an op
`magnet` with `detail` engage or disengage. Test-mode flags in the library shorten
delays, so read before trusting the library count (23 protocols with zero settle).

**`COMPONENT-FRACTION`** (role, warning). In a well whose technique is a digest or a
PCR: enzyme-role volume over 10% of the final volume; DNA-role (sample) volume over
25% of a digest or 40% of a PCR; a liquid whose name says cDNA or RT reaction over
10% of a qPCR (note between 10 and 20%, Thermo's limit). Pure arithmetic on the
final well from the state; needs the technique from the map. Fires: 3 µl of enzyme in
20 µl. Near miss: 1 µl in 20.

**`SUSPENSION-SETTLED`** (role, warning). A source whose liquid role is cells,
culture, colony, bacteria or beads is aspirated more than N minutes (we
set N; 5 is the bench convention, no source gives it) after the last mix stroke in
it, or after its load with no mix at all, while a dispense series is running from it.
Needs the clock, which `run.time_of` gives. Fires: 96 wells seeded from one tube over
25 minutes with no mix. Near miss: `mix_before=(10, 500)` on each transfer.
