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
  a pinned Action at 0.4.0 or older refuses the unknown field), `proof-by: <name>` (written by `odd spec`: which
  agent command wrote the sealed proof, section 3d; the same tool version, and the same refusal by an older one:
  delete the line for an older tool), `covers: R1, R3` (the ticket requirements this outcome covers, section 5a;
  the same tool version and the same refusal by an older one), `kind: bug` (section 4a), `asked: <question>`
  (written by `odd ask`: an open question, section 4b; the same tool version and the same refusal by an older one).

There is no status field. "Done" is never written to a committed file. A requirement becomes one or more outcome
files; their sentences and proofs are the specification, and each file is a task.

## 3. Commands

| command | what it does | exit |
|---|---|---|
| `odd init [--claude-hooks] [--mcp]` | installs or repairs: `.odd/odd.py`, `.odd/config.json`, the method in `AGENTS.md`, the import line in an existing Claude instruction file; prints the CI step, the conditions under which CI is the authority, and a proof suggestion (section 3a); `--mcp` also installs the MCP server (section 7) | 0 |
| `odd new <slug> "<outcome>" --proof CMD --in "GLOB, GLOB"` (comma-separated; `--in` may repeat) | writes the outcome file; `--proof auto [--test PATH]` picks the command (section 3a); `--covers R1,R3` writes `covers:` (section 5a; needs a tool newer than 0.4.0); `--kind bug|feature|refactor` writes `kind:` and prints a hint (sections 4a, 4c; needs a tool newer than 0.4.0); `--proof` may be left out only with `--kind refactor` (exit 2 otherwise, as before); refuses a sentence with no observable (section 4b; a tool newer than 0.4.0); after creating the file prints "read these first" (section 3f; a tool newer than 0.4.0) | 0, 1 refused (also: `auto` and no runner detected) |
| `odd seal <slug> [--base REF]` | optional: requires the proof to fail now, then fingerprints it in the outcome file (section 4) | 0 sealed, 1 already passes or no test file changed, 2 could not run |
| `odd done <slug> [--base REF]` | verifies the outcome (section 4) and records it locally | 0 verified, 1 not shown, 2 could not run |
| `odd race <slug> [--n N] [--agent CMD] [--base REF]` | N agent attempts at one outcome, each in its own git worktree, verified as `done` would; the winner is applied (section 3b); needs a tool newer than 0.4.0 | 0 winner applied, 1 none verified or the winner left as a patch, 2 could not run |
| `odd cascade <slug> [--agents C1,C2,...] [--race N] [--base REF]` | the agents in order, cheapest first, each level's attempts run and checked as in `race`; the next level only when none is verified, with the failure in its prompt; park after the last (section 3c); needs a tool newer than 0.4.0 | 0 verified attempt applied, 1 parked or the winner left as a patch, 2 could not run |
| `odd chain <ticket> [--race N] [--cascade] [--agents C1,C2,...] [--base REF]` | the outcomes in `.odd/chains/<ticket>.md` in order: each one without a checkpoint is raced (or cascaded), verified in your tree and committed as `odd: <slug> proven`; the first unproven one is parked and stops the chain, the tree back at the last checkpoint (section 3e); needs a tool newer than 0.4.0 | 0 every outcome proven, 1 an outcome parked, 2 could not run (a dirty tree, an unknown slug, a git failure: rolled back, not parked) |
| `odd spec <slug> --proof-by CMD [--tries N] [--base REF]` | another agent command (in practice a stronger model) writes only the proof in its own worktree; the test files come back and are sealed red (section 3d); retried, then parked; needs a tool newer than 0.4.0 | 0 proof brought back and sealed, 1 parked or refused (the proof passes in your tree, or did not apply), 2 could not run |
| `odd gate [--base REF] [--recompute] [--summary FILE] [--json FILE]` | checks the whole change (section 5); optionally also writes the result as Markdown or JSON | 0 pass, 1 fail, 2 could not run |
| `odd park <slug> "<reason>"` | the honest exit, for blocked work and for work that cannot be done as specified | 0 |
| `odd ask <slug> "<question>"` | records one open question as `asked:`; the gate reports the outcome as waiting for an answer (section 4b); needs a tool newer than 0.4.0 | 0, 1 not a question or no such outcome |
| `odd escaped <slug> "<what, where found>"` | records a defect that got past this outcome (section 9) | 0, 1 vague report or no such outcome |
| `odd stats` | counts, labelled self-reported, with escaped defects split by kind of proof, and dollars and seconds per proven outcome from agent attempts (section 3h; the cost table needs a tool newer than 0.4.0) | 0 |

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

1. **Working trees.** Each attempt gets its own working tree of HEAD under the git directory
   (`.git/odd/race/run-<pid>/<n>`), never the user's tree. Since the B3 commit it is a clone that reads the
   user's objects (`git clone --shared --no-checkout`, then a detached checkout of HEAD; the remote is removed and the
   user's `info/exclude` copied in), not a `git worktree add`: a linked worktree shares the user's `.git/config`,
   hooks, `info/` and refs, so an attempt's plain `git config core.fsmonitor ...` or a hook it wrote ran on every
   later git call in the user's repository, even after the attempt was discarded (review finding, test
   `Isolation`). The outcome file, the changed test files and `.odd/config.json` are copied in as they are in the
   user's tree and committed there as the attempt's start. Uncommitted product changes in the user's tree are not
   copied. Settings in the user's repository-local config (not the global one) do not apply inside an attempt, and an
   agent that commits needs a global `user.name`/`user.email`.
