#!/bin/sh
# The demo's machine size on Fly.io, changed in place: no redeploy, about a minute's restart,
# billed by the second, so a bigger machine costs only while it is on. A check replays the whole
# protocol in the simulator on one core, so a dedicated CPU (performance-*) is what makes a live
# run faster; more cores help when several people run at once. docs/deploy.md has the sizes.
#
#   deploy/fly-size.sh performance-1x             one dedicated CPU, 2 GB: the size for judging
#   deploy/fly-size.sh shared-cpu-1x              back to the everyday machine (1 GB)
#   deploy/fly-size.sh performance-2x --dry-run   print the commands, run none (needs no token)
#   deploy/fly-size.sh --show                     the size it runs at now
#
# The memory follows the size (below) unless PROVETTE_MEMORY_MB is set. fly.toml's [[vm]] names
# the size every deploy/fly-up.sh uses (performance-2x for the judging, D-36): change it too, or
# the next deploy moves the machine back to it. It reads, if it exists, and never prints:
#   ~/.config/provette/fly.env   FLY_API_TOKEN='FlyV1 ...'
set -eu
cd "$(dirname "$0")/.."
export PATH="$HOME/.fly/bin:$PATH"

DRY=0
SHOW=0
SIZE=""
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY=1 ;;
    --show) SHOW=1 ;;
    -h | --help) sed -n '2,15p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*) echo "unknown argument: $arg (try --help)" >&2; exit 2 ;;
    *) SIZE=$arg ;;
  esac
done

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
APP=$(sed -n 's/^app = "\(.*\)"/\1/p' fly.toml)

say() { printf '%s\n' "$*"; }
run() { # run <command...>: print it, and run it unless this is a dry run
  say "+ $*"
  [ "$DRY" = 1 ] || "$@"
}
need_token() {
  [ "$DRY" = 1 ] && return 0
  if [ -z "${FLY_API_TOKEN:-}" ]; then
    echo "no FLY_API_TOKEN: put it in $CONFIG_DIR/fly.env (docs/deploy.md)" >&2
    exit 1
  fi
}

if [ "$SHOW" = 1 ]; then
  need_token
  run fly scale show -a "$APP"
  exit 0
fi

# the memory each size runs with: enough for the simulator and the pages, and what Fly gives the
# performance sizes anyway
case "$SIZE" in
  shared-cpu-1x) MB=1024 ;;
  shared-cpu-2x) MB=2048 ;;
  shared-cpu-4x) MB=2048 ;;
  performance-1x) MB=2048 ;;
  performance-2x) MB=4096 ;;
  performance-4x) MB=8192 ;;
  "") echo "which size? for example: deploy/fly-size.sh performance-1x (try --help)" >&2; exit 2 ;;
  *) echo "not a size this script knows: $SIZE (shared-cpu-1x, shared-cpu-2x, shared-cpu-4x, performance-1x, performance-2x, performance-4x)" >&2; exit 2 ;;
esac
MB=${PROVETTE_MEMORY_MB:-$MB}

need_token
say "app $APP: to $SIZE with $MB MB"
run fly scale vm "$SIZE" --vm-memory "$MB" -a "$APP"
run fly scale show -a "$APP"
say "done. The next deploy/fly-up.sh uses fly.toml's [[vm]] size: change it too to keep this one."
