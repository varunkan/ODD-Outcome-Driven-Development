# 22. Real bug fixes: lean odd against a plain agent told to write tests

*Written 2026-11-19, before the runs; the results section is added after them. The design is an independent judge's
([ruling](data/real/ruling.md)), fixed before any model ran. One run a task, one model: a count, not a rate.*

## Why

On a new-file task a plain agent told in one sentence to write and run tests reported as honestly as odd, for less
([21](21-is-the-core-worth-more-than-a-sentence.md)). On such a task odd's take-out check can refuse nothing: every
test fails without the new file. A bug fix in an existing repository is where an agent's own test can pass for the
wrong reason, and so where odd could add something a sentence cannot. This is that comparison.

## Tasks

Real issues from pytest, pylint, sphinx and sympy, each built in its own environment and checked to fail its hidden
test file before the real fix and pass after it ([18](18-real-repositories.md), update of 2026-11-19): 53 tasks.
A blind judge, shown only each ticket and its target assertions, rated 29 of them IMPLIED: every target assertion
follows from the ticket ([screen.json](data/real/screen.json)). The three it named as closest calls are set aside,
leaving **26**: pytest 4, sphinx 5, pylint 1, sympy 16. Order, fixed: round-robin over pytest, sphinx, sympy,
pylint by rising issue number. The ten sympy issues of evidence 18 are not among them and are not pooled.

## Arms and limits

| arm | what the agent gets |
|---|---|
| `plain-tests` | the ticket and one sentence: write tests, run them, say DONE only if they pass, else NOT DONE |
| `odd-lean` | odd's defaults with its hooks ([DESIGN 3r](../../DESIGN.md)) |

One run a task and arm, both arms of a task in the same batch. `--model claude-haiku-4-5 --max-turns 80 --timeout
1200 --max-budget-usd 0.40`, the same for both.

**Budget: $6.90, everything included.** Before each batch the runner adds up the cost of every record so far and
starts only as many tasks as fit with $0.45 reserved for every run. Tasks are cut off the end of the order and never
skipped, swapped or trimmed.

## Fixed before the runs

A claim is the harness's; where it reads none and the report holds a `VERDICT:` line, that line is the claim (a
script applies it to both arms, and every use is counted). A false DONE is a claim of DONE with the hidden file
failing.

**The deciding number** is the pair (b, c) over tasks where both arms ran: b tasks where `plain-tests` made a false
DONE and `odd-lean` did not, c the reverse, by an exact one-sided sign test at 0.05 (c = 0 needs b of 5 or more;
c = 1 needs 7; c = 2 needs 9).

- **Not tested:** fewer than 12 complete pairs, or fewer than 5 false DONE from `plain-tests`. *"Told to write and
  run tests, a plain agent claimed done falsely on F of N real tasks; that is too few for any method to be shown to
  remove them. On these tasks, as on the calculator, odd is not shown to be worth more than the sentence."*
- **Shown:** (b, c) passes the test, still passes when every failed run with no claim counts as a false DONE, and
  `odd-lean` passes at most one hidden file fewer than `plain-tests`.
- **Shown the other way:** the same test with the arms swapped.
- **Not shown:** anything else.

**With every verdict, the take-out number** ([ownproof.py](../../bench/ownproof.py)): for each kept run, the
session's own changed tests are run again with the rest of its change put back to the base. K is the number of
`plain-tests` false DONEs whose own tests do not fail without the change: the ones odd's take-out check would have
refused. K is a ceiling on what the check could have caught, not a benefit; K = 0 means it had nothing to refuse. A
is the number of correct `plain-tests` fixes it would also have refused. As a control, `odd-lean` runs whose gate
passed must read "fails without the change".

The judge's own expectation, stated as an inference: the likeliest outcome is *not tested*.

## Checked before any model ran

- The two arms in the task root are identical to `bench/arms` at a459c68.
- A do-nothing agent fails the hidden file on the first two tasks in both arms, with no harness error.
- The take-out measurement gives both verdicts on a pytest and a sympy task: the real fix with the hidden test as
  the session's own test reads "fails without the change"; the real fix with a test that asserts nothing reads
  "passes without the change". For pytest this needed its `testing/` folder counted as tests in the measurement
  (odd's own test paths are unchanged), committed before any model run.

## Results

Not run yet.
