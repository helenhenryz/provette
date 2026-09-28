# `make check` is the gate before a push. There is no hosted CI (decided 2026-09-21): it runs
# here, and `make hooks` makes git run it before every push.
# READ THE EXIT CODE. Never grep its output and never pipe it to `tail`.

# A machine with ROS sourced puts its pytest plugins on PYTHONPATH, and they break collection.
unexport PYTHONPATH

.PHONY: check check-web check-all lint types test sync hooks web-fixtures

# `check` is the Python gate the pre-push hook runs; it never depends on node or npm state.
# `check-all` adds the pages; run it before a push that touches web/ or api/.
check: lint types test

check-all: check check-web

sync:
	uv sync

lint: sync
	uv run ruff check .
	uv run ruff format --check .

types: sync
	uv run mypy

test: sync
	uv run pytest -n auto

# The product's pages (web/): lint, type-check, build and the rendering tests. Needs node 22.
check-web:
	cd web && npm ci --no-audit --no-fund --silent && npm run lint --silent && npm run build --silent && npx vitest run --silent

# Refresh the frozen API answers the web tests render (the API must not be needed to run them).
web-fixtures:
	uv run python -m api.fixtures tests/web/fixtures

hooks:
	printf '#!/bin/sh\nexec make check\n' > .git/hooks/pre-push
	chmod +x .git/hooks/pre-push
