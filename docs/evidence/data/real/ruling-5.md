# Ruling 5: what can honestly be tested about the 6 of 24 that lean odd does not pass

*Ruled 2026-11-20, before any run. Read-only: nothing changed, no model ran, $0 spent. Read: evidence 22 to 24,
rulings 3 and 4, DESIGN 3r, 3s, 4a, 4c, the three arms, run.py flags, and for stage 0 the six kept trees and
transcripts, tickets, reference fixes and hidden tests. Inferences are marked.*
## 0. "100% accurate" is refused as a target, and what replaces it
No experiment here can show 24 of 24, and no check can promise it: the hidden tests hold choices the ticket does not
make (stage 0 finds three such tasks of the six). The engineer's statement stands, unsoftened. What can be tested:
(a) more tasks passing, (b) fewer wrong DONE. "Never a wrong DONE" cannot be shown either: 59 DONE in a row with
none wrong are needed to put the wrong-DONE rate under 5% (0.95^59 = 0.048). Lean odd has 14 DONE, 1 wrong.

## 1. Stage 0, done for $0: why each of the six failed
Rubric (set while reading the first two, then held): **A** out of money mid-work on a path that matches the reference fix; **B** finished
work that misreads what the ticket states; **C** finished work that meets a fair reading of the ticket, the hidden
test asks for more or for another place; **D** lost to the tool's own bookkeeping.

| task | class | evidence |
|---|---|---|
| sympy-12489 | A | Same change as the reference (`_af_new` made a classmethod, call sites moved one Edit at a time); the last call before the cut is one more such Edit; module-level call sites left. |
| sympy-19040 | A | No product file changed. Last message: "Found it! The issue is in Step 3", in `dmp_ext_factor`, the function whose one line the reference changes. |
| sympy-13615 | B | Ticket: "`{x, y} \ [-10,10]` is expected". Its own test asserts `{2, x, y} \ [-10,10]`. Gate passed; cut while writing "The fix is working perfectly". |
| sympy-18698 | C | It wrote "the convention in SymPy is to NOT combine factors at multiplicity 1" to keep an existing test green, and added `exp > 1`. The hidden test wants them combined (`sqf_list(x*(x + y))`); the ticket's example shows only multiplicity 3. Gate passed; cut at its last check. odd's strength report named that very line as unproven. |
| sphinx-8265 | C, part D | Fixed the symptom in `sphinx/util/inspect.py`; the hidden test calls `sphinx.pycode.ast.unparse`, which the ticket never names. Its test passes without the change. Last calls: `odd done` refused because `in:` named the wrong file. |
| sphinx-8638 | C | Ticket: "not be linked to any other". It made the lookup prefer the class's own attribute; the hidden test wants no link at all (the reference removes the role). The one wrong DONE; its tests fail without the change. |

What this already says, before money: **at most 2 of the 6 are a money problem.** More money on 13615 and 18698
would most likely have bought two more wrong DONE, not two passes (inference: both were at their summary). The
plain agent also failed all six: 12 failures in 12 runs, so these are hard tasks for this model, not six unlucky runs.

## 2. The levers
- **(1) Money: tested.** **(4) The model's reading: tested**, with a stronger model at the same money.
- **(2) Reproduce-first in the lean arm: refused, no arm.** At `odd done` a `kind: bug` outcome requires what the
  take-out check already requires (DESIGN 4a: "the base run is the take-out of section 4, unchanged"). Every lean
  run whose gate passed already reads "fails without the change" (evidence 24). Of the six, only sphinx-8265 had a
  test that did not reproduce the bug, and its gate was already failing for it. Nothing would change.
- **(3) `odd spec`: not in this budget.** It changes author, model and cost at once and needs its own control.
  It is the only lever aimed at class C, and section 6 says what its absence costs.

## 3. What to run: three arms, all the existing `odd-lean` directory, nothing to build

| arm | model | cap a run | turns | tasks | reserved |
|---|---|---|---|---|---|
| **C** control: the unchanged arm again | `claude-haiku-4-5` | $0.50 | 80 | all six | 6 x $0.53 = $3.18 |
| **M** money | `claude-haiku-4-5` | $1.00 | 160 | the five cut off (not 8638: it stopped by itself at $0.42) | 5 x $1.03 = $5.15 |
| **S** stronger model, same money as M | `claude-sonnet-5-5` | $1.00 | 160 | all six | 6 x $1.03 = $6.18 |

- Every run: `--arms odd-lean --odd-commit bd1abb4 --timeout 1200 --jobs 2 --keep --resume`, one run a task, one
  new `--out` per arm. `bd1abb4` is the odd of the 24 runs, so C is the same arm. Turns are doubled with the money,
  or the turn limit would replace the money limit (the cut runs used 43 to 68 of 80 turns for $0.50).
- `claude-sonnet-5-5` is the only Sonnet this harness has recorded (evidence 12; the alias `sonnet`).
  `claude-sonnet-4-5` has never run here and is not used. An S run whose `models` field holds anything else is void.
