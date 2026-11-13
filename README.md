# Outcome-Driven Development (ODD)

**An outcome counts as delivered only when its proof fails without the change.**

> **The rule:** nothing counts as done until a check that runs says so: a check that fails without the change, run
> by someone other than the one claiming it. **No proof, no done.** Why it holds, what it does not promise, and how to
> follow it with or without odd: [THE-RULE.md](THE-RULE.md).

Work is done when a proof says so, not when the agent says so. (Not to be confused with the product-management use of
"outcome-driven", aligning work with business goals, or with observability-driven development, also abbreviated ODD.
Here an outcome is something a command can check.)

`odd` is one small command-line tool and a half-page method for building software with a coding agent. It works with
Claude Code, Cursor, Copilot, Codex or anything else that can run a shell command, because it needs only a shell and
git.


**A reasoner for the hard parts** (a tool newer than 0.4.0; [DESIGN.md](DESIGN.md) section 3j). Set one agent
command for judgement, `"reasoner": "<your agent command, any model>"`: it plans a ticket
into checkable outcomes and their build order (`odd plan <ticket>`), writes proofs (`odd spec`) and challenges them
(`odd challenge`), while cheap agents write the code. Nothing it writes is trusted: a plan must cover every
requirement with observable outcomes, and a proof must fail before the code.

**The proof, in one page:** [docs/PROOF.md](docs/PROOF.md) lists every claim odd makes with the tests that show it
(all of them, run on Linux and macOS on every push), grouped by what they prove, and what the measurements show and do not show. It is generated from the test suite,
and CI fails when it is out of date.

## The problem

Coding agents report "done" for work that is not done. The tests pass, but they test nothing the change does; the bug
is still there; the summary says fixed. Writing more rules for the agent does not fix this, because a rule is
something the model may or may not follow. In the project this method came from, 1,856 instructions were given to
agents over three months, and the two most expensive mistakes were the process's own rules.

ODD keeps the one part that does not depend on the model agreeing: "done" is decided by a command, on the code.

## Who it is for

| you are | the problem it solves | how you use it |
|---|---|---|
| a developer working with an AI agent | the agent says done; the tests pass but test nothing | `odd init` once; the agent follows `AGENTS.md` and runs `odd done` before it reports done |
| a team letting agents open pull requests | reviewers cannot tell whether an agent's PR really works | one CI step, made a required check: a PR whose changed files are not covered by a proof that fails without them cannot merge |
| anyone running agents unattended | nobody is watching the "done" claims | the gate is the referee, and `odd park` gives the agent an honest "blocked" instead of a fake done |
| a user of Spec Kit, BMAD or Superpowers | specs and plans, but nothing proves the code meets them | ODD sits underneath as the last check; it replaces none of them |

It is not a planning framework, a prompt library or an agent orchestrator. It is the one check the others leave to
the model. Questions and objections: [FAQ](FAQ.md).

> **Status: early (0.4.0).** The tool passes its own tests (132), including the ways an agent could fake "done". It
> has been through a design review (23 changes, all applied) and a red team (48 confirmed defects, each now a test).
>
> **Does it work better? Measured, and mostly no difference.** In a same-task comparison (16 tasks with hidden
> acceptance tests, five ways of working, three runs each, two models, 480 runs) every arm, plain Claude Code included, got every doable task right on both Sonnet and Haiku (42 of 42 runs; one Superpowers miss on Sonnet). ODD did not make the code more correct; nothing did. The arms separated only on the impossible tasks with Haiku: ODD and Superpowers claimed "done" falsely in 2 of 6 runs, plain, BMAD and Spec Kit in 3 of 6, and ODD never edited a visible test: a hint, not a finding. ODD cost about a quarter to a half more than plain; BMAD and Spec Kit two to five times as much. These runs used ODD from before the 0.4.0 features.
> Full results and both grades: [15](docs/evidence/15-comparison.md).

## The idea

1. **State the outcome before the code.** One sentence saying who observes what, a command that exits 0 only when
   that is true, and the files the change may touch.
