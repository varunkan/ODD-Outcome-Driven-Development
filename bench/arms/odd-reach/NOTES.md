# odd-reach

The odd-cases arm with one more setting turned on: `"reach": "require"` (backlog 45). Same prompt (the ticket alone),
same method text in AGENTS.md, same post-check.

With the setting, `odd done` fails until the outcome names `entry:` (the command or .py file a user runs) and
`reject:` (the exit code it ends with on invalid input), or says why one does not apply. odd then runs the entry
point on inputs it makes itself: each example of the proof that is not rejected, followed by an ending the proof's
own examples show rejected. Each must be rejected, and none may crash. The failure's own text says how; the agent is
told nothing else.

Why: with edge cases required, all three calculators still reported division by zero for `1/0+`, which the ticket
calls an invalid expression (evidence 19, third round). Replayed on the nine kept calculators with no model, this
check fails the four that have that defect and none of the five that do not.

## To state with the results

- Whether each calculator has a defect of its own on the frozen probes, beside 3 of 3 (odd) and 3 of 3 (odd-cases).
- Whether the check went red and then green in each run, or was answered with `none - <why>`.
- Cost and time beside the odd-cases arm's ($0.82 for three runs).
