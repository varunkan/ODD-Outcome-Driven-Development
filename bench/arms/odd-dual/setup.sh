#!/usr/bin/env bash
# The odd arm's setup, unchanged: `odd init` with the pinned odd.py ($ODD_PY, the bench repository's HEAD copy).
set -euo pipefail
exec bash "$(dirname "$0")/../odd/setup.sh"
