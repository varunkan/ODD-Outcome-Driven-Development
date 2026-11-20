# 25. The six real bug fixes lean odd does not pass: is it money, the model, or the ticket?

*Written 2026-11-20, before the runs; the results section is added after them. The design is an independent judge's
([ruling-5.md](data/real/ruling-5.md)), fixed before any run. Six tasks chosen because they failed, one run a cell:
counts, not rates.*

## Why

On 24 real bug fixes lean odd passed the hidden tests on 18 (evidence 22 and 23). The owner asked for 24 of 24.
**That is refused as a target**, by the judge and by this page: the hidden tests hold choices the ticket does not
make, so no check can promise it, and even "never a wrong DONE" would need 59 DONE in a row with none wrong to put
the rate under 5%. What can be tested is whether the six failures close with more money or a stronger model.

## Stage 0, at no cost: reading the six

The judge read each kept run, its ticket, the reference fix and the hidden test, by a fixed rubric.

| task | why it failed |
|---|---|
| sympy-12489 | **Out of money mid-work**, on the same change as the reference fix |
| sympy-19040 | **Out of money mid-work**: it had just found the function the reference changes |
| sympy-13615 | **Misread the ticket**: its own test asserts something other than the ticket's expected result |
| sympy-18698 | **The hidden test asks more than the ticket shows**; it chose the other reading to keep an existing test green |
| sphinx-8265 | **The hidden test calls another place** than the one the ticket names; it also lost turns to a wrong `in:` line |
| sphinx-8638 | **The hidden test wants more** (no link at all) than its fair reading (the right link). The one wrong DONE |

So at most 2 of the 6 are a money problem, before any money is spent. The plain agent failed all six too.

## Fixed before the runs

- **Arms**, all the unchanged `odd-lean` at the odd of the 24 runs (harness bd1abb4), one run a task:
  **C**, the control: Haiku 4.5, $0.50 a run, 80 turns, all six. **M**, money: Haiku 4.5, $1.00, 160 turns, the five
  that were cut off. **S**, a stronger model at M's money: Sonnet 5.5, $1.00, 160 turns, all six.
- **A failed run rerun passes sometimes by chance.** C measures that chance; M and S are compared with C's new
  runs, never with the old ones.
- **Deciding number, one per lever:** b tasks the lever's arm passes and C does not, c the reverse; exact one-sided
  sign test at 0.05, which needs b of 5 or more with c = 0. HELPED: the test passes under both gradings. POINTS TO,
  NOT SHOWN: b - c is 2 or more and C passes at most one of those tasks. NO SIGN: anything else. The power to reach
  HELPED is low by design; the reading above expects 2 for M.
- **Seven predictions from the reading, checked as a count:** in M, 12489 and 19040 pass, 13615 and 18698 say DONE
  and fail, 8265 fails; in C, all six fail again, and 8638 says DONE and fails again.
- **Always printed per arm:** right DONE, wrong DONE, unfinished (cut off or silent, with how many of those pass).
- **Budget:** a hard cap of $14.51, the cap of each run plus $0.03 reserved before it starts, no top-up, no rerun.
- **Grades:** every run graded twice; two disputed runs of the 17 and it is not tested.
- **Never said, whatever happens:** "18 + b of 24" (the 18 were not rerun), "never a wrong DONE", or anything about
  other models, projects or tickets.

## Results

*Run 2026-11-20. All 17 runs, $7.18 of the $14.51 cap. No run errored or was contaminated; every run was graded
twice and the grades agree on all 17. Records: [runs-5.json](data/real/runs-5.json).*

| task | C: unchanged, $0.50 | M: twice the money | S: stronger model |
|---|---|---|---|
| sympy-12489 | fails, cut off | **says DONE, fails** | passes, DONE |
| sphinx-8265 | fails, cut off | **says DONE, fails** | passes, says NOT DONE |
| sympy-13615 | passes, cut off | passes, DONE | passes, DONE |
| sympy-18698 | passes, cut off | fails, no claim | passes, DONE |
| sympy-19040 | fails, cut off | passes, no claim | passes, DONE |
| sphinx-8638 | fails, cut off | not run | passes, DONE |
| **hidden tests pass** | **2 of 6** | **2 of 5** | **6 of 6** |
| right DONE / wrong DONE / unfinished (of which pass) | 0 / 0 / 6 (2) | 1 / 2 / 2 (1) | 5 / 0 / 0, and 1 NOT DONE that passes |
| cost | $3.03 | $3.36 | $0.79 |

**The unchanged arm, rerun, passed 2 of the 6 it had failed.** Run-to-run chance alone moves 2 of 6: the old 18 of
24 is 18 give or take, and one run a task was too thin. Every sentence below is read against that.

**Money: NO SIGN.** Twice the money passed 2 of 5; the rerun alone passed 2 of the same 5 (one task each way: b = 1,
c = 1). And it bought 2 wrong DONE where there had been none: runs that had been cut off now finish, and two of
them finish wrong, with odd's gate passing on the agent's own tests.

**A stronger model: 6 of 6 against 2 of 6, and by the rule fixed beforehand that is still NO SIGN.** It passed 4
tasks the rerun did not and lost none (b = 4, c = 0); the test needed 5, and the weaker band needed the control to
pass at most one, and it passed two. Against the money arm at equal money: 3 tasks ahead, none behind. It made no
wrong DONE, and it cost a quarter of the cheap model's runs: 7 to 19 turns a task against 33 to 91.

**What the stronger model's result is and is not.**
- **It is about the model, not about odd.** In 4 of its 6 runs the change was small enough to fit odd's small-edit
  budget, so no outcome was ever written and the take-out check never ran. Two of its fixes brought no test at all.
- **odd got in its way once.** On sphinx-8265 the fix was right and the model said NOT DONE: the gate refused an
  edit to an existing test for lack of a `test-change:` line. An honest report, and a correct fix reported as not
  done.
- **It may have recalled the fixes.** These are public issues with public fixes; nothing here rules that out.

**The reading of the six was mostly wrong as a forecast: 2 of its 7 predictions held.** It said 13615 and 18698
would finish wrong with more money; 13615 passed, and both passed in the plain rerun. It said all six would fail
again; two passed. Classifying one run of a task says little about the next run of it.

**About "100% accurate":** not reached and not promised. On these six tasks: the cheap model unchanged, 0 right
DONE, 0 wrong, 6 unfinished; with twice the money, 1 right, 2 wrong, 2 unfinished; the stronger model, 5 right, 0
wrong, and one correct fix it reported as not done.

**What stands.**
- On these six, more money for the cheap model did not help and made its reports worse.
- A stronger model passed all six for less. Whether odd adds anything to that model is not measured: no plain arm
  ran beside it, and it mostly did not need odd's check.
- One run a task is not enough to say which tasks an arm fails. The 24-task comparisons of evidence 22 and 23
  carry the same weakness.

Limits, as fixed beforehand: six tasks chosen because they failed, one run a cell, two tests, and a stronger model
that changes more than one thing at once.
