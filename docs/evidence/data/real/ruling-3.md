# Ruling 3: confirmation experiment on pass rate (real bug fixes, lean odd against the sentence)

*Ruled 2026-11-19, before any run. Read-only: nothing in the repository was changed and no model ran. Read: evidence
22, ruling.md, ruling-2.md, runs-2.json (cost, claim and grade of the 24 exploratory runs). Whatever ruling.md and
ruling-2.md say and this does not change, stands. Taken from the brief, not re-measured: the harness commit bd1abb4,
the arms at a459c68, the 24 screened-out tasks, the $10.00 cap. Inferences are marked.*

Checked while ruling, in runs-2.json: the three sympy pairs cost $0.67, $0.69 and $0.45. In all three `plain-tests`
stopped cheaply ($0.17, $0.19, $0.04; twice saying NOT DONE, once a false DONE) while `odd-lean` spent $0.41 to
$0.50. The highest cost of any run is $0.5089, under the $0.53 reservation.

## 1. Hypothesis and the one deciding number

**H:** on real bug-fix tasks whose target assertions follow from the ticket, `odd-lean` leaves the hidden test file
passing on more tasks than `plain-tests`.

**Deciding number:** over the complete pairs of this experiment only (one task, both arms, one run each):
b = tasks where `odd-lean` passes the hidden file and `plain-tests` does not; c = the reverse. The pair (b, c),
by an exact one-sided sign test at 0.05: **c = 0 needs b >= 5; c = 1 needs b >= 7; c = 2 needs b >= 9; c = 3 needs
b >= 10.** Recomputed while ruling.

"Passes" is the run-time grade of the whole hidden file. A run stopped by turns, time or money is graded on the
files it left, in both arms. No claim is needed and no claim repair bears on this number.

**Minimum: 10 complete pairs.** Fewer: not tested. (At 9 the test can still be passed, but only by 5 of 9 with none
the other way; the minimum is fixed so that a short run is not read.)

## 2. Tasks

- **Set and order: tasks 13 to 26 of ruling.md's fixed order, unchanged:** sympy-13615, sphinx-9673, sympy-13647,
  sympy-13877, sympy-16792, sympy-18211, sympy-18698, sympy-19040, sympy-20154, sympy-22914, sympy-23262,
  sympy-24066, sympy-24213, sympy-24661. Cut off the end by the budget rule, never skipped, swapped or trimmed.
- **How many:** 9 guaranteed (10.00 / 1.06 = 9.43). **Likely 13 or 14 (inference):** at about $0.60 a sympy pair and
  $0.90 the sphinx pair, 14 pairs cost about $8.70; pair 14 starts only if the first 13 cost $8.94 or less. The
  estimate rests on three sympy pairs.
- **Mostly sympy is acceptable, and it limits the claim.** The order was fixed before any outcome was seen, and
  keeping it untouched is worth more than a better mix chosen by a judge who has seen the 12. The claim, whatever the
  verdict, is: **"on N sympy bug fixes (and one sphinx) from SWE-bench Lite, with Haiku 4.5 and a $0.50 limit a
  run"**. It is not a claim about pytest, sphinx or pylint, and not about real bug fixes in general. Sympy is also
  where the exploratory difference was widest (0 of 3 against 2 of 3): the confirmation runs on the ground that
  favoured `odd-lean`, and the write-up says so.
- **The three closest calls: not used.** They are IMPLIED and would be legitimate for a pass-rate measure, but they
  have no place in the fixed order; putting one pytest and one sphinx task in front now would be a judge reordering
  after seeing where the difference appeared, and at the back they would not be reached.
- **The 24 screened-out tasks: not used, in the deciding number or beside it.** Where the hidden assertions do not
  follow from the ticket, both arms are expected to fail (inference): the pairs are concordant, cost a dollar each
  and move nothing; and a pass there measures guessing the hidden test, not fixing the bug. The ten pilot sympy
  issues stay out, as ruled.

## 3. Limits, jobs, reservation, batches

