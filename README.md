# Outcome-Driven Development (ODD)

**An outcome counts as delivered only when its proof fails without the change.**

Work is done when a proof says so, not when the agent says so. (Not to be confused with the product-management use of
"outcome-driven", aligning work with business goals, or with observability-driven development, also abbreviated ODD.
Here an outcome is something a command can check.)

`odd` is one small command-line tool and a half-page method for building software with a coding agent. It works with
Claude Code, Cursor, Copilot, Codex or anything else that can run a shell command, because it needs only a shell and
git.

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

> **Status: early (0.3.0).** The tool passes its own tests (82), including the ways an agent could fake "done". It
> has been through a design review (23 changes, all applied) and a red team (48 confirmed defects, each now a test).
>
> **Does it work better? Not claimed yet.** A same-task comparison is running: 16 tasks with hidden acceptance tests,
> each done by plain Claude Code, ODD, Spec Kit, BMAD and Superpowers, three times each, on Sonnet and on Haiku. It
> measures whether the work is really right, whether the agent claims "done" falsely, and the cost and time. The
> results will be published here with their spread, whatever they show. Early signs from the
> [pilot](docs/evidence/12-pilot.md), too small to be results: on Sonnet, plain Claude Code got the work right on
> every task tried, so correctness may not separate the five; on an impossible task, one framework claimed "done".

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
| `odd init [--claude-hooks]` | set up or repair a project; prints the step to add to CI |
| `odd new <slug> "<outcome>" --proof CMD --in "GLOB, GLOB"` | state an outcome (a three-line file in `.odd/outcomes/`) |
| `odd done <slug> [--base REF]` | verify it: passes, fails with the change taken out, passes again |
| `odd gate [--recompute]` | is every changed file inside a verified outcome? (`--recompute` for CI) |
| `odd park <slug> "<reason>"` | the honest exit: blocked, or cannot be done as specified |
| `odd stats` | counts, self-reported |

## What it checks, and what it does not

It checks that the proof **depends on the change**: with the change removed, the proof fails. It checks that nothing
was changed outside the stated boundary, including files written from a shell.

It then makes up to eight small breaks in the changed lines (a `<` for a `<=`, `and` for `or`, a number plus one),
one at a time, and names each one the proof does not notice: a changed line the proof does not depend on. That is
reported by default and can fail the gate (`"strength": "enforce"` in `.odd/config.json`, or `"off"`).

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

## In CI

On GitHub Actions the gate is one step at the end of your test job:

```yaml
- uses: actions/checkout@v4
- uses: varunkan/ODD-Outcome-Driven-Development@v0.3.0
```

It fetches the history it needs, judges the change with the action's own pinned copy of the tool (never the copy the
pull request carries) and reads the settings at the tip of the target branch. Pin a tag or a commit, and make the step
a required check. Other CI systems use the two lines `odd init` prints; they do the same.

The result is written for the reviewer: per outcome its sentence, its proof, what the proof said with the change
taken out and its strength score, then the exemptions and any control files changed. It goes to the job's step
summary always, and on a pull request into one comment that each run updates. To allow the comment, give the job:

```yaml
permissions:
  contents: read
  pull-requests: write
```

Without it (or on a pull request from a fork, whose token is read-only) the log says the comment could not be posted
and the check's result is unchanged. `with: comment: false` turns the comment off. Elsewhere, `odd gate --summary
FILE` writes the same Markdown and `--json FILE` the same result as data. Whether it saves review time is not yet
measured ([protocol](docs/review-time.md)).

## Works with

`odd init` writes the method (about twenty lines) into the root `AGENTS.md`.

| reads `AGENTS.md` without configuration | needs one line |
|---|---|
| Codex, Cursor, GitHub Copilot in VS Code (and its cloud agent and CLI), Claude Code, Junie, Windsurf/Devin | Gemini CLI: set `context.fileName` to `AGENTS.md`. Aider: `read: AGENTS.md` in `.aider.conf.yml`. Copilot Chat outside VS Code: point `.github/copilot-instructions.md` at `AGENTS.md`. |

The table rests on each tool's documentation ([sources](docs/evidence/10-design-review.md)). Only Claude Code has
been run with it so far. The command and the gate are the same for every tool and for a person.

Optional, for Claude Code only: `odd init --claude-hooks` adds two hooks for your machine (never committed) that give
one line of status at session start and stop a turn from ending on unproven work.

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
  results will be published with their spread, whatever they show.
- The check costs three runs of the proof, plus one per small break (at most eight by default), so the proof
  should be the narrowest command that shows the outcome.
- While the change is taken out, files are rewritten in place. They are put back on interruption and an edit made
  meanwhile is never overwritten, but a dev server or file watcher will see the revert.
- State outside tracked files (installed dependencies, caches) is not reverted; a dependency bump or a pure refactor
  uses `counterfactual: skip - <reason>`, which the gate names in its result.
- A proof that needs a real device, account or secret cannot be recomputed in CI.
- Windows is untested.

The full list is in [DESIGN.md](DESIGN.md#10-limits).

## Develop

```bash
python3 -m unittest discover -s tests
```

MIT licence. See [LICENSE](LICENSE).
