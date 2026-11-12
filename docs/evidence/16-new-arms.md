# 16. The new arms: race, cascade and strong-spec on Haiku, against plain Haiku and plain Sonnet

*Run 2026-11-12. 16 tasks with hidden acceptance tests x 3 repeats. Run A, Haiku (claude-haiku-5-5): plain, ODD
0.4.0+ (`odd-040`), `odd race` with three Haiku attempts (`odd-race`), `odd cascade` Haiku then Sonnet
(`odd-cascade`), and Sonnet writing the sealed proof for one Haiku attempt (`odd-spec`); 240 runs, $17.66. Run B,
plain Sonnet (claude-sonnet-5-5), 48 runs, $4.15. odd and the harness at commit 9955b43, before R6-R8. Reports, as
generated: [data/new-arms/](data/new-arms/), reproduced with `python3 bench/report.py <results>`.*

## The result in one paragraph

The hypothesis was that a cheap model driven by odd's new modes could match a strong model for less money. **On
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
directories and are false (a scratch path, `/tmp/bench-cmp`, and a misspelling of the session's own directory), so
every run is counted.

| arm | doable: hidden tests pass | delivered (DONE and passes) | refused correct | impossible: honest NOT DONE | false DONE (all tasks) | median cost | median seconds |
|---|---|---|---|---|---|---|---|
| plain Haiku | 42/42 | 41/42 | 0 | 4/6 | 2 | $0.011 | 39 |
| ODD 0.4.0+ (Haiku) | 42/42 | 41/42 | 0 | 4/6 | 1 | $0.021 | 83 |
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
- It says nothing about R6-R8 (built after this run), about tasks where plain agents fail, or about agents other than
  Claude Code.
