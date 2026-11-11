# ODD: outcome-driven development

**Work is done when a proof says so, not when the agent says so.**

`odd` is one small command-line tool and a half-page method for building software with a coding agent. It works with
Claude Code, Cursor, Copilot, or anything else that can run a shell command, because it needs only a shell and git.

> **Status: early (0.3.0).** The tool passes its own tests, including the ways an agent could fake "done", and a red team of 0.2.0 (48 confirmed defects, each now a test), and
> has been through one design review (23 changes, all applied). A same-task comparison against plain Claude Code,
> Spec Kit, BMAD and Superpowers is being built. No claim about speed, cost or quality is made here until those
> numbers exist.

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

```bash
curl -fsSLO https://raw.githubusercontent.com/varunkan/ODD-Outcome-Driven-Development/main/odd.py
cd your-project                      # any git repository; needs a POSIX shell, git 2.23+ and Python 3.8+
python3 ../odd.py init               # writes .odd/ (with its own copy of the tool) and the method into AGENTS.md

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

It does not check that the outcome is worth having, or that the proof is thorough. For new code, a proof that only
imports the new function already fails without it. The outcome sentence and the proof command are a few lines, and
the gate prints what the proof said when it failed; a person should read both.

**Where the enforcement is real.** On a developer's machine, an agent with shell access can bypass any local check.
The gate is the authority only in CI, and only when (1) it is a required check, (2) the tool, its settings and the CI
configuration need a person's review to change, and (3) the agent cannot merge or push to the target branch. The CI
step takes the tool and its settings from the base branch, so a pull request cannot loosen its own gate. `odd init`
prints that step.

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
- The check costs three runs of the proof, so the proof should be the narrowest command that shows the outcome.
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
