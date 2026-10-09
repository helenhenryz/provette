# Roadmap — what is not done, and what would make it so

One line each: what is missing, why it matters, and what it would take, with the page it was
read from. Nothing here is promised; it is the honest list, kept where a reader can find it.
The order inside each section is by value, as far as we can judge it.

## The product is ready for it; we have not done it yet

* **A rule written at the form by one of us, with her name on it.** The rule form (`/rules/new`)
  writes a declared rule as data and the Rules tab shows "proposed by" whom; today the only
  proposed rule is the example, and no rule carries a proposer's name. It would take one
  of us, one source, and one afternoon at the form (D-22, D-23; `provette/rules/README.md`,
  "Declared rules").
* **A recorded failure.** "Did this run work? No" under a verdict writes a failed-run record
  and `/rules#failures` offers "Start a rule from this"; the Failures tab reads "None yet". It
  would take one run the bench did not accept, marked by the person who ran it
  (`docs/how-it-works.md`, section 8; `api/outcomes.py`).
* **A practitioner's read of the findings.** Nobody outside the team has judged a finding;
  `eval/audit/triage.csv` has 942 rows with two empty columns (verdict, why) and the headline
  "N real problems in published protocols" waits for them. It would take us, or one
  person who runs a robot, reading ten findings (`eval/audit/README.md`, "Why the headline
  waits").

## The evidence

* **A single-candidate Nano row.** Nano's rows are best of three candidates with the checks as
  judge; the live flow runs one candidate, so the cheaper choice cannot be offered honestly
  until a single-candidate row exists. It would take one run of `eval/agent/run.py` on Nano,
  34 requests, one episode each (`eval/agent/README.md`).
* **Nano's reasoning is often cut and continued**, and every continuation re-sends the whole
  conversation; a server-side reasoning budget would remove the cut, and the cost of the
  continuation with it (`provette/agent/README.md`).
* **The planner is tested on Super only**, and a wrong map is caught by `verify` rather than
  prevented. It would take the planner's run on Nano and a read of every difference
  (`eval/planner/README.md`).
* **The library declares liquids in 11 of 833 protocols**, so the role-based rules are silent
  on it and the audit's counts are counts of findings, not of problems. It would take the
  triage above, or plate maps for a sample of library protocols (`eval/audit/README.md`).

## The checks

* **The catalogue's other rows are not rules.** For every technique, `not_checked` lists the
  mistakes the catalogue found and nothing checks (too much template, a pool never mixed, a
  bead cleanup's settle time, a thermocycler without its lid temperature, and the rest); the
  page shows them beside every verdict so silence is not safety. Each is a rule with a source
  and fixtures, in Python or, where a shape fits, as data (`provette/rules/coverage.yaml`,
  `not_checked`; `docs/detection-catalogue.md`, rows N9 to N18; D-22, D-25).
* **Roles are English word lists.** Liquids called A, B and C get structural severity only and
  are reported as unplaced; the product asks beside the verdict and keeps the answer. It would
  take the plate map or the request naming what each liquid is, and the lists growing from the
  names met (`provette/rules/README.md`, "Known blind spots"; D-24).
* **The runs the loop does not close.** Every episode that did not verify is read in
  `eval/agent/README.md`; what they have in common is what the loop should learn next (D-31).
* **Two library protocols hit a tracer bug** (`6cd9d6`, `generic_ngs_prep`) and one
  (`5520f0`) does not finish simulating in eleven minutes. It would take reading the two
  traces and a timeout that reports rather than waits (`docs/replay-support.md`, "The table").

## The replay

* **An empty module and the thermocycler lid are not drawn.** A module holding labware is
  drawn in 3D under it, at its definition's height; the trace records a module only as the
  `module` of the labware on it, so a module with nothing on it is not there at all, and the
  lid is not drawn. It would take the trace recording every loaded module with its model and
  slot (`docs/replay-support.md`, "Modules"; `provette/state/README.md`).
* **Custom labware has no height table.** 513 library protocols load a definition with no
  inner geometry; the well is drawn as a straight column and the contact model's height is a
  floor there, so a low dispense called dry may be wet. It would take the shape declared or
  measured per custom definition (`docs/replay-support.md`; D-14).
* **No labware upload on Check.** Most library protocols that use custom labware ship its definition beside the script;
  the check page takes only the protocol text, so the simulator refuses them ("Unable to find
  a labware"). `provette view --labware-dir` takes the folder; the page needs the same data path
  (`docs/replay-support.md`, "Custom labware on the product's check page").
* **The thermocycler's programme, the lid and time at temperature** are one event each and
  nothing is drawn; the trace's contract has no field for the profile's steps
  (`docs/replay-support.md`; `provette/trace/README.md`, "Known gaps").
* **Flex** is out of scope: it needs `opentrons` 9.x, which refuses every OT-2 protocol; JSON
  protocols and run-time parameters were not tried, and `move_labware` would not move the
  drawing. It would take a second pinned version behind the same interface (D-06, D-07;
  `provette/trace/README.md`, "Known gaps"; `docs/replay-support.md`, "Out of scope").

## The deployment

* **The checks run on the Machine, not in a Token Factory Sandbox.** The sandbox runner works
  (`eval/agent/results/super-sandbox`; a check takes about 14 s there against 6 s locally) and
  is one environment variable away, `PROVETTE_RUNNER`; the deployment runs local because the
  demo must not stop when a beta service does (D-35, D-37).
* **The live flow writes with Super only.** Nano is seen in the
  gallery with its transcripts; offering it live needs the single-candidate row above, or
  best-of-3 moved from `eval/agent/run.py` into the agent package (`api/live.py`, `RUN_MODEL`;
  `eval/agent/README.md`).

## Code worth tidying

* **A wall-clock assert** in `tests/api/test_checks.py` (the buggy PCR example's findings and
  replay in under fifteen seconds) states a documented claim and could flake on a loaded
  machine; it would take a bound that is measured, or a mark that skips it under load.
* **A real `sleep(60)`** in `tests/corpus/workers_for_tests.py` is the fixture that proves the
  timeout kills the process group; a shorter sleep with a shorter timeout in the test would do
  the same (`tests/corpus/workers_for_tests.py`).
* **Four `_ul` helpers** format microlitres, in `provette/calc/dilution.py`,
  `provette/intent/report.py`, `provette/agent/tools.py` and `provette/view/export.py`; one in
  `provette/model.py` would do, once its callers agree on the rounding.
