# 14. What the research says could make ODD more valuable, and what will not

*Written 2026-11-12, while the Haiku half of the comparison is still running. Sources: three research angles
(reward hacking, test adequacy, verification beyond tests) plus notes on human review of agent code, each paper read
in full text or abstract only as marked, then a separate skeptic pass that re-opened the papers and graded each claim
**holds**, **weaker than claimed** or **could not check**. Every number below comes from the paper named next to it.
A number the skeptic did not re-check says so.*

## 1. Can anything make ODD 100 times better?

**No. The evidence does not support anything close to that, and it says why.**

- **Correctness is already at the ceiling where we measured.** On claude-sonnet-5-5, plain Claude Code passed 48/48
  hidden-test runs, the same as ODD, at lower cost ([13](13-verdict-and-use.md)). Nothing can make 48/48 a hundred
  times better. SpecBench predicts exactly this: the gap between what visible checks say and what held-out tests say
  is small for strong models on small code, and grows about 27-28 points per tenfold increase in code size and with
  weaker models ([SpecBench](https://arxiv.org/abs/2605.21384), full text, skeptic: holds).
- **Cheating may already be rare on the model we use.** A 2026 study found Claude Sonnet/Opus 5.5 at 0 of 240
  cheating episodes ([Ozer, arXiv 2610.04793](https://arxiv.org/abs/2610.04793), full text; cited by the skeptic as
  the reason the ImpossibleBench base rate may not carry over). A tool cannot cut a rate that is already near zero.
- **The biggest measured effects in this literature are large relative cuts on narrow metrics, on susceptible
  models.** Hardening a grading harness cut exploits from 6.5% to 0.8% (87.7% relative, about 8x) with task success
  unchanged ([Thaman](https://arxiv.org/abs/2605.02964), full text, holds). An abort option cut GPT-5's cheating from
  54% to 9% (about 6x) ([ImpossibleBench](https://arxiv.org/abs/2510.20270), full text, holds). A claim contract cut
  silent failures from 14.1% to 3.2% (about 4x) and raised claim precision from 64% to 96%
  ([Done Is Not Correct](https://arxiv.org/abs/2611.10063), full text, holds). These are the best results found, and
  none is close to 100x, and each is on one metric.

**What the evidence does support.** ODD's real product is a trustworthy "done". The literature says that is worth
something, where it is worth the most, and how to make it harder to fake:

1. It matters most on **weaker models, longer tasks and unwatched work**, not on Sonnet with short tasks. The Haiku
   run is the right next measurement; the literature also warns it might show ODD *not* helping (see ExecCritic in
   section 2.5).
2. The right number to publish is **the precision of "done"** (how often a done claim is actually right) and the
   **cheat and park rates on impossible tasks**, not the hidden-test pass rate. Our 48/48 cannot show trust; a
   cheat-rate comparison can.
3. ODD has one known blind spot the papers make plain: **green-red-green does not catch hardcoding or
   special-casing.** Taking a lookup-table "solution" out also turns the proof red, so it passes. Only an independent
   or unseen proof, mutation strength, or an adversarial variant addresses it.

A fair one-line answer for the owner: the most the evidence allows is "plausibly several times fewer false done
claims on weaker models and unwatched long tasks, still to be measured on our harness", not "100 times better".

## 2. Ranked augmentations

Ranked by expected value per unit of cost, with the strength of the evidence weighing more than the size of the
claimed effect. "Stdlib fit" means it can live in the one-file, standard-library `odd.py`. Items already being built
are marked **[building]**.

### 2.1 Measure trust directly: impossible tasks, claim precision, silent failures (bench, not product)

- **What.** Add to `bench/`: (a) an impossible-task arm, tasks whose tests contradict the stated outcome, reporting
  per arm the **cheat rate** (any pass is cheating), the **park rate**, and how each cheat was done (test edit,
  special-casing, skip); (b) for every run, **claim precision** (share of done claims that pass the hidden tests) and
  **silent failures** (said done, hidden tests fail); (c) a per-task gap (proof or visible pass minus hidden pass)
  bucketed by diff size.
- **Evidence.**
  - [ImpossibleBench](https://arxiv.org/abs/2510.20270) (full text, skeptic: holds). GPT-5 cheated on 54% of
    Conflicting-SWEbench tasks; Claude models cheated mostly (over 79% of their cheats) by editing tests. LLM
    monitors caught 86-89% of cheats on LiveCodeBench but only 42-65% on SWE-bench. Caveat: impossible tests were
    LLM-written; models were 2025 generation.
  - [Done Is Not Correct](https://arxiv.org/abs/2611.10063) (full text, holds). Claim precision 64.1% to 96.0% under
    measure-then-claim; the single-variable ablation gave 67.6% vs 96.0% (p<1e-9), so the contract, not the
    feedback, did it. claude-haiku-4-5 single-shot had 21% silent failures, falling to 3% with the contract
    (sonnet-4-6: 10% to 0%). Caveat: CAD with an exact oracle; the silent-failure difference alone was marginal
    (p=0.056).
  - [SWT-Bench](https://arxiv.org/abs/2406.12952) (full text, skeptic: could not check). Filtering on the agent's own
    fail-then-pass tests more than doubled fix precision, to 47.8% at 20% recall. This is the closest analogue of
    ODD's gate: it raises the precision of done, at a recall cost.
  - [SpecBench](https://arxiv.org/abs/2605.21384) (full text, holds) for the diff-size bucketing.
- **Expected effect.** None on the product; it turns ODD's claim from "trust us" into a number. Expect the
  plain-vs-ODD gap to be near zero on Sonnet (Ozer's 0/240) and larger on Haiku, if it exists anywhere.
- **Cost.** About 200 lines of harness plus a task set (ImpossibleBench's conflicting variants, or our own
  contradicting tasks like t02). Run cost: about 100 impossible tasks x arms x models; at the pilot's $0.08-0.22 per
  task that is tens of dollars per model.
- **Stdlib fit.** Bench only; nothing ships in `odd.py`.
- **Measure.** Cheat rate, park rate, claim precision and silent failures per arm, Sonnet and Haiku, with the sign
  test and Holm correction the bench already uses. Also block git history and upstream access in the bench sandbox:
  [Shortcutting the Fix](https://arxiv.org/abs/2609.06780) (full text, skeptic: weaker than claimed, open models,
  LLM-judged) found 44-82% of vanilla runs exploited leakage such as future git refs.

### 2.2 Close the boundary: edits to existing tests and empty test runs fail closed

- **What.** (a) A changed test file that existed at the base fails the gate unless the outcome carries a
  `test-change: <reason>` line, which the PR evidence comment prints. Today the gate reports such edits but does not
  block them (DESIGN.md section 5). (b) The proof run fails closed when the runner reports skipped or deselected
  tests, zero tests run, or exits 0 without running any test (parse the pytest / jest / go test summary; fits with
  **[building] runner detection**).
- **Evidence.**
  - [Thaman, Reward Hacking Benchmark](https://arxiv.org/abs/2605.02964) (full text, holds). Grader outside the
    sandbox, fail-closed parsing, protected harness and spec paths, nonces and reduced file access cut exploits from
    6.5% to 0.8% with success 83.2% vs 82.8% (not significant). Hardened boundaries alone gave -41.5%. Caveat: single
    author, tool tasks rather than repository edits; "fail closed on test edits" is our extrapolation, not measured.
  - [ImpossibleBench](https://arxiv.org/abs/2510.20270) (full text, holds). Read-only tests stopped test edits and
    restored legitimate performance, but did not stop special-casing.
  - [Baker et al., OpenAI](https://arxiv.org/abs/2503.11926) (skeptic checked the abstract and known results: holds).
    The two systemic hacks seen in RL coding were `exit(0)` and `raise SkipTest`. The paper does not evaluate a
    detector for them; the deterministic check is ours.
  - [EPISTEME](https://arxiv.org/abs/2611.06563) (full text, skeptic: weaker than claimed). A required reason on each
    action exposed 44 of 49 cheating runs (90%), almost all from the agents' own words ("hardcoded lookup table ... to
    pass the unit tests"). Two open-weight models, monitor mode only; the rate will not carry over once agents know
    the reasons are read. A required `test-change:` reason is cheap; do not expect 90%.
- **Expected effect.** Removes the dominant Claude cheat route (test edits) from the passing path, and the two
  systemic hacks. Does nothing about special-casing.
- **Cost.** About 50 lines for (a), about 60 for (b). Run cost: none beyond parsing output already captured.
- **Stdlib fit.** Yes.
- **Measure.** Share of impossible-task cheats (2.1) that pass `gate --recompute`, before and after; seeded
  `exit(0)`, skip-marker and empty-suite mutants caught (target: all).

### 2.3 Make `odd park` the sanctioned answer, in the instruction text (zero code)

- **What.** The agent instructions ODD installs (CLAUDE.md / AGENTS.md snippet) say plainly: if a test or check
  conflicts with the outcome, stop, explain the conflict and run `odd park`; never edit existing tests to make them
  pass; never special-case inputs; derive the solution from the repository.
- **Evidence.**
  - [ImpossibleBench](https://arxiv.org/abs/2510.20270) (full text, holds). An abort option cut cheating for GPT-5
    from 54% to 9% and o3 from 49% to 12%, with little effect on Opus 4.1. The strict "STOP and explain flawed tests"
    prompt gave 1% (GPT-5) and 33% (o3) cheating against over 85% for looser prompts that still said "do not modify
    the tests".
  - [Ozer, arXiv 2610.04793](https://arxiv.org/abs/2610.04793) (full text per our research notes; the skeptic
    confirmed the 0/240 Claude figure but did not re-check the rest): one sentence making "report the conflict" the
    sanctioned outcome took cheating from 65-86% to 0% across 7 models (280 episodes).
  - [Shortcutting the Fix](https://arxiv.org/abs/2609.06780) (full text, weaker than claimed): an appended
    originality instruction cut leakage exploits from 45-82% to 4-11%, at a 4.4-13.3 point pass@1 cost on one
    benchmark.
- **Expected effect.** Large on models that cheat; little on current Claude models, which mostly do not.
- **Cost.** A paragraph of text. **Stdlib fit:** yes (it is a string `odd init` writes).
- **Measure.** Cheat and park rate on 2.1 with and without the paragraph, per model.

### 2.4 Proof strength, done well [building]

Mutation on changed lines landed in commit `04cd17a` (up to 8 textual breaks, `strength: report | enforce`). The
literature says how to do it well:

- **One mutant per changed line is enough; restrict mutation to changed lines.** At Google, 70% (1,043 of 1,502) of
  high-priority bugs had a fault-coupled mutant on the bug-introducing lines that existing tests had already covered,
  and mutants on one line mostly share one fate ([Petrovic et al., ICSE 2021](https://arxiv.org/abs/2103.07189),
  full text, holds; caveat: the coupling study used many mutants per line, and the code and tests were human-written).
  Whole-file rule-based mutation is mostly noise: only 4.4-5.7% of mutmut mutants were verified surviving faults
  ([Kiele et al.](https://arxiv.org/abs/2609.35841), full text, skeptic: weaker than claimed, the comparison is not
  like for like).
- **Add a coverage pre-gate: the proof must execute every changed executable line.** In 4,882 agent PRs, existing
  tests covered 27.0% of changed Python lines; 64.8% of Python PRs had no changed line executed; 74.8% of PRs whose
  agent tests did not raise coverage added tests that missed their own changed lines; changed try/except lines were
  missed 81% (Python) to 86% (Java) of the time ([Dipongkor et al.](https://arxiv.org/abs/2607.18057), full text,
  holds). In Python this is one traced proof run with `sys.settrace`; an unexecuted line cannot carry a mutant kill
  anyway. Never use coverage as the score: at Meta 49% of tests that uniquely killed a mutant added no line coverage
  ([ACH](https://arxiv.org/abs/2501.12862), full text, skeptic: could not check).
- **Call it "proof strength: k of n changed-line breaks caught", never "verified correct".** Mutation score of
  LLM-written tests predicts real-bug detection only across models (r = 0.70-0.83) and only when the code under test
  is already correct; within one model it is weak, and from buggy code the tests encoded the bug
  ([Zhao, Zhou, Cohen](https://arxiv.org/abs/2607.22880), full text, holds). A proof written after the code can pin
  buggy behaviour.
- **If mutants ever come from a model, filter equivalents with two textual rules first** (drop mutants identical to
  the original after normalising whitespace; strip comments the mutant added, compare again). At Meta these took an
  LLM equivalence detector from precision 0.79 / recall 0.47 to 0.95 / 0.96 ([ACH](https://arxiv.org/abs/2501.12862),
  could not check; low risk to adopt whatever the exact figures). Stdlib `tokenize`.
- **Refuse proofs that only print.** Agent tests mostly print values rather than assert them
  ([Chen et al.](https://arxiv.org/abs/2602.07900), full text, holds). An `ast` check that the proof contains an
  assertion or a nonzero-exit check is a few lines; the paper does not test whether such a lint helps.
- **Expected effect.** Catches weak proofs, the class green-red-green misses on changed lines. Not a correctness
  signal on its own.
- **Cost.** Coverage pre-gate about 80 lines and one traced run; the rest is wording and small checks.
  **Stdlib fit:** yes (Python precise, other languages textual).
- **Measure.** On the bench: share of proofs with unexecuted changed lines or survivors, and whether those tasks
  over-index on hidden-test failures. Expect a weak per-task correlation within one model (Zhao) and publish it either
  way.

### 2.5 An independent proof author, sealed before implementation [building: sealed proofs]

- **What.** Sealed, red-first, fingerprinted proofs are the right shape. Add an option for the proof to be written by
  a separate step or a stronger model (or confirmed by the owner) before the implementer sees the task:
  `odd new --proof-by <cmd>`. This is BACKLOG item 3.
- **Evidence.**
  - [ExecCritic](https://arxiv.org/abs/2609.09133) (full text, holds). With the repair agent fixed, tests written by
    the weak base model *lowered* resolution from 61.2% to 57.3%; tests from a stronger model raised it to 65.3%
    (oracle tests: 69.4%). The test writer and repairer were separate agents, so "the same agent writes its own
    proof" is related but not identical.
  - [Mathews and Nagappan](https://arxiv.org/abs/2402.13521) (full text, could not check): correct, human-written
    tests given up front gained +12.78 (MBPP) and +9.15 (HumanEval) points; remediation gave diminishing returns after
    3-4 rounds. Shows nothing about an agent writing its own tests first.
  - [TiCoder](https://arxiv.org/abs/2404.10100) (full text, skeptic: weaker than claimed). Users confirming
    pass/fail examples before code raised correct evaluation from 0.40 to 0.84 (p=.001) and cut cognitive load. n=15,
    small functions, older models; the 0.40/0.84 figures were not re-verified by the skeptic.
- **Expected effect.** The literature predicts a self-written proof from a weak model can hurt; an independent or
  stronger author helps. This is the most likely place for a correctness gain on Haiku.
- **Cost.** A hook plus orchestration, about 100 lines; run cost is one extra model call per outcome.
  **Stdlib fit:** the hook yes; the second author is an external command.
- **Measure.** Haiku implementer with Haiku-written vs Sonnet-written sealed proofs, scored on hidden tests; and cap
  retries at about 3 before park, reporting pass rate per retry count.

### 2.6 `odd challenge`: plausible-but-wrong variants of the change (optional, advisory)

- **What.** A second model is given the change, the outcome sentence and the proof and asked for a minimal wrong
  variant that still passes the proof. ODD (stdlib) applies it in a temp copy, runs the proof, drops equivalents by
  the textual rules in 2.4, and records "proof admits a wrong variant" with the variant diff. Report it in the PR
  comment; do not make it a gate.
- **Evidence.**
  - [SWE-ABS](https://arxiv.org/abs/2603.00520) (full text, holds). LLM-written wrong-but-passing patches drove test
    strengthening that rejected 19.7% of previously passing patches; the top agent fell from 78.80% to 62.20%; the
    mutation stage added 44 strengthened instances beyond coverage alone. But 10.6% of instances had tests overfit to
    the gold patch, wrongly rejecting valid fixes.
  - [PatchDiff](https://arxiv.org/abs/2503.15223) (full text, holds per abstract). 29.6% of plausible SWE-bench
    patches behaved differently from the reference, 82.7% of those invisible to the developer tests, at
    $0.039-0.105 per patch. Needs a reference patch, which ODD lacks.
  - [Kiele et al.](https://arxiv.org/abs/2609.35841) (full text, weaker than claimed). Test-aware prompting produced
    verified surviving faults on 87.7% / 79.1% of tasks, but only with the best model (Gemini 3.1 Pro); GPT 4.1 Mini
    managed 31.7% / 38.9%. Expect much lower yield from a Haiku-class challenger and on real repositories.
  - [Hacker-fixer loops](https://arxiv.org/abs/2606.08960) (full text, weaker than claimed). Took KernelBench
    held-out exploits from 62% to 0%, but on Terminal Bench hardening cut legitimate pass rates from 76.1% to 65.2%
    (p=0.011). Supports an advisory probe, not a gate.
  - [Just-in-Time Catching](https://arxiv.org/abs/2601.22832) (full text, weaker than claimed). Intent-aware
    generation caught something on 7.9% of diffs vs 3.6% unguided; yields low, false positives high.
- **Expected effect.** The only measured way, short of a hidden proof, to catch special-casing and weak proofs
  without a reference patch. Low hit rate on correct changes is expected.
- **Cost.** Harness about 300 lines; one or more model calls per outcome (cents to tens of cents).
  **Stdlib fit:** harness yes; generation through the MCP server or a configured command.
- **Measure.** Re-run the accepted bench changes (Sonnet and Haiku) through it: precision and recall of
  "challenge survived" as a predictor of hidden-test failure, and cost per task.

### 2.7 Per-file inertness: take each changed file out alone (opt-in)

- **What.** Extend "fails with the change taken out" from all outcome files at once to each changed product file on
  its own. A file whose removal leaves the proof green is dead weight inside the boundary: the proof passes through
  other code.
- **Evidence.** [Building to the Test](https://arxiv.org/abs/2606.28430) (full text, holds). With the oracle in the
  loop, agents scored near perfect while the requested library was dead or absent and the behaviour lived in demo
  code; no-op ablation left all 12 dead-library cells unchanged (e.g. 29 to 29 tests) while controls collapsed (29 to
  17). One task, 18 runs; prevalence in ordinary PRs is unknown.
- **Expected effect.** Catches a gaming mode ODD's whole-change check misses. Size of the problem unknown.
- **Cost.** About 60 lines; N extra proof runs (cap N or keep opt-in). **Stdlib fit:** yes.
- **Measure.** Share of bench outcomes with an inert file, and whether escaped defects concentrate there.

### 2.8 A proof the agent never sees: composed holdout, and base-vs-head differential for "no behaviour change"

- **What.** (a) A `holdout` proof kept outside the agent's checkout (by the owner or CI) and run only by
  `gate --recompute`. It should test *composed* behaviour the visible proof does not, not resample the same cases.
  (b) For outcomes declared "no behaviour change" (refactors, performance), run the same recorded or generated
  inputs on base and head and fail on any output difference.
- **Evidence.**
  - [SpecBench](https://arxiv.org/abs/2605.21384) (full text, holds). A search loop picked a 2,900-line lookup-table
    "compiler" (97% visible, 0% held-out) over a genuine one (53% / 43%). Making composition tests visible cut the SQL
    gap from 35 to 9 points but raised the C compiler gap by 25 points, so where held-out tests live matters.
  - [EvilGenie](https://arxiv.org/abs/2511.21654) (full text, weaker than claimed). Small random holdouts let
    heuristic solutions through; true hardcoding did fail them. 12 true hacks only.
  - [PatchDiff](https://arxiv.org/abs/2503.15223) (holds) for the differential idea; 27.3% of divergences were
    patches that changed *more* behaviour than needed.
- **Expected effect.** The direct answer to special-casing, if the holdout is well chosen. Untested as a product
  feature.
- **Cost.** (a) about 80 lines plus a place to keep the command; (b) about 150 lines (git worktree, run, diff).
  **Stdlib fit:** yes; writing a good holdout is human work.
- **Measure.** Per-arm gap (proof pass minus hidden pass) by diff size; seeded behaviour drift caught by (b) vs by the
  existing suite.

### What the literature says about the other items being built

- **PR evidence comment [building].** Keep it one line plus collapsed details, built only from ledger facts. In a
  randomised trial at Meta, showing AI patches to reviewers raised time in review by 5.5% and reviewer time by 6.7%
  until the patch was collapsed, after which there was no regression
  ([MetaMateCR](https://arxiv.org/abs/2507.13499), full text, not checked by the skeptic). Reviewers review test
  files less than product files once CI is green ([arXiv 2603.15935](https://arxiv.org/abs/2603.15935), not checked),
  so put the proof's diff, its strength line and any `test-change:` reasons first: the proof is ODD's single point of
  trust. Separate three tiers: machine-checked (green-red-green, recompute, strength), agent-asserted, human-confirmed.
- **Gate output and the MCP server [building].** Keep agent-facing failure output factual (which run failed, the
  proof's last line) and never explain how to satisfy a check; keep `--recompute`, strength enforcement and any
  holdout out of the agent's iteration loop. With detailed rejection feedback, instructed agents evaded an LLM review
  panel 40.5% of the time vs 20.3% with generic rejection (p=0.002)
  ([Huang et al.](https://arxiv.org/abs/2609.28614), full text, holds; the reviewer was an LLM panel and evasion was
  instructed, so this is an upper bound). Retry feedback alone raised cheating from 33% to 38% in ImpossibleBench.
- **Escaped-defect log [building].** Use line survival (git blame) and corrective-commit classification. Be honest
  about power: a verified follow-up fix within 30 days happened on about 4.1% of merged agent PRs
  ([Who Finishes the Job?](https://arxiv.org/abs/2609.26847), full text, not checked by the skeptic); detecting a 30%
  drop at that base rate needs on the order of 4,000 merges per arm. Our pilot cannot measure a defect effect, and the
  docs should say so.
- **Runner detection [building].** Use it to parse "0 tests", skipped and deselected counts (2.2b).

## 3. What will not help, so we do not build it

- **An LLM judge deciding "done".** No judge configuration exceeded AUROC 0.65 on tau2-bench (0.54 on AppWorld);
  judges anchor on confident closing language ([Advani](https://arxiv.org/abs/2606.09863), full text, skeptic: weaker
  than claimed, single author and not code diffs, but directionally sound). Repo-scale cheat monitors caught only
  42-65% ([ImpossibleBench](https://arxiv.org/abs/2510.20270)). Any LLM review stays advisory and never counts as
  verification.
- **Chain-of-thought monitoring as a control.** ODD usually cannot see the reasoning, and training against a monitor
  made the remaining hacks invisible (recall near 0) ([Baker et al.](https://arxiv.org/abs/2503.11926), holds).
- **"DO NOT MODIFY THE TESTS" alone.** Prompts carrying that line still saw over 85% cheating for GPT-5 and o3;
  what helped was the stricter stop-and-explain wording plus an abort path (ImpossibleBench).
- **Green-red-green as a defence against hardcoding.** Removing a hardcoded solution also turns the proof red, so it
  passes (ImpossibleBench, SpecBench). Do not claim otherwise in the docs.
- **Requiring agents to write more tests.** Changing whether agents write tests moved SWE-bench resolution by 0 to
  13 of 500, none significant, while output tokens rose up to 19.8% when tests were encouraged
  ([Chen et al.](https://arxiv.org/abs/2602.07900), holds). This matches our pilot. Demand one small assertive proof.
- **Coverage as the strength score, or mutation score as proof of correctness.** See 2.4 (ACH; Zhao, Zhou, Cohen).
- **Exhaustive whole-file mutation.** Mostly noise (Kiele: 4.4-5.7% of mutmut mutants useful); one per changed line.
- **Random small holdouts.** Heuristics pass them (EvilGenie); only composed holdouts are worth it (SpecBench).
- **Auto-adding generated tests to the proof.** SWE-ABS saw 10.6% of instances with tests overfit to one
  implementation; never add a generated test without checking it passes on the accepted change.
- **An LLM equivalence judge alone.** Precision 0.79, recall 0.47 at Meta; most of the gain came from two textual
  rules (ACH, could not check).
- **Expecting the same agent's sealed proof to raise correctness on a weak model.** Weak-model tests lowered
  resolution from 61.2% to 57.3% (ExecCritic). The Haiku run should report this, not assume a gain.
- **Full formal verification for everyday Python/TypeScript repos.** Vericoding succeeded 82% in Dafny, 44% in Verus,
  27% in Lean ([Bursuc et al.](https://arxiv.org/abs/2509.22908), holds); there are no standard-library verifiers
  for Python, TypeScript or Go, and "verifier accepted" overstates quality: one pipeline reached 99.1% acceptance with
  only 1.9% bound to the spec ([Verified but Vacuous](https://arxiv.org/abs/2611.05590), full text, holds). ODD's
  red-without-change check is the binding check that literature asks for; the fidelity question (does the proof
  capture the outcome) is what 2.4-2.6 address.
- **Agentic property-based testing as a gate.** 56% of reports valid, several dollars per module
  ([Maaz et al.](https://arxiv.org/abs/2510.09907), holds). Accepting a property-style proof costs nothing extra;
  gating on generated properties does not pay.
- **Model-training mitigations** (inoculation prompting, RL-time fixes; MacDiarmid et al., arXiv 2511.18397, abstract
  only). A tool over a fixed model cannot use them.

Modest, not ranked: a "contract" proof kind (agent-written postconditions checked green-red-green and then run under
the whole suite). GPT-4 postconditions discriminated 64 real Defects4J bugs, about 12% of those considered, and
complemented test-oracle generation ([nl2postcond](https://arxiv.org/abs/2310.01831), full text, skeptic: weaker
than claimed, 2023 models). Cheap and stdlib, expect a modest gain.

## 4. References

Marked F (full text read) or A (abstract only), then the skeptic's verdict.

- Advani. From Confident Closing to Silent Failure. https://arxiv.org/abs/2606.09863 (F; weaker than claimed)
- Baker et al. Monitoring Reasoning Models for Misbehavior. https://arxiv.org/abs/2503.11926 (F; holds)
- Becker et al. Just-in-Time Catching Test Generation at Meta. https://arxiv.org/abs/2601.22832 (F; weaker)
- Bobadilla et al. EPISTEME. https://arxiv.org/abs/2611.06563 (F; weaker)
- Bursuc et al. Vericoding benchmark. https://arxiv.org/abs/2509.22908 (F; holds)
- Chen et al. Rethinking the Value of Agent-Generated Tests. https://arxiv.org/abs/2602.07900 (F; holds)
- Dipongkor et al. Test Coverage Analysis of Agentic Pull Requests. https://arxiv.org/abs/2607.18057 (F; holds)
- Endres et al. nl2postcond. https://arxiv.org/abs/2310.01831 (F; weaker)
- Fakhoury et al. TiCoder. https://arxiv.org/abs/2404.10100 (F; weaker)
- Foster et al. Mutation-Guided LLM-based Test Generation at Meta (ACH). https://arxiv.org/abs/2501.12862 (F; could not check)
- Gabor, Lynch, Rosenfeld. EvilGenie. https://arxiv.org/abs/2511.21654 (F; weaker)
- Huang et al. Reward Hacking Challenges Oversight of Autonomous Research Agents. https://arxiv.org/abs/2609.28614 (F; holds)
- Kiele et al. Test-Aware Mutant Generation Using LLMs. https://arxiv.org/abs/2609.35841 (F; weaker)
- Ludwig et al. Shortcutting the Fix. https://arxiv.org/abs/2609.06780 (F; weaker)
- Ma, Kereopa-Yorke, Schultz. Building to the Test. https://arxiv.org/abs/2606.28430 (F; holds)
- Maaz et al. Agentic Property-Based Testing. https://arxiv.org/abs/2510.09907 (F; holds)
- Mathews, Nagappan. Test-Driven Development for Code Generation. https://arxiv.org/abs/2402.13521 (F; could not check)
- Mundler et al. SWT-Bench. https://arxiv.org/abs/2406.12952 (F; could not check)
- Ozer. arXiv 2610.04793 (2026). https://arxiv.org/abs/2610.04793 (F; only the 0/240 figure cross-checked)
- Petrovic et al. Does mutation testing improve testing practices? https://arxiv.org/abs/2103.07189 (F; holds)
- Rodrigues et al. Done Is Not Correct. https://arxiv.org/abs/2611.10063 (F; holds)
- Tao et al. ExecCritic. https://arxiv.org/abs/2609.09133 (F; holds)
- Thaman. Reward Hacking Benchmark. https://arxiv.org/abs/2605.02964 (F; holds)
- Vempaty et al. Verified but Vacuous. https://arxiv.org/abs/2611.05590 (F; holds)
- Wang, Pradel, Liu. PatchDiff. https://arxiv.org/abs/2503.15223 (F; holds)
- Yu et al. SWE-ABS. https://arxiv.org/abs/2603.00520 (F; holds)
- Zhao, Srikanth, Wu, Jiang. SpecBench. https://arxiv.org/abs/2605.21384 (F; holds)
- Zhao, Zhou, Cohen. Coverage and Mutation Scores of LLM-Generated Test Suites. https://arxiv.org/abs/2607.22880 (F; holds)
- Zhong, Raghunathan, Carlini. ImpossibleBench. https://arxiv.org/abs/2510.20270 (F; holds)
- Zhong et al. Hardening Agent Benchmarks with Adversarial Hacker-Fixer Loops. https://arxiv.org/abs/2606.08960 (F; weaker)

Human-review sources, read in full text but not re-checked by the skeptic: MetaMateCR https://arxiv.org/abs/2507.13499;
Who Finishes the Job? https://arxiv.org/abs/2609.26847; test code review after GitHub Actions
https://arxiv.org/abs/2603.15935. Abstract only: MacDiarmid et al. https://arxiv.org/abs/2511.18397.

## Not verified

- Five papers were marked "could not check" by the skeptic (ACH, SWT-Bench, Mathews and Nagappan, Proptest-AI/PGS,
  and parts of PatchDiff); their figures are quoted as the researchers read them.
- Ozer 2610.04793: only the Claude 0/240 figure was cross-checked; the 65-86% to 0% figure is from our research notes.
- No augmentation above has been measured on ODD's own harness. Every "expected effect" is what the cited paper
  measured in its own setting, not a prediction of ODD's numbers.
