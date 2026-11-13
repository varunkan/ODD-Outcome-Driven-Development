# odd

`setup.sh` runs `odd init` with the `odd.py` the runner gives it: the one in the bench repository's HEAD commit,
never the working-tree file. Nothing else: the method reaches the agent through the `AGENTS.md` that `init` writes.
The opt-in Claude Code hooks are not installed, so this arm measures the configuration every tool gets. The prompt is
the ticket; the runner adds the common ending (`arms/TAIL.md`). The branch `work` is the runner's, the same for every
arm.

`post.sh` runs `odd gate --recompute --base main` after the session, in a copy of what the session left that is not
the graded copy. Its exit status is recorded as `arm_check` beside the hidden-test result, so "gate passed, hidden
tests failed" can be reported as its own figure.

## To state with the results

- This is the house arm: the benchmark, its tasks and its runner are written by the ODD project.
- It is not a tagged release. Each result records the bench repository commit and the sha256 of the `odd.py` used
  (`provenance`); a run from a tree with uncommitted changes is marked `bench_dirty`.
- ODD tells the agent not to say done without a proof. A lower false-done rate can come from claiming less, so read
  it beside the pass rate and the honest not-done count.
- `arm_check` is the arm's own gate. No other arm has such a figure, and it never decides `passed`.
- Only `odd init` is measured: the `AGENTS.md` text. ODD's opt-in hooks are not installed.
- Whether a headless session reads the root `AGENTS.md` when there is no `CLAUDE.md` was not verified when this was
  written. If it does not, this arm is the plain arm with extra files; confirm it from a transcript before reading
  the figures.
