# 18. The comparison on real repositories

*Written 2026-11-13. BACKLOG item 18: does odd get more correct work done on real repositories, where plain agents
fail? The design, every change to it and the stop rules were ruled by an LLM judge before any result was seen (its
rulings are summarised below); a second, blind judge ruled on the failing tests. Data: [data/real-pilot/](data/real-pilot/).*

## Answer

**Not shown.** On ten real sympy issues, odd's cascade (Haiku, then Sonnet when its proof says so) passed 24 of 30
runs; plain Haiku 25 of 30; plain Sonnet 25 of 30. Each arm claimed done falsely 5 times. By the stop rule fixed before
any run ("not shown: cascade passes no more runs than plain Haiku"), the claim is not shown on these tasks.

**What was found instead, and is the useful result.** Every false "done" was read from the run's own tree:

- In **12 of the 15**, the work did exactly what the ticket shows (its literal expected output, or its examples running
  without the reported error) and failed only on behaviour the ticket does not show.
- In **3 of the 15**, the ticket's own example still failed. All three were plain agents (one plain Haiku, two plain
  Sonnet). **None of odd's 5 false "done"s left the ticket's example failing.**

So the line between what was and was not delivered fell exactly at what the requirement shows. Put as a rule: **"done"
can be proven exactly as far as the requirement shows, and no further, by any model or method.** odd's take-out check
held its side of that line in every run here; past it, no proof written from the ticket can reach. Ten tasks give a
hint, not a rate.

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
| **passed** | **24 of 30** | **25 of 30** | **25 of 30** |
| false DONE | 5 | 5 | 5 |
| honest NOT DONE | 1 | 0 | 0 |
| cost, total (median a run) | $1.13 ($0.019) | $0.25 ($0.008) | $2.00 ($0.055) |

The whole pilot, smoke run included, cost $3.41 against a $15 cap.

## Every false "done", read

**21930** (9 runs, every arm). The ticket: LaTeX for `Bd(a)**2` prints `b^\dagger_{0}^{2}` and "should be correct by
adding curly brackets `{b^\dagger_{0}}^{2}`". All nine runs print exactly `- \left[b_{0},{b^\dagger_{0}}^{2}\right]` for
the ticket's example. They fail because the hidden test also wants braces on the operator alone (`{b^\dagger_{i}}`) and
on a tensor (`{t^{ab}_{ij}}`). The blind judge, shown only the ticket and the failing assertions: the tensor case NOT
IMPLIED, the bare-operator cases UNCLEAR ("the ticket does not say where they go").

**23950** (6 runs, every arm). The ticket: `Contains(x, Reals).as_set()` returns a `Contains`, and
`Piecewise((6, Contains(x, Reals)), (7, True))` fails. The blind judge: IMPLIED (the Piecewise example needs `as_set()`
to return a set). Running the ticket's two examples on each tree: plain Haiku 1, plain Sonnet 2 and plain Sonnet 3
still raise `NotImplementedError`; cascade 1 and 3 and plain Haiku 3 run both examples correctly and fail a case the
ticket does not show (a set with a second free symbol).

**The trial run's 24909** (Lite, not Verified; outside the table). Both arms fixed `milli*W == W/1000` as upstream did
and failed only `assert m * k is S.One`, an identity the issue never asks for. This is why the judge moved the pilot
to Verified.

## What this says about odd's claims

- **"odd's own check agrees with hidden tests"** ([PROOF](../PROOF.md)) held on Sonnet over 48 synthetic runs. Here it
  did not: odd's gate passed 5 runs the hidden tests failed. In each, the agent's proof encoded the ticket's reading
  and the hidden test encoded the test author's. The take-out check shows a proof depends on the change; it cannot
  show the proof asks for everything a reviewer will.
- **"0 false DONE"** for cascade on synthetic tasks does not carry over to these real tasks (5 here, the same as plain).
  On the synthetic tasks the requirement and the hidden test agreed; here they did not, for two tasks.
- **A candidate check was measured and not built**: running the project's existing tests next to each changed file
  would have caught 0 of the 5 false "done"s in repeat 1 (measured on its 20 runs: none broke an existing test, and none of the 15 passing runs was flagged), so it would cost a proof run and move no
  number. A check that runs the ticket's own examples would have caught the 3 plain false "done"s with no false alarm
  in these runs; odd's method already avoided that class (0 of 5).

## Threats to validity

- **Ten tasks, two of them holding every failure.** No rate and no significance can be claimed.
- **Memorisation.** SWE-bench issues are public. In the passing runs, a median 25% of the real fix's added lines
  appear verbatim, and 7 (cascade), 7 (plain Haiku) and 10 (plain Sonnet) runs reproduce all of them; the fixes are
  2 to 11 lines, so some of that may be coincidence. Memorisation favours plain agents more than odd.
- **Too easy for the claim.** Plain Haiku passed 8 of the 10 tasks every time it ran them; the tasks where agents
  fail are ones whose tests ask for more than the ticket says, which no method can fix from the ticket alone.
- **Environment.** Python 3.13 with no numpy or scipy; tasks needing them were refused, not trimmed.

## How it was run

`bench/realtasks.py` (committed) builds the tasks from the dataset rows; the judge ruled the design (arms, a smoke run
first, whole-file grade, Verified tasks after the smoke found a Lite test asking for more than its ticket, keep every
tree, the $15 cap checked before each batch, stop rules) before results; a blind judge saw only each ticket and
failing test. Every failure was re-graded from the run's own kept tree. Not done: a second repository, harder tasks
where plain agents fail on what the ticket does say (the next step, if any).
