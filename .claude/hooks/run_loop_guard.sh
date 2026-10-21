#!/bin/sh
# Runs loop_guard.py with the project interpreter (.venv, Python 3.12).
#
# Only loop_guard.py itself may block a tool call (exit 2). Setup problems — no .venv yet,
# a missing script — must never block: they are reported on stderr and the call is allowed.
# (A bare `python3 missing.py` exits with 2, which Claude Code would treat as a block.)
ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd)
PY="$ROOT/.venv/bin/python"
SCRIPT="$ROOT/.claude/hooks/loop_guard.py"

if [ ! -x "$PY" ] || [ ! -f "$SCRIPT" ]; then
  echo "loop-guard: skipped, $PY or $SCRIPT not found (run 'make install')" >&2
  exit 0
fi
exec "$PY" "$SCRIPT" "$@"
