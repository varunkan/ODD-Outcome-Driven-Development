# The instruction catalog: every instruction given while building the POS, with its outcome

*Produced 2026-11-11 by twelve read-only agents over CLAUDE.md and its history, the 68 owner directives, the lessons ledger, the role charters, skills, workflows, decision rulings and scripts; exact duplicates merged and grouped by `tools/group_catalog.py`. The performance tag is the reading agent's classification from the outcome recorded beside each instruction; the validation rulings re-examine every one.*

Full data, one JSON file per area (id, instruction, outcome, owner's words where recorded, enforcement point, sources): `data/catalog/`.

## Counts

| area | instructions | proven to pay (recorded before/after) | earned from an incident | mandated, never measured | proven to fail, reverted |
|---|---|---|---|---|---|
| Frugality (tokens and cost) | 130 | 30 | 49 | 49 | 2 |
| Project management and orchestration | 343 | 14 | 149 | 175 | 5 |
| Outcome-driven work (research, requirements, outcome, spec) | 200 | 10 | 81 | 109 | 0 |
| Verification and implementation | 568 | 26 | 306 | 230 | 6 |
| Decisions, judging, learning and reporting | 485 | 19 | 148 | 311 | 7 |
| Safety and git hygiene | 130 | 3 | 62 | 65 | 0 |
| **all** | **1856** | **102** (5.5%) | **795** (42.8%) | **939** (50.6%) | **20** (1.1%) |

## Instructions proven to pay (102)

### Frugality (tokens and cost) (30)

**FR-001** Use a script for mechanical work (counts, diffs, greps, git facts, rule-decided verdicts). Spawn an agent only for judgement.

- Outcome: On 2026-09-15, 106 agents found nothing and one script found the blocker.
- Enforced by: judge tokenFindings
- Source: docs/process/history/CLAUDE.md:18

**FR-005** Keep agent steps short by capping tool calls ([step-cap 30]). Refuse call 31 except a context-file write, return the remainder as nodesLeft, and continue it in a fresh small step.

- Outcome: Cost grows with the square of step length. Measured: 934.5M tokens read against about 77k written across three swarms; eight developer agents (about 160 calls each at about 324k context per call) were 44% of it. Replaying with a 30-call cap reads about 40% less.
- Enforced by: tool_guard.py LENGTH; judged-swarm.js stepped()
- Source: docs/process/history/CLAUDE.md:140-144

**FR-010** Never open a large file to answer 'what calls X', 'who writes Y' or 'what breaks if I change Z'. Ask the graph or a callers query, then open only the named file:line in a bounded window. A file read compounds: it is re-read on every remaining turn.

- Outcome: Opening a 9,282-line file with 200 turns left costs 22.2M tokens, against 26.6k for graph_query.py callers. A 15-card wave re-read 235,682 tokens per turn over 3,512 turns: the bill is context size times turns, not agent count.
- Enforced by: tool_guard.py READ/RANGE; scripts/verify/graph_query.py callers
- Source: docs/process/history/CLAUDE.md:535-542

**FR-011** Before spawning an agent, ask whether a command could answer the question. Counts, diffs, greps, conflicts, git facts, board state and rule-decided verdicts are scripts. Correctness review, acceptance-criterion observables, failure classes and root-causing are agent work.

- Outcome: Triaging 53 stranded branches: 106 triage and judge agents were killed with no verdicts. One shell script plus one Python file took ~4 minutes at near-zero tokens and found the single systemic blocker.
- Enforced by: judge tokenFindings
- Source: CLAUDE.md:8, 201-203; docs/process/history/CLAUDE.md:1113-1133

**FR-012** Prefer a script even when an agent would work. A script is re-runnable, diffable, committable and idempotent, and it sees the whole distribution, where per-item agents each see one item.

- Outcome: The script found that all 53 branches had zero conflicts and 44 were blocked by one late policy, which no per-branch agent would have surfaced. ledger_branch_backfill.py ran twice: 42 events, then 0.
- Enforced by: judge tokenFindings
- Source: CLAUDE.md:203; docs/process/history/CLAUDE.md:1120-1124, 1135-1143

**FR-013** Never read a big file whole. Locate with grep -n or a code-graph query, then read a bounded range.

- Outcome: A file read is re-read on every later turn. A 9,282-line file opened with 200 turns left costs ~22.2M tokens, against 26,600 for a graph callers query. A 15-card wave re-read 235,682 tokens per turn over 3,512 turns.
- Enforced by: scripts/pipeline/tool_guard.py READ (refuses whole reads over 1000 lines)
- Source: CLAUDE.md:10; docs/process/history/CLAUDE.md:23, 535-541

**FR-015** Give every spawned workflow agent a named role type with a short tools list. Use a minimal generic 'step' charter when no role applies.

- Outcome: A default agent starts at ~95k tokens of context and a restricted one at ~48k. About 381M tokens were re-read in one session (2026-10-06).
- Enforced by: .claude/agents/step.md; judged-swarm.js uses step for planning
- Source: CLAUDE.md:17; docs/process/history/CLAUDE.md:30

**FR-016** Cap developer and fix steps at 30 tool calls ([step-cap 30]). Over the cap, only a context-file write is allowed; the remainder returns as nodesLeft and continues in a fresh step.

- Outcome: Across three swarms, 934.5M tokens were read against ~77k written. Eight developer agents (~160 calls at ~324k context each) were 44% of the reads. Replaying with a 30-call cap reads ~40% less.
- Enforced by: tool_guard.py LENGTH; judged-swarm.js stepped()
- Source: CLAUDE.md:43; docs/process/history/CLAUDE.md:143-148; scripts/pipeline/tool_guard.py:23-27

**FR-030** Before spawning any agent, ask: could a command answer this? If the answer is a count, diff, grep, file state, git fact, schema check or a table joining those, it is mechanical: write the script.

- Outcome: 53 branches sat ahead of main. A 106-agent workflow was killed mid-run with no verdicts. One shell script plus one Python file took ~4 minutes at near-zero tokens and found that all 53 had zero conflicts and 44 were blocked by one thing (a missing ledger event after POLICY 16 landed).
- Enforced by: judge tokenFindings (root CLAUDE.md)
- Source: docs/process/history/CLAUDE.md:1109-1130

**FR-031** Prefer a script even when an agent would work: a script is re-runnable, diffable, committable and idempotent.

- Outcome: ledger_branch_backfill.py ran twice: 42 events, then 0. An agent run twice gives two different answers and neither is reviewable.
- Enforced by: none
- Source: docs/process/history/CLAUDE.md:1145-1147

**FR-038** Before spawning any agent, ask whether a command could answer the question. If the answer is a count, diff, grep, file state, git fact, schema check, or a join of those, write a script.

- Outcome: 53 stranded branches: a workflow of 106 agents (53 triage plus 53 judges) was killed mid-run with no verdicts. One shell script plus one Python file took about 4 minutes and near-zero tokens, and found and cleared the single systemic blocker.
- Enforced by: judge tokenFindings (named in CLAUDE.md; the register section names no script)
- Source: docs/product/OWNER_DIRECTIVES.md:83-102

**FR-039** Prefer a script even when an agent would work, because a script is re-runnable, diffable, committable and idempotent.

- Outcome: ledger_branch_backfill.py ran twice: 42 events, then 0. An agent run twice gives two different answers, neither reviewable.
- Enforced by: none (method)
- Source: docs/product/OWNER_DIRECTIVES.md:117-119

**FR-049** Before spawning an agent or reading many files to build a table, ask 'could a command answer this?'. Counts, diffs, greps, git facts, file state and joins are mechanical: script them. Agents are only for judgement (correctness, right observable, failure class, adversarial review, root cause).

- Outcome: A 106-agent workflow triaging 53 stranded branches produced nothing; one shell script plus one Python file answered in about 4 minutes. It found all 53 had zero conflicts and 44 were blocked by a single missing ledger event.
- Enforced by: judge tokenFindings
- Source: .claude/agents/product-owner.card.md:65-80; .claude/agents/business-system-analyst.md:291-306

**FR-050** Prefer a script even where an agent would work: it is re-runnable, diffable and idempotent. A script sees the whole distribution, and the systemic answer lives in the distribution.

- Outcome: Same 53-branch measurement: the script found the single systemic blocker that per-item agents could not see.
- Enforced by: none
- Source: .claude/agents/product-owner.card.md:75-82; .claude/agents/business-system-analyst.md:301-308

**FR-051** The analysis is read-only and runs ahead: the analyst never runs the test suite, the analyzer, a gate, a battery or worktree creation. Produce each citation with ONE batched grep+window call per file covering every anchor, read cards, specs and lessons by section marker, and budget at most 110 turns.

- Outcome: Eleven analysts ran 17 full suites. The lean rows delivered the same artifact in 81-101 turns.
- Enforced by: scripts/pipeline/card_check.sh (BSA B-2)
- Source: .claude/agents/business-system-analyst.md:172-177; .claude/agents/business-system-analyst.card.md:15

**FR-052** Never open a large file to answer 'what calls X', 'who writes Y' or 'what breaks if I change Z'. Ask the code graph, then open only the file:line it names, in a bounded range.

- Outcome: Opening a 9,282-line file with 200 turns left costs about 22,200,000 tokens; a graph callers query costs about 26,600. One wave re-read 235,682 tokens per turn over 3,512 turns: cost is context size times turns.
- Enforced by: tool_guard.py READ (over 1000 lines); scripts/verify/graph_query.py
- Source: .claude/agents/business-system-analyst.md:268-282

**FR-053** Prefer a bounded window (sed -n 'A,Bp') or a targeted grep -n over reading any file over about 500 lines.

- Outcome: Same compounding-context measurement.
- Enforced by: tool_guard.py READ/RANGE
- Source: .claude/agents/business-system-analyst.md:283-284

**FR-054** Treat a grep hit list as cheap and the files it implicates as expensive. When the graph lacks an answer, fall back to a targeted search, never to opening everything.

- Outcome: A delete-symbol grep is 1,442 bytes, but the five files it names are 26,403 lines; the graph answers in about 133 tokens.
- Enforced by: none
- Source: .claude/agents/business-system-analyst.md:285-289

**FR-055** Never open a large file to answer 'what calls X', 'who writes Y' or 'what breaks if I change Z'. Ask the graph or a caller query, then read only the file:line it names, in a bounded range (sed -n 'A,Bp' or grep -n). Prefer bounded reads to a whole-file Read on anything over about 500 lines.

- Outcome: Measured 2026-09-14: opening a 9,282-line service file with 200 turns left cost 22,200,000 tokens, against 26,600 for a caller query. A 15-card merge wave re-read 235,682 tokens per turn across 3,512 turns. The cost is context size times turns, not the number of agents.
- Enforced by: tool_guard READ (over 1000 lines), per CLAUDE.md; charter text
- Source: .claude/agents/solution-architect.md:193-214; .claude/agents/developer.md:85

**FR-056** A grep hit list is cheap; the files it points to are not. Use the list (or the graph) to answer the question rather than opening every file it names.

- Outcome: A grep for a delete call was 1,442 bytes and could not tell a call from a comment. The five files it named held 26,403 lines. The graph answered the real question in about 133 tokens.
- Enforced by: none (charter text)
- Source: .claude/agents/solution-architect.md:210-212

**FR-058** Mechanical work gets a SCRIPT, never an agent. Before spawning a subagent or reading many files to build a table, ask whether a command could answer it (counts, diffs, greps, git facts, file state, joins). Agents are for judgement: correctness, whether an AC names the right observable, failure classes, adversarial review, root cause. Prefer a script even where an agent would work.

- Outcome: Measured 2026-09-15: a 106-agent workflow was launched to triage 53 stranded branches. One shell script plus one Python file answered in about 4 minutes and found that all 53 had zero conflicts and 44 were blocked by a single missing ledger event. A script sees the distribution; an agent sees only its one item.
- Enforced by: judge tokenFindings (per CLAUDE.md); charter text
- Source: .claude/agents/solution-architect.md:216-220; .claude/agents/solution-architect.card.md:64-81; .claude/agents/developer.card.md:71-88

**FR-066** Never open a large file to answer 'what calls X / who writes Y / what breaks if I change Z'. Ask the graph or grep, then open only the named file:line with a bounded range.

- Outcome: Measured 2026-09-14: a file read is re-paid on every remaining turn. Opening a 9,282-line file with 200 turns left cost 22,200,000 tokens; graph_query callers cost 26,600. The 15-card wave re-read 235,682 tokens per turn across 3,512 turns: context size times turns, not agent count.
- Enforced by: scripts/pipeline/tool_guard.py READ
- Source: .claude/agents/test-agent.md:85; .claude/agents/orchestrator.md:23-37

**FR-067** On any file over ~500 lines use 'sed -n A,Bp' windows (at most 200 lines) or a targeted 'grep -n', never a whole-file Read.

- Outcome: Same 22.2M vs 26.6K token measurement. The guard refuses whole reads over 1000 lines and sed windows over 200 lines.
- Enforced by: scripts/pipeline/tool_guard.py:19,27,50 (READ, RANGE=200)
- Source: .claude/agents/test-agent.md:86; .claude/agents/orchestrator.md:38-39; .claude/agents/step.md:11

**FR-068** Treat a grep hit list as cheap but the files it implicates as expensive. When the graph is silent, fall back to a targeted search, never to opening everything.

- Outcome: Measured: the grep for one delete method was 1,442 bytes and could not tell a call from a comment. The five files it named are 26,403 lines. The graph answered for ~133 tokens.
- Enforced by: none
- Source: .claude/agents/orchestrator.md:40-44

**FR-069** Before spawning a subagent or reading many files to build a table, ask 'could a command answer this?'. Script counts, diffs, greps, git facts, file states and joins, even where an agent would work. Agents are for judgement only (correctness, AC observables, failure classes, adversarial review, root-causing).

- Outcome: Measured: a 106-agent workflow was launched to triage 53 stranded branches. One shell script plus one Python file answered in ~4 minutes and found what per-branch reading could not: all 53 had zero conflicts and 44 were blocked by a single missing ledger event. 'A script sees the distribution; an agent sees its one item.'
- Enforced by: judge tokenFindings; scripts/pipeline/swarm_audit.py
- Source: .claude/agents/test-agent.md:87; .claude/agents/test-agent.card.md:67-84; .claude/agents/orchestrator.md:154-171; .claude/agents/orchestrator.card.md:64-81

**FR-083** Query first, then open only the file:line it names, with a bounded window (sed -n 'A,Bp').

- Outcome: Every open file is re-read on each remaining turn. Opening a 9,282-line file with 200 turns left compounds to ~22,200,000 tokens, vs 26,600 for one graph query.
- Enforced by: tool_guard.py READ (over 1000 lines, per CLAUDE.md)
- Source: .claude/skills/surgical-fix/SKILL.md:80-89

**FR-086** Aim for 3 graph/locator calls per file read and zero tool results over 8k tokens.

- Outcome: A live pod held 20 calls to 6 reads with 0 results over 8k; that was adopted as the bar.
- Enforced by: none (agent_efficiency.py reports tool-result KB)
- Source: .claude/skills/surgical-fix/SKILL.md:92-93

**FR-092** At every delivery, run a model-free transcript parser for per-agent turns, tool calls, suite/analyzer/merge/gate runs, repeats, re-reads, result size and tokens. It also writes an ordered command ledger for a judge to read.

- Outcome: A judge reviews ~2k tokens of ledger instead of a ~300k-token transcript.
- Enforced by: scripts/pipeline/agent_efficiency.py --out
- Source: .claude/skills/product-pipeline/SKILL.md:343-348

**FR-096** Set per-role budgets (turns, full-suite runs, trial merges, tool-result KB, worktrees added = removed) and enforce them as trip-wires that exit non-zero for a running agent.

- Outcome: Budgets came from the 2026-09-04 judge synthesis and were already met by each role's lean rows.
- Enforced by: scripts/pipeline/agent_efficiency.py --trip
- Source: .claude/skills/product-pipeline/SKILL.md:366-373

**FR-116** Orient each role with a targeted grep of the context file for the previous stage's rulings plus its last few lines. Never read the whole rulings section.

- Outcome: Measured 58,830 bytes (whole section) against 1,430 bytes (stage grep): 41x less on every spawn. A later edit back to 'sed -n the whole Judge rulings section' (33,616 bytes) was reverted (D92(5)).
- Enforced by: .claude/workflows/judged-swarm.js:36 orient form
- Source: docs/product/pos-zero-defect/DECISIONS.md:1389-1393, :1567-1569

### Project management and orchestration (14)

**PM-025** Remove coordinator turns between stages: run the per-requirement ladder (develop -> certify in parallel with judge -> one rework -> re-certify -> train) as one workflow. The coordinator acts only at rulings and the merge go.

- Outcome: The coordinator had been the serial bottleneck. The first workflow ran fifteen agents in 102 minutes with no coordinator turns in between.
- Enforced by: /req-ladder skill (.claude/skills/req-ladder/SKILL.md)
- Source: docs/process/history/CLAUDE.md:390-394

**PM-067** Prefer changing the SHAPE of work (batching, parallelism, absorption, sequencing) over adding CHECKING tooling. New checking tooling is frozen while finished work sits unmerged.

- Outcome: Everything that paid changed the shape of work; checking tooling never made delivery faster, and six of seven merges in a day were factory work.
- Enforced by: none
- Source: CLAUDE.md:187; docs/process/history/CLAUDE.md:1027-1033, 1041-1043

**PM-068** Dispatch per INVARIANT, not per ticket: one branch closes every open ticket that is an instance of its invariant. Absorbed tickets keep their ids as acceptance rows and are never dispatched alone.

- Outcome: REQ-161 closed 4 cards for ~200k tokens vs ~3.4M as four ladders (17x). One defect had been fragmented into four cards.
- Enforced by: dispatch_check.sh refuses an absorbed card
- Source: CLAUDE.md:191; docs/process/history/CLAUDE.md:1019, 1062-1067

**PM-069** Tier the pipeline by risk, computed from the diff and never chosen. Core money/sync/schema changes get the full ladder (probes, develop, certify, judge, rework, re-certify, train). Scripts/docs/specs-only changes get develop, certify, train with two agents. Other code adds probe-first for the touched classes.

- Outcome: 115 agents, 11,542 turns and 1.3B tokens merged 5 cards (board 140 to 152). A uniform 7-stage ladder cost ~840k tokens per card. The realistic gain is 10-20x, mostly from invariant dispatch and tiering.
- Enforced by: dispatch_check.sh computes the tier
- Source: CLAUDE.md:191; docs/process/history/CLAUDE.md:1054-1073, 1086-1088

**PM-079** Dispatch per INVARIANT, not per item. Before dispatching, ask what property the fix establishes and which other open items are instances of it; one branch then closes them all.

- Outcome: REQ-161 closed 4 cards for ~200k tokens vs ~3.4M as four ladders: paid 17x.
- Enforced by: scripts/pipeline/dispatch_check.sh
- Source: docs/process/history/CLAUDE.md:887-889,1017,1069-1073

**PM-096** Ship any rule that constrains an artifact's shape with a back-application sweep. Enumerate every unmerged branch carrying the affected artifact and fix or notify each one, including stages already COMPLETE, which in-flight messages never reach.

- Outcome: POLICY 9c landed 9 minutes before a branch's commit, and the task-DAG rule 36 minutes after a stage completed. The sweep found TWO blocked stages; one Test Agent was about to spend a whole certification discovering it.
- Enforced by: none
- Source: .claude/agents/LESSONS.md:68,293-308

**PM-117** Dispatch per invariant: one branch closes every open card that is an instance of the invariant, absorbing those cards as acceptance rows. Never split one defect across several cards.

- Outcome: Before: 115 agents, 11,542 turns and 1.3B context tokens to merge 5 cards and add 12, with one defect split across four cards and four ladders queued. Invariant batching then paid 17x (#47, line 58).
- Enforced by: CLAUDE.md 'Dispatch per INVARIANT'; REQ-161 worked example; directives_check.sh point 45
- Source: docs/product/OWNER_DIRECTIVES.md:56

**PM-122** Use agents only for judgement: correctness review, whether an AC names the right observable, which failure class a diff opens, root-causing an unexplained failure, design critique. Script enumerating, counting, joining, grepping, diffing, parsing and any verdict a rule decides.

- Outcome: Draws a sharp line between mechanical and judgement work.
- Enforced by: CLAUDE.md 'Mechanical work gets a SCRIPT'
- Source: docs/product/OWNER_DIRECTIVES.md:104-110

**PM-137** Dispatch per INVARIANT, not per card. Ask what property the fix establishes and which open cards are instances of it. One branch closes them all, each absorbed card kept as an acceptance row.

- Outcome: Per CLAUDE.md history of #45/#47: invariant batching closed 4 cards for about 200k tokens versus about 3.4M as four separate ladders (17x).
- Enforced by: scripts/pipeline/dispatch_check.sh:22 (refuses an absorbed card); card_check.sh (B-3)
- Source: .claude/agents/product-owner.md:131; .claude/agents/product-owner.card.md:16

**PM-138** Tier the verification ladder from the DIFF, never by choice. High-risk paths (money, sync, schema) get the full ladder. A docs/scripts/specs-only diff gets develop -> certify -> merge with two agents. Other code gets the middle tier plus probe-first for the failure classes it touches.

- Outcome: A uniform seven-stage ladder cost about 840k tokens per card regardless of risk (per CLAUDE.md history of #45).
- Enforced by: scripts/pipeline/dispatch_check.sh:62-64 (tier computed from the diff)
- Source: .claude/agents/product-owner.md:131

**PM-154** Dispatch each requirement as ONE resumable ladder workflow run and record its run id in the same action. Act only at rulings and the merge go; never relay stages by hand. Merge in trains of two to four branches.

- Outcome: Per CLAUDE.md #40, the first workflow ran fifteen agents in 102 minutes with no PO turns in between.
- Enforced by: .claude/skills/req-ladder (/req-ladder)
- Source: .claude/agents/product-owner.md:190

**PM-218** Pay ceremony once per file changed. Before opening a branch, find every open card that touches the same files and absorb them into ONE branch, keeping each id as an acceptance row (one fix doc, one coverage matrix, one battery, one gate).

- Outcome: 137 open cards (17 with branches, touching 36 lib/ files) collapsed by union-find into 7 provably disjoint components. Six cards in one auth service file became one change reviewed once.
- Enforced by: scripts/pipeline/batch_disjoint.sh --pick; scripts/pipeline/po_dispatch_check.sh
- Source: .claude/skills/surgical-fix/SKILL.md:51-65

**PM-227** Before launching a workflow, dry-run its control flow: wrap the body in an async IIFE with stubbed agent/parallel. A bare node --check rejects the top-level return the runtime allows.

- Outcome: Verified 2026-09-05: the happy, one-rework and API-death paths all reach MERGED.
- Enforced by: none
- Source: .claude/skills/req-ladder/SKILL.md:74-76

**PM-247** Keep one shared, singular product owner across parallel teams, owning priority, the board and done-ness. Never duplicate it.

- Outcome: One head holding the whole board caught REQ-037/042 as one defect, and REQ-042's unmeetable AC before its branch was cut.
- Enforced by: none
- Source: .claude/skills/product-pipeline/SKILL.md:141-146,234-235

### Outcome-driven work (research, requirements, outcome, spec) (10)

**OD-011** Ask the graph for the SHAPE of a defect to enumerate the whole class, then let evidence pick which members to fix. Never edit every member blind.

- Outcome: One query returned 241 unflexed Rows containing Text across 52 files in seconds. Editing all 241 blind would be guessing; the app's crash reporter names the real overflows.
- Enforced by: none
- Source: docs/process/history/CLAUDE.md:528-533

**OD-022** Query the code graph before proposing, reviewing or scoping a change. Answer 'what calls X / who writes Y' with a callers query, then do a bounded read.

- Outcome: ~22.2M tokens to open a large file vs 26,600 for the callers query.
- Enforced by: scripts/verify/graph_query.py
- Source: CLAUDE.md:110; docs/process/history/CLAUDE.md:535-541

**OD-025** Enumerate the CLASS with one shape query, then let evidence pick which members to fix. Never edit every member blind.

- Outcome: One query returned 241 unflexed Row-with-Text sites across 52 files in seconds.
- Enforced by: none
- Source: CLAUDE.md:110; docs/process/history/CLAUDE.md:528-533

**OD-040** Absorbed items keep their ids as acceptance rows on the absorbing branch, so nothing is descoped. An item that is an instance of an in-flight invariant is never dispatched separately.

- Outcome: Worked examples: REQ-161 (four cards, one seam), REQ-162 (three cards, one capability).
- Enforced by: dispatch_check.sh refuses an absorbed card (scripts/pipeline/dispatch_check.sh:22-25)
- Source: docs/process/history/CLAUDE.md:888-889,1071-1073

**OD-042** Run a script over the whole set to see the distribution, because the systemic answer lives in the distribution that per-item agents cannot see.

- Outcome: The script showed that 44 of 53 branches shared one blocker; the backlog was one piece of work, not 53.
- Enforced by: none
- Source: docs/process/history/CLAUDE.md:1140-1143

**OD-048** Run a script over the whole set to see the distribution; the systemic answer lives there, and per-item agents cannot see it.

- Outcome: All 53 branches had zero conflicts, and 44 were blocked by one policy that landed after they were written. The backlog was one piece of work, not 53.
- Enforced by: none (method)
- Source: docs/product/OWNER_DIRECTIVES.md:95-97,112-115

**OD-135** Before fixing a defect, list the whole CLASS of affected sites (callers, writers, blast radius) with a code-graph query instead of hunting the single instance.

- Outcome: 'Every writer of orders': graph ~297 tokens vs ~78,000 for grep-then-read of 12 files/26,027 lines (262x). Graph gave 4 real callers vs 11 mixed grep hits. One shape query found 241 candidates across 52 files.
- Enforced by: POLICY 17 at commit; scripts/verify/graph_query.py callers|writers|blast
- Source: .claude/skills/surgical-fix/SKILL.md:17-34

**OD-137** If the evidence naming the offenders does not exist yet, instrument the system to produce it (e.g. make the error reporter print the culprit file:line) before you hunt.

- Outcome: crash_reporter had been discarding the widget name, which turned a 1-line fix into a 241-candidate hunt. Once it printed file:line, the hunt became a 17-line fix list.
- Enforced by: none
- Source: .claude/skills/surgical-fix/SKILL.md:46-49; .claude/skills/instrument-check/SKILL.md:36

**OD-186** Answer 'what calls X / who writes Y' with a graph query process so only the answer enters context; open only the named file:line with a bounded read; cite only file:line from an actual read.

- Outcome: Opening a 9,282-line file with 200 turns left costs ~22.2M tokens vs ~26.6k for the query; the deleteOrder question cost ~79k tokens of file reads vs a few hundred.
- Enforced by: scripts/verify/graph_query.py callers
- Source: scripts/verify/graph_query.py:1-16; docs/process/history/agent-developer.md:722-740

**OD-189** Repair drifted citations by an old→new diff line map from the citation epoch; refuse deleted lines (the claim moved, a human decides); do not use anchor-text search.

- Outcome: The anchor heuristic repaired 11 citations with 2 wrong (landed on the declaration, not the return line); the diff map gave the correct line.
- Enforced by: scripts/verify/design_citation_repair.py
- Source: scripts/verify/design_citation_repair.py:1-17

### Verification and implementation (26)

**VE-002** Write device and UI legs as automated test code. Never hand-drive a device with coordinate taps.

- Outcome: About 450 tool calls by hand against about 8 as tests.
- Enforced by: tool_guard.py TAPS -> scripts/pipeline/no_manual_taps.sh
- Source: docs/process/history/CLAUDE.md:22

**VE-008** Run scripts before judges: before every judge, a prejudge script runs the repo's own checkers (citation rot, task DAG, coverage matrix, citation pins, invariants, affected tests). The producer fixes what fails, and the judge cites the report instead of re-checking.

- Outcome: REQ-306: 23 REVISEs in 30 verdicts over 14 hours, and six of seven wave-2 REVISEs had no product defect. prejudge.sh found the pin drift, missing coverage matrix and rotted citations in 2 min 20 s. REQ-322 and REQ-323 are the 'after' runs.
- Enforced by: scripts/pipeline/prejudge.sh <REQ> --stage <s>
- Source: docs/process/history/CLAUDE.md:132-139

**VE-038** Run one full test suite per merge batch, on the combined tree, before any push. Verifiers run only the affected tests. Non-interacting branches compose into one train and gate once.

- Outcome: The full suite ran five times in one day (2026-09-08) for changes that never interacted.
- Enforced by: scripts/pipeline/dispatch_check.sh
- Source: CLAUDE.md:14, 42, 191; docs/process/history/CLAUDE.md:27, 1074-1075

**VE-059** Ship the store-optimized per-device artifact, never a fat multi-architecture binary, to the store.

- Outcome: The fat APK was 66.8 MB, 95.5% of it native libraries carried three times. An arm64-only artifact cuts 63.2%; the bundle's arm64 delivery transfers 82.0% less.
- Enforced by: scripts/build_prod.sh
- Source: .claude/rules/builds.md:24-35

**VE-097** Device and UI test legs are code: integration tests run by a runner script. Hand-driving (tapping coordinates, reading UI dumps, comparing screenshots by hand) is refused.

- Outcome: Same hardware, tenant and evening: ~450 tool calls and ~2 hours for ~40 hand-driven legs, vs ~8 calls and 128 s for 8 tests. Only 13 of 57 legs were convertible at the time.
- Enforced by: scripts/pipeline/no_manual_taps.sh; tool_guard.py TAPS; dispatch_check.sh
- Source: CLAUDE.md:12, 177; .claude/rules/devices.md:20-41; docs/process/history/CLAUDE.md:1020

**VE-098** Allow only named exceptions to automated legs, and name them in the dispatch: a registration or account password, a physical peripheral, or an observable that differs between debug and release. 'Faster to just tap it' is never an exception.

- Outcome: Hand-driving was 50x slower and is paid again on every future build.
- Enforced by: no_manual_taps.sh refuses unnamed exceptions
- Source: .claude/rules/devices.md:43-48

**VE-099** Remove repetition; never review less.

- Outcome: Every measured win came from removing repetition (five suite runs, four ladders over one seam, forty hand-tapped legs). The adversarial reviews caught that week's real defects.
- Enforced by: none
- Source: CLAUDE.md:187; docs/process/history/CLAUDE.md:1044-1047

**VE-139** Construct the falsifying case and never argue it away. A deviation defended by 'that case cannot exist' does not ship until the fixture has been ATTEMPTED and its output pasted.

- Outcome: On 2026-09-08 a certifier built the tree a deviation called impossible; it compiled and reproduced both defects the card existed to prevent.
- Enforced by: none
- Source: docs/process/history/CLAUDE.md:897-900

**VE-142** Attack a pin or test with injected mutants before trusting it.

- Outcome: An anti-gaming pin was defeated by three injected mutants: every test still passed with the defect back in the file, because the pin matched only same-line spellings. A judge caught it before ship.
- Enforced by: mutation battery (scripts/verify/mutation_battery.sh per root CLAUDE.md)
- Source: docs/process/history/CLAUDE.md:906-908,1085-1087

**VE-143** Recompute; never inherit a summary or a carried artifact.

- Outcome: Recomputation FALSIFIED two of four carried rig artifacts; one reported a money-shaped divergence on a fleet in perfect agreement.
- Enforced by: none
- Source: docs/process/history/CLAUDE.md:909-910

**VE-144** Write device/UI test legs as code (integration tests run by a runner script); never hand-drive by tapping coordinates or reading pixels.

- Outcome: ~450 calls by hand vs ~8 as tests; 128 s / ~8 tool calls vs ~11 calls per leg. Paid, but only 13 of 57 legs were convertible.
- Enforced by: scripts/pipeline/no_manual_taps.sh, tool_guard TAPS, scripts/verify/legs.sh
- Source: docs/process/history/CLAUDE.md:948-950,1019

**VE-145** Batch device/environment testing by device STATE, grouping legs that share a state transition.

- Outcome: 5 state transitions for 24 graded legs: paid ~5x.
- Enforced by: none
- Source: docs/process/history/CLAUDE.md:1018

**VE-167** Run vacuity probes on a test suite: an always-pass stub and an always-fail stub. Together they prove no assertion is vacuous in either direction before you trust the suite.

- Outcome: For REQ-039, always-exit-0 gave 39/25 and always-exit-1 gave 44/20. That located the defect in the unpinned guards rather than the assertions.
- Enforced by: none
- Source: .claude/agents/LESSONS.md:267-269

**VE-168** Reject on a proven mechanism, not a suspicion. Replay the merge and its hooks in an isolated clone, capture the violations, and show the differential against a conforming artifact at the same door.

- Outcome: REQ-029's Test Agent proved the shape-rule block by replay. Two sibling files matching the same regex passed because they carried a conforming line.
- Enforced by: none
- Source: .claude/agents/LESSONS.md:300-305

**VE-183** For a script whose purpose is to touch an external device or system, one real read-only invocation of the documented call form is a mandatory cheap rung. Run it, don't read it.

- Outcome: Both REQ-103 defects cost one read-only real run each to find, after two clean off-device passes.
- Enforced by: none
- Source: .claude/agents/LESSONS.md:523-525

**VE-197** Batch expensive device or integration test batteries instead of running them once per item.

- Outcome: Later scored at about 5x for batching the rig by device state (#47).
- Enforced by: product-pipeline SKILL.md 'Operating policy'
- Source: docs/product/OWNER_DIRECTIVES.md:20

**VE-206** Merge branches gated on a real environment in batches: one composed build and one test-environment session per batch.

- Outcome: Later scored at about 5x for batching by device state (#47).
- Enforced by: product-pipeline SKILL.md 'Efficient fixes'
- Source: docs/product/OWNER_DIRECTIVES.md:44

**VE-215** Write UI and device test legs as code (integration tests run by a script). A dispatch-scanning script refuses hand-driving by taps, UI dumps or screenshot comparison. Every exception must be named: account registration or password, a physical peripheral, or a debug-versus-release observable.

- Outcome: Measured the same evening on the same hardware: about 450 tool calls, 830k tokens and 2 hours for about 40 hand-driven legs, versus about 8 tool calls and 128 s for 8 tests.
- Enforced by: scripts/pipeline/no_manual_taps.sh; dispatch_check.sh; session_brief.sh; directives_check.sh point 49
- Source: docs/product/OWNER_DIRECTIVES.md:60

**VE-218** Prove the whole path with one end-to-end test. Then one judge scores only the outcome, then the merge gate runs.

- Outcome: D163's run proved the install-to-first-order path on host fakes within about two hours.
- Enforced by: .claude/workflows/outcome-first.js
- Source: docs/product/OWNER_DIRECTIVES.md:265-267

**VE-369** Answer a delivery's deviation defence by CONSTRUCTING the falsifying case and, where you can, EXECUTING the reconciliation and pasting the result, rather than ruling on the argument.

- Outcome: REQ-136 re-certification (positive case): the pass built the fixture that broke the deviation, deleted the fallback, fixed the invalid probe and showed the set green. 'A REWORK that hands the Developer a proven path costs one round; a REWORK that hands over an objection costs three' (history agent-test-agent.md:347-352).
- Enforced by: none
- Source: .claude/agents/test-agent.md:177

**VE-385** Let evidence choose which members of a class to fix. Never bulk-edit the whole candidate set blind.

- Outcome: Of 241 unflexed Rows, about 17 actually overflowed. Editing all 241 would have been a guess big enough to create a new defect class.
- Enforced by: none
- Source: .claude/skills/surgical-fix/SKILL.md:41-45

**VE-390** Device and UI verification legs are code: integration tests run by a script. Never hand-drive taps, UI dumps or screenshot comparisons as the thing you observe.

- Outcome: Hand-driving cost ~450 tool calls for ~40 legs. The same work as tests cost ~8 calls in 128 seconds.
- Enforced by: scripts/verify/legs.sh; no_manual_taps.sh; tool_guard TAPS (per CLAUDE.md)
- Source: .claude/skills/surgical-fix/SKILL.md:119-123

**VE-406** Measure a new guard's blast radius against existing artifacts before merging it.

- Outcome: POLICY 17 was checked against 132 existing fix docs (7 would trip) before landing, so it did not break every future merge.
- Enforced by: none
- Source: .claude/skills/instrument-check/SKILL.md:114-115

**VE-433** Classify a diff as INSTRUMENT-ONLY by script when every line is an assert, debug guard, test seam, comment, import or bracket. It certifies without a device smoke; claiming the class over a production line fails the commit.

- Outcome: REQ-110's fifteen debug lines had cost two release builds and forty certifier turns.
- Enforced by: POLICY 9e; instrument_only_diff
- Source: .claude/skills/product-pipeline/SKILL.md:443-448

**VE-497** Attribute a performance excess with per-component revert arms before any rework, against a pre-registered outcome table. Never remove a graded visual to buy budget. Record baselines only on WITHIN BUDGET, by the record procedure, never hand-typed.

- Outcome: A x1.44 excess tracked render-count ratios, so it was structural, not noise. The arm method then found the app bar to be the cost (D1231).
- Enforced by: mutation revert rows + compare script
- Source: docs/product/pos-zero-defect/DECISIONS.md:9656-9665

**VE-550** Map a change to the end-to-end tests that observe it by call graph; an all-match table (text or import closure) discriminates nothing and is not evidence.

- Outcome: Import closure matched 33 of 33 cards; the call graph matched 40 of 43 with median 9 legs, minimum 1 (not 32).
- Enforced by: scripts/verify/leg_for_card.py
- Source: scripts/verify/leg_for_card.py:1-20

### Decisions, judging, learning and reporting (19)

**DL-049** Route decisions to a judge agent (question, facts, options, reversibility) that rules on the owner's behalf into a decisions log, and act on the ruling in the same turn. Only owner-only physical acts (credentials, billing, consoles, deploys, store uploads) wait for the owner.

- Outcome: Three decisions sat open for hours while fifteen agents ran. The merge go waited ~5 hours; the judge rules in minutes.
- Enforced by: Workflow 'decide'; docs/product/pos-zero-defect/DECISIONS.md
- Source: CLAUDE.md:39, 85, 173; docs/process/history/CLAUDE.md:938-941

**DL-090** State a process change's measurement (tool calls, tokens, wall clock) BEFORE building it, measure it AFTER on real work, record both, and REVERT what does not pay.

- Outcome: 2026-09-08 scorecard: invariant batching paid 17x; batching the rig by device state ~5x; legs as tests paid; the mutation generator caught defects but gave no speedup; the suite lock went unmeasured.
- Enforced by: none
- Source: CLAUDE.md:187; docs/process/history/CLAUDE.md:1010-1040

**DL-099** Have an independent judge from outside the delivering team review correctness adversarially.

- Outcome: Every blocking defect caught before a device came from a reviewer with no stake in the work.
- Enforced by: judge agent (.claude/agents/judge.md)
- Source: docs/process/history/CLAUDE.md:642-644

**DL-116** Route decisions to a judge agent, not the owner. A queue file of facts and options goes to a judge with one objective, the ruling is recorded in a decisions file, and the coordinator acts the same turn. Ask the owner only for what only the owner can do, and never end a turn with an open question while agents run.

- Outcome: Three decisions sat open for hours while fifteen agents ran, because the PO ended turns with questions. The merge go waited ~5 hours; the judge rules in minutes.
- Enforced by: decide workflow + DECISIONS.md (directive #51)
- Source: docs/process/history/CLAUDE.md:933-937

**DL-124** Prefer changing the SHAPE of work (batching, parallelism, absorption, sequencing) over adding CHECKING tooling, and freeze new checking tooling while finished work sits unmerged. Never present 'we can catch more bugs' as 'we can ship faster'.

- Outcome: Every change that paid on 2026-09-08 changed the shape of work (17x, ~5x). Checking tooling caught defects but gave no speedup, and treating it as speed is how six of seven merges in a day became factory work.
- Enforced by: none
- Source: docs/process/history/CLAUDE.md:1025-1031,1041-1043

**DL-125** Never trade quality for speed. Get wins by removing REPETITION (duplicate suite runs, duplicate ladders over one seam, hand-tapped legs), never by reviewing less.

- Outcome: Every measured win came from removing repetition, while the adversarial reviews caught that week's real defects.
- Enforced by: none
- Source: docs/process/history/CLAUDE.md:1044-1047,1085-1089

**DL-128** Keep process lessons in a two-tier ledger: a short rules table that every agent reads (injected at spawn) and an appendix of incident records read only at curation, when appending, or when that lesson's trigger fires.

- Outcome: Lets every agent get the rules cheaply while incident detail stays on disk. At the 2026-09-16 curation the ledger went from 39 counted entries / 664 lines to 17 counted entries with nothing dropped.
- Enforced by: SessionStart hook in .claude/settings.json:16 counts '^### L-[0-9]+ ' headings
- Source: .claude/agents/LESSONS.md:1-9,49,137-139

**DL-132** Cap the live rules table at about 30 lessons. Merge duplicates into one surviving id at each completeness audit, give each folded id a dated paragraph, sum their recurrence counts, and keep every old id resolvable through an alias row.

- Outcome: Curation took 39 entries to 17. Twelve ids were folded (e.g. L-17/L-22 into L-19), every citation still resolves, and recurrence counts carried over (L-25 summed to 6).
- Enforced by: SessionStart hook prints 'LESSONS.md over 30 entries -- PO must curate' (.claude/settings.json:16); POLICY 9c/9d resolve ids only via '### L-n ' or '| L-n |'
- Source: .claude/agents/LESSONS.md:7,13-29,86-101,133-134

**DL-134** At curation, re-verify every 'this is now mechanised' claim against the repository (e.g. git log --all -- '<file>'). If the claimed script or scan does not exist, correct the record in place and keep the lesson LIVE.

- Outcome: Found two false claims: merge_three.sh never existed on any ref, and the promised text scan for 'grep -q' was never built (only behavioural pins exist). Both lessons stayed live as owned residuals.
- Enforced by: none (curation step)
- Source: .claude/agents/LESSONS.md:43-47,241-243,477-480

**DL-177** Ship a process change only with its measurement: state the number before building, measure it afterwards on real work, and revert what does not pay.

- Outcome: Scored that day: invariant batching 17x, batching the rig by device state about 5x, legs-as-tests about 11x per leg.
- Enforced by: CLAUDE.md 'A process change ships with its measurement'; directives_check.sh point 47
- Source: docs/product/OWNER_DIRECTIVES.md:58

**DL-179** Never buy speed by reviewing less: remove repetition instead.

- Outcome: Every measured win came from removing repetition.
- Enforced by: CLAUDE.md #47 section
- Source: docs/product/OWNER_DIRECTIVES.md:58

**DL-213** Send decisions you would bring the owner to a product judge instead (queue file of facts and options -> judge -> decisions log), and act on the ruling that turn. Before sending a reply, count its question marks against the owner-only list (credentials, money, legal fields, store uploads).

- Outcome: Per CLAUDE.md earned method 19, a merge go waited about 5 hours on the owner; the judge rules in minutes. Three decisions sat open for hours while fifteen agents ran.
- Enforced by: grep -c '?' self-check; Workflow 'decide'; DECISIONS.md
- Source: .claude/agents/product-owner.md:153

**DL-244** A judge reviews every stage's artifact AND its execution: what was grounded versus assumed, what reachable thing was missed, whether the handoff carried what the next stage needs. Each capability finding becomes a durable upgrade to that role's charter (a new check, a sharper procedure, a named trap), logged under '## Charter upgrades'. Repeating a gap already found is a process defect, escalated.

- Outcome: Produced the dated '## Charter upgrades' lists in both charters: about 20 Architect entries and about 60 Developer entries, each tied to a judge finding. POLICY 9k blocks a REWORK that has no dated charter upgrade.
- Enforced by: scripts/policy_check.sh POLICY 9k (per CLAUDE.md)
- Source: .claude/agents/developer.md:48-59,116; .claude/agents/solution-architect.md:119-130

**DL-293** Run the mechanical pre-judge checkers (citation rot, task DAG, coverage matrix, citation pins, invariants, affected tests) before every judge, and have the producer fix their failures first. The judge cites the report, never re-opens what it covers, and spends its calls on what no script can see.

- Outcome: Measured on REQ-306: 14 h, 23 REVISEs in 30 verdicts. Six of seven wave-2 REVISEs named no product defect, and spec plus design took 13 serial rounds. prejudge.sh on that tree found the drifted pins, the missing coverage matrix and the rotted citations in 2 min 20 s.
- Enforced by: scripts/pipeline/prejudge.sh
- Source: .claude/agents/judge.md:52,75

**DL-297** At the design gate, check for duplicated code on this branch AND every unmerged branch with the overlap script, and rule each row that shares new names or code paths.

- Outcome: A cross-branch audit (50 agents, ~6.3M tokens) found a requirement re-deriving fixes two open PRs already held, while branch_overlap.py existed (it runs in seconds) and nothing referenced it (history agent-judge.md).
- Enforced by: scripts/pipeline/branch_overlap.py
- Source: .claude/agents/judge.md:56,75

**DL-305** Reserve REVISE for PRODUCT defects (correctness bug, unmet AC or evaluation row, hallucination about code, tests or product, broken repo rule, dishonest screen, departure from the owner's words). Process findings (call caps, token waste, report wording, an uncertified pass on right code) become directives and charter upgrades, never a round. PASS with directives is normal.

- Outcome: REQ-306: 23 REVISEs in 30 verdicts, six of seven wave-2 REVISEs with no product defect, 14 h of run time (history agent-judge.md). Directive #61.
- Enforced by: none
- Source: .claude/agents/judge.md:69,75

**DL-327** Back every process rule with numbers measured on this repo; the measurement is the argument for the rule.

- Outcome: The skill exists because a 20-line fix had been wrapped in twelve ceremonies and a 3,182-test suite run sixteen times; every figure in it was measured 2026-09-14/15.
- Enforced by: none
- Source: .claude/skills/surgical-fix/SKILL.md:8-11

**DL-361** Reviewers and judges must come from outside the team that delivered.

- Outcome: Every blocking defect caught before a device (a tender-gate zero, a tautological recurrence guard, an unmeetable AC, two unpinned production call sites) was found by a reviewer with no stake.
- Enforced by: none
- Source: .claude/skills/product-pipeline/SKILL.md:228-233

**DL-464** Attribute a red batch gate by computation: intersect the failing test files with the tests that reach each card's changed files; exonerate and re-drain unreached cards; a failing test no card reaches is main's own defect.

- Outcome: A drain reverted three good cards for one bad one; hand attribution cost two suite runs and ~40 min. The method found a pre-existing app-version break on main.
- Enforced by: scripts/pipeline/attribute_red.sh; test_attribute_red.sh
- Source: scripts/pipeline/attribute_red.sh:1-16

### Safety and git hygiene (3)

**SA-025** No agent types a password, and no credential or PIN is ever written into a file or commit. Use a carried session or an out-of-repo autologin file; the setup script refuses to write inside the repo.

- Outcome: Session carry across a fresh install was proven at 21-23 s with zero owner logins.
- Enforced by: scripts/setup_dev_autologin.sh refuses an in-repo path; scripts/verify/session_carry.sh
- Source: CLAUDE.md:195; .claude/rules/devices.md:60-77

**SA-037** Give every guard a sanctioned policy door so a legitimate action (such as a revert) always has a legal path.

- Outcome: The REQ-148 policy door unblocked a revert that had no other legal path; it paid in kind (unblocked vs blocked), not in speed.
- Enforced by: scripts/policy_check.sh (REQ-148 door)
- Source: docs/process/history/CLAUDE.md:1021

**SA-062** Merge in TRAINS: compose the branches with merge-tree, run one full gate per train, merge in order and retire each branch. A code train needs one go per train. Certify a debug-only code diff as INSTRUMENT-ONLY.

- Outcome: Per CLAUDE.md #45, the full suite once ran five times in one day for changes that never interacted.
- Enforced by: none
- Source: .claude/agents/product-owner.md:194

## Instructions proven to fail and reverted (20)

### Frugality (tokens and cost) (2)

**FR-008** (Reverted) Poll background jobs with periodic agent WAIT steps. Replaced: wait with a one-call scheduler script instead.

- Outcome: Agent WAIT/collect steps were assumed to 'cost almost nothing', but 24 collects spawned only to answer PENDING read 24.6M tokens. Replaced by jobs_wait.sh.
- Enforced by: scripts/pipeline/jobs_wait.sh
- Source: docs/process/history/CLAUDE.md:453-454,19

**FR-111** REVERTED rule: do not spawn a test agent to find out whether a background job has ended.

- Outcome: Failed at 24.6M tokens over 24 PENDING-only collects, with every chain UNVERIFIED (six back-to-back collects against a battery queued an hour for a suite slot). Replaced by the one-call waiter script.
- Enforced by: replaced by scripts/pipeline/jobs_wait.sh
- Source: .claude/workflows/judged-swarm.js:170-173; scripts/pipeline/jobs_wait.sh:9-13

### Project management and orchestration (5)

**PM-092** Do not fan out one triage agent (plus one judge) per item to answer mechanical questions.

- Outcome: 53 triage agents + 53 adversarial judges = 106 agents, killed mid-run with no verdicts; replaced by a script.
- Enforced by: none
- Source: docs/process/history/CLAUDE.md:1117-1119

**PM-202** (Superseded) For an unavoidable in-step wait, use a bounded 'perl select' of at most 60 s, polled at most once a minute.

- Outcome: Reverted by directive #48: the step that launches a job never sees its result. tool_guard WAIT now refuses perl select too (tool_guard.py:15-18). The only sanctioned wait is jobs_wait.sh as the single call of a lean waiter step. The charter line itself says '#48 overrides'.
- Enforced by: scripts/pipeline/tool_guard.py:15-18 WAIT; scripts/pipeline/jobs_wait.sh
- Source: .claude/agents/test-agent.md:135

**PM-229** Do not dispatch one long-running agent per stage (40-100 minutes each). Break stages into short steps.

- Outcome: Template v1 retired. On 2026-09-08 four of six stages overran, and the two that did not ran no battery.
- Enforced by: watchdog.sh STEP_OVER_3MIN (per CLAUDE.md)
- Source: .claude/skills/req-ladder/SKILL.md:114-118,318

**PM-282** REVERTED rule: do not stop a lane when its open count is at most skipped plus blocked.

- Outcome: The old stop rule (laneOpen <= skipped + blocked) quit at once on REQ-323. It was replaced by: stop only when the lane did nothing and nothing it holds is doable, and repeat passes while any pass ticks something.
- Enforced by: replaced at task-by-task.js:63-66,72-81
- Source: .claude/workflows/task-by-task.js:40-43

**PM-335** Gate N compatible changes once instead of once each, and verify main's final tree is byte-identical to the gated tree or revert (gate evidence applies only to the tree that became main).

- Outcome: Per-card trains re-ran the same ~3,400 tests eight times (1.6 h of repetition); the wave shape itself was later superseded by drain after its gates were spent on trees the hook refused.
- Enforced by: scripts/pipeline/wave.sh (superseded by drain.sh)
- Source: scripts/pipeline/wave.sh:1-11

### Verification and implementation (6)

**VE-011** Never write baseline numbers (warning counts, test counts) into the instruction file. Run the baseline script and cite its output with the tree sha it printed.

- Outcome: A fixed triple '6 warnings / 553 info' stayed stale from 2026-08-16 until two agents tripped over it, and its replacement was mis-measured. A test count written in the file was false from 2026-08-29 to 2026-09-02 with no code change.
- Enforced by: scripts/verify/baseline.sh
- Source: docs/process/history/CLAUDE.md:174-187

**VE-019** (Superseded) Require on-device verification for anything touching sync, money, printing or schema before merge.

- Outcome: Historical merge-gate item 5. The current CLAUDE.md replaces it with host diff coverage, fleet simulation and mutation rows (#66).
- Enforced by: none (superseded)
- Source: docs/process/history/CLAUDE.md:216-217

**VE-021** Do not add a gate that can never pass (lint, coverage). If you want a coverage gate, make it ratchet against a committed baseline.

- Outcome: Unpassable gates got routed around, so they were removed (history in .claude/rules/gates.md).
- Enforced by: none
- Source: docs/process/history/CLAUDE.md:237

**VE-057** Never install a gate that can never pass (e.g. fatal-infos lint, 100% coverage). If a coverage gate is wanted, it ratchets against a committed baseline.

- Outcome: lint_gate failed unconditionally on 553 pre-existing infos, and coverage_gate demanded 100% line coverage. Both were routed around and removed.
- Enforced by: none (deliberately absent)
- Source: CLAUDE.md:87; .claude/rules/gates.md:156-164

**VE-481** 'Proven' means proven on the real system. A green host proof is a step, not the proof. (Later amended: an exhaustive simulated-environment proof replaces the real device.)

- Outcome: The machine had no SDK, emulator or credentials, so the real-system leg was batched for the owner. This was superseded by D321.
- Enforced by: owner directive #65 (amended by #66)
- Source: docs/product/pos-zero-defect/DECISIONS.md:2862

**VE-496** Performance bars: use a deterministic in-test count bar (rebuilds, elements, render objects at most base x1.10) plus a coarse timing ceiling (x2.0). The fine timing bar comes only from an alternating base/head compare in one job (5 or more rounds, median of medians). Never wait for a quiet slot. RED is never waived.

- Outcome: The single-run x1.10 in-test timing bar (D983) was superseded: rounds spread 20-80% under load, so a 10% bar was a coin flip. Counts are exact.
- Enforced by: test/perf frame-budget test; scripts/verify/req406_g10_compare.sh
- Source: docs/product/pos-zero-defect/DECISIONS.md:8297-8305

### Decisions, judging, learning and reporting (7)

**DL-002** Give every default rule a named enforcer (a hook, script, gate or charter check). Prose alone does not hold.

- Outcome: Commit 3e5fadf8 records that 'Writing them down had already failed'. Rules written only as prose were broken, so a table now pairs each default with its enforcement point.
- Enforced by: defaults table maps each rule to tool_guard.py / watchdog.sh / dispatch_check.sh / branch_overlap.py / swarm_audit.py
- Source: docs/process/history/CLAUDE.md:8-9,16-28

**DL-233** Analyst closing-out (superseded): as your last action, set your row on the shared team dashboard to 'COMPLETE, AWAITING ASSIGNMENT' with a one-line verdict and artifact path, and append to the completion log.

- Outcome: The goal was stopping idle seats. Agents writing one shared file deadlocked both merge trains, and the card now routes hand-off rows to per-agent pod-rows files (business-system-analyst.card.md:30). The full charter still carries the old text.
- Enforced by: none
- Source: .claude/agents/business-system-analyst.md:85-92

**DL-248** Delete charter rules as readily as you add them. When a newer, broader rule covers an older one, remove the older one and record the deletion.

- Outcome: Deleted: 'fail-open only where blocking would be worse' and 'an uncited constant BLOCKS the spec' (Architect), and four Developer hard rules that duplicated CLAUDE.md, plus the fourth copy of 'never report done on unit tests alone'.
- Enforced by: none (charter text)
- Source: .claude/agents/solution-architect.md:247; docs/process/history/agent-solution-architect.md:272-273; docs/process/history/agent-developer.md:453-454

**DL-277** (Superseded) Compute the next decision id at write time as max+1 with a grep one-liner, never by hand.

- Outcome: Picking ids by hand left D41, D42 and D51 each heading two entries. The grep-at-write-time replacement still raced: two unstick judges both wrote D146 in the same minute (history agent-judge.md). Replaced by decision_add.py, which allocates under a file lock (judge.md:28,80). The orchestrator files still carry the old one-liner.
- Enforced by: scripts/pipeline/decision_add.py:2-18 (replacement)
- Source: .claude/agents/orchestrator.md:139; .claude/agents/orchestrator.card.md:42

**DL-379** Delete charter rules that merely restate another rule or contradict one.

- Outcome: 2026-08-27: removed a standing-autonomy section, a 'keep the user in the loop at merges' bullet and a merge-cadence trailer. All restated agreements #1/#5, and the merge clause contradicted #1.
- Enforced by: none
- Source: .claude/skills/product-pipeline/SKILL.md:531-533

**DL-388** REVERTED rule: do not count any changed file as progress. A no-progress test that accepts bookkeeping-only edits never fires.

- Outcome: The old test failed: 16 continuations 'progressed' on a ctx line alone, costing 29M tokens. It was replaced by the bookkeeping-excluded progress test.
- Enforced by: replaced by BOOKKEEPING filters (outcome-first.js:52, judged-swarm.js:114)
- Source: .claude/workflows/outcome-first.js:49-51; .claude/workflows/judged-swarm.js:124-125

**DL-428** REVERTED rule: do not run the judge only at stage and wave gates.

- Outcome: With gate-only judges, REQ-306's stuck run had 48 agents, 18 idle and 0 judge calls. Replaced by unstick-on-stall.
- Enforced by: replaced by unstick()
- Source: .claude/workflows/judged-swarm.js:315-319
