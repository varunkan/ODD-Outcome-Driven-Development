#!/usr/bin/env bash
# ODD: `odd init` only. The method reaches the agent through AGENTS.md, exactly as it would in any tool that reads
# that file; no hooks, no extra prompt text. No branch is made here: the runner puts every arm on `work`.
set -euo pipefail
python3 "$ODD_PY" init >/dev/null