2. **Agents run in parallel**, each in its own process group with stdin closed or the prompt, its output in
   `.git/odd/race/<slug>/agent-<n>.log`. At `race_timeout` seconds (default 1800) an agent is killed with its process
   group; when an agent ends, whatever it left running in its group is killed before its attempt is checked. Each
   agent starts with `ODD_ATTEMPT=<its working tree>/` in its environment; on Linux odd then reads `/proc` for any
   process still carrying that mark (one it detached with `setsid`, a daemon), kills it and refuses the attempt with
   `left process <pid> running (killed)`; the same sweep runs when a run is removed, including a run left by a
   killed odd. Not covered: a process that clears its environment, and systems without `/proc` (macOS), where only
   the process group is killed.
3. **Each attempt is checked when it ends**, one at a time, inside its worktree (`_settle()` first: its git config,
   `info/` and hooks put back as odd made them and its index reset to the start, so a `core.fsmonitor`, an exclude
   rule or `git update-index --assume-unchanged` cannot hide an edited file from the check or run during it; and
   the ignored files the agent created that the user's tree does not have are removed, because the applied patch
   carries no ignored file, so a winner cannot lean on one): it must not have edited the copied
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
6. **Cleanup**: the working trees are removed when the race ends, also on SIGTERM/SIGINT (agents killed first). After
   a kill -9 the next race, cascade or spec removes runs whose process is gone, and on Linux kills their agents still
   carrying the mark.

Limits: verification is sequential, so N attempts cost N verifications after the agents; the attempts share the
machine, so a timing-sensitive proof may behave differently under load; installed dependencies and caches outside
the worktree are shared; nothing stops an agent from writing outside its worktree on purpose (it runs as the user:
absolute paths, `git -C <your repo>`, the path in the clone's `objects/info/alternates`). An ignored file the agent
created that your tree also has is kept for the check whatever its content (a dependency directory such as
`node_modules` stays usable); one your tree lacks is removed, so an agent that installs dependencies into an ignored
directory your tree does not have yet gets "could not verify". Measured (fake agents, this machine): see BACKLOG
item 1; the clone costs 0.06-0.08 s of setup and clean-up per attempt against 0.03-0.04 s for the linked worktree
(5 runs each, 4 attempts, three-file repository).

### 3c. `odd cascade`: the cheapest agent first, pay more only when the proof says so

`odd cascade <slug>` tries the agent commands in order, one level each: `--agents "C1,C2,..."` (split on commas, so a
command containing a comma belongs in the setting instead) or the `"agents"` setting read as an ordered list,
cheapest first. Race reads the same setting as commands used in turn; cascade reads it as levels. Each level is one
call of race's attempt machinery (`_attempts()`): a fresh worktree of HEAD per attempt with the outcome and its tests
copied in, the agent in its own process group with `race_timeout`, and the same check (`_judge()`: copied files and
control files untouched, product changes inside `in:`, then `prove()`). `--race N` (default 1) runs N attempts of the
level's agent in parallel, ranked as in race. Every level starts from HEAD and the user's outcome and tests, never
from an earlier level's attempt.

1. **Stop at the first verified level**: its best attempt is applied exactly as race applies a winner (`_apply()`:
   only when nothing inside `in:` differs from HEAD in the user's tree, else `winner.patch` and exit 1). Later levels
   never run.
2. **Escalate with the failure passed on**: when no attempt at a level is verified, the next level's prompt gets, for
   every earlier attempt, the agent command and the whole finding of the check that refused it (up to 1500
   characters each): the proof's failing output, the surviving small breaks with their lines ("calc.py:6 - -> +:
   return a - b"), the changed lines the proof never ran, an edited test file, a timeout; then that attempt's `next:`
   block (section 4d).
3. **Park after the last level**: the outcome gets a `parked:` line naming each attempt and the first line of why it
   was refused, nothing is applied, and the full record (command, reason, finding, lines, seconds, cost per attempt)
   is written to `.git/odd/cascade/<slug>/cascade.json` beside the prompts and agent logs; exit 1. To try again,
   delete the `parked:` line.
4. **Output**: one table row per attempt (level, or level.attempt with `--race`; agent; cost; strength; lines; agent
   and verification seconds; verified or why not) and the sum of the reported costs.

**Cost** is what the agent says it cost: the last line of its output of the form `odd-cost: <usd>` (an optional `$`,
digits, an optional fraction, nothing else on the line). An agent that prints none shows "not reported"; odd never
estimates a price and never reads a vendor's output format. A wrapper script around a CLI agent is the place to print
it. `--race` needs no new setting; cascade uses `agents`, `race_timeout` and `race_seal`, so it too needs a tool newer
than 0.4.0.

Limits: the levels run one after another, so a failed cheap level adds its agent time and verification to the cost of
the dear one; the ordering is the user's (odd does not know which agent is cheaper); a cheap attempt that is verified
with surviving breaks under `"strength": "report"` stops the cascade (use `"enforce"` to escalate on a survivor);
the same limits as race on shared caches and agents writing outside their worktree. Measured (fake agents, this
machine): see BACKLOG item 2.

### 3d. `odd spec --proof-by`: one agent writes the proof, another writes the code

`odd spec <slug> --proof-by CMD` runs CMD, an agent command like the ones in `"agents"`, to write only the proof of an
outcome that `odd new` created. The author works in a fresh detached worktree of HEAD under the git directory with
the outcome file (and `.odd/config.json`) copied in (`_worktree()`, shared with race), in its own process group with
`race_timeout` (`_launch()`). Its prompt states the outcome, the proof command, the boundary it must not change and
the test globs, and that the proof must fail before the code. When it exits, odd checks the worktree
(`_proof_check()`, after the same `_settle()` as race, so a process the author detached refuses the try): only test files changed (a product file, a control file or the outcome file refuses the try), at
least one test file, and the proof command, run there, exits non-zero and is not unrunnable (the same `unrunnable()`
rule as `odd seal`). A refused try's reason goes into the next try's prompt. After at most `--tries`, or the
`"proof_tries"` setting (default 3, 1 to 32), the outcome gets a `parked:` line naming the author and each reason, the
journal records it, nothing is brought back, and the exit is 1.

An accepted proof is brought back as a patch of the test files only (`git apply`, all or nothing; a file that differs
in your tree makes it fail and the patch stays in `.git/odd/spec/<slug>/proof.patch`). Then `odd seal` runs in your
tree as it would by hand (`cmd_seal()`): the proof must fail there too. If it does not (for example the code is
already in your tree, uncommitted), the patch is reversed, so your tree is as it was, and the exit is 1. On success
the outcome gets `proof-by: <name>`: the command with environment assignments (`TOKEN=...`), the values of options
whose name looks like a credential (`--api-key X`, `--token=X`) and `{prompt_file}` removed, shortened. It names the
author for a reviewer; it is not proof of who ran.

Then `odd race` and `odd cascade` run with the sealed proof unchanged: the brought-back test files are changed test
files, so `_race_start()` puts them in the files an attempt must leave alone, and an attempt that edits them is
refused (and `check_seal()` refuses any later edit in your tree). Setting: `proof_tries`; field: `proof-by`; both need
a tool newer than 0.4.0.

**Why, and what to measure.** ExecCritic (arXiv 2609.09133; docs/evidence/14-research.md section 2.5): with the
repairing agent fixed, tests written by the weak base model lowered resolution from 61.2% to 57.3%, and tests from a
stronger model raised it to 65.3%. So the same weak agent writing its own proof can hurt, and a stronger author is the
likeliest place for a correctness gain on a cheap implementer. That is a paper's number, not ours: the measurement
still to run is a cheap implementer with a cheap-model sealed proof against the same implementer with a strong-model
sealed proof, scored on hidden tests, plus the cost of the extra call (BACKLOG item 3).

Limits: odd checks that the proof is red, touches only test files and stays sealed; it cannot check that the proof
tests the outcome rather than something easier to fail (a stronger author, the strength check after the code, and a
reviewer reading the proof are the defences). A kill during the author's run leaves your tree untouched (the
worktree is removed on the next race, cascade or spec); a kill between bringing the proof back and sealing it can
leave the unsealed test files in your tree. The author can write outside its worktree, as in race.

### 3e. `odd chain`: a long task as a chain of proven outcomes

`odd chain <ticket> [--race N] [--cascade] [--agents C1,C2] [--base REF]` reads `.odd/chains/<ticket>.md`: one outcome
slug per line, in order (blank lines, `#` comments and a leading `- ` or `* ` are allowed; each slug once; every slug
must name an outcome file, else exit 2 before any agent runs). It takes the outcomes one at a time:

1. **Already proven** when HEAD's history holds a commit whose subject is exactly `odd: <slug> proven` and no newer
   `Revert "odd: <slug> proven"` (`_checkpoint()`): skipped, no agent runs.
2. **Otherwise attempted** by race's machinery (`_race_run()`, the core `odd race` now calls: N attempts, the agents
   in turn, default as race) or with `--cascade` by cascade's (`_cascade_run()`: the agents as levels, `--race` per
   level, default 1). Nothing new judges an attempt: `_attempts()`, `_judge()` and `prove()` in each attempt's own
   working tree under the git directory, as section 3b describes.
