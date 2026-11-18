# odd-ask

odd-cascade with one step before it, measured here before it is built into odd: **ask before proving**.

1. A cheap session, in its own clone of `main`, reads the ticket, the code and the existing tests, and names what the
   ticket leaves open. A gap counts only when it names one concrete input and two different results that are both
   consistent with the ticket (`odd-ask: <input> | <result> | <other result>`); at most 2.
2. With a gap, the arm ends with the questions and `RESULT: NOT DONE`: an honest question instead of a guess that a
   proof would then seal. No code is written.
3. Without one, the arm runs exactly as odd-cascade.

Why: every false DONE odd let through on real issues was work that fitted one reading of a ticket whose hidden tests
followed another (evidence 18), and a second cheap reader mostly read the ticket the same way (odd-dual: 3 false DONE
of 6). The gaps could be stated as questions before any code.

## To state with the results

- An ask is not a delivery: report passes beside odd-cascade's, and how many runs that pass without it were turned
  into questions (the cost of asking too often).
- Whether each question names the gap the hidden tests turn on is rated by a judge who sees only the ticket, the
  question and the failing assertion.
- The asking session is one more cheap session, counted in the arm's cost.
