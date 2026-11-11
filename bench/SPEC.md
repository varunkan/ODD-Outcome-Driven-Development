# The comparison: specification

Purpose: measure, on the same tasks, what each way of working delivers and what it costs. Five arms: plain Claude
Code, ODD, Spec Kit, BMAD, Superpowers. Results are published whatever they show.

## What is measured, per run (one task, one arm, one repeat)

| measure | how |
|---|---|
| passed | `grade` exits 0 on a copy of the files the session left, with the hidden tests copied in (no partial credit) |
| claim | `DONE`, `NOT DONE` (with its reason) or `none`, read from the agent's final message by the rule below |
| false done | claim `DONE` and not passed: a defect that escaped the arm's own check |
| honest not-done | claim `NOT DONE` and not passed |
| regression | the visible tests, put back as shipped, pass on the session's code; recorded, never part of passed |
| arm check | exit status of the arm's own `post.sh`, when it has one; recorded, never part of passed |
| cost, tokens, turns, seconds | the CLI's own figures, from the final `result` event of its stream-json transcript |
| changed lines | against the "arm setup" commit: all the session wrote, planning documents included; `*.py` lines also apart |

Per arm: pass rate, false-done rate, median cost, median seconds, with the spread across repeats. A difference inside
the run-to-run spread is reported as no difference.

**The claim.** One parser, in `run.py`. It takes the last line of the final message that contains `RESULT:`, strips
Markdown emphasis (`*`, `_`, backtick), list, quote and heading marks and surrounding spaces, and reads the verdict
without regard to case: `DONE`, or `NOT DONE` optionally followed by `:` or `-` and a reason. Anything else is claim
`none`. `run.py` writes `.bench/claim.json` (`{"claim", "reason"}`) and `.bench/final.txt` into the grading copy
before `grade` runs. A hidden test that needs the claim reads `claim.json` and never parses the message.

## Fairness rules

1. Same model, same permission mode, same turn and budget caps, same ticket text for every arm.
2. Same start state: a fresh copy of the task's `repo/`, `git init` on branch `main`, commit "start", the arm's
   `setup.sh`, commit "arm setup", then `run.py` creates and checks out branch `work`. No `setup.sh` creates a
   branch. The repository has a local git identity (`bench`, `bench@example.com`).
3. The session runs with `--setting-sources project` and `--strict-mcp-config`, in an environment built from an
   allow-list (named in RUNNER-NOTES.md; `--pass-env NAME` adds to it) with `GIT_CONFIG_GLOBAL` at an empty file,
   so the machine's own configuration and a hosting session's variables stay out.
4. The prompt is the arm's `prompt.md` with `{ticket}` replaced, a blank line, then `arms/TAIL.md`: the one ending
   every arm gets (nobody will answer, so decide and proceed; the work is judged as the files left in the directory;
   end with the `RESULT:` line). The arm's `prompt.md` is only what its framework documents as the way to start work.
5. Grading never changes what a session can see, and nothing an arm runs afterwards changes what is graded. Every
   session lives in its own temporary directory. When it ends `run.py` makes two copies outside it: G, where the
   visible tests are put back as shipped and run (regression), then the hidden tests are copied in and `grade`
   runs; and P, where the arm's `post.sh` runs. `--keep` keeps the session directory as the session left it, never G.
6. A hidden test checks behaviour through the interface the ticket names. It never depends on names or structure the
   ticket leaves open.
7. A session that edits or deletes a visible test to pass is graded on the hidden tests like any other.
8. A run whose transcript shows a tool input naming the bench repository, `tests_hidden`, a `/hidden/` path or
   another session's directory is `contaminated`: it keeps its grade in the record, enters no rate, and is counted.
9. The odd arm runs the `odd.py` of the bench repository's HEAD commit, never the working-tree file. A real run from
   a bench repository with uncommitted changes is refused unless `--allow-dirty` is given; `bench_dirty` records it.

## The result record (one JSON file per run)

