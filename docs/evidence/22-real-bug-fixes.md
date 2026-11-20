# 22. Real bug fixes: lean odd against a plain agent told to write tests

*Written 2026-11-19: everything above "Results" before the runs, the results after them. The design is an independent judge's
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

## Results: not tested; the smoke stopped it

Four runs, $1.45 ([smoke-runs.json](data/real/smoke-runs.json)). The ruling's smoke had nine conditions; eight
held and one did not, and its rule for that one is to stop:

> At most one run hit the $0.40 cap. If this fails: stop, "not tested: these tasks cost more than this budget can
> pay for".

**Two of the four runs hit the cap**, both on the sphinx task, one in each arm. So by the rule fixed beforehand:
**not tested: these tasks cost more than this budget can pay for.** No further run was started; $5.45 of the $6.90
is unspent.

| task | arm | says | hidden file | cost | turns | its own tests without its change |
|---|---|---|---|---|---|---|
| pytest 5631 | plain-tests | DONE | passes | $0.32 | 39 | fail |
| pytest 5631 | odd-lean | DONE | recorded as failing; passes when graded again (below) | $0.31 | 42 | fail |
| sphinx 8035 | plain-tests | none (stopped at the money limit) | passes | $0.41 | 55 | fail |
| sphinx 8035 | odd-lean | none (stopped at the money limit) | passes | $0.41 | 54 | fail |

What four runs can and cannot say:

- **Cost.** A run on these repositories costs $0.31 to over $0.41 with Haiku 4.5, about forty times the $0.008 a
  plain run cost in the sympy pilot of evidence 18, whose model alias was not recorded as resolved. At these prices
  the 26 pairs need about $20 with no limit a run, and the 12 pairs a verdict needs about $9.
