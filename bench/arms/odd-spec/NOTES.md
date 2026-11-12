# odd-spec

As `odd-race` (read its NOTES.md), except:

- The first session (on `--model`, Haiku) only states the outcome with `odd new`; its prompt tells it not to write
  tests or code.
- Then `odd spec <slug> --proof-by <strong> --base main`: a claude session on `--strong-model` (default `sonnet`)
  writes only the proof in its own worktree; odd brings the test files back and seals them red, or retries (odd's
  default `proof_tries`, 3) and then parks: NOT DONE with odd's reason.
- Then `odd race <slug> --n 1 --agent <cheap>`: one Haiku attempt writes the code against the sealed proof.

## To state with the results

- The house arm, run with odd's new `spec` command: the proof is by the stronger model, the code by the cheap one, so
  the cost includes one to three strong-model sessions.
- odd race with one attempt is used because it is odd's own way to have one agent's attempt verified and applied.
- The adaptations of `odd-race` (commits, RESULT from odd's exit status) apply here too.
- Each claude session has the plain arm's `--max-turns` and `--timeout`; the whole arm is bounded by 4 x `--timeout`,
  which three refused proofs plus the attempt can reach.
