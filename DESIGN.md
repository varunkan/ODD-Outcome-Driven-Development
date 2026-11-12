# ODD design

Version 2, 2026-11-11. This replaces the first design after a four-lens review (tamper resistance, the correctness
of the check, day-to-day friction, portability) returned 23 required changes. The review and its ruling are in
[`docs/evidence/10-design-review.md`](docs/evidence/10-design-review.md).

## 1. What it is

One command-line tool, `odd`, in one file, and a half-page method that a coding agent follows.

**"Done" is recomputed from the code, not claimed by the agent.** An outcome is verified when its proof passes on the
tree as it is, fails on the same tree with the change taken out, and passes again once the change is put back. For
proofs that run from the repository, anyone, including CI, can recompute that.

Install: `pipx install odd-tool` (or download `odd.py`), then run `odd init` in a git repository. It needs a POSIX shell, git 2.23 or newer
and Python 3.8 or newer.

## 2. The unit of work: an outcome file

`.odd/outcomes/<slug>.md`, committed with the work:

```
---
outcome: A cashier who splits a bill three ways sees three totals that add up to the bill.
proof: pytest tests/test_split.py -q
in: src/billing/**
---
Free notes: questions asked and answered, decisions and why.
```

- `outcome`: one sentence, who observes what.
- `proof`: a command that exits 0 only when the outcome holds. It is the narrowest command that shows the outcome,
  never the whole suite. It asserts results or counts, not wall-clock time.
- `in`: globs of the product files this outcome may change (its boundary).
- Paths, globs and the proof are relative to the repository root.
- Optional lines: `counterfactual: skip - <reason>`, `parked: <reason>`, `escaped: ...` (written by `odd escaped`,
  section 9), `sealed: ...` (written by `odd seal`, section 4), `test-change: <reason>` (why this change edits or
  deletes a test that existed at the base, section 5; needs a tool newer than 0.4.0, the next release:
  a pinned Action at 0.4.0 or older refuses the unknown field).

There is no status field. "Done" is never written to a committed file. A requirement becomes one or more outcome
files; their sentences and proofs are the specification, and each file is a task.

## 3. Commands

| command | what it does | exit |
|---|---|---|
| `odd init [--claude-hooks] [--mcp]` | installs or repairs: `.odd/odd.py`, `.odd/config.json`, the method in `AGENTS.md`, the import line in an existing Claude instruction file; prints the CI step, the conditions under which CI is the authority, and a proof suggestion (section 3a); `--mcp` also installs the MCP server (section 7) | 0 |
| `odd new <slug> "<outcome>" --proof CMD --in "GLOB, GLOB"` (comma-separated; `--in` may repeat) | writes the outcome file; `--proof auto [--test PATH]` picks the command (section 3a) | 0, 1 refused (also: `auto` and no runner detected) |
| `odd seal <slug> [--base REF]` | optional: requires the proof to fail now, then fingerprints it in the outcome file (section 4) | 0 sealed, 1 already passes or no test file changed, 2 could not run |
| `odd done <slug> [--base REF]` | verifies the outcome (section 4) and records it locally | 0 verified, 1 not shown, 2 could not run |
| `odd race <slug> [--n N] [--agent CMD] [--base REF]` | N agent attempts at one outcome, each in its own git worktree, verified as `done` would; the winner is applied (section 3b); needs a tool newer than 0.4.0 | 0 winner applied, 1 none verified or the winner left as a patch, 2 could not run |
| `odd gate [--base REF] [--recompute] [--summary FILE] [--json FILE]` | checks the whole change (section 5); optionally also writes the result as Markdown or JSON | 0 pass, 1 fail, 2 could not run |
| `odd park <slug> "<reason>"` | the honest exit, for blocked work and for work that cannot be done as specified | 0 |
| `odd escaped <slug> "<what, where found>"` | records a defect that got past this outcome (section 9) | 0, 1 vague report or no such outcome |
| `odd stats` | counts, labelled self-reported, with escaped defects split by kind of proof | 0 |

`odd hook stop|session-start` is an internal entry point called only by the opt-in Claude Code hooks.

### 3a. Proof suggestions

`odd new ... --proof auto` picks a narrow proof from the test runner the repository already uses, prints every
runner it detected and the command it chose, and writes that command into the outcome file like any other. Nothing
detected is a refusal (exit 1) that says to give `--proof "<command>"`; it never guesses silently. `odd init` prints
the same suggestion with `<slug>` in place of a name. Detection, most specific first (the first one found is used):