Identical to the exploratory twelve, because a confirmation tests the same conditions:
`--model claude-haiku-4-5 --max-turns 80 --timeout 1200 --max-budget-usd 0.50 --jobs 2 --keep --resume`, a new
`--out` directory. Harness, budget script and regrade script at bd1abb4, arms at a459c68; check a of ruling.md 5
(arms byte-identical) and a `--dry-run` of task 13 in both arms are repeated at $0 before the first run. Nothing
changes after the first run; a needed change voids what ran before it and its cost still counts.

- **The limit is not raised**, though 9 of 24 runs were cut off: a cut run is graded on its files, so the cut costs
  claims, not grades, and the deciding number needs no claim. A higher limit buys fewer pairs. It is not lowered:
  that would be a different experiment from the one being confirmed.
- **Cap $10.00, everything included** (errored, voided and rerun runs, and any smoke). Reservation **$0.53 a run**.
  A record with no cost counts $0.53.
- **Batch rule:** before each batch a script prints `spent`, `B = floor((10.00 - spent) / 1.06)` (at most the tasks
  left) and the task ids, launches the next B tasks, both arms, and nothing else until every run of the batch is
  recorded. `B = 0`: stop. Worst case after any batch: spent <= 10.00. First batch is 9 tasks; later batches shrink
  to one pair.
- An errored run is rerun once with `--resume`, only if `10.00 - spent >= 0.53` after reserving for nothing else in
  flight; otherwise the pair is incomplete, listed, not counted. Three errored runs in one batch: halt.
- **No top-up.** The cap is hard. N < 10 when money ends: not tested. No stopping, extending or re-running because of
  how the numbers look; the runner reads costs and errors between batches and nothing else.
- No separate smoke: the first batch's records must meet ruling.md 5 d, e, g and h (f is no longer needed). If g
  fails (`odd-lean` did not use odd): stop, not tested.

## 4. Regrade disagreements

Ruling-2 C stands, applied to pass rate. Every run is regraded once after the last run; the run-time grade is the
grade of record; a run whose grades differ is disputed and its pair stays complete. (b, c) is computed under both
readings. **Confirmed, either way, needs the test passed under both.** Where the readings give different verdicts
the weaker stands (not tested, then not confirmed, then confirmed) and the write-up says "the verdict depends on D
disputed grades". **Three or more disputed runs: "Not tested: this harness's grade does not reproduce (D of R
runs)."** No further regrading and no hand ruling on which grade is right.

## 5. Verdicts, worded in advance

N = complete pairs of this experiment. P(arm) = hidden files passed of N.

- **CONFIRMED:** N >= 10 and (b, c) passes the test of 1 under both grade readings. "Confirmed on these N tasks (S
  sympy, 1 sphinx) with this model: odd-lean passed the hidden tests on P(o) of N, plain-tests on P(p) of N (b
  against c on the tasks where they differ), at X times the cost. False DONE: odd-lean F(o), plain-tests F(p)."
  If F(o) > F(p) + 1 the sentence continues: "and it claimed done falsely more often".
- **CONFIRMED THE OTHER WAY:** the same test with the arms swapped. "On these N tasks plain-tests passed the hidden
  tests more often than odd-lean (c against b)."
- **NOT CONFIRMED:** N >= 10 and neither. "Not confirmed. odd-lean P(o) of N, plain-tests P(p) of N (b against c).
  The difference seen in the first twelve (4 against 0) was not repeated at the size this budget paid for." If
  b > c the last sentence reads instead: "The direction is the same as in the first twelve; the count is short of
  the threshold fixed beforehand."
- **NOT TESTED:** N < 10, or three or more disputed runs, or `odd-lean` did not use odd. "Not tested: the $10.00
  paid for N pairs", or the regrade wording of 4. Counts only.

**The exploratory twelve are not in the test.** They were seen before this design was fixed; N, b, c and the verdict
come from the new pairs alone. If the two sets point different ways, the verdict of the new pairs stands and the
write-up states both counts side by side: the first twelve are then an unreplicated observation, not half of a
result. A pooled count may be given once, after the verdict, in this form only: "For description, not as a test:
over all N + 12 pairs, odd-lean passed on x and plain-tests on y (b' against c')." No p-value, no threshold, no
"overall" verdict on the pooled count, and it is never the headline.

