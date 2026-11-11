# Spec Kit, BMAD and Superpowers: what they are, how they enforce, what the evidence says

*Produced 2026-11-11 by a read-only research agent (Claude Fable 5.2); rendered from `data/research/{speckit,bmad,superpowers}.json` by `tools/render_evidence.py`. Agent-written: every figure carries its source, and the "Not verified" list says what the agent could not confirm.*

## GitHub Spec Kit (github/spec-kit) — spec-driven development toolkit

### What it is

An MIT-licensed open-source toolkit from GitHub that scaffolds a spec-first process into a coding agent. Its README describes it as giving "AI coding agents structured processes, reusable templates, and documented outcomes".

Scale and currency (read 2026-11-11): about 149k stars and 13.4k forks; latest release 1.4.0, dated 10 Nov.

Install: `uv tool install specify-cli`, then `specify init <project> --integration <agent>` (Python 3.11+, uv). The docs list 43 integration options, Claude among them. For Claude Code it installs each command as a skill; the copy vendored in this repo (version 0.8.11, `ai_skills: true`) is nine `.claude/skills/speckit-*/SKILL.md` files of 106 to 372 lines each, plus five templates and five bash scripts under `.specify/`.

Workflow, per the current quickstart:
- `/speckit-constitution`: project principles, run once; later steps are checked against them.
- `/speckit-specify`: feature spec from a plain-language description (what and why, no tech stack).
- `/speckit-clarify` (optional): up to 5 targeted questions, answers written back into the spec.
- `/speckit-plan`: technical plan and design artifacts.
- `/speckit-checklist` (optional): a requirements-quality checklist, described as unit tests for the spec.
- `/speckit-tasks`: dependency-ordered `tasks.md`.
- `/speckit-analyze` (optional): read-only consistency report across spec, plan and tasks; constitution conflicts are always CRITICAL.
- `/speckit-implement`: executes the tasks; checks checklist state first and asks before proceeding if items are unchecked.
- `/speckit-converge` (newer): checks the code against spec, plan and tasks, appends missing tasks, and repeats with implement until it reports "Converged".
- `/speckit-taskstoissues`: removed from core in 1.3.0 and moved to a `github` extension.

Artifacts: `.specify/memory/constitution.md`, `.specify/feature.json` (a pointer to the one active feature), and a per-feature folder holding `spec.md`, `plan.md`, `tasks.md`, checklists and design files such as research, data model and contracts. Boeckeler counted eight files in one feature folder and a separate branch per spec.

Template devices: `[NEEDS CLARIFICATION: ...]` markers ("Don't guess"), phase gates for simplicity, anti-abstraction and integration-first, and a "Complexity Tracking" table for justified violations.

Since 1.x it has grown into a platform: extensions (bug fixing, idea assessment), presets, workflows, overlays, bundles and catalogs. The README now calls the processes "independent entry points, not mandatory phases".

### Core principles

- Power inversion: "Code serves specifications"; the spec is the primary artifact and code is one expression of it (spec-driven.md).
- Intent as the source of truth: specs should be "living, executable artifacts", precise enough to generate working systems (GitHub blog, Sept 2025).
- Separate what and why (spec) from how (plan); mark ambiguity explicitly with [NEEDS CLARIFICATION] instead of guessing.
- A constitution of non-negotiable principles. The reference one has nine articles: Library-First, CLI Interface, Test-First ("No implementation code shall be written before" tests are approved and failing), Simplicity ("Maximum 3 projects"), Anti-Abstraction, Integration-First ("Prefer real databases over mocks"); articles IV to VI are project-defined.
- Phased refinement with a human verifying at each phase: "The AI generates the artifacts; you ensure they're right."
- Checklists act as a definition of done and as unit tests for the spec; features must trace to concrete user stories ("No speculative or 'might need' features").
- Test ordering: contracts, then integration, end-to-end and unit tests, then source.

### How it enforces its process

Mostly advisory prompting; nothing I read forces the agent to follow the process.

- The process lives in long SKILL.md prompts and markdown templates. Gates (constitution check, checklist status, phase gates) are instructions the model interprets. Boeckeler makes the same point: the checklists are interpreted by the AI, so compliance is not guaranteed.
- Before implementing, the implement skill counts `- [ ]` items in the checklists and asks the user whether to proceed. That is a soft prompt, not a block.
- "Extension hooks" (`before_implement`, `after_implement` in `.specify/extensions.yml`) are, in the vendored 0.8.11 skill, also prompt text: the model is told to read the YAML and emit `EXECUTE_COMMAND`, and to skip silently if the YAML is invalid. They are not Claude Code PreToolUse hooks.
- The deterministic parts are the bash scripts, which create the branch and feature directory, resolve paths and check that prerequisite files exist. They do not check content or behaviour.
- `/speckit-analyze` is strictly read-only and only recommends resolving CRITICAL findings before implement.
- `/speckit-converge` is a model-judged loop of code against spec; I found no test or proof requirement in its description.
- Newer releases add a workflow engine (shell steps, gates, opt-in "strict shell execution" in 1.2.6) and extension runtime events, which could carry real enforcement. The README does not describe any mechanism that blocks an agent from skipping steps.

### Strengths