2. **Make the change.**
3. **`odd done` decides.** It passes only when the proof passes on your code as it is, *fails on the same code with
   your change taken out*, and passes again once the change is put back. A proof that would pass anyway (`true`, a
   test that asserts nothing) is rejected.
4. **`odd gate` checks the whole change.** Every changed product file must be inside the boundary of one verified
   outcome. In CI it recomputes everything from the repository and trusts nothing the agent recorded.

Small edits (25 changed lines by default) need no outcome. If the work cannot be done as specified, `odd park` says
so, and that is an acceptable result.

## Try it

Install it either way; both give the same single file.

```bash
pipx install odd-tool                # or: pip install odd-tool        (then the command is `odd`)
curl -fsSLO https://raw.githubusercontent.com/varunkan/ODD-Outcome-Driven-Development/main/odd.py   # or just the file
```

```bash
cd your-project                      # any git repository; needs a POSIX shell, git 2.23+ and Python 3.8+
odd init                             # (or: python3 ../odd.py init) writes .odd/, with its own copy of the tool, and the method into AGENTS.md

python3 .odd/odd.py new split-bill \
  "A cashier who splits a bill three ways sees three totals that add up to the bill." \
  --proof "pytest tests/test_split.py -q" --in "src/billing/**"

# write tests/test_split.py, then make the change in src/billing/

python3 .odd/odd.py done split-bill
#   proof passed in 0.4s; two more runs (without the change, then with it again), about 0.8s
# split-bill: verified. took out 2 file(s), 41 line(s); without them the proof said: 1 failed in 0.04s; 0.4+0.4+0.4 s

python3 .odd/odd.py gate             # exit 0 only when every changed file is inside a verified outcome
```

From here your coding agent follows the method in `AGENTS.md` by itself.

| command | what it does |
|---|---|
| `odd init [--claude-hooks] [--mcp]` | set up or repair a project; prints the step to add to CI and a proof suggestion |
| `odd new <slug> "<outcome>" --proof CMD --in "GLOB, GLOB"` | state an outcome (a three-line file in `.odd/outcomes/`); `--proof auto` picks a narrow command from your test runner and prints what it detected; `--covers R1,R3` names the ticket requirements it covers; `--kind bug` requires the proof to fail on the unfixed code; `--kind feature` and `--kind refactor` fill their defaults and hints; prints the files to read first (all a tool newer than 0.4.0) |
| `odd done <slug> [--base REF]` | verify it: passes, fails with the change taken out, passes again |
| `odd race <slug> [--n N] [--agent CMD]` | run N agent attempts in parallel, each in its own git worktree; the verified one with the strongest proof and fewest changed lines is applied to your tree (a tool newer than 0.4.0) |
| `odd cascade <slug> [--agents C1,C2] [--race N]` | try the agents in order, cheapest first, each attempt in its own worktree; stop at the first verified one and apply it, else escalate with the failure in the next prompt, and park after the last (a tool newer than 0.4.0) |
| `odd chain <ticket> [--race N] [--cascade]` | do a long task as the outcomes listed in `.odd/chains/<ticket>.md`, in order: each one not yet proven is raced (or cascaded), verified and committed as the checkpoint `odd: <slug> proven`; an unproven one stops the chain, is parked with its reasons, and a rerun continues from it (a tool newer than 0.4.0) |
| `odd spec <slug> --proof-by CMD [--tries N]` | another agent (in practice a stronger model) writes only the proof in its own worktree; it is brought back and sealed red before any code, retried up to 3 times, then parked (a tool newer than 0.4.0) |
| `odd challenge <slug> [--agent CMD]` | advisory: another agent tries to make the verified change wrong while the proof still passes; prints its claim and the variant, applies nothing (a tool newer than 0.4.0) |
| `odd gate [--recompute]` | is every changed file inside a verified outcome? (`--recompute` for CI) |
| `odd park <slug> "<reason>"` | the honest exit: blocked, or cannot be done as specified |
| `odd ask <slug> "<question>"` | the outcome cannot be made checkable from the ticket: record one precise question; the gate says "waiting for an answer" until the `asked:` line is deleted (a tool newer than 0.4.0) |
| `odd escaped <slug> "<what, where found>"` | a defect got past a verified outcome: record it on that outcome |
| `odd stats [--json]` | counts, self-reported, including escaped defects by kind of proof, the escape rate per outcome kind, seal, strength band and proof author, and dollars and seconds per proven outcome from race, cascade and chain attempts (the rate table, `--json` and the cost table need a tool newer than 0.4.0) |

