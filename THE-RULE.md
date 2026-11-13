# The rule

> **Nothing counts as done until a check that runs says so: a check that fails without the change, run by someone
> other than the one claiming it.**

Short form: **no proof, no done.**

This is the one value this project has shown, kept here so every later change is held to it. It is written for people
and for agents, with any model, in any repository.

## The four parts

1. **Done is a fact, not a claim.** An agent, a person or a team saying "done" is a statement. Done is a command that
   exits 0 only when the outcome holds.
2. **The proof must fail without the change.** A check that passes with the work taken out proves nothing about the
   work. Take the change out, see the proof fail, put it back, see it pass.
3. **The checker is not the claimer.** The one who did the work does not get to judge it: the check is run again by
   something that trusts nothing the worker recorded (in odd, `gate --recompute` in CI, with the tool and settings
   from the target branch).
4. **Say what is not proven.** "Blocked", "not verified" and "owed on the real system" are honest answers. A forced
   pass is the wrong answer, even when it turns everything green.

## Why it holds

- **Outside checks beat self-review.** Models that correct their own reasoning without outside feedback often get
  worse; repeated attempts help only when a check that runs picks the winner (SWE-bench Lite: 15.9% to 56% solved).
  [Evidence 17](docs/evidence/17-how-frontier-models-reason.md).
- **Judges and rules do not enforce.** AI monitors caught 42-65% of cheating; prompt wording moved cheating on
  repository tasks only from 66% to 54%. [Evidence 17](docs/evidence/17-how-frontier-models-reason.md).
- **It worked here.** odd's own check never passed work that hidden tests rejected (48 runs on a strong model); with
  three cheap attempts and the proof choosing, false "done" was 0 in 48 runs against 2 for one plain session; a cheap
  model first and a stronger one only when the proof says so delivered 41 of 42 tasks with no false "done", at about a
  quarter of the strong model's cost; and when attempts disputed a wrong proof, it went back to its author, after which
  17 of 18 such runs delivered correct work.
  [Evidence 15](docs/evidence/15-comparison.md), [16](docs/evidence/16-new-arms.md).
- **It is cheap.** About one to three cents a task over a plain agent. [Evidence 15](docs/evidence/15-comparison.md).
- **It catches its own mistakes.** Applied to this project, the rule found a defect in odd's gate that refused
  correct work in 34 runs, corrected two figures in our own reports, and stopped a push that would have published
  private details. [Evidence 16](docs/evidence/16-new-arms.md).

## What it does not promise

It does not make a model smarter, and on easy tasks a plain strong agent is already right. It does not show that a
proof covers the whole requirement (a proof can encode a wrong reading of the ticket; held-out proofs and review
narrow that). Gains on large real repositories and with other vendors' models are not measured yet
([BACKLOG](BACKLOG.md) items 18 and 22). The rule makes "done" trustworthy; it does not make every "done" happen.

## How to follow it

With odd: `odd new` (one sentence, a proof command, the files it may touch), `odd done` (passes, fails without the
change, passes again), `odd gate --recompute` as a required CI check. Without odd, by hand: write the check first,
watch it fail, make the change, watch it pass, take the change out and watch it fail again, and let someone else's
machine run it before you merge.

## The rule applied to this project

Every addition to odd states the value it is meant to add and the number that shows it, is built test-first, and is
measured on the comparison harness; an addition whose number does not move is reverted, not kept. Every claim in the
documents links to the evidence for it, and what is not measured is said to be not measured. The tests behind every
claim are listed in [docs/PROOF.md](docs/PROOF.md), generated from the suite and checked by CI.
