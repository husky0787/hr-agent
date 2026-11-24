#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="$ROOT:$ROOT/backend"

if [ ! -d "$ROOT/.venv" ]; then
  python3 -m venv "$ROOT/.venv"
  "$ROOT/.venv/bin/pip" install -r "$ROOT/backend/requirements.txt"
fi

exec "$ROOT/.venv/bin/uvicorn" app.main:app --reload --app-dir "$ROOT/backend" --host 0.0.0.0 --port "${PORT:-8000}"
