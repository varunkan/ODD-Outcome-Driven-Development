#!/usr/bin/env bash
# Run after the session, in a copy of what it left: `odd check` from the pinned odd.py ($ODD_PY), never the copy the
# session could have edited. Its exit code is recorded as the arm's own check: 0 = shown, or no test to check.
set -uo pipefail
python3 "$ODD_PY" check --base main