- Very wide adoption and agent-neutral reach: about 149k stars and 43 integration options, so its vocabulary (constitution, spec, plan, tasks) is a de facto shared language.
- Clean separation of what/why from how, and an explicit ambiguity marker instead of silent guessing.
- Clarify is bounded (at most 5 questions) and analyze is read-only, so both are cheap and safe to run.
- A dependency-ordered tasks.md gives the agent small units that can be checked one at a time.
- Requirement-to-task traceability and an anti-speculation rule are built into the templates.
- The spec, plan, tasks, code, review lifecycle surfaces issues earlier, and template customization cuts unnecessary output (Thoughtworks Radar, April 2026, ring Assess).
- The newer converge step closes a known gap by re-checking code against the spec and looping.
- Extensible: presets, extensions and workflows let teams trim or replace the default process, and bug-fix and idea-assessment entry points no longer require a full spec first.
- One third-party benchmark found fewer review defects per merged ticket than a no-spec control (0.57 against 0.86) and fewer rework rounds (0.62 against 0.74).

### Weaknesses and documented criticisms

- Review burden and verbosity. Boeckeler (martinfowler.com, 15 Oct 2025): it "created a LOT of markdown files for me to review", repetitive and tedious; "I'd rather review code than all these markdown files."
- Measured overhead. Eberhardt (Scott Logic, 26 Nov 2025): one CRUD feature took 33.5 min of agent time, 2,577 lines of markdown and 3.5 hours of review for 689 lines of code, against about 8 min of agent time and 24 min of review and testing without it; he estimates roughly ten times slower.
- Tiny features explode. Zaninotto (marmelab, 12 Nov 2025): displaying the current date produced 8 files and about 1,300 lines of text.
- One opinionated workflow, overkill for small work: Boeckeler found it excessive for a 3 to 5 point story and did not finish the implementation.
- The agent does not reliably follow the artifacts. Boeckeler saw it ignore research notes about existing classes and create duplicates, and over-apply constitution articles. Zaninotto saw an agent tick "verify implementation" without writing a single unit test.
- False sense of control or security: heavy up-front specification conflicts with small iterative steps (Boeckeler); critics call it a waterfall revival (Zaninotto, Eberhardt).
- Double review: the technical plan already contains code, so reviewers read it twice (Zaninotto).
- Spec drift. Boeckeler classes it "spec-first only, not spec-anchored over time": per-change branches mean specs live only for one change, despite the "living artifact" messaging.
- Brownfield weakness: agents find context by text search and miss existing functions; Zaninotto calls SDD "mostly unusable" for large existing codebases. Thoughtworks does report teams using it mostly in brownfield, with instruction bloat and context rot as the stated challenges.
- Unclear target user: it needs both product-analysis and design skills (Boeckeler, Zaninotto).
- Redundancy with the agent's own plan mode and task lists; Eberhardt expects the guided steps to matter less as agents improve.
- Workflow gaps left unanswered: issue #1193 (how to resume, amend a spec mid-implement, merge the branch, skip test tasks) got no maintainer reply and was auto-closed as "not planned" after 180 days.
- Concurrency hazard seen in this repo: `.specify/feature.json` is a single repo-global pointer to the active feature, so parallel agents clobber each other; the local implement skill was patched to stop running the bundled scripts for that reason.
- Scope growth: the project is now a platform of extensions, presets, workflows, overlays, bundles and catalogs, which works against the simplicity its own constitution preaches (my inference).

### Evidence of effectiveness

No first-party measurements found. The GitHub launch post (Sept 2025) cites no data, and an ESEM 2026 paper states that no vendor has published empirical evidence and that GitHub describes Spec Kit as "an experiment".

Adoption is large (about 149k stars, 13.4k forks), but that is popularity, not effectiveness.

Independent evidence is mixed to negative:
- **Hill, ESEM 2026:** 88,052 pull requests across 119 open-source repositories; none of five vendor-derived hypotheses were supported. After matching, spec'd and unspec'd PRs were indistinguishable on defects (-0.6pp, p = 0.133) and rework showed no protective effect. The caveat matters: it measured issue and ticket references, not Spec Kit output, which no sampled repository commits, so tool adoption itself "remains untested".
- **Uvik benchmark (vendor blog, Oct 2026):** 50 brownfield Python tickets on one model, blind-reviewed. Spec Kit against a no-spec control:

| Metric | Spec Kit | No spec |
|---|---|---|
| Merge rate | 80% | 72% |
| Review defects per merged ticket | 0.57 | 0.86 |
| Cost per merged ticket | $3.33 | $2.43 |
| Median time to merge | 44 min | 29 min |

  The merge-rate gap is inside their stated ±10pp noise band, and 34% of Spec Kit's tokens went to the spec phase. One team, private code, not peer-reviewed.
- **Eberhardt (single developer, hobby app):** roughly ten times slower than iterative prompting, with a bug in the Spec Kit build and none in the baseline.
- **Thoughtworks Radar (April 2026):** ring Assess; a qualitative report that the lifecycle surfaced issues earlier and that experienced engineers with strong architectural practices benefit most.

In short: weak evidence of somewhat fewer review defects at clearly higher cost and time, and no controlled evidence that the full workflow pays for itself.

### Lessons for an outcome-driven toolkit

