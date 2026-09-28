# `api/` — the product's backend

FastAPI on Python 3.10, in the same process tree as `provette`. It wraps the pipeline and never
reimplements it: `provette.check.check`, `provette.intent.cli.verify_trace`, `provette.view.export`
and `render`, `provette.planner.loop.plan`, `provette.agent.loop.run_episode` with `LocalRunner`.
What it returns is the pipeline's own JSON, and the pages under [`web/`](../web/README.md)
render whatever is there.

```
deploy/dev-api.sh                      the API on :8765, serving web/dist (stop: deploy/dev-api.sh stop)
uv run uvicorn api.main:app --reload   the same, by hand
make check                             the Python gate (lint, types, tests: tests/api included)
make check-web                         the pages: build and rendering tests
make check-all                         both; run it before a push that touches web/
```

The live flow needs `PROVETTE_API_KEY`, `PROVETTE_BASE_URL` (`set -a; . ~/.config/provette/token-factory.env;
set +a`) and `PROVETTE_JUDGE_PASSWORD`; without them the gallery and the checker work and `/api/live`
says the flow is off. **Every setting, its default and what it does is in one place,
[`deploy/README.md`](../deploy/README.md)**; the top of [`settings.py`](settings.py) lists the
names and [`.env.example`](../.env.example) is the local copy. Errors a person would see are
sentences (`HTTPException` details, a run's `status.json`); the traceback behind one goes to the
process log (`logging`, module loggers), which uvicorn prints.

## The modules, one job each

| file | what it does |
|---|---|
| [`main.py`](main.py) | wires the routers, `/health`, the OpenAPI page at `/api/docs`, and serves the built pages with a fallback to `index.html` for deep links (only files under `web/dist`; an unknown `/api/...` path is a 404) |
| [`settings.py`](settings.py) | every environment variable, in one dataclass |
| [`episodes.py`](episodes.py) | reads an episode directory as the agent loop wrote it (`done.json`, `transcript.jsonl`, `NN-draft.py`, `NN-checks.json`) into the gallery's contract; a live run is an episode directory too |
| [`steps.py`](steps.py) | a transcript as readable steps: **one describer per tool**, a generic fallback for a tool it has never seen |
| [`worker.py`](worker.py) | one analysis in a subprocess: the simulator, the rules, the plate-map check and the replay export from one run |
| [`analysis.py`](analysis.py) | runs the worker with a timeout and caches by the protocol and map (`<data>/cache/`) |
| [`gallery.py`](gallery.py) | `GET /api/episodes`, `/api/episodes/{set}/{condition}/{request}` and, under it, `/drafts/{n}`, `/analysis`, `/protocol.py`, `/replay.html`: the pre-run episodes |
| [`checks.py`](checks.py) | `POST /api/checks`: flow 3, check a protocol you already have, kept at a shareable URL: `GET /api/checks` (this deployment's checks, newest first, for the Runs page's "Yours"), `GET /api/checks/{id}`, `DELETE /api/checks/{id}` (judge key), `/replay.html`, `/protocol.py`; `GET /api/platemaps` and `/api/platemaps/{id}` (the hand-written maps to check against); `GET /api/examples/protocol` (the reference protocol the page offers) |
| [`live.py`](live.py) | flow 2: `GET /api/live` (is the flow on, the day's spend); `POST /api/plans`, `GET /api/plans` (this deployment's plans, newest first), `GET /api/plans/{id}`, `DELETE /api/plans/{id}`, `/api/plans/{id}/events` (SSE), `POST /api/plans/{id}/stop` for the plate-map proposal (`POST /api/plan` is the same, unstreamed); `GET /api/runs`, `POST /api/runs`, `GET /api/runs/{id}`, `/events` (SSE), `POST /api/runs/{id}/stop` (the loop stops before its next model call or check; the record says "stopped" and the spend so far is charged), `DELETE /api/runs/{id}` (a run still going is refused: stop it first), `/drafts/{n}`, `/analysis`, `/protocol.py`, `/replay.html`; the judge password, rate limits, two runs at once |
| [`run_settings.py`](run_settings.py) | the Settings dialog's budgets: `GET /api/run-settings` (each value, its default and range), `PUT` (judge key; out of range is refused), `DELETE` (back to the defaults); kept in `<data>/run-settings.json`, read by every plan and run as it starts |
| [`ledger.py`](ledger.py) | the day's spend against the cap, a JSON file on the volume |
| [`limits.py`](limits.py) | rate limits per client address, in memory |
| [`rules.py`](rules.py) | `GET /api/rules`: every rule in `provette.rules.RULES`, with its sources; `GET /api/roles` the word lists of `provette/rules/roles.yaml`, `POST /api/roles/{list}` adds a word (judge password) |
| [`evidence.py`](evidence.py) | `GET /api/evidence`: the methods page's numbers, computed from `eval/`'s result files at request time |
| [`prices.py`](prices.py) | cost from token counts and `eval/prices.json`; the model's display name |
| [`fixtures.py`](fixtures.py) | freezes the API's answers for the web rendering tests (`make web-fixtures`) |
| [`docs.py`](docs.py) | `GET /api/documents` (the names) and `GET /api/documents/{name}`: the rulebook and what it links to, rendered from `docs/` |
| [`outcomes.py`](outcomes.py) | `POST/GET /api/outcomes`: the failed-run record ("did this run work?"), one JSON row per record in `<data>/outcomes.jsonl`; the rules page lists the failures without a rule yet |
| [`coverage.py`](coverage.py) | `GET /api/coverage?technique=`: what the checks cover for a technique and what they do not, from `provette/rules/coverage.yaml`; `GET /api/coverage/techniques` lists the techniques |
| [`auth.py`](auth.py) | the judge password check every write on a person's behalf goes through |
| [`declared.py`](declared.py) | `GET`/`POST /api/rules/sources` (the sources file, `provette/rules/sources.yaml`, read and appended to), `GET /api/rules/declared`, `POST /api/rules/preview`, `POST /api/rules/declared`: the rule form's backend over `provette.rules.declared` (validate, preview in the worker subprocess, save as proposed), and `reload_rules`, which re-reads the declared directory into `RULES` because the engine loads it once at import |
| [`replay_page.py`](replay_page.py) | `provette view`'s page with the product's theme and an embedded form, on request |

Tests: [`tests/api/`](../tests/api/): contract tests on the frozen episodes in `eval/agent/results`,
flow 3 end to end on `tests/fixtures/protocols/pcr_buggy.py` (under fifteen seconds), flow 2 with
a scripted planner and agent (no network), and the evidence pinned to the READMEs' figures.

## Where an extension goes

* **A new rule** in `provette/rules`: nothing here changes. It appears on the rules page from
  `RULES`, its findings render generically (rule id, severity, title, explanation, fix, line).
* **A new field on a finding, a prep row, a verify report**: nothing here changes; the JSON is
  passed through. The page shows it where the renderer is generic, and needs one small change
  where it is not (`web/README.md`).
* **A new tool in the agent**: one describer in `steps.py` (`DESCRIBERS`), so the step reads as
  a sentence instead of "called <name>". Nothing else.
* **A new result set in the gallery**: `PROVETTE_GALLERY_SETS` (the directory names under
  `eval/agent/results`); the image copies `eval/` whole, and the methods page computes the same
  sets.
* **A new evaluation number on the methods page**: a computation in `evidence.py` from a file
  under `eval/`, a line in `tests/api/test_evidence.py` pinning it to the README, and a sentence
  in `web/src/pages/How.tsx`. Never a typed number.
* **A different model for the live flow**: `RUN_MODEL` in `live.py`; its price must be in
  `eval/prices.json` or the cost shows as not recorded.
* **Where a live draft's checks run**: `PROVETTE_RUNNER=local|nebius|docker`
  (`provette.sandbox.make_runner`); `nebius` runs each check in a Token Factory Sandbox (about
  14 s a check against 6 s locally, measured by the evaluation session) and the pages say so.
* **A best-of-N episode** (`eval/agent/run.py --candidates`): nothing here changes; `episodes.py`
  follows `done.json`'s `chosen` to the candidate's files and the card says how many ran.
* **A repaired draft** (`provette/agent/prelint.py`): the step says "repaired before checking"
  with the fixes, and the draft view can show the file as the model wrote it.
* **A new word list, a new declared-rule shape, a new coverage technique**: nothing here; the
  pages read `/api/roles`, `/api/rules/sources` (shapes) and `/api/coverage` as data. A new
  shape needs its sentence in `web/src/pages/RuleForm.tsx` and its fields in `SHAPES` here.
* **Where the product writes** (a taught word, an added source, a declared rule, a failed-run
  record): `roles.yaml`, `sources.yaml` and `declared/` in the running checkout
  (`PROVETTE_ROLES_FILE`, `PROVETTE_SOURCES_FILE`, `PROVETTE_DECLARED_DIR` to move them; the tests
  use copies) and `<data>/outcomes.jsonl`. Every analysis runs in a fresh
  subprocess and its cache key digests those files, so a taught word is used at once.

## What it does not do

It does not run the model's draft in this process: every analysis is a subprocess with a timeout
(`worker.py`), and the live episode's checks run through `LocalRunner`, which is the same
subprocess path `eval/agent/run.py` uses. A draft runs with the container's privileges; the sandbox
runner (`provette.sandbox`) replaces `LocalRunner` when the account allows it, through the same
`Runner` contract, and nothing here changes.
