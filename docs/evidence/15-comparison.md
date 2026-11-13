# 15. The comparison: plain Claude Code, ODD, Spec Kit, BMAD and Superpowers

*Run 2026-11-11/12. 16 tasks with hidden acceptance tests x 5 arms x 3 repeats, on two models: claude-sonnet-5-5
(240 runs, $36.70) and claude-haiku-5-5 (240 runs, $10.09). Every arm got the same prompt ending and started from
the same state; the odd arm used odd as committed at 0e38e3e in both halves, which is **before** the 0.4.0 features
(proof strength, sealed proofs, the park wording of R3, race, cascade and the rest): those are not measured here.
Harness, tasks and per-run records: [`bench/`](../../bench/SPEC.md). The reports are reproduced with
`python3 bench/report.py <results>`.*

## The result in one paragraph

On tasks like these, **every arm got every doable task right on both models**, plain Claude Code included. No
framework, ODD included, made the code more correct. The only place the arms separated was the impossible tasks on
the weaker model, where most arms sometimes claimed "done" on a contradiction; there ODD and Superpowers did so
least, but with six runs per arm that is a hint, not a finding. Plain Claude Code was the cheapest and fastest; ODD
cost about a quarter to a half more than plain, Superpowers about the same as plain, BMAD and Spec Kit two to five
times as much.

## The figures

Doable tasks: 14 per arm, 3 runs each (42). Impossible tasks: t08 and t15, 3 runs each (6); "honest" means the run
said NOT DONE, every such reason read by a person (all of them named the conflict). Medians per run.

**Sonnet**

| arm | doable tasks right | impossible: honest NOT DONE | claimed done falsely (all tasks) | median cost | median seconds | median turns |
|---|---|---|---|---|---|---|
| plain | 42/42 | 6/6 | 0 | $0.083 | 15 | 4 |
| ODD | 42/42 | 6/6 | 0 | $0.105 | 22 | 5 |
| Superpowers | 41/42 | 6/6 | 1 | $0.091 | 16 | 4 |
| BMAD | 42/42 | 6/6 | 0 | $0.165 | 24 | 8 |
| Spec Kit | 42/42 | 5/6 | 1 | $0.219 | 38 | 14 |

**Haiku**

| arm | doable tasks right | impossible: honest NOT DONE | claimed done falsely (all tasks) | median cost | median seconds | median turns |
|---|---|---|---|---|---|---|
| plain | 42/42 | 3/6 | 3 | $0.012 | 42 | 9 |
| ODD | 42/42 | 4/6 | 2 | $0.019 | 72 | 13.5 |
| Superpowers | 42/42 | 4/6 | 2 | $0.013 | 43 | 9 |
| BMAD | 42/42 | 3/6 | 3 | $0.066 | 175 | 15 |
| Spec Kit | 42/42 | 3/6 | 3 | $0.038 | 123 | 28.5 |

Every false "done" on Haiku was on t08, the parser whose two stated rules contradict each other. On the impossible
tasks, runs that edited or removed a visible test: ODD 0, plain 1, BMAD 2, Spec Kit 2, Superpowers 3 (Haiku; read
from the trees the sessions left).

**Trust.** Claim precision (of the runs that said DONE, the share that passed): Sonnet 98-100% for every arm; Haiku
93-95% for every arm. Silent failures (said DONE on a doable task and failed it): zero for every arm on both models.

**Statistics.** Each arm was compared with plain task by task (exact sign test, Holm-corrected across the report).
Cost and time differences against plain are clear for ODD, BMAD and Spec Kit on both models. No difference in
correctness or in false "done" reaches significance for any arm: with every arm at or near the ceiling there is
almost nothing to differ.

## Two grading corrections, both published

1. **Impossible tasks.** The hidden test passes a NOT DONE only when its reason contains certain keywords. Read by a
   person, every NOT DONE reason in both halves named the conflict correctly; the keyword grade rejected some for
   wording alone (for example "urgent tickets arriving outside desk hours cannot satisfy both 'due within 4 clock
   hours' and 'due while the desk is open'"). The tables above use the reviewed grade; the strict grade and every
   reason verbatim are in each report's appendix.
2. **Contamination on Haiku.** The harness flagged 16 Haiku runs (BMAD 6, Spec Kit 8, plain 2) as contaminated and
   left them out of the rates. Checked against the working directory of every real session in both halves, none of
   them reached another session: each flagged string was a scratch path the agent made for itself under /tmp
   (`/tmp/bench-verify`, `/tmp/bench-check`, `/tmp/bench-cmp.py`, a misspelling of its own directory name, and the
   like), which the contamination rule's pattern `/tmp/bench-*` matched. All 16 runs passed. The tables above count
   them; the report as flagged is reproduced by running report.py on the original records. The rule is too broad
   and is to be narrowed to the real session and copy directories of a run.

## What this does and does not say about ODD

- It does **not** show that ODD makes agents produce better code. On these tasks nothing did; plain was already right.
- It does **not** show that ODD prevents false "done" better than the others: the differences are a run or two out
  of six.
- It **does** show ODD's cost: a fraction of a cent to two cents, and 7 to 30 seconds, more per task than plain
  (medians), much less than BMAD or Spec Kit.
- It **does** show that the odd arm's own check never passed work that was wrong on Sonnet. On Haiku it passed 3 runs
  the hidden tests failed: two on t08, where the agent wrote a proof for one reading of a contradictory ticket and
  said DONE (the take-out check proves the proof depends on the change, not that the reading was right), and one on
  t15 that correctly said NOT DONE but failed only the keyword grade.
- It says nothing about the 0.4.0 features, about tasks large or messy enough that plain agents fail, or about
  anything other than Claude Code.

The next measurement worth making is on tasks where plain agents actually fail (real repositories, longer work), and
with the features built since: the park wording that targets exactly the t08 behaviour, sealed proofs written by a
stronger model, race and cascade ([BACKLOG](../../BACKLOG.md) items 18 and 19).
