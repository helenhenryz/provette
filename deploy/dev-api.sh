#!/bin/sh
# The API for development, serving the built pages, on port 8765 (what web/vite.config.ts
# proxies to). `deploy/dev-api.sh stop` stops it. Logs go to .data/dev-api.log.
set -eu
cd "$(dirname "$0")/.."
mkdir -p .data
PID=.data/dev-api.pid
if [ "${1:-start}" = "stop" ]; then
  [ -f "$PID" ] && kill "$(cat "$PID")" 2>/dev/null && rm -f "$PID" && echo "stopped" || echo "not running"
  exit 0
fi
[ -f "$PID" ] && kill "$(cat "$PID")" 2>/dev/null && sleep 1 || true
PROVETTE_API_DOCS=1 PROVETTE_WEB_DIR="$PWD/web/dist" nohup env -u PYTHONPATH uv run uvicorn api.main:app --port 8765 \
  >.data/dev-api.log 2>&1 &
echo $! >"$PID"
for _ in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:8765/health >/dev/null 2>&1; then echo "up on http://127.0.0.1:8765"; exit 0; fi
  sleep 1
done
echo "did not come up; see .data/dev-api.log" >&2
exit 1
