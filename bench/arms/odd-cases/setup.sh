#!/usr/bin/env bash
# The odd arm's setup, plus one setting: "cases": "require" (backlog 44). Written before the session starts, so it is
# part of the base the gate reads its settings from; the agent is told nothing more than the odd arm is.
# ODD_REQUIRE names the settings to turn on (default: cases); the odd-reach arm passes "cases reach".
set -euo pipefail
bash "$(dirname "$0")/../odd/setup.sh"
python3 - <<'PY'
import json, os
path = '.odd/config.json'
cfg = json.load(open(path)) if os.path.exists(path) else {}
cfg.update({k: 'require' for k in os.environ.get('ODD_REQUIRE', 'cases').split()})
json.dump(cfg, open(path, 'w'), indent=2)
PY