| runner | shown by | proof (default test path) |
|---|---|---|
| pytest | `pytest.ini`, `[tool.pytest` in `pyproject.toml`, `[pytest]` in `tox.ini`, `[tool:pytest]` in `setup.cfg`, a `conftest.py` at any depth, `pytest` in a root `requirements*.txt` | `python3 -m pytest -q tests/test_<name>.py` |
| jest, vitest, node, mocha | the word (`node --test`) in `package.json`'s `scripts.test` | `npx jest` / `npx vitest run` / `node --test` / `npx mocha test/<slug>.test.js` |
| go | `go.mod` | `go test .` (`<name>_test.go`; `go test ./<dir>` for a test path in a directory) |
| cargo | `Cargo.toml` | `cargo test --test <name>` (`tests/<name>.rs`) |
| unittest | any `*.py` file outside `.odd/` | `python3 -m unittest -q tests/test_<name>.py` |
| make | a `test:` target in the Makefile | `make test`, flagged as running the whole target |

`<name>` is the slug with `-` and `.` turned into `_`. `--test PATH` names the test file instead (quoted for the
shell) and goes with `--proof auto` only. Limits: detection reads file names and a few settings, not how the
project really runs its tests (a virtualenv, `npm test` flags, a workspace, a Go package that is not the root); the
command is a starting point for a person or agent to read, and `make test` is not narrow. A proof literally `auto`
can no longer be written with `--proof` (edit the file). A proof that exits 5 or prints that it ran no tests gets the
hint that the runner may be wrong; unittest is still picked for a repository whose only sign is a `.py` file.

### 3b. `odd race`: parallel attempts, the proof picks the winner

`odd race <slug>` runs one outcome as N attempts by coding agents and keeps the one the proof favours. The outcome
must exist with its proof; with `"race_seal": true` it must also be sealed (recommended: the seal shows the proof
red before any attempt). odd never calls a model: an agent is a shell command in `"agents"` in `.odd/config.json`
(or `--agent CMD` for every attempt), used in turn, one per attempt; N defaults to the number of agents, or 3
when there is one. `{prompt_file}` in the command becomes the path
of a prompt file; without it the prompt arrives on stdin. The prompt names the outcome, the proof, the boundary, the
files to leave alone, and the method `odd init` installs.
The settings `agents`, `race_timeout` and `race_seal` need a tool newer than 0.4.0: v0.4.0 (and its Action)
refuses an unknown setting, so a project that adds them vendors the newer `odd.py` first.

1. **Worktrees.** Each attempt gets `git worktree add --detach` of HEAD under the git directory
   (`.git/odd/race/run-<pid>/<n>`), never the user's tree. The outcome file, the changed test files and
   `.odd/config.json` are copied in as they are in the user's tree and committed there as the attempt's start.
   Uncommitted product changes in the user's tree are not copied.
2. **Agents run in parallel**, each in its own process group with stdin closed or the prompt, its output in
   `.git/odd/race/<slug>/agent-<n>.log`. At `race_timeout` seconds (default 1800) an agent is killed with its process
   group; when an agent ends, whatever it left running in its group is killed before its attempt is checked.
3. **Each attempt is checked when it ends**, one at a time, inside its worktree: it must not have edited the copied
   files or a control file, and must not have changed product files outside `in:`; then the checks of `odd done`
   (`prove()`: the R2 test-change rule, then `verify()`: green, red without the change, green, the empty-proof
   checks and, unless `"strength": "off"`, the strength check; `"enforce"` applies as in `done`). A timed-out attempt is
   not checked.
