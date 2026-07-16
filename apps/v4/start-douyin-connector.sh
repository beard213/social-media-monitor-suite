#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
PYTHON_BIN="${PYTHON_BIN:-}"
if [[ -z "$PYTHON_BIN" ]]; then
  if [[ -x .venv/bin/python ]]; then PYTHON_BIN=.venv/bin/python
  elif command -v python3 >/dev/null 2>&1; then PYTHON_BIN=python3
  else PYTHON_BIN=python
  fi
fi
export PYTHONPATH="${PYTHONPATH:-.}"
export CONNECTOR_PLATFORM=douyin
exec "$PYTHON_BIN" -m uvicorn connector_service.main:app --host 0.0.0.0 --port "${DOUYIN_CONNECTOR_PORT:-9001}"
