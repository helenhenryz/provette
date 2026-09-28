#!/bin/sh
# The container's first process (docker/api.Dockerfile): seed the volume, then run the API.
#
# The files a student edits from the pages (the word lists, the sources, the declared rules)
# live on the volume so they survive a redeploy: PROVETTE_ROLES_FILE, PROVETTE_SOURCES_FILE and
# PROVETTE_DECLARED_DIR point into PROVETTE_DATA_DIR. On the first boot they do not exist yet, so
# each one that is missing is copied from the files shipped in the image; a file that exists is
# never touched (the volume is the truth after the first boot; deploy/README.md says how to
# push a change from the repository over it). A shipped declared rule that is new since the
# volume was seeded is added, one that was edited in the repository is not.
set -eu

SHIPPED=/src/provette/rules

seed_file() { # seed_file <shipped> <live>
  if [ -n "$2" ] && [ ! -f "$2" ]; then
    mkdir -p "$(dirname "$2")"
    cp "$1" "$2"
    echo "seeded $2 from $1"
  fi
}

mkdir -p "${PROVETTE_DATA_DIR:-/data}"
seed_file "$SHIPPED/roles.yaml" "${PROVETTE_ROLES_FILE:-}"
seed_file "$SHIPPED/sources.yaml" "${PROVETTE_SOURCES_FILE:-}"
if [ -n "${PROVETTE_DECLARED_DIR:-}" ]; then
  mkdir -p "$PROVETTE_DECLARED_DIR"
  for f in "$SHIPPED"/declared/*.yaml; do
    seed_file "$f" "$PROVETTE_DECLARED_DIR/$(basename "$f")"
  done
fi

# exec: uvicorn is PID 1, so the platform's stop signal reaches it and the shutdown is clean.
exec uvicorn api.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers \
  --forwarded-allow-ips '*' --no-server-header
