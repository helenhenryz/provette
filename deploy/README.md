# `deploy/` — the product as one container, and every setting in one place

The product is one image (`docker/api.Dockerfile`: the API, the built pages, `opentrons` 8.8.2
and `provette`) run as one always-on Machine on Fly.io with one volume. [`docs/deploy.md`](../docs/deploy.md)
says why Fly and what it costs, and holds the checklist the owner runs; this page is the
reference: what is in the image, every setting, the secrets, what is kept where, and what the
machine was sized from.

```
deploy/fly-up.sh [--dry-run]         deploy (first time and every time); --dry-run prints the commands
deploy/fly-down.sh [--destroy]       stop the Machine (keep the volume); --destroy deletes everything
python3 deploy/prewarm.py <url>       analyse every gallery episode once on a deployment (fly-up.sh runs it; no model calls)
deploy/fly-size.sh <size> [--dry-run] the Machine's size, in place (performance-1x for judging, shared-cpu-1x after); --show prints it
deploy/smoke.sh <url> [--warm]       the smoke test against a URL; --warm analyses every episode once
deploy/build.sh [--run]              build the image here, exactly as Fly builds it; --run starts it
deploy/dev-api.sh [stop]             the API for development on :8765, no container
deploy/entrypoint.sh                 the container's first process: seed the volume, exec uvicorn
```

## What is in the image, and what is not

| in the image (read-only, rebuilt on every deploy) | on the volume at `/data` (survives a redeploy) |
|---|---|
| `provette/`, `api/`, the built pages (`/srv/web`) | `runs/`, `plans/`: the live episodes the deployment makes |
| `eval/` whole at `/srv/eval` (the 267 pre-run episodes, the plate maps, the requests, the prices, the result files the methods page computes from; `eval/checks/protocols` and the HTML replays left out) | `checks/`: every protocol checked at a shareable URL |
| `docs/` at `/srv/docs` (the rulebook and the guide the product renders) | `cache/`: one analysis per (checker, protocol, map), written the first time an episode is opened |
| `tests/fixtures/protocols/pcr_buggy.py` at `/srv/examples` (the "try this" protocol) | `spend.json`: the day's model spend against the cap; `outcomes.jsonl`: the failed-run records |
| the shipped `roles.yaml`, `sources.yaml`, `declared/*.yaml` under `/src/provette/rules` | `rules/roles.yaml`, `rules/sources.yaml`, `rules/declared/*.yaml`: **the files a student edits from the pages** |

The evaluation results are **baked at build**: `fly deploy` sends the repository (minus the
ignore file) to Fly's builder, so the gallery is in the image and needs nothing on the volume.
The deploy gets them from the checkout it runs in; a new result set is a commit and a deploy.

