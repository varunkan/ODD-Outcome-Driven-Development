# Validation, comparison and verdict

*Produced 2026-11-11 by a 31-agent run on Claude Fable 5.2: 15 validators ruled on every catalog item, a consolidator and a skeptic per area re-examined the rulings, then one agent each composed the method, the comparison, three independent critiques and the decision. Rendered from `data/validation/` by `tools/render_evidence.py`. The decision agent re-read only the draft audit; other figures are quoted from the earlier documents and were not re-checked in that step.*

## Decision: build-lean (confidence 0.72)

Build it, but only as the roughly 400-line kernel the audit identified, with its measured holes closed, and with no comparative claim until a same-task run exists.

All three critiques return "conditional" at 0.72, so there is no majority to weigh; they agree on the evidence, and I weighed that.

**Why not do-not-build.** Three things are absent from Spec Kit, BMAD, Superpowers and plain Claude Code, and each has evidence behind it:
- **Prose rules failed, measured.** Over 294 swarm agents every rule was already written and still broken. External work agrees: telling a model not to cheat moved nothing (80% to 80%) while structural controls drove cheating near zero.
- **Done as an exit code on content, not a model's claim.** The other three frameworks enforce by prompt text; none has a tamper control, a mutation step or a script-written done.
- **An honest abort exit is cheap and evidence-backed.** An explicit "this is impossible" option cut cheating from 54% to 9% on an ImpossibleBench variant.

These concern ground truth and tamper resistance, which matter more as models produce more unreviewed change per hour. That is the synergy with future models.

**Why not a full build.** The 18-principle package would mostly restate vendor guidance (P2, P4, P6, P13) and the other frameworks, and would carry the source project's scar tissue:
- The two largest recorded wastes were the owner's own rules: the judged swarm, and the step cap at about 90M tokens per outcome.
- The draft's bundled frugality guard, forced retro layer, crawled research, keyword score and six stage files are the parts the audit calls over-engineered.
- Adoption cost is the highest of the five options and it is Claude Code only.

**What "100 times powerful" can honestly mean.** Not a multiplier; that is unmeasured and must not be claimed. The power is that one small mechanism (outcome, proof seen red, protected proof, script-written done on a content hash) holds at any model capability, and every other component carries an off-switch and is deleted when an on/off run shows it no longer pays.

The decision turns to do-not-build if the kernel cannot be made tamper-resistant, or if the on/off run against a no-process control shows no gain in escaped defects or rework at acceptable cost.

## What the validation found

The validation ruled on all 224 clusters across the six areas with none left unruled: 93 keep, 52 refine, 48 merge, 31 drop, and 78 earlier rulings overturned. The result is 18 principles, 17 rated durable and one (P18) rated a model workaround.

The evidence under those principles is thin in a specific way:
- **Real before/after figures exist for only a few rules.** Outcome-first reached a host proof in about 2 hours against 14 hours, 81 agents and 23 REVISEs of 30 verdicts. One script answered in about 4 minutes what 106 killed agents did not. Eight integration tests took about 8 tool calls and 128 s against about 450 tool calls and 830k tokens for about 40 hand-driven legs. Invariant batching cost about 200k tokens against about 3.4M (17x). Each is a single self-measured instance.
- **Most other principles count waste before a rule, not a saving after it.** P5, P6, P8, P10, P14 and P15 say so in their own caveats, and directives #61, #62, #64 and #66 have no after-figure.
- **The source project is its own counter-example.** 53% of commits touched no product or test code, with 68 directives and 204 governance scripts; no successful real install-to-first-order is recorded, and the one real-backend run stopped on a 403 no fake produced.
- **The draft toolkit is not shippable.** I read audit.json in this step: both suites pass (38/38 and 25/25) while forged ledger lines turn a failing gate green, Bash writes bypass the guard, a plain commit stales every proof, hooks.json points at a file not in the package, and trivially passing proofs are accepted. The audit puts the valuable part at about 400 of about 2,950 authored lines.
- **No same-task comparison exists** against Claude Code alone, Spec Kit, BMAD or Superpowers. The only controlled data cited (the Uvik vendor benchmark) has the no-process control cheapest and fastest, and equal to BMAD on small tickets.

Only audit.json was re-read here; every other figure is quoted from the supplied method, comparison and critique text and was not re-checked against pos.json, practices.json or models.json.

## Rulings on the 1,856 instructions

| area | rule clusters | keep | refine | merged as duplicate | drop | overturned by the skeptic | instructions left unruled |
|---|---|---|---|---|---|---|---|
| frugality | 25 | 6 | 5 | 6 | 8 | 8 | 0 |
| project-management | 43 | 21 | 10 | 7 | 5 | 8 | 0 |
| outcome-driven | 33 | 12 | 9 | 7 | 5 | 19 | 0 |
| verification | 44 | 20 | 11 | 10 | 3 | 16 | 0 |
| decisions-learning | 42 | 20 | 11 | 7 | 4 | 15 | 0 |
| safety | 37 | 14 | 6 | 11 | 6 | 12 | 0 |
| **all** | **224** | **93** | **52** | **48** | **31** | **78** | **0** |

Every cluster, with its verdict, evidence and the instruction ids it covers: [09](09-rulings.md) and `data/validation/areas.json`. The method built from the surviving rules: [08](08-refined-method.md).

## Compared with Claude Code alone, Spec Kit, BMAD and Superpowers

Sources are the research files `speckit.json`, `bmad.json`, `superpowers.json`, `practices.json`, `pos.json` and `audit.json`; "ODD" is the refined method. No run of ODD against the other four on the same tasks exists, so every ODD cell is self-measured and the cost rows are not comparable across columns.

