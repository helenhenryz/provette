# Where the product runs, and what it costs

One container on Fly.io: the API, the built pages and the checker in one image, a small volume
for what the deployment keeps, and the model calls going out to Nebius Token Factory. Every
setting the deployment reads, what is in the image and what is on the volume are in
[`deploy/README.md`](../deploy/README.md); the decisions are D-34 to D-37.

## What the container needs

One always-on Python process: FastAPI, `opentrons==8.8.2` and `provette`, serving
the pages and running the checks as subprocesses. Measured with `/usr/bin/time -v`
on `provette verify` of the reference fixture:

| what | measured |
|---|---|
| `import opentrons.simulate` | 0.79 s |
| one `provette verify` (simulator, replay, report), wall clock | 1.1 s |
| peak memory of that run | 106 MB |
| installed site-packages (`opentrons`, `numpy`, the rest) | 176 MB |

So the image is about 500 MB, one check needs about 100 MB for a second, and
the API itself holds the simulator's imports (about 120 MB). A machine with 1 GB
of memory runs the API and three checks at once with room to spare; 2 GB is the
step up if the memory alert ever fires. The disk holds the pre-run episodes
(read-only, in the image) and the live ones (a small volume, under 1 GB for the
whole competition at about 500 KB per episode).

The other requirements: no sleep-on-idle (a demo that takes 30 s to wake is a bad
demo), a domain with TLS, a health check that restarts the process, survival of
a host reboot, and outbound HTTPS to `api.tokenfactory.nebius.com`, up unattended
through the judging.

## The choice: Fly.io, one Machine, one volume

**Cost: $6.07 a month**, billed to a card on our Fly.io account. Egress at $0.02/GB is noise (a gallery page is under
1 MB). If memory ever alerts, the 2 GB Machine is $11.11 a month; nothing else
changes.

Why Fly over the cheaper-per-gigabyte Hetzner VM: the deployment is one file
(`fly.toml`) and one command (`fly deploy`) from the same Dockerfile that builds
the image locally; TLS, the domain (`provette.fly.dev`), the health check and the
restart on failure are the platform's, not ours to operate; the whole state of
the deployment is in the repository, so either of us can redeploy it. Hetzner would be about the same price and needs
Docker, Caddy, a systemd unit and unattended upgrades written and watched by us;
it stays the fallback (the steps are at the end of this page). Oracle's free tier
reclaims idle instances, and a Nebius VM would cost $37 a month for the same
container; the model calls already run on Nebius Token Factory.

### What runs where

```
provette.fly.dev  ──TLS (Fly)──▶  Fly Machine, region ams (nearest to Token Factory)
                                  ├─ uvicorn: the API and the built web pages
                                  ├─ subprocesses: provette verify / check / view
                                  ├─ /data (1 GB volume): SQLite index, live episodes
                                  └─ outbound HTTPS ──▶ api.tokenfactory.nebius.com
```

* `docker/api.Dockerfile`: the image, built from the repository root. Stage one
  builds the web pages with Node; stage two is `python:3.10-slim` with exactly
  the versions `uv.lock` pins, `provette`, the API, the built pages, the example
  protocol and the whole `eval/` directory read-only (the gallery's episodes, the
  plate maps, the prices and the result files the methods page computes from).
  629 MB on disk, 115 MB compressed, `/health` green 1 s after `docker run`. **Every setting, what is in the image and what is on
  the volume, and the measurements the machine was sized from are in
  [`deploy/README.md`](../deploy/README.md).**
* `deploy/entrypoint.sh`: the container's first process. On the first boot it
  copies the word lists, the sources and the declared rules from the image to
  `/data/rules/` (only files that are missing), so what a student teaches or
  saves from the pages survives every redeploy; then it runs uvicorn as PID 1.
* `fly.toml`: `auto_stop_machines = "off"`, `min_machines_running = 1`, an HTTP
  check on `/health` every 15 s, the volume mounted at `/data`, 1 GB of memory
  and 512 MB of swap, one shared vCPU.
