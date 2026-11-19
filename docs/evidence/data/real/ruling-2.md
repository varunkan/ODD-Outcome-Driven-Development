# Ruling 2: amendment for the second attempt (real bug fixes, lean odd against the sentence)

*Ruled 2026-11-19, before any run of the second attempt. Read-only: nothing in the repository was changed and no
model ran. Amends [ruling.md](ruling.md); whatever is not named here stands as ruled. Read: evidence 22 and
ruling.md. Facts taken from the brief, not re-measured by this judge: the four smoke costs and turn counts, the
13 of 13 regrades and 7 replays, the harness changes (private temporary folder, `grade_tail`, a regrade script),
the $9.00 cap. Inferences are marked.*

## A. Limits, reservation and what $9.00 buys

| flag | first attempt | second attempt | why |
|---|---|---|---|
| `--max-budget-usd` | 0.40 | **0.50** | both sphinx runs were cut at $0.41, 54 and 55 turns, already passing, before reporting |
| `--max-turns` | 80 | **80** | the most seen is 55; turns were never the limit |
| `--timeout` | 1200 | **1200** | no run hit it |
| reservation per run | 0.45 | **0.53** | the cap plus $0.03; the overshoot seen is $0.01, twice |
| `--jobs` | 2, then 4 | **2 throughout** | the condition the replays were made under |

Cap: **$9.00**, new money, everything of the second attempt included (voided, errored and rerun runs too). A record
with no cost counts as $0.53. Before each batch: `B = floor((9.00 - spent) / 1.06)`, at most the tasks left.

Arithmetic:

- **Guaranteed: 8 pairs.** 9.00 / 1.06 = 8.49. Holds if every run costs its reservation.
- **12 pairs cannot be guaranteed at any cap where runs finish.** 24 runs in $9.00 is $0.375 a run, below what a
  finished sphinx run costs. Guaranteeing 12 at these limits needs 24 x 0.53 = **$12.72**.
- **Likely: 10 to 12 (inference).** Pair 12 starts only if the first 11 pairs cost $7.94 or less, a mean of $0.361 a
  run. The four runs seen average $0.3625, and two of those were cut short. The first 12 tasks are 4 pytest, 4
  sphinx, 3 sympy, 1 pylint; at about $0.65 a pytest pair, $0.95 a sphinx pair, and $0.60 to $0.70 for the unmeasured
  sympy and pylint pairs, they cost about $8.90. **Reaching 12 is less likely than not.**
- Why 0.50 and not higher: at 0.60 (reservation 0.63) only 7 pairs are guaranteed and each sphinx pair may cost
  $1.20. That 0.50 lets the sphinx runs report is an inference from about $0.0075 a turn.

## B. The first attempt's two pairs: rerun, not reused

Tasks 1 and 2 are run again, both arms, as pairs 1 and 2 of the second attempt. The first attempt's four records stay
as they are at b560e61, reported as the first attempt, never pooled, never counted in N, b, c, F, P, K or A.

Reasons: (1) the agent sees the money limit, and it has changed; (2) the sphinx pair was cut before either arm could
claim, so it would add to N while being unable to say anything; (3) the pytest pair carries a grade the harness
cannot reproduce; (4) ruling.md 3 voids runs when the harness is changed. Reuse would save about $1.45 and make 12
pairs likelier; that is not a reason to count pairs made under other conditions.

These four reruns are also the check of the changed harness: smoke conditions d to h of ruling.md 5 must hold.
Condition i (runs at the money cap) is no longer a stop; it is reported. If d, e, f or h fails: fix the harness
only, rerun once, both costs count. If g fails: stop, odd-lean was not tested.

## C. The regrade rule

- After the last run, a script regrades **every** run **once**, on its kept tree, with the harness's own `grade()`,
  in a private temporary folder, one at a time. The script is committed before the first run. A missing kept tree is
  a disagreement.
- The **grade of record is the grade made at run time.** The regrade never replaces it.
- A run whose two grades differ is a **disputed run**. It is listed with its task, arm, both grades and
  `grade_tail`. Its pair stays complete.
- Every count that uses a grade (b, c, F, P, K, A) is computed twice: with recorded grades and with regrades.
  - **SHOWN** or **SHOWN THE OTHER WAY** needs every one of its conditions to hold under **both**.
  - **F(plain-tests) >= 5** must hold under **both**; otherwise NOT TESTED.
  - If the two readings give different verdicts, the verdict is the weaker one (NOT TESTED before NOT SHOWN before
    SHOWN), and the write-up says "the verdict depends on D disputed grades".
- **Three or more disputed runs:** the verdict is "Not tested: this harness's grade does not reproduce (D of R
  runs)", whatever the counts. With the cause of the first one unknown, three more is a broken instrument.
- No further regrading to settle a dispute, and no hand ruling on which grade is right. Reading `grade_tail` to find
  the cause is allowed and reported; it changes no count.

## D. The minimum stands

12 complete pairs and 5 `plain-tests` false DONE stand. They are what the sign test needs, not a preference.

If the cap yields N < 12: verdict **NOT TESTED**, in ruling.md 8's wording, plus "the $9.00 paid for N pairs". Reported
as counts only, each under both grade readings: N by project, F and P per arm, (b, c), K and A, runs stopped by each
limit, disputed runs, cost per arm and per project, and the cost a pair that 12 would have needed. No rate, no
"trend", no pooling with the first attempt or evidence 18.

A top-up: if N < 12 when the money ends, the owner may add money to reach **exactly 12**, same order, same flags, same
harness commit. That is allowed because below 12 there is no verdict to have looked at. Once N >= 12 has been read,
no extension, and no second repeat or closest calls on new money.

The judge's expectation (inference): NOT TESTED remains the likeliest outcome even at 12, since 5 false DONE from
`plain-tests` in 12 tasks is more than evidence 18 saw from agents told nothing.

## E. What else changes

1. A new `--out` directory for the second attempt; `spent` is summed over it alone. The harness commit is recorded
   once and the harness, the budget script and the regrade script do not change after the first run. A needed change
   voids what ran before it (cost still counts) and is stated.
2. Arms stay frozen at a459c68; check a of ruling.md 5 is repeated before the first run.
3. The cap of ruling.md 6 becomes 9.00 and the divisor 1.06. Stop rules 2, 4 and 5 stand. Rule 3's extras (closest
   calls, second repeat) run only if all 26 pairs complete inside the $9.00.
4. Two threats are added to ruling.md 10: "the limits were raised after the first attempt's costs and outcomes were
   seen, by a judge who had seen them"; and "one grade of the first attempt did not reproduce and its cause was never
   found; the private folder and the regrade guard against it and do not explain it".

Nothing else changes: hypothesis, deciding number, task set and order, arms, model, claim repair, verdict wordings,
the take-out number and the secondary numbers are as ruled.
