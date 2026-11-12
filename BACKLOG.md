# Backlog

What comes after the five additions now being built (proof strength, PR evidence comment, sealed proofs, escaped-defect
log, adoption aids). Built in this order unless a measurement says otherwise.

Every item ships the ODD way: an outcome sentence, a proof that fails without the change, tests written first, and the
number that decides whether it stays. An item whose number does not move is reverted, not kept. Measurements run on
the comparison harness ([`bench/`](bench/SPEC.md)) unless stated.

The aim: make development **quicker, cheaper and more accurate**, not only checked. A proof the agent cannot fake is
a trustworthy verifier, and a trustworthy verifier is what lets cheap models, parallel attempts and less human review
be used safely.

## From the research: do these first

The research synthesis ([14](docs/evidence/14-research.md)) found these the best supported by evidence and among the
cheapest. Each cites its papers there, with a skeptic's verdict.

### R1. Measure trust directly
- **Outcome:** the comparison reports, per arm, the cheat rate and park rate on impossible tasks, claim precision
  (how often "done" is true), silent failures, and the gap between the arm's own proof and the hidden tests by diff
  size, so ODD's trust claim becomes a number.
- **Evidence:** ImpossibleBench (arXiv 2510.20270); claim precision 64% to 96% and Haiku-class silent failures 21% to
  3% with a claim contract (arXiv 2611.10063).
- **Done** in the commit "R1: measure trust directly in the bench report" (`git log --grep '^R1:'`): `bench/report.py`
  prints claim precision, the silent-failure rate, the cheat rate by route and the park rate on impossible tasks, the
  own-check gap by changed lines, and an appendix of every impossible-task NOT DONE with its keyword grade, an empty
  "reviewed" column and the reason verbatim; `bench/run.py` records `visible_tests_edited` and `special_cased` from
  the tree the session left; one more impossible task, t17 (its visible test contradicts the ticket). Re-rendered on
  the finished Sonnet run (240 runs, transcripts only, no tree facts recorded): claim precision 98% to 100% per arm,
  one silent failure (superpowers), one cheat (speckit, a DONE claim), no test edits or special-casing seen in the
  transcripts; park rate 33% to 100% under the keyword grade, with 9 NOT DONE answers it rejected left for review.
  Not measured yet: the Haiku run, t17 on any model, and how many cheats the script-visible routes miss.

### R2. Fail closed on changed tests and empty proofs
- **Outcome:** a change that edits or deletes a test that existed at the base fails the gate unless its outcome says
  why (`test-change: <reason>`), and a proof that skips its tests, runs none, or exits 0 early fails too.
- **Evidence:** harness hardening cut exploits from 6.5% to 0.8% with no loss of success (arXiv 2605.02964); read-only
  tests stopped test edits, the main route Claude models used to cheat (ImpossibleBench); exit(0) and skip were the
  systemic hacks (arXiv 2503.11926). About 110 lines, no extra run time.
- **Done** in the commit "R2: fail closed on changed tests and empty proofs" (`git log --grep '^R2:'`): field
  `test-change:`, the empty-proof check in `hollow()`, 74 lines added and 8 removed in `odd.py`. Measured on seeded fixtures (exit(0)
  at import, with and without a skip; unittest.skip on an existing test, with and without a skip; unittest.skip on a
  new test under a skip; deleting the old test; an empty unittest suite under a skip; go test with no test files under
  a skip): 0.4.0 accepted 6 of 8 in both `done` and `gate --recompute`, this version refuses 8 of 8, and three honest
  controls (unittest, pytest, go) pass in both (Python 3.13, where an empty unittest suite already exits 5, so 0.4.0
  refused that one; on 3.11 and older it exits 0, not measured). Not measured: the share of impossible-task cheats caught (needs R1).
- **Review fixes, done** in the commit "R2, R4: review fixes ..." (`git log --grep '^R2, R4: review fixes'`), from the reviewer's probe
  (seven fixtures, re-run after the fix): a new `conftest.py` that drops an existing failing test was accepted, now
  refused (conftest.py, pytest.ini, a changed pytest section of pyproject.toml/setup.cfg/tox.ini and a changed
  `load_tests` line in an `__init__.py` need `test-change:`); all-xfail (pytest) and all-expectedFailure (unittest)
  under a skip were accepted, now refused; a reason can name the test files it covers, and the gate prints
  which files each reason covers. Not fixed: a go test that `t.Skip`s every test (go prints the same `ok` line;
  documented as not detected), and a reason that names no test file still covers every test edit, from any outcome,
  so older outcome files keep passing (the gate now says so next to it). Not compared: collected test ids at base
  and head.

