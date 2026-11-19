# Ruling: what odd must incorporate ("minimize tokens, maximum benefit, minimum cost")

Judge: independent LLM, 2026-11-19. Read: evidence 18, 19, 20 in full or by section; the summaries of 15 and 16; BACKLOG 39 to 49;
`DEFAULTS` and `METHOD` in odd.py; DESIGN.md headings 3a to 3q. Nothing was run with a model. Statements marked
**(inference)** are mine, not measured.

## The evidence in one paragraph

odd has one measured benefit: on the calculator, a plain Haiku agent passed the hidden tests 1 of 3 and said DONE
falsely 2 of 3; odd's one-session rounds passed 9 of 9 with 0 false DONE, at $0.23 to $0.40 a run against plain's
$0.27. Everywhere else the benefit is not shown: the duration task (same result, odd +34%, full checks +114%), ten
real sympy issues (24/30 against 25/30, 5 false DONE each, cascade about 4.5 times plain Haiku), and the 16-task
comparison of evidence 15 (every arm correct, odd +25% to +50%). Every newer check was built on the calculator. The
one that was replayed on a second task (`reject:`) did harm there. No check makes untested inputs right: 7 of 9 odd
calculators and 9 of 9 duration programs are wrong on frozen probes.

Two limits of the headline number, both **(inference)**:
- 0 false DONE of 9 against 2 of 3 is about p = 0.045 one-sided (Fisher, my arithmetic), on one task, pooling three
  configurations. It is a hint that survived three rounds, not a rate.
- Which part of odd produced it is unmeasured. No arm isolates the take-out check from "the agent was told to write a
  test and run it". Evidence 18 says the pilot never saw the take-out check refuse anything.

## Per-run costs used below (three runs each, Haiku 4.5)

| | calculator | duration |
|---|---|---|
| plain | $0.27 | $0.19 |
| odd, as `odd init` leaves it | $0.23 | $0.25 |
| + `"cases": "require"` | $0.27 (+$0.05) | not run alone |
| + cases + `"reach": "require"` | $0.40 (+$0.12 more) | not run alone |
| + cases + reach + report hook | not run | $0.40 |
| race then compare (odd-pair) | $0.52, 0 delivered | not run |
| odd-reach then `odd second` | $0.56 | not run |
| Spec Kit, continued | $0.88, a person twice | not run |

## Rulings, items 1 to 13

**1. Take-out check (green-red-green) and `gate --recompute`: CORE.**
It is the product, and the only configuration with a measured benefit (calculator: 0 false DONE of 9 against 2 of 3,
$0.23 against $0.27). It costs two more proof runs and no model tokens of its own. `gate --recompute` is what showed
FAIL in the sixth round's false DONE. Limits: no benefit on duration (+$0.06 a run, +34%) or on real issues; the
check alone is not isolated (see above).

**2. Proof strength (small breaks): REPORT-ONLY, and out of the method text.**
No evidence page measures an effect on delivered work: unmeasured. It costs up to 8 proof runs an outcome (compute,
not tokens). The method text says "full proof strength", and every claim in the 6 measured runs carried "a proof
weaker than the bar" as a not-proven point that 0 of 6 reports repeated. So today it costs agent tokens and changes
nothing measured. Keep `"strength": "report"`, print it in the gate for the reviewer, never fail on it, cut the
phrase from METHOD. `enforce` stays an opt-in value.

**3. `"cases": "require"` (B44): OPT-IN, not recommended.**
Its target was fixed beforehand and not met: 3 of 3 calculators still defective, with 7, 2 and 7 probes wrong against
1, 1 and 8 without it. Cost +$0.05 a run (+21%). The page's own reason holds: the author of the cases is the author
of the code. Keep it off. Remove it if the next experiment shows nothing.

