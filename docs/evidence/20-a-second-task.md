# 20. A second task: plain agent, odd, and odd with its newer checks

*Written 2026-11-19: everything above "Results" before the runs, the results after them. One small task, three runs an arm,
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

Nine runs, $2.51, harness at d6a7721 ([runs.json](data/duration/runs.json)).

| | plain | odd | odd-claim |
|---|---|---|---|
| hidden tests pass | 3 of 3 | 3 of 3 | 3 of 3 |
| false DONE | 0 | 0 | 0 |
| programs that differ on a frozen probe | **3 of 3** | **3 of 3** | **3 of 3** |
| cost, three runs | $0.56 | $0.75 | $1.20 |
| time a run | 57 to 107 s | 75 to 144 s | 122 to 238 s |

### 1. Is odd better than a plain agent here? Not shown

Every one of the nine programs is wrong on the same two or three probes, and on nothing else: a trailing newline is
accepted (`"1h\n"`, all nine), a tab between parts is accepted (four), a digit outside ASCII is accepted (eight; this
one is arguable, since the ticket says "digits" and does not say which). They come from how Python is usually
written (`strip()`, `\s`, `isdigit()`), every session wrote it that way, and none of odd's checks makes an input
no test file mentions. odd cost a third more than plain for the same result, and odd with its newer checks twice
as much.

This is the limit the research loop named in advance ([19](19-calculator-head-to-head.md)): a mistake every attempt
shares is seen by no check that compares attempts or grows inputs from the proof's own examples.

### 2. Does `reject:` hold on a second kind of program? No

The check failed all three `odd-claim` runs, and every input it named is handled correctly:

| run | it flagged | by the reference | what the session did |
|---|---|---|---|
| 1 | `1000d1h` exits 1 | right: valid, and too long | wrote `entry: none`, `reject: none` |
| 2 | `1000d1h` exits 1 | right | wrote `reject: none` |
| 3 | `1d2h`, `1w2h` exit 0 | right: valid | parked the outcome, and still ended `RESULT: DONE` |

The rule behind the check is "an ending rejected after one example is rejected after every other". `1h2h` is
rejected because a unit repeats; `2h` after `1d` repeats nothing. Replayed with no model on every kept program of
both tasks, tests of each run against programs of each run ([replay3.py](data/duration/replay3.py),
[replay3.json](data/duration/replay3.json)):

| rule | calculator: true alarms, false alarms (225 pairs) | duration: true, false (81 pairs) |
|---|---|---|
| as built (one pair of examples shows the ending) | 74, **0** | 0, **81** |
| an ending needs two pairs of examples | 5, 0 | 0, 0 (nothing is generated) |

No variant is both sound and useful: the rule is true of arithmetic expressions and false of a list of units in
order. **The check was changed because of this.** It still fails on an input that is not rejected, but the failure
now lists one input for each ending and names a way out, the outcome line `valid: <input> ;; <input>`; an ending so
declared is left out, and `odd claim` lists what was declared valid, so a reviewer sees it. An unsound inference can
no longer trap correct work, and a wrong declaration is visible. Not yet measured with a model.

### 3. Do reports carry the claim with the report check on? Partly: 2 of 3

In runs 1 and 2 the Stop hook blocked the first report once, and the final report then ends with the claim: the
verdict line and all five not-proven points (0 of 6 without the check, [19](19-calculator-head-to-head.md)). In run
3 the hook's message does not appear in the transcript, and the report says DONE about an outcome the session had
parked; why the hook did not fire there is not established.

### What this task says

- On a task a plain agent already delivers, odd added cost and no correctness.
- A check tuned on one program kind did harm on the next. It was measured as "0 false alarms" on the calculator, and
  the pages said then that this was one task; this is what that caveat was for.
- The one check here that is independent of the task, the report carrying the claim, worked where it ran.
