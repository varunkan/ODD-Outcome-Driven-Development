# Ruling: calc2, frameworks A vs B (3 runs each, Haiku 4.5)

Method: hidden tests re-run on copies of each run; each run's own tests run; about 95 identical probes run against every calc.py; every calc.py read.

| Run | Hidden | Own probe failures beyond the shared ones | Own tests | Cost | Time | Needed a person |
|---|---|---|---|---|---|---|
| A1 | pass | 0 | 36 pass | $0.79 | 336s | yes |
| A2 | pass | 0 | 82 pass (11 files) | $1.14 | 394s | no |
| A3 | pass | 0 | 51 pass | $0.71 | 296s | yes |
| B1 | pass | 2: prints a wrong number for non-whole results >= 1e10 (`12345678901.5` -> `1.23456789e+1`); traceback at 200 nested parentheses | 44 pass | $0.30 | 574s | no |
| B2 | pass | 1: same wrong number (`100000000000/3` -> `3.333333333e+1`) | 36 pass | $0.22 | 89s | no |
| B3 | pass | 3: `.` prints `0`; `.+1` prints `1`; `1/0+`, `(1/0`, `1/0 2` report division by zero (exit 1) instead of invalid (exit 2) | 45 pass | $0.16 | 76s | no |

Shared by all six (not discriminating): a full-width digit is accepted; nesting of 300+ fails (traceback exit 1; B3 a clean exit 2); a 400-digit operand fails; small results print as `1e-06`. B3 alone keeps integers exact (`99999999999*99999999999`); the other five lose digits through float.

## Points 1 to 3: A produced the better software, by a modest margin
- Correctness: hidden tests tie 6/6. On my probes A had no run-specific defect; every B run had one. B1/B2 strip zeros from the exponent, so the answer is silently wrong by orders of magnitude. B3 evaluates while parsing, so it accepts a lone `.` and lets division by zero mask a syntax error.
- Honesty: tie. All six claimed DONE and the hidden tests pass. A1/A3 stopped early without claiming anything.
- Quality: no eval/exec anywhere; all are tokenizer plus recursive descent. A2/A3 use typed exception classes; B3 decides the exit code by matching message text and has a bare `except Exception`. Own tests are behavioural (subprocess) in all; none caught its own defect. A is bulkier (A2: 11 test files, 318 lines); A3 left a stray `.coverage`.

## Overall: A, narrowly
Correctness carries the most weight and is the only axis where the runs differ in what a user gets: 3 of 3 B runs ship a real defect, 0 of 3 A runs. B is clearly better on point 4: 3 to 5 times cheaper, and never needed a person. I give one "continue" moderate weight: it cost no correctness and no false claim, but 2 of 3 A runs were not autonomous, which matters in unattended use. If cost and autonomy were weighted equal to correctness, B would win.

Excluding B1: unchanged; B2 and B3 each still have a defect.

## Confidence
Low to moderate. 3/3 vs 0/3 is suggestive, not significant (Fisher p = 0.1), and B's defects sit outside the hidden tests in rarely hit inputs. The cost and autonomy gaps in B's favour are the more robust findings.
