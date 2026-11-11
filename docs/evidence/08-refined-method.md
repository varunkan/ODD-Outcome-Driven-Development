# Outcome-Driven Development (ODD)

A lean method for building software with coding agents. It was distilled from 1,856 instructions given while building a production multi-device point-of-sale system (Aug-Nov 2026), after measuring which ones paid.

## The idea in four sentences

1. Start from one user-visible outcome and one end-to-end proof.
2. Trust a proof only after it has been seen to fail, and keep it out of the implementer's reach.
3. Let scripts and content-hashed evidence decide "done"; keep the few no-exception rules in code and the irreversible acts with the human.
4. Measure the method itself, and delete what does not pay.

## How to read the evidence

Each principle carries a grade:

- **Before/after**: a measured comparison. All are single instances measured by the session that made the change.
- **Measured waste**: the cost of not having the rule is counted; the rule's own saving is not.
- **Incident**: the rule prevents a recorded failure class; no number.
- **External**: published research or vendor guidance, not this project.

Only three results have a real before/after: invariant batching (17x on one instance), scripts instead of agents (about 4 minutes against 106 agents), and device checks as code (about 450 tool calls against about 8, on 13 of 57 convertible legs). Outcome-first has one strong data point (about 2 hours against 14). Everything else is graded lower and says so.

## The principles, strongest evidence first

### 1. One outcome, one proof (before/after, one instance)
Write one user-visible outcome sentence and one end-to-end test that asserts it. Trace the path on the current tree, fix only what blocks it, and stop when it is proven. Anything else you find is one backlog line and becomes the next outcome. For a defect, keep one short record: wrong behaviour, correct behaviour, test, result, content hash. Add plan or design documents only when risk or size requires.

*Evidence:* about 2 hours to a host proof against 14 hours, 81 agents and 23 send-backs in 30 verdicts for the full multi-stage swarm. 90th-percentile lead time to merge fell from 133 h to 11.7 h (observational).

### 2. Commands for mechanical questions, agents for judgement (before/after)
If a command can answer it (counts, diffs, greps, git facts, rule-decided verdicts), write the command. Run one script over a whole backlog and look at the distribution before working items one by one. Write device, UI and end-to-end checks as committed tests; name the ones that cannot be converted.

*Evidence:* 106 agents on 53 branches were killed with no answer; one script answered in about 4 minutes and found 44 blocked by a single cause.

### 3. Change the shape of the work, not the amount of checking (before/after)
- One branch closes every open item that is an instance of the same invariant.
- A script sets the amount of process from the risk of the diff.
- While working, run only the tests that can observe the change; cheap checks first.
- Run the full gate once per merge batch, on the exact tree that will land.

Added checks buy caught defects, not speed.

*Evidence:* 4 items for about 200k tokens against about 3.4M done separately; 20 items gated alone took 4 h against 12 min shared.

### 4. Measure the method; keep the instruction set small (measured waste)
State the number a process change should move before making it, measure after on real work, and remove the change if it did not pay. Record cost per outcome by script, as context tokens read. Keep one short always-loaded file of facts the model cannot infer, under a size budget a script checks. A rule enters with its incident and a date, lives in one place, and is deleted when a script covers it. When a defect escapes, add the check, not a paragraph.

*Evidence:* 74% of one run's 338M tokens read was always-loaded instructions; a scripted budget cut the file from 101 KB to 32 KB where a prose cap had failed. The token saving from the cut was never measured.

### 5. Bound every unattended run in code (measured waste)
The workflow script caps agents or tokens and hands back to the human when the cap is spent. The harness decides whether a loop made progress. Rework has a round limit and never passes by default. Limit work in progress. Never spend model turns waiting on a machine.

*Evidence:* about 130 agents spent with no passing verdict; 29M tokens on continuations that changed only a note; 24.6M tokens read by agents whose only answer was "pending".

### 6. Enforce few rules, in code, and test the enforcers (measured waste)
Rules with no exceptions get a hook, gate or test; preferences stay prose. A rule broken twice is enforced, rewritten or deleted, never restated. Each enforcer is product code: a planted violation turns it red, it fails open on its own errors, it has a logged override, and one command confirms it is installed. A gate nobody can pass is repaired or removed.

*Evidence:* across 294 agents every rule was written down and still broken. One guard miscounted by a factor of 1.94 for four weeks behind a green test suite.

