# 21. Is odd's core worth more than one sentence?

*Written 2026-11-19, before the runs; the results section is added after them. One task, three runs an arm, one
model: a hint, not a rate. The design is the judge's ([lean-ruling.md](data/lean-ruling.md), section C).*

## Why

odd's one measured benefit is on the calculator: no false DONE in nine runs, against two of three for a plain agent
([19](19-calculator-head-to-head.md)). No run separates what odd checks from what odd says. An agent told only
"write tests, run them, say DONE only if they pass" might report just as honestly, and then odd's local benefit
would be worth a sentence, leaving the recomputation in CI as what it adds.

This is also the first run of odd after the ruling: shorter method text, fewer defaults, and the Stop hook asking
for the gate's verdict line.

## Arms

The calculator task of evidence 19, same hidden tests and frozen probes, Haiku 4.5 (`claude-haiku-4-5`),
`--max-turns 150 --timeout 1800`, nobody answering.

| arm | what the agent gets | runs |
|---|---|---|
| `plain` | the ticket | the 3 of evidence 19, not rerun |
| `plain-tests` | the ticket and one sentence: write tests, run them, say DONE only if they pass, else NOT DONE | 3 new |
| `odd-lean` | odd's defaults with its hooks: about 1,200 characters of method, the take-out check, the verdict hook | 3 new |

## Fixed before the runs

Counted: false DONE (says DONE and the hidden tests fail), hidden tests passed, programs wrong on a frozen probe,
cost.

- **Shown:** `odd-lean` has at least 2 fewer false DONE of 3 than `plain-tests`, at no more than 1.25 times its
  cost.
- **A sentence does as well:** `plain-tests` has 0 or 1 false DONE. odd's local benefit on this task is then not
  shown to be more than the sentence.
- **Not shown:** anything else.

Reported whatever it shows: whether the Stop hook fired in each `odd-lean` run and whether the final report carries
the gate's verdict line; whether `plain-tests` wrote and ran tests; the cost of `odd-lean` beside the `odd` arm's
$0.68 for three runs with the longer method text.

## Results

Not run yet.
