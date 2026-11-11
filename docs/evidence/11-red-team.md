# 11. Red team of 0.2.0

Six attackers, each with a different angle (false accept, restore and data loss, the gate, an agent following the method, the
Claude Code hooks, the code itself), tried to break `odd.py` 0.2.0 with reproducible scripts. Every finding was then
reproduced independently before it counted. 48 were confirmed: 5 blockers, 27 major, 16 minor.

Each one is now a fixture in `tests/test_odd.py` (class `RedTeam`, plus updated earlier tests), written to fail on 0.2.0
before the fix. 0.3.0 passes all 78 tests. Several findings are the same defect seen from two angles and share one
fixture.

| # | severity | angle | finding |
|---|---|---|---|
| 0 | blocker | accept | A tag or local branch named origin/<target> shadows the remote-tracking ref: the documented CI step measures from HEAD and passes with 0 files changed |
| 1 | major | accept | A proof that runs a taken-out file through an interpreter (python3 src/x.py, sh src/x.sh) is recorded as verified |
| 2 | major | accept | Paths are handed to git as pathspecs: the lane reads another file's line count, and the take-out permanently reverts a file outside the outcome |
| 3 | major | accept | `ignore = all` in .gitmodules hides a submodule pointer change from the changed set |
| 4 | major | accept | Settings are read from the merge-base, which the author chooses: a branch cut before a tightening is judged by the old settings |
| 5 | major | accept | gate --recompute without --base takes default_branch from the working-tree config, so a change can set its own base to HEAD |
| 6 | major | accept | The small-change lane counts newline characters: a module on one line or with CR-only line ends is 1 line, and empty files and mode changes are 0 |
| 7 | minor | accept | gate --recompute measures the working tree, not the commits: a committed change that is reverted in the working tree passes |
| 8 | blocker | restore | A file or symlink standing where the base has a directory is destroyed by the take-out: crash with a stuck tree, or silent deletion with exit 0 |
| 9 | major | restore | After a kill, recovery writes to the path recorded in the journal, not the working tree it runs in: a renamed tree is not restored, and the journal is deleted |
| 10 | blocker | restore | `git restore` runs without literal pathspecs: a changed file with [ ] in its name makes the take-out overwrite a sibling outside the boundary, which is never put back |
| 11 | blocker | restore | One path that cannot be removed aborts the put-back: the other files stay at the base version and every later odd command crashes with exit 1 |
| 12 | major | restore | A kill while odd itself is writing is not recovered correctly: a later edit is overwritten (take-out window), or a half-written file is left truncated and blamed on the user (put-back) |
| 13 | major | restore | If the journal directory disappears during the failing run, nothing is put back and nothing says so |
| 14 | major | restore | A path the change deleted does not reliably go back to absent: the file stays, unnamed, when the proof rewrote it, and the directories git created always stay |
| 15 | major | restore | A killed check whose pid still answers is taken for a live one: the change is not put back and odd judges the reverted tree, for up to 47 minutes |
| 16 | blocker | gate | A directory replaced by a symlink (or a file) of the same name: odd done crashes while putting the change back, leaves the tree reverted, and every later odd command crashes the same way |
| 17 | major | gate | gate --recompute (no --base) takes default_branch from the changed working-tree config, so a change can point the base at itself and pass with '0 file(s) changed' |
| 18 | major | gate | A submodule pointer bump is invisible to the gate when .gitmodules says ignore = all, and the same change can add that line |
| 19 | major | gate | .odd/config.json is never validated: a string where a list belongs exempts every file, unparsable JSON silently means the defaults, and other wrong types are tracebacks that odd init cannot repair |
| 20 | major | gate | The local gate prints 'ok' and PASS for an outcome whose most recent odd done, on exactly the current content, failed |
| 21 | minor | gate | Exempt and test globs also match everything under a directory with a matching name, so notes.md/payload.py, app.lock/worker.py and LICENSE-tools/run.py need no outcome |
| 22 | minor | gate | A changed symlink that points at a directory, or a file replaced by a directory, is counted as 1,000,000 lines and reported as 'a binary file or submodule pointer' |
| 23 | minor | gate | Unexpected errors end in a Python traceback with exit 1, the code that means 'fail': an outcome file that is not UTF-8, and a change with 30,000 test files |
| 24 | major | agent | `odd done` can never verify a Python change when `__pycache__` is not git-ignored and `in:` is a directory glob: exit 2 on every run, and the message names neither the cause nor the remedy |
| 25 | major | agent | After a commit on the default branch, `odd done` advises `counterfactual: skip`; following it gives exit 0 from both `done` and `gate` with 0 lines verified. The method never says to work on a branch |
| 26 | major | agent | Default branch not named main/master and no origin/HEAD: `odd done` exits 2 and tells the agent to pass `--base`, a flag `odd done` does not have; `odd init` reports 'is set up' without noticing |
| 27 | major | agent | A test that asserts nothing is verified when its file is inside `in:` and is run through an interpreter; DESIGN section 4 says the check stops, but only the first word of the proof is compared |
| 28 | major | agent | `--in` takes comma-separated globs, which the method, README and DESIGN never say; space-separated, repeated and brace forms are accepted silently and `odd done` then advises a skip |
| 29 | minor | agent | Adding any test file makes every already-verified outcome in the change stale, although DESIGN section 5 says 'an edit elsewhere changes nothing'; each later outcome costs three more proof runs per earlier one |
| 30 | minor | agent | `odd park` prints 'its changes must be removed or the gate fails'; the gate passes with the failed change still in the tree, and nothing says what to do with the proof's test, which stays red |
| 31 | minor | agent | `odd new` accepts a `--proof` containing a line break and writes an outcome file odd cannot read; `done`, `gate` and `stats` then exit 1 for every outcome, and `odd done` on a good outcome prints 'verified' and exits 1 |
| 32 | major | hooks | Stop hook cannot see edits to untracked files: a verified outcome over new files goes stale, or 300 unowned lines land in an untracked directory, and the turn ends unblocked |
| 33 | major | hooks | `odd init` leaves Claude Code without the method when the Claude file is .claude/CLAUDE.md (the import names a file that does not exist) or CLAUDE.local.md (no import at all), and reports success |
| 34 | major | hooks | Stop hook blocks a turn that changed nothing: edits made in the forced continuation (or typed by the person between turns) are charged to the next turn; the same early return also discards the interrupted-check notice |
| 35 | minor | hooks | Parking an outcome gets the turn blocked as 'no outcome', with a message telling the agent to park |
| 36 | minor | hooks | Stop hook blocks again on byte-identical files after a turn that only ran `git add` or `git commit` |
| 37 | minor | hooks | `odd init --claude-hooks` silently deletes the user's own Stop/SessionStart hooks from .claude/settings.local.json |
| 38 | minor | hooks | `odd done` says verified, then the Stop hook and `odd gate` at once call the outcome stale when the proof wrote a file under a test path |
| 39 | minor | hooks | `odd init` dies with a Python traceback (exit 1, half applied) on an invalid or oddly shaped settings.local.json, AGENTS.md as a directory, a non-UTF-8 CLAUDE.md, or when the vendored copy is run through a symlinked path |
| 40 | major | code | A change that replaces a directory with a same-named file crashes the put-back, strands the tree reverted, and every later odd command crashes too |
| 41 | major | code | gate --recompute without --base takes default_branch from the working-tree config, so a change can move its own base to HEAD and pass with 0 files changed |
| 42 | major | code | proof_timeout is not enforced: odd waits for the proof's output pipe, so a proof that leaves one detached descendant is called a timeout and blocks odd for as long as that process lives |
| 43 | major | code | .odd/config.json is never validated: a string where a list is expected exempts every file, and a JSON syntax error silently restores the defaults |
| 44 | minor | code | A directory whose name looks like an exempt file (notes.md/, LICENSES/) exempts everything under it |
| 45 | minor | code | The local gate lists an outcome as ok although the most recent `odd done` on the same tree failed |
| 46 | minor | code | Non-UTF-8 bytes and malformed JSON reach the user as Python tracebacks with exit 1, the code documented as fail / not shown |
| 47 | minor | code | A proof that fails with exit 255 once the change is taken out is reported as could not run, so the outcome can never be verified |

## What remains a limit

- The check that a proof does not run a file inside the change reads the command as text. `cd dir && python3 file.py`,
  globs and shell substitution get past it. A person reading the outcome file is the backstop.
- A proof that deliberately exits with 129-192 looks like a killed process and is reported as could not run.
- A process a proof starts with its own session (setsid) escapes the clean-up after the proof ends.
- The small-change lane counts at most 120 bytes per line, so a long line costs more than one line; that is intended.
