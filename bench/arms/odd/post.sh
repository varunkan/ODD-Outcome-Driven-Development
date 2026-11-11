#!/usr/bin/env bash
# Run after the session, before the hidden tests are copied in. Its exit code is recorded as the arm's own check:
# 0 = the ODD gate passed on what the session left. "Gate passed, hidden tests failed" is reported as its own figure.
set -uo pipefail
python3 .odd/odd.py gate --recompute --base main