4. **The winner**: verified, then the highest share of small breaks caught, then the fewest changed lines (test and
   product files against the attempt's start), then the earliest agent finish. The output is a table of attempts
   (strength, lines, seconds of agent and of verification, verified or the first line of why not) and the reason
   the winner beat the runner-up.
5. **Applying**: the winner's diff is written to `.git/odd/race/<slug>/winner.patch` and applied with `git apply`
   only if no path inside `in:` differs from HEAD in the user's tree; otherwise, or if `git apply` refuses, the tree
   is left alone and the patch path is printed (exit 1). The race records no evidence in the user's tree: run
   `odd done <slug>` there, which re-verifies on the tree as it is.
6. **Cleanup**: the worktrees are removed when the race ends, also on SIGTERM/SIGINT (agents killed first). After a
   kill -9 the next race removes runs whose process is gone; agents still running then are not found.

Limits: verification is sequential, so N attempts cost N verifications after the agents; the attempts share the
machine, so a timing-sensitive proof may behave differently under load; installed dependencies and caches outside
the worktree are shared; nothing stops an agent from writing outside its worktree (it runs as the user). Measured
(fake agents, this machine): see BACKLOG item 1.

## 4. Verification (`odd done`, and `odd gate --recompute`)

**The base** is one revision for everything: where this branch left the target branch (the merge-base of HEAD and
`--base REF`, or of HEAD and the default branch). If it cannot be found, the result is "could not run" with the
command that fetches it.

**The changed set** is `git diff --name-only -z --no-renames <base>` plus untracked, non-ignored files. A rename is a
delete and an add. It is computed from git, so files written through a shell are seen like any other.

**Test files** are the files matching `test_globs` in the settings (`tests/**`, `**/test_*.py`, `**/*_test.*`,
`**/*.test.*` and the like). They are never taken out, need no outcome, and do not count toward the small-change lane.

**The check is green, red, green:**

1. The proof passes on the tree as it is.
2. The product files this outcome changed are taken out: added files are removed, deleted files recreated, modified
   files put back to their base version. The proof must now fail by running to completion and exiting non-zero.
3. The change is put back and the proof passes again.

This shows the proof depends on the change. For new code it shows only that the proof reaches it. It costs three
proof runs per outcome, plus one per mutant of the strength check below.

Rules of the in-place check:

- A journal of byte copies (type and mode kept, links as links) is written under the git directory before the first
  file changes. Nothing of it is visible in the working tree.
- Git writes the base versions to the working tree only; the index is never touched.
- The change is put back in a `finally`, on SIGINT, SIGTERM and SIGHUP, and by any later `odd` command that finds
  the journal of a dead run (that command then stops with exit 2 so the tree can be looked at).
- A path is put back only if it still holds exactly what the check left there. If it was edited meanwhile, the edit
  stays and the earlier version is kept beside the journal; both are named.
- One check at a time per working tree.
- Any error while taking the change out: put it back and exit 2. The proof never runs on a half-reverted tree.
- Every file the check writes gets a newer modification time, so caches keyed on it notice.
- With the change taken out, a timeout, exit 126 or 127, or death by signal is "could not run", not a failure.
- If nothing inside `in` changed, the check stops with exit 1 before a second run.
- If the proof runs a file that would be taken out, the check stops and says to keep it under a test path.

**Proof strength: small breaks in the changed lines.** After green, red, green, the check makes small deliberate
breaks ("mutants") in the changed lines of the outcome's product files, one at a time, and runs the proof against
each. A mutant the proof still passes ("survivor") is a changed line the proof does not depend on: a weak proof, or
a line no test reaches, without any language's coverage tool.

- The breaks are textual and the same in every language: `<` `<=` `>` `>=` `==` `!=` swapped, `and`/`or`,
  `&&`/`||`, `+`/`-`, `true`/`false` in their usual spellings, an integer literal plus one. Strings and comments
  (quotes, triple quotes, `/* */`, `#`, `//`, a leading `--`) are blanked first; the detection is approximate and
  errs towards fewer mutants.
- At most `mutants` (default 8) per outcome, in a fixed order, so two runs on the same tree make the same breaks.
  One break per changed line comes first, the files sharing the cap evenly and each file's lines spread; a second
  break on a line only once every changed line has one (one mutant per line is enough, docs/evidence/14-research.md
  section 2.4). Each costs one proof run.
- Each mutant goes in and comes out through the same journal as the take-out: a kill puts it back, an edit made
  meanwhile stays.
- A mutant whose run times out, exits 126 or 127, or dies by a signal is neither caught nor survived; it is listed.
  Under `"enforce"` any such mutant is a failure: the proof controls its own exit code, so a run that did not
  complete is never evidence of strength.
- Under `"report"` sampling stops once the breaks have taken about as long as the three core runs (at least 2 s),
  and says so; the estimate is printed before the first break. `"enforce"` always runs all `mutants`. A survivor
  line ends with a `next:` step.
- The setting `strength`: `"report"` (default) prints the score and each survivor (file:line, the swap, the line) in
  `odd done` and the gate; `"enforce"` makes a survivor a failure; `"off"` makes no mutant. `--recompute` measures
  it again with the settings of the target branch.
- The score reads "proof strength k of n" everywhere (`odd done`, the gate, the pull-request summary, `odd stats`):
  k of the n breaks the proof caught. It is never called "verified": a strong score on a proof written after the
  code can still pin a bug (section 10).
- **Changed lines the proof never runs (Python only).** When the proof calls Python (`python`, `python -m unittest`,
  `pytest`, `python -m pytest`, or a `.py` file) and the outcome changed `.py` files, the strength check runs the
  proof once more with a trace hook: a `sitecustomize.py` put first on `PYTHONPATH` installs `sys.settrace` (and
  `threading.settrace`) in every Python process the proof starts, restricted to the changed files, and writes the
  lines each ran when the process exits. The proof's own interpreter also says which lines are executable, so a
  different Python version's line table is never guessed. Each changed executable line no process ran is listed:
  "not run by the proof: file:line,line". Under `"enforce"` such a line is a failure, reported with any survivors.
  Not measured, and said so ("lines run: not measured (...)"): a proof that calls no Python, a change with no
  `.py` file, a traced run that does not exit 0, or a Python started with `-I`, `-S` or `-E` (it never loads the
  hook). A project's own `sitecustomize` is run after the hook. Other languages are not measured. Limits: lines run
  only in a process that leaves through `os._exit` (multiprocessing workers) are not seen and show as not run; this
  run is the one place the proof's environment differs (`ODD_TRACE_DIR`, `PYTHONPATH`), so a proof could tell it
  apart, but faking a line as run only hides it from this list, never from the mutants; a result recorded before
  this check existed shows nothing here and passes `"enforce"` on the local gate (`--recompute` measures it).

**Sealed proofs (optional).** `odd seal <slug>` runs the proof on the tree as it is and requires it to fail (run
to completion, non-zero); a proof that passes is refused with exit 1, one that cannot run is exit 2. It then writes
`sealed: proof@<hash>, <test file>@<hash>, ...` into the outcome file: a 12-hex sha256 of the proof command and of
each test file changed since the base (content, mode, a link as a link). It refuses when no test file has changed.
`odd done`, the local gate and `--recompute` then fail while the proof command or a sealed file differs, naming
them: "the sealed proof changed after it was sealed: <files>; reseal it or restore it". Resealing is `odd seal`
again; it needs the proof red again (take the product change out first) and it changes the outcome file, so it is
visible in review. Limits: the seal is written by the party being checked, so it proves nothing about what the test
was before `seal` ran, and a reseal is allowed; it covers only the files named, not helpers or fixtures added after;
a malformed `sealed:` line fails. Outcomes without it behave exactly as before. Seal runs no in-place edit, so it
needs no journal. `odd seal` also records a seal event (fingerprint, base, what the red proof said) in local
evidence; `odd stats` counts an outcome as sealed only when that event matches its `sealed:` line, and shows
`unseen` otherwise (a hand-written line, or a seal made on another machine). CI cannot check that the seal came
first; what it does check, with the sealed test files in place, is the take-out: the proof fails over the base.

**A proof that ran no test is not a proof.** Before anything else, a proof that exited 0 is read for the signs
that it showed nothing, and refused (exit 1) when one is there. This applies under `counterfactual: skip` too, where
the take-out check would not catch it. First, from the command itself: a proof whose every step only prints is
refused ("it only prints"). A step only prints when it is `echo` or `printf`, or Python code (`python -c`, or a
`.py` file the command names) whose top-level statements are only imports of the change's own modules and a few
inert stdlib modules (`sys`, `os`, `json`, `math`, ...), `print(...)` calls, calls on those inert modules and
assignments to names, and in which no expression can fail on purpose: no subscript, no division or modulo, no call
named `exit`, `quit`, `abort`, `fail*`, `assert*`, `system`, `exec*` or the like, and a call into the change only
inside `print(...)` or an assignment. That is the proof that prints a value and turns red only because the import of
a new file fails. Any other step (a test runner, `-m`, `grep`, `test`, a helper module from the repository, any
other import, an `assert`, an `if`, `1 / (add(2, 3) == 5)`, `{5: 0}[add(2, 3)]`, a bare `calc.selfcheck()`) may
check something and is never refused; the rule reads one file, not what it imports. A call inside `print(...)` can
still fail inside the change; the line is drawn there on purpose. A pipe into `grep -q .`, which checks only that
something printed, is not detected. Then, from the last 20 lines of the proof's own output:

- unittest: `Ran 0 tests`, or an `OK (...)` whose skipped plus expected failures is every test it ran
  (`OK (expected failures=1)`): an expected failure shows nothing either. An unexpected success counts as passing.
- pytest: `no tests ran`, or a summary with skipped or xfailed tests and none passed, xpassed or failed.
- jest: `Tests: ... 0 total`, `Tests:` with skipped and none passed, or `No tests found, exiting with code 0`.
- go test: every package line `[no test files]` or `[no tests to run]` (only when the output is under 20 lines,
  so no earlier `ok` line can have been cut off). A go test that calls `t.Skip` in every test is not detected:
  without `-v` or `-json`, go prints the same `ok` line for it as for a test that passed.
- A summary that says the tests took more than a second longer than the whole proof ran: a run did not print it.
- An early exit 0: a proof that is one command calling `python -m unittest`, `pytest` (or `python -m pytest`) or
  `go test`, and whose output lacks the summary that runner always prints when it finishes (`Ran N tests in`, the
  pytest count line or its `[100%]` progress mark, which `-qq` in `addopts` still prints, a go package line). This is how `sys.exit(0)` at import shows: the runner never reaches its
  summary.

It is deliberately conservative: a proof of several steps (`&&`, `;`, a pipe), a runner told to print less (`-qq`,
`--json`, `-p no:terminal`, a custom reporter), a script run directly (`python3 tests/check.py`), jest's missing
summary, and a test run where some tests are skipped and others pass are not refused. Not detected: `sys.exit(0)`
inside a script or a test file run directly, `os._exit(0)` after a fake summary printed by the code itself, a test
that passes because it asserts nothing (the take-out check catches that unless the outcome is a skip), and runners
not named here (mocha, rspec, cargo, ctest and the rest). The jest patterns are written from jest's known summary
lines and have not been run against jest here; unittest, pytest and go test were.

**A skip is an exemption with a reason, not a verification.** `counterfactual: skip - <reason>` is for a change
where nothing can fail first: a pure refactor, a dependency bump, a removal, a submodule pointer. The proof must
still pass. Every skip is named in the gate's result with its reason and its changed-line count.

## 5. The gate, and who is trusted

An outcome is **in play** when its file was added or changed since the base. `odd gate` passes when every changed
product file is inside the boundary of exactly one verified in-play outcome, or falls under a printed exemption.

- A changed product file may match the `in` of only one in-play outcome. Otherwise the gate fails and names both:
  such outcomes become one outcome, or two successive changes.
- A parked outcome covers no files. Its changes are removed, moved to another outcome, or fit the small-change lane.
- **Locally**, the gate runs no proof. An outcome counts as verified when `odd done` passed on exactly the current
  content (a hash of the proof, the boundary and the files inside it, kept under the git directory). A commit or an
  edit elsewhere changes nothing. This is fast feedback, and an agent with a shell could forge it.
- **With `--recompute`**, nothing recorded is trusted. Every in-play outcome that is not parked is verified again,
  and the settings are read from the base revision, so a change cannot loosen its own gate.
- "Could not run" is never reported as a pass.

The gate report is written for the person who reviews the change. Per outcome: the files and lines taken out, the
last line the proof printed when it failed, the seconds. Per change: the lines that passed under each exemption (the
small-change lane, exempt paths, each skip with its reason), the test files changed, and control files changed.

**An edit to an existing test fails closed.** A test file (under `test_globs`, read from the target branch under
`--recompute`) that existed at the base and is modified or deleted fails `odd done` and the gate, naming the files,
unless an in-play outcome that is not parked carries `test-change: <reason>`. The gate's test-files line and the
review comment then show `test-change (<slug>): <reason>`, so a reviewer reads why. Rewriting the test is the
easiest way to make a proof pass, and the main route models used to cheat on impossible tasks (ImpossibleBench,
[docs/evidence/14-research.md](docs/evidence/14-research.md) 2.2). New test files need no reason. A change with no
outcome (the small-change lane) that edits an existing test needs one now. The reason is text written by the party
being checked: it makes the edit visible, it does not judge it.

Turning a test off counts as editing it. A file that decides which tests run needs the same reason when it is added
or changed: a `conftest.py` at any depth or a `pytest.ini` (both count as test files, so they never fall in the
small-change lane), a changed line inside a pytest section of `pyproject.toml` (`[tool.pytest...`), `setup.cfg`
(`[tool:pytest]`) or `tox.ini` (`[pytest]`), and a changed line naming `load_tests` in an `__init__.py`. The gate's
test-files line lists them as "decide which tests run".

A reason that names test files (`test-change: tests/test_keep.py - the old test pinned the bug`) covers only those
files; another touched test file still fails. A reason that names no test file covers every test edit in the change,
as before, so older outcome files keep passing; the gate then prints `[names no file, so it covers every test edit:
<files>]` next to it, and for a named reason `[covers: <files>]`, so a reviewer sees which reason covers which file
and from which outcome. The named form is the same `test-change:` field, so it needs the same tool version (newer
than 0.4.0).

**CI is the authority only when** (1) the gate is a required check on the target branch, (2) the tool, its settings
and the CI configuration cannot change without a person's review, and (3) the agent cannot merge or push to the
target branch. Without all three the gate is advisory. On GitHub Actions the step is `uses: varunkan/ODD-Outcome-Driven-Development@<tag>` (`action.yml`): it unshallows the checkout, fetches the target branch and runs the action's own copy of the tool, pinned by the workflow. Elsewhere the CI step runs the copy of the tool from the target branch:

```
git show "refs/remotes/origin/$TARGET:.odd/odd.py" > "$TMP/odd.py" 2>/dev/null || cp .odd/odd.py "$TMP/odd.py"
python3 "$TMP/odd.py" gate --recompute --base "refs/remotes/origin/$TARGET"
```

**The review comment.** `odd gate --summary FILE` writes the same result as Markdown for the person who reviews
the change, and `--json FILE` as data: the verdict first, then per outcome its sentence, its proof, what the proof
printed with the change taken out (the last line naming a reason, such as an error or an assertion, then its last line), the strength score and each survivor, then every exemption, the control
files changed and why it did not pass. A result of "could not run" is written too, never left blank. The Action
appends it to the job's step summary always and, on `pull_request` events (input `comment`: `auto`, `true`,
`false`), creates or updates one pull-request comment: the comment by the input `author` (default
`github-actions[bot]`) whose body starts with the hidden line `<!-- odd-gate -->`, searched over every page; a
marker in anyone else's comment is ignored. Text from the change (outcome, proof, output, reasons, paths) is
escaped: entities for `& < >`, a backslash before Markdown punctuation, a code fence longer than any backtick run.
The gate runs in one step with no token; the token is given only to a second step (`if: always()`) that posts the
comment from the summary file. Limit: a proof runs as the same user, so a process it leaves behind could still
rewrite that file before the comment step reads it; it never sees the token in its environment. That needs
`permissions: pull-requests: write`; a refused or failed comment is logged and never changes the exit code. A pull
request from a fork gets a read-only token, so it gets the step summary and no comment. At most 50 pages of
comments are searched; the comment is cut at 60,000 characters. Whether the comment saves review time is not
measured; the protocol is [`docs/review-time.md`](docs/review-time.md).

