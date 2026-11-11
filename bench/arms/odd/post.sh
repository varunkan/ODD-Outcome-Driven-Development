#!/usr/bin/env bash
# Run after the session, in a copy of what it left: the gate takes the change out and puts it back, and that must
# never touch the copy that is graded. Its exit code is recorded as the arm's own check: 0 = the ODD gate passed.
# "Gate passed, hidden tests failed" is reported as its own figure.
# The gate is the pinned odd.py ($ODD_PY: the bench repository's HEAD copy), never the session's .odd/odd.py, which
# the agent could have edited; whether it did is written to $BENCH_POST_NOTES (run.py records it as arm_notes).
set -uo pipefail
if [ ! -f .odd/odd.py ]; then
    odd_py=missing
elif cmp -s .odd/odd.py "$ODD_PY"; then
    odd_py=same
else
    odd_py=differs
fi
if [ -n "${BENCH_POST_NOTES:-}" ]; then
    printf '{"odd_py": "%s"}\n' "$odd_py" > "$BENCH_POST_NOTES"
fi
python3 "$ODD_PY" gate --recompute --base main