### R3. Make parking the sanctioned answer
- **Outcome:** the installed method tells the agent plainly to stop and explain with `odd park` when the task cannot
  be done as asked, instead of forcing a pass.
- **Evidence:** an abort option took GPT-5 cheating from 54% to 9% and o3 from 49% to 12% (ImpossibleBench). One
  paragraph, no code. Expected effect is small on current Claude models, large on models that cheat.
- **Done** in the commit "R3: make parking the sanctioned answer" (`git log --grep '^R3:'`): step 5 of the method now
  says STOP and explain with `odd park` when the task cannot be done as asked or the proof cannot honestly pass, that
  parking is then the expected, correct answer, and that a forced pass is wrong even when the gate turns green (same
  sentence count as before; block 1,998 -> about 2,260 characters, 27 -> 30 lines, tested under 2,600 and 32). `odd
  park` and the Stop hook use the same words. Not measured: any change in cheat or park rates (needs R1).

### R4. Proof strength done well (refines the step being built)
- **Outcome:** one mutant per changed line, a check that every changed line actually runs under the proof, the
  wording "proof strength k of n" (never "verified"), and print-only proofs refused.
- **Evidence:** 64.8% of Python agent PRs execute no changed line (arXiv 2607.18057); coupled mutants on covered lines
  for 70% of serious bugs (arXiv 2103.07189); mutation score is not correctness (arXiv 2607.22880).
- **Done** in the commit "R4: proof strength k of n, one mutant per line, unrun lines, print-only proofs"
  (`git log --grep '^R4:'`): `pick()` takes one mutant per changed line first, the files sharing the cap; `ran()`
  runs a Python proof once under a `sys.settrace` sitecustomize restricted to the changed `.py` files and lists
  "not run by the proof: file:line,..." (a Fail under `"enforce"`), "not measured" for other languages;
  `prints_only()` in `hollow()` refuses an echo or a Python script with no assert, raise or exit call; "proof
  strength k of n" in done, gate, summary and stats. Measured on one machine (Python 3.13): the demo's traced run
  added 0.1 s (core runs 0.1 s each) and flagged 0 lines; a pytest fixture with an uncalled function added 0.4 s
  (core 0.4 s each) and flagged its 3 unrun lines. Not measured: the bench share of proofs with unrun lines, the
  per-task correlation with hidden-test failures, and the overhead on a large suite.
- **Review fix, done** in the commit "R2, R4: review fixes ..." (`git log --grep '^R2, R4: review fixes'`): print-only is narrowed to top-level
  imports, `print(...)`, inert-module calls and name assignments with no subscript, division or modulo, and a call
  into the change only inside `print(...)` or an assignment, so `1 / (add(2, 3) == 5)`, `{5: 0}[add(2, 3)]` and a
  bare `calc.selfcheck()` are no longer refused. Not detected (documented): `| grep -q .` after a print.

### R5. An independent author for the proof
- **Outcome:** the proof can be written by a different, stronger model (`--proof-by <cmd>`) and sealed before the
  implementer starts, with about three attempts before parking.
- **Evidence:** stronger-model tests raised resolution from 61.2% to 65.3%; weak-model tests lowered it to 57.3%
  (arXiv 2609.09133). The likeliest place for a correctness gain on a weaker implementer. Merges with item 3 below.
- **Done** as item 3 (`odd spec --proof-by`, commit "B3: ..."); the comparison itself is not measured yet.

### R6. `odd challenge` (advisory)
- **Outcome:** a second model tries to write a plausible but wrong variant that still passes the proof; if it
  succeeds, the proof is too weak.
- **Evidence:** 19.7% of passing patches rejected by such checks (arXiv 2603.00520); 29.6% of passing patches diverge
  in behaviour (arXiv 2503.15223). The only measured way, without a reference patch, to catch special-casing.

### R7. Per-file inertness (opt-in)
- **Outcome:** each changed file is taken out on its own, and a file whose removal leaves the proof green is flagged.
- **Evidence:** arXiv 2606.28430, one task only; prevalence unknown.

### R8. A proof the agent never sees
- **Outcome:** an optional held-out proof run only by `gate --recompute`, plus a base-against-head behaviour diff for
  "no behaviour change" outcomes.
- **Evidence:** visible-only checks scored 97% against 0% held-out on a lookup-table solution (arXiv 2605.21384).

