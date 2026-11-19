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

Not run yet.
