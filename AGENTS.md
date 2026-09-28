# AGENTS.md — the operating guide for an AI-assisted session

Tracked, and part of the repository: the same guide as `CLAUDE.md`, for the agents
that read `AGENTS.md`. It says how a session works here: what the goal is, what
governs it, where to look before investigating anything, and what to run before
pushing.

## The mission

A submission to the Nebius x NVIDIA Global AI Hackathon, entered by
**2026-10-29**, one day ahead of the deadline: a working product, a measured
finding, and a three-minute video — on code that is modular, readable,
documented, and that we, the two biology students who built it, can open after
the build and add a rule to without asking anyone.

A rule that fires only on the mutant written to trigger it is evidence about
the mutant, not the rule. If the test makes the answer inevitable, say so and
change the test. The findings that count come from protocols we did not write.

## The frame, and everything is held against it

**The simulator checks the physics. Provette checks the experiment.** A plate map
says what every well should end up holding; a deterministic replay of the protocol
proves or disproves that the script delivers it, without harmful carry-over, without
losing a sample, without running dry. That replay is the test suite lab-robot
protocols never had, and it is what lets an open model write them (D-28).
Four artefacts:

| artefact | what it is |
|---|---|
| **the plate map** | the intent: what each well should hold at the end, approved by a person |
| **the trace** | every primitive action of a protocol run, as a structured event with its source line |
| **the state** | what is in every well and on every tip after each event: composition, provenance, time at temperature |
| **the finding** | where the state departs from the plate map or breaks a rule, with the step, the line, the wells and a sentence anyone in the lab can read |

**So the question every piece of work answers is: does this help prove that a
protocol does what was intended, or help a model get to one that does?** When a
session cannot say how its task serves that sentence, the task is wrong.

**It checks the logic, not the physics**, and every report says so.

**The checker is deterministic. The language model is never the judge.** It
names what a liquid is, it writes protocols, and it patches them from a report.
A finding the model asserts and the state cannot show is not a finding.

**No model training.** Hosted Nemotron on Nebius Token Factory, and a checker
made of ordinary Python. That is a constraint of the project, not a gap in it.

## Before you investigate anything

Most of what a session is about to work out is already written down. Look in
this order:

| where | what is in it |
|---|---|
| [`README.md`](README.md) | what Provette is, in one page |
| [`docs/how-it-works.md`](docs/how-it-works.md) | how every piece works and why, end to end, each claim with the file it was read from; read it before asking "why does it do that?" |
| [`docs/design.md`](docs/design.md) | how the product looks, reads and behaves: the principles, the tokens, the patterns every page reuses |
| [`docs/hackathon.md`](docs/hackathon.md) | the governing text: requirements, tracks, criteria and dates |
| [`docs/pain-points.md`](docs/pain-points.md) | what people who run liquid handlers say is hard, with sources |
| [`eval/`](eval/README.md) | the evaluation: the checks on correct and broken protocols, the agent runs, the baseline, the planner |
| [`DECISIONS.md`](DECISIONS.md) | one row per decision: what was chosen, its basis, and what would change it |
| [`docs/rulebook.md`](docs/rulebook.md) | the rulebook we own: every rule in words, what it rests on, the numbers and what changing them does |
| [`docs/rule-sources.md`](docs/rule-sources.md) | what every rule family rests on, where the sources disagree, and what we looked for and did not find |
| [`docs/index.md`](docs/index.md) | every document under `docs/`, one line each; [`CONTRIBUTING.md`](CONTRIBUTING.md) is how a change, or a rule, gets in |

**A file's name is not its contents.** Read the page before deciding it says
nothing.

**When you settle something, write it where the next person will look**, and
say in your report where you put it. If the right place does not exist, that is
the finding: make the place, and add it to the table above. If a page is wrong,
fix the page rather than working around it.

## What governs

**The hackathon's rules govern what we submit.** They are transcribed in
`docs/hackathon.md` from the Devpost pages; that file changes only when the
source changes. If the rules do not decide a question, record it in
`DECISIONS.md` with what we build to meanwhile and what would settle it.

**The biology is governed by the rulebook we write.** Every rule
names who proposed it and what it rests on: a course protocol, a datasheet, a
paper. A rule with no basis is not a rule yet.

**Everything else, the session decides.** Decide, act, and write the decision
down with its reasoning, what you rejected, and what would change your mind. A
menu of options handed to a reviewer is worse than a decision made badly,
because their pick ratifies your framing.

## The two laws

**1. First principles. Never guess a runtime fact.** How the Opentrons
simulator behaves, what a Token Factory Sandbox allows, what a Nemotron
endpoint returns: read the code, read the official documents, or run it. If you
cannot verify it, say you could not.

**2. Delete before you build.** Make the requirement less dumb; delete the part
or the step; simplify what survives; accelerate the cycle; automate last.

And the rule that catches the most: **a cause is not established until it is
measured in a run.** Reading the code says what *could* happen.

## The gates

```
make check      lint, strict types and the whole test suite -- READ THE EXIT CODE.
                Never grep its output, and never pipe it to `tail`, which returns
                tail's status and not make's.
make check-all  the same, and the pages under web/: lint, types, build, tests
make hooks      once per clone: git then runs `make check` before every push
```

`make check` exit 0 is the gate before a push; `make check-all` before one that
touches `web/` or `api/`. **There is no hosted CI**: the
gate runs on the machine the work is done on. Python is pinned to 3.10 and
`opentrons` to 8.8.2 (D-04); the Makefile unsets `PYTHONPATH`, because a
machine with ROS sourced breaks test collection otherwise.

## Who reads the output

The product is used by a working lab scientist, someone who runs an OT-2 and
knows what a plate map, a master mix and a µl are: the pages are terse, in lab
words, and carry no sentence such a person would not miss. The product is
built and maintained by us, two biology students at the start of our degrees:
the rulebook, the word lists, every finding's explanation, every rule's
description and every page under `docs/` are written so we can read and change
them, and a sentence that needs a systems background to parse is rewritten.

## How the work is divided between sessions

* **A leading session directs the work.** It holds the plan, reviews every
  change before it lands, and is the only session that decides what is next. It
  is a real session a person can talk to, never a subagent: a subagent reports
  to its parent and dies with it, so it cannot hold a plan across a day.
* **Buildable pieces go to subagents**, one testable piece of work each, with
  the exact contracts and paths written out — never "read the plan for
  context". A truncated or wandering result means the piece was too big: split
  it, do not retry the same size.

Whoever does the work, the gate is the same: `make check` exit 0, and a review
by the leading session before anything lands on `main`.

**Process notes live outside this repository.** The plan of the day, the
hand-offs and the reports are working papers; what belongs here is the decision
and its reasoning, written where the next person will look.

## The model setting

The roles above are what is fixed; the models behind them are a setting. Use the
strongest model you have for the leading session and for any subagent that
writes code, and say in the report which one did the work.
