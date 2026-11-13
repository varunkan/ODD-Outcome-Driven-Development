# 18. The comparison on real repositories

*Written 2026-11-13. BACKLOG item 18: does odd get more correct work done on real repositories, where plain agents
fail? The design, every change to it and the stop rules were ruled by an LLM judge before any result was seen; a
second judge, blind to the arms, ruled on the failing tests; a third checked this write-up against the data and
corrected it. Data: [data/real-pilot/](data/real-pilot/).*

## Answer

**Not shown.** On ten real sympy issues, odd's cascade passed 24 of 30 runs; plain Haiku 25 of 30; plain Sonnet 25 of
30. Each arm claimed done falsely 5 times. By the stop rule fixed before any run ("not shown: cascade passes no more
runs than plain Haiku"), the claim is not shown on these tasks.

**What was found, read from every run's own tree:**

1. **Plain agents claimed done with no change to the code; odd's arm did not (a hint).** Three plain runs (plain Sonnet
   twice, with no file changed at all; plain Haiku once, adding only a test) claimed DONE without changing a source
   file, all on one task whose ticket no longer reproduced (23950). Every odd run on that task changed source. The one
   odd run that changed no source file (22456) said NOT DONE because its proof failed, so the pilot never saw odd's
   take-out check refuse a no-change claim. By construction it would: with nothing changed there is nothing to take
   out, and `odd done` refuses (test `FailureFeedback`, "nothing changed ... names the remedy", exit 1). Three against
   zero on one task is a hint, not an observation of the mechanism.
2. **The other 12 false "done"s fixed what the ticket shows and failed on more than that.** In 21930 (9 runs, every
   arm) all nine produce the exact output the ticket asks for; a blind judge rated the failing assertions UNCLEAR (4)
   or NOT IMPLIED (1) by the ticket. In 23950 (3 runs) the work handled the case the ticket shows and not the general
   one the blind judge ruled IMPLIED (one cascade run special-cases `S.Reals` only).

So no method here, odd included, verified more than the proof's author understood the ticket to ask for, and the
false "done"s odd let through were all of that kind. That is consistent with a principle, not a measurement of it:
**a proof reaches as far as the requirement it was written from, and no further.** Ten tasks, two models and two
methods give a hint at most.

## Tasks

