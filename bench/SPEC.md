# The comparison: specification

Purpose: measure, on the same tasks, what each way of working delivers and what it costs. Five arms: plain Claude
Code, ODD, Spec Kit, BMAD, Superpowers. Results are published whatever they show.

## What is measured, per run (one task, one arm, one repeat)

| measure | how |
|---|---|
| passed | the task's hidden acceptance tests pass on the tree the session left (no partial credit) |
| claimed | the last line of the agent's final message: `RESULT: DONE` or `RESULT: NOT DONE: <reason>` |
| false done | claimed DONE and not passed: a defect that escaped the arm's own check |
| honest not-done | claimed NOT DONE and not passed |
| cost, tokens, turns, seconds | from the `claude -p --output-format json` result, as reported by the CLI |
| changed lines | `git diff --shortstat` against the starting commit, hidden tests excluded |

Per arm: pass rate, false-done rate, median cost, median seconds, with the spread across repeats. A difference inside
the run-to-run spread is reported as no difference.

## Fairness rules

1. Same model, same permission mode, same turn and budget caps, same ticket text for every arm.
2. Each arm starts from a fresh copy of the task's `repo/`, committed as one commit, then prepared by the arm's
   `setup.sh` and committed again. The session runs with `--setting-sources project` and `--strict-mcp-config`, so
   nothing from the machine's own configuration leaks in.
3. The prompt is the arm's `prompt.md` with `{ticket}` replaced. Every prompt ends with the same two sentences:
   nobody will answer questions, so decide and proceed; end with the `RESULT:` line. The rest of an arm's prompt is
   only what its framework documents as the way to start work.
4. Hidden tests are never inside the session's directory. They are copied in only after the session has ended.
5. A hidden test checks behaviour through the interface the ticket names. It never depends on names or structure the
   ticket leaves open.
6. A session that edits or deletes a visible test to pass is graded on the hidden tests like any other.

## Layout

```
bench/tasks/<id>/task.json      {"id", "size": "small|medium|large", "kind": "bugfix|feature|trap|vague|impossible",
                                 "grade": "<command run in the repo after hidden/ is copied in; exit 0 = passed>",
                                 "expect": "done|not-done"}
bench/tasks/<id>/ticket.md      the request as a user would write it; names the public interface; no test hints
bench/tasks/<id>/repo/          starting files: Python 3 standard library only, with a few visible tests
bench/tasks/<id>/hidden/        acceptance tests, copied to the repo root after the session (paths as they will sit)
bench/tasks/<id>/solution.patch a reference change (git diff) used only to validate the task
bench/arms/<arm>/setup.sh       run inside the fresh repo copy; installs the framework at project scope; idempotent
bench/arms/<arm>/prompt.md      the prompt template
bench/arms/<arm>/NOTES.md       sources for how the framework is installed and started headlessly; version pinned
bench/validate.py               every task: hidden tests fail on repo/, pass after solution.patch
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
  states. Passing means: `RESULT: NOT DONE` with the reason, and the existing visible tests still pass unmodified.
  For these tasks `grade` checks exactly that.

`validate.py` requires, for every task with `expect: done`, that `grade` fails on `repo/` and passes after
`solution.patch`; for `expect: not-done`, that `grade` passes on an untouched `repo/` given `RESULT: NOT DONE`.

## Known limits (to be printed with every report)

Tasks are written by this project, are small, and are Python only. One model per run. The frameworks are driven
headlessly, which is not how Spec Kit and BMAD are mainly used. Costs are the CLI's own figures.