- Copy: one short statement of intent before any code, and an explicit ambiguity marker instead of guessing. The value sits in the first few lines of the spec, not the full artifact set.
- Copy: a bounded clarify step (at most 5 questions) and a read-only cross-artifact analysis; both are cheap and non-destructive.
- Copy: dependency-ordered small tasks, kept machine-validated. The repo's own `tasks_dag.py` goes beyond Spec Kit's prose ordering.
- Copy: the converge idea of re-checking the result against the intent and looping, but make the oracle an executable proof test, not a model's opinion of the code against markdown.
- Avoid: markdown volume. The documented failure is thousands of lines of spec for hundreds of lines of code and hours of review. Set a hard artifact budget per outcome (for example one outcome sentence, one proof test, one short context file) and make the human review the proof, not prose.
- Avoid: one fixed pipeline for every size of work. Tier ceremony from the diff or risk, as the repo already does, and make the default path the shortest.
- Avoid: gates that are prompt text. Spec Kit's checklists and hooks are interpreted by the model and get skipped. Put anything that must hold in a PreToolUse hook, a script exit code or a merge gate, and prove each gate can fail.
- Avoid: self-reported completion. "Verify implementation" was ticked with no tests written; require a RED-then-GREEN proof captured by a script, with the tree sha.
- Avoid: global mutable state such as `.specify/feature.json`. Key all state by outcome or requirement id so parallel agents cannot clobber each other.
- Avoid: 150 to 370 line skill prompts and platform sprawl. Thoughtworks names instruction bloat and context rot as the live problems. Keep skills short and push detail into scripts, which also survives model upgrades better than prompt choreography.
- Beat: spec drift. Make the durable artifact the executable proof test plus a one-line outcome, which cannot drift silently because it fails.
- Beat: brownfield duplication. Require a "name the nearest existing code" step with a cited search before writing, since Spec Kit agents were seen regenerating existing classes.
- Beat: the evidence gap. Spec Kit publishes no measurements. Ship with a reproducible measurement (tokens, wall clock, review minutes, defects against a no-process control on the same tickets) and state the noise band.
- Beat: obsolescence risk. Eberhardt expects guided steps to matter less as agents improve; constrain outcomes and proofs (what must be true) and leave the how to the model.
- Caution for this project: the benchmark shows process costs about a third more tokens and about 50% more time for a modest defect gain. A toolkit that adds judges and stages on top must show it does better than that, or it repeats the same criticism.

### Sources