It needs full history (not a depth-1 checkout) and the toolchain the proofs use, so it belongs at the end of the
project's existing test job. On GitHub, do not move it to `pull_request_target`. Without CI, fetch the target
branch and run `odd gate --recompute --base <target branch>` on the committed work before merging. A ref name that
could mean a tag, a local branch and a remote branch at once is refused rather than guessed.

## 6. Exemptions

- **The small-change lane.** Product lines changed outside any outcome pass while they total at most `trivial_lines`
  (default 25). It is a per-change budget read from the base settings. Small is not the same as low-risk, and a run
  of small changes passes. A binary file or a submodule pointer changed outside an outcome is over the limit.
- **Exempt paths** (default: `.odd/outcomes/**`, `**/*.md`, licence and ignore files, lockfiles).
- **Control files** (`.odd/odd.py`, `.odd/config.json`) need no outcome and are always reported when changed.
- **Test files** and **skips**, as above.

Exemptions are not verification. Each is printed with its line count.

## 7. How it reaches each tool

`odd init` writes the method, about thirty lines, into the root `AGENTS.md` between markers (at the top on first
insertion). That is the only rendered copy. If a Claude instruction file exists (`CLAUDE.md` or `.claude/CLAUDE.md`),
it gets one `@AGENTS.md` import line. Running `init` again replaces the block in place and leaves the rest of the file
as it was; the block is held under 2,600 characters and 32 lines by a test (about 2,260 and 30 today).

