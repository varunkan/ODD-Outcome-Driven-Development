# 23. Real bug fixes, the second question: does lean odd pass more often?

*Written 2026-11-19, before the runs; the results section is added after them. The design is an independent judge's
([ruling-3.md](data/real/ruling-3.md)), fixed before any run. One run a task, one model: a count, not a rate.*

## Why

[Evidence 22](22-real-bug-fixes.md) asked whether lean odd makes fewer false DONE than a plain agent told to write
and run tests, and could not be tested: the plain agent made too few. It also showed something it was not built to
decide: the hidden file passed on 9 of 12 tasks for lean odd against 5 of 12, ahead on four tasks and behind on
none. A difference found by looking is a hypothesis. This is the test of it, on tasks neither arm has run.

## Fixed before the runs

- **Hypothesis:** `odd-lean` leaves the hidden file passing on more tasks than `plain-tests`.
- **Deciding number:** the pair (b, c) over the new complete pairs only: b tasks where `odd-lean` passes and
  `plain-tests` does not, c the reverse. Exact one-sided sign test at 0.05: c = 0 needs b of 5 or more; c = 1 needs
  7; c = 2 needs 9; c = 3 needs 10. "Passes" is the run-time grade of the whole hidden file; a run cut off by a
  limit is graded on its files. At least 10 complete pairs, or it is not tested.
- **Tasks:** numbers 13 to 26 of the order fixed in evidence 22, unchanged and cut only off the end: thirteen sympy
  issues and one sphinx. The three closest calls and the screened-out tasks are not used.
- **Arms, model and limits:** as in evidence 22's twelve pairs: `plain-tests` and `odd-lean`, Haiku 4.5, `--max-turns
  80 --timeout 1200 --max-budget-usd 0.50 --jobs 2`, harness at bd1abb4, arms at a459c68.
- **Budget:** a hard cap of $10.00, $0.53 reserved for every run, no top-up. It guarantees 9 pairs.
- **Grades:** every run is graded twice; (b, c) is computed under both readings and a verdict of confirmed needs
  both; three or more runs whose grades differ and it is not tested.
- **Verdicts:** *confirmed* (the test passes under both readings); *confirmed the other way* (the same with the arms
  swapped); *not confirmed* (at least 10 pairs and neither); *not tested*. The twelve pairs of evidence 22 are not
  pooled into the test. A pooled count may be given once, after the verdict, for description only.

## What this can and cannot show, said beforehand

- **The claim is narrow.** Thirteen of the fourteen tasks are one project, and sympy is where the first twelve
  showed the widest gap. A confirmation would be about sympy bug fixes with this model at this money limit, not
  about bug fixes in general.
- **It may be effort and not the method.** odd's method text and Stop hook keep an agent working where the plain arm
  gives up cheaply (on the three sympy tasks so far the plain arm stopped at $0.17, $0.19 and $0.04). A sentence
  such as "do not stop until your tests pass" might buy the same. Nothing here isolates odd's take-out check.
- **The power is low.** By the judge's arithmetic, if the first twelve were exactly right this design confirms
  about half the time; with the shrinkage usual for a difference found by looking, one time in three to one in six.
  Its expectation: not confirmed with the same direction about 65%, confirmed about 25%. A not-confirmed verdict
  here is weak evidence against the hypothesis. A test with power near 0.8 needs about 50 pairs, more screened tasks
  than exist.

## Results

*Run 2026-11-19. Twelve new pairs (tasks 13 to 24 of the order; the budget rule let no more start), $8.98 of the
$10.00 cap. No run errored or was contaminated. Every run was graded twice and the two grades agree on all 24.
Records: [runs-3.json](data/real/runs-3.json).*

**Verdict: not confirmed.** (b, c) = (2, 0): lean odd passed and the plain agent did not on sympy-13877 and
sympy-20154; the reverse happened on no task. With c = 0 the threshold fixed beforehand was b of 5 or more. The
direction is the same as in the first twelve; the count is short of the threshold fixed beforehand.

| twelve pairs, one run each | `plain-tests` | `odd-lean` |
|---|---|---|
| hidden file passes | 7 | 9 |
| says DONE | 7 | 7 |
| says DONE and the hidden file fails (false DONE) | 3 | 0 |
| says NOT DONE | 1 | 0 |
| no claim (of these, hidden file fails) | 4 (1) | 5 (3) |
| cut off by the money limit (of these, hidden file passes) | 4 (3) | 5 (2) |
| cost, total (median, highest) | $4.27 ($0.36, $0.51) | $4.71 ($0.46, $0.51) |
| turns, median | 36.5 | 55 |

What the secondary numbers say, as counts and nothing more:

- **False DONE: 3 against 0.** The plain agent said DONE with the hidden file failing on sympy-13615, 13877 and
  20154; lean odd on none. As a pair that is (3, 0), under the 5 a test would need. Added to evidence 22's 2
  against 1, still not a test: the two experiments were not designed to be pooled.
- **Would the take-out check have refused them? 2 of the 3.** On 13877 and 20154 the plain agent's own tests pass
  with its change taken out (they show nothing about the change); on 13615 they fail without it, so the check would
  have let that one through. One plain run that passed (13647) wrote no test of its own. Control: every lean-odd run
  whose gate passed has tests that fail without the change.
  *Corrected by [evidence 24](24-the-check-with-no-setup.md): on 13877 and 20154 the agent changed no product
  file at all, only tests. odd would have refused both, but for having nothing to take out.*
- **Lean odd did not always finish.** Five of its twelve runs ended at the money limit with no claim, and in three
  of those the hidden file fails. Its own gate failed at the end of three runs (sphinx-9673, sympy-19040, 23262),
  and passed on two whose hidden file fails (sympy-13615 and 18698, both cut off with no claim): a passing gate is
  proof of the agent's tests, not of the hidden ones.
- **Cost:** lean odd cost 1.10 times the plain agent. Runs under $0.20: one plain (19040, fails), two lean odd
  (13647 and 13877, both pass), so "the plain arm gives up cheaply" did not repeat here.
- **Inside lean odd's sessions:** the take-out check refused nothing; the Stop hook sent the agent back 4 times; 6
  reports carry the verdict line; in 4 runs the agent first wrote a proof that names its own folder by absolute
  path, was refused, and ended with a passing gate.

**Pooled, for description only, not a test:** over all 24 pairs of evidence 22 and this page, the hidden file
passed on 18 for lean odd and 12 for the plain agent; on the tasks where they differ, 6 against 0.

**What stands.** On real bug fixes, lean odd has not been shown to pass more often than a plain agent told in one
sentence to write and run tests. Two experiments point the same way and neither reaches its threshold; the limits
said beforehand hold (mostly one project, one model, one run a task, effort not separated from method).
