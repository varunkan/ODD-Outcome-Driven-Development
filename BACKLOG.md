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
- **Done** in the commit "R6: odd challenge" (`git log --grep '^R6:'`), a tool newer than 0.4.0: `odd challenge <slug>
  [--agent CMD]`, advisory, exit 1 when a variant the challenger calls wrong passes the proof ([DESIGN 3i](DESIGN.md)).
  Built on race's attempt machinery (`_attempts(judge=, seed=, counted=)`, `_contained()`). Tests: `Challenge`.
  Measure: on the harness, how many verified outcomes a challenger breaks, and how many of those claims a person
  confirms; not yet run.

### R7. Per-file inertness (opt-in)
- **Outcome:** each changed file is taken out on its own, and a file whose removal leaves the proof green is flagged.
- **Evidence:** arXiv 2606.28430, one task only; prevalence unknown.
- **Done** in the commit "R7: per-file inertness" (`git log --grep '^R7:'`), a tool newer than 0.4.0: setting
  `"inert"` (off, report, enforce; default off), one proof run per changed file, only when more than one changed
  ([DESIGN 4f](DESIGN.md)). Tests: `InertFiles`. Measure: how many verified outcomes on the harness carry an inert
  file, under `"report"`; not yet run.

### R8. A proof the agent never sees
- **Outcome:** an optional held-out proof run only by `gate --recompute`, plus a base-against-head behaviour diff for
  "no behaviour change" outcomes.
- **Evidence:** visible-only checks scored 97% against 0% held-out on a lookup-table solution (arXiv 2605.21384).
- **Done** in the commit "R8: held-out proofs and same-behaviour checks" (`git log --grep '^R8:'`), a tool newer than
  0.4.0: setting `"held_out"`, run only by `gate --recompute`, output never shown ([DESIGN 5e](DESIGN.md)); outcome
  line `same: <command>`, output identical with and without the change ([DESIGN 4e](DESIGN.md)). Tests:
  `HeldOut`, `SameBehaviour`. Measure: not yet run on the harness (it needs held-out tests per task, which the
  harness's hidden tests already are: the next comparison can pass them as `"held_out"`).

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
  cannot check that a covering outcome's proof tests its requirement. Review fix (commit "Fix review findings ...",
  `git log --grep '^Fix review findings'`): an asked outcome (item 6) covered requirements, so `odd ask` got around
  `coverage=enforce`; now a parked or asked outcome covers nothing (test `test_an_asked_outcome_covers_nothing`, seen
  RED, one mutant turning it red).

### 5. Reproduce first for bugs
- **Outcome:** for a bug, the proof must fail on the unfixed code by reproducing the reported behaviour before any fix
  is written.
- **How:** an outcome kind `bug` whose seal requires the proof to fail at the base revision with the reported symptom.
- **Measure:** pass rate and false "done" on the bugfix and trap tasks, with and without.
- **Done** in the commit "B5: reproduce first for bugs ..." (`git log --grep '^B5:'`): the outcome field `kind: bug`,
  `odd new --kind bug`, the MCP `new` tool's `kind`; DESIGN.md section 4a. The base run is the existing take-out
  (`without_change`): `verify()` refuses a bug proof that passes there and records `reproduced:`; `odd seal` takes an
  already-written fix out the same way. Measured with `tests/test_odd.py` class `ReproduceFirst` (6 tests; 4 seen RED
  on the missing `--kind`; the unknown-kind test and the unchanged-outcome control passed before the code, the first
  for the wrong reason, the field being unknown) and 13 hand-made mutants of the new code in odd.py and odd_mcp.py,
  each turning a `ReproduceFirst` test red. Not measured: pass rate and false "done" on bug tasks with and without;
  odd cannot tell whether the failure is the reported symptom. Review fix (commit "Fix review findings ..."): editing
  `kind: bug` to `kind: refactor` dropped the rule unseen; now a seal carries `kind@<kind>` (a sealed bug that changes
  kind fails until resealed) and the local gate prints `kind changed from bug` from local evidence (2 tests, seen
  RED). An unsealed outcome never run as a bug here, and `--recompute` without a seal, still show nothing.

### 6. Ambiguity stop
- **Outcome:** when the outcome cannot be made checkable from the ticket, the agent asks one precise question instead
  of guessing.
- **How:** a method rule plus `odd new` refusing an outcome sentence with no observable; an "ask" result distinct from
  park.
