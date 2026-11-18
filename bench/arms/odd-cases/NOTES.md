# odd-cases

The odd arm with one setting turned on: `"cases": "require"` (backlog 44). Same prompt (the ticket alone), same
method text in AGENTS.md, same post-check.

With the setting, `odd new` refuses until the ticket's requirements are written in `.odd/requirements/<ticket>.md`,
each with at least one edge case (`R1.1: <a boundary input and what must happen>`), and the gate fails until every
case is named in a test of the change. The refusal's own text says how; the agent is told nothing else.

Why: on the calculator task every odd calculator passed its own proof and the hidden tests and was still wrong on
inputs nobody tested, while Spec Kit's runs, which wrote 14 to 18 requirements and an edge-case section before any
code, had no such defect (evidence 19).

## To state with the results

- Whether the judge's further probes find a defect in each calculator, beside the odd arm's 3 of 3.
- Cost and time beside the odd arm's and Spec Kit's: writing requirements and cases is extra work.
- How many requirements and cases each run wrote, and whether a case named in a test is really tested there.
