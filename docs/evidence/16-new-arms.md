# 16. The new arms: race, cascade and strong-spec on Haiku, against plain Haiku and plain Sonnet

*Run 2026-11-12. 16 tasks with hidden acceptance tests x 3 repeats. Run A, Haiku (claude-haiku-5-5): plain, ODD
0.4.0+ (`odd-040`), `odd race` with three Haiku attempts (`odd-race`), `odd cascade` Haiku then Sonnet
(`odd-cascade`), and Sonnet writing the sealed proof for one Haiku attempt (`odd-spec`); 240 runs, $17.66. Run B,
plain Sonnet (claude-sonnet-5-5), 48 runs, $4.15. odd and the harness at commit 9955b43, before R6-R8. Then, after
both causes found below were fixed, run C: race, cascade and spec again on Haiku, odd and harness at 88ce905, 144
runs, $10.05 (section "After the fixes"). Reports, as generated: [data/new-arms/](data/new-arms/), reproduced with
`python3 bench/report.py <results>`.*

## The result in one paragraph

**After the fixes (run C):** cascade delivered 39 of 42 doable tasks at a median $0.027 a task, a third of plain
Sonnet's cost; race delivered 35 with no false DONE in 48 runs; spec delivered 30 and claimed DONE falsely 5 times.
Plain Haiku delivered all 42 at $0.011 but claimed DONE falsely twice; plain Sonnet delivered all 42 with none at
$0.082. In 17 of the 18 runs where nothing was verified, the coding attempts reported that the sealed proof itself
was wrong (one checked by hand: the proof's own fixture sums to 4900, its assertion says 4800). So the next lever is
a disputed proof sent back for rewriting ([BACKLOG](../../BACKLOG.md) item 23), not the model.

**Before the fixes (runs A and B), as first written:** the hypothesis was that a cheap model driven by odd's new modes could match a strong model for less money. **On
these tasks, as built and driven here, it did not.** Race, cascade and spec gave an honest NOT DONE on every
impossible run (6 of 6 each, as plain Sonnet did; plain Haiku 4 of 6) and race and cascade never claimed DONE
falsely, but they delivered fewer doable tasks than plain Haiku, at three to thirteen times its cost and two to three
times its time. Reading every failure found two causes, neither the model's: a defect in odd's gate that refused
correct work proven as successive outcomes (34 runs), and outcomes run out of dependency order with boundaries too
narrow for an attempt to finish (about 23 runs). Both are fixable; until the comparison is run again after the fixes,
the new modes are not shown to help.

## The figures

Doable tasks: 14 per arm, 3 runs each (42). "Delivered": the run said DONE and the hidden tests passed. "Refused
correct": the arm's verdict (odd's exit status) was NOT DONE although the tree it left passed the hidden tests.
Impossible tasks t08 and t15, 3 runs each (6); every NOT DONE reason was read by a person and every one named the
conflict, so "honest" counts every NOT DONE. Both contamination flags were checked against the runs' real session
directories. One is a scratch path (`/tmp/bench-cmp`). The other (t10, ODD 0.4.0+, run 1) was flagged for a misspelling
of the session's own directory; replaying the narrowed rule later showed the same run had also listed processes (`ps`)
and so seen a concurrent t10 race run's directory name, with every tool call in its own directory. Neither reached
another session's files, so every run is counted.

| arm | doable: hidden tests pass | delivered (DONE and passes) | refused correct | impossible: honest NOT DONE | false DONE (all tasks) | median cost | median seconds |
|---|---|---|---|---|---|---|---|
| plain Haiku | 42/42 | 42/42 | 0 | 4/6 | 2 | $0.011 | 39 |
| ODD 0.4.0+ (Haiku) | 42/42 | 42/42 | 0 | 4/6 | 1 | $0.021 | 83 |
| race, 3 Haiku attempts | 36/42 | 23/42 | 13 | 6/6 | 0 | $0.060 | 131 |
| cascade, Haiku then Sonnet | 29/42 | 18/42 | 11 | 6/6 | 0 | $0.036 | 96 |
| spec: Sonnet proof, Haiku code | 34/42 | 22/42 | 12 | 6/6 | 2 | $0.133 | 82 |
| plain Sonnet (reference) | 42/42 | 42/42 | 0 | 6/6 | 0 | $0.082 | 16 |

Statistics (exact sign test over tasks against plain Haiku, Holm-corrected, in the report): the higher cost and
time of every odd arm are clear; no difference in correctness reaches significance with three repeats. Claim
precision (of DONE claims, the share that passed): race and cascade 100%, plain Haiku 95%, spec 92%. The two false
DONE of spec were on feature tasks where the Sonnet-written proof passed work the hidden tests reject.

## Why the new arms lost: every failure read

The arm flow ([`bench/arm_agent.py`](../../bench/arm_agent.py)): one Haiku session states the outcomes and seals
their proofs (in spec, Sonnet writes each proof through `odd spec`); then each outcome in turn is raced or cascaded,
verified with `odd done`, and committed as `odd: <slug> proven`, the same checkpoint `odd chain` writes; then one
`odd gate --recompute` judges the whole branch. Where each run that did not deliver stopped:

| where it stopped | hidden tests pass | hidden tests fail |
|---|---|---|
| the final gate, after every outcome was raced, verified and committed | 34 | 2 |
| race or cascade: no attempt verified | 1 | 23 |
| spec | 1 | 0 |

1. **The gate refused successive outcomes that share a file (a defect in odd).** When the first session split a
   ticket into several outcomes touching one file, each was proven in turn, and the final gate failed with "X is
   inside the boundary of A and B: within one change a file belongs to one outcome", read in the sessions' own gate
   runs (t06, t10, t11, t13 and others). The rule is from the design review ([10](10-design-review.md), item 8): on
   one change, taking out B's files also takes out A's work, so a hollow B could be credited by A's test. Its remedy
   was "two successive changes", and checkpoints on one branch are successive changes, but the gate measures the
   whole branch from the target and so refuses them. `odd chain` has the same defect: two chained outcomes on one
   file end in a gate that fails. The harness's reason line quoted the first outcome's passing summary instead of the
   gate's problem (`why()` picks the wrong line), which hid this until the transcripts were read.
2. **Outcomes run out of dependency order, with boundaries too narrow to finish (the harness and the method).**
   The harness runs the stated outcomes in name order. On t12 the first session made three outcomes; cascade ran
   `tax-rounding-export` first, whose proof also needs the rounding fix in `invoicing/tax.py`, a file inside another
   outcome's `in:`. Neither level could pass it from `invoicing/export.py` alone, and both said so. Race, with three
   attempts on the same narrow boundary, fails the same way (t11, 0 of 3). Plain and ODD 0.4.0+ work as one session
   on the whole ticket and do not meet this.

## After the fixes

Run C changed two things and nothing else: odd at 88ce905 (successive outcomes on one branch verified as their own
changes, B20; and R6-R8, which these arms do not invoke), and the arms' first session told to prefer one outcome and,
when it splits, to write the build order as `.odd/chains/<ticket>.md`, which the harness follows (item 21). Same 16
tasks, same three repeats, same model. Plain Haiku, ODD 0.4.0+ and plain Sonnet are from runs A and B, the same day.

| arm | doable: hidden tests pass | delivered | refused correct | impossible: honest NOT DONE | false DONE (all tasks) | median cost | median seconds |
|---|---|---|---|---|---|---|---|
| plain Haiku (run A) | 42/42 | 42/42 | 0 | 4/6 | 2 | $0.011 | 39 |
| race, 3 Haiku attempts | 35/42 | 35/42 | 0 | 6/6 | **0** | $0.046 | 100 |
| cascade, Haiku then Sonnet | 39/42 | 39/42 | 0 | 5/6 | 1 | $0.027 | 96 |
| spec: Sonnet proof, Haiku code | 30/42 | 30/42 | 0 | 5/6 | 5 | $0.109 | 99 |
| plain Sonnet (run B) | 42/42 | 42/42 | 0 | 6/6 | 0 | $0.082 | 16 |

- **Refused correct went from 11-13 per arm to 0**: the gate fix holds on real agents.
- **Every run that was not delivered, read.** 18 ended with no attempt verified. In 17 the attempts (one to three per
  run, independently) stopped and named an assertion in the sealed proof that contradicts the ticket, the proof's own
  fixture or another assertion, and refused to edit it, as the method requires. One was checked by hand (t11, race
  run 3: the legacy fixture's checking entries are 80000 - 75000 - 100 = 4900; the Haiku-written proof asserts 4800).
  The other one (t05, spec run 2) is an attempt that believed it had passed and odd did not verify. By task: t11 4
  runs, t10 3, t05, t06 and t13 2 each, t02, t04, t12, t14 and t16 one each.
- **False DONE.** Cascade's one and one of spec's were on t08, the contradictory parser (a proof for one reading of
  the contradiction). Spec's other four (t01, t02, t11, t12) passed odd's gate and failed the hidden tests: the
  Sonnet-written proof depended on the change, as the take-out check requires, but did not check what the hidden
  tests check. The take-out check shows a proof depends on the change, not that it covers the ticket; a held-out
  proof (R8) is the check for that, and these arms ran without one.
- **Contamination.** Five runs were flagged. Three were scratch paths the agent made (`/tmp/bench-odd-base.txt`,
  `/tmp/bench-done.txt`, `/tmp/bench-check`). Two were real: t10 cascade run 1 and t10 race run 1 ran at the same time
  and each listed the other's processes (`ps`), seeing its directory name and test command. Neither made a tool call
  into the other's directory and both passed; they are counted. The harness does not isolate concurrent runs'
  process lists (a known limit, recorded in [RUNNER-NOTES](../../bench/RUNNER-NOTES.md)).
- **Cost.** Run C cost $10.05 in all (race $2.48, cascade $1.98, spec $5.59), less than run A's three arms ($15.45),
  because fewer outcomes meant fewer sessions.

Reading: with the defects out, **cascade comes close to plain Sonnet's delivery (39 of 42) at a third of its cost**,
and **race matches plain Sonnet's zero false DONE** at about half its cost while delivering less. Neither beats plain
Haiku on these tasks, which already delivers everything and costs least; what they add over plain Haiku is fewer
false DONE (race 0 and cascade 1, against 2) and an honest NOT DONE more often. With three repeats per task no
difference in correctness or false DONE reaches significance; cost and time differences do. A cheaper path to the
remaining runs is visible: in 17 of them the attempts had already found the proof's mistake.

## What it does and does not show

- It does **not** show that race, cascade or strong-spec make a cheap model as good as a strong one: as measured they
  delivered less than plain Haiku and cost more than plain Haiku, and spec more than plain Sonnet.
- It **does** show the new modes kept Haiku honest on contradictions: 6 of 6 honest NOT DONE in every new arm,
  against 4 of 6 for plain Haiku, and race and cascade made no false DONE. With six impossible runs per arm this is a
  hint, as in [15](15-comparison.md).
- It **does** show a real defect in odd (successive outcomes on one file refused, also in `odd chain`, shown by a
  test that failed before the fix), found only by running the method end to end on real agents. Fixed after this
  run ([BACKLOG](../../BACKLOG.md) item 20, [DESIGN 5](../../DESIGN.md)); the dependency order and the rerun are
  item 21. These figures are from before the fix.
- ODD 0.4.0+ as a single session matched plain Haiku on doable tasks (42/42) with one false DONE fewer, at about
  twice the cost, as in [15](15-comparison.md).
- After the fixes it shows cascade near plain Sonnet's delivery at a third of the cost, and race with no false DONE,
  on these tasks; not that either beats plain Haiku here.
- It says nothing about R6-R8 (built after runs A and B, not invoked in C), about tasks where plain agents fail, or about agents other than
  Claude Code.