Step 5 of the method makes parking the sanctioned answer: when the agent is blocked, or the task cannot be done as asked
or the proof cannot honestly pass, it is told to STOP and explain with `odd park`, that parking is then the expected,
correct answer and not a failure, and that a forced pass (special-casing a test's inputs, editing, weakening or deleting
a test) is the wrong answer even when it turns the gate green. The wording follows ImpossibleBench, where an abort path
plus strict stop-and-explain wording cut cheating for GPT-5 from 54% to 9% and o3 from 49% to 12%, with little effect
on Opus 4.1, while "do not modify the tests" alone did not (docs/evidence/14-research.md, section 2.3). `odd park`'s
own message and the Claude Code Stop hook's block message use the same words (one constant, `PARK_WHEN`). This is
instruction text: it changes what the agent is told, not what the gate enforces, and its effect on cheating in this
tool has not been measured here.

| reads a root `AGENTS.md` without configuration | needs one line of configuration |
|---|---|
| Codex, Cursor, GitHub Copilot in VS Code (and its cloud agent and CLI), Claude Code (directly, or through the import), Junie, Windsurf/Devin | Gemini CLI, Aider, Copilot Chat outside VS Code |

The tool and the gate are the same for every agent and for a person.

Opt-in, per developer, never committed: `odd init --claude-hooks` adds two Claude Code hooks to
`.claude/settings.local.json`. At session start one line of status. At turn end, a block only when this turn changed
files and either a locally verified outcome has gone stale or more than the lane changed with no outcome in play.
The hook commands cannot exit non-zero.

