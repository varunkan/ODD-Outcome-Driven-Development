#!/usr/bin/env bash
# plain-tests plus one Stop hook: `odd check`, the take-out check with no outcome file and no method text. When the
# tests the session wrote pass without its change, or do not pass, the end of the turn is blocked once with the
# result. The tool is the bench repository's odd.py ($ODD_PY), copied in; nothing else of odd is installed.
set -euo pipefail
mkdir -p .odd .claude
cp "$ODD_PY" .odd/odd.py
cat > .claude/settings.json <<'JSON'
{"hooks": {"Stop": [{"hooks": [{"type": "command", "timeout": 600, "command": "python3 \"$(git rev-parse --show-toplevel 2>/dev/null)/.odd/odd.py\" check --base main --stop-hook 2>/dev/null || true"}]}]}}
JSON