* Secrets: `PROVETTE_API_KEY`, `PROVETTE_BASE_URL`, `PROVETTE_JUDGE_PASSWORD` and, if
  set, `PROVETTE_DAILY_CAP_USD` are Fly secrets, staged by `deploy/fly-up.sh` from
  `~/.config/provette/*.env` and never printed; never in the image or the repository.
* `PROVETTE_RUNNER` in `fly.toml` says where a live draft's checks run: `local`
  (subprocesses in the container, about 6 s a check) or `nebius`, a Token Factory
  Sandbox (about 14 s a check).
  The episode page says which ran. `local` is what the script deploys, because it
  is faster and depends on nothing outside the Machine;
  `PROVETTE_RUNNER=nebius deploy/fly-up.sh` switches one deploy, the line in
  `fly.toml` switches for good (D-37).
* Reboot: a Fly Machine with `restart = "always"` comes back on its own after a
  crash or a host reboot. A Machine with a volume is pinned to the host that
  holds the volume; if that host is lost, Fly's daily volume snapshot (kept 5
  days) is restored to a new volume by `fly volumes create --snapshot-id`. The
  gallery needs no volume at all, so the demo survives even that with the live
  flow paused and the rules files back at the shipped versions.

### What you create or pay for

1. **A Fly.io account** at <https://fly.io/app/sign-up>, with a credit card on
   file (Billing, in the dashboard). Without the card Fly gives a 7-day trial
   whose machines stop after five minutes, which is not a deployment.
2. **A deploy token**, so a script can deploy without the owner's password: in the dashboard, or in a terminal where the owner has run
   `fly auth login`:

   ```
   fly tokens create org -o personal -x 2160h --name provette-ui
   ```

   `-o` names the organisation: `personal` for an account's own; `fly orgs list`
   prints it. Without it the command works only interactively, so redirecting its
   output into the file fails with "org slug argument must be specified". In one
   line, without the token ever reaching the screen, **quoted, because a Fly token
   holds a space** (`FlyV1 fm2_...`) and an unquoted value would run its second half
   as a command when the file is sourced:

   ```
   umask 077; printf "FLY_API_TOKEN='" > ~/.config/provette/fly.env; fly tokens create org -o personal -x 2160h --name provette-ui | tr -d '\n' >> ~/.config/provette/fly.env; printf "'\n" >> ~/.config/provette/fly.env
   ```

   A token that has been printed anywhere is revoked (`fly tokens list -o personal`,
   `fly tokens revoke <id>`) and made again.

   `deploy/fly-up.sh` reads the file itself and never prints it.
3. **A judge password**, any sentence, in `~/.config/provette/judge.env` as
   `PROVETTE_JUDGE_PASSWORD=...` (and `PROVETTE_DAILY_CAP_USD=...` on a second line
   to change the $2-a-day cap). It is what the run page asks for before a live
   run, a taught word or a saved rule.
4. **The Token Factory key**, in `~/.config/provette/token-factory.env` as
   `PROVETTE_API_KEY=...` and `PROVETTE_BASE_URL=https://api.tokenfactory.nebius.com/v1`.
   Nothing else: the app name `provette` and the region
   are set in `fly.toml`; the volume and the secrets are created by
   `deploy/fly-up.sh` the first time. A domain of our own is optional;
   `provette.fly.dev` has TLS already. If we want one, point its DNS at the app
   (`fly certs add`) or put it behind Cloudflare's free plan, and the doc gets a
   line.

Expected bill: $6.07 a month, prorated by the hour, on the card.

### Making it faster, for the judging

The everyday Machine is one shared CPU with 1 GB. A live run is mostly checks, and a check
replays the whole protocol in the simulator on one core, so on a shared CPU a run with several
repairs takes minutes. A dedicated CPU is what makes each check faster; more cores help when
several people run at once. The size changes in place, with no redeploy and about a minute's
restart, and Fly bills by the second, so the bigger Machine costs only while it is on:

```
deploy/fly-size.sh performance-1x   # before the judging: one dedicated CPU, 2 GB
deploy/fly-size.sh performance-2x   # if several judges run at once: two, 4 GB
deploy/fly-size.sh shared-cpu-1x    # after: back to the everyday Machine
deploy/fly-size.sh --show           # the size it runs at now
```

`fly.toml` names the size every deploy uses; for the judging it is `performance-2x` (D-36:
on the shared CPU the host throttled sustained checks until they timed out). After the judging,
run `fly-size.sh shared-cpu-1x` and set `fly.toml`'s `[[vm]]` back to `shared`, `1`, `"1gb"`, or
the next deploy moves it up again. `fly platform vm-sizes` lists every size, and Fly's
pricing page has what each costs.

### The checklist: from a token to a URL

Every command runs from the repository root, with `flyctl` installed (`~/.fly/bin`;
the scripts add it to `PATH`).

1. **The three files exist and hold what they should.** No values are printed.

   ```
   ls ~/.config/provette/fly.env ~/.config/provette/token-factory.env ~/.config/provette/judge.env
   grep -c '^FLY_API_TOKEN=' ~/.config/provette/fly.env        # 1
   grep -c '^PROVETTE_API_KEY=' ~/.config/provette/token-factory.env   # 1
   grep -c '^PROVETTE_JUDGE_PASSWORD=' ~/.config/provette/judge.env    # 1
   ```

2. **The gate and the image, locally.** `make check-all` must exit 0, and the image
   must build and pass the smoke test before Fly's builder sees it. About four minutes.

   ```
   make check-all; echo exit $?                 # exit 0
   deploy/build.sh --run                        # builds provette-api:dev, starts it on :8000, prints /health
   deploy/smoke.sh http://127.0.0.1:8000        # "smoke test passed", about 30 lines of "ok"
   docker rm -f provette-api
   ```

3. **Read what the deploy will do.** `--dry-run` needs no token and runs
   nothing; the secrets show as `<token-factory.env>` and `<judge.env>`.

   ```
   deploy/fly-up.sh --dry-run
   ```

   prints:

   ```
   app provette, region ams, org personal, volume provette_data (1 GB), url https://provette.fly.dev
   + fly apps list --json | grep -qi '"name": *"provette"' || fly apps create provette --org personal
   + fly volumes list -a provette --json | grep -qi '"name": *"provette_data"' || fly volumes create provette_data -a provette -r ams -s 1 -y
   + fly secrets set -a provette --stage PROVETTE_API_KEY=<token-factory.env> PROVETTE_BASE_URL=<token-factory.env> PROVETTE_JUDGE_PASSWORD=<judge.env>
   + fly deploy -a provette --ha=false --yes
   + fly status -a provette
   + deploy/smoke.sh https://provette.fly.dev
   deployed: https://provette.fly.dev
   ```

4. **Deploy.** The first run takes about five minutes (Fly's builder builds the
   image; later deploys reuse its layers). The script is idempotent: run it
   again after a commit and it skips what exists.

   ```
   deploy/fly-up.sh
   ```

   Expect: `fly apps create` says the app is created (if it says the name is
   taken, change `app = "provette"` in `fly.toml` to another name and run again;
   the URL follows the name); `fly volumes create` prints the volume's id;
   `secrets staged`; the build log, then `Machine ... update finished: success`
   and `fly status` showing one Machine `started` in `ams` with its checks
   `passing`; then the smoke test's lines ending in `smoke test passed` and
   `deployed: https://provette.fly.dev`. The Machine's log (`fly logs -a provette`)
   starts with four `seeded /data/rules/...` lines on the first boot and none
   after.