**As MCP tools.** `odd init --mcp` copies `odd_mcp.py` (shipped beside `odd.py`, standard library only) into
`.odd/` and adds `"odd": {"command": "python3", "args": [".odd/odd_mcp.py"]}` under `mcpServers` in the project's
`.mcp.json`, keeping every other server and key; a `.mcp.json` it cannot read, or whose `mcpServers` is not an
object, stops `init` with exit 2 before anything is written. `.odd/odd_mcp.py` is a control file. The server speaks
JSON-RPC 2.0 over stdio and exposes `new`, `seal`, `done`, `gate`, `park` and `escaped`; each call runs `odd.py`
from beside it as a subprocess in the server's working directory and returns its exit code (in
`structuredContent.exit_code`, and `isError` when not 0) and everything it printed, so no logic is repeated.
Arguments of the wrong name or kind are refused (-32602) before odd runs. It is dual-era: it serves the stateless
MCP revision `2026-07-28` (`server/discover`, the version in each request's `_meta`) and the `initialize` handshake
of `2025-11-25` and earlier, echoing a requested legacy version it knows. Limits: the relative path in `.mcp.json`
assumes the client starts the server at the repository root (not checked against Claude Code); only a pipe
round trip in the tests has driven it, not Claude Code or another client; a call runs as long as odd does
(`proof_timeout` bounds each proof); the protocol's newer optional parts (subscriptions, tasks, input requests) are
not implemented. `pip install odd-tool` also installs an `odd-mcp` command.

## 8. Measurement

`odd stats` counts outcome files (total, skipped, parked, escaped) and local verification attempts, and splits
recorded escaped defects by kind of proof (section 9). It is self-reported and is never published as a result.

Published figures come only from the comparison harness in `bench/`: hidden acceptance tests, the harness's clock and
the token counts the agent CLI reports. It reports "gate passed, hidden tests failed" as its own figure: that is the
size of what this design does not catch.

Trust is reported as its own numbers, per arm (BACKLOG R1): claim precision (of the runs that said DONE, the share
the hidden tests passed), the silent-failure rate (said DONE and failed, over every expect-done run), on impossible
tasks the cheat rate (said DONE, deleted or took a line out of a shipped visible test, or wrote a visible test's
quoted input into added code) and the park rate, and the arm's own check against the hidden tests by changed lines.
The cheat routes are what a script can see in the tree and the transcript, not every cheat; the park rate uses the
hidden tests' keyword grade, which rejects some correct answers, so every impossible-task NOT DONE is listed with its
reason for a person to grade. All of this is in the harness only; nothing ships in `odd.py`.

## 9. Learning

A defect that escaped is recorded on the outcome it got past: `odd escaped <slug> "<what went wrong, where it was
found>"` appends `YYYY-MM-DD: <text>` (UTC date, whitespace collapsed) to that outcome's `escaped:` line, entries
joined by `; `, so the field stays one line. Then it becomes a new outcome whose proof fails on the escaped behaviour.
Changing only the `escaped:` line of a merged outcome does not put it back in play; any other edit to the file does.

`odd stats` prints, per outcome, the escape count, whether it is sealed, and the proof strength (k of n) of the
latest passing verification recorded on this machine; then, in total, escapes against outcomes split three ways:
sealed or not, take-out skipped or checked, and proof strength n of n, a mutant survived, or not measured here. Each
split reads `N in K of M`: N escapes in K of the M outcomes of that kind. There is no lessons database.

Limits: only recorded escapes are counted, so the figures are self-reported. Strength comes from local evidence, so
on another machine, or for an outcome verified before strength existed, it is "not measured here". Seal and skip are
read from the outcome file as it is now, not as it was when the defect escaped. An entry is counted by its
`YYYY-MM-DD: ` prefix after `; `; a free-text `escaped:` value written by hand counts as one, and text that itself
contains `; 2026-01-02: ` is counted twice. Before `odd escaped` existed this document suggested `escaped: <slug>` on the *new* outcome; such a
line still loads, and is now counted as one escape against the outcome that carries it.

## 10. Limits

- CI is the authority only under the three conditions in section 5. Nothing inside a repository can protect its own
  CI configuration. The change that adopts the tool is judged by its own copy and default settings; a person reviews it.
- The check shows that the proof depends on the change, not that it checks the outcome. A proof that only imports a
  new symbol fails on the tree without it. The strength check narrows this only for the few textual breaks it makes,
  on at most `mutants` of them: a survivor is a real gap, but no survivor does not prove the proof complete, a
  change with no operator or number in it gets no mutant, and a break that makes the code invalid (a generic
  `List<int>` read as a comparison) is "caught" by any proof. Proof strength is not correctness: a proof written after the code can
  catch every break and still pin a bug (arXiv 2607.22880), and every changed line run is not every case checked. Each run moves the files' modification times a few
  seconds further into the future. A flaky test counts as a failure. The last line of the failing run is
  printed for a person to read.
- The proof is written by the party being checked, so it can tell the reverted tree from the real one (git state,
  file hashes). This is not closed. The proof text is in the diff.
- Coverage is by path. An outcome with `in: **` puts every changed file inside its boundary. The gate shows lines per
  outcome; it does not prevent this.
- State outside tracked files (installed dependencies, build outputs, caches, databases) is not reverted. A
  dependency-only change, a generated file or a runner that selects tests from git state needs a skip.
- The proof's test must live in a file of its own under a test path. Tests in the same file as the product (Rust
  `#[cfg(test)]`, doctests) cannot be verified and need a skip.
