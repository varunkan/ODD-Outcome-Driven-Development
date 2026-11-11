# ODD design

Version 2, 2026-11-11. This replaces the first design after a four-lens review (tamper resistance, the correctness
of the check, day-to-day friction, portability) returned 23 required changes. The review and its ruling are in
[`docs/evidence/10-design-review.md`](docs/evidence/10-design-review.md).

## 1. What it is

One command-line tool, `odd`, in one file, and a half-page method that a coding agent follows.

**"Done" is recomputed from the code, not claimed by the agent.** An outcome is verified when its proof passes on the
tree as it is, fails on the same tree with the change taken out, and passes again once the change is put back. For
proofs that run from the repository, anyone, including CI, can recompute that.

Install: download `odd.py`, run `python3 odd.py init` in a git repository. It needs a POSIX shell, git 2.23 or newer
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
- Optional lines: `counterfactual: skip - <reason>`, `parked: <reason>`, `escaped: <slug>`.

There is no status field. "Done" is never written to a committed file. A requirement becomes one or more outcome
files; their sentences and proofs are the specification, and each file is a task.

## 3. Commands

| command | what it does | exit |
|---|---|---|
| `odd init [--claude-hooks]` | installs or repairs: `.odd/odd.py`, `.odd/config.json`, the method in `AGENTS.md`, the import line in an existing Claude instruction file; prints the CI step and the conditions under which CI is the authority | 0 |
| `odd new <slug> "<outcome>" --proof CMD --in GLOBS` | writes the outcome file | 0 |
| `odd done <slug>` | verifies the outcome (section 4) and records it locally | 0 verified, 1 not shown, 2 could not run |
| `odd gate [--base REF] [--recompute]` | checks the whole change (section 5) | 0 pass, 1 fail, 2 could not run |
| `odd park <slug> "<reason>"` | the honest exit, for blocked work and for work that cannot be done as specified | 0 |
| `odd stats` | counts, labelled self-reported | 0 |

`odd hook stop|session-start` is an internal entry point called only by the opt-in Claude Code hooks.

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
proof runs per outcome.

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
small-change lane, exempt paths, each skip with its reason), test files that existed at the base and were modified or
deleted, and control files changed.

**CI is the authority only when** (1) the gate is a required check on the target branch, (2) the tool, its settings
and the CI configuration cannot change without a person's review, and (3) the agent cannot merge or push to the
target branch. Without all three the gate is advisory. The CI step runs the copy of the tool from the base revision:

```
git show "origin/$TARGET:.odd/odd.py" > "$TMP/odd.py" 2>/dev/null || cp .odd/odd.py "$TMP/odd.py"
python3 "$TMP/odd.py" gate --recompute --base "origin/$TARGET"
```

It needs full history (not a depth-1 checkout) and the toolchain the proofs use, so it belongs at the end of the
project's existing test job. On GitHub, do not move it to `pull_request_target`. Without CI, run
`odd gate --recompute` before merging.

## 6. Exemptions

- **The small-change lane.** Product lines changed outside any outcome pass while they total at most `trivial_lines`
  (default 25). It is a per-change budget read from the base settings. Small is not the same as low-risk, and a run
  of small changes passes. A binary file or a submodule pointer changed outside an outcome is over the limit.
- **Exempt paths** (default: `.odd/outcomes/**`, `**/*.md`, licence and ignore files, lockfiles).
- **Control files** (`.odd/odd.py`, `.odd/config.json`) need no outcome and are always reported when changed.
- **Test files** and **skips**, as above.

Exemptions are not verification. Each is printed with its line count.

## 7. How it reaches each tool

`odd init` writes the method, about twenty lines, into the root `AGENTS.md` between markers (at the top on first
insertion). That is the only rendered copy. If a Claude instruction file exists (`CLAUDE.md` or `.claude/CLAUDE.md`),
it gets one `@AGENTS.md` import line.

| reads a root `AGENTS.md` without configuration | needs one line of configuration |
|---|---|
| Codex, Cursor, GitHub Copilot in VS Code (and its cloud agent and CLI), Claude Code (directly, or through the import), Junie, Windsurf/Devin | Gemini CLI, Aider, Copilot Chat outside VS Code |

The tool and the gate are the same for every agent and for a person.

Opt-in, per developer, never committed: `odd init --claude-hooks` adds two Claude Code hooks to
`.claude/settings.local.json`. At session start one line of status. At turn end, a block only when this turn changed
files and either a locally verified outcome has gone stale or more than the lane changed with no outcome in play.
The hook commands cannot exit non-zero.

## 8. Measurement

`odd stats` counts outcome files (total, skipped, parked, escaped) and local verification attempts. It is
self-reported and is never published as a result.

Published figures come only from the comparison harness in `bench/`: hidden acceptance tests, the harness's clock and
the token counts the agent CLI reports. It reports "gate passed, hidden tests failed" as its own figure: that is the
size of what this design does not catch.

## 9. Learning

A defect that escaped becomes a new outcome whose proof reproduces it; the file may carry `escaped: <slug>`. There is
no lessons database.

## 10. Limits

- CI is the authority only under the three conditions in section 5. Nothing inside a repository can protect its own
  CI configuration. The change that adopts the tool is judged by its own copy and default settings; a person reviews it.
- The check shows that the proof depends on the change, not that it checks the outcome. A proof that only imports a
  new symbol fails on the tree without it. A flaky test counts as a failure. The last line of the failing run is
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
- Every effectiveness figure is unmeasured until the comparison runs.
