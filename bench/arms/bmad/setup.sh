#!/usr/bin/env bash
# BMAD Method, pinned. Runs the project's own headless install command: the BMad Method module (bmm) with its
# Claude Code skills. Everything the session needs lands in the repository: _bmad/ (configuration and the shared
# scripts), _bmad-output/ (where the skills write their records) and .claude/skills/ (29 skills). Nothing is written
# to the home directory; npm's cache is redirected to BENCH_CACHE. Sources and what was verified: NOTES.md.
set -euo pipefail

BMAD_VERSION="6.12.4"          # npm bmad-method@6.12.4 = git tag v6.12.4 (commit bab9082c3e884e0d72c759bcd1a6d90bcc01be84)
ENTRY_SKILL="bmad-build-auto"  # the skill prompt.md starts

: "${BENCH_CACHE:?BENCH_CACHE must name a writable cache directory}"

fail() { echo "bmad setup: $*" >&2; exit 1; }

# Machine prerequisites the project lists: Node.js 20.12+ for the installer, uv for the build skills (their first
# step is `uv run _bmad/scripts/render_skill.py`, and they halt when it fails).
command -v node >/dev/null 2>&1 || fail "node not found on PATH (the installer needs Node.js 20.12 or later)"
command -v npx  >/dev/null 2>&1 || fail "npx not found on PATH (the installer is run with npx)"
command -v uv   >/dev/null 2>&1 || fail "uv not found on PATH (the BMAD build skills halt without it)"
node -e 'const [a, b] = process.versions.node.split(".").map(Number); process.exit(a > 20 || (a === 20 && b >= 12) ? 0 : 1)' \
  || fail "Node.js 20.12 or later is required, found $(node --version)"

manifest="_bmad/_config/manifest.yaml"
installed() {
  [ -f "$manifest" ] && grep -qxF "  version: ${BMAD_VERSION}" "$manifest" \
    && [ -f ".claude/skills/${ENTRY_SKILL}/SKILL.md" ] && [ -f "_bmad/scripts/render_skill.py" ]
}

# Idempotent: a second run finds the pinned install and leaves every file as it is. (Re-running the installer itself
# would do a "quick update" that rewrites the timestamps in four generated files.)
if ! installed; then
  mkdir -p "$BENCH_CACHE/npm"
  log="$(mktemp "${TMPDIR:-/tmp}/bmad-setup.XXXXXX")"
  # --user-name: without it the installer writes the machine's login name into the project configuration.
  if ! npm_config_cache="$BENCH_CACHE/npm" npm_config_update_notifier=false \
      npx --yes "bmad-method@${BMAD_VERSION}" install \
        --directory . --modules bmm --tools claude-code --user-name User --yes \
        </dev/null >"$log" 2>&1; then
    cat "$log" >&2
    rm -f "$log"
    fail "the installer failed (output above)"
  fi
  if ! installed; then
    cat "$log" >&2
    rm -f "$log"
    fail "the installer exited 0 but the pinned install is not in place (output above)"
  fi
  rm -f "$log"
fi

# The entry skill's first step needs uv to find Python 3.11 or later. Check that here, where a failure is a setup
# error, and not inside a measured session. `--help` writes nothing into the repository.
uv run --no-cache _bmad/scripts/render_skill.py --help >/dev/null 2>&1 \
  || fail "uv could not run _bmad/scripts/render_skill.py (it needs Python 3.11 or later)"
