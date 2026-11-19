# odd-lean

odd's defaults after the ruling of 2026-11-19 ([data](../../../docs/evidence/data/lean-ruling.md)), with its Claude
Code hooks installed. Same prompt as the `odd` arm: the ticket alone; the method reaches the session through
AGENTS.md.

What is on: the take-out check, the folder check, proof strength as a report, and the Stop hook, which blocks once
a report that does not end with the gate's verdict line. What is off: requirements and coverage, edge cases, the
reject rule as a failing check, races, a second attempt, the claim's points in the report.

## To state with the results

- False DONE and hidden tests beside `plain` and `plain-tests`.
- Whether the Stop hook fired, and whether the final report then carries the gate's verdict.
- Cost beside `plain-tests`: the method text is about 1,200 characters where it was about 2,600.
