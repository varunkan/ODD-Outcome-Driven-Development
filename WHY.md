# Why outcome-driven development: the evidence so far

**Verdict, 2026-11-11: build it, but lean (confidence 0.72).** All 1,856 instructions were ruled on, the result was
compared with Spec Kit, BMAD, Superpowers and Claude Code alone, and three independent critics each returned "adds
value, conditionally". The evidence and every ruling are under [`docs/evidence/`](docs/evidence/README.md).

## The verdict

**What the rulings were.** The 1,856 instructions reduce to 224 distinct rules: 93 kept, 52 kept after rewriting, 48
merged as duplicates and 31 dropped. A skeptic pass overturned 78 first rulings. The survivors compose into 18
principles ([08](docs/evidence/08-refined-method.md)), of which about seven are worth teaching.

**Why build anything.** Three things are absent from the other frameworks and from Claude Code used alone, and each
has evidence behind it:

- The few rules with no exceptions are enforced in code. Written rules failed, measured: across 294 agents every
  broken rule was already written down. Outside research agrees that telling a model not to cheat changed nothing,
  while structural controls did.
- "Done" is a script's exit code on the content, with the proof kept out of the implementer's reach. In the other
  frameworks, done is the model's claim or a ticked checklist.
- An honest "cannot be done as specified" exit, which cut cheating from 54% to 9% in one benchmark.

These matter more as models improve, because a stronger agent produces more unreviewed change per hour.

**Why only a small core.** The two largest recorded wastes in the source project were its own rules (the multi-agent
swarm and the step cap). About half of the 18 principles restate the other frameworks or the vendor's guidance. Plain
Claude Code was the cheapest and fastest arm in the only controlled benchmark found, and equal on small tickets.

**What would overturn the decision.** If the core cannot be made tamper-resistant, or if running the same tasks with
and without it shows no gain in escaped defects or rework at an acceptable cost.

**What is not claimed.** No multiplier and no win over any other framework: no same-task comparison exists. The
evidence is one project, measured by itself, mostly single instances, and its central product outcome was never
observed end to end on a real system.

**The seven things worth learning.**

1. Start from one user-visible outcome sentence and one end-to-end proof. Everything else is the next outcome.
2. If a command can answer the question, write the command. Use agents for judgement.
3. A proof counts only after it failed before the change, and fails again when the change is broken.
4. The implementer cannot edit the proof, the gate or the done record. Only a script writes done, on a content hash.
5. Simulated checks may gate a merge. Only a run on the real system proves the outcome.
6. Enforce the few no-exception rules in code, keep the rest as plain prose, and delete rules that never changed a
   decision.
7. Name once the acts only the owner performs, and decide everything else from the goal and the evidence.

## The claim being tested

Before any work, write the outcome: one sentence saying who observes what result, measurably, and the command that
proves it. Work is done only when that proof passes. The few rules that must always hold are enforced by scripts and
hooks, not by prose. A change to the process ships with its before-and-after number or is reverted.

The method came from building a production, multi-device restaurant point-of-sale system with Claude Code between
August and November 2026, under 68 standing directives and 1,856 distinct instructions.

## What supports it

**1. Delivery improved as the method matured** ([01](docs/evidence/01-method-measured.md), measured from git by script).

| | With CLAUDE.md, before the directives | Outcome-first period (from 7 October) |
|---|---|---|
| Lines changed in process files per line of product code | 9.9 | 2.4 |
| Share of commits that changed product code | 15% | 33% |
| First commit to merge, slowest 10% of product branches | 133 hours | 12 hours |
| Reverts per week | 2.7 | 1.0 |

Testing grew about tenfold: 0.09 test lines per product line before, 2 to 7 after; 121 test files became 1,307.
These series are observational: periods overlap, and model versions changed during them.

**2. The parts with a recorded before and after changed the shape of the work**
([02](docs/evidence/02-pos-evidence-ledger.md)).

- One branch for all instances of an invariant, with review depth set by risk: 17 times cheaper on the one measured
  instance.
