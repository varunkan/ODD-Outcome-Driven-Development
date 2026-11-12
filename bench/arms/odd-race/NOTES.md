# odd-race

`setup.sh` and `post.sh` are the `odd` arm's. `agent.sh` is an arm-supplied agent (SPEC.md): it runs
`arm_agent.py odd race`, which does exactly this, in the session directory:

1. One claude session on `--model` (Haiku in the planned run), prompted with `prompt.md` (the ticket, then: state the
   outcome with `odd new`, write and seal its proof with `odd seal`, do not change product code; park and say NOT DONE
   if it cannot be done) and the common ending.
2. If that session's RESULT line says NOT DONE, that message is the arm's final message and nothing else runs.
3. The outcome files the session added (not on `main`) that are not parked are taken in name order. None: NOT DONE
   ("no outcome was stated", or the parked reason). An outcome without a `sealed:` line is sealed by the arm
   (`odd seal <slug> --base main`); if that fails (the proof already passes, no test file changed): NOT DONE with
   odd's reason. The tree is then committed, because every attempt starts from HEAD.
4. `odd race <slug> --n 3 --agent <cmd> --base main`, where `<cmd>` is one more claude session on `--model` started
   with exactly the plain arm's flags and environment (`arm_agent.py session`), the race prompt on stdin. Exit not 0
   (no verified attempt, the winner left as a patch, could not run): NOT DONE with odd's reason.
5. `odd done <slug> --base main` on the applied winner, a commit, then (after every outcome) `odd gate --recompute
   --base main`: DONE when it passes, else NOT DONE with the gate's reason.

The odd it runs is the pinned copy (`ARM_ODD_PY`, the same file `ODD_PY` names to setup), never the session's
`.odd/odd.py`. `post.sh` then runs the same gate in P, as for `odd`.

## To state with the results

- The house arm, run with odd's new `race` command: three to four claude sessions per run against plain's one; its
  cost and seconds are the sum and the wall clock of all of them.
- The first session writes the proof; the race prompt is odd's, not the ticket. The code is never written by a
  session that saw the ticket's wording, only the outcome sentence and the proof.
- Adapted, not in odd: the arm (not the agent) seals an unsealed proof, commits before the race and after `odd done`,
  and turns odd's exit status into the RESULT line.
- Each claude session has the plain arm's `--max-turns` and `--timeout`; the whole arm is bounded by 4 x `--timeout`.
- A claude session that ends without a result object (a crash, an API error) makes the run an infrastructure error,
  not graded, even when odd went on without that attempt.
