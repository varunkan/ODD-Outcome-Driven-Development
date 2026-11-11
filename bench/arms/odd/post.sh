#!/usr/bin/env bash
# Run after the session, in a copy of what it left: the gate takes the change out and puts it back, and that must
# never touch the copy that is graded. Its exit code is recorded as the arm's own check: 0 = the ODD gate passed.
# "Gate passed, hidden tests failed" is reported as its own figure.
set -uo pipefail
python3 .odd/odd.py gate --recompute --base main