### What the research says not to build
An LLM judge as the arbiter of done; chain-of-thought monitoring as a control; prompt-only "do not modify the tests";
requiring agents to write more tests; coverage or mutation score presented as correctness; whole-file exhaustive
mutation; random small holdouts; auto-adding generated tests to the proof; full formal verification for ordinary
repositories. Reasons and sources: [14](docs/evidence/14-research.md).

## Accuracy and productivity

### 1. `odd race`: parallel attempts, the proof picks the winner
- **Outcome:** a developer runs one outcome as N parallel agent attempts, each in its own git worktree, and gets back
  the attempt that is proven, strongest on the deliberate breaks and smallest, with the others discarded.
- **How:** the proof is written and sealed once; the agent command is a setting (any CLI agent); attempts run in
  parallel; the winner is merged into the working tree; the race result says why it won.
- **Measure:** accuracy and cost per proven outcome for Haiku x 3 race against plain Sonnet x 1 and plain Haiku x 1, as
  a new bench arm.
- **Done** in the commit "B1: odd race ..." (`git log --grep '^B1:'`): `odd race <slug> [--n N] [--agent CMD]`, the
  settings `agents`, `race_timeout`, `race_seal` (a tool newer than 0.4.0), the MCP tool `race`, and `prove()` shared
  with `odd done`; DESIGN.md section 3b. Each attempt runs in a detached worktree under the git directory, is checked
  by the copied-files rule, the boundary and `prove()` (R2 + green-red-green + strength), and the winner is applied
  only to a tree with no changes inside the boundary. Measured with fake agents (`tests/test_odd.py` class `Race`,
  8 tests; 12 hand-made mutants of the new code, each turned its test red): one correct, one weak-proof (an unproven
  extra function), one broken, one that edits the test, rotated through 10 races: the correct one won 10 of 10
  (on proof strength), 1.3 to 1.5 s wall per race of four; setup and removal 0.03 s per attempt on a three-file
  repository. Not measured: real agents, the bench arm (Haiku x 3 against Sonnet x 1 and Haiku x 1), large
  repositories (worktree checkout grows with the tree), and agents that write outside their worktree (not prevented).
- **Review fix** (in the B3 commit, `git log --grep 'review fix: attempts'`): three
  reproduced findings closed. (1) An attempt's plain `git config core.fsmonitor ...` (or a hook, an exclude rule, a
  branch) reached the user's repository through the linked worktree and ran on later git calls there, also for a
  discarded attempt: attempts are now `git clone --shared` working trees with their own config, hooks, refs and
  index. (2) A winner could import an ignored file the patch leaves out, and the applied change broke the user's
  tree: `_settle()` removes ignored files the agent made that the user's tree lacks before the check. Found while
  fixing: `git update-index --assume-unchanged` on the sealed test let an attempt edit the proof unseen and win;
  `_settle()` now resets the index, config, `info/` and hooks before the check. (3) A `setsid` child outlived the
  race: agents carry `ODD_ATTEMPT=<tree>/`, and on Linux `/proc` is swept, the process killed and the attempt
  refused. `tests/test_odd.py` class `Isolation` (6 tests) and `Spec.test_an_author_that_leaves_a_detached_process_is_refused`:
  the four first written were seen RED on the old code (config kept, rc 0 for the ignored helper, rc 0 for the index
  trick, rc 0 for the detached process); 13 hand-made mutants of the new code, 12 turned a test red; the survivor is
  `skip_group` (the agent's own group excluded from the report), a guard against reporting processes killpg already
  killed that no test could make fire. Setup and clean-up rose from 0.03-0.04 s to 0.06-0.08 s per attempt (5 races
  of 4 attempts each way, three-file repository). Not covered: processes that clear their environment, systems
  without `/proc` (macOS), agents writing outside their tree on purpose, a repository-local config setting the check
  depended on (it no longer applies inside an attempt).

### 2. `odd cascade`: cheap model first, pay more only when the proof says so
- **Outcome:** an outcome is attempted by the cheapest configured model first and escalated to a stronger one only when
  the attempt is not proven.
- **How:** an ordered list of agent commands in settings; each attempt is verified by `odd done`; escalation stops at
  the first proven attempt or parks after the last.
- **Measure:** cost per proven outcome and accuracy for Haiku-then-Sonnet against plain Sonnet. The Haiku half of the
  comparison already shows how often a cheap first attempt is proven, which bounds the saving.
- **Done** in the commit "B2: odd cascade ..." (`git log --grep '^B2:'`): `odd cascade <slug> [--agents C1,C2,...]
  [--race N] [--base REF]`, reading `agents` as ordered levels, the MCP tool `cascade`; DESIGN.md section 3c. Each
  level is one call of race's attempt machinery (`_attempts()`, `_judge()`, `prove()`, `_apply()`, factored out of
  `cmd_race`, which now uses them too). A refused attempt's whole finding goes into the next level's prompt; after the
  last level the outcome is parked with every reason and `.git/odd/cascade/<slug>/cascade.json`; cost is the agent's
  own final `odd-cost: <usd>` line, else "not reported". Measured with fake agents (`tests/test_odd.py` class
  `Cascade`, 6 tests seen RED on the missing command, then green; 12 hand-made mutants of the new code, each turned its
  test red): 5 runs each on a three-file repository, 0.65-0.71 s wall when level 1 is verified (level 2 never ran),
  0.74-0.87 s when level 1 is refused and level 2 verified, 0.42-0.49 s to park after two refused levels (nothing
  applied in 5 of 5). Not measured: real agents, the bench arm (Haiku-then-Sonnet against Sonnet), the real saving.

