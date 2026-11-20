# 26. A fix that is wrong in the same way as its tests: what a second reading catches

*Written 2026-11-20. No model ran and nothing was spent. The rule for an alarm was fixed in the script before the
replay ([crosstest.py](../../bench/crosstest.py), commit a50fdc0). Records: [crosstest.json](data/real/crosstest.json).*

## Why

A fix and the tests written beside it share one reading of the ticket. Every check odd runs on those tests passes
when the reading is wrong: 6 of the 30 runs `odd check` called shown fail the hidden tests (evidence 24), and with
twice the money two runs said DONE wrongly with the gate passing (evidence 25). Only a reading made apart from the
fix can see it. Before building on that idea, this asks what it would have caught on runs already kept.

## What was done

The kept runs hold 65 separate attempts at the 24 real bug fixes (two a task for 18 tasks, four or five for the six
of evidence 25). For every two attempts X and Y at one task, X's test files were copied over a copy of Y's tree and
run there. X's tests count only when they pass on X's own tree: 50 of the 65 do. **An alarm on Y: tests of another
attempt fail on Y's fix.**

## What it shows

| the fix | fixes with another attempt's tests to try | at least one alarm |
|---|---|---|
| fails the hidden tests | 24 | **22** |
| passes the hidden tests | 33 | **11** |

- **A second reading catches most wrong fixes: 22 of 24.** On the 18 tasks with only two attempts: 5 of 5.
- **It also flags a third of the right ones: 11 of 33.** 13 of those 17 failing pairs come from tests written by an
  attempt that was itself wrong. A second reader can misread too, so this cannot be a check that fails work.
- **A disagreement almost always has a wrong side: 52 of 56.** Of the 113 pairs tried, 56 disagree; in only 4 do
  both attempts pass the hidden tests. Which side is wrong, the pair cannot say.
- **Agreement is not proof: 18 of the 57 agreeing pairs are two wrong attempts** that share a reading, and 15 more
  have one wrong side. The one wrong DONE of the first 24 runs (sphinx-8638) is among the two wrong fixes no other
  attempt's tests flag.
- **When the tests come from an attempt that is right** they fail 24 of 29 wrong fixes and 4 of 28 right ones. The
  reader's quality is the whole of it, and nothing here says how to know it beforehand.

## What was built from it

`odd reread <slug> [--by CMD] [--ticket FILE]` (backlog 54, DESIGN 3t): another agent writes a proof at the base,
where the change does not exist, from the outcome and the request as written; the proof must fail there; odd then
runs it on a copy of the change. It ends in one of three ways: the two readings agree (and it says agreement is not
proof); they disagree, exit 1, with the failing test, and a person decides; or not compared. It applies nothing,
records nothing and the gate does not read it.

## What stands, and what does not

- **Shown, with no model:** on these runs a reading made apart from a fix disagrees with most wrong fixes, and a
  disagreement nearly always means one side is wrong.
- **Not shown:** that `odd reread` does this. In the replay each second reading came from an attempt that also
  wrote a fix and ran its tests on it; a reader that writes only tests may read worse or better. No model round has
  run with the command, so by the admission rule (DESIGN 3r) it is advisory.
- **Not solved:** a fix that is wrong where the ticket does not say. Two readers given the same silent ticket can
  agree on the same wrong answer, and here they did, 18 times.
- Limits: one model for 59 of the 65 attempts, mostly two projects, and the six hard tasks hold 29 of the 65
  attempts and so most of the pairs.