- **Measure:** rework and wrong-problem rate on the vague tasks.
- **Done** in the commit "B6: ambiguity stop ..." (`git log --grep '^B6:'`): `odd new` refuses a sentence with
  neither a verb of observation nor a measurable term (two English word lists, `OBSERVE` and `MEASURE` in odd.py;
  setting `"ambiguity_stop"`, default `true`); `odd ask <slug> "<question>"` and the MCP `ask` tool write the new
  field `asked:`; the gate reports such an outcome as `asked` / "waiting for an answer", covering no files, and `done`
  refuses it; the method says to ask one precise question. DESIGN.md section 4b. Measured with `tests/test_odd.py`
  class `AmbiguityStop` (7 tests; 6 seen RED on the missing check, command, method text and MCP tool; the
  conservative-refusal test passed before the code, as a control) and 20 hand-made mutants of the new code in odd.py
  and odd_mcp.py, each turning an `AmbiguityStop` test red (one survived at first, dropping the measurable-term list;
  a sentence relying only on it was added and it then turned red). Not measured: rework and wrong-problem rate on
  vague tasks; the word list lets through vague sentences containing a listed word and likely refuses other languages.
  Review fix (commit "Fix review findings ..."): the lists refused ordinary sentences ("The login button is disabled
  while the request is pending.", "A cashier can split a bill between guests.") and passed "Improve the code so the
  tests pass."; now state predicates, "can <verb>" and common domain verbs count, and the suite passing is taken out
  first (`SUITE_PASSES`); 2 tests with 10 sentences, seen RED. Sentences built only from unlisted words are still
  refused.

### 7. Outcome templates by kind of change
- **Outcome:** a bug, a feature and a refactor each start from the right proof shape: reproduce-then-fix; new
  behaviour plus existing behaviour unchanged; existing suite green with the take-out check skipped and the reason
  recorded.
- **How:** `odd new --kind bug|feature|refactor` filling the matching fields and hints.
- **Measure:** turns and failed `done` attempts per outcome.
- **Done** in the commit "B7: outcome templates by kind of change ..." (`git log --grep '^B7:'`): `KINDS` gains
  `feature` and `refactor`; `odd new --kind` prints `hint (<kind>): ...` after creation (`HINTS`); `--kind refactor`
  writes `counterfactual: skip - behaviour-preserving refactor` and makes `--proof` optional, defaulting to the
  detected runner's whole suite (`SUITES`, through `suggest_proof(..., suite=True)`); the MCP `new` tool no longer
  requires `proof`. DESIGN.md section 4c. Measured with `tests/test_odd.py` class `KindTemplates` (7 tests; 5 seen
  RED on the unknown kinds and missing hints; the missing-proof refusal and the no-kind-no-hint control passed before
  the code, as controls) and 14 hand-made mutants of the new code in odd.py and odd_mcp.py, each turning a
  `KindTemplates` test red. Not measured: turns and failed `done` attempts per outcome with and without templates;
  `feature` adds only a field and a hint; only the unittest whole-suite command is exercised.

### 8. Precise failure feedback
- **Outcome:** when `odd done` fails, the agent is told exactly what is unproven (the line, the surviving break, the
  proof output) so it fixes that instead of guessing.
- **How:** a compact machine-readable failure block in `done` output and through the MCP server.
- **Measure:** turns between the first failed `done` and the first passing one.
- **Done** in the commit "B8: precise failure feedback ..." (`git log --grep '^B8:'`): a failed `done`, and a race or
  cascade with no verified attempt, ends with `next:`, one line per item present (`proof:` failing line, `survived:`
  break, `not run:` line, `refused:` test edit) and `rerun:` the command; items ride on `Fail.items`, one formatter
  `next_block()`, reused by the cascade prompt; the MCP server adds `structuredContent.next`. DESIGN.md section 4d.
  Measured with `tests/test_odd.py` classes `FailureFeedback` and `AttemptFeedback` (8 tests, 7 seen RED for want of
  the block before the code; the pass-has-no-block control passed). Mutants: no record of a B8 mutation run was kept; in the review-fix step
  2 mutants of the `cmd_done` block condition (block always, block never) were run, each turning a `FailureFeedback`
  test red; no other B8 mutants were run. Review fix: a failure with no item printed only `rerun:` of the command
  known to fail the same way (for example nothing changed inside `in:`, whose remedy is `--base <revision>`); now such
  a failure prints no block (2 tests, seen RED). Not measured: the turns between the
  first failed `done` and the first passing one, with and without the block (no agent run).

### 9. Regression guard
- **Outcome:** every proven outcome's proof joins a guard set, and the proofs of outcomes touching the same files run
  again on later changes, so an agent cannot silently break earlier proven work.
- **How:** the guard set derived from merged outcome files; `odd gate` runs the guards whose files the change touches.
- **Measure:** earlier outcomes broken by later changes, on a multi-step task sequence.
- **Done** in the commit "B9: regression guard ..." (`git log --grep '^B9:'`): `guards()` picks every earlier
  outcome (tracked at the base, not in play, not parked, asked or skipped) whose `in:` holds a touched product or test
  file and runs its proof once through `run_proof` (green only, no take-out); `odd gate` local and `--recompute` fail
  with `<slug> (proven in <commit>) now fails: <last line>` under the setting `"guard"` (`enforce` default, `report`,
  `off`; a tool newer than 0.4.0); `--json` `guards`, `--summary` **Guards** list. DESIGN.md section 5b. Measured with
  `tests/test_odd.py` class `RegressionGuard` (5 tests; the 3 positive ones seen RED for want of the guard and the
  setting before the code, the 2 negative ones passed vacuously before it and are pinned by mutants). Mutants: 9 of
  the new code (off ignored, no overlap filter, parked, asked and skipped kept as guards, report acting as enforce, no
  problem raised, no summary list, a fail recorded as ok), each turned a `RegressionGuard` test red. Suites: 214
  tests and 75 bench tests green. Not measured: earlier outcomes broken by later changes on a multi-step task
  sequence, with and without the guard (no agent run); the guard's cost on a real repository (one proof run per
  guard by construction).

