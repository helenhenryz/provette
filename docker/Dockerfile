# The image the sandbox runners execute: Python 3.10, opentrons 8.8.2 and provette, nothing else.
#
#   docker build -t provette-checks:dev -f docker/Dockerfile .
#   docker run --rm --network none -v "$PWD/work:/work" provette-checks:dev
#
# /work holds protocol.py and platemap.json; result.json is written next to them. The build
# context is the repository root, with .dockerignore keeping .cache, eval and the tests out.

FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    OT_API_CONFIG_DIR=/tmp/ot

WORKDIR /src
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY provette ./provette

# The pin is the project's (pyproject.toml, DECISIONS.md D-09); repeating it here means a drift
# in pyproject.toml fails the build instead of silently changing what the sandbox runs.
RUN pip install "opentrons==8.8.2" "pyyaml==6.0.3" && pip install --no-deps . \
    && python -c "import opentrons, provette; assert opentrons.__version__ == '8.8.2'" \
    && mkdir -p /tmp/ot /work

COPY docker/run_checks.py /usr/local/bin/run_checks.py

WORKDIR /work
ENTRYPOINT ["python", "/usr/local/bin/run_checks.py", "--work", "/work"]
