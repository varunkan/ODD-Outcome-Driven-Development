#!/usr/bin/env bash
# Spec Kit (github.com/github/spec-kit). Installs the pinned Specify CLI once into BENCH_CACHE, then initialises
# this repository for Claude Code with the command the project documents for scripted runs and adds the bundled bug
# extension (offline). Afterwards everything a session needs is inside the repository (.specify/ and
# .claude/skills/speckit-*/): the CLI is not used again.
set -euo pipefail

VERSION="1.4.0" # PyPI specify-cli==1.4.0 = tag v1.4.0 = commit 0019fa14d12f45edabc2cc3176c9168a68bd0f97
SKILLS="constitution specify plan tasks implement converge" # the SDD skills prompt.md names
BUG_SKILLS="bug-assess bug-fix bug-test"                     # the bug extension's skills prompt.md names

: "${BENCH_CACHE:?BENCH_CACHE must name a writable cache directory}"
mkdir -p "$BENCH_CACHE"
home="$(cd "$BENCH_CACHE" && pwd)/speckit-$VERSION"
specify="$home/bin/specify"

cli_ready() { [ "$("$specify" --version 2>/dev/null)" = "specify $VERSION" ]; }

initialised() {
  grep -qs "\"speckit_version\": \"$VERSION\"" .specify/init-options.json || return 1
  grep -qs '"integration": "claude"' .specify/init-options.json || return 1
  [ -f .specify/scripts/bash/common.sh ] && [ -f .specify/templates/spec-template.md ] || return 1
  for s in $SKILLS; do [ -f ".claude/skills/speckit-$s/SKILL.md" ] || return 1; done
}

# A plain `specify extension add bug` exits 1 once the extension is registered, even with a skill gone: hence --force.
bug_added() {
  [ -f .specify/extensions/bug/extension.yml ] || return 1
  for s in $BUG_SKILLS; do [ -f ".claude/skills/speckit-$s/SKILL.md" ] || return 1; done
}

if ! cli_ready; then
  mkdir -p "$home"
  # One installer at a time when several runs start together. The lock is held on descriptor 9 and ends with it.
  exec 9>"$home/install.lock"
  python3 -c 'import fcntl; fcntl.flock(9, fcntl.LOCK_EX)' ||
    echo "setup: no file lock available in $home; installing without one" >&2
  if ! cli_ready; then
    if command -v uv >/dev/null 2>&1; then
      UV_CACHE_DIR="$home/uv-cache" UV_TOOL_DIR="$home/tool" UV_TOOL_BIN_DIR="$home/bin" \
        uv tool install --quiet --force "specify-cli==$VERSION"
    else
      python3 -m venv "$home/venv"
      "$home/venv/bin/python" -m pip install --quiet --disable-pip-version-check "specify-cli==$VERSION"
      mkdir -p "$home/bin"
      ln -sf "$home/venv/bin/specify" "$specify"
    fi
    cli_ready || { echo "setup: specify-cli $VERSION did not install into $home" >&2; exit 1; }
  fi
  exec 9>&-
fi

if initialised && bug_added; then
  echo "setup: Spec Kit $VERSION and its bug extension are already here; nothing to do"
  exit 0
fi

# Scripted init of an existing repository: docs/installation.md, "CI and AI Agent Harnesses".
if ! initialised; then
  if ! log="$("$specify" init --here --force --non-interactive --integration claude --script sh \
    --ignore-agent-tools </dev/null 2>&1)"; then
    printf '%s\n' "$log" >&2
    exit 1
  fi
  if ! initialised; then
    printf '%s\n' "$log" >&2
    echo "setup: specify init ended without the files the session needs" >&2
    exit 1
  fi
fi
# The defect process: README.md "Bug fixing"; the extension is bundled in the package, so no network.
if ! bug_added; then
  if ! log="$("$specify" extension add bug --force </dev/null 2>&1)" || ! bug_added; then
    printf '%s\n' "$log" >&2
    echo "setup: specify extension add bug ended without the bug skills" >&2
    exit 1
  fi
fi
echo "setup: Spec Kit $VERSION initialised for Claude Code, bug extension added (.specify/, .claude/skills/speckit-*/)"
