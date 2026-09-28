# The product's image: the API, the built pages, opentrons 8.8.2 and provette, one container.
#
#   deploy/build.sh --run                                    # builds and runs it on localhost:8000
#   docker build -t provette-api:dev -f docker/api.Dockerfile .
#   docker run --rm -p 8000:8000 -v provette-data:/data provette-api:dev
#   curl localhost:8000/health
#
# The build context is the repository root; docker/api.Dockerfile.dockerignore says what goes in. The
# sandbox image (docker/Dockerfile) is a different, smaller thing and stays as it is.
# Measured 2026-09-24 (deploy/README.md): 626 MB on disk, 115 MB compressed, built in 114 s,
# /health green 1.2 s after `docker run`.

# ---- stage 1: the pages ---------------------------------------------------------------------
FROM node:22-slim AS web
# The public repository's URL, for the footer's and About's link to the code (web/README.md);
# `--build-arg VITE_REPOSITORY=https://...`, which deploy/fly-up.sh and deploy/build.sh pass
# from PROVETTE_REPOSITORY_URL when it is set. Empty, the pages carry no link.
ARG VITE_REPOSITORY=
ENV VITE_REPOSITORY=$VITE_REPOSITORY
WORKDIR /web
COPY web/package.json web/package-lock.json* ./
RUN if [ -f package.json ]; then npm ci --no-audit --no-fund; fi
COPY web ./
RUN if [ -f package.json ]; then npm run build; else mkdir -p dist; fi

# ---- stage 2: the API -----------------------------------------------------------------------
FROM python:3.10-slim

# The image's own defaults. deploy/README.md is the one place that lists every setting; fly.toml
# sets only what depends on the machine. The three rules files point into the volume and are
# seeded from the shipped copies on the first boot (deploy/entrypoint.sh).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    OT_API_CONFIG_DIR=/tmp/ot \
    PROVETTE_DATA_DIR=/data \
    PROVETTE_EVAL_DIR=/srv/eval \
    PROVETTE_DOCS_DIR=/srv/docs \
    PROVETTE_WEB_DIR=/srv/web \
    PROVETTE_EXAMPLE_PROTOCOL=/srv/examples/pcr_buggy.py \
    PROVETTE_ROLES_FILE=/data/rules/roles.yaml \
    PROVETTE_SOURCES_FILE=/data/rules/sources.yaml \
    PROVETTE_DECLARED_DIR=/data/rules/declared \
    PORT=8000

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* && mkdir -p /tmp/ot /data /srv/eval /srv/web /srv/examples

WORKDIR /src
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY provette ./provette
COPY api ./api

# Exactly the versions uv.lock pins (the ones `make check` tested), exported by uv and installed
# by pip with their hashes; then the project itself. The opentrons pin is the project's
# (pyproject.toml, DECISIONS.md D-09); asserting it here means a drift in the lock fails the
# build instead of silently changing what the product runs.
RUN pip install "uv==0.12.9" \
    && uv export --frozen --no-dev --group api --no-emit-project -o /tmp/requirements.txt \
    && pip install --no-deps -r /tmp/requirements.txt \
    && pip install --no-deps . \
    && pip uninstall -y uv && rm /tmp/requirements.txt \
    && python -c "import opentrons, provette, api, fastapi, uvicorn; assert opentrons.__version__ == '8.8.2'"

# The evaluation: the pre-run episodes the gallery shows, the plate maps and requests they were
# run from, the prices, and the result files the methods page computes its numbers from.
COPY eval /srv/eval
COPY docs /srv/docs
COPY tests/fixtures/protocols/pcr_buggy.py /srv/examples/pcr_buggy.py
COPY --from=web /web/dist /srv/web
COPY deploy/entrypoint.sh /usr/local/bin/provette-entrypoint
RUN chmod +x /usr/local/bin/provette-entrypoint

EXPOSE 8000
# Docker's own check, for `docker run`; Fly uses [[http_service.checks]] in fly.toml instead.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD curl -fsS http://127.0.0.1:8000/health || exit 1
CMD ["provette-entrypoint"]
