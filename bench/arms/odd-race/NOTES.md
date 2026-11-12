# odd-race

`setup.sh` and `post.sh` are the `odd` arm's. `agent.sh` is an arm-supplied agent (SPEC.md): it runs
`arm_agent.py odd race`, which does exactly this, in the session directory:

1. One claude session on `--model` (Haiku in the planned run), prompted with `prompt.md` (the ticket, then: state the
   outcome with `odd new`, write and seal its proof with `odd seal`, do not change product code; park and say NOT DONE
   if it cannot be done) and the common ending.
2. If that session's RESULT line says NOT DONE, or it has no RESULT line, or it stopped at a cap, that message is the
   arm's final message and nothing else runs (graded as plain's only session would be).
3. The outcome files the session added (not on `main`) that are not parked are taken in name order. None: NOT DONE
   with the parked reason the session wrote, or with no reason ("no outcome was stated" goes to `arm_reason`). An outcome without a `sealed:` line is sealed by the arm
   (`odd seal <slug> --base main`); if that fails (the proof already passes, no test file changed): NOT DONE, odd's
   reason in `arm_reason`, never on the RESULT line. The tree is then committed, because every attempt starts from HEAD.
4. `odd race <slug> --n 3 --agent <cmd> --base main`, where `<cmd>` is one more claude session on `--model` started
   with exactly the plain arm's flags and environment (`arm_agent.py session`), the race prompt on stdin. Exit not 0
   (no verified attempt, the winner left as a patch, could not run): NOT DONE, odd's reason in `arm_reason`.
5. `odd done <slug> --base main` on the applied winner, a commit, then (after every outcome) `odd gate --recompute
   --base main`: DONE when it passes, else NOT DONE, the gate's reason in `arm_reason`.

The odd it runs is the pinned copy (`ARM_ODD_PY`, the same file `ODD_PY` names to setup), never the session's
`.odd/odd.py`. `post.sh` then runs the same gate in P, as for `odd`.

## To state with the results

- The house arm, run with odd's new `race` command: three to four claude sessions per run against plain's one; its
  cost and seconds are the sum and the wall clock of all of them.
- The first session writes the proof; the race prompt is odd's, not the ticket. The code is never written by a
  session that saw the ticket's wording, only the outcome sentence and the proof; the earlier sessions'
  transcripts are kept outside every session's tree, and the audit flags a session that reaches them.
- Adapted, not in odd: the arm (not the agent) seals an unsealed proof, commits before the race and after `odd done`,
  and turns odd's exit status into the RESULT line.
- `--max-turns` and `--max-budget-usd` are the run's, as for plain: each claude session gets what is left of
  them after the earlier ones, and none starts once one is spent (`budget_scope: run`); the three parallel
  race attempts each get what was left when they started. Each session has plain's `--timeout`; the whole
  arm is bounded by 4 x `--timeout`.
- The claim graded is the arm's: DONE only when odd's gate passes, so the false-done rate is the gate's
  false-pass rate, not the model's honesty (`claim_source: arm`; the first session's own claim is
  `agent_claim`, shown beside it in the report). A NOT DONE the arm writes carries no reason on its
  RESULT line (`arm_reason` holds it), so on an impossible task only a model's own words can pass the
  keyword grade. A first session that says NOT DONE, gives no RESULT line or stops at a cap ends the arm.
- A claude session that ends without a result object (a crash, an API error) makes the run an infrastructure error,
  not graded, even when odd went on without that attempt.