3. **Applied, verified here, checkpointed**: the winner is applied with `_apply()`, verified again in the user's tree
   with `prove()` (as `odd done` would, recording local evidence through `_verified()`, shared with done), and
   committed as `odd: <slug> proven` with only these paths: the winner's files, the outcome file, the chain file and
   the test files the proof names (`proof_runs()`) or its seal holds. A later outcome's red test stays uncommitted, so
   no checkpoint carries a failing proof of an outcome not yet done.
4. **An unproven outcome stops the chain**: no attempt verified (or the apply or the check here failed) parks it with
   `parked: odd chain <ticket> (<date>): attempt 1: <why>; attempt 2: ...`, exit 1, with the next: block of every
   attempt. If the winner was already applied when something failed, its patch is reversed (`git apply -R`, the same
   `_patch()`), so the tree is back at the last checkpoint; this also runs on Ctrl-C and SIGTERM. A git failure (the
   checkpoint commit refused by a hook, say) rolls back the same way but does not park: exit 2, status `stopped`.
5. **Status**: every run ends with one line per outcome: `proven (<commit>)`, `parked: <reason>`, `stopped: ...` or
   `not started`.

**Resume**: run the same command again; proven outcomes are skipped by their checkpoint commit and the chain
continues at the first one without it. A parked outcome in the chain is attempted again (the rerun is the request);
its `parked:` line goes when it is proven. To skip an outcome, take it out of the chain file.

