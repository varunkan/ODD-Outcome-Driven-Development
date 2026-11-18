# odd-dual

odd-cascade with one addition, measured here before it is built into odd: a **blind second proof**.

1. As odd-cascade: one cheap session states the outcome and seals its proof.
2. A second cheap session, in its own clone of `main` beside the project, writes one test (`test_blind_proof.py`) from
   the ticket alone. It must fail on the code as it is; otherwise it is not used and the arm runs as odd-cascade.
   The test is kept outside the project: no coding attempt sees it.
3. odd cascade, `odd done`, `odd gate --recompute`, as odd-cascade.
4. The blind test runs on the result. If it passes, DONE. If it fails, it becomes a second sealed outcome
   (`blind-proof`) and the same cascade must satisfy it too; DONE only when both proofs pass, else NOT DONE.

Why: in the real-repository pilot odd's gate passed 5 runs the hidden tests failed, each because the one proof encoded
one reading of the ticket (evidence 18). Two independent readers are a check on the reading, and their disagreement
is a sign the ticket is unclear. The prompt, setup and post-check are odd-cascade's.

## To state with the results

- The arm's model is the cheap model for the outcome, both proofs and the first level; the strong model only at the
  second level of a cascade. The blind author is one more cheap session, counted in the arm's cost.
- A blind test that passes on the code as it is, or that pytest cannot run, is not used: say how many runs had none.
- The blind proof is another model's reading of the ticket, not ground truth: say how many correct results it refused.
