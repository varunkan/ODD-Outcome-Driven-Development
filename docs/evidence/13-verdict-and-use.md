# 13. Verdict so far, and where ODD is really useful

*Written 2026-11-12 and updated when both halves of the comparison finished ([15](15-comparison.md)). Every figure
links to its source; what is not shown is said to be not shown.*

## The verdict in one paragraph

ODD is worth using as a **trust layer for code written by agents**, not as a productivity booster. It does what it was
built to do: it refuses a "done" whose proof does not depend on the change, and in CI nothing it judges can loosen
its own check. On a strong model it does not make the work more correct, because plain Claude Code already gets
almost everything right on tasks like ours. Its value grows with how little the agent's work is watched.

## The facts behind it

**1. The tool does what it claims.**
- It refuses a test that asserts nothing and accepts a real one: [`launch/demo.sh`](../../launch/demo.sh), run by the
  test suite so the demo cannot drift from the tool.
- A design review applied 23 changes ([10](10-design-review.md)); a red team confirmed 48 defects in 0.2.0, each now
  a test that failed before its fix ([11](11-red-team.md)). The suite is green on Linux (Python 3.8 and 3.13) and macOS.

**2. In real runs its own check agreed with the hidden tests.** In the 48 Sonnet runs of the comparison, ODD's own
gate passed 47 times; in none of them did the hidden tests then fail. The one disagreement went the safe way: the gate
failed on work the hidden tests accepted.

**3. On a strong model, correctness is already at the ceiling.** Sonnet, 16 tasks x 3 runs per arm, hidden tests,
with every "not done" reason on the impossible tasks read by a person:

| arm | runs right | claimed done falsely | median cost per task | median seconds |
|---|---|---|---|---|
| plain Claude Code | 48/48 | 0 | $0.08 | 14 |
| ODD | 48/48 | 0 | $0.11 | 21 |
| BMAD | 48/48 | 0 | $0.17 | 23 |
| Superpowers | 47/48 | 1 | $0.09 | 16 |
| Spec Kit | 47/48 | 1 | $0.22 | 37 |

The strict keyword grade, fixed before the run, reads lower for several arms (plain 46/48, BMAD 46/48, Spec Kit 44,
Superpowers 45, ODD 48). The gap is the grader, not the work: eight correct "not done" answers on the second impossible
task named the conflict ("rules 1 and 2 contradict for urgent tickets arriving while the desk is closed") without the
literal words "four hours" that the keyword check requires. ODD's 48/48 on the strict grade is therefore not evidence
that ODD answers impossible tasks better. Both grades, with every reason verbatim, will be published with the full
results. Cost differences against plain are statistically clear (exact sign test over tasks, Holm-corrected);
differences in correctness and false "done" are not.

**4. The cost is modest.** About three cents and seven seconds more per task than plain Claude Code, about half
of Spec Kit's and about two thirds of BMAD's, on the same tasks.

**5. The method behind it worked in the project it came from.** Measured from 6,047 commits of the source project as
the method matured: process lines per product line fell from 9.9 to 2.4, the slowest tenth of changes from 133 hours
to 12, reverts from 2.7 to 1.0 a week ([01](01-method-measured.md)). One project, measured by itself.

## What is not shown

- That ODD makes agents produce better code. On Sonnet it did not, and could not, since plain was already right.
- That ODD prevents false "done" better than the others. Its zero matches plain's zero; the others' one each is too
  few to call a difference.
- That ODD helps a weaker model get work right: on Haiku every arm, plain included, got all 42 doable runs right. On
  the impossible tasks ODD and Superpowers claimed "done" falsely in 2 of 6 runs, plain, BMAD and Spec Kit in 3 of
  6, and ODD never edited a visible test (others 1 to 3 times): a hint in six runs, not a finding
  ([15](15-comparison.md)).
- That race, cascade or a strong model's proof make Haiku as good as Sonnet for less: as first run they delivered
  fewer tasks than plain Haiku at higher cost; after two defects were fixed, cascade delivered 39 of 42 at a third of
  plain Sonnet's cost and race made no false DONE, but neither beat plain Haiku on these tasks ([16](16-new-arms.md)).
- Review time saved, adoption by other teams, or any agent other than Claude Code running the method.

## Where it is really useful

| situation | why ODD helps there | what to set up |
|---|---|---|
| agents open pull requests | a reviewer cannot read every diff; ODD makes "done" checkable at the merge gate | the GitHub Action as a required check |
| agents run unattended (overnight, background, many at once) | nobody is watching the "done" claims; the gate is the referee and `odd park` gives an honest "blocked" | the Action, plus `odd init` so agents follow the method |
| cheaper or weaker models | on our tasks Haiku got every doable task right without help; where it slipped (claiming "done" on a contradiction) ODD's arm slipped least often, by one run in six | the same |
| a team that must show what was promised and what was proven | each outcome file is a three-line record, kept in the repository | `odd init` |
| teams already on Spec Kit, BMAD or Superpowers | they plan; nothing in them proves the code meets the plan | ODD underneath as the last check |

Where it adds least: a person working closely with a strong model on small changes, reviewing every diff. There the
model is usually right and the person already checks; ODD costs a few cents and seconds for little gain.

## How to say it

> Strong models already get most work right. ODD does not make them smarter. It makes their "done" verifiable: in
> CI, nothing merges without a proof that fails when the change is taken out. It costs about three cents a task, and
> it matters more the less you watch your agents.
