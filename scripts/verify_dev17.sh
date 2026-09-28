#!/usr/bin/env bash
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"

python3 -m compileall -q .

# The structural verifier expects a clean Legacy registration surface. Never let
# the operator's live ~/.hermes/nerve/profile.json change release verification.
VERIFY_HOME=$(mktemp -d)
(
  trap 'rm -rf "$VERIFY_HOME"' EXIT
  HERMES_HOME="$VERIFY_HOME" python3 scripts/verify_release.py
)

python3 scripts/verify_dev6_benchmark.py

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
export TMP
JOBS="${JEV_TEST_JOBS:-4}"

# Exact bounded-per-file pattern used for release verification. Keeping each
# pytest process independent avoids the known monolithic shutdown/background
# hang while still covering every in-repo test file.
printf '%s\n' tests/test_*.py | xargs -P "$JOBS" -I{} bash -c '
  f="$1"
  b=$(basename "$f" .py)
  PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 timeout 75s python3 -m pytest -q "$f" >"$TMP/$b.log" 2>&1
  rc=$?
  echo "$rc $f" >"$TMP/$b.rc"
' _ {} || true

failed=0
for rcfile in "$TMP"/*.rc; do
  rc=$(cut -d' ' -f1 "$rcfile")
  f=$(cut -d' ' -f2- "$rcfile")
  if [ "$rc" = 0 ]; then
    printf 'PASS %s\n' "$f"
  else
    printf 'FAIL %s rc=%s\n' "$f" "$rc"
    b=$(basename "$f" .py)
    tail -80 "$TMP/$b.log" || true
    failed=1
  fi
done

[ "$failed" -eq 0 ] || exit 1
printf 'DEV17_VERIFY=PASS\n'