**Racing agents.** With `"agents": ["<agent command>", ...]` in `.odd/config.json` (any CLI agent; `{prompt_file}`
in the command becomes the prompt's path, else the prompt goes to stdin), `odd race <slug>` starts one attempt per
command in its own working tree under `.git/` (a `git clone --shared`, so its git config, hooks and refs stay its
own), checks each one as `odd done` would, prints a table of attempts and
applies the winner: verified, then the most small breaks caught, then the fewest changed lines, then the earliest
finish. If your tree already has changes inside the boundary it writes the winner as a patch instead. On fake agents
(one correct, one with a weaker proof, one broken, one that edits the test) the correct one won 10 races of 10, and
setting up and removing an attempt's tree costs 0.06-0.08 s per attempt on a three-file repository. An attempt is
refused if it left a process running (found by its `ODD_ATTEMPT` mark on Linux, and killed), and ignored files it made
that your tree lacks are removed before the check, since the applied patch would not carry them. Not measured yet:
real agents, and whether a race of cheap models beats one strong one (BACKLOG item 1). Details: [DESIGN.md](DESIGN.md) section 3b.

**Cheapest agent first.** `odd cascade <slug>` reads the same `"agents"` list as levels, cheapest first (or
`--agents "C1,C2"`): the first agent attempts the outcome in a fresh worktree; if the attempt is verified it is applied
and nothing dearer runs; otherwise the next agent gets the precise failure (the proof's output, the surviving small
break and its line, the line the proof never ran) in its prompt. After the last level the outcome is parked with every
reason, and nothing unverified is applied. `--race N` runs N attempts per level. Each attempt's cost is shown when the
agent prints a final line `odd-cost: <usd>`, else "not reported". On fake agents: 0.65-0.71 s wall when level 1 is
verified, 0.74-0.87 s when it escalates to level 2, 0.42-0.49 s to park after two (5 runs each, three-file repository).
Every race, cascade or chain attempt also records its reported cost and its seconds locally, and `odd stats` prints
dollars and seconds per outcome and per proven outcome, failed attempts included, labelled self-reported (a floor
when some agents report no cost; seconds are summed per attempt, not wall clock).
Not measured: real agents and whether Haiku-then-Sonnet is cheaper than Sonnet alone (BACKLOG item 2). Details:
[DESIGN.md](DESIGN.md) section 3c.

**Long tasks as a chain.** Split a ticket into small outcomes (`odd new` each, proofs written), list their slugs in
order in `.odd/chains/<ticket>.md`, and run `odd chain <ticket>` (`--race N`, or `--cascade` to use the agents as
levels). Each outcome is attempted in worktrees as race or cascade would, verified again in your tree, and committed
as its own checkpoint `odd: <slug> proven`; the next one starts from that commit. When one cannot be proven the chain
stops, the tree is at the last checkpoint, the outcome is parked with the reasons, and the status lists every outcome
as proven, parked or not started. Run it again to continue. It refuses to start if your tree or index has changes outside the
chain's outcomes and their tests, and it only ever reverses the patch it applied itself (and unstages what it staged);
an uncommitted edit to a test the proof names goes into that outcome's checkpoint. On fake agents, three
outcomes took 3.9-4.2 s with three checkpoint commits; a chain stopping at the second took 1.7-1.9 s and its resume
2.8-3.1 s (5 runs each, a repository of six small files). Not measured: real agents, and how much longer an unattended task gets
with chains than without (BACKLOG item 10). Details: [DESIGN.md](DESIGN.md) section 3e.

**Every requirement covered.** Write the ticket's requirements once, one per line, in
`.odd/requirements/<ticket>.md` (`R1: ...`, `R2: ...`), and let each outcome name the ones it covers (`covers: R1, R3`,
or `odd new ... --covers R1,R3`). `odd gate` and the pull-request summary then print `requirements <ticket>: 1 of 2
covered; not covered: R2 (...)`, and a `covers:` id that is not in the file fails the gate. `"coverage": "enforce"` in
`.odd/config.json` makes an uncovered requirement a Fail too (`"report"` is the default, `"off"` turns it off; a tool
newer than 0.4.0). It catches "works, but not what was asked" only as far as the list is complete and each proof tests
what its outcome says; odd checks neither. Not measured: requirements missed with and without it (BACKLOG item 4).
Details: [DESIGN.md](DESIGN.md) section 5a.

**Earlier proven work stays proven.** A merged outcome keeps its file, so its proof stays in the repository. When a
later change touches a file inside an earlier outcome's `in:`, `odd gate` (local and `--recompute`) runs that proof
again (green only) and fails with `<slug> (proven in <commit>) now fails: <last line>` when it no longer passes; the
pull-request summary lists every guard run. Parked, asked and skipped outcomes are not guards. The cost is one proof
run per guard. `"guard": "report"` only prints, `"off"` turns it off (the default `"enforce"`; a tool newer than
0.4.0). Editing only an outcome's `escaped:` line keeps it a guard. Deleting or parking a merged outcome runs its
base proof as a reported guard that never fails the gate, prints `deleted <slug> (merged in <commit>)` for a deletion,
and sends the auto lane to review. Overlap is by path: a break through a file outside the earlier `in:` is not seen. Not measured: earlier
outcomes broken with and without it (BACKLOG item 9). Details: [DESIGN.md](DESIGN.md) section 5b.

**A verification is not repeated when nothing it reads changed.** `odd done`, `race`, `cascade`, `chain` and `gate
--recompute` key each verification on the tool, the settings, the base commit and every file that differs from it; a
match with an earlier pass prints `cached (verified at <time>)` and runs no proof, and a one-byte change in any of
them runs it in full (`--no-cache` always does). Locally the cache is under the git directory. In CI it is used only
with `"cache_file"` (a tool newer than 0.4.0) set on the target branch to a path outside the repository, holding
what an earlier `--recompute` wrote; restore it on pull requests and save it only from the target branch. The gate
also says how many earlier proofs the regression guard skipped as unaffected. Measured on the test fixture: a second
`done` 0.22 s against 0.91 s, a second `gate --recompute` 0.16 s against 0.73 s (5.66 s with a proof that sleeps 1 s).
Ignored files, installed packages and the environment are not in the key. Details: [DESIGN.md](DESIGN.md) section 5d.

**The agent starts from the boundary.** After `odd new` (and the MCP `new` tool) writes the outcome, it prints
`read these first`: the files inside `in:` that exist, at most ten, the largest change against the base first, then
the largest file, and the files the proof names. The race, cascade and chain prompt carries the same list (a tool
newer than 0.4.0, no setting). Whether it saves an agent turns or tokens is not measured yet. Details:
[DESIGN.md](DESIGN.md) section 3f.

**An auto-merge lane, off by default.** With `"auto_lane": true` (a tool newer than 0.4.0) the gate also says
`"lane": "auto"` or `"lane": "review"` with its reasons: auto only when the gate passed, every outcome in the change
is verified with every small break caught (`"auto_min_strength"`, default 1.0) and no changed line its proof never
runs, the change is at most `"auto_max_lines"` product lines (default 120) all inside outcomes, and there is no
control file, no `test-change:`, no skipped take-out check, no parked or asked outcome, no deleted merged outcome file, and every
regression guard passed. It shows in `--json`, in the pull-request summary (`Auto-merge lane: yes` or `no, because ...`) and as the
Action output `odd_lane`. odd never merges: a repository wires its own auto-merge job on `odd_lane == 'auto'`, and a
change that takes it merges with nobody reading its code, so the outcome sentence and the proof are all that is
checked. Not measured: review minutes saved or defects escaping through it (BACKLOG item 11). Details:
[DESIGN.md](DESIGN.md) section 5c.

**Bugs are reproduced first.** `odd new <slug> ... --kind bug` marks a bug fix. Then `odd seal` and `odd done` require
the proof to fail on the unfixed code (the outcome's changed files put back to the base) and print
`reproduced: <last line of the failure>`; a proof that passes there is refused ("the proof does not reproduce the
bug"). A tool newer than 0.4.0. odd shows the failure line; whether it is the reported symptom is for the reviewer
(a missing new file also fails). Details: [DESIGN.md](DESIGN.md) section 4a.

**Each kind of change starts from its proof shape.** `odd new ... --kind bug|feature|refactor` (a tool newer than
0.4.0) writes `kind:` and prints a one-line hint: bug, reproduce first; feature, the proof covers the new behaviour
and the existing suite stays green; refactor, the existing suite is the proof. `--kind refactor` may leave out
`--proof` (it becomes the detected runner's whole suite) and writes `counterfactual: skip - behaviour-preserving
refactor`, so `done` checks only that the suite passes and no test changed unexplained. odd does not run the suite for
a feature, and does not show that the suite exercises a refactored line. Details: [DESIGN.md](DESIGN.md) section 4c.

**A vague outcome is stopped, and a question is a valid answer.** `odd new` refuses a sentence with nothing anyone
would see, get or measure ("Refactor the billing module.") and suggests "<who> <observes> <what>, measurably". It is a
small English word list, not a model: wide on purpose (state words such as "is disabled", "keeps", "can export"
count), so it misses vague sentences that contain a listed word and still refuses ordinary sentences built only from
unlisted words; "so the tests pass" does not count as an observable. `"ambiguity_stop": false` turns it off. When the ticket does not say what should be observable, `odd ask <slug>
"<question>"` records the question; the gate reports that outcome as waiting for an answer, not failed, until the
`asked:` line is deleted; until then it covers no files and no requirement. A tool newer than 0.4.0. Details: [DESIGN.md](DESIGN.md) section 4b.

**A stronger model writes the proof, a cheaper one the code.** `odd spec <slug> --proof-by "<command>"` gives the
outcome to one agent command to write only the proof, in its own worktree. odd accepts it only if it changes test
files alone and the proof fails before the code; it brings the tests back, seals them (`odd seal`) and writes
`proof-by: <name>` in the outcome file (credentials on the command line are left out). A proof that passes before the
code is refused and the reason goes to the next try; after 3 tries (`"proof_tries"`) the outcome is parked. Then
`odd race` or `odd cascade` with cheaper agents works against that sealed proof, and an attempt that edits it is
refused. Why: in one study, tests from a stronger model raised a fixed repair agent's resolution from 61.2% to 65.3%,
while tests from the weak model itself lowered it to 57.3% (arXiv 2609.09133, see
[docs/evidence/14-research.md](docs/evidence/14-research.md)). On odd's harness ([16](docs/evidence/16-new-arms.md#after-the-fixes)) it
did not: with Sonnet's proofs, Haiku delivered 30 of 42 doable tasks and 4 of Sonnet's proofs passed work the hidden
tests reject; cascade (39 of 42 at a third of plain Sonnet's cost) and race (no false DONE) did better. Details: [DESIGN.md](DESIGN.md) section 3d.

**An attempt budget per outcome.** `"max_attempts": N` (default 0, off; a tool newer than 0.4.0) parks an outcome
after N failed attempts at it, counted on this machine from odd's local evidence: failed `odd done` runs and refused
`race`, `cascade` or `chain` attempts, since the outcome was last verified. The `parked:` line lists each reason; a
cascade runs no further level once the budget is reached. While parked for its budget, `done`, `race`, `cascade`
and `chain` refuse the outcome (exit 1) and run no proof and no agent, until a person deletes the `parked:` line. The
number is never written into `AGENTS.md` or an agent's prompt (in our pilot a visible budget made an agent skip work),
but it is in `.odd/config.json`, which an agent can read in its copy of the repository. Whether it
saves money on tasks that end unsolved is not measured. Details: [DESIGN.md](DESIGN.md) section 3g.

**A proof the agent never sees.** `"held_out": [{"name", "proof", "in"}]` (a tool newer than 0.4.0) lists proofs
kept outside the repository, for example in a private checkout a CI step provides. Only `odd gate --recompute` runs
them, with the list read from the target branch, and their output is never shown: a change fitted to its visible
proof (a lookup table for the cases it checks) fails there without learning why. Why: visible-only checks scored 97%
against 0% held out on such a solution (arXiv 2605.21384). Details: [DESIGN.md](DESIGN.md) section 5e.

**Files the proof does not need.** `"inert": "report"` or `"enforce"` (default off; a tool newer than 0.4.0) takes
each changed file out on its own after the main check; a file whose removal leaves the proof passing is named, or
fails the check under `"enforce"`. Smaller changes, nothing riding along unproven. Details: [DESIGN.md](DESIGN.md)
section 4f.

**Checks earned from real projects** (a tool newer than 0.4.0; [DESIGN.md](DESIGN.md) section 5f): standing
project rules as commands every gate runs (`"checks"`, a secrets scan for example); `"repeat"` so a flaky proof
cannot fake the take-out check; `target:` so a proof must show it ran against this commit's deploy or build;
`owed:` and `odd owed` for steps still owed on the real system, closed only with evidence; `"max_cost"`, a budget in
dollars; and proofs piped into `tail` or `grep -q .` refused, since the pipe hides their exit code.

**Refactors checked by comparison, not skipped.** `same: <command>` in an outcome (a tool newer than 0.4.0) runs the
command with the change and with it taken out; its exit code and whole output must be identical, or `done` names the
first differing line. Details: [DESIGN.md](DESIGN.md) section 4e.

## What it checks, and what it does not

It checks that the proof **depends on the change**: with the change removed, the proof fails. It checks that nothing
was changed outside the stated boundary, including files written from a shell.

It then makes up to eight small breaks in the changed lines (a `<` for a `<=`, `and` for `or`, a number plus one),
one per changed line first and spread across files, one at a time, and names each one the proof does not notice: a
changed line the proof does not depend on. The score reads "proof strength k of n" (k breaks caught of n), never
"verified". For a Python proof (`python -m unittest`, `pytest`, a `.py` file) it also runs the proof once under a
stdlib trace hook and names each changed line the proof never executed ("not run by the proof: calc.py:6"); for other
languages it says "not measured". A proof that only prints (`echo`, or a Python script of imports, `print(...)`
and plain assignments, with no assert, raise, exit, subscript or division) is refused. All of this is reported by default and can fail the gate (`"strength":
"enforce"` in `.odd/config.json`, or `"off"`); no new setting or field, so the v0.4.0 Action reads the same files and
measures the 0.4.0 way.

It does not check that the outcome is worth having, or that the proof is thorough. For new code, a proof that only
imports the new function already fails without it; the small breaks catch some of that, not all. The outcome sentence and the proof command are a few lines, and
the gate prints what the proof said when it failed; a person should read both.

**Where the enforcement is real.** On a developer's machine, an agent with shell access can bypass any local check.
The gate is the authority only in CI, and only when (1) it is a required check, (2) the tool, its settings and the CI
configuration need a person's review to change, and (3) the agent cannot merge or push to the target branch. The CI
step takes the tool and its settings from the base branch, so a pull request cannot loosen its own gate. `odd init`
prints that step.

**Sealed proofs (optional).** Write the test, run `odd seal <slug>`, then write the code. `seal` refuses a proof that
already passes, and writes `sealed: proof@<hash>, tests/test_x.py@<hash>` into the outcome file. If the proof command
or a sealed test file changes afterwards, `odd done` and the gate fail until it is resealed, and a reseal changes the
outcome file, so it shows in the diff. It makes fitting the test to the code visible; it does not stop it. A reseal
needs the proof red again, so take the product change out first. Unsealed outcomes work as before.

**Changed tests and empty proofs fail closed.** A change that edits or deletes a test file that existed at the base
fails `odd done` and the gate unless an outcome in the change says why with `test-change: <reason>`; the gate and the
review comment print the reason; a reason that names test files (`test-change: tests/test_keep.py - ...`) covers
only those, and the gate shows which reason covers which file. A new or changed `conftest.py` or `pytest.ini`, a
changed pytest section in `pyproject.toml`/`setup.cfg`/`tox.ini` or a changed `load_tests` needs a reason too:
turning a test off is editing it. Other new test files need none. A proof that exits 0 but ran no test, skipped every test
it ran (or only had expected failures: xfail, `expectedFailure`), or stopped before its runner printed its summary (`sys.exit(0)` at import, an empty suite, `go test` with no
test files) is refused, for unittest, pytest, jest and go test, read from the proof's own output and deliberately
conservative ([DESIGN](DESIGN.md) section 4 lists what is not detected). On seeded fixtures of the systemic hacks,
0.4.0 accepted 6 of 8 and this version refuses all 8; three honest fixes still pass.

**Escaped defects.** When a defect gets past a verified outcome, run `odd escaped <slug> "<what went wrong, where it
was found>"`. It appends a dated entry to that outcome's `escaped:` line and tells you the next step: a new outcome
whose proof fails on the escaped behaviour. `odd stats` then counts escapes against outcomes that were sealed or not,
that skipped the take-out check or not, and whose proof caught every small break or not (when that was measured on
this machine). Over time that shows which kinds of proof let defects through. It counts only what people record, so
it is self-reported, not a measurement. With a tool newer than 0.4.0 it also prints a table of escape rates (escaped
defects per outcome) grouped by outcome kind (bug, feature, refactor, none), sealed or not, proof strength band (full,
partial, not measured) and whether another agent wrote the proof (`odd spec --proof-by`), and says under each group of
fewer than 10 outcomes that its counts are small; `odd stats --json` gives the same as JSON.

## In CI

On GitHub Actions the gate is one step at the end of your test job:

```yaml
- uses: actions/checkout@v4
- uses: varunkan/ODD-Outcome-Driven-Development@v0.4.0
```

It fetches the history it needs, judges the change with the action's own pinned copy of the tool (never the copy the
pull request carries) and reads the settings at the tip of the target branch. Pin a tag or a commit, and make the step
a required check. Other CI systems use the two lines `odd init` prints; they do the same. The `strength` and
`mutants` settings and the `sealed:` field need the Action at 0.4.0 or later: an older pinned Action refuses them.
The `test-change:` field needs a tool newer than 0.4.0 (the next release): the Action at v0.4.0 refuses it as an
unknown field, and does not enforce the changed-test and empty-proof rules.

The result is written for the reviewer: per outcome its sentence, its proof, what the proof said with the change
taken out and its strength score, then the exemptions and any control files changed. It goes to the job's step
summary always, and on a pull request into one comment that each run updates. To allow the comment, give the job:

```yaml
permissions:
  contents: read
  pull-requests: write
```

Without it (or on a pull request from a fork, whose token is read-only) the log says the comment could not be posted
and the check's result is unchanged. `with: comment: false` turns the comment off. The step that runs the proofs
is never given the token, only the comment step after it; only odd's own comment (by `github-actions[bot]`, or
`with: author:` for a personal token) is updated, and text from the change is rendered inert. Elsewhere, `odd gate --summary
FILE` writes the same Markdown and `--json FILE` the same result as data. Whether it saves review time is not yet
measured ([protocol](docs/review-time.md)).

## Works with

`odd init` writes the method (about thirty lines) into the root `AGENTS.md`; running it again replaces that block in
place. Its last step tells the agent that when the task cannot be done as asked or the proof cannot honestly pass, it
should STOP and explain with `odd park`, and that this is the expected answer, not a failure (wording from
ImpossibleBench's abort option; its effect here is not measured). Step 4 tells it to stop once `odd done` passes
with full proof strength and `odd gate` passes: report, and do not plan, review or refactor further in this outcome.
`odd done` then ends with `next: report the outcome as done (odd gate passed)`, or with the gate's problems when the
gate fails (a tool newer than 0.4.0; whether this saves cost or time is not measured).

| reads `AGENTS.md` without configuration | needs one line |
|---|---|
| Codex, Cursor, GitHub Copilot in VS Code (and its cloud agent and CLI), Claude Code, Junie, Windsurf/Devin | Gemini CLI: set `context.fileName` to `AGENTS.md`. Aider: `read: AGENTS.md` in `.aider.conf.yml`. Copilot Chat outside VS Code: point `.github/copilot-instructions.md` at `AGENTS.md`. |

The table rests on each tool's documentation ([sources](docs/evidence/10-design-review.md)). Only Claude Code has
been run with it so far. The command and the gate are the same for every tool and for a person.

Optional, for Claude Code only: `odd init --claude-hooks` adds two hooks for your machine (never committed) that give
one line of status at session start and stop a turn from ending on unproven work.

Optional, for any MCP client: `odd init --mcp` adds odd's MCP server to the project's `.mcp.json` (other servers are
kept), so an agent calls `new`, `seal`, `done`, `gate`, `park` and `escaped` as tools and gets odd's exit code and
output back; a failed `done` ends with a `next:` block (the proof's failing line, each surviving break, each
unrun changed line, each refused test edit, the command to rerun; a failure with none of these items has no block,
since the remedy is in the message; DESIGN.md section 4d, a tool newer than 0.4.0),
also returned as `structuredContent.next`. It is a thin wrapper that runs `.odd/odd.py`; so far it has been driven only by the test suite, not by
a real client ([details and limits](DESIGN.md#7-how-it-reaches-each-tool)).

## Why, and the evidence

The method was distilled from building a production point-of-sale system with coding agents: 1,856 instructions
given over three months, each measured and ruled on. Most were dropped.

- [FAQ.md](FAQ.md): short answers, the differentiator, objections, how to adopt it, and a script for explaining it
  in a session.
- [WHY.md](WHY.md): what the evidence supports, what it counts against, and what is not claimed.
- [What went wrong](docs/evidence/02-pos-evidence-ledger.md): the waste record of the source project. The two most
  expensive mistakes were its own rules.
- [The comparison with Spec Kit, BMAD and Superpowers](docs/evidence/07-validation-and-verdict.md), and
  [the research behind it](docs/evidence/04-spec-kit-bmad-superpowers.md).
- [All of it](docs/evidence/README.md), including every ruling and the data.
- [DESIGN.md](DESIGN.md): how the tool works and its known limits, and
  [the review that shaped it](docs/evidence/10-design-review.md).

## Limits

- Evidence so far is one project, measured by itself. The comparison harness is in [`bench/`](bench/SPEC.md); its
  results will be published with their spread, whatever they show. Its report states trust as numbers per arm: claim
  precision, silent failures, the cheat and park rates on impossible tasks, and the own check against the hidden tests
  by change size. A cheat is counted only by the routes a script can see (a DONE claim, an edited visible test, a test
  input quoted into the code).
- The check costs three runs of the proof, plus one per small break (at most eight by default; under `report` it
  stops once the breaks took about as long as the core runs), so the proof should be the narrowest command that
  shows the outcome. With a 0.8 s jest proof that is about 2.4 s for the core and about as much again for strength.
  A Python proof adds one traced run: on the demo 0.1 s (core runs 0.1 s each), on a pytest fixture 0.4 s (core
  runs 0.4 s each), measured on one machine with Python 3.13; tracing a long suite slows it more.
- While the change is taken out, files are rewritten in place. They are put back on interruption and an edit made
  meanwhile is never overwritten, but a dev server or file watcher will see the revert.
- State outside tracked files (installed dependencies, caches) is not reverted; a dependency bump or a pure refactor
  uses `counterfactual: skip - <reason>`, which the gate names in its result.
- A proof that needs a real device, account or secret cannot be recomputed in CI.
- The verification cache does not see ignored files, installed packages, the environment or the clock; use
  `--no-cache` when the result depends on them. Locally, anything that can write the git directory can plant a
  cached pass for `odd done`; only `gate --recompute`, which ignores the local cache, decides.
- Windows is untested.

The full list is in [DESIGN.md](DESIGN.md#10-limits).

## Develop

```bash
python3 -m unittest discover -s tests
```

MIT licence. See [LICENSE](LICENSE).