The three rules files are copied from the image to the volume by `deploy/entrypoint.sh` on the
first boot, file by file, **only when the file is missing**. After that the volume's copies are
the truth: a word taught on the pages, a source added, a rule saved through the form are on the
volume and survive every redeploy; a declared rule *added* to the repository later is seeded on
the next boot; one *edited* in the repository is not (the volume's copy wins). To push a
repository change over the volume's file: `fly ssh console -a provette -C "cp /src/provette/rules/roles.yaml /data/rules/roles.yaml"`
and restart, or delete the volume's file and restart so it is seeded again.

Every check runs in a fresh subprocess and reads the three files from wherever the settings
point (`provette.rules.roles`, `sources` and `declared` read their variables at import), and the
analysis cache key digests those files, so a taught word or a saved rule is used by the very
next check. Measured in the container: a rule saved through `POST /api/rules/declared`
appeared in `GET /api/rules` at once and in the findings of the next `POST /api/checks`.

## Every setting

`api/settings.py` reads these; nothing else reads the environment except `PORT` and the
`OT_API_CONFIG_DIR` the simulator wants. "checkout" is the default when nothing is set (what
`deploy/dev-api.sh` and the tests run with); "image" is the Dockerfile's `ENV`; "Fly" is what
`fly.toml` or a secret sets on top.

| setting | checkout default | image / Fly | what it does |
|---|---|---|---|
| `PROVETTE_DATA_DIR` | `.data` | `/data` (the volume) | everything the deployment writes: `runs/`, `plans/`, `checks/`, `cache/`, `spend.json`, `outcomes.jsonl`, `rules/` |
| `PROVETTE_EVAL_DIR` | `eval` | `/srv/eval` | the evaluation directory; the next five default to paths under it |
| `PROVETTE_EPISODES_DIR` | `<eval>/agent/results` | unchanged | the evaluation's episodes the gallery shows |
| `PROVETTE_GALLERY_SETS` | the four sets named in `settings.py` | unchanged | which result sets under it the gallery and the methods page show, comma-separated |
| `PROVETTE_PLATEMAPS_DIR` | `<eval>/platemaps` | unchanged | the hand-written plate maps of the request set |
| `PROVETTE_REQUESTS_FILE` | `<eval>/requests/requests.jsonl` | unchanged | the requests (id, technique, request); `eval/requests-*` directories are found beside it |
| `PROVETTE_PRICES_FILE` | `<eval>/prices.json` | unchanged | list prices per model, for the cost figures |
| `PROVETTE_DOCS_DIR` | `docs` | `/srv/docs` | the documents the product renders (the rulebook and what it links to) |
| `PROVETTE_WEB_DIR` | unset (API only) | `/srv/web` | the built pages to serve; unset, only `/api` and `/health` answer |
| `PROVETTE_COVERAGE_FILE` | `provette/rules/coverage.yaml` | unchanged (in the package) | what the checks cover per technique |
| `PROVETTE_ROLES_FILE` | `provette/rules/roles.yaml` | `/data/rules/roles.yaml`, seeded | the word lists a taught word is written to |
| `PROVETTE_SOURCES_FILE` | `provette/rules/sources.yaml` | `/data/rules/sources.yaml`, seeded | the sources an added source is written to |
| `PROVETTE_DECLARED_DIR` | `provette/rules/declared` | `/data/rules/declared`, seeded | where the form saves a declared rule, and where the rules are loaded from |
| `PROVETTE_EXAMPLE_PROTOCOL` | `tests/fixtures/protocols/pcr_buggy.py` | `/srv/examples/pcr_buggy.py` | the protocol the check page offers to try (the tests are not in the image) |
| `PROVETTE_API_KEY` | empty: live flow off | **secret** | the Token Factory key |
| `PROVETTE_BASE_URL` | empty: live flow off | **secret** | the Token Factory endpoint |
| `PROVETTE_JUDGE_PASSWORD` | empty: every write off | **secret** | the password in front of every write (below) |
| `PROVETTE_DAILY_CAP_USD` | `2.00` | secret, only if set in `judge.env` | the day's spend cap for live episodes (below) |
| `PROVETTE_RUNNER` | `local` | `fly.toml`: `local` | where a live draft's checks run (below) |
| `PROVETTE_API_DOCS` | unset (off) | unset (off) | `1` serves FastAPI's route documentation at `/api/docs`; the dev server sets it, the deployment does not list its routes to anyone |
| `PROVETTE_ANALYSES_AT_ONCE` | `2` | `fly.toml`: `2` | simulator subprocesses at once, process-wide (below, "CPU and memory") |
| `PROVETTE_SANDBOX_PROJECT` | discovered from the key | unset | the Token Factory project id for the `nebius` runner |
| `PORT` | `8000` | `8000` | what uvicorn listens on; `fly.toml`'s `internal_port` must match |
| `PROVETTE_REPOSITORY_URL` | unset: no link | unset; `fly-up.sh` and `build.sh` pass it to the web build as `VITE_REPOSITORY` | the public repository's URL, read at **build** time, not by the API: the footer's and About's link to the code. Set it once the public repository exists |

## The secrets, and how `fly-up.sh` sets them

Four values never enter the image or the repository. `deploy/fly-up.sh` reads them from files
under `~/.config/provette/` (`PROVETTE_CONFIG_DIR` moves the folder), a variable already in the
environment winning over a file, and passes them to `fly secrets set --stage`, which stores
them encrypted on the app; they reach the Machine as environment variables with the next
deploy. The script never echoes a value; `--dry-run` prints `PROVETTE_API_KEY=<token-factory.env>`
in place of it.

| file | holds | made by |
|---|---|---|
| `fly.env` | `FLY_API_TOKEN='FlyV1 ...'` (quoted: the token holds a space) | the owner, from `fly tokens create org -o personal -x 2160h --name provette-ui` (`docs/deploy.md` has the one-liner) |
| `token-factory.env` | `PROVETTE_API_KEY=...`, `PROVETTE_BASE_URL=...` | exists already (the evaluation's key) |
| `judge.env` | `PROVETTE_JUDGE_PASSWORD=...`, optionally `PROVETTE_DAILY_CAP_USD=...` | the owner: any sentence; it is typed into the run page |

`FLY_ORG` (default `personal`) names the organisation the app is created in.

## The judge password: every write goes through it

The pages read without any credential. Anything that writes on a person's behalf sends the
`X-Judge-Password` header and `api/auth.py` compares it in constant time: a live plan or run
(`POST /api/plan`, `/api/plans`, `/api/runs`), a taught word (`POST /api/roles/{list}`), an
added source (`POST /api/rules/sources`), a saved rule (`POST /api/rules/declared`), a failed-run
record (`POST /api/outcomes`). Without the header or with the wrong one: 401; with no password
set on the deployment: 503 and a sentence. Two routes
write without it and are bounded instead: `POST /api/checks` (a protocol checked at a shareable
URL; 20 a minute per address) and `POST /api/rules/preview` (20 a minute per address, and the
simulation slots).

## The daily cap

`PROVETTE_DAILY_CAP_USD` (default $2.00) is the most the live flow spends per UTC day, kept in
`spend.json` on the volume from the model's usage fields at list prices (`api/ledger.py`).
A plan is estimated at $0.01 and a run at $0.10 before it starts; when the day's total plus the
estimate is over the cap the route answers 503 with the sentence the page shows, and the flow
comes back at midnight UTC. `/health` reports `spent_today_usd`. A run costs a few cents
(`eval/agent/README.md`), so $2 is dozens of runs a day: enough for a demo, small enough that a loop
cannot run up a bill.
The demo at <https://provette.fly.dev> sets it to $20.00 for the judging period, so several judges
can run it on the same day.

## The runner for the live flow

`PROVETTE_RUNNER` says where a live draft's four check commands run:

* **`local` (what `fly.toml` sets)**: subprocesses in the container, about 6 s a check,
  no network, no other service. It is the default because it is the fastest and the only one
  with no dependency outside the Machine: the demo does not stop if a beta service does.
* **`nebius`**: one disposable Token Factory Sandbox per check (`provette/sandbox/README.md`):
  about 14 s a check, five at once in the time of one; needs `PROVETTE_API_KEY`'s project to have
  the sandbox grant (`provette/sandbox/README.md`) and outbound HTTPS to `api.tokenfactory.nebius.com`
  and `api.nebius.cloud`, which a Fly Machine has. The episode page says the checks ran in a
  sandbox. `PROVETTE_RUNNER=nebius deploy/fly-up.sh` uses it for one deploy (`fly deploy -e`);
  to switch for good, change the line in `fly.toml`.
* `docker` is for a machine with Docker and the sandbox image built; not for Fly.

The choice of runner does not change the memory sizing much: a local check is one simulator
subprocess at a time per run (about 110 to 140 MB), a sandbox check is a few HTTP calls.

## Logging

uvicorn writes its access log and errors to stdout; Fly keeps them (`fly logs -a provette`, or the
dashboard). The entrypoint logs each file it seeds. The subprocesses' stderr is captured and the
last line is what a 503 says. Nothing is written to the volume as a log; a live run's own
files (`transcript.jsonl`, `events.jsonl`, `log.jsonl`) are under `runs/<id>/`.

## The health route

`GET /health` answers `{"ok": true, "opentrons": "8.8.2", "provette": ..., "episodes": 267,
"live": bool, "spent_today_usd": ...}` once the process is up and the simulator imports.
`fly.toml` polls it every 15 s with a 5 s timeout after a 30 s grace period and restarts the
Machine when it fails (`[[restart]] policy = "always"` covers a crash and a host reboot).
The Dockerfile's `HEALTHCHECK` is the same request for `docker run`; Fly ignores it.

## What would break on Fly and not locally, and what was done about it

Measured with the image, run with `docker run --memory=1g`
and a fresh volume; the container's cgroup `memory.peak` is the figure.

| what | measured | consequence |
|---|---|---|
| image | 629 MB on disk, 115 MB compressed; built in 114 to 142 s | Fly's builder does the same build; the first deploy takes a few minutes |
| cold start, `docker run` to `/health` 200 | 0.9 to 1.2 s | `grace_period = "30s"` is generous; a restart is invisible |
| the process, idle, with the simulator imported | 62 to 68 MB | |
| one analysis of a large episode (3,746 events, 291 wells) | container peak 208 MB (the worker about 140 MB), 4.6 s in the worker, 5.9 s at the route | a 3,000-event replay is not a memory problem |
| `POST /api/checks` on the reference protocol | 1.3 to 2.2 s, peak 222 MB | |
| three uncached analyses at once on two slots | all three in 5.0 s, peak 272 MB | the third waited for a slot; nobody was refused |

**Memory.** The worst plausible moment is two simulator subprocesses (the slots) beside two
live runs each in a `provette verify` subprocess: 68 + 2 × 140 + 2 × 140 = about 630 MB, under the
1 GB Machine (`[[vm]] memory = "1gb"`) with 512 MB of swap behind it (`swap_size_mb`). That is
why `PROVETTE_ANALYSES_AT_ONCE` is 2 and `MAX_RUNS_AT_ONCE` (`api/live.py`) is 2. A 2 GB Machine is
`memory = "2gb"` and $11.11 a month if the memory graph ever says so.

**CPU.** `shared-cpu-1x` is one shared vCPU. A check is CPU-bound for a few seconds; two at once
each take about twice as long, which the numbers above show (2.8 s each for two small episodes
in parallel against 1.6 s alone). The bound on simulator subprocesses is one semaphore for the
whole process (`api.analysis.slot`): a check, an episode's first analysis and a rule preview all
take a slot; a request waits up to 30 s for one and is then told to try again (503). Per address,
checks and previews are 20 a minute, plans 6 and runs 3 in ten minutes (`api/limits.py`, keyed by
`Fly-Client-IP`, which Fly's proxy sets).

**The proxy's 60 seconds.** Fly's proxy closes a connection after 60 s with no bytes on it
("We close connections after 60s of inactivity", Jerome from Fly.io, community.fly.io/t/5369);
bytes keep it open. The two streaming routes (`/api/runs/{id}/events`, `/api/plans/{id}/events`)
send a snapshot when the run's files change and a `: keep-alive` comment every 0.5 s otherwise,
so a 46-second episode streams to the page; verified in the container: the first snapshot
arrives at once. A plain check answers in one response; the largest episode takes 6 s and the
slot wait is at most 30 s, so the sum stays under 60 s. The worker's own limit is 180 s: a
protocol that took longer than 60 s would be cut by the proxy, finish on the server, land in the
cache, and the same request a second time would answer from the cache at once. No measured
protocol comes near it.

**Disk.** The volume is 1 GB: an episode is about 500 KB, a check about 3 MB when its replay is
large, the whole gallery's cache about 50 MB. `fly volumes extend` grows it without a redeploy.

**Root.** The process runs as root inside the Machine, as the Dockerfile builds it; Fly mounts
the volume root-owned, and a draft protocol runs with the container's privileges in a subprocess
(the `nebius` runner is the answer when that matters, `api/README.md`).

**Versions.** The image installs exactly what `uv.lock` pins (`uv export` at build, `pip install`
with hashes), so the container runs the versions `make check` tested; an unpinned install
drifts (starlette 1.7.0 against the lock's 1.6.0).
