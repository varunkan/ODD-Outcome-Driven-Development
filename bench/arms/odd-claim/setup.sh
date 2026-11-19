#!/usr/bin/env bash
# The odd-reach arm's setup, with odd's Claude Code hooks installed and "report": "claim" (backlog 47).
set -euo pipefail
ODD_INIT_FLAGS="--claude-hooks" ODD_REQUIRE="cases reach report=claim" bash "$(dirname "$0")/../odd-cases/setup.sh"
# odd writes its hooks to the personal settings file; the runner loads project settings only, so they go there.
mv .claude/settings.local.json .claude/settings.json