```
passed             true | false | null: not graded (setup failed, or the CLI gave no result, or an error that is
                   not a cap); `error` then says why and is null otherwise
stopped_at         null | "max_turns" | "max_budget" | "timeout": a cap was reached; the tree is still graded
claim, claim_reason, false_done      false_done = claim is "DONE" and passed is false
regression_passed  true | false | null: `python3 -m unittest discover -s tests -q` on the visible tests as shipped
arm_check          exit status of post.sh in P, or null
changed_lines, files_changed         everything, against the "arm setup" commit; changed_lines_py: `*.py` only
branch, worktrees, left_outside      the branch checked out at the end; the count from `git worktree list`; true
                   when a worktree other than the session directory exists, or a local branch other than main and
                   work holds commits HEAD does not reach (work the grade never saw)
contaminated, contaminated_by        rule 8, and the first string that showed it
models             the model ids that did work
transcript         file name of the saved stream-json transcript, beside the record
provenance         {bench_commit, bench_dirty, odd_sha256, task_tree, arm_version}
env_passed         names of the environment variables the agent received
```

## Layout

```
bench/tasks/<id>/task.json      {"id", "size": "small|medium|large", "kind": "bugfix|feature|trap|vague|impossible",
                                 "grade": "<command run in G after hidden/ is copied in; exit 0 = passed>",
                                 "expect": "done|not-done", "note": "<optional: what a pass does not show>"}
bench/tasks/<id>/ticket.md      the request as a user would write it; names the public interface; no test hints
bench/tasks/<id>/repo/          starting files: Python 3 standard library only, with a few visible tests
bench/tasks/<id>/hidden/        acceptance tests, copied to the root of G after the session (paths as they will sit)
bench/tasks/<id>/solution.patch a reference change (git diff) used only to validate the task
bench/arms/TAIL.md              the ending every arm's prompt gets
bench/arms/<arm>/setup.sh       run inside the fresh repo copy; installs the framework at project scope; idempotent
bench/arms/<arm>/prompt.md      the prompt template, without the ending
bench/arms/<arm>/post.sh        optional: the arm's own check, run in P; its exit status is `arm_check`
bench/arms/<arm>/VERSION        one line: the release or commit setup.sh installs (or "this repository", "none")
bench/arms/<arm>/NOTES.md       sources for how the framework is installed and started headlessly; its section
                                "## To state with the results" is printed by report.py
bench/validate.py               every task: grade fails on repo/, passes after solution.patch; nothing leaks
bench/run.py                    runs task x arm x repeat; writes bench/results/<run-id>/<task>.<arm>.<n>.json
bench/report.py                 aggregates a results directory into a table and a JSON summary
```

## Task kinds

- **bugfix** (small): a defect with a clear report. Hidden tests: the reported case and two neighbours.
- **feature** (medium): new behaviour across two to four files. Hidden tests: the behaviour the ticket states.
- **trap**: the obvious change passes the visible tests and breaks something the ticket states plainly. Hidden tests
  cover the stated requirement.
- **vague**: the ticket is underspecified in one respect; any sensible reading passes; hidden tests check only what
  the ticket does state.
- **impossible** (`expect: not-done`): the ticket asks for something that cannot hold given a constraint it also
  states. Passing means: the claim is `NOT DONE` with a reason, and the visible tests as the task ships them (a copy
  under `hidden/`) pass on the session's code. Tests the session added do not matter; tests it edited cannot help.
  The reason is not judged: any `NOT DONE` with a reason passes, so a pass does not show that the contradiction was
  found.

`validate.py` requires, for every task with `expect: done`, that `grade` fails on `repo/` and passes after
`solution.patch`; for `expect: not-done`, that `grade` passes on an untouched `repo/` when the claim is `NOT DONE`
with a reason and fails when it is `DONE`, has no reason or is missing. For every task it also fails on a leak: the
words hidden, bench, solution, grade, acceptance, RESULT, trap, impossible or vague in `ticket.md` or under `repo/`,
or a compiled or patch-reject file anywhere in the task.

## Known limits (to be printed with every report)

Tasks are written by this project, are small, and are Python only. One model per run. The frameworks are driven
headlessly, which is not how Spec Kit and BMAD are mainly used. Costs are the CLI's own figures. There is one
impossible task, one vague task and two traps, so a figure per kind rests on one or two tasks. On the impossible
task the common ending's "decide and proceed" pulls every arm towards claiming DONE.
