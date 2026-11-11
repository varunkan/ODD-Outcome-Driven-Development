# ODD design: the lean, portable kernel

Status: design for review, 2026-11-11. Supersedes the first draft (audited in `docs/evidence/06`). Decisions it rests
on: `docs/evidence/07` (build lean) and the owner's answers of 2026-11-11: do what works best and is more efficient
than Spec Kit, BMAD and Superpowers; a lean core that is a real differentiator; a generic tool that sits on top of
Claude, Copilot, Cursor or any other coding agent; publish the waste record; run a same-task comparison as proof.

## 1. What it is

One small command-line tool, `odd`, plus a half-page method that any coding agent can follow.

The differentiator: **"done" is recomputed from the code, not claimed by the agent.** An outcome is done only when
its proof passes on the tree as it is AND fails on the same tree with the change taken out. Anyone, including CI, can
recompute that from the repository alone. No other framework compared does this; they rely on prompt text.

Portability comes from using only what every tool shares: a shell, git, and a plain instruction file. In-editor hooks
are optional adapters, never the enforcement of record.

## 2. The unit of work: an outcome file

`.odd/outcomes/<slug>.md`, committed with the work:

```
---
outcome: A cashier who splits a bill three ways sees three totals that add up to the bill.
proof: pytest tests/test_split.py -q
in: src/billing/**
tests: tests/test_split.py
real: no
base: 3f2a1c9
status: open
---
Free notes: clarifications asked and answered, sources, decisions.
```

- `outcome`: one sentence, who observes what. `proof`: a command that exits 0 only when the outcome holds.
- `in`: globs of product files this outcome may change (the boundary). `tests`: globs of the proof's own files.
- `real`: whether the proof runs against the real system or a simulation. `base`: the commit the work started from.
- `status`: open, done, parked, aborted. Optional: `after: <slug>` (order), `counterfactual: skip - <reason>`.

A requirement becomes one or more outcome files. Their sentences and proofs are the specification; `after:` is the
plan; each file is a task. There are no separate spec, plan or task documents.

## 3. Commands (ten)

| command | what it does | exit |
|---|---|---|
| `odd init [--claude] [--cursor] [--copilot] [--ci] [--hook]` | writes `.odd/`, a vendored copy of the tool (`.odd/odd.py`), the method into `AGENTS.md`, and the chosen adapters; detects them when no flag is given | 0 |
| `odd new <slug> "<outcome>" --proof CMD --in GLOBS [--tests GLOBS] [--after S] [--real]` | writes the outcome file, records `base` | 0 |
| `odd red <slug>` | optional early check: the proof fails now, before the change | 0 if it fails |
| `odd done <slug>` | verifies (section 4), writes the evidence, sets `status: done` | 0 only if verified |
| `odd gate [--base REF] [--recompute]` | every change since base is covered by a verified outcome (section 5) | 0 pass, 1 fail, 2 could not run |
| `odd park <slug> "<reason>"` / `odd abort <slug> "<reason>"` | honest exits: blocked, or cannot be done as specified | 0 |
| `odd widen <slug> <glob> "<reason>"` | adds a glob to the boundary, with the reason recorded | 0 |
| `odd status` | outcomes and their state | 0 |
| `odd stats` | measurements (section 8) | 0 |
| `odd doctor` | is enforcement installed and live; restores an interrupted check | 0 healthy, 1 not |

Also `odd escape <slug> "<what escaped>"`: records a defect found after the gate passed.

## 4. Verification (`odd done`)

1. **Green.** Run the proof in the working tree. It must exit 0.
2. **Counterfactual red.** Put the product files this outcome changed (those matching `in`, not `tests`) back to their
   `base` content, in place, and run the proof again. It must fail. Then restore the files. A journal in `.odd/tmp/`
   lets any later `odd` command restore the tree if the run was interrupted.
   - This one check replaces "see it fail first", the mutation step and the sentence score: a proof that cannot tell
     the change from its absence (`test 1 = 1`, a weakened test) passes on the reverted tree and is rejected.
   - It runs in place so the environment (dependencies, build cache) is identical; a failure is due to the content.
   - If nothing can fail first (a pure refactor), the file carries `counterfactual: skip - <reason>`. Skips are
     counted and listed at every gate, and a project can set `max_skips`.
3. **Boundary.** Every file changed since base is inside some in-play outcome's `in` or `tests`, or is exempt
   (section 6). This is computed from `git`, so it also covers files written through the shell.
