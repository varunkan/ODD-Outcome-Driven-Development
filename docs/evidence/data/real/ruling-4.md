# Ruling 4: the one claim worth testing about `odd check` (real bug fixes)

*Ruled 2026-11-20, before any run. Read-only: nothing changed, no model ran. Read: evidence 22, 23, rulings 1 to 3,
screen.json, runs-2.json, runs-3.json, DESIGN 3r, the four arms, realtasks.py, ownproof.py, odd.py `check` (committed
as 2dd3287 while I read; its message says the replay on the 48 kept runs was still running). Power computed for
this ruling (exact sign test; Fisher by simulation). Inferences are marked.*

## 0. The proposal is refused as the deciding question

"Does `plain-check` make fewer false DONE than `plain-tests`" cannot be answered for this money:
- **The ceiling is small.** `plain-tests` made 5 false DONE in 24. Only 3 read "passes without the change" (sphinx-8638,
  sympy-13877, sympy-20154); the other two (sympy-12489, sympy-13615) read "fails without the change", so the hook
  would let them through. The hook can remove at most 3 in 24, and fewer if any of those three is among the three
  runs that changed only tests, which the new command passes with exit 0. The records do not say which.
- **Power of the sign test**, pb = per-task chance that only `plain-tests` is false, pc the reverse. At (0.125, 0),
  every flagged run fixed and no noise: 0.29 at N = 29, 0.77 at 50. At (0.08, 0.02), 2 of 3 flagged runs fixed:
  0.05 at 29, 0.18 at 50, 0.48 at 100, 0.70 at 150, 0.83 at 200. At (0.08, 0.04): 0.33 at 150.
  A fair test needs about 150 new screened tasks: $159 for two arms, $239 for three, at $0.53 a run.
- **The tasks do not exist.** Unused and IMPLIED: 5 (tasks 25, 26, three closest calls). The other 24 were screened
  out (the hidden test asks more than the ticket). Repeats are not new tasks. `plain-persist` controls nothing here.

## 1. The deciding question, statistic and threshold

**Claim under test:** when `odd check` says a plain agent's tests "pass without the change", the fix is wrong.
It is about the check's verdict, computed with no model on what a plain agent left: one arm, no pairs, no claim
reading. It is also the true alarm on tasks the check was not built on that DESIGN 3r rule 3 asks for.

**Not already answered:** 5 of 5 is a slice found by looking. Ruling 1 registered K and A over three verdicts
together, and so counted the check would also have refused 2 correct fixes (sphinx-8035, sympy-13647). The command
has changed since. For description only: 5 of 5 flagged among 18 failing of 48 runs is p = 0.005 (Fisher); 0 of 30
passing runs flagged puts false alarms under 9.5%; the lower bound on "a flag means a wrong fix" is 0.55.

**Statistic.** Over the new `plain-tests` runs, one a task: N runs, F fail the hidden file, k read "passes without
the change" under the frozen command on the kept tree after the session, f of those k fail the hidden file.
One-sided Fisher exact test at 0.05 that flagged runs fail more often: P(X >= f), X hypergeometric (N, F, k). With
every flagged run failing that is k >= 5 when half of all runs fail, k >= 6 when 0.6 do. "Only tests changed" is
counted apart, not in k: with no product change the hidden file fails by construction.

**Power** (half of all runs fail; q = share of runs flagged; "k < 5" = not tested):

| q, true precision | N = 36 | N = 48 | N = 60 |
|---|---|---|---|
| 4 in 24, 1.0 | 0.71 (k < 5: 0.25) | 0.92 (0.08) | 0.98 |
| 4 in 24, 0.9 | 0.48 | 0.71 | 0.83 |
| 3 in 24, 1.0 | 0.42 (0.52) | 0.72 (0.26) | 0.87 |
| 2 in 24, 1.0 | 0.14 (0.82) | 0.33 (0.63) | 0.53 |
| any, 0.5 (the flag means nothing: the false-positive rate) | 0.02 | 0.02 | 0.02 |

**Gate at $0, before any money (stage 0).** odd.py, ownproof.py and the arms frozen at one named commit. Replay
the frozen command twice on all 48 kept trees and print every verdict beside its hidden grade. Let q0 = old
`plain-tests` runs that read "passes without the change". **q0 = 4: N = 48. q0 = 3: N = 60. q0 <= 2: no model run;
the fallback of section 2 is the result.** Also printed: the new verdict of each of the 5 `plain-tests` false DONE;
ruling 1's check c (both verdicts on one pytest and one sympy task); every `odd-lean` run whose gate passed reads
"fails without the change"; the replay on the kept calculator and duration programs (3r rules 1 and 2).

## 2. Arms, model, limits, money

- **One arm: `plain-tests`.** `plain-check` and `plain-persist` are not run. The hook's effect is 3r rule 4, sized
  by that rule (2 of 3 flagged runs fixed, no correct work failed, cost up 15% at most): its own ruling, later.
