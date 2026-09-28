# Provette

**Every well, proven.** The test suite lab-robot protocols never had. A scientist states what every well
should end up holding; a deterministic replay proves or disproves that a protocol
delivers it; and with that proof in the loop, an open model can write the protocol.

**Live:** <https://provette.fly.dev> (the judge password is in the submission notes)

Lab robots run Python scripts, and more and more of those scripts are written by
language models, because most biologists cannot program. The robot's own simulator
checks the physics: the arm can reach, there is a tip on, the well will not overflow.
It does not know what the liquids are. It passes a serial dilution at half the
volume asked, a master mix at fifteen times the volume asked, and one tip carrying
patient samples back into the shared reagent. People who run these robots say the
missing thing plainly: for code an agent can test and correct itself, for a robot
protocol "there is no equivalent". ([`docs/pain-points.md`](docs/pain-points.md))

Provette runs the protocol in the Opentrons simulator, follows every microlitre through
every tip and well, and answers the questions a scientist cares about:

* Does every well end up with what the **plate map** says, to the microlitre?
* Did any sample end up in the bin, or in a well it was never meant for?
* Did a used tip carry something harmful into a stock?
* Will a tube run dry, or the tips run out, half way through?
* Is every volume within what the pipette can measure?

Every answer names the line, the wells and the fix, in words anyone in the lab can
read, and says beside the verdict what was checked for this technique and
what was not: silence is not safety. A **prep sheet** (what to load where, and how
much) and a **deck replay** (`provette view`) come out of the same run. Then an agent built on
NVIDIA Nemotron, on Nebius Token Factory, uses those checks the way a coding agent
uses tests: it writes, checks, repairs, and submits only what verified.

Built for the Nebius x NVIDIA Global AI Hackathon, Coding and Agentic Engineering
track. It checks the **logic** of a protocol, not the physics: whether a viscous
liquid pipettes accurately still needs a real run, and every report says so.

## What the numbers say

Requests written the way a scientist would ask: 17 everyday ones, each in two wordings (34 runs),
and 15 harder ones ([`eval/requests/`](eval/requests/), [`eval/requests-hard/`](eval/requests-hard/));
the model writes, the simulator and Provette judge,
the model repairs from the report. How each number is measured is in [`eval/`](eval/README.md);
the Methods page computes every one from those files when it loads.

"Verified and clean" means the plate map matches on every well, the sample accounting and the
prep sheet have no flag, and none of the twelve checks raises an error or a warning; the model's own first draft is
judged the same way.

| Nemotron on Token Factory, reasoning on | verified alone (first draft) | **with Provette in the loop** | cost per verified protocol |
|---|---|---|---|
| Super 120B, 34 requests | 1 of 34 | **31 of 34 (91%)** | $0.044 |
| Super 120B, 15 harder requests | 2 of 15 | **12 of 15 (80%)** | $0.097 |
| Nano 30B, 34 requests, best of 3 | 0 of 34 | **25 of 34 (74%)** | $0.196 |
| Nano 30B, 15 harder requests, best of 3 | 0 of 15 | **8 of 15 (53%)** | $0.287 |
| Super 120B, 34 requests, the twelve rules in its prompt, no checker | 7 of 34 | no loop | $0.37 in all |

The same twelve rules written into Super's prompt as instructions, with no checker, give 7 of
34: of its 29 drafts that ran, 19 broke a rule it had just been told. It is the loop that carries
the result, not knowing the rules ([`eval/baseline/`](eval/baseline/README.md)). Every episode
that did not verify is read in [`eval/agent/README.md`](eval/agent/README.md): Super's misses are
plate-map layouts the loop did not close and a few prep-sheet or accounting flags; Nano's are
mostly reasoning that runs out of tokens. The plate-map planner verifies a known-correct protocol
on 14 of 17 requests, and never turned a real request away ([`eval/planner/`](eval/planner/README.md)).
The same loop also ran with every check in a Token Factory Sandbox, one disposable sandbox per
check: 2 of 3 verified (`results/super-sandbox` in [`eval/agent/README.md`](eval/agent/README.md)).
The demo runs its checks on its own machine, so it does not stop when the beta service does (D-37).

The checks themselves: 34 correct protocols verify, across 986 wells, and none verifies against
the wrong map; of the 228 planted bugs that change what a well holds, all of which the simulator
passes, 212 are caught, and the 16 missed are samples swapping wells on a plate whose map leaves
positions free ([`eval/checks/`](eval/checks/README.md)). Opentrons' own analysis of each run
agrees with the ledger on 788 of 788 public protocols, and on 16 of 16 written for API 2.14 or
later, where it is a fully independent reading ([`eval/ledger/`](eval/ledger/README.md)).

## Try it

```
uv sync                                   # Python 3.10, opentrons 8.8.2
uv run provette check   protocol.py                              # the biology
uv run provette verify  protocol.py --platemap map.json          # the plate map, accounting, prep sheet
uv run provette view    protocol.py --platemap map.json --out replay.html   # watch it
```

The agent needs a Token Factory key in `PROVETTE_API_KEY` and `PROVETTE_BASE_URL`
(`https://api.tokenfactory.nebius.com/v1`):

