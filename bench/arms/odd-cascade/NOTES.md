# odd-cascade

As `odd-race` (read its NOTES.md for every step), except step 4: `odd cascade <slug> --agents "<cheap>,<strong>"
--base main`, where `<cheap>` is a claude session on `--model` (Haiku) and `<strong>` one on `--strong-model`
(default `sonnet`), each started by `arm_agent.py session` with the plain arm's flags and environment. The strong
level runs only when no cheap attempt is verified, with the cheap attempt's failure in its prompt (odd's own
escalation). After the last level odd parks the outcome: NOT DONE with odd's reason.

## To state with the results

- The house arm, run with odd's new `cascade` command: two claude sessions when the cheap attempt is verified, three
  when it escalates; one of them may be the stronger, dearer model, so its cost is not a Haiku-only cost.
- `models` in each record shows whether the strong model ran.
- The adaptations of `odd-race` (seal by the arm, commits, RESULT from odd's exit status) apply here too.
- Each claude session has the plain arm's `--max-turns` and `--timeout`; the whole arm is bounded by 4 x `--timeout`.
