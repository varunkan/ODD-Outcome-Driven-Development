# ODD: outcome-driven development

**Work is done when a proof says so, not when the agent says so.**

`odd` is one small command-line tool and a half-page method for building software with a coding agent. It works with
Claude Code, Cursor, Copilot, or anything else that can run a shell command, because it needs only a shell and git.

> **Status: early (0.1.0).** The tool passes its own tests, including the ways an agent could fake "done". A design
> review and a same-task comparison against plain Claude Code, Spec Kit, BMAD and Superpowers are in progress. No
> claim about speed, cost or quality is made here until those numbers exist.

## The idea

1. **State the outcome before the code.** One sentence saying who observes what, a command that exits 0 only when
   that is true, and the files the change may touch.
2. **Make the change.**
3. **`odd done` decides.** It passes only when the proof passes on your code as it is *and fails on the same code
   with your change taken out*. A proof that would pass anyway (`true`, a test that asserts nothing) is rejected.
4. **`odd gate` checks the whole change.** Every changed file must be inside the boundary of a verified outcome. In
   CI it recomputes everything from the repository and trusts nothing the agent recorded.

Small edits (25 changed lines by default) need no outcome. If the work cannot be done as specified, `odd abort` says
so, and that is an acceptable result.

## Try it

```bash
git clone https://github.com/varunkan/ODD-Outcome-Driven-Development odd
cd your-project                      # any git repository
python3 ../odd/odd.py init           # writes .odd/ (with its own copy of the tool) and the method into AGENTS.md

python3 .odd/odd.py new split-bill \
  "A cashier who splits a bill three ways sees three totals that add up to the bill." \
  --proof "pytest tests/test_split.py -q" --in "src/billing/**"

# write tests/test_split.py, then make the change in src/billing/

python3 .odd/odd.py done split-bill
# split-bill: DONE (the proof is a simulation; not yet proven on the real system)
#   proof passes; fails with the change taken out (2 file(s)); there it said: 1 failed in 0.04s

python3 .odd/odd.py gate             # exit 0 only when every change is covered by a verified outcome
```

From here your coding agent follows the method in `AGENTS.md` by itself. Requirements: Python 3.8+ and git 2.23+.

| command | what it does |
|---|---|
| `odd init [--claude] [--cursor] [--copilot] [--ci] [--hook pre-push]` | set up a project; adds the files each tool reads |
| `odd new <slug> "<outcome>" --proof CMD --in GLOBS` | state an outcome |
| `odd done <slug>` | verify it: passes now, fails with the change taken out |
| `odd gate [--recompute]` | is every change covered by a verified outcome? (`--recompute` for CI) |
| `odd park` / `odd abort <slug> "<reason>"` | honest exits: blocked, or cannot be done as specified |
| `odd widen <slug> <glob> "<reason>"` | let an outcome touch more files, on the record |
| `odd status`, `odd stats`, `odd doctor` | where things stand; self-reported measurements; is enforcement live |

## What it checks, and what it does not

It checks that the proof **depends on the change**: with the change removed, the proof fails. It checks that
nothing was changed outside the stated boundary, including files written from a shell.

It does not check that the outcome is worth having, or that the proof is thorough. `test -f x` is a true and useless
proof. The outcome sentence and the proof command are a few lines; a person should read them.

**Where the enforcement is real.** On a developer's machine, an agent with shell access can bypass any local check.
The gate is authoritative only when it runs in CI that the agent cannot edit: the gate job is a required check, and
the workflow file, `.odd/odd.py` and `.odd/config.json` need a person's review to change. `odd init --ci` writes a
workflow that takes the tool and its settings from the base branch, so a pull request cannot loosen its own gate.

## Works with

| | how the method arrives | in-editor feedback |
|---|---|---|
| Claude Code | `AGENTS.md`, imported by `CLAUDE.md` | yes: a write outside the open outcome's boundary is refused; a turn that changed files cannot end unproven |
| Cursor | `AGENTS.md` and `.cursor/rules/odd.mdc` | not in this version |
| GitHub Copilot | `AGENTS.md` and `.github/copilot-instructions.md` | not in this version |
| anything else, or a person | `AGENTS.md` | none |

Every tool gets the same command and the same gate.

## Why, and the evidence

The method was distilled from building a production point-of-sale system with coding agents: 1,856 instructions
given over three months, each measured and ruled on. Most were dropped.

- [WHY.md](WHY.md): what the evidence supports, what it counts against, and what is not claimed.
- [What went wrong](docs/evidence/02-pos-evidence-ledger.md): the waste record of the source project. The two most
  expensive mistakes were its own rules.
- [The comparison with Spec Kit, BMAD and Superpowers](docs/evidence/07-validation-and-verdict.md), and
  [the research behind it](docs/evidence/04-spec-kit-bmad-superpowers.md).
- [All of it](docs/evidence/README.md), including every ruling and the data.
- [DESIGN.md](DESIGN.md): how the tool works and its known limits.

## Limits

- Evidence so far is one project, measured by itself. The comparison harness is in [`bench/`](bench/SPEC.md); its
  results will be published with their spread, whatever they show.
- The check that takes the change out rewrites files in place for the length of one proof run. It restores them on
  interruption and never overwrites an edit made meanwhile, but a dev server or file watcher will see the revert.
- A proof that fails without the change for an unrelated reason (a flaky test) still counts as failing.
- Windows is untested.

## Develop

```bash
python3 -m unittest discover -s tests
```

MIT licence. See [LICENSE](LICENSE).