SWE-bench Verified instances from sympy (people checked each test against its issue), chosen by a rule fixed before
any was tried: one test file, newest first, the first ten whose whole test file fails before the real fix and passes
after it on this machine (`bench/realtasks.py --strict --want 10`). Kept: 20590, 21847, 21930, 22456, 22714, 23534,
23824, 23950, 24443, 24539. Refused: ten candidates whose test file the real fix itself fails here (numpy or scipy not
installed, a sympy expected failure that plain pytest counts as one). The grade is the whole hidden test file, so a
change that breaks another test in it fails (SWE-bench's same-file regression check). Regressions elsewhere in sympy
are not checked.

## Results

90 runs: 10 tasks x 3 arms x 3 repeats, `--max-turns 50 --timeout 600`, harness at commit 4202068, no run errored or
was contaminated. P passed; f failed but claimed DONE; n failed and said NOT DONE.

| task | odd cascade (Haiku, Sonnet if needed) | plain Haiku | plain Sonnet |
|---|---|---|---|
| 20590 | P P P | P P P | P P P |
| 21847 | P P P | P P P | P P P |
| 21930 | f f f | f f f | f f f |
| 22456 | n P P | P P P | P P P |
| 22714 | P P P | P P P | P P P |
| 23534 | P P P | P P P | P P P |
| 23824 | P P P | P P P | P P P |
| 23950 | f P f | f P f | P f f |
| 24443 | P P P | P P P | P P P |
| 24539 | P P P | P P P | P P P |
| **passed** (per repeat) | **24 of 30** (7, 9, 8) | **25 of 30** (8, 9, 8) | **25 of 30** (9, 8, 8) |
| false DONE | 5 | 5 | 5 |
| of them with no source change | 0 | 1 | 2 |
| honest NOT DONE | 1 | 0 | 0 |
| cost a run: min, median, max | $0.011, $0.019, $0.225 | $0.003, $0.008, $0.016 | $0.041, $0.054, $0.225 |
| cost, total | $1.13 | $0.25 | $2.00 |

The cascade used Sonnet in 4 of its 30 runs (22456 in all three repeats, 23950 in repeat 2), so it is close to Haiku
with odd, at about 4.5 times plain Haiku's cost. The whole pilot, smoke run included, cost $3.41 against a $15 cap.

## Every false "done", read

**21930** (9 runs, every arm). The ticket: LaTeX for `Bd(a)**2` prints `b^\dagger_{0}^{2}` and "should be correct by
adding curly brackets `{b^\dagger_{0}}^{2}`". All nine runs print exactly `- \left[b_{0},{b^\dagger_{0}}^{2}\right]` for
the ticket's example. They fail because the hidden test also wants braces on the operator alone (`{b^\dagger_{i}}`) and
on a tensor (`{t^{ab}_{ij}}`). The blind judge, shown only the ticket and the failing assertions: the tensor case NOT
IMPLIED, the four bare-operator cases UNCLEAR ("the ticket does not say where they go").

**23950** (6 runs, every arm). The ticket: `Contains(x, Reals).as_set()` returns a `Contains`, and
`Piecewise((6, Contains(x, Reals)), (7, True))` fails with an AttributeError. On the task's base tree neither
reproduces: the Piecewise example already runs, and `as_set()` raises `NotImplementedError`. The blind judge ruled the
failing assertion IMPLIED (`as_set()` should return the set). Plain Sonnet 2 and 3 changed no file; plain Haiku 1
added only a test; all three claimed DONE. Cascade 1 and 3 and plain Haiku 3 made `as_set()` return the set for the
shown case and not in general (cascade 1 special-cases `S.Reals`).

**The trial run's 24909** (Lite, not Verified; outside the table). Both arms fixed `milli*W == W/1000` as upstream did
and failed only `assert m * k is S.One`, an identity the issue never asks for. This is why the judge moved the pilot
to Verified.

## What this says about odd's claims

- **"odd's own check agrees with hidden tests"** ([PROOF](../PROOF.md)) held on Sonnet over 48 synthetic runs. Here it
  did not: odd's gate passed 5 runs the hidden tests failed. In each, the agent's proof encoded its reading of the
  ticket and the hidden test encoded the test author's. The take-out check shows a proof depends on the change; it
  cannot show the proof asks for everything a reviewer will.
- **"0 false DONE"** for cascade on synthetic tasks does not carry over to these real tasks (5 here, the same as plain).
- **A hint of what odd prevents:** a claim of done with no change to the code: 3 plain runs, 0 odd runs, all on one
  stale ticket; the take-out check that refuses such a claim was not triggered in this pilot (it is shown by odd's
  own tests).
- **A candidate check was measured and not built**: running the project's existing tests next to each changed file
  would have caught 0 of the 5 false "done"s in repeat 1 (measured on its 20 runs: none broke an existing test, and
  none of the 15 passing runs was flagged), so it would cost a proof run and move no number.

## Threats to validity

- **Ten tasks, two of them holding every failure.** No rate and no significance can be claimed.
- **Memorisation.** SWE-bench issues are public. In the passing runs, a median 25% of the real fix's added lines
  appear verbatim, and 7 (cascade), 7 (plain Haiku) and 10 (plain Sonnet) runs reproduce all of them; the fixes are
  2 to 11 lines, so some of that may be coincidence. Memorisation favours plain agents more than odd. Not re-checked
  by the third judge.
- **Too easy for the claim.** Plain Haiku passed 8 of the 10 tasks every time it ran them.
- **A stale ticket.** 23950's reported behaviour does not reproduce on its base tree, which invites a "nothing to do"
  answer; that is where all three no-change claims happened.
- **Environment.** Python 3.13 with no numpy or scipy; tasks needing them were refused, not trimmed (the refusals
  were not re-checked by the third judge).

## How it was run

`bench/realtasks.py` (committed) builds the tasks from the dataset rows; the judge ruled the design (arms, a smoke run
first, whole-file grade, Verified tasks after the smoke found a Lite test asking for more than its ticket, keep every
tree, the $15 cap checked before each batch, stop rules) before results; a blind judge saw only each ticket and
failing test; every failure was re-graded from the run's own kept tree; a third judge recomputed every number and ran
the tickets' examples on the false-DONE trees, and its corrections are applied here. Not done: a second repository,
harder tasks where plain agents fail on what the ticket does say.