**4. `reject:` / `"reach": "require"` / `valid:` (B45): `reach: require` REMOVE; `reject:` REPORT-ONLY; `valid:` unmeasured.**
Calculator: 74 true, 0 false alarms; the target defect went 3 of 3 to 0 of 3 at +$0.12 a run. Duration: 0 true, 81
false; it failed 3 of 3 runs on correct work, two sessions wrote `none` to escape and one parked correct work and
still said DONE. A rule that is true of expressions and false of unit lists cannot be required of every outcome.
`reject:` may print its findings when an outcome declares it. It must not fail work until it passes rule D. The
`valid:` way out has never been run with a model.

**5. Attempts compared in a race (B46), `odd race`, `odd cascade`: OPT-IN, out of the method text.**
B46 with a model: 0 of 3 delivered, the comparison never ran, $0.52 a run. Race and cascade after their fixes
(evidence 16, run C): cascade delivered 39 of 42 at a median $0.027, race 35 of 42; plain Haiku delivered 42 of 42
at $0.011. On real issues cascade passed 24 of 30 at about 4.5 times plain Haiku, which passed 25. They cost more
and deliver less. Their one measured plus is no false DONE in 48 race runs against plain Haiku's 2. Keep for people
who ask for them. Never the default.

**6. `odd second` (B48): OPT-IN, marked experimental.**
Not shown by its own target. 1 of 3 runs did the comparison, and that one caught and fixed a real defect. Cost $0.56
a run, about 2.4 times basic odd, for 2 to 3 sessions. By its own replay it cannot see a defect both attempts share,
and on duration all 9 programs share their defects. It is the only check that has caught a wrong value with a model,
so it stays, off.

**7. `odd claim` and `"report": "claim"` (B43, B47): OPT-IN; remove `odd claim` from the method text.**
Without the hook: 6 of 6 ran `odd claim`, 0 of 6 reports used it. That instruction is pure token cost. With the
hook: 2 of 3 carried the claim; in the third the hook did not fire and the cause is not established. The hook's own
cost was never isolated (it ran only inside the $0.40 arm): unmeasured. Whether a reader gains from five not-proven
points is unmeasured. The lean form is item 12.

**8. `anchored()` folder check (B49): CORE.**
Deterministic, no model cost. It names a real cause found in 2 of 3 runs and explains the unexplained gate mismatch
of the third round. A proof that names its own absolute path is wrong in any other checkout, CI included, so the
check is sound by construction **(inference)**. Owed, at $0: replay it on the kept duration test files to count
false alarms on a second task. It was seen on the calculator only.

**9. `entry:`, `copied` literals, `probe:`: `entry:` OPT-IN; `copied` REPORT-ONLY, to the reviewer only; `probe:` OPT-IN.**
All three are unmeasured on their own. `entry:` rests on outside literature; in the fourth round sessions declared
it only after a refusal told them how. `copied` is advisory by design and the backlog calls it noisy; reports ignored
tool output 6 times of 6, so printing it to the agent buys nothing **(inference)**: print it in the gate comment.
`probe:` has never run on the harness ("its tasks carry no `probe:` line").

**10. `odd spec` (stronger model writes the proof): OPT-IN, not recommended; next in line for removal.**
It has not been measured against the one-session flow on the calculator. It has been measured against plain agents
(evidence 16, run C): 30 of 42 delivered with 5 false DONE, against plain Haiku's 42 of 42 with 2. Worse on both
counts at higher cost. The fifth round used the same shape (proof sealed first, separate coders) and delivered 0 of
3; one sealed test was itself wrong (29.5 for 28.5). The evidence that exists is against it.

**11. Not built: generic hostile inputs through `entry:`, crash as the only oracle: do not build as a check. A $0 replay first.**
The measured defects are not crashes. Duration: a trailing newline, a tab and a non-ASCII digit are *accepted* with
exit 0. Calculator: wrong values with exit 0 and a wrong exit code. A crash-only oracle would have flagged none of
the defects these pages describe **(inference: the kept programs are not in the repository, so I could not replay
it)**. The inputs are the right ones (they are exactly what all 9 duration programs got wrong); the oracle is the
wrong one. Replay the generator on the 18 kept programs at no model cost. Build only if it finds true alarms and no
false ones on both tasks, and then as report-only (rule D).

