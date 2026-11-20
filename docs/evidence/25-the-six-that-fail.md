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

Not run yet.
