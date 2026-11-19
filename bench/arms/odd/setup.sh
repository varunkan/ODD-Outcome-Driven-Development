#!/usr/bin/env bash
# ODD: `odd init` only. The method reaches the agent through AGENTS.md, exactly as it would in any tool that reads
# that file; no hooks, no extra prompt text. No branch is made here: the runner puts every arm on `work`.
set -euo pipefail
# ODD_INIT_FLAGS: more flags for `odd init`; the odd-claim arm passes --claude-hooks.
python3 "$ODD_PY" init ${ODD_INIT_FLAGS:-} >/dev/null