5. **Try it as a visitor**, in the browser: the gallery at
   `https://provette.fly.dev`, one episode, the check page with the example, and
   a live run with the judge password. `fly dashboard -a provette` shows the
   memory graph; it should sit around 70 MB and spike to about 300 MB during
   checks.

6. **Warm the cache, once** (optional, about four minutes): every episode's
   first visitor otherwise waits one to six seconds for its analysis.

   ```
   deploy/smoke.sh https://provette.fly.dev --warm
   ```

**To change the Token Factory key**, from the browser, with no rebuild: sign in at
<https://fly.io/dashboard>, open the app, go to **Secrets**, replace the value of
`PROVETTE_API_KEY` with the new key, and deploy the change when the dashboard offers it. The
Machine restarts on the same image in about fifteen seconds; the volume, the history and every
other setting stay. A live run that is going at that moment ends as failed, so change it when the
history shows nothing running. From a terminal, `fly secrets set -a provette PROVETTE_API_KEY=...`
does the same. Put the new key in `~/.config/provette/token-factory.env` as well, so the next
`deploy/fly-up.sh` does not set the old one back.

**After a commit:** `make check-all`, then `deploy/fly-up.sh` again. The volume
and the secrets stay; only the image changes. A deploy interrupts a live run in
flight (its page says it failed), so deploy when the run list is quiet.

**To roll back** to the previous image without a rebuild:

```
fly releases -a provette --image          # the releases, newest first, with their image references
fly deploy -a provette --image registry.fly.io/provette:deployment-<id-of-the-release-that-worked>
```

The volume is untouched by a rollback; a rule saved through the newer image's
form stays on it and the older image reads it like any other file. `fly status`
and `deploy/smoke.sh https://provette.fly.dev` say the rollback is up.

**To stop or remove it:** `deploy/fly-down.sh` scales to zero Machines (the volume
and the secrets stay, about $0.15 a month; `deploy/fly-up.sh` brings it back on
the same data); `deploy/fly-down.sh --destroy` deletes the app, the volume and
the secrets. Both take `--dry-run`.

**The smoke test** (`deploy/smoke.sh <url>`) is one list of requests, the same
against a local image and the deployment: `/health` (and that it says
`opentrons 8.8.2`), the episode list, one episode, its analysis (and that the
simulator passed and the replay has events), its replay page, the coverage,
rules, roles, declared rules, sources, evidence, documents, outcomes, plate
maps, the example protocol, the live status, the run list and one run record
when there is one, the pages `/`, `/examples`, `/rules`, `/check`, `/methods` and an
episode's deep link, a 404 for an unknown API path, and a `POST /api/checks` of
the example protocol with its plate map that must come back with findings (that
is the Opentrons simulator running in the deployment), then that check's record
and replay page. Exit 0 means every line said `ok`.

### The fallback: a Hetzner CX23 (or any VM)

If a VM is preferred: create the server (Ubuntu 24.04, an SSH
key, an IPv4), `apt install docker.io caddy`, `docker run -d --restart=always
-p 127.0.0.1:8000:8000 -v /srv/provette:/data --env-file /etc/provette.env
ghcr.io/<owner>/provette-api`, a `Caddyfile` of two lines (`provette.example.org {
reverse_proxy 127.0.0.1:8000 }`) for TLS, and a domain pointed at the IP. Docker's
restart policy and Caddy's systemd unit survive a reboot. Cost €5.99 a month
plus the domain.

## The stack behind the pages, in one paragraph

The API is FastAPI on Python 3.10, in the same process tree as `provette`, with
server-sent events for the live flow and SQLite for the episode index. The pages
are React with TypeScript, built by Vite into static files the API serves, so the
deployable is one container and the build is one command. React was chosen over
server-rendered templates because we wanted components with one job each and
rendering tests on frozen episode files, and that is what a component framework
gives; it was chosen over
smaller frameworks because it is the one the most people can extend. The bundle
stays small (no UI kit, no state library, CSS variables for the dozen tokens)
and the deck replay draws the same JSON that `provette view` exports.