### 7. A contract and an honest exit for every unit of work (external)
Acceptance criteria are a short list; each names an observable, a number where one applies, and the check that reads it. Each dispatch ends done, incomplete or blocked, and the last two are acceptable. A criterion no run can satisfy is itself the defect: correct it on record, never waive it.

*Evidence:* an explicit "this is impossible" option cut one model's cheating from 54% to 9% on a benchmark. Fifteen unsatisfiable criteria surfaced in one test window here.

### 8. Keep the proof out of the implementer's reach (external)
Proof tests, gate scripts, thresholds and the done-ledger are not writable by the agent doing the work. Only a script writes "done". Only the owner relaxes a check, on record.

*Evidence:* telling a model not to cheat changed nothing (80% to 80%); hiding the tests drove cheating near zero. In an audit, forged ledger lines turned a failing gate green.

### 9. A proof must be able to fail (incident)
Run every proof on the unfixed tree first. On high-risk changes, delete each added guard by script and require a test to go red. Test the path production uses and name every fake. The test battery validates itself with an unmutated control.

*Evidence:* eight guards could each be deleted with the suite green; a one-character change to a collection name left 1,957 tests and every gate green. Mutation misses about 17% of real faults, so it is a bar, not a guarantee.

### 10. Evidence belongs to the content it ran on (incident)
Record each result with a hash of the product content, not the commit id. Cite it while the content is unchanged; discard it when the content changes. A check has three results: pass, fail, could not run. The merge gate is one local command on the merge tree. Reports list what was run and what was not.

### 11. Decide from the tree, not from a report (incident)
Every cited path, count or list comes from a command run in this pass. A claim of "every" or "only" carries its query. Fix the class, not the instance. Search for existing code before writing new code. State the root cause and confirm the mechanism runs before fixing.

### 12. Simulation gates; the real system proves (incident)
Label each proof as real or simulated. Call an outcome proven, and release, only after one run on the real system with the shipping artifact. Confirm by checksum that what was tested is what was built. For shared state, compare the data in every replica.

*Evidence:* the one real-backend run on record failed on an error no fake produced.

### 13. Scripts first, then one independent reviewer (incident)
One fresh-context, read-only reviewer who did not write the change checks the outcome, verifies load-bearing claims itself, reports everything in one pass, and sends work back only for a reproduced product defect. A second review only for high-risk classes.

### 14. Isolate parallel work (incident)
One writer per file and per worktree, computed, not assumed. No shared mutable state between agents. One coordinator composes shared files. One machine-wide lock caps heavy runs.

### 15. State lives in the repository (incident)
Commit what a later session must read. Derive boards from git and one append-only ledger. On resume, the repository wins over prose.

### 16. Human-owned acts stay human-owned (incident)
Name the owner's acts once: credentials, billing, deploys, release, production deletion, anything irreversible, relaxing a rule. The agent decides everything reversible and continues. Automation touches only disposable accounts, fails closed on a live target, and never disturbs an environment in use. Bulk writes are staged.

### 17. Main is production; history is recoverable (incident)
Every change is a branch through the gate. Tag before any destructive git operation. Stage explicit paths. One owner pushes; pushed history is not rewritten.

### 18. Tunable defaults, not rules (model workarounds)
These ship as settings, loose or off by default:

| Default | Compensates for |
|---|---|
| Locate before reading a large file | context cost |
| One deliverable per dispatch, no fixed budgets | short reliable horizons |
| A code index only locates, never proves | search cost |
| A one-page list of test traps | test-design gaps |
| No hard-coded model id | model retirement |

**Retirement test:** at each model upgrade, run the same outcome with the default off. If the proof, escaped defects and cost per outcome hold, delete it.

## What the method adds beyond the source rules

- A mutation step on every proof, as the quality signal.
- A periodic real-system run that calibrates the simulation, with escaped defects recorded as its error rate.
- A "cannot be done as specified" exit on the outcome itself.
- Control files only the tool can write, with a hash-chained ledger.
- A human-labelled set of past verdicts to calibrate the reviewer, which may answer "unknown".
- An expiry step on every learned rule.
- Method on-versus-off runs, reported as lead time, change failure rate, rework rate and cost per outcome.
- A small-change lane: one outcome block, red, code, green, done.

## What was dropped

