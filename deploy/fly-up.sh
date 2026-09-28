#!/bin/sh
# The product on Fly.io: the first deployment, and every one after it. Idempotent: creates the
# app if it is missing, the volume if it is missing, stages the secrets, deploys, runs the smoke
# test against it, analyses every gallery episode once and prints the URL. deploy/README.md lists
# every setting; docs/deploy.md has the checklist around this script.
#
#   deploy/fly-up.sh              deploy
#   deploy/fly-up.sh --dry-run    print every command it would run, run none (needs no token)
#   PROVETTE_RUNNER=nebius deploy/fly-up.sh   this deploy runs live checks in Token Factory Sandboxes
#   PROVETTE_REPOSITORY_URL=https://... deploy/fly-up.sh   the pages carry this link to the code
#
# It reads, if they exist, and never prints:
#   ~/.config/provette/fly.env             FLY_API_TOKEN='FlyV1 ...'    (quoted: a Fly token holds a
#                                                                     space; docs/deploy.md says how)
#   ~/.config/provette/token-factory.env   PROVETTE_API_KEY=... PROVETTE_BASE_URL=...
#   ~/.config/provette/judge.env           PROVETTE_JUDGE_PASSWORD=...  [PROVETTE_DAILY_CAP_USD=2.00]
# A variable already in the environment wins over the files. PROVETTE_CONFIG_DIR moves the folder.
set -eu
cd "$(dirname "$0")/.."
export PATH="$HOME/.fly/bin:$PATH"

DRY=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY=1 ;;
    -h | --help) sed -n '2,17p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown argument: $arg (try --dry-run)" >&2; exit 2 ;;
  esac
done

# -- the settings ------------------------------------------------------------------------------
CONFIG_DIR=${PROVETTE_CONFIG_DIR:-$HOME/.config/provette}
load_env() { # load_env <file>: KEY=VALUE lines into the environment, never overriding what is set
  [ -f "$1" ] || return 0
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in '' | '#'*) continue ;; esac
    key=${line%%=*}
    value=${line#*=}
    value=${value#\"}; value=${value%\"}; value=${value#\'}; value=${value%\'}
    eval "current=\${$key:-}"
    [ -n "$current" ] || export "$key=$value"
  done <"$1"
}
load_env "$CONFIG_DIR/fly.env"
load_env "$CONFIG_DIR/token-factory.env"
load_env "$CONFIG_DIR/judge.env"

APP=$(sed -n 's/^app = "\(.*\)"/\1/p' fly.toml)
REGION=$(sed -n 's/^primary_region = "\(.*\)"/\1/p' fly.toml)
VOLUME=$(sed -n 's/^ *source = "\(.*\)"/\1/p' fly.toml)
VOLUME_GB=$(sed -n 's/^ *initial_size = "\([0-9]*\)gb"/\1/p' fly.toml)
ORG=${FLY_ORG:-personal}
URL="https://$APP.fly.dev"

missing=""
for name in FLY_API_TOKEN PROVETTE_API_KEY PROVETTE_BASE_URL PROVETTE_JUDGE_PASSWORD; do
  eval "value=\${$name:-}"
  [ -n "$value" ] || missing="$missing $name"
done
if [ -n "$missing" ]; then
  if [ "$DRY" = 1 ]; then
    echo "# dry run: not set (the real run stops here):$missing" >&2
  else
    echo "not set:$missing" >&2
    echo "put them in $CONFIG_DIR/{fly,token-factory,judge}.env (top of this script)" >&2
    exit 1
  fi
fi

# -- run or print -----------------------------------------------------------------------------
run() { # run <command...>: printed with a leading '+' in a dry run, executed otherwise
  if [ "$DRY" = 1 ]; then printf '+ %s\n' "$*"; else "$@"; fi
}
say() { printf '%s\n' "$*"; }

say "app $APP, region $REGION, org $ORG, volume $VOLUME (${VOLUME_GB:-1} GB), url $URL"

# 1. The app. Names are global on Fly: if the create says the name is taken, change `app` in
#    fly.toml (the URL follows it) and run again.
if [ "$DRY" = 1 ]; then
  say "+ fly apps list --json | grep -qi '\"name\": *\"$APP\"' || fly apps create $APP --org $ORG"
elif ! fly apps list --json | grep -qi "\"name\": *\"$APP\""; then
  fly apps create "$APP" --org "$ORG"
fi

# 2. The volume, in the primary region; fly.toml's [mounts] puts it at /data.
if [ "$DRY" = 1 ]; then
  say "+ fly volumes list -a $APP --json | grep -qi '\"name\": *\"$VOLUME\"' || fly volumes create $VOLUME -a $APP -r $REGION -s ${VOLUME_GB:-1} -y"
elif ! fly volumes list -a "$APP" --json | grep -qi "\"name\": *\"$VOLUME\""; then
  fly volumes create "$VOLUME" -a "$APP" -r "$REGION" -s "${VOLUME_GB:-1}" -y
fi

# 3. The secrets, staged: they take effect with the deploy below, not as a release of their own.
#    Values are never printed; a dry run shows where each comes from.
secret_args() {
  printf 'PROVETTE_API_KEY=%s PROVETTE_BASE_URL=%s PROVETTE_JUDGE_PASSWORD=%s' \
    "$1" "$2" "$3"
  [ -z "${PROVETTE_DAILY_CAP_USD:-}" ] || printf ' PROVETTE_DAILY_CAP_USD=%s' "$4"
}
if [ "$DRY" = 1 ]; then
  say "+ fly secrets set -a $APP --stage $(secret_args '<token-factory.env>' '<token-factory.env>' '<judge.env>' "${PROVETTE_DAILY_CAP_USD:-}")"
else
  # shellcheck disable=SC2046
  fly secrets set -a "$APP" --stage $(secret_args "$PROVETTE_API_KEY" "$PROVETTE_BASE_URL" \
    "$PROVETTE_JUDGE_PASSWORD" "${PROVETTE_DAILY_CAP_USD:-}") >/dev/null
  say "secrets staged"
fi

# 4. The deploy: Fly builds docker/api.Dockerfile on its builder, one Machine (--ha=false), the
#    strategy in fly.toml. PROVETTE_RUNNER in the environment overrides fly.toml's for this deploy;
#    PROVETTE_REPOSITORY_URL, when set, goes into the web build as VITE_REPOSITORY (the footer's
#    and About's link to the code); unset, the pages carry no link.
set -- fly deploy -a "$APP" --ha=false --yes
[ -z "${PROVETTE_RUNNER:-}" ] || set -- "$@" -e "PROVETTE_RUNNER=$PROVETTE_RUNNER"
[ -z "${PROVETTE_REPOSITORY_URL:-}" ] || set -- "$@" --build-arg "VITE_REPOSITORY=$PROVETTE_REPOSITORY_URL"
run "$@"

# 5. What came up, and the smoke test against the public URL.
run fly status -a "$APP"
run deploy/smoke.sh "$URL"
# every gallery episode analysed once, so no visitor waits for a first analysis (no model calls)
run python3 deploy/prewarm.py "$URL"
say "deployed: $URL"
