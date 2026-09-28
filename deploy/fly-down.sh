#!/bin/sh
# Take the product down on Fly.io. The opposite of deploy/fly-up.sh, in two strengths:
#
#   deploy/fly-down.sh              stop: scale to zero Machines. Compute billing stops; the volume
#                                   (the live runs, the taught words, the declared rules) and the
#                                   secrets stay, about $0.15 a month. deploy/fly-up.sh brings it back.
#   deploy/fly-down.sh --destroy    delete the app, its Machines, its volume and its secrets. The
#                                   URL stops working for everyone and the volume's data is gone;
#                                   Fly keeps its daily volume snapshots for 5 days after that.
#   deploy/fly-down.sh --dry-run    print the commands, run none (with or without --destroy)
#
# Reads FLY_API_TOKEN from ~/.config/provette/fly.env like fly-up.sh, and never prints it.
set -eu
cd "$(dirname "$0")/.."
export PATH="$HOME/.fly/bin:$PATH"

DRY=0
DESTROY=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY=1 ;;
    --destroy) DESTROY=1 ;;
    -h | --help) sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown argument: $arg (--destroy, --dry-run)" >&2; exit 2 ;;
  esac
done

CONFIG_DIR=${PROVETTE_CONFIG_DIR:-$HOME/.config/provette}
if [ -z "${FLY_API_TOKEN:-}" ] && [ -f "$CONFIG_DIR/fly.env" ]; then
  # the value is quoted in the file (a Fly token holds a space), either kind of quote
  FLY_API_TOKEN=$(sed -n 's/^FLY_API_TOKEN=//p' "$CONFIG_DIR/fly.env" | tr -d "\"'" | tail -1)
  export FLY_API_TOKEN
fi
if [ -z "${FLY_API_TOKEN:-}" ] && [ "$DRY" = 0 ]; then
  echo "FLY_API_TOKEN is not set (put it in $CONFIG_DIR/fly.env)" >&2
  exit 1
fi

APP=$(sed -n 's/^app = "\(.*\)"/\1/p' fly.toml)
run() { if [ "$DRY" = 1 ]; then printf '+ %s\n' "$*"; else "$@"; fi; }

if [ "$DESTROY" = 1 ]; then
  echo "destroying app $APP, its Machines, its volume and its secrets"
  run fly apps destroy "$APP" --yes
  echo "gone: https://$APP.fly.dev (snapshots of the volume: 5 days, 'fly volumes snapshots list')"
else
  echo "stopping app $APP: zero Machines, the volume and the secrets kept"
  run fly scale count 0 -a "$APP" --yes
  run fly status -a "$APP"
  echo "stopped; deploy/fly-up.sh brings it back on the same volume"
fi
