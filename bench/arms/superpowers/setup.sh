#!/usr/bin/env bash
# Superpowers (github.com/obra/superpowers), pinned. It is a Claude Code plugin: 15 skills and one SessionStart hook
# that puts the text of its "using-superpowers" skill into every new session. This script keeps one unmodified
# checkout of the pinned release in BENCH_CACHE and writes that directory's absolute path into .bench-plugin-dir at
# the repository root. The runner loads it for the one session with `claude --plugin-dir <that path>`.
# Nothing is written to the home directory or to .claude/. Sources and what was verified: NOTES.md.
set -euo pipefail

REPO_URL="https://github.com/obra/superpowers.git"
TAG="v7.0.2"                                       # the release
COMMIT="22f0b463e7a5e579904dd6211a520321035526f7"  # the commit that tag names: this is the pin
POINTER=".bench-plugin-dir"                        # read by the runner; holds the path and nothing else

: "${BENCH_CACHE:?BENCH_CACHE must name a writable cache directory}"

fail() { echo "superpowers setup: $*" >&2; exit 1; }

command -v git >/dev/null 2>&1 || fail "git not found on PATH"
command -v python3 >/dev/null 2>&1 || fail "python3 not found on PATH"

mkdir -p "$BENCH_CACHE"
cache="$(cd "$BENCH_CACHE" && pwd -P)"
plugin="$cache/superpowers"

# Git bound to the checkout itself, so it can never answer for a repository that encloses the cache directory.
pgit() { git --git-dir="$plugin/.git" --work-tree="$plugin" "$@"; }
at_pin() { [ -d "$plugin/.git" ] && [ "$(pgit rev-parse --verify -q 'HEAD^{commit}' 2>/dev/null)" = "$COMMIT" ]; }
unmodified() { local out; out="$(pgit status --porcelain --ignored --untracked-files=all 2>&1)" && [ -z "$out" ]; }

# One setup at a time in the cache when several runs start together. The lock is held on descriptor 9 until exit.
exec 9>"$cache/superpowers.lock"
python3 -c 'import fcntl; fcntl.flock(9, fcntl.LOCK_EX)' 2>/dev/null ||
  echo "superpowers setup: no file lock available in $cache; continuing without one" >&2

if [ ! -e "$plugin" ]; then
  # Clone beside the final place and move it in only when it is the pinned commit, so an interrupted or wrong
  # download never becomes the checkout.
  tmp="$(mktemp -d "$cache/superpowers.clone.XXXXXX")"
  trap 'rm -rf "$tmp"' EXIT
  if ! log="$(GIT_TERMINAL_PROMPT=0 git clone --quiet --depth 1 --branch "$TAG" "$REPO_URL" "$tmp/checkout" \
    </dev/null 2>&1)"; then
    printf '%s\n' "$log" >&2
    fail "could not clone $REPO_URL at $TAG"
  fi
  got="$(git --git-dir="$tmp/checkout/.git" rev-parse --verify -q 'HEAD^{commit}')" || got="nothing"
  [ "$got" = "$COMMIT" ] || fail "tag $TAG is $got, not the pinned commit $COMMIT"
  if [ ! -e "$plugin" ]; then # still absent: only another setup running without the lock could have made it
    mv "$tmp/checkout" "$plugin"
    echo "superpowers setup: cloned Superpowers $TAG into $plugin"
  fi
fi

at_pin || fail "$plugin exists but is not a checkout of commit $COMMIT; move it away and run again"

# A checkout that an earlier session or a person changed is put back, so every run gets the same framework.
if ! unmodified; then
  pgit reset --quiet --hard "$COMMIT" && pgit clean -ffdxq
  unmodified || fail "could not restore $plugin to commit $COMMIT"
  echo "superpowers setup: files in $plugin had been changed, added or removed; restored the pinned commit" >&2
fi

grep -qs "\"version\": \"${TAG#v}\"" "$plugin/.claude-plugin/plugin.json" ||
  fail "$plugin/.claude-plugin/plugin.json does not declare version ${TAG#v}"

# The whole arm rests on the SessionStart hook: without its output a session only has the skill list. Run the
# hook's own command here, as Claude Code will, so that a machine where it prints nothing fails setup and not a
# measured session. The hook only reads skills/using-superpowers/SKILL.md and prints JSON.
CLAUDE_PLUGIN_ROOT="$plugin" "$plugin/hooks/run-hook.cmd" session-start </dev/null 2>/dev/null |
  python3 -c '
import json, sys
out = json.load(sys.stdin)["hookSpecificOutput"]
assert out["hookEventName"] == "SessionStart"
assert "superpowers:using-superpowers" in out["additionalContext"]
' 2>/dev/null || fail "the plugin's SessionStart hook did not print its bootstrap text on this machine"

# No trailing newline: the file is the path, byte for byte.
printf '%s' "$plugin" >"$POINTER"
echo "superpowers setup: Superpowers $TAG (${COMMIT:0:12}) ready; plugin directory written to $POINTER"