- `--model claude-haiku-4-5 --max-turns 80 --timeout 1200 --max-budget-usd 0.50 --jobs 2 --keep --resume`, one run
  a task, a new `--out` directory. Nothing changes after the first run; a needed change voids what ran, cost counted.
- **Hard cap, $0.53 reserved a run, everything included: $25.44 for N = 48** ($31.80 for N = 60). Likely spend
  about $18 (inference: `plain-tests` averaged $0.366 over 24 runs, highest $0.509). Before each batch
  `B = floor((cap - spent) / 0.53)`; a record with no cost counts $0.53; no top-up; no stopping or extending on results.
- **Cheaper fallback: $0.** Publish the stage 0 replay as "seen on 48 runs, not tested", the check report-only.
  N = 36 ($19.08) is allowed only if q0 = 4, its power (0.71 at best) stated first. Under 30 runs: do not buy.

## 3. Counting rules

- **No claim, or cut off by money, turns or time:** the run counts, graded on the files it left and checked as
  left. The deciding number needs no claim. Secondary: the same table for runs that said DONE only.
- **Double grading:** every run is regraded once and the frozen check replayed twice. A run where either differs
  is disputed; the test is computed under every reading and the weaker verdict stands. Three disputed: not tested.
- **Contaminated or errored:** rerun once with `--resume` if $0.53 is left, else listed, not counted. Three errored
  runs in one batch: halt.
- **Not tested:** fewer than 30 counted runs; k < 5; three or more disputed runs; a stage 0 control fails; the
  command or arm changed after the first run; fewer than 36 tasks could be built.

## 4. Tasks: no choice left to the experimenter

None of the 62 candidates or the ten pilot sympy issues. Take every SWE-bench Verified instance of the five
projects SPECS names that is not among them (inference, not checked: about 90; a script prints the list before the
first run). Order: round-robin over pytest, sphinx, sympy, pylint, requests, by rising issue number, a used-up
project skipped. Build in that order with `realtasks.py --strict --python spec --want N`: the first N that build
are the tasks, run in that order, cut only off the end by the budget rule; refused builds are listed. No LLM
screen: Verified's human check of test against issue takes its place. Limit: mostly sympy and sphinx again.

## 5. What each verdict says, written now

- **CONFIRMED** (test passes under every reading): "On N new real bug fixes a plain agent left tests that pass
  without its change on k; the hidden tests fail on f of those k, against F of N overall. `odd check` finds this with
  no model." Not: that the check makes agents better, or anything for another model or project. If f < k add "it
  flagged k - f correct fixes", and by 3r rule 6 the verdict stays report-only.
- **NOT CONFIRMED** (k >= 5, test not passed): "A flag was not shown to mark wrong work: f of k flagged runs fail,
  F of N overall." Not: that the flag is useless; the earlier 5 of 5 stands as an unrepeated observation.
- **CONFIRMED THE OTHER WAY** (same test, flagged runs fail less often): "Flagged runs were more often right than
  the rest." The check stays report-only everywhere.
- **NOT TESTED:** "A plain agent left such tests on k of N tasks: too few to test." It says how often the fault
  happens with this model, nothing about the check. The old 48 are never pooled into the test.

## 6. May "passes without the change" fail work today? No: report-only, and opt-in where it blocks

- **3r rule 1 is not met.** The admitted take-out check is `odd gate`'s, where the author names the proof.
  `odd check` picks the proof itself (every changed test file) with no outcome file: a later change, which resets
  the replay. The 5 of 5 was recorded before the command's final form (three runs now read "only tests changed"),
  and the frozen replay was unfinished at 2dd3287. One kind of task; no program written after the freeze.
- **Rule 2:** not yet replayed on the calculator and duration programs. **Rule 3:** every true alarm is on runs the
  command was shaped on. **Rule 4:** no model round with the hook; "fixes 2 of 3" and "cost up at most 15%" are
  unmeasured. **Rule 5:** it enters as report only.

So `odd check` prints its verdict. Exit 1 in CI and the blocking Stop hook stay opt-in (the Action's `check` mode,
a hook the user installs): not in `odd init --claude-hooks`, and the README may not say the check may fail work.
Stage 0 can meet rule 2 and half of rule 1; CONFIRMED with f = k meets rules 1 and 3; rule 4 needs its own small
round. "Not passing as left" flagged 2 correct runs of 9 (both cut off by money): never fail unfinished work on it.

**Threats to state with the result.** One model, one run a task, mostly two projects: a count, not a rate. The
hypothesis came from looking at the 48 runs; only new runs test it. A flag on a wrong fix does not show the check
helps: a refused agent may still be wrong. Verified tasks with no LLM screen differ from evidence 22 and 23. q0
rests on 24 runs. This judge had read all earlier results; after stage 0 nothing is left to choose.
