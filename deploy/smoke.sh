#!/bin/sh
# The smoke test: the same requests that were verified against the image on this machine, run
# against a URL. Exit 0 when every one answers as expected; the first failure is printed.
#
#   deploy/smoke.sh https://provette.fly.dev            the reads, the pages, and one check
#   deploy/smoke.sh http://127.0.0.1:8000 --no-check  without POSTing a check
#   deploy/smoke.sh https://provette.fly.dev --warm     also analyse every gallery episode once, so
#                                                     the first visitor of each reads the cache
#
# Needs curl and python3. The check POSTs the example protocol with its plate map and expects
# findings back: that is the Opentrons simulator running in the deployment.
set -eu
URL=${1:?usage: deploy/smoke.sh <url> [--no-check] [--warm]}
URL=${URL%/}
shift
CHECK=1
WARM=0
for arg in "$@"; do
  case "$arg" in
    --no-check) CHECK=0 ;;
    --warm) WARM=1 ;;
    *) echo "unknown argument: $arg" >&2; exit 2 ;;
  esac
done
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
failed=0

expect() { # expect <path> <status> [<content-type substring>]
  path=$1; want=$2; type=${3:-}
  got=$(curl -sS -o "$TMP/body" -w '%{http_code} %{content_type} %{time_total}' "$URL$path" || echo "000 none 0")
  code=${got%% *}; rest=${got#* }; ctype=${rest% *}; secs=${rest##* }
  if [ "$code" = "$want" ] && { [ -z "$type" ] || case "$ctype" in *"$type"*) true ;; *) false ;; esac; }; then
    printf 'ok   %-60s %s %ss\n' "$path" "$code" "$secs"
  else
    printf 'FAIL %-60s got %s %s, wanted %s %s\n' "$path" "$code" "$ctype" "$want" "$type"
    failed=1
  fi
}

echo "smoke test against $URL"
expect /health 200 application/json
python3 -c "import json,sys; d=json.load(open('$TMP/body')); assert d['ok'] and d['opentrons']=='8.8.2', d; print('     opentrons', d['opentrons'], '| episodes', d['episodes'], '| live', d['live'], '| spent today \$', d['spent_today_usd'])"
expect /api/episodes 200 application/json
EPISODE=$(python3 -c "import json; d=json.load(open('$TMP/body')); rows=d.get('episodes', d if isinstance(d, list) else []); r=rows[0]; print(r['id'])")
expect "/api/episodes/$EPISODE" 200 application/json
expect "/api/episodes/$EPISODE/analysis" 200 application/json
python3 -c "import json; a=json.load(open('$TMP/body')); r=a.get('replay') or {}; print('     analysis of', '$EPISODE', '| simulator passed', a['simulator']['passed'], '| replay events', len(r.get('events', [])), '| findings', len((a.get('check') or {}).get('findings', [])))"
expect "/api/episodes/$EPISODE/replay.html" 200 text/html
expect "/api/coverage?technique=pcr" 200 application/json
expect /api/coverage/techniques 200 application/json
expect /api/rules 200 application/json
expect /api/roles 200 application/json
expect /api/rules/declared 200 application/json
expect /api/rules/sources 200 application/json
expect /api/evidence 200 application/json
expect /api/documents 200 application/json
expect /api/outcomes 200 application/json
expect /api/platemaps 200 application/json
expect /api/platemaps/pcr-01 200 application/json
expect /api/examples/protocol 200 application/json
expect /api/live 200 application/json
expect /api/runs 200 application/json
RUN=$(python3 -c "import json; d=json.load(open('$TMP/body')); rows=d.get('runs', []); print(rows[0]['run_id'] if rows else '')")
if [ -n "$RUN" ]; then
  expect "/api/runs/$RUN" 200 application/json
else
  echo "     no live run on this deployment yet (GET /api/runs/{id} not exercised)"
fi
expect / 200 text/html
expect /runs 200 text/html
expect /rules 200 text/html
expect /check 200 text/html
expect /methods 200 text/html
expect "/episodes/$EPISODE" 200 text/html
expect /api/no-such-route 404

if [ "$CHECK" = 1 ]; then
  curl -sS -o "$TMP/example" "$URL/api/examples/protocol"
  curl -sS -o "$TMP/map" "$URL/api/platemaps/pcr-01"
  python3 -c "import json; e=json.load(open('$TMP/example')); m=json.load(open('$TMP/map')); json.dump({'protocol': e['protocol'], 'platemap': m, 'name': e['name']}, open('$TMP/check.json', 'w'))"
  got=$(curl -sS -o "$TMP/body" -w '%{http_code} %{time_total}' -H 'content-type: application/json' --data-binary "@$TMP/check.json" "$URL/api/checks" || echo "000 0")
  code=${got%% *}; secs=${got##* }
  if [ "$code" = 200 ] && python3 -c "import json; a=json.load(open('$TMP/body'))['analysis']; assert a['simulator']['passed'], a['simulator']; f=a['check']['findings']; assert f, 'no findings on the buggy example'; print('     findings:', ', '.join(sorted({x['rule_id'] for x in f})))"; then
    printf 'ok   %-60s %s %ss\n' "POST /api/checks (the example, with its map)" "$code" "$secs"
    ID=$(python3 -c "import json; print(json.load(open('$TMP/body'))['id'])")
    expect "/api/checks/$ID" 200 application/json
    expect "/api/checks/$ID/replay.html" 200 text/html
  else
    printf 'FAIL %-60s got %s in %ss\n' "POST /api/checks" "$code" "$secs"
    failed=1
  fi
fi

if [ "$WARM" = 1 ]; then
  curl -sS -o "$TMP/episodes" "$URL/api/episodes"
  n=0
  for id in $(python3 -c "import json; d=json.load(open('$TMP/episodes')); print(' '.join(r['id'] for r in d.get('episodes', [])))"); do
    n=$((n + 1))
    got=$(curl -sS -o /dev/null -w '%{http_code} %{time_total}' "$URL/api/episodes/$id/analysis" || echo "000 0")
    case "$got" in 200*) ;; *) printf 'warm %s -> %s\n' "$id" "$got" ;; esac
  done
  echo "warmed $n episodes' analyses"
fi

if [ "$failed" = 0 ]; then echo "smoke test passed"; else echo "smoke test FAILED" >&2; exit 1; fi