```
uv run python eval/agent/run.py --model nvidia/nemotron-3-super-120b-a12b --out results/super
```

The product (the pages under `web/`, served by `api/`) runs with `sh deploy/dev-api.sh` after
`cd web && npm ci && npm run build`, at http://127.0.0.1:8765; every `PROVETTE_*` setting is
listed in [`.env.example`](.env.example). Deploying it (one machine on Fly.io, one command
once three files exist) is [`docs/deploy.md`](docs/deploy.md), and every setting the
deployment reads is in [`deploy/README.md`](deploy/README.md).

```
make check        lint, strict types and the whole Python suite: the gate before every push
make check-web    the pages: lint, type-check, build and the rendering tests (needs node 22)
make check-all    both
make hooks        once per clone: git runs `make check` before every push
make web-fixtures refresh the frozen API answers the web tests render
```

Read the exit code of `make check`, never its output. [`CONTRIBUTING.md`](CONTRIBUTING.md)
says how a rule is added; [`docs/index.md`](docs/index.md) lists every document.

## How it is built

```
request ──► plate map ──► model writes ──► simulator ──► verify + check ──► repair ──► prep sheet, replay
              (approved)     (Nemotron)     (physics)     (Provette)          (model)
```

| where | what |
|---|---|
| [`provette/trace`](provette/trace/README.md) | runs a protocol under the simulator and records every action, checked against Opentrons' own analysis of the same run (independent from API 2.14) |
| [`provette/state`](provette/state/README.md) | replays the record: what is in every well and on every tip, where it came from, whether the tip touched the liquid |
| [`provette/intent`](provette/intent/README.md) | the plate map: does every well hold what was asked; where did every sample go; what must be on the deck |
| [`provette/rules`](provette/rules/README.md) | the twelve checks: carry-over into a stock or a well, an unmixed draw, a volume the pipette cannot measure, a well past its rim, a trough drawn from above its liquid, a cold module never set, a mix too weak, a well left unmixed, an enzyme before its diluent, a PCR plate without its control, the wrong plate for the technique; severity follows what was carried, and every threshold is in [`docs/rulebook.md`](docs/rulebook.md) |
| [`provette/planner`](provette/planner/README.md) | the plate map proposed from the request, for a person to approve |
| [`provette/agent`](provette/agent/README.md) | the tool-calling loop: plate map, labware, calculators, write, check, submit |
| [`provette/view`](provette/view/README.md) | the deck replay page |
| [`provette/sandbox`](provette/sandbox/README.md) | where the checks run: this machine, Docker, or a Token Factory Sandbox |
| [`api`](api/README.md), [`web`](web/README.md) | the product: the API and the pages |
| [`eval`](eval/README.md) | the evaluation every number comes from |
| [`docs/how-it-works.md`](docs/how-it-works.md) | every stage end to end, each claim with the file it was read from |
| [`docs/harness-practices.md`](docs/harness-practices.md) | how the loop is fitted to Nemotron: a cut thought closed and continued, the reasoning sent back, old reports collapsed, NVIDIA's sampling, best of k with the checker as judge; each practice with its source |
| [`docs/roadmap.md`](docs/roadmap.md) | what is not done, why it matters, and what it would take |
| [`DECISIONS.md`](DECISIONS.md) | every decision, its basis, and what would change it |

The nearest prior art we found, PyLabRobot's contamination tracker of 2024, followed tips and
wells for one rule family and raised an error on aspirate; it is cited in `DECISIONS.md` (D-26).

## Who we are

We're [Helen Henry](https://www.linkedin.com/in/helen-henryz/) and
[Nyle Hussain](https://www.linkedin.com/in/nyle-hussain-b7ab05423/), two first-year biology
students: Helen at [Tampere University](https://www.tuni.fi/en) in Finland, Nyle at the
[University of Glasgow](https://www.gla.ac.uk/) in Scotland. We teamed up for this
hackathon and built Provette across two countries, with AI coding agents, the same way
Provette works: we set the goal, wrote the checks the work had to pass, and reviewed what came
back. The operating guide we gave the agents is in the repository, beside the code it produced.

What we built: the agent harness around Nemotron (its tools, its budgets and the repair loop),
the ledger that follows every microlitre through every tip and well, the rules and the
plate-map check, the planner and its request gate, the 2D and 3D replay, the rule form, and the
evaluation every number here comes from.

Every rule rests on a published source: a paper, a kit manual or a lab guideline, cited beside
the rule ([`docs/rule-sources.md`](docs/rule-sources.md)). We read them, turned each into a
check a machine can run, tested it against real protocols until it stopped crying wolf
([`docs/detection-catalogue.md`](docs/detection-catalogue.md)), and decided how much each
finding matters. A rule without a source doesn't load. The plate maps, and the word lists that
tell Provette what a liquid is, are ours too. We wrote every rule so that a biologist who
doesn't code can read it, argue with it, and add a new one through a form.

## Disclaimer

Provette is a checking aid. It does not replace review by a trained scientist, and a
verified protocol is not a promise that an experiment will work.

## License

Apache-2.0. See [`LICENSE`](LICENSE).
