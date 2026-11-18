# 19. A calculator, built with odd and with Spec Kit

*Written 2026-11-18. One small task, three runs per framework, one model: a hint, not a rate. The owner asked for a
head-to-head on a calculator with Haiku 4.5 and an LLM judge to decide. Data: [data/calculator/](data/calculator/).*

## Answer

**Two rulings, and they differ.** Left alone, odd won on delivery and cost. With a person saying "continue" to Spec Kit,
a second blind judge chose Spec Kit, narrowly, for the better software, and odd for cost and for finishing unaided
([the second round](#second-round-spec-kit-told-to-continue)).

**First round, nobody answering: the judge chose odd.** It did not know which framework was which (they were labelled A and B, with each
framework's own folders removed from the code).

| | odd | Spec Kit |
|---|---|---|
| working calculators (hidden tests all pass) | **3 of 3** | 1 of 3 |
| false DONE | 0 | 0 |
| cost, all three runs | **$0.68** ($0.16 to $0.30 a run) | $1.42 ($0.12, $0.15 and $1.14) |
| time a run | 76 s, 89 s, 574 s | 60 s, 66 s (no code), 394 s (the one that delivered) |

What this supports: on this calculator task with Haiku 4.5, odd delivered in every run and Spec Kit in one of three,
and odd's cost for each working calculator was about a fifth of Spec Kit's ($0.23 against $1.14 for its one delivery;
$1.42 counting the two runs that delivered nothing). It does not support a general ranking: one task, three runs,
one model.

## The task

One ticket, the same for both ([ticket.md](data/calculator/ticket.md)): `python3 calc.py "<expression>"` with
`+ - * /`, precedence, parentheses, repeated unary signs, exact output formatting, three kinds of error with fixed
messages and exit codes, no `eval` or `exec`, and its own unit tests. Graded by hidden tests neither framework saw
([hidden_tests.py](data/calculator/hidden_tests.py)): 25 expressions, 3 divisions by zero, 15 invalid inputs, the
usage message, the no-eval rule, and that the project's own tests pass. The hidden tests fail on the empty project
and pass on a reference solution written to check them.

Both arms are the harness's own (`bench/arms/odd`, `bench/arms/speckit`: Spec Kit 1.4.0 with its documented
six-step process named in the prompt), run with `--model claude-haiku-4-5 --max-turns 150 --timeout 1800`, harness
at commit c17e961; every session was served by `claude-haiku-4-5`. Nobody answered questions.

## The six runs as first left, side by side

Each image shows the same commands run in what the run left behind; the output is real.

![Run 1: odd passes the hidden tests; Spec Kit stopped after its specification and left no calc.py](img/calculator-run1.png)

![Run 2: both pass the hidden tests; odd cost $0.221 in 89 s, Spec Kit $1.144 in 394 s](img/calculator-run2.png)

![Run 3: odd passes the hidden tests; Spec Kit stopped after its specification and left no calc.py](img/calculator-run3.png)

## Why the first judge chose odd

The ruling in full: [judge-ruling.md](data/calculator/judge-ruling.md). Its reasons, in the order it weighed them:

1. **Delivery.** odd left a working calculator in 3 of 3 runs. Two of Spec Kit's three runs ended after writing the
   specification ("Next Step: Run `/speckit-plan`"), with no code and no claim, although the prompt told it to carry
   on through every step. Both failures were the same failure, which points to a cause rather than chance.
2. **Honesty: a tie.** Neither framework claimed DONE falsely. Spec Kit's two non-deliveries made no claim at all.
3. **Quality of what was left.** Spec Kit's one delivery was on a par with odd's and had the widest tests (82, split
   by behaviour, against 36 to 45) and the cleanest structure (a separate evaluator). odd's third calculator was the
   weakest delivered: `.` alone prints `0`, and `1/0+` reports division by zero where the ticket says invalid
   expression; the hidden tests cover neither. All four delivered calculators share gaps the ticket's examples do
   not reach (very small results print in scientific notation).
4. **Cost and time.** odd spent $0.68 for three calculators; Spec Kit $1.42 for one.

The judge's own confidence: high on the direction, moderate on the size of the gap.

## Second round: Spec Kit told to continue

The owner asked for the two stopped Spec Kit runs to be told to continue, and for the finished software to be judged
again. The harness does not keep sessions, so "continue" was a new session in the same folder (the specification the
run wrote still there), with the same prompt, model and limits, and one more paragraph: carry on from where the files
show you stopped. One "continue" was enough for each; both then claimed DONE and pass the hidden tests
([speckit-continue.json](data/calculator/speckit-continue.json)).

| | odd | Spec Kit, two runs continued once |
|---|---|---|
| hidden tests pass | 3 of 3 | 3 of 3 |
| calculators with a defect of their own, on the judge's 95 further probes | **3 of 3** | **0 of 3** |
| needed a person | 0 runs | 2 runs |
| cost, all three runs | $0.68 | $2.65 ($0.79, $1.14, $0.71) |
| time a run | 76 s, 89 s, 574 s | 336 s, 394 s, 296 s |

A fresh judge, again blind to which framework was which, ruled **Spec Kit the winner, narrowly, on the software**,
and odd clearly ahead on what it took ([judge-ruling-after-continue.md](data/calculator/judge-ruling-after-continue.md)):

- **Correctness.** The hidden tests tie. On the judge's own probes every odd calculator had a defect no Spec Kit
  calculator had. odd runs 1 and 2 print a wrong number for non-whole results of 1e10 and more: `12345678901.5`
  prints `1.23456789e+1` (the zero-stripping eats the exponent). odd run 3 prints `0` for a lone `.` and reports
  division by zero for `1/0+`, which the ticket calls an invalid expression. Checked again on each run's own files:
  all confirmed, and all three Spec Kit calculators answer these correctly.
- **Honesty.** A tie: all six claims are true by the hidden tests.
- **What it took.** odd was 3 to 5 times cheaper and never needed a person. The judge gave one "continue" moderate
  weight, and said that with cost and autonomy weighted equal to correctness, odd would win.
- **Its confidence:** low to moderate. Three against none is suggestive, not significant, and the defects sit in
  rarely used inputs.

What this says about odd: its proofs, and the hidden tests, passed three calculators that were wrong on inputs
nobody tested. That is the limit evidence 18 found on real code, seen again on a small task: a proof reaches as far
as the cases it holds. Spec Kit's longer process cost about four times as much and, on this task, left more careful
code.

## Third round: odd with edge cases required

The second ruling turned on defects in inputs nobody tested, and Spec Kit's runs had written requirements with an
edge-case section first. odd got that as a setting, `"cases": "require"` (backlog 44), and the task was run three
more times (arm `odd-cases`, same ticket, model and limits; target fixed before the run: no calculator with a defect
of its own, at a cost under Spec Kit's).

| | odd | odd, edge cases required | Spec Kit, continued |
|---|---|---|---|
| hidden tests pass | 3 of 3 | 3 of 3 | 3 of 3 |
| calculators with a defect of their own | 3 of 3 | **3 of 3** | 0 of 3 |
| needed a person | 0 | 0 | 2 runs |
| cost, three runs | $0.68 | $0.82 ($0.21, $0.23, $0.38) | $2.65 |
| time a run | 76 s, 89 s, 574 s | 86 s, 99 s, 147 s | 336 s, 394 s, 296 s |

**The target was not met.** The runs wrote 8 to 11 requirements and 33 to 36 edge cases each, and the two defects of
the first round did not come back (the corrupted exponent, the lone `.`). But all three calculators report division
by zero for `1/0+`, which the ticket calls an invalid expression, and two of them for `(1/0` and `1/0)` as well.
Each test file had `2+` rejected and `1/0` as a division by zero; none had the two together. The author of the
cases is the author of the code, so the case nobody thought of is still missing. The harness recorded odd's own
gate as failing after run 3; run again on the kept files it passes, and that difference is not explained.

### How a defect is counted from here on

The judges' probes were not kept, so the count could not be repeated. It is now a file:
[probes.py](data/calculator/probes.py) holds 143 expressions, and [probes.json](data/calculator/probes.json) the
expected exit code and output of the 142 on which four programs written apart agree (a reference using exact
fractions, and the three Spec Kit calculators). The one left out is listed in the file. Where the ticket does not fix
the notation (a result of 1e10 or more that is not whole), the output is read as a number. Counted this way the nine
kept calculators give what the judges found: odd 1, 1 and 8 probes wrong; Spec Kit 0, 0, 0; odd with edge cases 7,
2 and 7, all of them an error after a division by zero.

### A check for it, replayed with no model

odd now has a check where the tool makes the inputs: an outcome declares `reject: <exit code>` beside its entry
point, and odd runs the entry point on each example of the proof that is not rejected, followed by each ending the
proof's own examples show rejected (backlog 45, [DESIGN 3o](../../DESIGN.md)). It came out of a research loop on
this evidence: three sets of hypotheses (the literature, odd's own evidence, other fields), 19 in all, ranked by
measuring each on copies of the kept calculators. The checks where the agent writes the oracle lost to their
tool-owned neighbours, and two candidates were dropped because they fired as often on the correct calculators.

Replayed on the nine kept calculators, every test file against every program
([replay.py](data/calculator/replay.py), [replay.json](data/calculator/replay.json)):

| | pairs failed by the check |
|---|---|
| the 4 calculators with the defect (odd 3; edge cases 1, 2, 3) | 35 of 36 |
| the 5 without it (odd 1, 2; Spec Kit 1, 2, 3) | 0 of 45 |

With its own tests, each of the four fails and each of the five passes. The check does not see the corrupted
exponent of odd runs 1 and 2: that is a wrong value with exit 0, and the check judges exit codes only.

This is a replay on finished programs, not a run. It shows the check tells these defective calculators from the
correct ones; it does not show an agent, told nothing, will declare `reject:` and fix what the check finds.

### Fourth round, fixed before it is run

Arm `odd-reach`: the `odd-cases` arm plus `"reach": "require"`, which makes `odd done` fail until the outcome names
its entry point and its reject code, or says why not. Three runs, same ticket, model and limits. Shown only if all
of these hold; one calculator with a defect counts as partly; anything else as not shown:

- 0 of 3 calculators differ on any frozen probe;
- 3 of 3 pass the hidden tests, no false DONE, nobody answers anything;
- the three runs cost at most $1.36 (twice the first round);
- in at least 2 of 3 runs the outcome declares `reject:` with an exit code, not `none`.

## What to keep in mind

- **Three runs each, one task, one model.** 3 of 3 against 1 of 3 is not statistically significant.
- **One odd run was flagged** by the harness's contamination rule: a process listing in its transcript showed the
  harness's own launch command. No solution was reachable from it, and the judge's ruling is the same with that run
  left out (2 of 2 against 1 of 3).
- **Spec Kit's stops may be a property of this pairing**, a step-by-step process with a small model and nobody to say
  "continue", rather than of Spec Kit with a stronger model or a person present. The earlier comparison ([15](15-comparison.md)) measured Spec Kit at
  2 to 5 times a plain agent's cost.
- **odd's own check is not what made the difference here**: nothing claimed done falsely in either arm. The
  difference was that one process finished and the other stopped.
- The first round cost $2.10, the two continued Spec Kit runs $1.22 and the edge-case rerun $0.82.
