# odd-second

The odd-reach arm (one session, edge cases and reach required), followed by `odd second` (backlog 48):

1. One session does the whole request, as in the odd arm. If it does not say DONE, its message is the arm's.
2. For each outcome that names an entry point: `odd second <slug>`. One more session writes the product again in
   its own copy, from the base with the outcome and its tests, without seeing the first one's code. odd runs both on
   inputs it makes from the tests' examples.
3. If they differ, one settling session in the project gets the differing inputs and is told to decide each from
   the request, add it to the tests, fix the program, and run `odd done` and `odd gate` again. Its message is the
   arm's. If the second attempt is not verified, nothing is compared and the first session's message stands.

Why not odd-pair: that arm seals the proof first and then races two attempts, and delivered 0 of 3 calculators (a
wrong sealed test, attempts that wrote outside their files, a first session that ended without a result line); the
comparison never ran. Here the flow that delivered 3 of 3 is kept and the second attempt is added after it.

## To state with the results

- Calculators wrong on a frozen probe, beside 1 of 3 (odd-reach).
- In each run: was the second attempt verified, did the two differ, on what, and what the settling session did.
- Cost and time: two or three sessions for odd-reach's one.