- [github/spec-kit README](https://github.com/github/spec-kit)
- [spec-driven.md (Spec Kit philosophy and constitution)](https://github.com/github/spec-kit/blob/main/spec-driven.md)
- [Spec Kit docs home](https://github.github.com/spec-kit/)
- [Spec Kit quickstart](https://github.github.com/spec-kit/quickstart.html)
- [Spec Kit releases](https://github.com/github/spec-kit/releases)
- [Spec Kit issue #1193: Seeking Guidance on Proper Usage of the Spec Kit Workflow](https://github.com/github/spec-kit/issues/1193)
- [GitHub blog (Den Delimarsky, 2 Sept 2025): Spec-driven development with AI](https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai-get-started-with-a-new-open-source-toolkit/)
- [Birgitta Boeckeler (15 Oct 2025): Understanding Spec-Driven-Development: Kiro, spec-kit, and Tessl](https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html)
- [Colin Eberhardt, Scott Logic (26 Nov 2025): Putting Spec Kit Through Its Paces](https://blog.scottlogic.com/2025/11/26/putting-spec-kit-through-its-paces-radical-idea-or-reinvented-waterfall.html)
- [Francois Zaninotto, marmelab (12 Nov 2025): Spec-Driven Development: The Waterfall Strikes Back](https://marmelab.com/blog/2025/11/12/spec-driven-development-waterfall-strikes-back.html)
- [Thoughtworks Technology Radar (April 2026): GitHub Spec Kit, ring Assess](https://www.thoughtworks.com/radar/languages-and-frameworks/github-spec-kit)
- [Brenn Hill, ESEM 2026: Specification Artifacts in Open-Source Pull Request Workflows Do Not Reduce Defects](https://drops.dagstuhl.de/storage/00lipics/lipics-vol394-esem2026/LIPIcs.ESEM.2026.84/LIPIcs.ESEM.2026.84.pdf)
- [Uvik Software SDD Benchmark 2026 (vendor blog)](https://uvik.net/blog/spec-driven-development-benchmark/)

### Not verified

- Web pages were read through a summarizing fetch tool, so quotes from them are as that tool relayed them; only the ESEM abstract and the local Spec Kit files were read as raw text.
- The upstream reference page for core commands returned 404. Descriptions of clarify, analyze, checklist and taskstoissues come from the quickstart and from the copy vendored in this repo (version 0.8.11, locally modified), not the current 1.4.0 text.
- Whether extension hooks in 1.4.0 are still prompt-interpreted, or now run through the CLI's workflow engine or real agent lifecycle hooks, is not confirmed. The README mentions "extension runtime events" and 1.3.0 adds CLI-side hooks, which I did not inspect.
- Exactly how `/speckit-converge` judges convergence (model opinion or tests) was not read from its source, only from the quickstart description.
- The Thoughtworks blurb was returned as a summary, not verbatim.
- The Uvik benchmark is a vendor blog on private repositories and cannot be reproduced; I only read its own page.
- The ESEM paper's full results and the Eberhardt figures were not cross-checked beyond the abstract and the blog post respectively; the fetch reported the same markdown line count for his Plan and Tasks rows, which may be a transcription slip.
- No GitHub issues specifically about token cost, verbosity or drift were read; the search did not honour the site restriction and only #1193 was opened.
- The 'honest critique' page from the search results returned 404 and was not used.
- Star and fork counts and the release date ("10 Nov", year not shown) are as the page showed on 2026-11-11.


## BMAD Method (bmad-code-org/BMAD-METHOD, "Breakthrough Method for Agile AI Driven Development")

### What it is

An MIT-licensed, role-based agile framework for AI coding tools, published by BMad Code, LLC. As read on 2026-11-11 the repo shows 55.3k stars and 6.2k forks; stable is v6.12 (npm installer, bug fixes only) and v7 is a preview alpha with breaking changes.

Structure, classic (v4 through early v6, per a secondary explainer):
- Two phases. Agentic Planning: Analyst, PM and Architect produce a brief, PRD, UX spec and architecture, often in a web UI via "web bundles". Context-Engineered Development: Scrum Master, Dev and QA work in the IDE.
- The Scrum Master shards the PRD and architecture into self-contained story files. Each carries context, implementation details, architectural guidance, constraints, embedded tests and links to the source docs.
- Dev implements one story at a time and QA reviews it.
- Roster: Analyst, PM, Architect, PO, Scrum Master, Dev, QA, UX Expert, plus Orchestrator and Master agents.
- "Expansion packs" extended it to games, creative writing and business.

Structure, current docs (v6.12 / v7):
- Personas are skills: Mary (Analyst), John (PM), Sofia (Product Owner: spec, tickets, board, replan), Winston (Architect), Amelia (Developer: BUILD, TESTS, REVIEW, RETRO), Sally (UX). The Tech Writer is on hiatus. Scrum Master and QA no longer appear as separate personas; their work sits with Sofia and Amelia.
- Expansion packs are now "modules": Builder, Creative Intelligence Suite, Test Architect, Loop, Game Dev Studio.
- Four planning paths sized to the work: trivial (BMAD optional), one session (straight to `bmad-build`), epic-sized (intent, spec and stories, one build per story, retrospective), project-sized (about 20+ sessions; shared product, UX and technical contracts, then epics).
- Artifacts: `prd-<slug>.md`, `architecture-<slug>.md`, `DESIGN.md`, `EXPERIENCE.md`, story and epic files, `.memlog.md`, an ordered `tickets.toml`, per-run plan files, `deferred-work.md`.

In Claude Code:
- Skills install to `.claude/skills/` via `npx bmad-method install`, `npx skills add bmad-code-org/BMAD-METHOD --skill '*'`, or `/plugin marketplace add bmad-code-org/bmad-plugins`. Both routes need uv and Python.
- `bmad-build` runs in a fresh chat: investigate the repo, route to a light or full plan, human approves the plan, implement, parallel reviewer lenses (Blind Hunter, Edge Cases Hunter, Verification Gap Finder), triage, local commit. The ticket is left at `built`; only a human or orchestrator marks it done.
- `bmad-build-auto` is an unattended single-ticket worker. Multi-agent discussion ("party mode") defaults to one model voicing every persona.

### Core principles

- "AI is the facilitator. The human is the expert." AI amplifies both skilled and weak thinking.
- The spec is the work: invest in planning before building, because assistants "often turn unstated assumptions into code".
- "The rigour should match the work": small changes go straight to build, complex work gets depth.
- Agile evolved, not abandoned: the epic is the unit of work, opening with an inception and closing with a retrospective.
- Role separation: each persona has a bounded role and one deliverable, and documents carry decisions forward instead of chat history.
- Fresh context per workflow, with self-contained story or ticket files so the dev agent does not re-read the whole PRD.
- Human stays in the loop: plan approval, open questions answered before build, and only a human marks work done.
- "Autonomy is earned with evidence": hand over more only as shipped results hold up.
- No vendor lock-in: not tied to one model or harness; organisations inject their own modules and standards.

### How it enforces its process

Mostly advisory prompting with human checkpoints. I found no Claude Code hooks, no PreToolUse guards and no merge gate in the pages I read.

- The build page describes sizing, routing, triage and status handling as agent behaviour. Tests are an output only "if your project has a test suite", and verification is a review lens, not a gate.
- Review is advisory: "The review never changes the ticket's status: marking it done is yours."
- The deterministic parts are thin. `_bmad/method/scripts/tickets.py` (`next`, `find`, `status`, `mark`) resolves tickets and routes on status. Build Auto handles one ticket per invocation, commits but never pushes, and never sets `done`.
- Build Auto halts on named blocked outcomes: unclear intent, no subagents, ticket not resolved, implementation verification failed. A review repair loop halts as non-convergent after 5 iterations, and a blocked plan stops later dispatch of that ticket until someone resets it.
- `bmad-eval` is a skill-testing harness (clean temp directory, three runs per case, no-partial-credit grader). It tests skills, not the user's delivery.
- The repo listing shows `.pre-commit-config.yaml`, but that covers BMAD's own repo, not the user's project.

I could not read the skill source files, because GitHub API access to that repo was not enabled in this session. This verdict rests on the documentation, not the code.

### Strengths

- Widest lifecycle coverage of the compared frameworks; one practitioner writes "only BMAD covers the full span from research to retro".
- It now states when to skip itself: trivial edits need no BMAD, and a PRD is required only when several people must agree.
- Self-contained story and ticket files plus fresh sessions are sound context engineering.
- On large tickets it held its merge rate at 80% where the no-spec control fell to 50% (vendor benchmark, 10 large tickets).
- Fewer review defects and rework rounds than no-spec in the same benchmark: 0.49 vs 0.86 defects per merged ticket, 0.46 vs 0.74 rework rounds.
- Review triage is disciplined: findings are verified at the named location, dismissals carry a recorded reason, and "a problem this change caused is never deferred".
- The build never marks its own work done, which keeps the done-claim out of the agent's hands.
- It is honest about role-play: the docs say "One model voicing five personas tends to make them agree" and offer separate subagents when independence matters.
- Large adoption (55.3k stars) and an active module ecosystem.

### Weaknesses and documented criticisms

- Most expensive arm in the one controlled benchmark I found: $4.23 per merged ticket vs $2.43 for no-spec, about 74% more.
- Slowest in that benchmark: 55 minutes median to merge vs 29 for no-spec, with a 28-minute median spec phase.
- Spec work took 43.9% of tokens (227k median spec-phase tokens), the highest share of any arm.
- Its +10 point merge-rate gain over no-spec sits at the edge of the benchmark's own ±10 point noise band.
- Spec drift was 12.2%, against 2.4% for OpenSpec and 4.9% for Kiro: the long documents go stale.
- Engineers rated its spec review effort 2 out of 5 (others 4), and only 3 of 5 would use it again on client work, the lowest.
- Ceremony on small work: one practitioner spent 2 days and got "Zero lines of actual code", writing "I needed a TODO app, not a sprint ceremony."
- False done-claims are reported: one user spent 9+ hours on an auth system the pipeline "erroneously marked as complete". A reviewer argues agents reviewing agents is not real verification.
- Steep learning curve: about two months to proficiency by one estimate, with 50+ commands and sub-workflows in v6.
- Token burn at scale: one user reported about 230 million tokens in a week; an earlier monolithic workflow averaged about 31,667 tokens per run before v6 stepping cut it to about 8,333.
- Persona theatre: the default discussion mode is a single model voicing every persona, which the docs concede drifts to agreement.
- Churn: v4, v6 and v7 differ in install path, commands and roster, so most tutorials are stale and v7 alpha warns of breaking changes.
- No hard enforcement of tests or gates in the user's project; quality depends on the model following instructions and the human checking.

### Evidence of effectiveness

The project itself publishes no benchmarks. The README carries no results, and the `bmad-eval` page describes a method but gives no scores.

The only controlled data I found is a vendor benchmark by Uvik Software (run 2026-10-15): 50 brownfield Python tickets, claude-sonnet-5, Claude Code, BMAD 6.x, reviewers blind to the workflow.

| Metric | BMAD | No-spec control | Best other arm |
|---|---|---|---|
| Merge rate | 82% (41/50) | 72% (36/50) | OpenSpec 84% |
| Cost per merged ticket | $4.23 | $2.43 | Kiro $2.35 |
| Median time to merge | 55 min | 29 min | OpenSpec 36 min |
| Review defects per merged ticket | 0.49 | 0.86 | Kiro 0.39 |
| Rework rounds per ticket | 0.46 | 0.74 | (BMAD lowest) |
| Spec drift | 12.2% | n/a | OpenSpec 2.4% |
| Merge rate, large tickets | 80% | 50% | not extracted |

Caveats on that benchmark: one company with services to sell, private code, Python only, one model, 45-minute time boxes, engineers not blind during the run, and a ±10 point noise band on merge rate.

Other evidence is anecdotal. One practitioner "built about 75% of the app in one afternoon" after about eight hours of planning. A secondary source reports 5.5 hours with BMAD vs 12 minutes with OpenSpec on one dashboard build. Adoption is 55.3k stars and 6.2k forks.

### Lessons for an outcome-driven toolkit

- Copy: sizing the process to the work, including an explicit "this is trivial, skip the toolkit" path. BMAD added this after the ceremony complaints.
- Copy: the build never marks its own work done. Keep the done-claim behind a check the agent cannot write.
- Copy: named blocked outcomes and a hard cap on repair loops (BMAD halts after 5 review iterations as non-convergent).
- Copy: self-contained work units read in a fresh context, about one session or roughly 500 changed lines each.
- Copy: review triage that verifies each finding at its location and records a reason for every dismissal.
- Copy: testing your own skills against the bare model (BMAD's Baseline mode), and publish the result. BMAD has the harness but no published numbers, so this is where ODD can beat it.
- Avoid: personas as the organising idea. BMAD's own docs say one model voicing several personas tends to agree; use a separate context only where independence changes the answer.
- Avoid: front-loaded documents. BMAD spent 43.9% of tokens on specs and still drifted 12.2%; one outcome sentence plus a proof test is cheaper to keep true than a 188-line spec.
- Avoid: a large command surface. 50+ commands and a two-month learning curve are the most repeated complaints; a handful of entry points is the lean answer.
- Avoid: breaking installs between versions. Keep the contract in plain files and scripts so it survives model and harness changes.
- Beat: enforcement. BMAD's tests and reviews are advisory in the user's repo; a hook or script gate that refuses "done" without a RED-then-GREEN proof targets the documented "marked complete but broken" failure.
- Beat: cost reporting. BMAD's docs carry no cost warnings; reporting tokens per outcome makes the overhead visible and falsifiable.
- Caution for ODD: the benchmark shows no-spec is cheapest and fastest on small tickets (85% merge rate for both on small). Any added process must prove it pays on small work or step aside.

### Sources

- [BMAD-METHOD repository (README, stats, versions, modules, install)](https://github.com/bmad-code-org/BMAD-METHOD)
- [BMAD README (raw)](https://raw.githubusercontent.com/bmad-code-org/BMAD-METHOD/main/README.md)
- [BMAD docs: Skills and agents reference](https://docs.bmad-method.org/reference/skills-and-agents/)
- [BMAD docs: Choose a planning path](https://docs.bmad-method.org/plan/choose-a-planning-path/)
- [BMAD docs: Build a change](https://docs.bmad-method.org/build/build-a-change/)
- [BMAD docs: Review a change](https://docs.bmad-method.org/build/review-a-change/)
- [BMAD docs: Autonomous development loops](https://docs.bmad-method.org/build/autonomous-development-loops/)
- [BMAD docs: Run multi-agent discussions](https://docs.bmad-method.org/customize/run-multi-agent-discussions/)
- [BMAD docs: bmad-eval](https://docs.bmad-method.org/toolsmith/bmad-eval/)
- [BMAD docs: site navigation](https://docs.bmad-method.org/)
- [BMad Code: Philosophy](https://www.bmadcode.com/philosophy)
- [Uvik: Spec-driven development benchmark (50 tickets)](https://uvik.net/spec-driven-development-benchmark/)
- [Limitations of BMAD Method (asantos2000, 2026-01-10)](https://asantos2000.github.io/blog/post-3/)
- [bmad method disappointment (guillim, 2026-02-08)](https://guillim.github.io/ai/development/2026/02/08/bmad-method-disappointment.html)
- [Stephan Miller: BMAD, Spec Kit, Superpowers, OpenSpec by project size](https://www.stephanmiller.com/bmad-spec-kit-superpowers-openspec-which-agent-skill-framework-fits-your-project-size/)
- [The BMAD Method Explained (codemyspec, 2026-06-03)](https://codemyspec.com/blog/bmad-method-explained)

### Not verified

- I could not read the BMAD skill source files or repo tree: GitHub API access to that repo was not enabled in this session. The enforcement verdict rests on the docs only, so hooks or scripts beyond `tickets.py` may exist.
- The classic v4/v6 structure (two phases, Scrum Master, QA, story files, expansion packs, web bundles) comes from a secondary explainer, not a primary v4 source. The old docs URLs now redirect.
- Whether "party mode" is still the product name: current docs call it multi-agent discussions.
- The Uvik benchmark is a single vendor study on private code; I could not check its data.
- The token and cost figures in the limitations blog (31,667 to 8,333 tokens per run, $847 to $220 a month, 230M tokens in a week, two-month learning curve, 9+ hour auth failure) are second-hand reports I did not trace to their originals.
- The Reenbit comparison (5.5 hours BMAD vs 12 minutes OpenSpec) is quoted from a secondary source; I did not read the original.
- The "up to 90% token saving from sharding" claim appeared only in a search summary and I did not open its source.
- I found no Reddit or Hacker News threads in two searches, so practitioner criticism here comes from blogs.
- The author's personal identity: the pages I read name only BMad Code, LLC.
- BMad Loop's actual behaviour: the docs say it "does not dispatch from the ticket tree yet", and I read no Loop module page.
- All WebFetch content was summarised by a small model, so short quotes may be imperfect; the benchmark table was not re-checked against the page by hand.


## Superpowers for Claude Code (Jesse Vincent / obra)

### What it is

An MIT-licensed plugin that the README calls "a complete software development methodology for your coding agents, built on top of a set of composable skills and some initial instructions". The repo page showed 316.1k stars and 28.1k forks when read, and lists installs for 16 harnesses (Claude Code: `/plugin install superpowers@claude-plugins-official`).

Structure: a library of Markdown skills (SKILL.md files), plus one bootstrap hook. Skills listed in the README:
- Testing: test-driven-development.
- Debugging: systematic-debugging, verification-before-completion, diagnosing-superpowers.
- Collaboration: brainstorming, writing-plans, executing-plans, dispatching-parallel-agents, requesting-code-review, receiving-code-review, using-git-worktrees, finishing-a-development-branch, subagent-driven-development.
- Meta: writing-skills, using-superpowers.

Workflow, in README order:
1. brainstorming: draws out the design before anything is built.
2. using-git-worktrees: isolated workspace on a new branch after design approval.
3. writing-plans: tasks of "2-5 minutes each" with exact file paths and verification steps.
4. subagent-driven-development (fresh subagent per task) or executing-plans (inline in one session).
5. test-driven-development: RED-GREEN-REFACTOR.
6. requesting-code-review between tasks; "Critical issues block progress."
7. finishing-a-development-branch: verify tests, then merge / PR / keep / discard, and clean up.

Subagent-driven-development in detail (current SKILL.md):
- One implementer at a time, never parallel; implementers never spawn their own subagents.
- Each task gets a brief containing only the task, its interfaces and global constraints; accumulated history is not pasted in.
- A task reviewer works from a BASE..HEAD diff file and gives two verdicts, spec compliance and code quality.
- Fix loop is capped: rounds 1-3 resume the same implementer, rounds 4-5 escalate to a model at least one tier higher; unresolved findings are "parked" with a ruling.
- The controller does not pause between tasks; it settles ambiguities itself and logs each as a ruling with rationale and cost if wrong. It stops only for irreversible, security-sensitive or external-side-effect actions, or a plan too broken to follow.
- A whole-branch review runs once at the end.

Artifacts: a design from brainstorming, a plan file, a git worktree and branch, and a per-plan git-ignored ledger file (the skill says controllers without one "have re-dispatched completed tasks" after compaction).

Triggering: a SessionStart hook injects the using-superpowers bootstrap; after that the model is expected to match skill descriptions to the task and load the skill itself. The README says skills "trigger automatically".

### Core principles

- README philosophy, four bullets: TDD ("Write tests first, always"), systematic over ad-hoc ("Process over guessing"), complexity reduction ("Simplicity as primary goal"), evidence over claims ("Verify before declaring success").
- "Mandatory workflows, not suggestions" (README). The bootstrap skill says: "If you think there is even a 1% chance a skill might apply to what you are doing, you ABSOLUTELY MUST invoke the skill" and "Invoke relevant or requested skills BEFORE any response or action".
- User instructions outrank skills: "User instructions (CLAUDE.md, AGENTS.md, GEMINI.md, etc, direct requests) take precedence over skills".
- Iron laws stated per skill: "NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST" (code written before its test is deleted and redone) and "NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE" (identify the proving command, run it fresh, read the output, only then claim).
- Rationalization tables: each discipline skill lists the excuses an agent makes ("Should work now", "The skill is overkill", "Agent said success") with a rebuttal, to pre-empt them.
- Skills are themselves developed test-first: the author pressure-tests them on subagents with realistic scenarios (a production outage where "Every minute costs $5k", a sunk-cost case) and strengthens the wording after each failure.
- Persuasion principles (Cialdini: authority, commitment, scarcity) are deliberately used in skill wording to raise compliance; the author credits a study co-authored by Dan Shapiro.
- Fresh context per task: implementation goes to subagents so the controller's context stays small; "Use the least powerful model that can handle each role", with the warning "Turn count beats token price".
- Small plan steps (2-5 minutes) with exact paths, and review between tasks rather than only at the end.

### How it enforces its process

Advisory prompting only, with one hook that injects text.

- The only hook registered in hooks/hooks.json is SessionStart (matcher `startup|clear|compact`), which runs `run-hook.cmd session-start` to inject the using-superpowers bootstrap. It re-fires after compaction on Claude Code.
- There is no PreToolUse, Stop or other blocking hook in that file. Nothing checks that a skill was loaded, that a test was written first, or that verification ran before a completion claim.
- The TDD, verification-before-completion and using-superpowers SKILL.md files contain no script, git hook or CI gate. Their force comes from capitals, `<EXTREMELY-IMPORTANT>` tags, "iron laws", rationalization tables and persuasion techniques.
- The closest things to structural gates are procedural and still run by the model: the reviewer subagent must be given a diff file, both review verdicts are required before the next task, and the fix loop has a round cap.
- Triggering depends on the harness showing skill descriptions to the model. The author documented that Claude Code (as of 2.0.70) had a default 15,000-character budget for skill and command descriptions and that skills past it dropped out silently, with no warning.
- On harnesses without a post-compaction hook the bootstrap can be lost: the README says of Hermes that "a very long session that compacts over its first turn loses the bootstrap".

### Strengths

- Very low adoption cost: one plugin install, no project scaffolding, and it works across 16 harnesses.
- Light base footprint by the author's account: Simon Willison reports the core as "VERY token light", with the main document under 2,000 tokens and other pieces loaded only when needed; a full plan-and-implement chat for a sample todo app reached about 100k tokens.
- The skills name the real failure modes of coding agents (claiming done without running anything, skipping the failing test, trusting a subagent's report) and give a concrete counter-procedure for each.
- Subagent-driven-development has explicit cost controls: one brief per task with no pasted history, model tier chosen per role, an explicit model always named, capped fix rounds with escalation.
- Compaction-aware: SessionStart re-injects on `compact`, and progress lives in a ledger file rather than conversation memory.
- Autonomy with a short stop list: the controller logs rulings instead of pausing, and stops only for irreversible, security-sensitive or external-side-effect actions.
- The skills are tested against pressure scenarios before release, and the author corrected his own first test design when subagents were merely being quizzed ("less than useful").
- User instructions explicitly outrank skills, so it layers under a project's own rules rather than fighting them.

### Weaknesses and documented criticisms

- No mechanical enforcement. Every "mandatory" rule is text the model may or may not follow; the only hook injects a prompt.
- Skills can fail to trigger silently. The author's own post explains that descriptions past the character budget vanish from the model's view without warning; his workaround was `SLASH_COMMAND_TOOL_CHAR_BUDGET=30000` and shortening or merging skills in v4.0.
- Token weight of the skill bodies. Issue #832 reported cutting the 14 skills from 3,150 to 977 lines (69%) by removing rationalization tables, red-flag lists and verbose examples, and asked for a lean mode for lower-quota users. The maintainer closed it the same day, saying the tables exist because of "extensive testing and real world use"; the reporter's reply that the concern was quota, not activation, drew four thumbs-up.
- Overhead on trivial work. The 1% rule and "Questions are tasks. Check for skills" apply the same ceremony to small tasks. Secondary write-ups (seen only as search summaries) say simple tasks used more tokens with the plugin and that some users reserve it for larger features.
- Process-first, not outcome-first. The pipeline starts from brainstorming a design and ends at a green branch; there is no single user-visible outcome sentence, no end-to-end proof on the real system, and no merge gate beyond tests passing.
- Review is model-on-model with no scripted pre-checks, no evaluation file to score against, and no ratcheting baselines.
- No project memory or learning loop in the shipped workflow: the launch post describes the conversation-memory skill as built but "I just haven't had time to wire them together".
- No measurement built in: nothing reports token cost, step duration or rule violations per task.
- Serial by design in its main mode ("Never dispatch implementation subagents in parallel"), which trades wall-clock time for safety.
- The README states "we don't generally accept contributions of new skills", so project-specific discipline has to live elsewhere.

### Evidence of effectiveness

No measured results from the author. The README and launch post give only anecdotes ("It's not uncommon for your agent to work autonomously for a couple hours at a time without deviating from the plan") and a demo todo-app transcript. The launch post itself records that early subagent tests reported "a perfect score" that turned out to be misleading.

Adoption is the strongest signal: 316.1k stars and 28.1k forks on the repo page when read, and distribution through the official Claude Code plugin marketplace.

One third-party experiment is repeated across secondary articles: 12 Claude Code sessions, 6 with and 6 without the plugin, reporting roughly 14% fewer tokens and about 9% lower cost with it, and more tokens on simple tasks. I saw this only in search-result summaries, not the original write-up, so treat it as unverified; six runs per arm is in any case too few to trust the percentages.

The persuasion-principles claim rests on the author's description of a study by Dan Shapiro and co-authors, which I did not read.

### Lessons for an outcome-driven toolkit

- Beat: turn the iron laws into hooks. Superpowers states "no completion claims without fresh verification evidence" and "no production code without a failing test first" as prose; a PreToolUse or Stop hook that refuses the claim or the commit without the evidence file is the difference between advisory and enforced.
- Beat: start from one owner-visible outcome and prove it end to end on the real or simulated system. Superpowers ends at reviewed code on a green branch.
- Beat: measure. Report tokens, tool calls and violations per milestone; Superpowers ships no numbers and its maintainer answered a 69% trim proposal with experience rather than data.
- Beat: scripts before judges. Run mechanical checkers ahead of any reviewer subagent, and give the reviewer a per-feature evaluation file; Superpowers reviews are model judgement on a diff.
- Copy: the SessionStart bootstrap that re-fires on `startup|clear|compact`, so standing rules survive compaction.
- Copy: the ledger file per plan. The skill admits controllers without one re-dispatched finished tasks.
- Copy: task briefs that carry only the task, its interfaces and global constraints, never accumulated history; name the model explicitly per role, cheapest that can do it, and cap fix rounds with escalation.
- Copy: logged rulings instead of pauses, with a short explicit stop list (irreversible, security-sensitive, external side effects).
- Copy: pressure-test each rule on a subagent under realistic temptation before shipping it, and keep a GREEN control so the test is known to be able to fail.
- Copy: user and project instructions outrank the toolkit's skills, stated in the bootstrap.
- Avoid: relying on description matching for anything that must happen. Skills dropped out silently past the 15,000-character budget; anything load-bearing belongs in a hook or script, and the toolkit should check its own description budget.
- Avoid: one ceremony level for every task. The 1% rule taxes trivial work; tier the process from the diff or risk class.
- Avoid: long rationalization tables in every skill body, since the whole body loads on each invocation. Keep the non-obvious defaults and gates, move the rest to reference files, and measure whether a table changes behaviour before keeping it.
- Avoid: self-reported test scores as proof. The author's first subagent tests scored perfectly and were wrong; every check needs a demonstrated failing case.

### Sources

- [obra/superpowers README (GitHub)](https://github.com/obra/superpowers)
- [Jesse Vincent, "Superpowers" launch post, 2025-10-09](https://blog.fsck.com/2025/10/09/superpowers/)
- [Jesse Vincent, "Claude Code skills not triggering", 2025-12-17](https://blog.fsck.com/2025/12/17/claude-code-skills-not-triggering)
- [using-superpowers SKILL.md](https://raw.githubusercontent.com/obra/superpowers/main/skills/using-superpowers/SKILL.md)
- [verification-before-completion SKILL.md](https://raw.githubusercontent.com/obra/superpowers/main/skills/verification-before-completion/SKILL.md)
- [test-driven-development SKILL.md](https://raw.githubusercontent.com/obra/superpowers/main/skills/test-driven-development/SKILL.md)
- [subagent-driven-development SKILL.md](https://raw.githubusercontent.com/obra/superpowers/main/skills/subagent-driven-development/SKILL.md)
- [hooks/hooks.json](https://raw.githubusercontent.com/obra/superpowers/main/hooks/hooks.json)
- [hooks directory listing](https://github.com/obra/superpowers/tree/main/hooks)
- [Issue #832: 69% line reduction proposal, closed by maintainer](https://github.com/obra/superpowers/issues/832)
- [Simon Willison on Superpowers, 2025-10-10](https://simonwillison.net/2025/Oct/10/superpowers/)

### Not verified

- The 12-session A/B test (about 14% fewer tokens, about 9% lower cost, more tokens on simple tasks, attributed in one write-up to Marc Nuri): seen only in search-result summaries; the original was not read. Two review pages that repeat it (kunalganglani.com, mejba.me) returned HTTP 403.
- Practitioner criticism that the mandatory language is overkill on trivial tasks and that users reserve the plugin for larger features: from search summaries of secondary blogs, not pages I read.
- The contents of the `session-start` script and `hooks-cursor.json` were not read; that the hook injects the using-superpowers bootstrap comes from the README and launch post, not the script itself.
- All skill and hook files were read through a summarising fetch of the `main` branch on 2026-11-11, not as raw text; quoted lines are as that tool returned them. The implementer statuses other than DONE (DONE_WITH_CONCERNS, NEEDS_CONTEXT, BLOCKED) live in a reference file I did not open.
- Skills I did not open individually: brainstorming, writing-plans, executing-plans, systematic-debugging, using-git-worktrees, dispatching-parallel-agents, requesting/receiving-code-review, finishing-a-development-branch, writing-skills, diagnosing-superpowers. Their descriptions here come from the README.
- The README lists 15 skill names under a heading the fetch summarised as 14 skills; I did not reconcile the count.
- The Shapiro et al. persuasion study was not read; only the author's description of it.
- The launch post describes an older layout (getting-started/SKILL.md, a skill-search script, the obra/superpowers-marketplace install); the current repo differs, and I did not trace the version history or release notes between them.
- Star and fork counts are as displayed on the repo page at fetch time.
