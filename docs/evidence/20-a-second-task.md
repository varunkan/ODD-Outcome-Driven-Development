# 20. A second task: plain agent, odd, and odd with its newer checks

*Written 2026-11-19, before the runs; the results section is added after them. One small task, three runs an arm,
one model: a hint, not a rate. Data: [data/duration/](data/duration/).*

## Why

Everything about odd's newer checks was measured on one calculator ([19](19-calculator-head-to-head.md)), and the
input generator was adjusted while looking at those programs. The calculator comparison also had no plain agent in
it. This task is a different kind of program, written after the checks were, with a plain arm.

## The task

One ticket ([ticket.md](data/duration/ticket.md)): `python3 dur.py "<duration>"` normalises a duration such as
`1h30m` or `90s`: five units in a fixed order, each at most once; output in days, hours, minutes and seconds; over
365 days is `error: too long` (exit 1); an invalid duration is exit 2, with eight listed ways of being invalid.

- **Hidden tests** ([hidden_tests.py](data/duration/hidden_tests.py)): 20 values, 4 too long, 15 invalid, the usage
  message, and the project's own tests pass.
- **Frozen probes** ([probes.py](data/duration/probes.py), [probes.json](data/duration/probes.json)): 151 inputs.
  The expectation of each is what two programs written apart agree on: a reference written for the probes, and a
  second one written by a separate session from the ticket's text alone
  ([second_reference.py](data/duration/second_reference.py)). They agree on all 151, and the second one passes the
  hidden tests. A program is counted as defective when it differs on any probe.

## Arms

Three runs each on Haiku 4.5 (`claude-haiku-4-5`), `--max-turns 150 --timeout 1800`, nobody answering.

| arm | what the agent gets |
|---|---|
| `plain` | the ticket and nothing else |
| `odd` | odd as `odd init` leaves it |
| `odd-claim` | odd with edge cases required, entry point and reject code required, and the report check (backlog 44, 45, 47) |

## Fixed before the runs

1. **Is odd better than a plain agent here?** Counted: programs that differ on any frozen probe, and false DONE
   (says DONE, hidden tests fail).
   - *Shown*: `odd-claim` has at least 2 fewer defective programs of 3 than `plain`, and no more false DONE.
   - *Not tested*: `plain` has no defective program and no false DONE (the task did not make a plain agent fail).
   - *Not shown*: anything else. `odd` against `plain` is reported the same way.
2. **Does `reject:` hold on a second kind of program?** For every time the check fails a run, the input it names is
   looked up against the reference. *Safe* if every such input really is handled wrongly; each one that is not is a
   false alarm and is listed.
3. **Do reports carry the claim with the report check on?** Counted as in evidence 19: the final report holds the
   claim's verdict line and every not-proven point. *Shown* at 3 of 3, *partly* at 2 (it was 0 of 6 without the
   check).
4. Cost and time for each arm are reported; no target.

## Results

Not run yet.