4. Evidence is appended to `.odd/evidence/<slug>.jsonl` with a content hash of the proof command and the files in
   `in` and `tests`. A commit or an unrelated edit does not change the hash, so nothing goes stale needlessly.

## 5. The gate, and who is trusted

`odd gate` passes when every non-exempt file changed since base is covered by an outcome that is part of this change
and is verified.

- **Locally** (git hook, or the agent calling it) the gate accepts evidence whose content hash matches the current
  files. This is fast feedback. An agent with a shell could forge a local evidence line; the design does not pretend
  otherwise.
- **In CI** (`odd gate --recompute`) nothing recorded is trusted: every in-play outcome is verified again from the
  checked-out content. This is the authority. A forged evidence line, a skipped hook or `--no-verify` changes nothing.
- Results: pass, fail, could not run (not a git repository, base not found, proof timed out). "Could not run" is
  never reported as pass.

Without CI, the same command in a `pre-push` hook gives the same recomputation on the developer's machine.

## 6. Scaling to the size of the change

- **Trivial lane.** Changes outside any outcome pass the gate while they total at most `trivial_lines` changed lines
  (default 25), with a printed notice. Small low-risk edits need no ceremony.
- **Exempt paths** (default `.odd/**`, `**/*.md`, `docs/**`, licence and ignore files) never need an outcome.
- Both are settings in `.odd/config.json`.

## 7. How it reaches each tool

| layer | Claude Code | Cursor | Copilot / VS Code | any other agent or a person |
|---|---|---|---|---|
| The method (half a page) | `AGENTS.md`, imported by `CLAUDE.md`; skills `odd`, `odd-clarify`, `odd-review`, `odd-research` | `AGENTS.md` and `.cursor/rules/odd.mdc` | `AGENTS.md` and `.github/copilot-instructions.md` | `AGENTS.md` |
| The tool | `odd` in the shell | same | same | same |
| Enforcement of record | git hook and CI | same | same | same |
| Early feedback (optional) | hooks: refuse a write outside the open outcome's boundary; at turn end, block only if this turn changed files and the gate fails; session-start status | none in v1 | none in v1 | none |

The method text has one source (a constant in the tool); `odd init` renders it into each file between markers, and a
test asserts the rendered copies match.

## 8. Measurement

`odd stats` reports, per outcome and in total: time from `new` to `done`, verification attempts (rework rounds),
skips, parks and aborts, escaped defects, changed lines, and real versus simulated proofs. Token cost depends on the
agent, so it is read by adapters (Claude Code transcripts) and by the benchmark harness, not by the core.

The comparison the owner approved: the same tickets, each with hidden acceptance tests, run through plain Claude
Code, ODD, Spec Kit, BMAD and Superpowers; three runs per arm; graded with no partial credit on hidden tests;
reporting pass rate, cost, time, and defects that escaped the arm's own claim of done. Results are published with
their noise band, whatever they show.

## 9. Learning, kept small

- A defect that escaped becomes a new outcome whose proof reproduces it. That is the only "self-heal" mechanism.
- Project rules live in the project's own instruction file, each with a date, the incident and a review date;
  `odd doctor` lists rules past review. No lessons database, detectors or retro gate.

## 10. What was cut from the first draft

Six mandatory stage files; mandatory crawled research; the 0-100 sentence score; the five-level trace chain; the
learning layer (detectors, library, lessons, retro gate); the bundled token guard, step caps and three-minute steps;
the hash-chained ledger idea (CI recomputation replaces it); the single active-run pointer; the judge gates.
Research and review remain as short opt-in skills.

## 11. Known limits and risks

- Locally, an agent with a shell can bypass the hook or forge evidence. Only CI or `pre-push` recomputation closes it.
- The counterfactual check rewrites files in place for the length of one proof run. An editor or agent writing the
  same files at that moment could conflict. The journal restores after a crash, not after a concurrent edit.
- A proof that fails on the reverted tree for an unrelated reason (a flaky test) counts as red.
- An outcome can still be weak and true to its word (`test -f x`). The tool checks that the proof detects the
  change, not that the outcome is worth having. That judgement stays with the reviewer.
- Only the Claude Code adapter has in-editor hooks in v1. Other tools rely on the instruction file and the gate.
- All effectiveness figures are unmeasured until the comparison runs.