**12. Not built: the stop hook refuses a final "DONE" when the gate's verdict is not DONE: BUILD, then CORE where hooks exist.**
This exact failure was measured twice: sixth round run 1 (gate FAIL, report DONE, the only false DONE in any
calculator round) and duration run 3 (outcome parked, report DONE). The check is deterministic, compares two facts
the tool already has, needs no generator and cannot be tuned to a task **(inference)**. It costs one blocked turn
only when it fires. Two conditions: first find out why the B47 hook did not fire in duration run 3, because this
check rides the same hook; and CI's `gate --recompute` stays the authority, since a hook exists only in Claude Code.

**13. Other cuts.**
- METHOD, the requirements file and `--covers` sentence: cut. `"coverage"`: set to `off`. No measured benefit in
  the one-session flow; it makes every session write a file.
- METHOD, "ask one precise question ... and stop there": cut the stop. Evidence 18: asking first stopped work that
  was fine in 12 of 24 runs. Keep `odd ask` as a command, out of the text.
- METHOD, `assume:`, `red-because:`, "Recommended: `odd seal`": cut. All unmeasured in the one-session flow; the
  sealed-proof flows are the ones that delivered least.
- METHOD, "Report `odd claim`'s output": cut (0 of 6).
- METHOD, "full proof strength": cut (item 2).
- METHOD, "If a command can answer a question, run the command" and the owner-decisions sentence: cut to one clause.
  Unmeasured.
- `"owed": "report"`, `"duplication"`, `"inert"`, `"held_out"`, `"auto_lane"`, `"checks"`, `"repeat"`,
  `"max_cost"`, `"max_attempts"`: all off or inert by default already and cost no tokens. Leave them; do not
  document them in anything a session reads. None has a measurement on these pages: unmeasured.
- `"ambiguity_stop": true`: unmeasured. It can cost a retry turn. Leave it on only until it is counted in the next
  run; if it trips on a good outcome sentence once, set it to report.
