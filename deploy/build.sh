#!/bin/sh
# Build the product image locally, exactly as Fly builds it, and run its health check.
#
#   deploy/build.sh            # builds provette-api:dev
#   deploy/build.sh --run      # and starts it on localhost:8000 with a throwaway volume
set -eu
cd "$(dirname "$0")/.."
DOCKER=${DOCKER:-docker}
if ! $DOCKER info >/dev/null 2>&1; then DOCKER="sudo docker"; fi

# docker reads only the context root's .dockerignore, and that one belongs to the sandbox image
# (docker/Dockerfile). BuildKit reads <Dockerfile>.dockerignore next to the Dockerfile instead.
# --network=host: on some machines containers on the bridge network cannot reach the internet,
# and a build needs pip and npm. Fly builds remotely.
$DOCKER build --network=host -t provette-api:dev -f docker/api.Dockerfile \
  --build-arg "VITE_REPOSITORY=${PROVETTE_REPOSITORY_URL:-}" .

if [ "${1:-}" = "--run" ]; then
  $DOCKER rm -f provette-api >/dev/null 2>&1 || true
  $DOCKER run -d --name provette-api -p 8000:8000 -v provette-data-dev:/data provette-api:dev
  for _ in $(seq 1 30); do
    if curl -fsS http://127.0.0.1:8000/health 2>/dev/null; then echo; exit 0; fi
    sleep 1
  done
  echo "the container did not come up; docker logs provette-api" >&2
  exit 1
fi