**The user's work is never at risk**: the chain refuses to start (exit 2) when the tree or index differs from HEAD
anywhere but the chain file, the chain's outcome files and test files (both are checked: `git diff HEAD` and `git
diff --cached HEAD`), and it never resets: the only write it undoes is the patch it applied, and what the failed step
staged is unstaged again, so the index and the tree are both at the last checkpoint. An uncommitted edit of yours to a
test file the proof names goes into that outcome's checkpoint commit with the rest. New command and MCP tool `chain`; no new setting (it uses `agents`, `race_timeout`,
`race_seal`), so it needs a tool newer than 0.4.0.

Limits: a kill with SIGKILL between applying a winner and committing its checkpoint leaves the winner's files
uncommitted; the next run refuses to start and names them (nothing is lost, nothing is guessed). The checkpoint is
recognised by its commit subject, so a checkpoint commit squashed or reworded away is attempted again, and an outcome
whose proof or `in:` was edited after its checkpoint is not re-proven by the chain (`odd gate` and the regression
guard of section 5b still judge it). Commit hooks of the repository run on every checkpoint. Outcomes run one after
another; nothing runs two outcomes of one chain in parallel. Measured (fake agents, this machine): see BACKLOG
item 10.

### 3f. Boundary as context: "read these first"

A tool newer than 0.4.0 (backlog item 13; no setting). After `odd new` writes the outcome file (also through the MCP
`new` tool, which returns odd's output) it prints, under the heading `read these first`, the files inside the
outcome's `in:` boundary that exist (tracked or untracked and not ignored, never under `.odd/`), at most ten
(`READ_FIRST`), the largest change against the base first (changed lines from `sizes()`, the helper the small-change
lane uses; a binary counts as no lines), then the largest file, then by path, with `and N more` past the cap; and
`the proof runs: <files>`, the repository files the proof command names (`proof_runs()`, the reader the
take-out check uses). The prompt file of `race`, `cascade` and `chain` (`_prompt()`) carries the same block, computed
in the user's tree from the same base, so an agent starts from the boundary instead of exploring the repository.
Without a target branch to measure from (no `main`, `master` or `--base`), `new` lists against the empty tree, so
every file counts its whole length as changed. Limits: the list is a reading order, not a closure (imports of a
listed file and callers outside the boundary are not listed); a proof that reaches its tests through `cd` or a
script is read as text, as in the take-out check; whether the list cuts an agent's turns and tokens (the item's
measure) is not measured.

### 3g. Attempt budget per outcome: `"max_attempts"`

A tool newer than 0.4.0 (backlog item 15; the Action at v0.4.0 refuses `"max_attempts"` as an unknown setting, so
set it only once the tool in use is newer). `"max_attempts"` (an integer, default 0 = off) parks an outcome once its
failed attempts reach the number. The count comes from local evidence under the git directory (`failures()` reads the
log `record()` writes): every failed `odd done` (the `ok: false` line it already wrote; a run that could not run,
exit 2, is not an attempt) and every attempt of `race`, `cascade` or `chain` that `_judge()` refused (one
`failed: "attempt <name>"` line each, written by `_attempts()`, the machinery all three share). It counts from the
latest verified `done` or the latest budget park, whichever is newer. When the count reaches the limit,
`budget()` writes `parked: odd: attempt budget reached (N failed attempts, <date>): <the first line of each
reason>`, records the park as the new starting point, and the command exits 1 with `attempt budget reached: N failed
attempt(s) at <slug>; parked ...`; `done` prints that line in place of its `next:` block. A race or chain checks the
count after its attempts; a cascade also checks it between levels and runs no further level once it is reached (the
spend the item is about); a chain parks the outcome with the budget's line after `odd chain <ticket>`. A race whose
winner is verified is not parked, although its refused attempts are counted until the next verified `done`. Resetting
is deleting the `parked:` line, as for any park. The number is never shown to an agent in advance: neither the
`AGENTS.md` block nor a race, cascade or chain prompt mentions it, because a budget the agent could see made agents
skip review and spec steps in the pilot ([12](docs/evidence/12-pilot.md)); the agent sees it only once reached.

Limits: the evidence is per machine and per worktree (`state_dir()`), so attempts on another machine, in CI or in a
fresh clone are not counted, and deleting `.git/odd/evidence/` resets every count; an agent that runs `odd done` in
a loop still uses the full budget; `odd stats` counts refused race attempts only in its cost table (section 3h), not
in its attempts column; the parked line is
the reason list cut to the first line of each reason (up to 160 characters), the full findings stay in the race and
cascade logs. The spend saved on tasks that end unsolved (the item's measure) is not measured on real agents.

### 3h. Cost per proven outcome

A tool newer than 0.4.0 (backlog item 16; no new setting). Every attempt that `race`, `cascade` or `chain` runs (all
three go through `_attempts()`) writes one line to the outcome's local evidence (`record()`, under the git directory,
never committed): `attempt` (its name), `cost` (the agent's last `odd-cost: <usd>` line, parsed by `_cost()` as for
the cascade table, or null when it printed none) and `seconds` (the agent's seconds plus the verification's, rounded
to 0.1). A refused attempt's line also carries `failed` and `why`, the same keys the attempt budget (3g) counts; a
verified attempt's line carries neither, so it is not a failure.

`odd stats` ends with a table headed `cost per proven outcome (self-reported: ...)`: per outcome with at least one
attempt, the attempts, how many reported a cost, dollars, seconds and whether a `done` here has verified the outcome
(`proven`); then a total line: dollars and seconds over all attempts, failed attempts and unproven outcomes included,
divided by the number of proven outcomes among them, and how many attempts reported a cost. Without any attempt it says
`no race, cascade or chain attempt recorded here`.

Limits: dollars are what the agent command says, unchecked; an attempt that prints no line adds nothing to the dollars,
so the dollar figure is a floor whenever "cost reported for k of n" has k < n. Seconds are summed per attempt, so a
race of three parallel attempts counts about three times its wall clock; they are not the agent's turns or tokens
(the item's "turns" is not recorded: odd sees no turns, only a command's output). Work done outside race, cascade and
chain (an agent session that ends in `odd done`, `odd spec --proof-by`) is not counted. The evidence is per machine and
worktree, as for the budget. Not measured on real agents; the tests use fake agents that print a cost.

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
  and the settings are read from the base revision, so a change cannot loosen its own gate. The one exception is
  opt-in: a `"cache_file"` from the target branch's settings, outside the repository, holding results an earlier
  `--recompute` wrote (section 5d).
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

### 5a. Requirement coverage

A ticket's requirements can be recorded once, before any outcome, as numbered lines in
`.odd/requirements/<ticket>.md` (`R1: ...`, `R2: ...`, also as list items; any other line is prose and ignored),
written by the agent or a person. Each outcome names the ones it covers with `covers: R1, R3` (`odd new --covers`).
For every requirements file added or changed in the change, `odd gate` (local and `--recompute`) prints
`requirements <ticket>: k of n covered; not covered: R2 (<text>)` and, when a requirement listed at the base is gone,
`removed in this change: R4`; the `--summary` lists each requirement with the outcomes that cover it, and `--json`
has a `requirements` list. A parked or asked outcome covers nothing (an asked one counts again once its `asked:`
line is deleted). The setting `"coverage"` decides the rest:

- `"report"` (the default): an uncovered requirement is printed, not a Fail.
- `"enforce"`: an uncovered requirement is a Fail, with the remedy (cover it, or take it out of the file).
- `"off"`: no requirement is read and `covers:` is ignored.

Under `"report"` and `"enforce"` a `covers:` id that names no requirement is always a Fail: an id missing from the
file, a plain id when the change has no requirements file or more than one (then write `<ticket>:R1`), a malformed
id, a requirement listed twice, or a requirements file with no `R<n>:` line. `<ticket>:R1` may also name a ticket
recorded in an earlier change; it is checked to exist and counts for nothing. `covers:` is not part of what `odd done`
verified, so changing it needs no new `done`. Setting `coverage` and field `covers` need a tool newer than 0.4.0.

Limits: odd checks that every listed requirement is named by some outcome, not that the outcome's proof tests it, and
not that the list is the whole ticket: whoever writes the list can leave a requirement out, and a requirement removed
in the change is printed but not refused (review reads the list). Requirements files are exempt only through the
default `**/*.md` exemption; a custom `"exempt"` list without it makes them product files. Not measured: requirements
missed per task with and without the check (BACKLOG item 4).

### 5b. Regression guard: earlier proofs run again

A merged outcome keeps its outcome file, and so its proof, in the repository. `odd gate` (local and `--recompute`)
then also runs the proof of every **earlier outcome** whose boundary (`in:`) holds a file this change touches (a
product or test file). An earlier outcome is one whose file is tracked at the base (the commit it last changed in at
the base is its "proven in" commit) and is not in play in this change; parked, asked and skipped (`counterfactual:
skip`) ones are not guards. Each guard's proof runs once on the tree as it is: green only, no take-out run, no
strength check, so the cost is one proof run per guard. The gate prints `guard   <slug> (proven in <commit>): still
passes, <s>s` per guard and how many earlier proofs it skipped as unaffected (5d), `--json` has a `guards` list and the `--summary` a **Guards** list. `odd done` prints the
gate for the whole change afterwards, so it runs the guards too (its own exit code is unchanged). The setting
`"guard"` decides what a failing guard does:

- `"enforce"` (the default): it fails the gate with `<slug> (proven in <commit>) now fails: <last line of its output>`
  and the proof command. A guard that times out fails the same way.
- `"report"`: the same line is printed, the gate does not fail on it.
- `"off"`: no earlier proof runs.

Setting `guard` needs a tool newer than 0.4.0. A repository that vendors the new tool gets `"enforce"`: a later
change that touches an earlier outcome's files now costs one proof run per such outcome and fails when that proof
fails; set `"off"` for the earlier behaviour. In CI the setting is read from the target branch, like every setting.

Three cases run a guard that is **reported and never fails the gate** (a tool newer than 0.4.0 after this fix), each
with the outcome as it is at the base: a merged outcome this change parks or asks (`guard   <slug> (proven in
<commit>), parked in this change, now fails: ...`), and a merged outcome whose file this change deletes (`..., its
outcome file is deleted in this change, ...`); the gate also prints `deleted <slug> (merged in <commit>)`, `--json`
has a `deleted` list and the `--summary` a **Deleted outcomes** list, and the auto lane (5c) goes to review. An edit
to only the `escaped:` line keeps an earlier outcome out of play (section 9), so it stays a guard.

Limits: overlap is by path, so a change that breaks an earlier outcome through a file outside its `in:` (an import, a
config read at run time) runs no guard; widen `in:` to what the proof depends on. An earlier outcome whose file this
change edits otherwise is in play and must pass `done` again. Deleting a merged outcome, or parking it, does not fail
the gate even when its proof now fails: it is reported, and a reviewer decides (deleting a feature with its outcome is
legitimate). A flaky earlier proof fails the gate. Not measured: earlier outcomes broken by later changes
on a multi-step task sequence, with and without the guard (BACKLOG item 9).

### 5c. Auto-merge lane: a flag the repository's merge rules may use

Off unless `.odd/config.json` sets `"auto_lane": true` (a tool newer than 0.4.0; in CI read from the target branch,
like every setting). Then `odd gate` (local and `--recompute`) adds a result: `"lane": "auto"` when every condition
below holds, else `"lane": "review"` with every reason that failed (none is weighed against the others). It appears
as `lane` and `lane_reasons` in `--json`, as the line `lane    auto ...` or `lane    review: <reasons>` in the
printed result, as `Auto-merge lane: yes` or `Auto-merge lane: no, because <reasons>` in the `--summary` (the
pull-request comment), and as the Action output `odd_lane` (`auto`, `review`, or `off` when the setting is off;
`review` when the Action could not read the result). **odd never merges**; the flag only says the change qualifies.
The exit code is the gate's, unchanged.

The conditions (each one failing is a reason, in the words shown):

- the gate passed (`the gate did not pass`), and at least one outcome in the change is verified (`no verified outcome
  in this change`);
- each verified outcome's recorded proof strength (the small breaks of section 4, measured by `done` or `--recompute`):
  measured (`proof strength was not measured`, e.g. under `"strength": "off"`), at least one break made (`no small
  break could be made`), at least the share `"auto_min_strength"` caught (default `1.0`: k of n with k = n; `proof
  strength k of n, below ...`), no break that did not run to completion, and no changed line the proof never runs
  (`not run by the proof: ...`);
- no skipped take-out check (`counterfactual: skip`), no parked or asked outcome in the change;
- at most `"auto_max_lines"` changed product lines (default 120; test files, exempt paths and outcome files do not
  count), and no line outside every outcome (the small-change lane is unverified, so it disqualifies);
- no control file changed, no existing test changed under a `test-change:` reason;
- the regression guard (5b) is on and every guard passed (a guard failing under `"report"` disqualifies;
  `"guard": "off"` disqualifies), and no merged outcome's file is deleted (`outcome <slug> (merged in <commit>) is
  deleted in this change`).

Wiring it (a sketch; not run by any test here, and `uses:` must pin the odd version you vendor): a branch-protection
rule (or ruleset) on the target requires the `odd` check, and the repository allows auto-merge. Then:

```yaml
on: pull_request
permissions: {contents: write, pull-requests: write}
jobs:
  odd:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: {fetch-depth: 0}
      - id: odd
        uses: varunkan/ODD-Outcome-Driven-Development@<a tag newer than v0.4.0>
      - if: steps.odd.outputs.odd_lane == 'auto'
        run: gh pr merge --auto --squash "${{ github.event.pull_request.number }}"
        env: {GH_TOKEN: "${{ github.token }}"}
```

GitHub's auto-merge still waits for every required check. A repository whose branch protection requires a human
approval gets no auto-merge from this; it must lift that requirement for the lane, which is the risk below. Key only
on `== 'auto'`: `review` and `off` both mean a person reviews.

Risk, stated plainly: a change in the auto lane merges with nobody reading its code. What stands between it and
`main` is the outcome sentence, the proof and the checks above. A proof that is strong against odd's small breaks can
still miss behaviour outside the changed lines, test the wrong thing, or encode a wrong requirement; an outcome
sentence can be wrong. The lines-run check exists for Python only: for other languages "no changed line the proof
never runs" is not measured and the lane relies on k of n alone. Requirement coverage (5a) is not a condition.
Mutants are capped by `"mutants"` (8 by default) and sampled, so k = n is of the breaks made, not of every possible
fault. A local `odd gate` reads recorded results, which can be forged; only the Action's `--recompute` decides
anything a merge rule should trust. Not measured: review minutes per merged change or defects escaping through the
lane (BACKLOG item 11).

### 5d. Verification cache and affected guards

`odd done`, `race`, `cascade`, `chain` and `gate --recompute` all verify through one function, `verify()`. Before
it runs a proof it computes a key over everything the check reads (`verify_key()`): the tool (its version and the
sha256 of its own file), every setting in force (under `--recompute` the target branch's), the base commit (what the
take-out check restores), and the state (content, mode, link target) of every path that differs from the base, the
same `_state()` the local gate's content hash uses. With the base commit that names every tracked and untracked file
the proof could read, inside the boundary or not, the outcome file and `.odd/config.json` included. When a
verification with that key passed before, its result is returned with `cached` set to when it ran, and the report
says `cached (verified at <time>): ...`; no proof runs. A failed or "could not run" check is never stored. `--no-cache`
(on `done`, `gate`, `race`, `cascade`, `chain`, and the MCP tools) runs it in full. A changed path that is a
directory (a submodule) gives no key, so that outcome always runs in full.

Where it is kept:

- **Locally**: `.git/odd/verified.json` (the common git directory, so a linked worktree shares it), or `"cache_file"`
  (relative to the repository root) when set. Race, cascade and chain attempts run in clones under the git directory;
  they read and write the user's cache, so `odd done` after a race reuses the winner's verification.
- **Under `--recompute`**: only `"cache_file"` read from the target branch's settings, after `~` and `$VAR`
  expansion, and only when it is an absolute path outside the work tree and outside the git directory; anything else
  prints `cache   "cache_file" not used under --recompute: ...` and every outcome runs in full. Only entries written
  by an earlier `--recompute` are trusted there (an entry carries `mode`), so what `odd done` writes never satisfies
  CI. Without `"cache_file"`, `--recompute` uses no cache, as before.

The file is read once, before any proof (or, for race, any agent) of the process runs, and each write puts back that
snapshot plus the entries this process added (atomic rename), also at the end of every `gate --recompute` and every
race; so what a proof or an agent writes to the file during the run is dropped. At most 1000 entries are kept, the
newest. A write that fails loses only the cache.

For CI, a cache step saves and restores the file. Restore it on pull requests and save it only from runs on the
target branch (`actions/cache/restore` on `pull_request`, `actions/cache/save` on `push` to the default branch), so a
pull request's own proofs never write the file a later run trusts. This recipe is not run on GitHub Actions here.

`"cache_file"` needs a tool newer than 0.4.0: the Action at v0.4.0 refuses it as an unknown setting, so set it only
once the pinned Action is newer. Without it, nothing changes in CI; locally `odd done` caches by default.

**Affected guards.** The regression guard (5b) already selects earlier proofs by path. The gate now also prints
`guard   N earlier proof(s) skipped as unaffected: no file this change touches is inside their boundaries` and
`--json` has `guards_skipped`; it counts merged, not parked, asked or skipped outcomes whose boundary holds no touched
file.

Measured (one machine, Python 3.13, the fixture of `tests/test_odd.py`, script
`measure.sh` in the step's scratch): a first `odd done` 0.91 s and a second 0.22 s; a first `gate --recompute` 0.73 s,
a second 0.16 s, `--no-cache` 0.70 s, and after a one-byte change to the product file 0.70 s. With a proof whose test
sleeps 1 s: 5.70 s and 0.20 s for done, 5.66 s and 0.16 s for the gate, 5.70 s after a one-byte change. Tests
(`VerifyCache`) show that a one-byte change in each input kind forces a full run: the proof command, a setting, a
file inside the boundary, a test file the proof runs, an unchanged-at-base file outside the boundary, the tool, the
base commit, and a setting changed only on the target branch under `--recompute`.

Limits: ignored files (build output, `node_modules`, a virtualenv), installed packages, the environment, the clock,
the network and anything outside the repository are not in the key: a proof whose result depends on them gets the
earlier result until a tracked or untracked file, a setting or the tool changes; `--no-cache` or a dependency file in
the repository covers that. A flaky proof that passed once stays passed for that content. A `"cache_file"` outside the
repository can be written by anything else on the machine, and a process a proof starts that escapes its process
group could write it after odd exits; the restore-on-PR, save-on-target recipe is what keeps a pull request from
planting entries. Not measured: seconds saved per CI gate on a real repository, and false passes on real work (none
seen in the tests, which is not the same).

### 4a. Reproduce first: `kind: bug`

An outcome may carry `kind: bug` (`odd new ... --kind bug`; needs a tool newer than 0.4.0; the kinds are `bug`,
`feature` and `refactor` (section 4c), any other value is refused). For a bug outcome `odd seal` and `odd done` (and so `odd gate --recompute`) require the proof
to fail at the base revision, and print how it failed as `reproduced: <last line of its output>`. The base run is the
take-out of section 4, unchanged: taking out every changed product file inside the outcome's `in:` puts back exactly
the base version of those files (a file the change added is removed). `odd seal` on a bug outcome takes the fix out
the same way when one is already written, so it can be sealed after the fix too; plain outcomes still require the
proof to fail in the tree as it is. A proof that passes at the base is refused by both, exit 1: "the proof does not
reproduce the bug". `counterfactual: skip` is refused on a bug outcome. Outcomes without `kind:` behave as before.

Giving the rule up by editing `kind: bug` to another kind (for example `kind: refactor` with a skip line) is shown, not
prevented: a sealed outcome's `sealed:` line ends with `kind@<kind>` when it has a kind, so a sealed bug outcome whose
kind changes fails `done` and the gate ("the kind (sealed as bug)") until it is resealed; and every `done` and `seal`
records the kind in local evidence, so the local gate prints `kind changed from bug to <kind>` under the outcome and
`(N changed kind from bug: <slugs>)` on the verdict line, and `--summary` marks it. Limits: an unsealed outcome that was
never run as `kind: bug` on this machine leaves no trace, and `--recompute` in CI has no local evidence, so there only
the seal shows it; seals written before this change carry no `kind@` entry and are not checked for kind.

Where "the take-out" and "the base revision" differ: (1) only the outcome's own product files go back; product files
of other outcomes, files outside every `in:`, test files and exempt files stay as they are in the tree; (2) a new
product file the proof imports is removed, so the proof fails with an import error and that counts as reproduced,
though it is not the reported symptom: the `reproduced:` line shows it, and a reviewer reads it; (3) the proof
itself is the tree's version, since a test written for the bug did not exist at the base. odd cannot tell whether the
failure is the reported behaviour; it shows the line. Measured: `tests/test_odd.py` class `ReproduceFirst`. Not
measured: false "done" on bug tasks with and without it (BACKLOG item 5).

### 4b. Ambiguity stop: no observable, ask instead

`odd new` refuses an outcome sentence that has neither a verb of observation (sees, gets, receives, returns, shows,
prints, is refused, ...) nor a measurable term (a digit, `%`, a number word, every, each, only, exactly, within,
under, at most, seconds, errors, ...), exit 1, and suggests the form "<who> <observes> <what>, measurably". A state
predicate ("is disabled", "becomes visible", "keeps", "no longer", "still"), a capability ("can export") and common
domain verbs (export, split, save, delete, open, close, ...) count as observation. "The tests pass" does not: a phrase
whose subject is only the tests, the suite, the build or CI passing or succeeding is taken out before the check, so
"Improve the code so the tests pass." is refused. The test is English word lists in `odd.py` (`OBSERVE`, `MEASURE`,
`SUITE_PASSES`), never a model, and is meant to be wide: it refuses "Refactor the billing module." and "Make search
better and faster.", and passes every example in the README, the demo and the tests, plus the ordinary sentences in
class `AmbiguityStop` ("The login button is disabled while the request is pending.", "A cashier can split a bill
between guests."). It cannot tell a checkable sentence from one that only contains a listed word ("Users see a nicer
page." and "Clean the code so it still works." pass), an ordinary sentence built from words not in the lists is
refused, and a sentence in another language is likely refused: set `"ambiguity_stop": false` in
`.odd/config.json` to turn the check off (default `true`; the setting needs a tool newer than 0.4.0, and an older tool
refuses the unknown setting).

When the outcome cannot be made checkable from the ticket, the method tells the agent to ask one precise question
and stop. `odd ask <slug> "<question>"` writes it as `asked: <question>` (one line, ending in `?`, at least 15
characters). Such an outcome is not a fail and not parked: the gate prints `asked   <slug>: <question> (waiting for an
answer; ...)`, adds `(N waiting for an answer: <slugs>)` to the verdict line, and reports state `asked` in `--json`
and "waiting for an answer" in `--summary`. Like a parked outcome it covers no files, so code written before the
answer is outside every outcome and fails the gate as usual (the exit codes keep their meaning: only the outcome file
changed means PASS). `odd done` (and so `race` and `cascade`) refuses an asked outcome, exit 1. Answering is deleting
the `asked:` line, with the answer written into the sentence, proof or notes. Measured: `tests/test_odd.py` class
`AmbiguityStop`. Not measured: rework and wrong-problem rate on vague tasks with and without it (BACKLOG item 6).


### 4c. Templates by kind of change: `odd new --kind bug|feature|refactor`

Needs a tool newer than 0.4.0. `--kind` writes `kind: <kind>`, fills the kind's defaults, and prints one line
`hint (<kind>): ...` after the file is written (`HINTS` in odd.py); without `--kind` nothing changes and no hint is
printed.

| kind | defaults written | what `seal`/`done` then do | hint |
|---|---|---|---|
| `bug` | `kind: bug` | require the proof to fail at the base revision (section 4a) | reproduce first, then fix |
| `feature` | `kind: feature`; the proof as given | as for an outcome without a kind | the proof covers the new behaviour; keep the existing suite green (the proof alone does not run it) |
| `refactor` | `kind: refactor`; `counterfactual: skip - behaviour-preserving refactor`; `--proof` optional, defaulting to `auto` with the runner's whole suite | `done` passes when the proof passes and no existing test changed unexplained (section 4's take-out and the strength check are skipped, as for any `counterfactual: skip`) | the existing suite is the proof; do not change the tests to fit |

The whole-suite command per runner is `SUITES` in odd.py, picked by the same detection as `--proof auto` (section
3a): `python3 -m pytest -q`, `npx jest`, `npx vitest run`, `node --test`, `npx mocha`, `go test ./...`, `cargo test`,
`python3 -m unittest discover -q -s tests` (or `-s test`, or no `-s` when neither folder exists), `make test`.
`--proof auto --test PATH` with `--kind refactor` keeps the one test file; an explicit `--proof` is kept as given.
No runner detected: refused, exit 1, as for `--proof auto`. Limits: `feature` adds only the field and the hint; odd
does not run the existing suite for it. A refactor's take-out is skipped, so odd does not show that the suite
exercises the changed code. The refactor sentence still meets the ambiguity stop (section 4b): "Refactor X." is
refused, "Every existing test of X still passes after the split." is not. Only the unittest suite command is
exercised by the tests; the others are not run. Whether the templates lower turns or failed `done` attempts is not
measured.

### 4d. Failure feedback: the `next:` block

Needs a tool newer than 0.4.0. When `odd done` fails (exit 1), and when `odd race` or `odd cascade` ends with no
verified attempt, the output ends with a block an agent can act on without reading the prose above it:

```
next:
  proof: AssertionError: 0 != 5
  survived: calc.py:6 - -> +: return a - b
  not run: calc.py:6
  refused: tests/test_keep.py
  rerun: odd done add --base main
```

One line per item that is present, and nothing else: `proof:` the proof's failing line (the last output line that
names a reason, as in the "without them the proof said" summary; else its last line), when the proof fails or fails
on the third run; `survived:` each small break the proof did not notice and `not run:` each changed line the proof
never executed, when `"strength": "enforce"` turns them into a fail (under `"report"` done passes and prints no
block); `refused:` each existing test file edited without a `test-change:` reason (R2). `rerun:` is always last: the
command as given (`--base` and the other options kept). A failed `done` with no such item (the proof passes with the
change taken out, nothing changed inside `in:`, an empty proof, a skip on a bug outcome) prints no block: rerunning
the same command would fail the same way, and the remedy (for example `--base <revision>`) is in the message above. Race
and cascade prefix each item with its attempt (`attempt 1.2 proof: ...`) and rerun the race or cascade command.

The items travel on the exception (`Fail.items`), so there is one formatter (`next_block()`) for all three: `odd done`
appends it, `_judge()` keeps each attempt's items, the cascade prompt gives every refused attempt its finding then
its block (rerun `odd done <slug>` in the attempt's worktree), and the final race/cascade failure lists them. The MCP
server returns the same text in `output` and the lines after the last `next:` line as `structuredContent.next`
(absent when there is none). odd flushes standard output before it prints the failure, so with both streams on one
pipe the block is the last thing printed. Following the research note in `docs/evidence/14-research.md` (detailed
rejection feedback raised evasion of an LLM review panel), the block states facts only and says nothing about how to
satisfy a check. Exit 2 (could not run) gets no block. Limits: not measured whether the block lowers the turns
between the first failed `done` and the first passing one (BACKLOG item 8's measure); a third proof run that fails
after a pass is not covered by a test.

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
as it was; the block is held under 2,600 characters and 32 lines by a test (2,595 and 32 today, measured on the
block `init` writes with the default settings: no room is left, so a later addition must shorten something).

Step 4 of the method stops the work when it is proven (backlog item 14, a tool newer than 0.4.0, no setting): once
`odd done` passes with full proof strength and `odd gate` passes, the agent is told to stop and report, and not to
plan, review or refactor further in this outcome. `odd done`'s success output then ends with the line
`next: report the outcome as done (odd gate passed)` (the constant `DONE_NEXT`) when the gate it runs passes; when that
gate fails, the output ends with the gate's `FAIL` and its problems, and the line is not printed. The MCP `done` tool
returns odd's output, so it carries the line too. Limits: the line follows the gate only, so under the default
`"strength": "report"` it is printed even when the proof strength is below full (the strength is on the line above it;
the method's wording, not the tool, asks for full strength); and whether it cuts cost or seconds per task (the item's
measure) is not measured. To make room, step 2 no longer says that a reseal shows in review (DESIGN section 4 and the
FAQ still do).

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
recorded escaped defects by kind of proof (section 9), and the spend per proven outcome from agent attempts (section
3h). It is self-reported and is never published as a result.

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
- The regression guard (section 5b) runs an earlier proof only when the change touches a file inside its `in:`; a
  break through any other file is not seen. Deleting or parking a merged outcome reports its proof and never fails
  the gate (the auto lane goes to review).
- `odd chain` (section 3e) knows a proven outcome by its checkpoint commit's subject only; a SIGKILL between applying
  a winner and committing it leaves the winner's files uncommitted (the next run refuses and names them).
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