- A script instead of agents for mechanical work: about 4 minutes and the answer, against 106 agents killed with none.
- Outcome-first: about 2 hours to an end-to-end proof on a host, where a full multi-agent swarm had run 14 hours.
- A size budget on always-loaded instructions: CLAUDE.md cut by about 69% and held there.
- Device checks written as tests: about 11 times cheaper per check, on the 13 of 57 that could be converted.

Most of these are single instances measured by the session that made the change.

**3. Outside research points the same way** ([05](docs/evidence/05-practice-and-model-trends.md)).

- Deterministic enforcement (hooks, deny rules) is the model vendor's own stated design for rules with no exceptions.
- Mutation score correlates with real fault detection independently of coverage (357 real faults studied).
- Coding agents game proofs: reward hacking measured at 30% on one benchmark and 50 to 76% on another. Giving the agent
  an honest "cannot be done as specified" exit cut cheating from 54% to 9%.
- What stays valuable as models improve is what the model cannot supply itself: the outcome, external ground truth,
  enforcement of no-exception rules, and decisions that belong to a person.

**4. The existing frameworks leave this gap open** ([04](docs/evidence/04-spec-kit-bmad-superpowers.md)).

- Spec Kit, BMAD and Superpowers enforce their process through prompt text and human review. None was found to block
  an agent from declaring work done without a passing proof.
- None publishes first-party measurements of its own effect.
- Specification-heavy process has measured costs: one practitioner recorded 33.5 minutes of agent time, 2,577 lines of
  markdown and 3.5 hours of review for 689 lines of code, against about 8 minutes and 24 minutes without it. One
  controlled benchmark put BMAD at 74% more cost per merged ticket than no process. A study of 88,052 pull requests
  found no defect benefit from specs (it measured ticket references, not these tools' output).

## What counts against it

The same evidence is plain about where the method, as practised, cost more than it returned.

- **Process outgrew the product.** 43.1 MB of process markdown against 7.7 MB of product code; 382 governance
  script files; 68 directives in under three months. In the heaviest week, 579 of 746 commits changed only process files.
- **Most instructions were never measured.** Of 1,856, 102 (5.5%) have a recorded before and after; 939 (50.6%) were
  mandated and never measured; 20 were proven to fail and reverted ([03](docs/evidence/03-instruction-catalog.md)).
- **Written rules did not hold until something enforced them.** Four directives record that they restate an
  instruction that was not being followed; one calls itself the fourth telling.
- **The full multi-agent swarm was waste.** 14 hours, 81 agents and 23 revisions in 30 verdicts on one requirement,
  most naming no product defect. It was withdrawn the next day.
- **A frugality rule produced waste.** A counting bug in the step cap cut agents at about half their allowance for
  four weeks; the capped worker agents became 82% of one 446-million-token run.
- **Judging everything did not deliver.** 733 recorded rulings in 44 days, 278 of them on one requirement.
- **The central outcome is unproven on a real system.** The one recorded real-system run failed on a refusal that no
  simulation produced. Total token spend and escaped defects were never tracked.
- **The first toolkit built from these rules repeated the mistake** ([06](docs/evidence/06-first-draft-audit.md)):
  about 2,950 lines of which about 400 were judged essential, with real defects: a plain commit made every proof
  stale, the proof ledger could be forged, and file writes through shell commands bypassed the guard.

## What follows

The tool in this repository is the lean version the decision called for, after a design review cut it further
([DESIGN.md](DESIGN.md), [the review](docs/evidence/10-design-review.md)): a three-line outcome file (outcome, proof
command, boundary); a check that the proof passes, fails with the change taken out, and passes again; one gate that
CI recomputes from the repository; and one honest exit for work that is blocked or cannot be done as specified.
Research, review and unattended running are left to the agent and its harness.

Published results will come only from the comparison harness in [`bench/`](bench/SPEC.md): the same tasks, with
hidden acceptance tests, run through plain Claude Code, this tool, Spec Kit, BMAD and Superpowers. Until it has run,
nothing here is a measured advantage.
