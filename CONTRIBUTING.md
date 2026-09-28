# Contributing

The frame every change is held against: **the simulator checks the physics; Provette checks
the experiment.** A plate map says what every well should end up holding, a deterministic
replay proves or disproves that the protocol delivers it, and the language model is never
the judge (D-01, D-28). So the question every piece of work answers is: does this help prove
that a protocol does what was intended, or help a model get to one that does? The gate is
`make check` exit 0; the voice is the last section; [`docs/how-it-works.md`](docs/how-it-works.md)
says how every piece works and [`DECISIONS.md`](DECISIONS.md) why. This page says how a change,
or a rule, gets in.

## Running it

```
uv sync                                      # Python 3.10 and opentrons 8.8.2, pinned (D-04)
uv run provette check  protocol.py             # the biology checks
uv run provette verify protocol.py --platemap map.json   # the plate map, accounting, prep sheet
uv run provette view   protocol.py --platemap map.json --out replay.html
cd web && npm ci && npm run build && cd .. && sh deploy/dev-api.sh    # the product on :8765
```

On a machine with ROS sourced, prefix every Python command with `env -u PYTHONPATH` (the
Makefile does it). Settings the product reads are in [`.env.example`](.env.example); the
checker needs none.

## The gate

```
make hooks        once per clone: git runs `make check` before every push
make check        lint, strict types (mypy strict) and the whole Python suite
make check-web    the pages: lint, type-check, build, rendering tests (node 22)
make check-all    both; run it before a push that touches web/ or api/
```

`make check` exit 0 is the gate. **Read the exit code**, never its output; there is no hosted
CI, so the gate runs on the machine the work is done on. Commit by path (`git add <files>`)
and read `git status` before every commit. A commit message is a sentence about what changed
and why, in the voice below.

## Adding a rule in Python

The full recipe is in [`provette/rules/README.md`](provette/rules/README.md), "How to add a rule
in Python"; the short form:

1. Find what the rule rests on and add a row to
   [`docs/rule-sources.md`](docs/rule-sources.md) (and its key to
   `provette/rules/sources.yaml`). A rule with no source is not a rule yet.
2. Write the fixtures first: `tests/fixtures/rules/<RULE-ID>/fires_*.py` (at least two) and
   `near_miss_*.py` (at least three), realistic protocols whose first comment line says in
   plain words what the file tests and whether it should fire.
3. Write the module: the rule in words at the top (what happens, why it matters to the
   experiment, what it does not fire on), then a function over `facts_of(trace, run)`
   (`provette/rules/common.py`), registered in `RULES` (`provette/rules/__init__.py`).
4. `PROVETTE_REGEN=1 env -u PYTHONPATH uv run pytest tests/rules` freezes what the rule found
   beside each fixture as `<name>.expected.json`; read every file it wrote before trusting it.
5. Run it over the correct protocols (`eval/checks/run_correct.py` must still verify all 34),
   over the agent runs' drafts, and over the public library (`eval/audit/`), and read every
   hit. A rule that floods is worse than no rule.
6. Add its row to the table in `provette/rules/README.md` and its section to
   [`docs/rulebook.md`](docs/rulebook.md). `make check`, exit 0.

## Adding a declared rule (no code)

If the rule is one of the three shapes (a tip carrying one kind of liquid must not enter a
well of another; a well this full must not be mixed; one liquid goes in after another), it is
a YAML file, `provette/rules/declared/<RULE-ID>.yaml`, and `provette.rules` loads it beside the
Python rules. Copy the example in `provette/rules/README.md`, "Declared rules"; keep
`status: proposed` (a proposed rule only ever makes a note, so it can be watched on real
drafts before anyone trusts it, D-23); write its fixtures and freeze them as above; add it to
the README table and the rulebook. The product's rule form (`/rules/new`) writes the same
file. Adopting a rule is changing `status` to `adopted` and writing `adopted_on`, in a commit.

## The voice

We built Provette, and we are biology students at the start of our degrees. Every
finding's explanation, every rule's description, every page under `docs/` and every README
is written so we can read it: if a sentence needs a systems background to parse, rewrite
the sentence. Decisions go in [`DECISIONS.md`](DECISIONS.md) with their basis and what would
change them; what was measured, and how, goes in the README of the experiment under
[`eval/`](eval/README.md). A number quoted on a page comes from a file under `eval/` and is
pinned there by a test, never typed. How the pages look and read is
[`docs/design.md`](docs/design.md).