### 10. Long tasks as a chain of proven outcomes
- **Outcome:** a large ticket is done as a sequence of small outcomes, each proven and checkpointed before the next,
  and a failed one rolls back alone, so agents can run for hours and leave proven slices.
- **How:** an ordered outcome list for one ticket; a checkpoint commit per proven outcome; rollback to the last one.
- **Measure:** size and length of tasks completed unattended, with and without.
- **Done** in the commit "B10: odd chain ..." (`git log --grep '^B10:'`): `odd chain <ticket> [--race N] [--cascade]
  [--agents C1,C2] [--base REF]` over `.odd/chains/<ticket>.md` (one slug per line), the MCP tool `chain`; DESIGN.md
  section 3e. No new attempt machinery: `cmd_race` and `cmd_cascade` were split into `_race_run()` and
  `_cascade_run()`, which chain calls; the winner goes through `_apply()`, is verified again in the user's tree by
  `prove()` and recorded by `_verified()` (factored out of `cmd_done`), then committed as `odd: <slug> proven` with
  only its own files (winner's files, outcome file, chain file, the tests its proof names or its seal holds). An
  outcome is proven when that commit is in HEAD's history and not reverted. An unproven outcome is parked with each
  attempt's reason and stops the chain (exit 1); a failure after the apply reverses the winner's patch (`_patch()`);
  a git failure rolls back without parking (exit 2); the chain refuses to start on changes outside the chain's
  outcome files and tests. Measured with fake agents (`tests/test_odd.py` class `Chain`, 7 tests; the 6 first
  written seen RED on the missing command and MCP tool, the revert test added after a mutant of the subject match
  survived): three outcomes proven with three checkpoint commits and a clean tree; a failing middle outcome keeps
  the first checkpoint, parks the second ("attempt 1: the proof fails"), leaves the third not started, and the
  resume (with `--cascade`) skips the first without running an agent and proves the other two; a checkpoint refused
  by a pre-commit hook rolls the tree back; a dirty file outside the chain refuses the start. Mutants: 19 hand-made
  of the new code, each turned a `Chain` test red. Wall time, 5 runs each on a repository of six small files: 3.9-4.2
  s for three outcomes with `--race 1`, 1.7-1.9 s for a chain stopping at the second, 2.8-3.1 s for its resume.
  Suites: 221 tests and 89 bench tests green. Not measured or not tested: real agents; size and length of tasks
  completed unattended with and without chains (the backlog's measure); the rollback on Ctrl-C or SIGTERM (by code,
  `except BaseException`, no test); a SIGKILL between apply and checkpoint (leaves the winner's files uncommitted;
  the next run refuses and names them); the sealed-file part of the checkpoint paths and the flags in the `rerun:` line
  (no test pins them).

### 11. Auto-merge lane
- **Outcome:** a proven, strong, small change inside its stated files can merge with the reviewer reading only the
  outcome and the proof.
- **How:** a gate result flag and an action output the repository's merge rules can use; off by default.
- **Measure:** human review minutes per merged change ([docs/review-time.md](docs/review-time.md) protocol), and
  escaped defects through the lane.
- **Done** in the commit "B11: auto-merge lane ..." (`git log --grep '^B11:'`): settings `"auto_lane"` (default
  `false`), `"auto_min_strength"` (default `1.0`, k of n with k = n) and `"auto_max_lines"` (default 120), a tool
  newer than 0.4.0. `lane()` and `_strong()` read what the gate already computed (the recorded strength results, the
  `test_change()` reason, `survey()`'s control, stray and product lists, the guard results, the problems); no new
  check runs, and the only extra work is one `sizes()` over the product files. `--json` `lane` and `lane_reasons`,
  the printed `lane` line, the summary line `Auto-merge lane: yes` / `no, because ...`, and the Action output
  `odd_lane` (`auto`, `review`, `off`; the gate step now also writes `--json`). odd never merges. DESIGN.md section
  5c (with a wiring sketch and the risk). Measured with `tests/test_odd.py` class `AutoLane` (16 tests): 13 seen RED
  before the code (the settings did not exist, no `odd_lane` output); the default-off and wrong-value tests passed
  vacuously before it and are pinned by mutants; the 120-line default test was added after a mutant of the default
  survived. Mutants: 29 hand-made of the new code and the Action (each disqualifier dropped, the threshold
  loosened, the defaults and validators changed, the flag forced to auto, the text, summary and output lines
  broken), each turned an `AutoLane` test red. Suites: 237 tests and 89 bench tests green. Not measured or not
  tested: review minutes per merged change and escaped defects (no repository uses the lane); the wiring sketch in
  DESIGN.md 5c (no GitHub run); the lines-run condition outside Python (not measured there, so the lane relies on
  k of n alone); the `value:` line of the Action output (only the output's declaration is asserted).
- **Review fixes** in the commit "B9-B11 review fixes: ..." (`git log --grep '^B9-B11 review fixes'`): `guards()` now
  skips only outcomes in play, so an edit to only the `escaped:` line no longer turns a guard off (blocker); a
  merged outcome file deleted in the change is listed by `survey()` (`deleted`), printed `deleted <slug> (merged in
  <commit>)`, in `--json` and the summary, is a lane reason, and its base proof runs as a reported guard (blocker);
  a merged outcome parked or asked in the change runs its base proof as a reported guard (minor); the chain unstages
  what a failed step staged and `_dirty()` also reads `git diff --cached HEAD` (minor, two). `Outcome.parse()` and
  `outcome_at()` were factored out of `Outcome.load()` so the base text parses the same way. 4 new tests and 1
  strengthened (`RegressionGuard` 3, `Chain` 1 new and the hook test now asserts the index), all 5 seen RED for the
  intended reason before the fix; 6 mutants of the fix each turned one red. Suites: 241 tests and 89 bench tests
  green. Not done: a deleted or parked outcome's failing proof does not fail the gate (reported only, by choice:
  deleting a feature with its outcome is legitimate); the reviewer repro scripts r1, r3 and r6 were rerun and show the fixed behaviour; r4 and r5 were not rerun.

## Speed and cost

### 12. Run only the affected proofs, and cache verification
- **Outcome:** during the loop only the proofs that cover the changed files run, and a verification whose inputs did
  not change is not repeated, locally or in CI.
- **How:** a file-to-proof map learned from past runs; the content hash already used by the local gate, shared as a CI
  cache.
- **Measure:** seconds per `done` and per CI gate, and that no false pass appears.
- **Done** in the commit "B12: verification cache and affected guards" (`git log --grep '^B12:'`), a tool newer than
  0.4.0: `verify()` keys each verification (`verify_key()`: the tool's version and own bytes, every setting in force,
  the base commit, and `_state()` of every path that differs from the base, the helper the local gate's content hash
  uses) and returns an earlier pass as `cached (verified at <time>)`; `--no-cache` on done, gate, race, cascade and
  chain and on the MCP tools. Locally `.git/odd/verified.json` (shared with race attempts' clones) or `"cache_file"`;
  under `--recompute` only a `"cache_file"` from the target branch's settings outside the repository and its git
  directory, and only entries an earlier `--recompute` wrote; the file is snapshotted before any proof or agent runs
  and put back after, so what they write to it is dropped. The guard now reports `N earlier proof(s) skipped as
  unaffected` (`guards_skipped` in `--json`). Measured on the test fixture (one machine, Python 3.13): second `done`
  0.22 s against 0.91 s, second `gate --recompute` 0.16 s against 0.73 s; with a 1 s proof 0.20 s against 5.70 s and
  0.16 s against 5.66 s; a one-byte change runs in full (0.70 s, 5.70 s). A test per input kind (proof command,
  setting, boundary file, test file, unchanged file outside the boundary, tool, base commit, a target-only setting
  under `--recompute`) forces a full run; 17 mutants of the new code (odd.py 16, odd_mcp.py 1) each turned a new
  test red, and one more survived as equivalent (using the local cache under `--recompute` is also refused because
  it lies inside the git directory). Not done: the
  learned file-to-proof map (selection stays by `in:` path); the CI recipe (restore on pull requests, save on the
  target branch) is documented, not run on GitHub Actions; ignored files, installed packages and the environment are
  not in the key; seconds per CI gate on a real repository and false passes on real work are not measured.
- **Fixed after review** (commit "Review fixes: B12 key per outcome, B15 park enforced, B17 snapshot label"): the key did not name the outcome, so a second outcome of one change was given the
  first one's pass, under `done` and inside one `gate --recompute` (a false pass in CI). `verify_key()` now hashes
  the outcome's path and its `proof`, `in`, `counterfactual`, `kind` and `sealed` fields, and makes no key while a
  tracked file is flagged assume-unchanged or skip-worktree (git diff hides its edits). Tests
  `VerifyCache.test_a_second_outcome_in_the_same_change_is_never_given_the_first_ones_pass`,
  `test_recompute_runs_every_outcome_of_one_change`, `test_a_file_git_diff_is_told_to_ignore_is_never_served_from_the_cache`,
  each seen RED before the fix (the first two served `cached`, the third served the stale pass); mutants dropping the
  outcome from the key or ignoring the index flags each turned them red. Documented, not fixed: locally anything that
  can write the git directory can plant a cached pass for `done` (entries are not authenticated); only
  `gate --recompute` decides.

### 13. Boundary as context
- **Outcome:** the agent is given the outcome's file boundary up front, so it explores less of the repository.
- **How:** `odd new` and the MCP server return the boundary and the relevant files for the agent to read first.
- **Measure:** turns and tokens per task.
- **Done** in the commit "B13: boundary as context" (`git log --grep '^B13:'`), a tool newer than 0.4.0, no setting:
  `read_first()` lists, under `read these first`, the files inside `in:` that exist (never `.odd/`), at most ten
  (`READ_FIRST`), the largest change against the base first (`sizes()`; a binary counts as no lines), then the
  largest file, with `and N more`, and `the proof runs: <files>` (`proof_runs()`). `odd new` prints it (so the MCP
  `new` tool returns it) and `_prompt()` puts it in the race, cascade and chain prompt file. Measured with
  `tests/test_odd.py` classes `BoundaryContext` and `BoundaryPrompt` (7 tests; 5 seen RED for the missing heading
  before the code, 2 added after): 12 hand-made mutants of the new code each turned a new test red (one survived
  first, a changed binary ranked as 10^6 lines; fixed and covered). Cost on a clone of this repository (362 files,
  `--in "bench/**"`, one machine, Python 3.13): `odd new` 0.16-0.25 s against 0.11-0.14 s before. Not done: turns
  and tokens per task (the item's measure) are not measured; the list is a reading order, not a closure (imports
  and callers outside the boundary are not listed); the `changed, not text` label is not asserted by a test.

### 14. Stop when proven
- **Outcome:** the method tells the agent to stop as soon as the outcome is proven and strong, with no further planning
  or review rounds.
- **Measure:** cost and seconds per task at unchanged accuracy.
- **Done** in the commit "B14: stop when proven" (`git log --grep '^B14:'`), a tool newer than 0.4.0, no setting:
  step 4 of the method gains one sentence (once `odd done` passes with full proof strength and `odd gate` passes,
  stop and report; do not plan, review or refactor further in this outcome), and `odd done`'s success output ends with
  `next: report the outcome as done (odd gate passed)` when its gate passes, with the gate's `FAIL` and problems
  otherwise. To keep the `AGENTS.md` block within the existing size test (2,600 characters, 32 lines) step 2 drops
  "and the reseal shows in review"; the block is now 2,595 characters and 32 lines. Measured with `tests/test_odd.py`
  class `StopWhenProven` (4 tests; 3 seen RED before the code for the missing sentence and line, the fourth, the
  gate-fails case, passed before too and is a control that the line is never printed after a failing gate): 7
  hand-made mutants (no line, always the line, inverted condition, changed wording, changed method sentence, block 32
  characters over, block one line over) each turned a new test red. Suites: 264 and 89 tests OK. Not done: cost and
  seconds per task (the item's measure) are not measured; the line follows the gate only, so under the default
  `"strength": "report"` it also appears when strength is below full; the block has no size headroom left.

### 15. Attempt budget per outcome
- **Outcome:** after N failed attempts an outcome is parked or escalated instead of consuming tokens without end.
- **How:** counted by ODD from local evidence, never shown to the agent as a budget (the pilot showed a visible budget
  makes agents skip work, [12](docs/evidence/12-pilot.md)).
- **Measure:** spend on tasks that end unsolved.
- **Done** in the commit "B15: attempt budget per outcome" (`git log --grep '^B15:'`), a tool newer than 0.4.0, setting
  `"max_attempts"` (default 0, off; the v0.4.0 Action refuses it as unknown): `failures()` counts, from local evidence,
  failed `odd done` runs and every attempt `_judge()` refused in `_attempts()` (so race, cascade and chain alike),
  since the latest verified `done` or budget park; `budget()` parks with the first line of each reason and exit 1 when
  the count reaches the limit; a cascade runs no further level once reached. Nothing in `AGENTS.md` or a prompt names
  it (asserted). DESIGN.md section 3g. Measured with `tests/test_odd.py` class `AttemptBudget` (6 tests) and
  `Chain.test_chain_attempts_count_for_the_attempt_budget`; the 6 `AttemptBudget` tests seen RED before the code (the
  unknown setting, exit 2); the chain test was added after the code, and the mutant dropping the chain reason turns it
  red: 12 hand-made mutants
  (no reset on a verified done, no reset on a budget park, race attempts not counted, `>=` to `>`, default 1, no
  attempt record, no cascade stop, chain reason dropped, no budget in done, in race, in cascade, no park record) each
  turned a new test red. In the cascade test with `"max_attempts": 2` and three levels, the third agent did not run.
  Suites: 271 and 89 tests OK. Not done: spend on tasks that end unsolved (the item's measure) is not measured on real
  agents; the count is per machine and worktree; `odd stats` does not show refused race attempts.
- **Fixed after review** (commit "Review fixes: B12 key per outcome, B15 park enforced, B17 snapshot label"): a budget park stopped nothing; `done`, `race`, `cascade` and `chain` ran on and a
  later pass deleted the line. Now `prove()` and `_race_start()` refuse a budget-parked outcome (`Parked`, exit 1, no
  proof, no agent, not counted), a chain stops without rewriting the line, and the message says to report it to a
  person instead of "delete that line". Test `AttemptBudget.test_a_budget_park_refuses_done_race_cascade_and_chain_until_a_person_clears_it`,
  RED before the fix (the message offered the way round); mutants (no refusal in `prove()`, none in `_race_start()`,
  chain overwriting the park, done recording the refusal, the old message) each turned it red; a guard in
  `_verified()` was dropped as unreachable (its mutant survived because `prove()` refuses first). Documented, not
  changed: the number is in `.odd/config.json`, readable by an agent in its copy; an agent with a shell can delete the
  `parked:` line itself.

### 16. Cost per proven outcome
- **Outcome:** ODD reports dollars, seconds and turns per proven outcome, the figure the race and the cascade optimise.
- **How:** from the agent's own usage where available (bench records, MCP) and local evidence.
- **Done** (commit "B16: cost per proven outcome", a tool newer than 0.4.0, no new setting): `_attempts()`, which
  race, cascade and chain share, records every attempt's `cost` (the agent's `odd-cost: <usd>` line via `_cost()`, or
  null) and `seconds` (agent plus verification) in local evidence; `odd stats` prints per outcome and in total the
  dollars and seconds spent, proven outcomes, and dollars and seconds per proven outcome, failed attempts included,
  labelled self-reported. DESIGN.md section 3h. Measured with `tests/test_odd.py` class `CostPerOutcome` (4 tests,
  fake agents printing costs), all 4 seen RED before the code (no attempt line recorded; no cost table); 12 hand-made
  mutants (cost dropped, seconds zeroed, failed key dropped, attempt key renamed, proven always false, dollars zeroed,
  divide by attempts, proven inverted, empty message dropped, reported count from attempts, table not printed, every
  outcome counted as proven) each turned a new test red. Suites: 275 and 89 tests OK (the Chain budget test was made independent of the order parallel attempts end in, after it failed once on that order). Not done: turns are not recorded (odd sees
  only a command's output); dollars are a floor when an agent prints no cost; seconds are summed per attempt, not wall
  clock; work outside race, cascade and chain is not counted; nothing measured on real agents.

## Learning

### 17. Proof quality trends
- **Outcome:** a project sees which kinds of outcomes and proofs let defects through, from the escaped-defect log and
  strength scores, so the method sharpens on its own failures.
- **How:** `odd stats` grouped by outcome kind, seal and strength.
- **Done** (commit "B17: proof quality trends", a tool newer than 0.4.0, no new setting): `odd stats` prints a table
  `proof quality trends (self-reported: ...)` with one row per group (kind bug, feature, refactor, none; sealed or not;
  strength full, partial, not measured; proof by another agent, from the `proof-by:` line, or not): outcomes, escaped
  defects and the rate (escaped defects per outcome), and under each group of fewer than 10 outcomes a line saying the
  counts are small and self-reported. The groups are one table (`TRENDS`) counted by `tally()`, which also renders the
  existing `N in K of M` splits. `odd stats --json` prints the outcomes, the groups and the cost totals (`spend()` now
  returns them); the MCP server gains a `stats` tool. DESIGN.md section 9. Measured with `tests/test_odd.py` class
  `ProofQualityTrends` (6 tests, fixture outcome files and evidence written directly); the first 4 seen RED before
  the code (no trends table; `--json` unknown, exit 2), the seal-line, MCP and exact-10 checks added after the code
  when mutants survived; 16 hand-made mutants (band swapped, proof-by inverted, empty rate 0, rate inverted, `<` to
  `<=`, threshold 100, small line dropped, tally swapped, escapes counted per outcome, no `kind: none`, sealed read from
  the file alone, `--json` ignored, JSON polluted by the cost print, per-proven spend always null, JSON strength only
  when full, MCP flag as string) each turned a new test red. Suites: 281 and 89 tests OK. Not done: no trend over
  time (a single snapshot, not dated buckets); kind, seal and proof-by are read as the outcome files are now, not as
  they were when a defect escaped; "the same author" includes outcomes whose proof author was never recorded; no
  real project's escape log has been run through it.
- **Fixed after review** (commit "Review fixes: B12 key per outcome, B15 park enforced, B17 snapshot label"): the table was headed "proof quality trends" although it is one undated snapshot. It
  is now `escaped defects by group (a snapshot of the outcome files as they are now, not a trend over time;
  self-reported: ...)`; the JSON key stays `trends` for compatibility. `ProofQualityTrends` asserts the heading; the
  old heading as a mutant turns it red. Dated buckets are still not done.

## Evidence

### 18. The comparison on real repositories
- **Outcome:** the comparison is repeated on real open-source issues with their own tests (SWE-bench style), where
  agents do fail, because our hand-written tasks proved too easy for a strong model.
- **Measure:** the same measures as today, published with spread, whatever they show.

### 19. New arms for the comparison
- Haiku x 3 race, Haiku-then-Sonnet cascade, and strong-spec / cheap-code, against plain Sonnet and plain Haiku.
- **Run** 2026-11-12 ([16](docs/evidence/16-new-arms.md)): 288 runs, $21.81. As built and driven, the new arms
  delivered less than plain Haiku (race 23, cascade 18, spec 22 of 42 doable tasks delivered, plain Haiku 42, plain
  Sonnet 42) at three to thirteen times its cost; they gave an honest NOT DONE on all 6 impossible runs each (plain
  Haiku 4). Two causes, both read from every failure: items 20 and 21.

### 20. Successive outcomes on one branch
- **Outcome:** outcomes proven one after another on one branch (`odd chain`'s checkpoints) may share a file; the gate
  verifies each as its own change and refuses one that a later change broke.
- **Evidence:** 34 runs in [16](docs/evidence/16-new-arms.md) proved every outcome and were then refused by the gate
  ("within one change a file belongs to one outcome"), though their work passed the hidden tests.
- **Done** in the commit "B20: successive outcomes on one branch" (`git log --grep '^B20:'`), a tool newer than
  0.4.0 ([DESIGN 5](DESIGN.md)). Tests: `Successive` (a chain of two outcomes on one file passes; a hollow later
  outcome, a forged checkpoint, a later change that breaks an earlier outcome and an outcome edited after its
  checkpoint are refused; each refusal shown to fail with the fix broken). The harness's reason line now quotes a
  failed gate's first problem.

### 21. Dependency order, and the rerun
- **Outcome:** a ticket split into outcomes is built in an order where each outcome's proof can pass from its own
  boundary; then the new arms are run again.
- **Evidence:** about 23 runs in [16](docs/evidence/16-new-arms.md) ended with no attempt verified, because the
  harness ran outcomes in name order and an outcome's proof needed a file inside a later outcome's boundary (t12,
  t11).
- **Plan:** the first session writes the order as a chain file (`.odd/chains/<ticket>.md`) and the arms run `odd
  chain`, so the harness exercises odd's own path; then rerun race, cascade and spec on Haiku (about $16, measured
  in 16).
- **Measure:** delivered doable tasks and cost against plain Haiku and plain Sonnet, as in 16.
- **Done and run** (commit "bench: the new arms build outcomes in the session's chain order (item 21)"; 144 runs,
  $10.05, [16](docs/evidence/16-new-arms.md#after-the-fixes)): delivered race 35, cascade 39, spec 30 of 42 (from 23,
  18, 22); refused correct 0 in every arm (from 11-13); false DONE race 0, cascade 1, spec 5. Cascade came near plain
  Sonnet's delivery at a third of its cost; neither beat plain Haiku, which delivered all 42 at the lowest cost with
  two false DONE.

### 21b. A contamination rule that flags only other sessions
- **Done** in the commit "bench: the contamination rule flags only other sessions' directories" (`git log --grep
  'contamination rule flags only'`): the temporary-directory pattern matched any `/tmp/bench-*` path, so every
  comparison flagged scratch files agents made for themselves (16 runs in [15](docs/evidence/15-comparison.md), 4 in
  [16](docs/evidence/16-new-arms.md)), each cleared by hand. It now matches only mkdtemp's `bench-` plus eight
  characters, the form of every session directory. Replayed on the 7 flagged runs of 16: the 4 scratch flags clear,
  the 3 real peer sightings (process listings of a concurrent run) stay flagged.

### 22. Other models and agents
- **Outcome:** the comparison is run with at least one agent that is not Claude Code and one model that is not
  Claude (for example Codex CLI, Gemini CLI or aider with an open model), as a plain arm and as a race or cascade
  level.
- **Why:** odd itself calls no model (an agent is a command line in `"agents"`; the method is in `AGENTS.md`), but
  every measured run so far used Claude Code with Claude models, so "works with any model" is designed, not shown.
- **Needs:** the other CLIs installed in the runner and their API keys; `bench/arm_agent.py`'s session command takes
  only the `claude` CLI today.
- **Measure:** delivered, false DONE and cost per agent, as in 16.

### 23. A disputed proof goes back to be rewritten
- **Outcome:** when the attempts at a sealed outcome all fail and say the proof itself is wrong (a line `odd-dispute:
  <assertion and why>`, as `odd challenge` uses `odd-wrong:`), race and cascade stop spending attempts, keep the
  disputes, and hand the proof back to its author (`odd spec --proof-by`, or the first session) with them, instead of
  parking the outcome; the gate never reads a dispute.
- **Evidence:** in [16](docs/evidence/16-new-arms.md#after-the-fixes), 17 of the 18 runs that ended with no attempt
  verified had attempts naming a wrong assertion in the sealed proof (one checked by hand: the fixture sums to 4900,
  the proof asserts 4800): 17 of the 22 doable runs that race, cascade and spec did not deliver in run C. A better
  attempt cannot deliver them while the proof is wrong.
- **Measure:** delivered doable tasks on the same harness with disputes sent back, against run C; false DONE must not
  rise (a rewritten proof is sealed red again, before any code).
- **Done** in the commit "B23: a disputed proof waits for an answer instead of parking" (`git log --grep '^B23:'`), a
  tool newer than 0.4.0 ([DESIGN 3d1](DESIGN.md)). Tests: `Disputes`. The harness sends a disputed proof back to its
  author once (`odd spec`; the arm's own model for race and cascade, the strong model for spec) and runs the attempts
  again; test `test_a_disputed_proof_goes_back_to_its_author_once_and_the_race_runs_again`. Measure: not yet run.

## From the source projects' session logs (2026-11-12)

The session logs of the projects this method came from (a mobile point of sale on a cloud database, and a booking
website) were read for corrections and recurring failures that odd does not yet check. Coverage was partial: the logs
are large, and the evidence below is described in general terms, without project details. Ranked by value against
cost to build.

### 24. Standing checks: project rules as commands every gate runs
- **Evidence:** the owner had to restate the same project rules across sessions; a session ran a device command the
  project forbids; credentials once committed to a repository's history had to be rotated.
- **Outcome:** `"checks": [{"name", "cmd", "in"}]` in the settings (read from the target in CI), run by `odd gate`
  (and `--recompute`) when the change touches their `in:`, output shown; one that fails fails the gate. A secrets
  scan is the documented first example. Shares the held-out proofs' runner.
- **Done** in the commit "B24-B29: checks, flakes, targets, owed steps, cost, pipes" (`"checks"`; tests `Checks`; [DESIGN 5f](DESIGN.md)).


### 25. A flaky proof cannot fake the take-out check
- **Evidence:** snapshot tests that failed and then passed on rerun; a red that is a flake makes a proof look as if it
  depends on the change.
- **Outcome:** `"repeat": N` (default 1): the take-out run must fail N times and the proof pass N times.
- **Done** in the commit "B24-B29: checks, flakes, targets, owed steps, cost, pipes" (`"repeat"`; tests `Flaky`; [DESIGN 5f](DESIGN.md)).


### 26. Target binding: the proof says what it ran against
- **Evidence:** an agent inspected the default database while the app uses a named one, and drew wrong conclusions; a
  device was tested without the fixed build; a site's login broke in production with green local tests because the
  deployed site lacked its settings, and smoke checks hit an older deployment.
- **Outcome:** `target: <command>` in an outcome prints what the proof runs against; it runs with the proof, and its
  output must contain the commit under test or the expected text in `target-is:`, else `done` fails.
- **Done** in the commit "B24-B29: checks, flakes, targets, owed steps, cost, pipes" (`target:`, `target-is:`; tests `Target`; [DESIGN 5f](DESIGN.md)).


### 27. Owed real-system steps keep an outcome open
- **Evidence:** a fully green unit suite while the fix failed on the device; a host proof green while the real
  service refused the request; work reported done with several owner-only steps still open.
- **Outcome:** `owed: <step>; <step>` in an outcome: the gate reports it as proven with steps owed and the auto lane
  never takes it; `odd owed <slug> "<step>" --evidence <file>` closes a step; `"owed": "enforce"` fails the gate.
- **Done** in the commit "B24-B29: checks, flakes, targets, owed steps, cost, pipes" (`owed:`, `odd owed`, `"owed"`; tests `Owed`; [DESIGN 5f](DESIGN.md)).


### 28. A budget in dollars
- **Evidence:** long sessions that spent heavily on repeated review rounds of the same screens.
- **Outcome:** `"max_cost": <usd>` parks an outcome once its recorded attempt costs reach it, like `"max_attempts"`.
- **Done** in the commit "B24-B29: checks, flakes, targets, owed steps, cost, pipes" (`"max_cost"`; tests `AttemptBudget.test_a_dollar_budget_parks_once_the_attempts_cost_reaches_it`; [DESIGN 5f](DESIGN.md)).


### 29. Proof commands whose pipe can hide a failure are refused
- **Evidence:** a recorded lesson: a shell check piped into `grep -q` that stayed green when it should fail.
- **Outcome:** `odd new` and `done` refuse a proof whose verdict comes from a pass-through stage of a pipe (`| tail`,
  `| tee`, `| grep -q .`) without `pipefail`, naming the stage.
- **Done** in the commit "B24-B29: checks, flakes, targets, owed steps, cost, pipes" (`masked()`; tests `MaskedPipe`; [DESIGN 5f](DESIGN.md)).


### 30. A proof that reads the changed files as text is not strength
- **Evidence:** a test asserted a style string read from a component's source; it kills every mutant and proves no
  behaviour.
- **Outcome:** proof strength marks a test that opens a file inside `in:` as text, and says the score does not count.
- **Done** in the commit "B30-B31: text-reading proofs and look-alike bugs" (`textual_reads()`; tests `TextualProof`; [DESIGN 5f](DESIGN.md)).


### 31. Look-alike bugs
- **Evidence:** repeated fix-of-fix entries in one project's fix log (a sibling code path a few lines away had the same
  defect).
- **Outcome:** `class: <regex>` on a `kind: bug` outcome: `done` lists every match in the tree and which the proof's
  run executed (the execution check), so each is covered or named as excluded.
- **Done** in the commit "B30-B31: text-reading proofs and look-alike bugs" (`class:`, `lookalikes()`; tests `LookAlikes`; [DESIGN 5f](DESIGN.md)).


### 32. Verification in the background
- **Evidence:** the owner asking why work kept stopping while a suite of thousands of tests ran for about 20 minutes.
- **Outcome:** `odd done --background` returns at once and writes the verdict to the local evidence when it ends.

### 33. Inertness per hunk
- **Evidence:** a change made for a premise the data later disproved, reverted at the owner's request.
- **Outcome:** item R7 per changed hunk, not only per file.

### 34. `odd ship`: what is delivered is what was gated
- **Evidence:** release checks done by hand each time (tree equal to the gated tree, signer, app id, checksum).
- **Outcome:** `odd ship <artifact>` records the artifact's hash with the commit and that commit's gate verdict, and
  lists every check not run.
