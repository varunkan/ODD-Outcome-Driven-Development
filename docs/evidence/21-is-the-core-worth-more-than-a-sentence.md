# 21. Is odd's core worth more than one sentence?

*Written 2026-11-19: everything above "Results" before the runs, the results after them. One task, three runs an arm, one
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

Six new runs, $1.08, harness at 4481f09 ([runs.json](data/core/runs.json)); `plain` is evidence 19's.

| | plain | plain-tests | odd-lean |
|---|---|---|---|
| hidden tests pass | 1 of 3 | **3 of 3** | **3 of 3** |
| false DONE | 2 of 3 | **0 of 3** | **0 of 3** |
| calculators wrong on a frozen probe | 2 of 3 | 2 of 3 | 1 of 3 |
| cost, three runs | $0.80 | **$0.41** | $0.67 |
| time a run | 85 to 105 s | 47 to 59 s | 60 to 131 s |

**By the rule fixed beforehand: a sentence does as well.** `plain-tests` made no false DONE, so on this task odd's
local benefit is not shown to be more than the sentence "write tests, run them, say DONE only if they pass". odd-lean
also cost 1.63 times `plain-tests`, over the 1.25 allowed.

What this changes: evidence 19's plainest result, 0 false DONE in 9 against a plain agent's 2 of 3, is a result
about asking for tests, not about odd's take-out check. Nothing here shows the take-out check refusing work that
the sentence would have let through; that case did not arise in these six runs.

What was also seen, none of it a pre-registered target:

- **Frozen probes:** 1 of 3 odd-lean calculators differs on a probe (the corrupted exponent again, in one probe),
  2 of 3 `plain-tests` ones (the error after a division by zero, 7 probes; 10 decimal places, 4 probes), 2 of 3
  plain ones. Three runs an arm: a hint in odd's favour and no more.
- **The verdict line:** all three odd-lean reports carry the gate's `VERDICT:` line, word for word. Two wrote it
  unasked, from the method's step 5; in the third the Stop hook blocked once and the report then ended with it.
  Without the step and the hook it was 0 of 6 ([19](19-calculator-head-to-head.md)). Each verdict was
  `DONE, WITH 3 POINTS NOT PROVEN`, which no plain report says.
- **One side effect:** that third report ends with the verdict line and has no `RESULT:` line, so the harness
  recorded no claim for it. The work passes the hidden tests and odd's gate. The method's last line and the
  harness's last line compete for the same place. The method and the hook now ask for the verdict line in the report,
  not at its end, so another tool's closing line can follow it.
- **The shorter method text did not make odd cheaper:** $0.67 for three runs against $0.68 for the `odd` arm with
  the text twice as long. The cost is the work odd asks for, not the reading.
- **Cost of the gate in CI is not in these figures**, and neither is its benefit: nothing an agent writes in a
  session, sentence or method, can be recomputed by someone else unless a tool does it.

## What odd is, after this

For a single agent session on a small task, telling the agent to write and run tests buys the honesty that odd was
credited with, at about 60% of the cost. What odd still does that a sentence cannot: it reruns the proof in CI where
the agent cannot edit the result, it refuses a test that would pass without the change, it refuses a proof tied to
one folder, and it ends every report with a verdict that counts what was not proven. Whether those are worth the
extra cost is not shown by any run so far. It needs tasks where a test passes for the wrong reason, which these
tasks did not produce.
