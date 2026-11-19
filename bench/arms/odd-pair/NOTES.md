# odd-pair

The odd-race arm's flow (one session states the outcome and seals its proof; coding sessions then attempt it) with
two attempts instead of three, and the odd-reach arm's settings: `"cases": "require"` and `"reach": "require"`.

What it adds over odd-reach is a second, independent implementation. When both attempts pass the proof, odd runs each
attempt's entry point on inputs it makes from the proof's examples (backlog 46) and compares them. Attempts that
differ dispute the proof: it goes back to its author once with the differing inputs, and the attempts run again.

Why: the one defect left in the fourth calculator round was a wrong value with exit 0 (10 decimal places for 10
significant digits), which no check of a single attempt judges. Replayed with no model on the fifteen kept
calculators, two clean programs never differ (0 of 120), and each program with a wrong value differs from every
clean one (evidence 19).

## To state with the results

- Calculators wrong on a frozen probe, beside 1 of 3 (odd-reach).
- Whether attempts differed, what the author did with the differing inputs, and whether the second race agreed.
- Cost and time: this arm runs three or more sessions where odd-reach runs one.
- NOT DONE runs: a dispute that is not settled ends the run without a delivery.
