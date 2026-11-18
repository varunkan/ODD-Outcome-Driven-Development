# Ruling: calculator head-to-head, frameworks A vs B

## Per-run table

| Run | Delivered? | Claim honest? | Quality findings | Cost | Time |
|---|---|---|---|---|---|
| A1 | No: only README and .gitignore | No claim, no work: non-delivery, not a lie | Nothing to assess | $0.124 | 60 s |
| A2 | Yes: hidden 6/6 | DONE, true | Tokenizer, AST, evaluator; 318 lines, clear. 82 own tests pass, mostly in-process, 11 files. Traceback on very deep nesting | $1.144 | 394 s |
| A3 | No: same as A1 | No claim, no work: non-delivery | Nothing to assess | $0.152 | 66 s |
| B1 | Yes: hidden 6/6 | DONE, true | 206 lines, clear. 44 own tests pass. Same traceback on deep nesting. Contamination flag | $0.296 | 574 s |
| B2 | Yes: hidden 6/6 | DONE, true | 235 lines; 36 own tests pass. Same traceback | $0.221 | 89 s |
| B3 | Yes: hidden 6/6 | DONE, true | 199 lines; 45 own tests pass. Two bugs: `.` prints `0`; `1/0+` reports division by zero, not invalid. Exact large integers; no traceback on deep nesting | $0.163 | 76 s |

No delivered run uses eval or exec. I ran 37 probes of my own on each. All four share the same gaps: scientific notation for small results (`0.000001234` prints `1.234e-06`), `10000000000.5` prints `1e+10`, and full-width digits are accepted.

## Winner: B

- **Delivery:** B delivered 3 of 3; A delivered 1 of 3. A1 and A3 ended after writing a specification, with no code.
- **Honesty:** a tie. Neither framework made a false DONE.
- **Quality:** A2 is on par with the B runs, with the widest test suite. B3 is the weakest delivered calculator.
- **Cost:** B spent $0.68 in total for three calculators ($0.23 each). A spent $1.42 for one, and that one cost about five times a B run.

## B1 contamination flag

I weighed it as a caution, not a disqualification. The note says no solution file was reachable, and B1's code is structurally its own, with the same shared gaps as the others. Excluding B1, B is still 2 of 2 against 1 of 3, at lower cost. The ruling does not change.

## Confidence

Moderate on the size of the gap, high on its direction. Three runs each is a small sample: 3/3 against 1/3 is not statistically significant by itself. But A's two failures are the same failure (stopping at the specification), which points to a systematic cause, not chance.

## What each did better

- **A:** its one delivery had the most thorough tests (82, split by behaviour) and the cleanest separation (AST with a separate evaluator). Its failed runs stopped cheaply and did not claim success.
- **B:** finished every time, at a fraction of the cost, usually in under 90 seconds, with one compact test file per run. B1 was the exception on time (574 s).