| Dimension | ODD (refined method) | Claude Code alone | Spec Kit | BMAD | Superpowers |
|---|---|---|---|---|---|
| Core unit of work | One user-visible outcome sentence plus one end-to-end proof test (P1) | The prompt or session; plan mode and task lists are built in (speckit.json weaknesses/10) | A feature spec, refined into plan and tasks (speckit.json what_it_is) | Epic, then story or ticket, sized by four planning paths (bmad.json what_it_is) | A brainstormed design, then plan tasks of 2-5 minutes (superpowers.json what_it_is) |
| Artifacts and volume | Outcome, proof, one short defect record; plan or design only when risk requires (P1). The earlier draft toolkit needed six stage files for a one-line fix (audit.json) | None required beyond a short CLAUDE.md (practices.json item 8) | Constitution, spec, plan, tasks, checklists, design files. Measured: 2,577 lines of markdown for 689 lines of code; 8 files and about 1,300 lines to display a date (Eberhardt, Zaninotto) | PRD, architecture, DESIGN, EXPERIENCE, story files, `tickets.toml`; 43.9% of tokens spent on spec (Uvik) | Design, plan file, worktree, git-ignored ledger; skill bodies total 3,150 lines (issue #832) |
| Enforcement | Hooks, gate scripts and a done-script for the no-exception rules, prose for the rest (P6, P8). No before/after shows the hooks reduced violations | Whatever hooks and deny rules the user writes; the vendor's own split is prompt = "no guarantee", hook = deterministic (practices.json item 8) | Prompt text. Checklist gate is a question to the user; "extension hooks" are prompt-interpreted in 0.8.11; bash scripts check only that files exist. 1.2.6+ workflow engine not inspected | Prompt text plus human checkpoints; thin `tickets.py`; Build Auto halts on named blocked outcomes and after 5 review iterations. Skill source not read | Prompt text only. One SessionStart hook that injects the bootstrap; no PreToolUse or Stop hook; force comes from capitals, "iron laws" and rationalization tables |
| Definition of done | Only a script writes done; one gate result on one content hash; proof and review on the same tree (P8, P10) | The model's claim unless the user supplies a check; guidance is "give Claude a check to run" (practices.json) | Checklists ticked and `/speckit-converge` reporting "Converged", a model judgement. "Verify implementation" was seen ticked with no tests written (Zaninotto) | Build leaves the ticket at `built`; only a human or orchestrator marks done. A false "complete" on a 9+ hour auth build is reported second-hand | "No completion claims without fresh verification evidence", self-applied; ends at a reviewed green branch |
| Verification and test quality | Proof seen red on the unfixed tree; diff-derived mutants on high-risk changes; coverage a floor only; real-system run before "proven" (P9, P12). Mutation generator cost about 600k tokens with no speedup | No built-in standard | Test-first article in the constitution and "prefer real databases over mocks", both advisory; no proof requirement found in converge | Tests only "if your project has a test suite"; verification is a review lens (Verification Gap Finder), not a gate | Strict RED-GREEN-REFACTOR skill, code written before its test is deleted; nothing checks it happened. No mutation or real-system step |
| Learning across runs | A defect adds a check, not a prose rule; rules carry a date and incident and are deleted when covered; size budget by script (P4). The source project is also the counter-example: charter bytes grew 227,205 to 361,883 in four weeks | CLAUDE.md and memory, by hand | Constitution, written once; specs live for one change ("spec-first only, not spec-anchored", Boeckeler) | Retrospective per epic, `.memlog.md`, `deferred-work.md`; spec drift 12.2% (Uvik) | None shipped: the memory skill was "built but not wired" (launch post). Skills themselves are pressure-tested before release |
| Token and time cost evidence | Self-measured single instances: about 2 h against 14 h and 81 agents; about 200k against about 3.4M tokens (17x, one instance). Project total spend unrecorded (pos.json) | Cheapest and fastest arm: $2.43 per merged ticket, 29 min median, 72% merge, 0.86 review defects (Uvik no-spec control) | $3.33 per merged ticket, 44 min, 80% merge, 0.57 defects; 34% of tokens on spec (Uvik). Roughly 10x slower on one CRUD feature (Eberhardt) | $4.23 per merged ticket, 55 min, 82% merge, 0.49 defects, 0.46 rework rounds; most expensive and slowest arm (Uvik). 230M tokens in a week is a second-hand report | Core under 2,000 tokens, about 100k for a sample todo app (Willison). A 12-session test (about 14% fewer tokens) was seen only in search summaries and is unverified |
| Human review burden | Human reviews the proof and one gate result, and performs owner-only acts (P16). Not measured; the source project produced 733 rulings in 44 days | The code diff: about 24 min of review and testing in Eberhardt's baseline | Highest on record: 3.5 hours of review for one feature; "I'd rather review code than all these markdown files" (Boeckeler) | Plan approval, open questions, marking done; spec review effort rated 2 of 5, lowest of the arms (Uvik) | Design approval, then low: the controller logs rulings and stops only for irreversible, security-sensitive or external actions |
| Scaling to task size | Tier computed from the diff by script; a small-change lane is proposed, not yet shown working (P3, additions) | Best on small tickets (85% merge, equal to BMAD); falls to 50% on large tickets (Uvik) | One pipeline; excessive for a 3-5 point story (Boeckeler). README now calls the steps "independent entry points" | Explicit paths including "trivial: BMAD optional"; held 80% merge on large tickets against 50% for no-spec (10 tickets) | One ceremony level: the "1% chance" rule applies to small tasks too; serial implementers by design |
| Future-model durability | 17 of 18 principles are about ground truth, enforcement and human-owned acts; step and read limits are settings with a retirement test (P18). Untested across a model upgrade | Fully durable by definition; improves with each model | Guided steps expected to matter less as agents improve (Eberhardt); 106-372 line skill prompts; instruction bloat and context rot named by Thoughtworks | Model- and harness-neutral by policy, but v4, v6 and v7 break installs, commands and roster | Wording tuned by pressure-testing against current models; capitals and absolute emphasis; skills dropped out silently past a 15,000-character description budget |
| Adoption cost | Highest: hooks, gate scripts, evidence store and ledger must be built and each needs fixture tests; no public package | Zero | `uv tool install`, `specify init`; 43 integrations; vocabulary is a de facto standard | npm or plugin install; 50+ commands and about two months to proficiency (second-hand estimate) | One plugin install, 16 harnesses, no scaffolding |
| Published evidence | One project, self-measured, mostly single instances and waste counts; no successful real install-to-first-order recorded; no comparison run | METR RCT: 19% slower in early 2025, later 4-18% faster with intervals spanning zero; DORA surveys (practices.json) | No first-party data. Hill, ESEM 2026: 88,052 PRs, no defect benefit (measured ticket references, not Spec Kit output). Uvik vendor benchmark. Thoughtworks Radar: Assess | No first-party data; `bmad-eval` harness exists with no published scores. Uvik vendor benchmark only | No first-party data; 316.1k stars; the author records early skill tests scoring "perfect" and being wrong |

### Where the refined method is ahead

- Enforcement is mechanical where the other three are prompt text. Spec Kit's gates and extension hooks are model-interpreted (speckit.json enforcement), BMAD's docs show no hooks or merge gate in the user's project (bmad.json enforcement), and Superpowers registers only a SessionStart hook that injects text (superpowers.json enforcement, hooks/hooks.json). ODD puts the no-exception rules in hooks and gate scripts (P6), which is what the vendor guidance prescribes: "If something has to happen every time, make it a hook" (practices.json item 8). Limit: the source repo measured prose failing (294 agents, every rule already written and still broken) but has no before/after showing the hooks reduced violations.
- Done is written by a script on a content hash, not claimed by the model. This targets the failures recorded for the others: "verify implementation" ticked with no unit test under Spec Kit (Zaninotto, speckit.json weaknesses/4) and a 9+ hour BMAD build "erroneously marked as complete" (bmad.json weaknesses/7, second-hand). Superpowers' verification rule is self-applied prose. BMAD comes closest by never letting the build mark done, but the check behind that is a human, not a script.
- Proof quality is specified; the others only specify that tests exist. ODD requires a proof seen to fail on the unfixed tree and diff-derived mutants on high-risk changes (P9), in line with mutation score tracking real-fault detection independently of coverage (Just et al., practices.json item 4). None of the three frameworks has a mutation step or a harness self-check. Superpowers has red-first, unenforced.
- The proof is kept out of the implementer's reach (P8). The research finding is that telling a model not to cheat moved nothing (80% to 80%) while structural controls did (METR and ImpossibleBench, practices.json item 6). None of Spec Kit, BMAD or Superpowers has a tamper control in the files read. Limit: the draft ODD toolkit failed this itself (forged ledger lines turned a gate green, audit.json), so it is a design intent, not a demonstrated property.
- A real-system proof is required before an outcome is called proven (P12). Superpowers ends at a reviewed green branch and BMAD at `built`; Spec Kit's converge loop is a model's reading of code against markdown. Limit: the source project has no successful real install-to-first-order on record, so ODD states this requirement without having met it once.
- Artifact volume is lower by design: one outcome sentence and one proof against 2,577 lines of markdown for 689 lines of code (Eberhardt) or 43.9% of tokens on spec (Uvik, BMAD arm). The durable artifact is an executable test, which cannot drift silently, against measured spec drift of 12.2% for BMAD. Limit: ODD's own artifact count has not been measured on a small change, and its draft required six stage files for a one-line fix (audit.json).
- It measures itself and deletes rules (P4). Spec Kit, BMAD and Superpowers publish no first-party measurements (each file's evidence_of_effectiveness), and Superpowers answered a 69% trim proposal with experience rather than data (issue #832). ODD ships a transcript cost ledger and a remove-if-no-after-figure rule. Limit: its own project total is unrecorded and several of its rules have no after-figure.
- Unattended runs are bounded in code (agent or token cap, harness-decided progress, round limit; P5). BMAD has a 5-iteration cap and named blocked outcomes and Superpowers a 5-round fix cap with escalation, both run by the model; Spec Kit has none in the files read. ODD adds a spend cap and a progress test the agent cannot satisfy with bookkeeping. Limit: all the supporting figures measure waste before the caps; none records a cap saving a run.
- Parallel work is isolated by computation (disjoint file sets, worktree lease, per-session state; P14). Spec Kit's `.specify/feature.json` is a single repo-global pointer that parallel agents clobber (speckit.json weaknesses/12); Superpowers avoids the problem by forbidding parallel implementers; BMAD's Build Auto handles one ticket per invocation.
- Model-specific scaffolding is separated out as settings with a retirement test (P18). The others bake it into prose: Superpowers' capitals, absolute emphasis and 2-5 minute steps, Spec Kit's 106-372 line skills, BMAD's command surface that broke across v4, v6 and v7.

### Where the others are ahead

- Claude Code alone is the cheapest and fastest on small work, and no data shows ODD beating it. The no-spec control cost $2.43 per merged ticket and 29 minutes median, with an 85% merge rate on small tickets equal to BMAD's (Uvik; bmad.json lessons/12). ODD's source project is the cautionary case, not the counter-evidence: 53% of commits touched no product or test code, with 68 directives and 204 governance scripts (pos.json).
- All three frameworks have something ODD lacks entirely: independent, third-party data. Spec Kit and BMAD have a blind-reviewed 50-ticket benchmark showing fewer review defects than no-spec (0.57 and 0.49 against 0.86) and fewer rework rounds (Uvik, a vendor study with a stated ±10 point noise band); Spec Kit also has an ESEM 2026 paper and a Thoughtworks Radar entry. ODD has one project, self-measured, mostly single instances.
- Adoption cost. Superpowers is one plugin install across 16 harnesses with a core under 2,000 tokens (superpowers.json strengths/0-1); Spec Kit is one CLI with 43 integrations and a vocabulary people already share. ODD requires hooks, gate scripts, an evidence store and a ledger, each needing its own fixture tests, and its draft package shipped a hook pointing at a file that was not in it (audit.json).
- BMAD on large and multi-person work. It held an 80% merge rate on large tickets where no-spec fell to 50% (10 tickets, Uvik) and it covers research through retrospective (bmad.json strengths/0, /3). ODD has no discovery, product or UX stage and no way to get several people to agree on a requirement; it assumes the outcome sentence already exists.
- Front-end clarification. Spec Kit's `[NEEDS CLARIFICATION]` marker and bounded clarify step (at most 5 questions), and Superpowers' brainstorming skill, handle a vague request. ODD's P7 demands observable criteria but has no step for getting from a vague ask to an outcome; its only signal is "rulings per requirement keep rising" (P16), which fires late.
- Superpowers' rules are tested on the model before they ship. Each skill is pressure-tested on subagents under realistic temptation and reworded after failures (superpowers.json principles/5). ODD tests its enforcers with fixtures (P6) but its skill text and prose rules have no equivalent test.
- Superpowers' subagent protocol is more concrete than ODD's P13: a brief containing only the task, its interfaces and constraints; reviewer works from a BASE..HEAD diff file with two verdicts; fix rounds 1-3 with the same implementer, 4-5 escalated a model tier, then parked with a ruling (superpowers.json what_it_is). ODD says "one fresh-context reviewer" and "bounded rework" without that detail.
- BMAD and Spec Kit state plainly when not to use them: BMAD's "trivial: BMAD optional" path and "a PRD only when several people must agree"; Spec Kit's README now calls its steps "independent entry points, not mandatory phases". ODD's small-change lane is still a proposed addition.
- Portability. Spec Kit (43 integrations), Superpowers (16 harnesses) and BMAD (no vendor lock-in by policy) work outside Claude Code. ODD's hooks, deny rules and workflow scripts are Claude Code mechanisms.
- Compaction survival is solved in Superpowers and only stated in ODD: its SessionStart hook re-fires on `startup|clear|compact` and progress lives in a per-plan ledger (superpowers.json strengths/4). ODD's P15 says to resume from committed files but names no re-injection mechanism.
- Honesty about process theatre. BMAD's docs say "one model voicing five personas tends to make them agree" and offer separate contexts only where independence matters. ODD reached the same conclusion only after 14 hours, 81 agents and 23 REVISEs of 30 verdicts.

### What to borrow from them

- From Spec Kit: an explicit ambiguity marker in the outcome block ("don't guess") and a clarify step capped at 5 questions before any proof is written. This fills ODD's missing front end (speckit.json lessons/0-1).
- From Spec Kit: a read-only cross-check of outcome, criteria and tasks before work starts, kept as a script where possible. Take the converge idea of re-checking the result against the intent, with the executable proof as the oracle instead of a model reading markdown (speckit.json lessons/1, /3).
- From BMAD: a written "this is trivial, use Claude Code alone" path as the first branch of the method, plus BMAD's unit size of about one session or roughly 500 changed lines (bmad.json lessons/0, /3). The benchmark shows no-spec matches the heaviest framework on small tickets.
- From BMAD: review triage rules. Each finding is verified at its named location, each dismissal carries a recorded reason, and a problem the change caused is never deferred (bmad.json strengths/5). This is a direct answer to ODD's own record of REVISEs that named no product defect.
- From BMAD: a Baseline mode that runs the same case with and without the method, three runs per case with a no-partial-credit grader (`bmad-eval`). ODD proposes on-versus-off measurement but has no harness; BMAD has the harness and no published scores, so publishing is where ODD could lead (bmad.json lessons/5).
- From Superpowers: the SessionStart bootstrap that re-fires on `startup|clear|compact`, so the short always-loaded file and the hook health check survive compaction (superpowers.json lessons/4).
- From Superpowers: the task brief format (task, interfaces, global constraints, no pasted history), the reviewer working from a diff file, and the fix-round ladder of 3 rounds then escalate a model tier then park with a ruling (superpowers.json lessons/6). Adopt these as the concrete form of P13 and P5.
- From Superpowers: pressure-test each prose rule or skill on a subagent under realistic temptation before shipping it, with a passing control. Use it as the entry test for any rule that stays as prose, and measure whether a rationalization table changes behaviour before keeping one (superpowers.json lessons/8, /12).
- From Superpowers: state in the bootstrap that user and project instructions outrank the method's skills, and keep a short stop list for autonomy (irreversible, security-sensitive, external side effects). ODD's P16 list is longer; the short list is easier to teach.
- From Superpowers' own failure: add a check that the method's skill descriptions fit the harness's description budget, since skills past 15,000 characters dropped out silently (superpowers.json weaknesses/1). Anything load-bearing stays in a hook or script.
- From the Uvik benchmark design: the comparison ODD needs before any claim. Same tickets, a no-process control, blind review, reporting merge rate, cost per merged item, median time, review defects, rework rounds and the noise band (speckit.json lessons/12, /14). The bar to clear is known: Spec Kit cost about a third more and about 50% more time than no-spec for a modest defect gain.

### Overlap

**Verdict.** About half of ODD restates what Superpowers, BMAD or Spec Kit already say; what is its own is mechanical enforcement, a proof the implementer cannot edit, mutation-checked proofs, content-hashed evidence, real-system proof and self-measurement. No head-to-head run exists, so none of this is a measured advantage. All four sources looked for a controlled comparison and found none for any of these methods against each other (practices.json unverified/7).

**Where ODD duplicates the others**

| ODD principle | Already in | Difference |
|---|---|---|
| P9 red-first proof | Superpowers TDD "iron law"; Spec Kit constitution Test-First article | ODD records the red run by script and adds mutants; the idea is the same |
| P10 and P8 "no done without evidence" | Superpowers verification-before-completion; BMAD "build never marks done" | ODD keys evidence to a content hash and has a script write done |
| P13 fresh-context reviewer | Superpowers task reviewer; BMAD reviewer lenses | ODD runs scripts first and limits it to one reviewer; Superpowers' protocol is more detailed |
| P14 one worktree per runner | Superpowers using-git-worktrees | ODD adds a computed disjoint-file check and a lease |
| P15 ledger and repo as state | Superpowers per-plan ledger; BMAD `tickets.toml` and `.memlog.md` | ODD commits it and derives boards; Superpowers' ledger is git-ignored |
| P5 bounded rework | BMAD 5-iteration halt; Superpowers 5-round cap with escalation | ODD puts the cap in workflow code and adds a spend cap |
| P7 done, incomplete, blocked | BMAD named blocked outcomes; Superpowers implementer statuses (DONE_WITH_CONCERNS, NEEDS_CONTEXT, BLOCKED) | Same idea; ODD adds a schema |
| P3 process sized to risk | BMAD four planning paths; Spec Kit independent entry points | ODD computes the tier from the diff; BMAD lets the agent or human choose |
| P16 owner-only acts | Superpowers stop list; BMAD human-in-the-loop | Same idea; ODD adds fail-closed target guards |
| P1 traceability to an outcome | Spec Kit "no speculative features", requirement-to-task tracing | ODD traces to one outcome sentence, not a spec |
| P11 search before writing | No equivalent in the three | Duplicate generation is a reported Spec Kit failure (Boeckeler), so this is a gap ODD fills, not a duplicate |

**Overlap with Claude Code alone.** P4 (short always-loaded file), P6 (hooks for the no-exception rules, a small enforced set), P13 (fresh subagent review, skip style) and P2 (give the agent a check to run) are the vendor's own published guidance (practices.json item 8). For those four, ODD is a worked implementation of documented practice, not a new method.

**Things to keep in view**
- The Uvik benchmark is one vendor study on private code. The two files give two URLs for it (`uvik.net/blog/spec-driven-development-benchmark/` and `uvik.net/spec-driven-development-benchmark/`); I did not resolve which is correct.
- The Superpowers 12-session token figure, the BMAD 230M-token and two-month figures and the 9+ hour false-done report are second-hand in the source files.
- BMAD's skill source and Spec Kit's 1.4.0 hook engine were not read by the researchers, so "prompt-only enforcement" for those two rests on documentation and a vendored 0.8.11 copy.
- This step read only the three framework files and practices.json in full. The ODD figures are quoted from the method text supplied, not re-checked against pos.json or audit.json.

## The three critiques

### Skeptic: adds value "conditional" (confidence 0.72)

**On the way of working.** Sound as a set of habits, not yet as a taught method. The refined core is well supported: one outcome sentence plus one end-to-end proof (P1), scripts for mechanical questions (P2), changing the shape of work instead of adding checks (P3), and enforcing a few no-exception rules in code (P6, P8). These are the only places the POS ledger has a real before/after: 17x on invariant batching, 4 minutes against 106 agents, about 11x per device leg, about 2 hours against a 14-hour swarm (pos.json honest_assessment). Each is a single instance measured by the session that built it.

Against teaching it as it stands:
- The source project is the counter-example for its own method. 53% of commits touched no product or test code, with 68 directives, 28 policies and 204 governance scripts; the judged swarm and the step cap were the two largest recorded wastes and both were the owner's rules (pos.json honest_assessment).
- The central product outcome is unproven. The only real-system run failed on a 403 no fake produced, and no successful install-to-first-order is recorded. P12 states a requirement the project never met.
- 18 principles is still too many to learn. About half restate Superpowers, BMAD or Spec Kit, and P2, P4, P6 and P13 are the vendor's published guidance (comparison overlap table).
- Most supporting evidence counts waste before a rule, not a saving after it. P5, P6, P8, P10, P14 and P15 each say so in their own caveat.

What I concede: outcome plus proof seen red, done written by a script on a content hash, proof files the implementer cannot edit, and owner-only acts. These are about ground truth and tamper resistance, which get more important as models run longer unattended, and no other framework enforces them mechanically.

**Is it good for others to learn?** Partly. Worth learning by anyone running agents unattended or on high-stakes code:
- State one user-visible outcome and one end-to-end proof, and see the proof fail first.
- Ask whether a command can answer before spawning an agent.
- Put the few no-exception rules in hooks and keep the proof and the done record out of the implementer's reach.
- Tie every result to a content hash, and call nothing proven until it has run on the real system.
- Name the owner-only acts once.

These fit on one page and need the roughly 400-line kernel, not a framework.

Not for others as it stands:
- The orchestration layer (waves, tiers, batch trains, ledgers, locks) solves problems created by running dozens of agents on one repo; most teams never reach it.
- For small or routine tickets the evidence favours plain Claude Code.
- For multi-person requirement agreement, discovery and UX, BMAD or Spec Kit cover ground this method does not.
- For a low-cost install with a tested subagent protocol, Superpowers is ahead.

The most useful thing the owner could publish is the measured ledger of what was waste (the swarm, the step cap, directive volume, 733 rulings in 44 days). It is rarer and more credible than the method.

**Reasoning.** The toolkit adds value only if it shrinks to the part Claude and the three frameworks do not already supply, and only once it is measured against a no-process control.

Why not "yes":
- No head-to-head run exists. Every ODD figure is self-measured, and the only controlled data in the evidence (the Uvik benchmark) has plain Claude Code as the cheapest and fastest arm, matching the heaviest framework on small tickets.
- The draft toolkit failed its own claims when audited (audit.json). Forged ledger lines turned a failing gate green. Bash writes bypassed the write guard. A plain commit staled every proof. Its hook pointed at a file not in the package, which blocks every matched tool call. It accepted trivially passing proofs and a free "red: n/a" exit. Both of its test suites passed (38/38 and 25/25) while all of this was true.
- The audit puts the valuable part at about 400 lines of roughly 2,950; the rest is ceremony the refined method itself now drops.
- Adoption cost is the highest of the five options, and it is Claude Code only.

Why not "no":
- Prose demonstrably failed in this repo: over 294 agents every rule was written and still broken. External evidence agrees that telling a model not to cheat moved nothing (80% to 80%) while structural controls did.
- Spec Kit, BMAD and Superpowers enforce by prompt text; none has a tamper control, a mutation step or a script-written done. That gap is real, and Claude alone does not fill it unless the user writes the hooks.
- An explicit abort option cut cheating from 54% to 9% in external work, so the honest-exit schema is cheap and evidence-backed.

Net: a roughly 400-line kernel (outcome block, red-then-green recorded on a content hash, protected proof and ledger, one gate exit code, park with a reason, a doctor command) is worth shipping. The 18-principle method as a packaged toolkit is mostly a restatement of vendor guidance plus project scar tissue.

I read audit.json in full structure, the pos.json honest assessment and the models.json rules; the other figures are taken from the method and comparison text supplied and were not re-checked.

**Must cut**

- P18 as a shipped component: tool_guard read/wait/range rules, step caps and step shapes are a separate frugality product whose only measured effect is higher cost (about 90M tokens per outcome under the cap). Leave a note, not code.
- P5's workflow machinery (agent caps, progress tests, can-finish checks, health script) from the core package: every figure measures waste the owner's own swarm created, and no after-figure shows a cap saving a run. Keep only a round limit and the no-polling rule as text.
- P13 and P14 as toolkit features: fresh-context review and worktree isolation are already in Claude Code and Superpowers. Keep one paragraph each, no agents or lease scripts.
- P15's ledger-derived boards and P3's tier-from-diff, batch-gate and red-attribution scripts: project-scale orchestration that a single developer or small team never reaches.
- P11 as one principle: it bundles nine habits. Keep 'completeness claims carry their query' and 'search for existing code first'; move the rest to skill text or drop.
- From the draft toolkit: six mandatory stage files, mandatory crawled research, the 0-100 keyword outcome score, the forced retro and self-heal layer, the five-level trace chain, the judge-share knob, 30-second nodes and the three overlapping principle documents (audit.json over_engineered).
- Any comparative or '100x' or 'frugal' claim, and the unverified figures (18 judge rounds and 12M tokens, the 22.2M projection, the pinned-model incident, the 6.3M audit figure), until re-cited.
- The 18-principle count itself: teach at most six or seven (outcome and proof, script over agent, enforce few rules in code, protected proof, evidence on a content hash, real-system proof, owner-only acts); the rest is reference material.

**Must add**

- A first branch that says 'this is trivial, use Claude Code alone', and a small-change lane of one file with outcome, proof and boundary. Without it the toolkit will be switched off for most real work (audit.json missing).
- A controlled comparison before any claim: the same tickets through a no-process control, Spec Kit, BMAD, Superpowers and ODD, with blind review, reporting merge rate, cost per merged item, median time, review defects and rework rounds.
- An on/off harness per component, run at each model upgrade, with deletion when outcome and cost hold with the component off (models.json RULE 2, RULE 14).
- Tamper resistance that actually holds: control files written only by the tool, a hash-chained ledger, and a gate-time diff against the boundary so shell write routes are covered (audit.json measured both bypasses).
- Proof strength check: break or revert the change and require the proof to go red; remove the free 'red: n/a' exit or cap and report its use.
- Content-scoped staleness keyed on the hash of files inside the outcome's boundary, so a commit or unrelated edit invalidates nothing.
- Per-session run state and a doctor command that reports whether each hook is installed and live; a packaging test that every file named in hooks.json exists.
- One recorded successful real-system run of the method's own flagship outcome (install to first order) before P12 is taught as practice.
- A clarify step for vague requests, capped at about five questions with an explicit 'do not guess' marker (borrowed from Spec Kit); the method currently assumes the outcome sentence already exists.
- A hard cap on the enforced set (around ten hooks) with a date, incident and expiry on every rule, so the toolkit cannot regrow into 68 directives and 204 scripts.

**Risks**

- Regrowth: the same owner and process produced 204 governance scripts and charter bytes growing from 227,205 to 361,883 in four weeks; a toolkit with a 'learn' loop repeats this by design.
- False assurance: the draft's suites were green while the gate was forgeable; enforcers that are wrong are worse than none (the step-cap guard double-counted for four weeks while its suite passed 36/36).
- Net cost on small work: the only controlled data shows plain Claude Code cheapest and fastest with equal merge rate on small tickets; ODD may be a pure tax there.
- Evidence base is one project, self-measured, mostly single instances, with no successful real-system proof of the product outcome; publishing it as validated would overstate it.
- Maintenance burden and lock-in: hooks and workflow scripts are Claude Code specific and each needs fixture tests; harness changes can silently break them, and fail-open hides the break.
- Obsolescence: P2, P4, P6 and P13 are already vendor guidance; future models and harness features may absorb more, leaving the toolkit as dead weight unless the on/off test is actually run.
- Stop-hook and boundary friction lead users to park or disable by reflex, which empties the gate of meaning (audit.json failure_modes).
- Shell-executed proof commands written after reading crawled pages are an injection route (audit.json failure_modes).

### Practitioner: adds value "conditional" (confidence 0.72)

**On the way of working.** DONE (check: audit.json read in this step; pos.json honest_assessment read at line 120; the other ODD figures are taken from the supplied method text and were not re-checked).

As a practitioner I would adopt the core tomorrow and leave most of the rest. The refined method is sound in its judgement but still too large to learn: 18 principles, most of them paragraphs carrying four to eight sub-rules, is a handbook. The comparison text itself rates ODD's adoption cost "Highest" and notes there is no public package.

What is worth teaching others, in order of evidence:
- **Outcome plus proof (P1).** One outcome sentence, one end-to-end proof, stop when proven. This has the strongest single data point (about 2 hours against a 14-hour, 81-agent swarm) and audit.json calls the outcome block "the only genuinely new idea, and it is good".
- **Script over agent (P2) and batch by invariant (P3).** These are two of the three results with a real before/after (pos.json honest_assessment), and they need no tooling to adopt.
- **Red-first proof and a script-written done on a content hash (P8, P9, P10).** This is the real difference from Spec Kit, BMAD and Superpowers, where done is a model's claim.
- **Owner-only acts and main-is-production (P16, P17).** These are cheap, incident-backed and true for any model.
- **Measure and delete (P4).** This is the right discipline, but the source project is its own counter-example: 68 directives, 204 governance scripts, and 53% of commits touching no product or test code.

What is sound but not something to teach first: P5, P13, P14 and P15 only matter once you run unattended multi-agent work, which most adopters will not do on day one. P11 is seventeen merged rules in one paragraph and reads as a checklist, not a principle. P12 states a real-system requirement the source project never met once.

The owner's way of working, as lived, is not the thing to copy; the refined residue is. The honest lesson for others is that shape changes paid and added checking did not.

**Is it good for others to learn?** Yes for the small core, no for the whole.

**Who gains:** a solo developer or small team shipping a real product with Claude Code who has been burned by "done" that was not done. For them, six habits pay on day one with no install: one outcome sentence and one proof per change; write a command before spawning an agent; see the proof fail first; let a script, not the model, say done; name the acts only the owner performs; delete any rule without a number behind it. The enforcement layer (write guard, gate, park) is worth adding once those habits are in use, in about 400 lines.

**Who should not adopt it:** anyone doing small tickets where plain Claude Code already merges at the same rate for less, teams needing discovery, product or UX stages or multi-person agreement (BMAD covers that; ODD does not), and anyone not on Claude Code.

**Learning time:** the six-habit version is learnable in under an hour from one page and one example. The 18-principle version is not, and the comparison text's own adoption-cost row says so.

**Durability:** the core is about ground truth, exit codes and human-owned acts, which hold for any model. The step and read limits are the part to leave behind.

**Reasoning.** **Why conditional and not yes.** A toolkit adds value over Claude Code alone only if it is the roughly 400-line core the audit identified: outcome block, red-then-green ledger tied to content, write guard, gate with park. The draft was about 2,950 lines and about 60 concepts, needed six stage files for a one-line fix, and could be defeated through Bash writes or forged ledger lines (audit.json). In that form it is waste and would be switched off for most real work.

**Evidence that limits the claim:**
- No head-to-head run exists. The only independent benchmark cited shows plain Claude Code as the cheapest and fastest arm, matching the heaviest framework on small tickets.
- Most "paid" figures are single instances measured by the session that built the change.
- #61, #62, #64 and #66 have no after-figure.
- The measured failure of prose rules is real (294 agents, every rule written and still broken), but no before/after shows the hooks reduced violations.
- The central product outcome was never proven on the real system.

**Why not no.** Three things are absent from the alternatives and cheap in their small form: done as an exit code on a content hash, a proof seen to fail first, and the proof kept out of the implementer's reach. External evidence supports the structural approach (hiding tests drove cheating near zero, while telling the model not to cheat moved nothing).

**Condition for yes.** Ship the small core with a two-minute start and a doctor command, make everything else opt-in, and run the same tickets against a no-process control before making any comparative claim.

**Must cut**

- Cut the default surface from 18 principles to about 6: outcome plus proof, script over agent, red-first proof with script-written done on a content hash, proof out of the implementer's reach, owner-only acts, measure and delete. Move the rest to an opt-in 'unattended and parallel work' module (P5, P13, P14, P15) and a reference appendix (P11 sub-rules).
- Cut the six mandatory stage files, the mandatory crawled research, the five-level trace chain and the 30-second nodes from the toolkit (audit.json over_engineered). A one-line fix must cost one file.
- Cut the 0-100 outcome score and the 40-word vague list: keyword regexes that score 'Every user always sees 100 things' at 100 give false confidence (audit.json).
- Cut the forced self-heal and retro layer (learn.py, detectors, lessons with recurrence counts, the second Stop block). Forced learning every run is the same mechanism that grew charter bytes from 227,205 to 361,883 in four weeks.
- Cut the bundled frugality guard (wait, range and read rules, the 30-call step cap, the 3-minute step) from the package. The step cap is the largest recorded waste after the swarm (about 90M tokens per outcome), and it doubles the surface.
- Cut P18 from the taught method: ship it as a settings file that is off by default. A principle that says 'these are not rules' should not occupy a principle slot.
- Cut the judge-share knob and judge gates at four stages; keep one read-only reviewer, and only for high-risk diffs.
- Cut the Stop hook's block on conversational turns; block only a session that wrote code this turn.
- Cut diff-derived mutation batteries from the default path (about 600k tokens with no speedup); keep the single 'break the change, the proof must go red' check.
- Cut every unverified figure before publication: the 18 judge rounds and about 12M tokens, the 22.2M projection, the pinned-model incident, the 6.3M audit figure, and the conflicting 95 KB and 101 KB sizes.
- Cut the three overlapping principle documents down to one page plus the skill.

**Must add**

- A first branch that says 'this is trivial, use Claude Code alone', with a stated size (borrow BMAD's about one session or roughly 500 changed lines). The benchmark shows no-spec equals the heaviest framework on small tickets.
- A small-change lane as the default: one file with outcome, proof and boundary, then red, code, green, done. The fuller pipeline is opt-in.
- A two-minute start: one page, one copyable example run, and a doctor command that reports whether each hook is installed and live. Fail-open without a health check hides absent enforcement.
- A self-contained package with a test that loads hooks.json and asserts every referenced file and skill exists. The draft pointed at a missing hook file and eleven skills that do not exist.
- Content-scoped staleness: key evidence on the content hash of files inside the outcome's boundary so a commit or unrelated edit does not stale every proof.
- Tamper detection by diff at gate time, with control files (ledger, config, active pointer) written only by the tool. This covers shell write routes without trying to parse Bash.
- A clarify step for vague asks, capped at about five questions with an explicit 'do not guess' marker, since the method currently assumes the outcome sentence already exists.
- Per-session active state so parallel sessions and subagents are not blocked by one shared pointer.
- A real-versus-simulated label on every proof, and one recorded successful real-system run before the method claims the requirement works.
- An on-versus-off harness and one published comparison on the same tickets with a no-process control: merge rate, cost per merged item, median time, review defects, rework rounds. Without it the method has no evidence a stranger should trust.
- A brownfield entry: state an outcome for a defect in existing code without inventing requirements around it.
- A SessionStart bootstrap that re-fires after clear and compaction, so the short always-loaded file and the hook health check survive.

**Risks**

- Governance regrowth: the source project turned a frugality method into 68 directives and 204 scripts; a toolkit with a learn loop can do the same to an adopter. Mitigation is a scripted size budget and rule expiry, enforced on the toolkit itself.
- False confidence from a gameable gate: trivially passing proofs, a free 'red: n/a' exit and forged ledger lines were all demonstrated in the draft. A green gate that can be faked is worse than no gate.
- Friction leading to switch-off: strict boundaries that refuse a test file, lockfile or rename, and a Stop hook that nags on questions, will make users disable enforcement within days.
- Unproven advantage: every ODD figure is self-measured, mostly single instances, and plain Claude Code is the cheapest arm in the only independent benchmark. The method may cost more than it saves on small work.
- Enforcer bugs cost more than the violations: the step-cap guard double-counted for four weeks while its own suite passed 36 of 36. Each hook an adopter installs is product code they must maintain.
- Claude Code lock-in: hooks, deny rules and workflow scripts do not port to other harnesses, unlike the three compared frameworks.
- Model drift: P18 defaults and any capitalised or absolute wording may hurt on newer models that follow cautions more literally; the retirement test has never been run across an upgrade.
- The real-system requirement is stated but was never met by the source project, so the method teaches a bar its author has not cleared.
- This review did not re-check the method's figures against pos.json beyond the honest_assessment entry; cited numbers are as supplied.

### Architect: adds value "conditional" (confidence 0.72)

**On the way of working.** Sound as refined, and worth teaching, but as a small core rather than 18 principles. The original way of working (1,856 instructions, 68 directives, 204 governance scripts, 53% of commits touching no product or test code, per pos.json honest_assessment) is not something others should copy; the refinement is. Its lasting parts are the ones that do not depend on how capable the model is: one outcome sentence with one proof (P1), scripts for mechanical questions (P2), a proof seen red first and kept out of the implementer's reach (P8, P9), results keyed to content (P10), real-system proof before 'proven' (P12), owner-only acts (P16) and a measured, shrinking rule set (P4). These get more valuable as models improve, because a stronger agent produces more unreviewed change per hour and the only scalable check is ground truth it cannot edit. Three weaknesses keep it from being a finished method: (1) the evidence is one project, self-measured, mostly single instances, with no after-figure for several rules; (2) the central product claim is unmet, since the only real-backend run on record failed on a 403 no fake produced and no successful real install-to-first-order is recorded; (3) 18 principles with 145 traced rules is still too many to learn, and about half restates Superpowers, BMAD, Spec Kit or vendor guidance. It also has no front end for turning a vague request into an outcome sentence.

**Is it good for others to learn?** Yes, in a reduced form and with its limits stated. What others can learn in an hour and keep across model versions:
1. Start from one user-visible outcome sentence and one end-to-end proof; park everything else as the next outcome.
2. If a command can answer it, write the command; use agents only for judgement.
3. A proof counts only after it failed on the unfixed tree and fails again when the change is broken.
4. The implementer cannot edit the proof, the gate or the done record; only a script writes done, on a content hash.
5. Simulated green gates a merge; only a run on the real system with the shipping artifact proves the outcome.
6. Enforce the few no-exception rules with a tested hook; leave the rest as short prose; delete a rule when a check covers it.
7. Name the owner-only acts once; the agent decides everything reversible and records it.
8. Measure cost per outcome and re-test each piece of scaffolding with it switched off at every model upgrade.

It should be taught with the cautionary half attached: the judged swarm (14 hours, 81 agents, 23 REVISEs of 30 verdicts), the step cap that raised cost, and 733 rulings in 44 days are as instructive as the wins. It is not yet suitable to present as a proven or superior method: there is no same-task comparison with a no-process control or the other frameworks, and for small tickets the available third-party data favours plain Claude Code.

**Reasoning.** Read this step: audit.json (whole, 15 KB), the pos.json honest_assessment and the models.json key list; the method and comparison figures are taken from the task text and were not re-checked against their sources.

(a) The method. Judged three years out, the principles sort into three groups.
- Appreciates with better models: P1, P2, P8, P9, P10, P12, P16, P17 and the measurement half of P4. They concern ground truth, tamper resistance and human-owned acts, none of which a better model makes unnecessary.
- Sound but shrinking: P5, P13, P14, P15, P7. Harnesses will absorb run caps, worktree isolation, per-session state and fresh-context review. Keep them as thin adapters over whatever the harness provides, not as owned scripts.
- Already dead weight: P18's hard forms. The enforced step cap produced about 90M tokens per outcome, and runners were 82% of a 446M-token run. P18 correctly demotes these to settings with a retirement test.

(b) The toolkit. Conditional. The audit's verdict is "INCOMPLETE as a product, sound as a core": about 400 valuable lines (outcome block, red-then-green ledger tied to the tree, write guard, gate with park) inside about 2,950 authored lines. The draft adds value only if all of these hold:
- It is cut to that core plus a small-change lane.
- The measured holes are closed: forged ledger lines turned a failing gate green, Bash writes bypass the guard, a plain commit stales every proof, proofs like a trivially true test are accepted, and a hook points at a file not in the package.
- It defers to Claude Code alone for trivial work. The only third-party benchmark cited has the no-process control cheapest and fastest, and equal to the heaviest framework on small tickets.
- It measures itself on versus off.
As drafted it would be switched off for most real work, and it is waste where it bundles the frugality guard, forced retros, crawled research and a keyword score.

(c) How it improves automatically with better models. Make every component carry its own off-switch and a recorded on/off comparison (proof held, escaped defects, cost per outcome), run at each model upgrade, so the toolkit deletes its own scaffolding. Use no pinned model ids. Write rules as plain reasons rather than emphatic commands, since newer models follow accumulated cautions more literally (the models.json rules as quoted in the method). Let proof strength (mutants killed, real-system pass) be the quality signal rather than process steps completed; that signal stays valid at any capability level.

**Must cut**

- Six mandatory stage files and the five-level trace chain (audit.json over_engineered); replace with one outcome block (outcome, proof, boundary) as the default lane
- Mandatory crawled research citations per requirement; a fix in your own code has no web source, and crawled text can reach a shell through agent-written proofs run with shell=True
- The 0-100 keyword outcome score and the 40-word vague list; the audit showed a vague sentence scoring 100. Proof strength replaces it
- The forced self-heal layer: retro required every run, second Stop block, lessons with recurrence counts, detectors, library file. Forced learning becomes boilerplate and contradicts P4's 'add a check, not a prose rule'
- Bundled frugality product: tool_guard WAIT/RANGE/READ rules, 30-tool-call step cap, 3-minute steps, 30-second nodes. Measured as cost (about 90M tokens per outcome under the cap); ship at most as off-by-default settings
- judge_share_max and judge gates at four stages; keep one fresh-context reviewer after scripts pass, second review only for high-risk classes
- Three overlapping principle documents; keep one page plus one copyable example
- The Stop hook blocking every conversational turn; block only a session that wrote code this turn, otherwise users park by reflex and the gate loses meaning
- The free 'red: n/a' exit without limit or recorded reason reviewed at the gate
- Collapse 18 principles to roughly 7 teachable ones: fold P7 into P1 (criteria belong to the outcome), P10 into P8/P9 (evidence integrity), P11 into P2 (answer from a command run now), P14/P15/P17 into one 'repository hygiene' default that defers to harness features, and keep P18 as settings, not a principle
- Unverified figures before publication: the '18 judge rounds, about 12M tokens' figure, the 22.2M-versus-26.6k projection, the pinned-model incident, the 6.3M-token audit figure, and the conflicting 95 KB and 101 KB instruction-file sizes
- Any comparative or multiplier claim ('100x', 'frugal') until a same-task run against a no-process control exists

**Must add**

- A first branch that says 'this is trivial, use Claude Code alone', then a small-change lane in one file; the fuller pipeline opt-in by computed risk
- Proof strength as the gate: revert or break the change and the proof must go red, recorded by script; this is what stops trivially passing proofs and test-then-touch gaming
- Tamper resistance: control files (ledger, config, active pointer) writable only by the tool, hash-chained ledger entries, and a gate-time diff of changed files against the boundary so shell write routes are covered
- Content-scoped staleness: key evidence on the content hash of files inside the outcome's boundary so a commit or unrelated edit invalidates nothing
- Real-versus-simulated label on every proof and one periodic run on the real system with the shipping artifact, recording each escaped defect as the simulation's error rate; the source project still owes its first successful real install-to-first-order
- Per-session run state keyed by session id, plus a doctor command that reports whether each hook is installed and live, and a test that every file referenced by the hook config exists
- An on/off measurement harness run at each model upgrade: same outcome with a component disabled, comparing tokens, tool calls, wall clock, escaped defects and rework; components that no longer pay are deleted. Include a no-process control and report lead time and change failure rate
- Rule expiry: each learned rule carries date, incident, scope and reason and is reviewed or removed; written in plain sentences without capitals
- A front end for vague requests: an explicit ambiguity marker and a clarify step capped at a few questions before the proof is written (borrowed from Spec Kit)
- An honest 'cannot be done as specified' exit on the outcome itself, treated as a valid result
- Reviewer calibration against a small human-labelled set of past verdicts with an 'unknown' verdict allowed, and review triage that verifies each finding at its named location
- A session-start bootstrap that re-fires after clear and compact so the short always-loaded file and hook health survive compaction (borrowed from Superpowers)
- Exact glob boundary matching with a default allowance for the proof's own test file and a one-command, reason-recording way to widen a boundary
- Brownfield entry: state an outcome for a defect in existing code without inventing requirements or research around it
- A project-total cost script; total spend is not recorded anywhere in the source project

**Risks**

- Evidence base is one project, self-measured, mostly single instances; several rules have no after-figure, so publishing it as validated would overclaim
- The method's central requirement (real-system proof) has not been met once by its own source project
- Governance regrowth: the source project grew charter bytes from 227,205 to 361,883 in four weeks under a rule meant to improve it; a toolkit with a learning layer can repeat this in every adopter's repo
- Enforcer defects are silent and expensive: the step-cap guard double-counted for four weeks while its own suite passed 36/36; fail-open hooks hide absent enforcement
- Harness absorption: caps, worktree isolation, session state and fresh-context review are likely to become built-in, leaving owned scripts as maintenance debt unless they are thin and removable
- Claude Code lock-in: hooks, deny rules and workflow scripts do not port, while Spec Kit, BMAD and Superpowers run on many harnesses
- Adoption cost is the highest of the compared options and no public package exists; without the trivial path and small-change lane it will be switched off
- Stronger models are better at gaming weak proofs; if tamper resistance and proof strength are not real, the toolkit certifies false done with more authority than a model's claim
- This verdict's own limits: method and comparison figures were taken from the supplied text and not re-checked against pos.json, practices.json or the framework files; only audit.json and the pos.json honest_assessment were read in this step

## The lean design the decision calls for

A small-change lane by default: one outcome block (outcome, proof command, boundary), proof seen red then green and red again when the change is broken, recorded on a content hash in a ledger only the tool writes, one gate exit code, and an honest park or cannot-be-done exit; everything else is opt-in and carries an off-switch.

### Skills

- `odd`: The one-page method and entry point. First branch: if the change is trivial (about one session or roughly 500 changed lines is the borrowed unit size; small low-risk edits go to plain Claude Code), do not use the toolkit. Otherwise write one outcome block in one file, run red, code, green, gate. States that user and project instructions outrank the skill, and teaches the cautionary half (swarm, step cap, 733 rulings in 44 days) with the wins.
- `odd-clarify`: Front end for a vague ask: mark ambiguity explicitly ('do not guess'), ask at most five questions, and produce the outcome sentence, an observable acceptance check and the boundary. Covers the brownfield case: an outcome for a defect in existing code with no invented requirements or research.
- `odd-review`: Opt-in, for the project's high-risk classes only. One fresh-context, read-only reviewer spawned after the mechanical checks pass, working from a base-to-head diff. It verifies each finding at its named location, may return 'unknown', sends work back only for a reproduced product defect, and reworks at most a fixed number of rounds before parking.
- `odd-unattended`: Opt-in reference text for parallel and unattended work (P5, P13, P14, P15): round limit, no model turns spent waiting on a machine, one writer per worktree, state committed to the repo. Text and thin adapters over harness features, no owned orchestration scripts.

### Engine

- Outcome block parser: three load-bearing fields (outcome sentence, proof command, boundary as exact path globs), multi-line values allowed, and the proof's own test file allowed by default.
- `odd red` and `odd green`: run the proof on the unfixed tree, then on the fixed tree, and record both with the content hash of the files inside the boundary (not the commit id), so a commit or unrelated edit stales nothing.
- `odd break`: revert or break the change and require the proof to go red again. This replaces the 0-100 sentence score as the quality signal; any 'red: n/a' use needs a recorded reason, is counted, and is listed at the gate.
- Ledger written only by the CLI, hash-chained, kept apart from agent-writable outcome files; config and the active pointer are control files too.
- `odd gate`: one exit code. It verifies the ledger chain, requires red, green and break on the current boundary hash, diffs every changed file against the boundary (which covers shell write routes), flags any edit to proof or gate paths, and has three results: pass, fail, could not run.
- Proof label on every record: real system or simulated. An outcome is reported 'proven' only with a real-system record; simulated green may gate a merge.
- `odd park <reason>` and `odd abort <reason>` ('cannot be done as specified'), both recorded as valid results.
- `odd widen <glob> <reason>`: one command to widen a boundary, with the reason recorded.
- Run state keyed by session id, so parallel sessions and subagents do not share one active pointer.
- `odd doctor`: reports whether each hook is installed and live and whether every file named in the hook config exists; run at session start.
- `odd cost`: sums context tokens read, tool calls and wall clock per outcome and for the project from transcripts.
- `odd measure`: on/off harness that runs the same outcome with a named component disabled and writes the comparison.

### Hooks

- PreToolUse on write tools: refuse product-code writes with no active outcome and no recorded red, and refuse writes to the ledger, config, gate and proof paths. Fails open on its own errors, with a logged override.
- Stop: block only a session that wrote code this turn and has an ungated, unparked outcome; pass through when the stop hook is already active so it cannot loop.
- SessionStart on startup, clear and compact: re-inject the one-page method and run the doctor check, printing a visible warning when enforcement is absent.
- A hard ceiling of about ten hooks in the package, each with fixture tests (a planted violation goes red, a known-good input stays green) and a packaging test that loads the hook config and asserts every referenced file exists.

### Cut from the first draft

- Six mandatory stage files (request, research, requirements, spec, plan, DAG) and the guard that enforces them through the tasks stage.
- Mandatory crawled research with cited source ids, and crawl.py.
- The 0-100 keyword outcome score and the 40-word vague list.
- The self-heal layer: learn.py, the retro template, detectors, lessons with recurrence counts, the library file, and the second Stop block until the retro is done.
- The five-level trace and coverage chain.
- The bundled frugality guard: tool_guard wait, range and read rules, jobs_wait.sh, the 30-call step cap, 3-minute steps and 30-second nodes. P18 ships at most as a settings file that is off by default, each setting with a retirement test.
- judge_share_max and judge gates at four stages.
- Two of the three principle documents; keep one page plus one copyable example run.
- The eleven referenced sub-skills that do not exist.
- From the method as packaged: P3's tier-from-diff, batch-gate and red-attribution scripts, P5's agent-cap and health machinery, P14's lease and lock scripts and P15's derived boards. They stay as opt-in reference text, since their figures measure waste one swarm created and no after-figure shows them saving a run.
- Diff-derived mutation batteries from the default path (about 600k tokens with no speedup); the single break-the-change check stays.
- The 18-principle count as taught: teach about seven (outcome and proof; script over agent; proof seen red and red again when broken; proof and done record out of the implementer's reach on a content hash; real-system proof before 'proven'; few rules enforced in code and deleted when covered; owner-only acts). The rest is reference.
- Every comparative or multiplier claim ('100x', 'frugal') and every unverified figure: the 18 judge rounds and about 12M tokens, the 22.2M-versus-26.6k projection, the pinned-model incident, the 6.3M-token audit figure, and the conflicting 95 KB and 101 KB instruction-file sizes.

### Defects to fix from the first draft

- hooks.json runs a tool_guard.py that is not in the package; a missing file exits 2 and blocks every matched tool call. Remove the dependency and add the packaging test.
- Writes under odd/ always pass the guard, so the agent can forge ledger lines and set enforce to false; forged lines turned a failing gate green. Split control files from outcome files and hash-chain the ledger.
- Bash writes (sed -i, heredocs, tee, git apply) bypass the write guard. Detect by diffing changed files against the boundary at gate time.
- tree_id is HEAD plus a diff hash, so a plain commit stales every proof and re-proving is quadratic; outside git it is a constant and nothing ever goes stale. Key on the content hash of boundary files.
- Trivially passing proofs are accepted and red-then-green is gameable with `test -f x` then `touch x`. Add the break step.
- 'red: n/a' plus any text skips the red requirement with no limit. Count it, require a reason, and show it at the gate.
- The Stop hook blocks every turn end, including questions, and appends a gate line each time (9 of 54 ledger lines in the e2e run). Block only sessions that wrote code this turn.
- ACTIVE is one file per project, so an unrelated session has its writes refused. Key it by session id.
- Boundary matching is a substring test with a basename fallback (a.py passes if data.py is named) and strict mode refuses a needed test file, lockfile or rename. Use exact globs, the default test-file allowance and the widen command.
- Hooks fail open silently, so a broken install enforces nothing and tells nobody. Add doctor and the session-start warning.
- Proof commands run with shell=True in the project root, including proofs written after reading crawled pages. Removing crawl closes that route; show the proof command to the user when it is first registered.
- Field values must be single lines and a blank line closes a block, so a wrapped outcome sentence is silently truncated. Parse multi-line values or reject loudly.
- The existing suites (38/38 and 25/25) pass while all of the above is true. Add one fixture per hole that fails on the current draft before the fix.

### How the toolkit measures its own value

The toolkit ships with no claim until these numbers exist, and it states the number each component should move before the run.

**Per outcome, by script from transcripts:** context tokens read (not output), tool calls, wall clock, rework rounds, escaped defects (defects found after the gate passed), and whether the proof was real or simulated. A project total is summed from the same records.

**On versus off, same tasks:** run a fixed task set with the toolkit on, with each component disabled in turn, and with a no-process control (plain Claude Code). Use three runs per case and a no-partial-credit grader, the form borrowed from BMAD's baseline mode. Report merge rate, cost per merged item, median time, review defects and rework rounds, with blind review of the diffs.

**Noise band:** the only stated band in the inputs is the Uvik benchmark's plus or minus 10 points. Until the toolkit's own run-to-run spread is measured from the three repeats, treat any difference inside that band as no difference. The owner's band is an open question.

**Keep or delete rule:** a component stays only if switching it off worsens escaped defects or rework beyond the band at a cost the owner accepts. Repeat at every model upgrade; a component whose off-run holds is deleted.

**Kernel integrity, as tests rather than opinion:** the measured attacks from the audit (forged ledger line, shell write outside the boundary, trivially true proof, plain commit, missing hook file) each have a fixture that must fail the gate.

**Before any comparative claim:** the same tickets through Spec Kit, BMAD and Superpowers with the same figures. The known bar is that Spec Kit cost about a third more and about 50% more time than no-spec for a modest defect gain.

**Real-system calibration:** a periodic run with the shipping artifact on the real system, with each escaped defect recorded as the simulation's error rate. The source project's first successful real install-to-first-order is the first entry owed.

### Rules for staying useful as models improve

- Every component has an off-switch and a recorded on/off comparison; re-run it at each model upgrade and delete what no longer pays.
- Quality is proof strength (red on the unfixed tree, red when the change is broken, real-system pass), not process steps completed. That signal holds at any capability level.
- The implementer cannot edit the proof, the gate or the done record; only a script writes done, on a content hash.
- No pinned model ids in any step; inherit or use a tier alias.
- No hard-coded minute budgets, call caps, step shapes or read windows. Where a limit helps today it is a setting, off by default, with a retirement test.
- Rules are plain sentences with scope and reason, no capitals or absolute emphasis, since newer models follow accumulated cautions more literally.
- Each learned rule carries a date, its triggering incident and a review-or-expire step; an escaped defect adds a check, not a prose rule.
- The enforced set stays small (about ten hooks); when a prose rule is broken twice it is enforced, rewritten or deleted, never restated.
- Run caps, worktree isolation, session state and fresh-context review are thin adapters over harness features, removed when the harness provides them.
- Owner-only acts (credentials, billing, consoles, deploys, release, production data deletion, irreversible changes, relaxing a check) stay with the human in every version.
- Anything load-bearing lives in a hook or script, and skill descriptions are checked against the harness's description budget so they do not drop out silently.

## Questions left for the owner

- Will you fund the comparison run before publishing any claim: a fixed ticket set through plain Claude Code, the lean kernel, Spec Kit, BMAD and Superpowers, with blind review? Without it the toolkit can be published only as 'one project, self-measured'.
- What task set and noise band do you accept for the on/off runs? The only band in the evidence is the Uvik benchmark's plus or minus 10 points; the toolkit's own spread is unmeasured.
- The source project has no successful real install-to-first-order on record. Should the toolkit wait for that run before teaching real-system proof (P12) as practice, or publish with the gap stated?
- Is Claude Code-only acceptable for the first release? The hooks and deny rules do not port, while the three compared frameworks run on many harnesses.
- Do you agree to publish the waste ledger (the judged swarm, the step cap, 733 rulings in 44 days, 53% of commits touching no product code) alongside the method? The skeptic critique rates it as more credible than the method itself.
- Can the unverified figures be re-cited from the repo, or should they be removed: the 18 judge rounds and about 12M tokens, the 22.2M-versus-26.6k projection, the pinned-model incident, the 6.3M-token audit figure, and the 95 KB versus 101 KB instruction-file sizes?
- Where does 'trivial, use Claude Code alone' end? BMAD's unit of about one session or roughly 500 changed lines is the only size in the evidence, and it is a unit of work, not a triviality threshold.