Of 224 rule clusters, 145 survive in the principles above, 48 were duplicates, and 31 were dropped:

| Class | Clusters | Reason |
|---|---|---|
| Step micro-management (call caps, read windows, timed steps, task graphs) | 7 | The only real data shows higher cost |
| Fixed role relays and specification ceremony | 4 | No measured payoff; measured cost |
| Layered LLM judging | 4 | 23 send-backs in 30 verdicts, most naming no defect |
| Unmeasured tooling and habits | 5 | Failed the measure-or-remove rule |
| Project-specific content | 7 | Belongs in the project's own rules |
| Prose restatements with no incident | 4 | Covered by a script or a default |

## Known limits

- Most figures are single instances measured by the session that built the change.
- The central product outcome was never observed on the real system end to end.
- Hook effectiveness has no before/after: the failure of prose is measured, the effect of enforcement is not.
- Project total token spend was never recorded.
- No comparison run against Spec Kit, BMAD or Superpowers exists yet; any comparative claim needs the same task run through each with cost and escaped defects recorded.
- Five figures could not be verified in the records and must be re-cited or removed before publication: the "18 judge rounds, about 12M tokens" figure, a 22.2M-token read projection, the pinned-model incident, a 6.3M-token audit figure, and the peak instruction-file size (95 KB or 101 KB).

---

*This is the method as refined by the validation (see [07](07-validation-and-verdict.md)); the decision there is to teach about seven of these principles and keep the rest as reference. Each principle below traces to the rule clusters in [09](09-rulings.md).*

## Trace: principle to rule clusters

| principle | durability | carried by | rule clusters |
|---|---|---|---|
| P1 | durable | Script: the runner refuses a run without requirement, outcome, path and proof; a merge check lists files that trace to no outcome. Skill tex | OU-R1, OU-R2, OU-R3, OU-R4, OU-R20, PR-R43, PR-R42, DE-R40 |
| P2 | durable | Skill text plus a habit check at dispatch; a hook refuses hand-driven device input where a test runner exists. | FR1-R1, PR-R21, OU-R11, PR-R20, OU-R10, VE-R1 |
| P3 | durable | Scripts: tier-from-diff, file-overlap check, batch gate on the composed tree, red attribution; a test wrapper that scopes working runs. | PR-R16, OU-R19, PR-R17, DE-R12, PR-R37, SA1-R27, DE-R41, FR1-R13, VE-R2, VE-R28, DE-R7, PR-R22 |
| P4 | durable | Scripts: transcript cost ledger per outcome, size budget, a check that every named command and file exists. Habit: review-and-delete pass on | DE-R6, FR1-R18, FR1-R9, DE-R33, DE-R34, DE-R36, DE-R1, OU-R27, VE-R38, OU-R28 |
| P5 | durable | Workflow code (agent cap, progress test, round limit, can-finish check); a hook refusing sleep and poll loops; one health script that report | FR1-R22, PR-R5, DE-R30, DE-R31, PR-R6, FR1-R2, PR-R3, PR-R23, PR-R15 |
| P6 | durable | Hooks and gate scripts, each with fixture tests that replay real transcripts; a session-start doctor command. | DE-R2, DE-R3, FR1-R24, VE-R14, VE-R4, DE-R4, SA1-R9, SA1-R13, SA1-R12, PR-R34 |
| P7 | durable | Schema on step results (three end states); a script checks that criteria exist and each names a check; preflight script with an exit code. | PR-R1, OU-R24, DE-R29, OU-R12, OU-R13, DE-R23, PR-R18, PR-R19 |
| P8 | durable | Hook (deny edits to gate, proof and control paths, including shell write routes or an after-the-fact diff at gate time); done-script that ow | VE-R5, DE-R17, VE-R9, SA1-R10 |
| P9 | durable | Scripts: red-on-base run recorded with the proof, diff-derived mutation battery with self-validation, production-path check. | VE-R10, OU-R14, VE-R11, VE-R13, VE-R17, VE-R15, PR-R41 |
| P10 | durable | Scripts: evidence store keyed by content hash, three-state result parser, local gate runner, remote-ref check. | FR1-R12, PR-R36, VE-R6, DE-R20, VE-R8, DE-R21, VE-R3, SA1-R30, SA1-R31 |
| P11 | durable | Script: citation and name checker before review, completeness-claim check at commit, cross-branch overlap search as a gate step. Skill text  | OU-R6, OU-R7, OU-R8, VE-R7, VE-R16, PR-R32, PR-R27, PR-R25, PR-R24, DE-R24, DE-R25, DE-R38, OU-R16, OU-R17, OU-R18, VE-R31, VE-R32 |
| P12 | durable | Scripts: proof label (real or simulated) in the evidence record, artifact checksum preflight, replica comparison, visual launch check; one h | VE-R18, VE-R19, VE-R21, VE-R26, VE-R34, VE-R35 |
| P13 | durable | Script: prejudge checks before any reviewer is spawned; reviewer agent definition with read-only tools; skill text for the brief. | DE-R8, DE-R9, DE-R11, VE-R23, PR-R33, FR1-R7, PR-R30 |
| P14 | durable | Scripts: disjoint-file check at dispatch, worktree lease, machine-wide lock, bookkeeping merge resolver. | PR-R11, PR-R12, DE-R39, SA1-R22, VE-R27, PR-R4, SA1-R29 |
| P15 | durable | Scripts: checkpoint commit, ledger writer, derived board; pre-commit check for outside paths. | PR-R9, DE-R27, DE-R28, SA1-R26, SA1-R16 |
| P16 | durable | Hooks deny the destructive subset; fail-closed target guard in test and data scripts; refusing release script; skill text for the reversible | DE-R16, DE-R15, DE-R18, PR-R7, SA1-R8, SA1-R18, SA1-R20, SA1-R21, VE-R25, VE-R36, SA1-R6 |
| P17 | durable | Hook (main-commit block, sweep-add block); branch-retirement script; tool restrictions on workers for push. | SA1-R4, SA1-R1, SA1-R24, SA1-R25 |
| P18 | model-workaround | Config values with an optional guard; a one-line lint for pinned model ids; skill text. | FR1-R3, PR-R2, OU-R9, VE-R12, FR1-R23 |

