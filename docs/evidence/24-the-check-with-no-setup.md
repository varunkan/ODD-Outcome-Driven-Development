# 24. The check with no setup, replayed on every kept run

*Written 2026-11-20. No model ran and nothing was spent. The plan is an independent judge's
([ruling-4.md](data/real/ruling-4.md)), written before the replay; its gate decided that no model run is bought.
Records: [check-replay.json](data/real/check-replay.json), [check-replay-small.json](data/real/check-replay-small.json).*

## Why

Evidence 22 and 23 left one number that looked like odd's own: of the plain agent's five false DONE on real bug
fixes, three were recorded as "its tests pass without its change", the fault odd's take-out check exists for. The
question was whether that check, cut loose from the rest of odd, is worth telling people about. So it was built as
one command, `odd check`: no outcome file, no `.odd` folder. It runs the test files a change brings, takes the rest
of the change out, and runs them again.

## What was done

`odd check`, frozen at commit 360a221, was run on a copy of what each kept session left: the 48 runs of evidence 22
and 23 (twice), and 33 kept runs of the two small tasks of evidence 19 to 21. Each verdict is set beside the hidden
tests' grade recorded at the time.

## What the 48 real bug-fix runs show

| `odd check` says | runs | hidden tests fail | of these, said DONE and wrong |
|---|---|---|---|
| fails without the change (shown) | 30 | 6 | 3 |
| no test of its own | 3 | 0 | 0 |
| the tests do not pass as left | 9 | 7 | 0 |
| **only test files changed, and they pass** | 4 | 4 | 3 |
| passes without the change | 1 | 1 | 0 |

One run more (pytest 7236, lean odd) read differently in the two replays and is left out: the replays ran side by
side and shared pytest's temporary folder.

- **The earlier reading was wrong, and this corrects it.** The four plain-agent runs recorded in evidence 22 and 23
  as "tests pass without the change" are runs where the agent **changed no product file at all**. It wrote a test
  that passes on the code as it was, and in three of the four said DONE. The earlier script put back "every
  non-test file" of a change that had none, and so reported the right words for the wrong reason.
- **Three of the plain agent's five false DONE are this fault.** It needs no take-out to see: the change holds only
  tests, and they pass. `odd check` names it (`NO CHANGE`) and, when asked (`--require-change`, or as a Stop hook),
  exits 1 on it. The other two false DONE have tests that do fail without the change: the fix is real and wrong, and
  no check of this kind sees it.
- **The true take-out fault was seen once in 48 runs**, in a lean-odd run that made no claim. So the question the
  judge ruled for, "when a plain agent's tests pass without its change, is the fix wrong?", has nothing to count:
  0 of 24 plain-agent runs. By the ruling's gate (2 or fewer: no model run), **no experiment is bought. Seen, not
  tested.**
- **No correct fix was flagged for changing nothing or for tests that pass anyway.** Of the 30 runs whose hidden
  tests pass, none reads "only tests changed" or "passes without the change". Two read "the tests do not pass as
  left"; both were cut off by the money limit, mid-work.
- **A shown change is not a correct one.** 6 of the 30 runs the check calls shown fail the hidden tests.

## What the small tasks show, and what the replay fixed

On 33 kept runs of the calculator and duration tasks: 25 could be measured, 24 read "fails without the change" (23
pass the hidden tests) and one "does not pass as left" (it fails them). **No correct program was flagged.** Eight
could not be measured in a copy: their tests hold their own folder's absolute path, so from a copy they run the
original program (the fault of backlog item 49; `odd check` notes it and fails nothing for it).

The replay is why two defects of the first build are gone, each now a test: an empty `tests/__init__.py` was handed
to pytest alone, which exits 5 when it collects nothing, and that failed 7 correct programs; and 15 kept trees carry
a setting that no longer exists, which stopped the command (it now says so and uses the defaults).

## What stands

- `odd check` exists, with no setup, as a command, a Claude Code Stop hook (`--stop-hook`), a GitHub Action mode
  (`mode: check`) and an MCP tool. **It reports.** By the admission rule (DESIGN 3r) it may not be called a check
  that fails work: it exits 1 only where someone chose to run it, and it is not installed by `odd init`.
- **The one fault it was built for is rare with this model on these tasks.** The common fault it does see is cruder:
  an agent that says DONE having changed only tests. That is 3 of the plain agent's 24 runs, and 0 of lean odd's 24.
- **Not shown:** that telling an agent so makes its work right. The arms for that (`plain-check`, with the hook, and
  `plain-persist`, the control for effort) are in `bench/arms/` and have not been run. The judge's count: a fair
  test of "fewer false DONE with the hook" needs about 150 new tasks and $160 to $240.
- One model, one run a task, mostly two projects: counts, not rates. The verdicts were read from runs the command
  was shaped on; only new runs can test it.
