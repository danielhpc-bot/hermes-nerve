#!/usr/bin/env bash
set -eu

PROFILE="${1:-abtest-nerve-dev17}"
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
DEST="$HOME/.hermes/profiles/$PROFILE/plugins/hermes-nerve"
LEGACY="$HOME/.hermes/profiles/$PROFILE/plugins/hermes-jev"
STAMP=$(date +%Y%m%dT%H%M%S)

if ! hermes profile show "$PROFILE" >/dev/null 2>&1; then
  echo "Error: Hermes profile '$PROFILE' does not exist." >&2
  echo "Create it first, for example:" >&2
  echo "  hermes profile create $PROFILE --clone-from default --description \"Paperclip Nerve builder\"" >&2
  exit 2
fi

mkdir -p "$(dirname "$DEST")"
if [ -e "$LEGACY" ]; then
  LEGACY_BACKUP="${LEGACY}.pre-nerve-${STAMP}"
  mv "$LEGACY" "$LEGACY_BACKUP"
  echo "Legacy Hermes-Jev plugin preserved at: $LEGACY_BACKUP"
  hermes -p "$PROFILE" plugins disable hermes-jev >/dev/null 2>&1 || true
fi
if [ -e "$DEST" ]; then
  BACKUP="${DEST}.pre-dev17-${STAMP}"
  mv "$DEST" "$BACKUP"
  echo "Existing plugin preserved at: $BACKUP"
fi
mkdir -p "$DEST"
cp -a "$ROOT"/. "$DEST"/
rm -rf "$DEST/.pytest_cache" "$DEST/__pycache__"

hermes -p "$PROFILE" plugins enable nerve
printf 'Installed Nerve %s into %s\n' "$(python3 -c "import sys; sys.path.insert(0, '$DEST'); from hermes_nerve.provenance import VERSION; print(VERSION)")" "$DEST"