- Keep the park paragraph, shortened. Honest NOT DONE on impossible tasks is measured (evidence 16: 6 of 6 for
  odd's modes, 4 of 6 for plain Haiku; a hint).

## A. The METHOD text

Current length: 2,509 characters and 404 words as written in odd.py, about 2,600 once `{park_when}` and `{trivial}`
are filled in. That is roughly 600 to 650 tokens **(inference, about 4 characters a token)**.

Be clear about where the money is **(inference)**: 650 tokens read once is well under a cent. The cost is the work
the text asks for: a requirements file, a seal, a prediction, premises, a claim. Each sentence removed removes a
tool call or a file, and that is the saving.

Keep, in this order:
1. Done means the proof says so; `odd` means `python3 .odd/odd.py`.
2. Before code: one outcome sentence, one proof command, the files. `odd new <slug> "<outcome>" --proof "<cmd>" --in "<globs>"`.
3. The proof is a test in its own file under a test path, the narrowest command, relative paths only (B49).
4. `odd done <slug>`, then `odd gate`. Passes only when the proof passes, fails with the change taken out, passes
   again. Then stop.
5. Your last line is the gate's verdict, word for word. If the gate does not say DONE, you do not say DONE.
6. If a pass would need special-casing or weakening a test, or the outcome cannot be checked: `odd park <slug> "<why>"`
   and say so. That is a correct answer.
7. Edits up to {trivial} lines need no outcome. Do not edit `.odd/odd.py` or `.odd/config.json`.

Cut: everything listed in item 13.

Target: **1,200 characters** (about 300 tokens), with the cap lowered from 2,600 to 1,300 so it cannot grow back. A
check never adds text here; it explains itself in its own failure message, which costs tokens only when it fires.

## B. Lean odd

```json
{
  "strength": "report",
  "coverage": "off",
  "cases": "off",
  "reach": "off",
  "report": "off",
  "guard": "enforce",
  "finish_turn": false
}
```

Plus: the take-out check, `anchored()`, `gate --recompute` in CI, the 1,200-character method, and the verdict-only
stop hook once built (item 12). No race, cascade, spec, second, claim, cases, reach or reject by default.

This is close to "odd as `odd init` leaves it" with `coverage` off and a shorter text, so the measured costs of that
arm are the best estimate:

| | plain | odd as measured | ratio |
|---|---|---|---|
| calculator, a run | $0.27 | $0.23 | 0.85 |
| duration, a run | $0.19 | $0.25 | 1.34 |
| both tasks, 6 runs | $1.36 | $1.43 | 1.05 |
| 16 tasks, evidence 15 (an older odd) | | | 1.25 to 1.5 |

Expected cost: **about 1.05 to 1.5 times a plain agent**; cheaper than plain only where plain flounders. The same
tables with every check on: $2.39 for the same 6 runs, 1.76 times plain. Whether the shorter text lowers the ratio
is unmeasured; I expect a little **(inference)**.

What it buys, stated plainly: on one task, fewer false DONE. On the other three measurements, nothing. It does not
make untested inputs right.

## C. The one experiment

The ruling that everything else rests on is item 1, and its cause is not isolated. So: **is odd's core worth more
than one sentence?**

1. Arms: `plain` (3 runs exist), `plain-tests` (the ticket plus one sentence: "write tests, run them, and say DONE
   only if they pass, else NOT DONE"), `lean-odd` (configuration B).
2. Tasks: the calculator first, because it is the only task where plain fails; then tasks added until plain fails
   on at least three.
3. Runs: 3 an arm in the first stage, same model and limits, hidden tests and frozen probes as they stand.
4. Shown: `lean-odd` has at least 2 fewer false DONE of 3 than `plain-tests`, and costs at most 1.25 times it.
   Not shown: anything else. If `plain-tests` has 0 or 1 false DONE, odd's local benefit on this task equals a
   sentence, and what remains of odd's case is the CI recompute.
5. Fixed before the runs, with the arm files committed; reported whatever it shows.

Spending: 6 new runs at $0.23 to $0.27 is about **$1.50**, which fits in $2, calculator only. That gives a hint at
n = 3. A result worth a default needs about 4 tasks x 3 arms x 5 runs = 60 runs at about $0.27, **about $16**. The 53
real tasks are a cheaper second stage per run (sympy runs cost $0.008 plain and $0.038 cascade in evidence 18), about
$3 to $5 for one run of two arms **(inference: other projects' environments may cost more)**, but evidence 18 says
plain agents pass most of them, so they test cost more than benefit.

Do first, at $0: the replays owed in items 8 and 11.

## D. Rule for admitting a check

A check may **fail** work only when all of these hold. Until then it prints, at most.

1. **Two kinds of task, one unseen.** It is replayed with no model on kept programs from at least two tasks of
   different kinds. At least one of them was written after the check's code was frozen at a named commit. Any change
   to the check or its generator after looking at a task makes that task "seen" and resets the count.
2. **No false alarm.** Zero alarms on every program the frozen probes call correct, on every task. One false alarm
   means report-only.
3. **A true alarm away from home.** At least one true alarm on a task it was not built on. A check that is silent
   everywhere else is opt-in for the kind of program it was built for, and says so.
4. **One model round, targets fixed first.** 3 runs or more: it fails no correct work, the session fixes what it
   flags in at least 2 of 3, and the cost a task rises by at most 15%, stated in dollars.
5. **It enters as report-only and is promoted, never the other way round.** Promotion to default-on needs 1 to 4.
6. **Automatic demotion.** One recorded false alarm on correct work in any later run puts it back to report-only
   until 1 to 4 are repeated.
7. **No method text.** A check adds nothing to METHOD. Its failure message carries the instruction and a way out,
   and every use of the way out is printed for the reviewer.

Deterministic checks of facts the tool already holds (items 8 and 12) still need 2 and 4; rule 1 is met by a $0
replay.

By this rule, today: the take-out check and `anchored()` are in (the second with a replay owed); `reject:`,
`cases`, the race comparison, `odd second`, `entry:`, `probe:` and proof strength are not.
