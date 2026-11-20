# 27. `odd reread` with a model: does a reader that writes only tests read like a second attempt?

*Written 2026-11-20, before the runs; the results section is added after them. The design is an independent judge's
([ruling-6.md](data/real/ruling-6.md)), fixed before any run. Five tasks, about 24 readers an arm: counts, not rates.*

## Why

Evidence 26 found, with no model, that the tests of another attempt disagree with most wrong fixes. `odd reread`
was built on that, and has never run with a model. Its reader differs from the replay's: it writes only tests, sees
no fix of its own, and is one reader, not up to four.

## What the judge corrected first

- **The command can take 13 of the 25 wrong fixes kept, on 5 tasks.** It refuses a change whose own proof fails (8)
  and a change with no product file (4).
- **"22 of 24" is not the yardstick for one reader.** On the fixes the command can take, one other attempt's tests
  fail on **21 of 41 wrong-fix pairs and 11 of 39 right-fix pairs**; from an attempt that is itself right, 10 of 15
  and 2 of 22. That is what a single reading is measured against.
- **Two faults of the command, found by reading it**, are fixed and tested before these runs (commit 14ff0e2): any
  non-zero exit counted as "fails before the change", and a reader whose test sat at another path than the proof
  runs read as agreement.

## Fixed before the runs

- **Only the reader is paid for.** Each host is a fix kept from evidence 22, 23 or 25, with its hidden grade. The
  harness ([rereadtest.py](../../bench/rereadtest.py)) rebuilds each tree from the task's repository with the kept
  run's changed files laid over it, takes the hidden grade again, and writes the outcome file itself: a neutral
  sentence, the kept run's own tests as the proof, its changed product files as `in:`. This is the best case for
  an independent reading, and the result must say so.
- **Hosts:** 24 in a fixed list, 13 wrong and 11 right, on sympy and sphinx tasks; 8 more right ones only from money
  left. All 32 were built and checked at no cost before the first session
  ([reread-hosts.jsonl](data/real/reread-hosts.jsonl)): every one usable, every grade equal to its record.
- **Two readers a host:** Haiku 4.5 (the authors' model) and Sonnet 5.5. Each session: $0.27, 40 turns, 900
  seconds, one try. The reader gets the ticket as written.
- **Every accepted proof is then run, with no model, on every host of its task.** A comparison is one accepted
  proof on one fix; the harness's own run decides (exit 0 agree, 1 disagree, anything else not compared).
- **Numbers, per reader:** A = share of wrong-fix comparisons that disagree (up to 52); B = the same on right fixes
  (30 or more); C = share of sessions with no accepted proof.
  **BETTER** than the replay: A of 60% or more, B of 15% or less, a catch on 4 of the 5 tasks.
  **LIKE** the replay: A of 40% or more, B of 40% or less, A minus B of 15 points or more, a catch on 3 of 5.
  **WORSE:** A under 40%, or A minus B under 15 points, or B over 40%.
  **NOT TESTED:** C over a third; fewer than 26 wrong or 15 right comparisons; 3 or more void sessions.
  "The stronger reader is better" only if its A minus B is 20 points or more above the other's.
- **A session is void** if its transcript holds the path of the tree with the fix, of the kept run or of the tasks,
  the words `tests_hidden` or `solution.patch`, or another model.
- **Budget:** a hard cap of $14.40, $0.30 reserved a session, no top-up, no rerun.
- **One difference from the ruling:** it named odd at a018794; the runs use 14ff0e2, which is that commit with the
  two faults above fixed. The harness still counts what those faults would have hidden.

## Said beforehand

- **No outcome lets `odd reread` fail work** (DESIGN 3r): it flags right fixes in the replay, every task here is one
  it was shaped on, and no session fixes what it flags. It stays advisory.
- The reader may recall the public fix or its tests; the stronger model is the more exposed.
- The reader is told the proof command, which names the first author's test file, and `in:`, which names the files
  the fix changed. Both pull towards agreement. It is how the command works, so it is measured, not removed.
- Never said, whatever happens: "catches 22 of 24", a rate, anything about private code, or that agreement shows a
  fix is right.

## Results

Not run yet.
