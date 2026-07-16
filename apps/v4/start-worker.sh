#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p data/storage data/logs run_logs
PYTHON_BIN="${PYTHON_BIN:-}"
if [[ -z "$PYTHON_BIN" ]]; then
  if [[ -x .venv/bin/python ]]; then PYTHON_BIN=.venv/bin/python;
  elif command -v python3 >/dev/null 2>&1; then PYTHON_BIN=python3;
  else PYTHON_BIN=python;
  fi
fi
export PYTHONPATH="${PYTHONPATH:-.}"
"$PYTHON_BIN" -m app.init_db
exec "$PYTHON_BIN" -m app.worker