## What the method should add (from the research)

- Proof strength as the quality signal: require a mutation step on every proof (revert or break the change and the proof must go red), not only on high-risk diffs' guards. Evidence: the draft toolkit accepted proofs such as 'test 1 = 1' and a free 'red: n/a' exit (audit.json failure_modes, missing); mutation, not coverage, measures fault detection, with the stated limit that about 17% of real faults couple to no mutant (practices.json).
- Real-system calibration of the simulation: a cheap periodic run on the real system with the shipping artifact, with every escaped defect recorded as the simulation's error rate. Evidence: the only real-backend run failed on a 403 no fake produced, #66 then removed the real device from the merge conditions with no measured cost or benefit, and no source read supports simulation-only proof (pos.json honest_assessment; practices.json lessons_for_odd).
- An honest abort exit beyond blocked: a 'cannot be done as specified' verdict on the outcome itself, treated as a success, with pressure to return done removed. Evidence: an abort option cut cheating from 54% to 9% on an ImpossibleBench variant (practices.json); the repo has no measurement of its own three-state rule.
- Tamper resistance for control state: split agent-writable outcome files from control files (ledger, config, active pointer), let only the tool write the latter, hash-chain ledger entries, and detect out-of-boundary edits by diff at gate time so shell write routes are covered. Evidence: forged ledger lines turned a failing gate green and Bash writes bypassed the guard (audit.json, measured).
- Judge calibration: keep a small human-labelled set of past verdicts, score the reviewer against it, and allow an 'unknown' verdict. Evidence: 23 REVISEs of 30 verdicts with most naming no product defect; eleven rulings wrong for lack of checking; 733 rulings in 44 days; vendor guidance to calibrate LLM judges against humans (pos.json; practices.json).
- Rule expiry: every learned rule carries a date, its triggering incident, its scope and reason, and a review-or-expire step; rules are written plainly without capitals or absolute emphasis. Evidence: 68 directives, 28 policies and 204 governance scripts with 53% of commits touching no product or test code; two three-day-old rules were broken on a day there were already 45; newer models follow accumulated cautions more literally (pos.json; models.json RULE 9, RULE 10).
- Measure the method on versus off: run the same outcome with a component disabled at each model upgrade and compare tokens, tool calls, wall clock, escaped defects and rework rate; report lead time and change failure rate, not gates passed. Run the same task through Spec Kit, BMAD and Superpowers with the same figures before making any comparative claim. Evidence: most 'paid' figures are single self-measured instances; no after-figure for #61, #62, #64, #66, #67; developers in a METR study believed they were 20% faster while measured 19% slower (pos.json; practices.json; audit.json missing).
- A small-change lane: one outcome block (outcome, proof, boundary), red, code, green, done, in one file; the fuller pipeline is opt-in. Evidence: the draft toolkit required six stage files for a one-line fix, and a one-flag change cost the same 840k tokens as a schema migration (audit.json over_engineered; pos.json waste/4).
- Content-scoped staleness: key evidence on the content hash of the files inside an outcome's boundary so a commit or an unrelated edit does not invalidate proofs. Evidence: in the draft toolkit a plain commit turned every proof stale and re-proving was quadratic (audit.json, measured).
- Per-session run state and a doctor command: key the active run by session id so parallel sessions and subagents work, and ship one command that says whether each hook is installed and live. Evidence: one shared active pointer blocked unrelated sessions; a missing hook file exits 2 and blocks every matched tool call; fail-open without a health check hides absent enforcement (audit.json).
- A recorded project total: one script that sums token spend per outcome and for the project. Evidence: total spend is not recorded anywhere, only per-run figures (pos.json honest_assessment).
- Before publication, re-cite or remove the figures this validation could not verify: the '18 judge rounds, about 12M tokens' figure (OU-R3), the 22.2M-versus-26.6k projection (FR1-R3), the pinned-model incident (FR1-R23), the 6.3M-token audit figure (DE-R38), and the conflicting 95 KB and 101 KB peak sizes for the instruction file.

