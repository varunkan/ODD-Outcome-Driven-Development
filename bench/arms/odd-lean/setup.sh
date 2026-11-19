#!/usr/bin/env bash
# odd as `odd init --claude-hooks` leaves it: the defaults, the method text, and the Stop hook, which asks for the
# gate's verdict line at the end of a report ("report": "verdict", the default).
set -euo pipefail
ODD_INIT_FLAGS="--claude-hooks" bash "$(dirname "$0")/../odd/setup.sh"
# odd writes its hooks to the personal settings file; the runner loads project settings only, so they go there.
mv .claude/settings.local.json .claude/settings.json