### 3. Strong model writes the spec, cheap model writes the code
- **Outcome:** the outcome sentence and the proof are written by the strongest model and sealed; the implementation is
  done by a cheaper model or a race of them.
- **How:** separate agent commands for `new`/proof and for implementation; sealing from the build's step 3.
- **Measure:** accuracy and cost against the strong model doing both.
- **Done** (with R5) in the commit "B3: odd spec --proof-by ..." (`git log --grep '^B3:'`): `odd spec <slug>
  --proof-by CMD [--tries N] [--base REF]`, the setting `proof_tries` (default 3), the outcome field `proof-by`, the MCP
  tool `spec`; DESIGN.md section 3d. The author runs in a worktree under the git directory (`_worktree()`,
  `_launch()`, `_next()`, factored out of race's `_attempts()`); a try is refused unless it changed test files only and
  the proof fails there and is runnable; the reason goes into the next prompt; after the last try the outcome is parked.
  An accepted proof comes back by `git apply` and is sealed by `cmd_seal()` in the user's tree (reversed if the seal
  refuses). Race and cascade keep it byte-identical (test). Measured with fake agents (`tests/test_odd.py` class
  `Spec`, 7 tests: 6 seen RED on the missing command, the seventh (the seal refused in the user's tree) written after; all green; 16 hand-made mutants of the new code, each turned its
  test red): 5 runs each on a three-file repository, 0.31-0.42 s wall to bring back and seal on the first try,
  0.41-0.52 s to park after 3 refused tries. Not measured: real agents, the comparison above (cheap implementer with a
  cheap-written against a strong-written sealed proof, on hidden tests), and whether the proof tests the outcome
  rather than something easier (odd cannot check that).

### 4. Requirement coverage check
- **Outcome:** before code, every requirement in the ticket is mapped to an outcome, and a requirement no outcome
  covers is reported, so "works, but not what was asked" is caught at the cheapest point.
- **How:** the ticket is split into numbered requirements (by the agent, recorded in the outcome files); `odd gate`
  reports any requirement without an outcome.
- **Measure:** requirements missed per task on the vague and feature tasks, with and without.
- **Done** in the commit "B4: requirement coverage check ..." (`git log --grep '^B4:'`): requirements as `R<n>: ...`
  lines in `.odd/requirements/<ticket>.md`, the outcome field `covers: R1, R3` (or `<ticket>:R1`), `odd new --covers`,
  the MCP `new` tool's `covers`, the setting `coverage` (`off` / `report`, the default / `enforce`), one sentence in
  step 1 of the method; DESIGN.md section 5a. `coverage()` runs inside `gate()` (local and `--recompute`, settings
  from the target under `--recompute`), so the summary and `--json` carry it; a parked outcome covers nothing; an
  unknown, ambiguous or malformed id is a Fail unless `off`; a requirement dropped since the base is printed.
  Measured with `tests/test_odd.py` class `Coverage` (11 tests; 9 seen RED on the missing `--covers`, setting and
  sentence; the `off` test, split out of one of them, and the removed-requirement test written after; all green) and
  20 hand-made mutants of the new code, each turning a `Coverage` test red (one survived at first, the ids of a parked
  outcome going unchecked; an assertion was added and it then turned red).
  Not measured: requirements missed per task with and without it, and whether an agent writes a complete list; odd
  cannot check that a covering outcome's proof tests its requirement.

### 5. Reproduce first for bugs
- **Outcome:** for a bug, the proof must fail on the unfixed code by reproducing the reported behaviour before any fix
  is written.
- **How:** an outcome kind `bug` whose seal requires the proof to fail at the base revision with the reported symptom.
- **Measure:** pass rate and false "done" on the bugfix and trap tasks, with and without.

### 6. Ambiguity stop
- **Outcome:** when the outcome cannot be made checkable from the ticket, the agent asks one precise question instead
  of guessing.
- **How:** a method rule plus `odd new` refusing an outcome sentence with no observable; an "ask" result distinct from
  park.
- **Measure:** rework and wrong-problem rate on the vague tasks.

### 7. Outcome templates by kind of change
- **Outcome:** a bug, a feature and a refactor each start from the right proof shape: reproduce-then-fix; new
  behaviour plus existing behaviour unchanged; existing suite green with the take-out check skipped and the reason
  recorded.
- **How:** `odd new --kind bug|feature|refactor` filling the matching fields and hints.
- **Measure:** turns and failed `done` attempts per outcome.

### 8. Precise failure feedback
- **Outcome:** when `odd done` fails, the agent is told exactly what is unproven (the line, the surviving break, the
  proof output) so it fixes that instead of guessing.
- **How:** a compact machine-readable failure block in `done` output and through the MCP server.
- **Measure:** turns between the first failed `done` and the first passing one.

### 9. Regression guard
- **Outcome:** every proven outcome's proof joins a guard set, and the proofs of outcomes touching the same files run
  again on later changes, so an agent cannot silently break earlier proven work.
- **How:** the guard set derived from merged outcome files; `odd gate` runs the guards whose files the change touches.
- **Measure:** earlier outcomes broken by later changes, on a multi-step task sequence.

### 10. Long tasks as a chain of proven outcomes
- **Outcome:** a large ticket is done as a sequence of small outcomes, each proven and checkpointed before the next,
  and a failed one rolls back alone, so agents can run for hours and leave proven slices.
- **How:** an ordered outcome list for one ticket; a checkpoint commit per proven outcome; rollback to the last one.
- **Measure:** size and length of tasks completed unattended, with and without.

### 11. Auto-merge lane
- **Outcome:** a proven, strong, small change inside its stated files can merge with the reviewer reading only the
  outcome and the proof.
- **How:** a gate result flag and an action output the repository's merge rules can use; off by default.
- **Measure:** human review minutes per merged change ([docs/review-time.md](docs/review-time.md) protocol), and
  escaped defects through the lane.

## Speed and cost

### 12. Run only the affected proofs, and cache verification
- **Outcome:** during the loop only the proofs that cover the changed files run, and a verification whose inputs did
  not change is not repeated, locally or in CI.
- **How:** a file-to-proof map learned from past runs; the content hash already used by the local gate, shared as a CI
  cache.
- **Measure:** seconds per `done` and per CI gate, and that no false pass appears.

### 13. Boundary as context
- **Outcome:** the agent is given the outcome's file boundary up front, so it explores less of the repository.
- **How:** `odd new` and the MCP server return the boundary and the relevant files for the agent to read first.
- **Measure:** turns and tokens per task.

### 14. Stop when proven
- **Outcome:** the method tells the agent to stop as soon as the outcome is proven and strong, with no further planning
  or review rounds.
- **Measure:** cost and seconds per task at unchanged accuracy.

### 15. Attempt budget per outcome
- **Outcome:** after N failed attempts an outcome is parked or escalated instead of consuming tokens without end.
- **How:** counted by ODD from local evidence, never shown to the agent as a budget (the pilot showed a visible budget
  makes agents skip work, [12](docs/evidence/12-pilot.md)).
- **Measure:** spend on tasks that end unsolved.

### 16. Cost per proven outcome
- **Outcome:** ODD reports dollars, seconds and turns per proven outcome, the figure the race and the cascade optimise.
- **How:** from the agent's own usage where available (bench records, MCP) and local evidence.

## Learning

### 17. Proof quality trends
- **Outcome:** a project sees which kinds of outcomes and proofs let defects through, from the escaped-defect log and
  strength scores, so the method sharpens on its own failures.
- **How:** `odd stats` grouped by outcome kind, seal and strength.

## Evidence

### 18. The comparison on real repositories
- **Outcome:** the comparison is repeated on real open-source issues with their own tests (SWE-bench style), where
  agents do fail, because our hand-written tasks proved too easy for a strong model.
- **Measure:** the same measures as today, published with spread, whatever they show.

### 19. New arms for the comparison
- Haiku x 3 race, Haiku-then-Sonnet cascade, and strong-spec / cheap-code, against plain Sonnet and plain Haiku.