- **The one false DONE in the table does not reproduce, and is not counted as one.** The harness recorded lean
  odd's pytest run as failing the hidden file. Graded again by the harness's own function on the kept tree, it
  passes: 13 times of 13, twelve of them at once, and in 4 replays of the whole path (setup, the session's final
  files, odd's post-check, the grade) with two jobs running, as in the run. Lean odd's change is the real fix in
  other words (`p.new is s` for each sentinel, where the project's fix compares with `is` twice). Why the grade
  failed at the time is not established, and until it is, no count from this harness on these tasks should be read
  as a result. On the evidence that can be checked, both arms fixed the pytest issue.
- **The take-out check did refuse something, once, and it was right.** In lean odd's pytest run the first `odd
  done` failed with "the proof still passes with the change taken out, so it does not depend on the change": the
  agent's test, written with a stand-in for a numpy array, passed on the unfixed code. The agent rewrote the test
  and the second `odd done` passed; the test it left fails without the fix. This is the first time the check is seen
  refusing a real agent's test on a real repository. The plain agent's test also fails without its fix, so on this
  task the sentence got there without the check.
- Both arms did equal work on the sphinx task (54 and 55 turns, both passing the hidden file, both cut off before
  reporting): odd added no cost there, and no benefit.

**What it would take to answer the question.** First, the cause of the grade that does not reproduce; then about
$20 for the 26 pairs with the money limit raised to where runs finish, or about $9 for the first 12.

## Second attempt, amended before it is run

The owner approved continuing, with a hard cap of $9.00 for this attempt. The same judge amended the design
([ruling-2.md](data/real/ruling-2.md)) before any further run. What changes:

- **Limits.** `--max-budget-usd 0.50` (it was 0.40: both sphinx runs were cut off at $0.41, already passing, before
  they could report), `--jobs 2` throughout, $0.53 reserved for every run. Turns and time are unchanged.
- **Tasks 1 and 2 are run again** as pairs 1 and 2. The first attempt's four runs stay as reported above and are
  never pooled: the money limit an agent sees has changed, and one of them carries the grade that does not
  reproduce.
- **Every run is graded twice.** The harness now grades in a temporary folder of its own and keeps the grade's last
  lines; after all runs, [regrade.py](../../bench/regrade.py) grades each kept tree once more. The run-time grade
  is the grade of record. A run whose two grades differ is a disputed run: every count is computed under both
  readings, a verdict of shown needs every condition under both, and where the readings disagree the weaker verdict
  stands. Three or more disputed runs: *not tested: this harness's grade does not reproduce*.
- **What $9.00 buys.** It guarantees 8 pairs. Twelve are likely and not certain: pair 12 starts only if the first
  11 cost $7.94 or less. With fewer than 12 the verdict is *not tested* and counts only are reported; the minimum
  of 12 pairs and 5 false DONEs from `plain-tests` stands.
- **Two threats are added:** the limits were raised after the first attempt's costs were seen, and the cause of the
  grade that did not reproduce was never found, so the new safeguards guard against it without explaining it.

Nothing else changes: the hypothesis, the deciding number, the 26 tasks and their order, the arms, the model, the
verdict wordings and the take-out number are as first ruled. The judge's expectation, again as an inference: *not
tested* is still the likeliest outcome.

### Results of the second attempt: not tested, with counts

Twelve pairs, 24 runs, $9.32: ten under the $9.00 cap ($8.12), then the top-up to exactly twelve that the amendment
allows and the owner approved ([runs-2.json](data/real/runs-2.json); harness at bd1abb4 throughout). Every run was
graded twice and **the two grades agree on all 24**. No run was flagged as contaminated.

**By the rule fixed beforehand: not tested.** There are 12 complete pairs, but a verdict also needs at least 5 false
DONE from `plain-tests`, and there are 2. *Told to write and run tests, a plain agent claimed done falsely on 2 of 12
real tasks; that is too few for any method to be shown to remove them. On these tasks, as on the calculator, odd is
not shown to be worth more than the sentence.*

| | plain-tests | odd-lean |
|---|---|---|
| hidden file passes | 5 of 12 | 9 of 12 |
| by project (pytest, sphinx, sympy, pylint) | 3 of 4, 1 of 4, 0 of 3, 1 of 1 | 4 of 4, 2 of 4, 2 of 3, 1 of 1 |
| says DONE | 5 | 8 |
| false DONE | 2 | 1 |
| says NOT DONE (both times with the hidden file failing) | 2 | 0 |
| no claim: cut off by the $0.50 limit | 5 | 4 |
| no claim and the hidden file fails | 3 | 2 |
| cost, twelve runs | $4.51 (median $0.48) | $4.81 (median $0.42) |

- **The deciding pair is (1, 0).** On sympy 12489 `plain-tests` said DONE with the hidden file failing and `odd-lean`
  did not; on no task the reverse. On sphinx 8638 both said DONE and both fail. Counting every failed run with no
  claim as a false DONE it is 5 against 3.
- **The take-out number is K = 1 of 2.** Of the two `plain-tests` false DONEs, one (sphinx 8638) left tests that pass
  with its change taken out: odd's take-out check would have refused it. The other's tests do fail without its
  change. A = 1: one correct `plain-tests` fix (sphinx 8035) was left with tests of its own that do not pass, which
  odd would also have refused. In the twelve `odd-lean` sessions the check refused nothing. Control: of the 10
  `odd-lean` runs whose gate passed, 9 read "fails without the change" and 1 "no test of its own" (below).
  *Corrected by [evidence 24](24-the-check-with-no-setup.md): in that run the agent changed no product file at
  all, only tests. odd would have refused it, but for having nothing to take out, not for a test that passes
  anyway.*
- **`odd-lean`'s one false DONE had a real proof of the wrong thing.** On sphinx 8638 its gate passed, its own tests
  fail without its change, and the hidden file fails: the limit of evidence 18 again, a proof reaches as far as its
  cases. The gate also passed on sympy 12489, where the run was cut off and the hidden file fails. So the gate
  passed on 2 of the 3 `odd-lean` runs that the hidden file fails.
- **Nine of the 24 runs were cut off by the money limit**, so a missing claim is mostly a run that ran out of money,
  about equally in both arms.
- **The verdict line** is in all 8 `odd-lean` reports that made a claim; the Stop hook blocked 7 times.

**On passing the hidden file, which this experiment was not designed to decide:** `odd-lean` passed on 4 tasks where
`plain-tests` did not, and on none the other way (9 against 5 of 12, at 7% more cost). By the same sign test that is
one chance in sixteen if the arms were equal, short of the 0.05 fixed for the deciding number, and it was not the
number fixed beforehand. It is the direction a benefit would have, on twelve tasks, one run each. An experiment
built to test it would fix pass rate as the deciding number first.

**A weakness seen once.** In `odd-lean`'s sphinx 8120 run the whole proof was `cd /tmp/<a project the agent
built> && make ...`: the fix is right and the hidden file passes, but nothing of the proof is in the change, and
the gate passed in the harness's copy only because that folder was still on the machine. odd now reports a proof
that runs in a folder outside the repository, in the verification and the claim (backlog 52, report only).

**Still open.** The cause of the first attempt's grade that did not reproduce: with a private temporary folder for
each grade it did not recur in 24 runs, which guards against it without explaining it. And the question this page
asks: on real bug fixes a plain agent told to write tests made two false DONEs in twelve, which leaves too little
for a check to be shown to remove.