- **Regression to the mean is controlled by C, not by argument.** A failed run rerun passes sometimes by chance.
  C is that chance, measured on the same six tasks. M and S are compared with C's new runs, never with the old ones.
- **Hard cap $14.51**, everything included, reserve = cap per run + $0.03. A run starts only if cap minus spent
  minus reserves in flight covers its reserve. A record with no cost counts its reserve. No top-up, no rerun of an
  errored run (it is listed, its pair not counted), no stopping or extending on results. Task order: 12489, 8265,
  13615, 18698, 19040, 8638; the three arms of a task are one batch. Likely spend about $12 (inference).

## 4. Numbers fixed now
- **Deciding statistic, one per lever:** pairs on the hidden file's run-time grade; a cut run is graded on its
  files. **M against C** on five tasks, **S against C** on six: b = tasks the lever's arm passes and C does not,
  c = the reverse. Exact one-sided sign test at 0.05: **b of 5 or more with c = 0.** Nothing less passes it. S
  against M (five tasks, equal money) is secondary: it is what separates the model from the money.
- **Bands:** HELPED = the test passes under both gradings. POINTS TO, NOT SHOWN = b - c is 2 or more and C passes
  at most one of those tasks. NO SIGN = anything else. The power to reach HELPED is low by design: stage 0 expects
  b = 2 for M. Said now so that NOT SHOWN is not read as a failure of the run.
- **Stage 0's predictions, checked as a count of 7:** in M: 12489 passes; 19040 passes; 13615 says DONE and
  fails; 18698 says DONE and fails; 8265 fails. In C: all six fail again; 8638 says DONE and fails again.
- **Wrong DONE, per arm, always printed beside the passes:** right DONE (says DONE, hidden passes), wrong DONE,
  no claim (and how many of those pass), honest NOT DONE.
- **Double grading:** every run regraded once; a run whose grades differ is disputed; verdicts are computed under
  both readings and the weaker stands. Two disputed runs of the 17: not tested.
- **Not tested** (per lever): fewer than 5 complete pairs; two disputed runs; a wrong model in `models`; the arm,
  odd commit or flags changed after the first run (what ran is void, its cost counts); lean odd not used in a run.

## 5. Headline: yes, wrong DONE first, pass count second
A cut run with no claim is **not a wrong DONE and not a success: it is "unfinished"**, its own column, with the
hidden grade beside it. Three columns always: right DONE, wrong DONE, unfinished. Today, lean odd over 24: 13 right
DONE, 1 wrong, 10 unfinished or silent (5 of them pass). Plain: 5 wrong DONE. Two rules so the headline cannot be
gamed: an arm may not look honest by not finishing (so right DONE is always shown), and unfinished runs are also
shown counted as failures. Pass count stays the deciding statistic here because money and model act on it.

## 6. Money
- **Recommended: $14.51** (section 3).
- **Cheaper fallback: $8.33**: C on six and M on five, no S. Lost: any test of "the gap is the model's reading".
  Or **$0**: publish section 1 as "read, not tested"; it already rules out money for 4 of the 6.
- **Lost against a larger design** (all 24 tasks in the three arms, $62.16): no new "x of 24" may be stated; nothing
  is learnt about whether more money or a stronger model breaks any of the 18 passes or turns their 5 unfinished
  runs into right DONE; and lever 3 stays untested (an `odd-spec` arm on 24 with its control: about $50 more).

## 7. Sentences, written now
- **M HELPED:** "With twice the money lean odd passed b of the 5 cut-off failures; the unchanged arm, rerun,
  passed k." To the owner: "Money closes part of the gap. It is not 100%: n of 6 still fail."
- **M POINTS TO / NO SIGN** (expected): "Twice the money moved b of 5 (the rerun alone: k). Reading the six said
  2 at most." If wrong DONE rose: "and it bought w more wrong DONE: runs that had been cut off now finish wrong."
- **S HELPED:** "A stronger model at the same money passed b of 6. The gap was mostly the model." To the owner:
  "The lever is the model, not odd; odd's part is that the wrong ones are fewer or flagged, if the table shows it."
- **S POINTS TO / NO SIGN:** "A stronger model did not close the six (b of 6). What is left is what the ticket does
  not say." To the owner: "These need a person's answer or a better ticket. No tool setting gets them."
- **C passes 2 or more of six:** "Run-to-run chance alone moves 2 of 6: the old 18 of 24 is 18 give or take, and
  one run a task was too thin." Every other sentence is then read against that.
- **Not tested:** counts only, and the reason. **Under every outcome, about "100% accurate":** "Not reached and not promised. Lean odd: x right DONE, y wrong,
  z unfinished." **Never said:** "18 + b of 24" (the 18 were not rerun, and some would fail too); "never a wrong
  DONE"; anything about other models, projects or tickets.

## 8. Threats to state with the result
Six tasks chosen because they failed: C corrects the comparison, not the smallness. One run a cell. The agent sees
its budget, so M differs from C in more than money. S against C changes model and money together. Two tests at 0.05.
The judge who read stage 0 set the predictions; the rubric took shape while reading. A stronger model may recall the fix.