## Classes of instruction that were dropped

- Totals from the validation stats: 224 clusters ruled across six areas; 93 kept and 52 refined (the 145 surviving rules traced above), 48 merged into another cluster as duplicates, 31 dropped; 78 first-pass verdicts were overturned on review and 0 instruction ids were left unruled. Counts below are clusters; the number of the 1,856 source instructions inside dropped clusters was not computed in this step.
- Step micro-management, 7 clusters (FR1-R4, FR1-R6, FR1-R8, PR-R26, PR-R39, VE-R42, SA1-R15): fixed 200-line read windows, locator-call ratios, 30-tool-call step caps, fixed step durations and launch/collect shapes, mandated task DAGs with 30-second nodes, timed commit steps. Dropped because the only real data shows higher cost (about 90M tokens per outcome under the cap) and models.json RULE 6 classes them as workarounds for weak context handling. Their surviving residue is P18's tunable defaults.
- Fixed role relays and specification ceremony, 4 clusters (PR-R38, OU-R32, DE-R14, OU-R29): pods of persona agents, analyst-architect document pipelines, a constitution file, per-role failure attribution. Dropped because no statement had a measured payoff and the measured evidence is all against (14 hours and 81 agents on one requirement; 43.1 MB of process markdown against 7.7 MB of product code).
- Layered LLM judging, 4 clusters (FR1-R19, OU-R30, OU-R31, DE-R13): a judge over every agent and artifact, three parallel lens judges, a general 'best product ever' objective, a token-efficiency judge. Dropped as measured cost with no recorded benefit (23 REVISEs of 30 verdicts; 733 rulings in 44 days). One fresh-context reviewer survives in P13 and stall detection in P5.
- Unmeasured tooling and habit instructions, 5 clusters (FR1-R15, FR1-R16, FR1-R17, VE-R44, DE-R35): standing delegation of wide searches to subagents, a context-compression proxy, compaction every 1M tokens, adversarial self-review before every commit, a mandatory lessons line on every artifact. Dropped for failing the project's own measure-or-revert rule; standing delegation lines are reported to raise cost on current models (models.json).
- Project-specific content, 7 clusters (FR1-R25, PR-R31, PR-R40, OU-R33, VE-R43, DE-R42, SA1-R37): this product's data-layer traps, build and device details, licensing notes, lock-script fixes, a broken remote CI account. Dropped from the method and kept in the project's own rules files, which P4 says load only with the code they govern.
- Prose restatements and implementation details with no incident, 4 clusters (SA1-R5, SA1-R14, SA1-R33, SA1-R35): a release-flow checklist already covered by the release script, an ignore-file rule, a lock-ownership detail, a ledger backfill for a cost the governance itself created.
