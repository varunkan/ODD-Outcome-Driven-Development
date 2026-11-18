#!/usr/bin/env bash
# The odd-cases arm's setup with one more setting: "reach": "require" (backlog 45).
set -euo pipefail
ODD_REQUIRE="cases reach" exec bash "$(dirname "$0")/../odd-cases/setup.sh"
