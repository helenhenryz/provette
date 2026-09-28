# The sandbox runners

Where a draft protocol is run so the agent loop can read the result. Three
runners share the contract in [`provette/agent/runner.py`](../agent/runner.py):
`run_checks(protocol_text, platemap_json) -> dict`, the dict being what
`judge` in `eval/baseline/run.py` computes (`provette verify`, then `provette check`,
text and JSON, exit codes 0/1/2/3). The loop does not know which one it has.

| name | where the checks run | what it needs |
|---|---|---|
| `local` | this machine, in-process (`provette.agent.local_runner`, built by the agent-loop work) | the project's own venv |
| `docker` | a local container from `docker/Dockerfile`, no network, 300 s limit | Docker, and the image built |
| `nebius` | a Nebius Token Factory Sandbox, one disposable instance per run | the Token Factory key, and sandbox access on the project |

```python
from provette.sandbox import make_runner

runner = make_runner("nebius")
result = runner.run_checks(protocol_text, platemap_json)
runner.close()
```

All three run the same code: [`entrypoint.py`](entrypoint.py) reads
`protocol.py` and `platemap.json` from a work folder, runs the four commands
as subprocesses, writes `result.json`, and with `--print` prints it. The
tests run it in-process; the image and the sandbox run it as
`python -m provette.sandbox.entrypoint --work /work --print`.

## The image

`docker/Dockerfile`: `python:3.10-slim`, `opentrons==8.8.2` pinned a second
time (a drift in `pyproject.toml` fails the build rather than changing what
the sandbox runs), the package installed from the repository, `OT_API_CONFIG_DIR=/tmp/ot`.
The build context is the repository root; `.dockerignore` lets in only
`pyproject.toml`, `uv.lock`, `README.md`, `LICENSE`, `provette/` and
`docker/run_checks.py`, so `.cache/`, `eval/`, `.venv/` and the tests never
enter the image.

```
docker build -t provette-checks:dev -f docker/Dockerfile .
docker run --rm --network none -v "$PWD/work:/work" provette-checks:dev
```

**Not built here.** The machine this was written on has no Docker (no
binary, no socket, no service), so the image has not been built and
`DockerRunner` has not been run. Its tests carry the `docker` marker and
skip unless `docker info` succeeds and the image exists. The image size and
the container's run time are unmeasured; the in-process entrypoint is the
only measured number below. Build it on a machine with Docker and write the
size here.

## The Nebius sandbox: how it authenticates

Read from the official documentation and the `contree-sdk` 0.3.6 source, then
checked against the service.

* The API is `https://api.tokenfactory.nebius.com/sandboxes/v1`. Every call
  needs `Authorization: Bearer <key>` **and** a `Project: <id>` header; without
  the header the service answers `400 Missing "Project" header`.
* The bearer is the project's Token Factory key as it is (`PROVETTE_API_KEY`). It is a
  Nebius IAM static key on a service account; it does not need exchanging.
* The project id is not in the key and not shown by any Token Factory
  endpoint we found. It is the service account's parent: `GET
  https://api.nebius.cloud/iam/v1/profiles` with the same key returns
  `serviceAccountProfile.info.metadata.parentId` (`aiproject-…`). The runner
  asks for it at start-up (0.5 s); `PROVETTE_SANDBOX_PROJECT` overrides.
* Cloudflare in front of `api.nebius.cloud` answers `403 error code: 1010`
  to Python's default `User-Agent`; the runner sends `provette-sandbox/0.1`.
* The runner uses the standard library only. The SDK (`pip install
  contree-sdk`, `ContreeSync`, `images.oci`, `image.run(...).wait()`) exists
  and matches the earlier notes, but adding it would mean a new dependency
  in `pyproject.toml`; the six REST calls it makes are short enough to write.

## Access: the sandbox grant