- For the length of the failing run the tree holds base content, so a dev server, hot reload or file sync sees it.
- A proof that needs a real device, account or secret cannot be recomputed in CI. The tool has no "proven on the real
  system" label.
- Within one change a file belongs to one outcome.
- Changes are measured against the target branch. Work committed directly on it is not seen. A shallow clone is
  "could not run". Editing a merged outcome file puts it back in play.
- Windows, Git LFS and `autocrlf` are untested. A submodule change needs a skip.
- Only Claude Code has been run with it. The other tools' paths rest on their documentation.
- The empty-proof check reads output, so a proof that prints a convincing summary and exits 0 by itself gets past
  it; it covers four runners, conservatively (section 4). A go test that skips every test and a `| grep -q .` after a
  print are accepted though they check nothing; a print-only proof whose printed call into the change asserts inside
  the change is refused though it can check (section 4). `test-change:` takes any reason; one that names no
  test file covers every test edit in the change, whichever outcome it sits in (the gate shows it).
- Turning tests off is seen only through the files named in section 5. A deletion alone in a pytest section, a
  `-k`/`--deselect` passed in the proof command itself (that is in the diff as proof text), a `PYTEST_ADDOPTS`
  environment variable, a plugin installed outside the repository, a `load_tests` in a test module, or test
  selection written in a product file are not detected. The ids collected at the base and at the head are not
  compared.
- Every effectiveness figure is unmeasured until the comparison runs.
