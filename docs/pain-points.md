# Pain points — what people who run liquid handlers say is hard

Researched online on 2026-09-21. Every row is something read on the page
linked, not recalled. It is a desk study: **nobody was interviewed**, and the
loudest voices are practitioners on Hamilton and Tecan machines, not students
on an OT-2. This page informs the decisions in [`../DECISIONS.md`](../DECISIONS.md); it
decides nothing by itself.

## What the sources say

| # | pain point | in their words | source |
|---|---|---|---|
| 1 | **There is no feedback loop for a robot protocol.** Code has tests; a protocol has an expensive run | "there is almost no room for error when running sensitive samples worth thousands of dollars"; for code an agent can test and correct itself, for hardware "there is no equivalent" | practitioner `silvioo`, [labautomation.io, AI Assisted Method Writing](https://labautomation.io/t/ai-assisted-method-writing/7218) |
| 2 | **Nobody trusts an AI-written method they cannot check** | "hope that you don't end up staring at an AI response saying 'You're completely right, I shouldn't have thrown those irreplaceable primary cells into the tip waste.'" | practitioner `LukeWitt`, [same thread, page 2](https://labautomation.io/t/ai-assisted-method-writing/7218?page=2) |
| 3 | **A script that compiles can still be wrong about the experiment** | "a script may compile while still violating the validated protocol, misaligning sample or well mappings, mishandling tips"; general LLMs passed their gates at most 35.0% of the time; in their wet-lab run "colonies appeared on the negative-control plate" | [ProtoPilot, arXiv 2606.31763](https://arxiv.org/html/2606.31763) |
| 4 | **Programming is the barrier for biologists** | "for individuals who lack a programming background, this necessity makes building, modifying, and troubleshooting pipetting routines a frustrating and laborious task" | search summary of [The Scientist, Accessible Automation](https://www.the-scientist.com/accessible-automation-for-liquid-handling-workflows-74719); the skills gap is also the theme of [Holland and Davies 2020](https://www.frontiersin.org/journals/bioengineering-and-biotechnology/articles/10.3389/fbioe.2020.571777/full): "amphibious researchers" |
| 5 | **Research protocols change constantly, and many are used once** | protocols "need to change or evolve frequently, as this will imply repeated workflow construction or modification"; "some of these protocols are only used once" | [Torres-Acosta et al., bioRxiv 2022](https://www.biorxiv.org/content/10.1101/2022.11.03.515004.full.pdf) |
| 6 | **Small changes force re-programming and re-testing** | "hard-coding tips has been a major issue in the past as when a tip type ran out on critical day the handlers were down as they had to be re-programed and re-tested" | [labautomation.io, toy problem](https://labautomation.io/t/liquid-handling-software-toy-problem-difficult/1586) |
| 7 | **Validation is slow and physical** | "it is best to do it dry, next do it with water, then change the tips out so they are sterile, and run it with your real samples" | [Opentrons, Calibrate and run a protocol](https://opentrons.com/archives/resource/calibrate-and-run-a-protocol); Opentrons documents a [dry-run use case](https://docs.opentrons.com/v2/parameters/use_case_dry_run.html) |
| 8 | **Automation spreads a mistake across everything** | a systematic error can run across "many thousands of samples" before anyone notices | [Holland and Davies 2020](https://www.frontiersin.org/journals/bioengineering-and-biotechnology/articles/10.3389/fbioe.2020.571777/full) |
| 9 | **Method errors, not only hardware errors: mixing, sequential dispensing, wrong parameters, over-dispensing** | unmixed wells give concentrations "very different from the assumed theoretical concentration levels"; 20% over-dispensing in a screening lab costs "$750,000" a year in reagent | [BioProcess International, Automated liquid handlers as sources of error](https://www.bioprocessintl.com/assays/automated-liquid-handlers-as-sources-of-error) |
| 10 | **Deck setup by a human is a known failure point** | vendors sell software that "analyzes the deck for common setup errors" before a run | search summary of [Beckman, Biomek Method Launcher](https://www.beckman.com/liquid-handlers/software/biomek-method-launcher) |
| 11 | **Spreadsheet arithmetic is wrong more often than people think** | uncorrected errors "in at least one percent of the formula cells" of spreadsheets built in laboratory experiments | search summary of [Panko, spreadsheet error studies](https://arxiv.org/pdf/0804.0941); not read in full |
| 12 | **Methods cannot be shared, versioned or reviewed** | "there is no shareability, no version control, no ability to collaborate" | practitioner `nateazevedo`, [labautomation.io thread](https://labautomation.io/t/ai-assisted-method-writing/7218) |

## What the same sources say is hard and we cannot touch

The practitioners' deepest objection to AI method writing is **physics**:
liquid classes, viscosity, aspirate speeds, droplets on a well wall, a tip
brushing a cell layer ("fighting physics, chemistry, and biology"; "the number
of options on those moves ... is nearly infinite"). Also integrating third-party
devices and LIMS. A simulator-based checker sees none of this. Anything we
build verifies the **logic** of a protocol — what goes where, in what amount,
through which tip — and must say plainly that it does not verify the physics.

## Where this points

Rows 1, 2 and 3 are one pain, said three ways by three kinds of source: **there
is no way to check that a protocol does what was intended, short of running
it.** Rows 5, 6 and 7 say why it hurts: protocols change all the time, and every
change restarts a dry, water, real cycle. That is the gap a deterministic replay
fills, and it is the thing we have already built the hard part of.

Rows 4, 10, 11 and 12 are real, and adjacent: they argue for the package around
the check (plate map in, prep sheet out), not for a different core.

What the research did **not** find: anyone asking for contamination checking by
name. The nearest is ProtoPilot's contaminated negative control and
"mishandling tips". It is one check inside the answer, not the answer.
