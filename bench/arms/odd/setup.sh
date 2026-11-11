#!/usr/bin/env bash
# ODD: `odd init` only. The method reaches the agent through AGENTS.md, exactly as it would in any tool that reads
# that file; no hooks, no extra prompt text. The task repositories have a `main` branch, so the work is done on a
# branch and measured against it.
set -euo pipefail
python3 "$ODD_PY" init >/dev/null
git checkout -q -b work 2>/dev/null || true