## 6. Secondary numbers (none can change the verdict)

1. False DONE per arm, and the old pair (b, c) on false DONE, with ruling.md's claim repair; also with every failed
   run with no claim counted as one. Honest NOT DONE per arm.
2. Cost: per arm total, median, maximum; ratio; and **cost per arm on the discordant tasks**. Only if b > c: "each
   extra hidden-file pass cost $(y - x)/(b - c)".
3. Runs cut off by money, turns and time, per arm; and of the cut-off runs, how many pass the hidden file, per arm.
4. Turns per arm (median), and `plain-tests` runs that ended under $0.20, with their grades.
5. The take-out number as ruled: K, A, the control on `odd-lean` gate passes; take-out refusals inside `odd-lean`
   sessions; "odd's gate passed and the hidden file failed: n of N".
6. Stop-hook blocks, verdict lines, proofs run outside the repository (backlog 52).
7. Disputed runs. P by project. Every discordant task read by hand and listed.

## 7. Threats to state with the result

1. **Small and one-shot:** at most 14 tasks, one run each, one model. A count, not a rate.
2. **Thirteen of fourteen tasks are one project.** Sympy tasks share failure modes; the tasks are not fourteen
   independent draws from "real bug fixes". The claim is limited as in 2.
3. **Chosen ground:** the pass-rate question, and its direction, came from looking at the first twelve; the
   remaining tasks are mostly the project where the difference was widest. The test is honest only because the new
   pairs were not seen; the hypothesis was still fitted to data.
4. **Effort, not method, may be what differs.** On sympy `plain-tests` stopped at $0.04 to $0.19 and `odd-lean`
   spent $0.41 to $0.50. A higher pass rate may be the Stop hook and method text keeping the agent working, which a
   sentence such as "do not stop until your tests pass" might buy as well. The arm is not the take-out check;
   secondary 2, 4 and 5 are what speaks to this, and none of them isolates it.
5. **The money limit is visible** to the agent and cuts `odd-lean` more often on sympy (inference from three
   pairs). A cut can only lower `odd-lean`'s grade, so it works against H, not for it.
6. **Memorisation:** public issues and fixes; lifts both arms.
7. **The grade is the whole hidden file** in an environment resolved by date; a pass can be lost to an unrelated
   test. The first attempt's grade that did not reproduce is still unexplained; the private folder and the regrade
   guard against it without explaining it.
8. **The screen is one LLM's rating**; SWE-bench Lite, not Verified.
9. **Same judge:** this design was written by a judge who had read the exploratory results, including cost by arm.
   Nothing in the task set, order, limits or arms was changed by it; the deciding number and the minimum were.
10. **Run-to-run variation is unmeasured.** With one run a task a discordant pair may be noise in either arm; the
    sign test treats that as it should, but b and c are not properties of the tasks.

## 8. Expectation and power (inference)

Power of this design, computed exactly for a per-task chance pb of an `odd-lean`-only pass and pc of the reverse:

| true (pb, pc) | N = 10 | N = 13 | N = 14 |
|---|---|---|---|
| 0.33, 0.00 (the first twelve taken at face value) | 0.21 | 0.44 | 0.51 |
| 0.33, 0.05 | 0.15 | 0.28 | 0.32 |
| 0.25, 0.05 (some shrinkage) | 0.06 | 0.13 | 0.16 |
| 0.15, 0.08 | 0.01 | 0.02 | 0.02 |

So even if the first twelve were exactly right, the design confirms about half the time; with the shrinkage a
selected observation usually suffers, one time in six to one in three. **The likeliest verdict is NOT CONFIRMED,
with b > c** (my estimate: not confirmed about 65%, confirmed about 25%, not tested about 8%, confirmed the other
way about 2%). A not-confirmed verdict from this design is weak evidence against H: it cannot tell a real effect of
this size from none. That should be said before the money is spent: $10.00 buys a test that can confirm a large
effect and cannot refute a moderate one. A design with power near 0.8 at (0.25, 0.05) needs about 50 pairs (0.69 at 40, 0.81 at
50), about $35 to $40, and tasks that do not exist yet in the screened set.