Sandboxes are in beta, and a project needs the grant: without it `GET /whoami` answers with
every permission false and every real call `403 Insufficient permissions`, although the key
authenticates. With it, `PROVETTE_NETWORK=1 uv run pytest tests/sandbox/test_nebius_runner.py`
passes. The limits `whoami` states: instance_max_timeout 3600 s, instance_max_concurrency 50,
instance_max_layer_bytes 12 GiB, images_import_max_concurrency 8.

## The Nebius image: how it is made and reused

Nothing of ours is published anywhere. The runner:

1. Asks for `tag:provette-checks:<hash>`, the hash being 12 hex characters of
   the package source it would install (`pyproject.toml`, `uv.lock`,
   `README.md`, `LICENSE`, `provette/**`, deterministic: fixed mtimes, sorted).
   If it exists, that is the image. A change to any file gives a new tag.
2. Otherwise imports `python:3.10-slim` from Docker Hub (the service pulls
   public images itself), uploads the source as one tar.gz (149 KB) with
   `files=`, and in one **non-disposable** run does `pip install
   opentrons==8.8.2` and `pip install --no-deps ./src`, asserts the version,
   and cleans up. Networking is on by default in a sandbox, so pip reaches
   PyPI.
3. Tags the resulting image `provette-checks:<hash>` (tags are unique across
   images; retagging moves the tag) and appends a line to
   `~/.config/provette/sandbox-image.txt`. The tag is what keeps the image
   findable; the documentation says checkpoint images are kept 180 days.

Each `run_checks` is one disposable instance: two uploads (deduplicated by
SHA-256 on the server), one `POST /instances`, polling `GET
/operations/{id}` from 0.5 s backing off to 5 s, the entrypoint's stdout
parsed as JSON. Nothing is kept.

## Measured numbers

| what | number | where |
|---|---|---|
| entrypoint, `pcr_buggy.py` with `pcr-01.json`, in-process | **5.7 s** (four simulator runs) | this machine |
| source tarball uploaded per build | 149 KB | `package_tarball()` |
| project discovery (IAM profiles) | 0.5 s | `discover_project()` |
| Nebius image, second use (tagged, found by digest) | 0.7 s to be ready | `make_runner("nebius")` |
| Nebius one `run_checks`, round trip | **14.4 s** (9.5 s inside the sandbox) | `runner.last` |
| Nebius 5 `run_checks` at once | **11.6 s** for all five | a thread pool |
| max_rss reported by a run | 110,744 (the unit is undocumented) | `runner.last` |
| `cost` reported by a run | 0.0956 per run (the unit is undocumented) | `runner.last` |
| image size (Docker) | not measured: Docker needs a group change on this machine | |

So a check in a sandbox costs about 8 seconds over running it here, and five run in the
time of one; that is what best-of-N candidates are for. `eval/agent/run.py --runner sandbox`
uses it.

## D-35: what a sandbox allows, from the service

* **Lifetime:** up to 3600 s a run; the runner asks for 300.
* **Concurrency:** 50 instances at once, 8 imports at once; five at once measured.
* **Disk:** the writable layer is capped at 12 GiB.
* **CPU and memory:** still stated nowhere; a run reports `max_rss` and CPU times.
* **Billing:** each run reports `cost` (0.0956 for one check); whether and how it is
  charged is not documented. The email granting access said nothing about price.
* **Network:** on by default per the documentation and the REST schema; the image build
  (`pip install` inside the sandbox) worked, which needs it.

## Known gaps

* No Docker on this machine: the image is unbuilt and `DockerRunner` unrun.
* No sandbox grant on the key: `NebiusRunner` is written against the
  documented and source-read API and has been exercised up to the first
  refused call; the build, run, latency and concurrency paths have not run.
* `verify` in the result is the full `provette verify --json`, which for a
  96-well plate can be tens of kilobytes; the sandbox's stdout is capped at
  10 MiB per stream, which is plenty, and `truncated` is not yet checked.
* The result's `findings` carry seven keys (`rule_id`, `severity`,
  `certain`, `line`, `title`, `explanation`, `fix`), as the contract names;
  `judge` in `eval/baseline/run.py` keeps five.
