# FAQ: Outcome-Driven Development (ODD)

Short answers to the questions people ask, plus a script for explaining ODD in a session. Where a claim depends on
evidence, the evidence is linked; where it is not proven yet, this page says so.

- [What it is](#what-it-is)
- [The name](#the-name)
- [What makes it different](#what-makes-it-different)
- [Who it is for](#who-it-is-for)
- [Next to other tools](#next-to-other-tools)
- [Does it work?](#does-it-work)
- [Objections](#objections)
- [Trying and adopting it](#trying-and-adopting-it)
- [Explaining it in a session](#explaining-it-in-a-session)

## What it is

**What is ODD, in one sentence?**
An outcome counts as delivered only when its proof fails without the change.

**What problem does it solve?**
Coding agents report "done" for work that is not done: the tests pass, but they test nothing the change does, and the
bug is still there. Writing more rules does not fix this, because a rule is something the model may or may not
follow. ODD makes "done" a command's verdict instead of the agent's claim.

**How does it work?**
1. Before writing code, the agent states the outcome: one sentence saying who observes what, a command that exits 0
   only when it is true, and the files the change may touch (`odd new`).
2. The agent makes the change.
3. `odd done` runs the proof, takes the change out and runs it again (it must fail), then puts the change back and
   runs it a third time (it must pass).
4. In CI, `odd gate --recompute` redoes all of it from the code and trusts nothing the agent recorded. Every changed
   file must sit inside a verified outcome.

Small edits (25 lines by default) need no outcome. If the work cannot be done as specified, `odd park` says so, and
that is an acceptable result.

**What is it not?**
Not a planning framework, a prompt library or an agent orchestrator, and it does not make the agent smarter. It is
the one check the others leave to the model.

**Where did it come from?**
From building a production restaurant point-of-sale system with coding agents over three months. 1,856 instructions
were given; each was catalogued and ruled on, and most were dropped. The two most expensive mistakes in that project
were its own process rules ([the waste record](docs/evidence/02-pos-evidence-ledger.md),
[why](WHY.md)).

## The name

**Why "Outcome-Driven Development"?**
Because every piece of work starts from one outcome a command can check, and ends only when that outcome is proven.
It sits beside test-driven (TDD) and behaviour-driven (BDD) development, and it describes how the source project was
actually built.

**Isn't that term already used?**
Yes, in two other senses. In product management, "outcome-driven development" means aligning work with business
goals ("outcomes over outputs"). And "ODD" is also the usual abbreviation for observability-driven development. Here
an outcome is narrower: something a command can check, with a proof that fails without the change. That is why the
definition always comes with the name.

## What makes it different

**What is the real differentiator?**
"Done" stops being the agent's claim and becomes a command's verdict the agent cannot fake. Three things together:

1. **The take-out check.** The proof must pass with the change, fail without it, and pass again. That catches the most
   common false "done": a test that passes but tests nothing the change does.
2. **Enforced outside the model.** In CI the gate recomputes everything from the code, with its own pinned copy of the
   tool and the target branch's settings, so a change cannot loosen the check that judges it. Every changed file must
   belong to a proven outcome, so unproven work cannot slip in beside proven work.
3. **An honest exit.** `odd park` makes "this cannot be done as specified" the expected answer instead of a pressure
   to fake success; the installed method, `odd park` and the Stop hook say so in the same words.

**What is not new?**
- Stating the outcome first: Spec Kit and others do something similar.
- The take-out idea itself: it is TDD's "red first" and a relative of mutation testing. What is new is making it the
  agent's definition of done, checked automatically and enforced at merge.
- Making agents smarter: ODD does not. Early measurements suggest strong models already get most work right.

**So what is it, really?**
A trust layer for code written by agents. It matters most where nobody is watching closely: agents opening pull
requests, agents running unattended, teams that must merge agent work safely, and weaker or cheaper models. The more
code agents write without anyone reading it, the more a check they cannot talk their way past is worth.

## Who it is for

| you are | the problem | how you use it |
|---|---|---|
| a developer working with an AI agent | the agent says done; the tests pass but test nothing | `odd init` once; the agent follows `AGENTS.md` and runs `odd done` before it reports done |
| a team letting agents open pull requests | reviewers cannot tell whether an agent's PR really works | one CI step, made a required check: a PR whose files are not covered by a proof that fails without them cannot merge |
| anyone running agents unattended | nobody is checking the "done" claims | the gate is the referee; `odd park` gives an honest "blocked" instead of a fake done |
| an engineering lead | no record of what was promised and what was proven | each outcome file is a three-line record; `odd stats` counts them |
| a user of Spec Kit, BMAD or Superpowers | specs and plans, but nothing proves the code meets them | ODD sits underneath as the last check |

**Which coding tools does it work with?**
Anything that can run a shell command. `odd init` writes the method into `AGENTS.md`, which Codex, Cursor, GitHub
Copilot in VS Code, Claude Code, Junie and Windsurf read without configuration; Gemini CLI, Aider and Copilot Chat
outside VS Code need one line. So far only Claude Code has actually been run with it.

## Next to other tools

| | what it adds | who decides "done" |
|---|---|---|
| Spec Kit | constitution, spec, plan, tasks, implement | the model, against written checklists |
| BMAD | agent roles and story workflows | the model; tests and reviews are advisory |
| Superpowers | skills with "iron laws" such as test first | the model; the rules are text |
| ODD | an outcome, a proof, a boundary | a command that reruns the proof without the change |

From each project's own documentation ([sources](docs/evidence/04-spec-kit-bmad-superpowers.md)). Other frameworks
help the agent plan; ODD checks whether the work is actually done. Use them together.

## Does it work?

**Is it proven to make agents better?**
Not yet, and nothing here claims it. A same-task comparison is running: 16 tasks with hidden acceptance tests (bug
fixes, features, traps, vague requests, impossible ones), each done by plain Claude Code, ODD, Spec Kit, BMAD and
Superpowers, three times each, on two models. It measures whether the work is really right, whether the agent claims
"done" falsely (claim precision and silent failures), whether it cheats or stops on tasks that cannot be done (cheat
and park rates, counted by the routes a script can see), and cost and time. The results will be published whatever they show. The harness is open in
[`bench/`](bench/SPEC.md).

**What has been measured so far?**
- The tool itself: 82 tests, a design review (23 changes) and a red team (48 confirmed defects, each now a test).
  See [the design review](docs/evidence/10-design-review.md) and [the red team](docs/evidence/11-red-team.md).
- The source project, from its git history: process lines per product line fell from 9.9 to 2.4 and the slowest
  tenth of changes from 133 hours to 12 as the method matured ([measurement](docs/evidence/01-method-measured.md)).
  One project, measured by itself.
- A pilot of the comparison ([pilot](docs/evidence/12-pilot.md)), too small to be a result: on Sonnet, plain Claude
  Code got the work right on every task tried, so correctness may not separate the five; on an impossible task, one
  framework claimed "done".

## Objections

| objection | answer |
|---|---|
| "Isn't this just TDD?" | TDD's red-first is the idea. ODD makes it the agent's definition of done, checks it automatically and enforces it at merge. |
| "Another framework to learn?" | Six commands (two more, `seal` and `escaped`, are optional) and about thirty lines of method, which your agent reads itself. |
| "My tests are fine." | Then `odd done` passes in seconds. If it does not, you have learned something. |
| "It will slow us down." | The proof runs three times, plus once per small break (at most eight; by default it stops once the breaks took about as long as the three runs), so make it the narrowest test that shows the outcome, usually seconds. Rework after a fake "done" costs more. |
| "My agent could cheat it." | On a laptop an agent with a shell can bypass any local check, so CI is the authority: a required check, its own pinned copy of the tool, settings from the target branch. |
| "We already use Spec Kit or BMAD." | Keep them. They plan; ODD checks the result. |
| "Does it make agents better?" | Not proven. The comparison will say, and it will be published either way. |
| "What if the work cannot be done?" | `odd park <slug> "<why>"`. The method tells the agent that when the task cannot be done as asked or the proof cannot honestly pass, stopping and explaining with `odd park` is the expected, correct answer, and a forced pass is the wrong one. This is wording, not enforcement; its effect here is not measured. |
| "Can the agent just rewrite the test to fit its code?" | Not silently. Editing or deleting a test that existed at the base fails `done` and the gate unless the outcome says why (`test-change: <reason>`, which can name the files it covers), and the review comment prints that reason with the files it covers. Turning a test off counts too: a new or changed `conftest.py`, `pytest.ini`, pytest section or `load_tests` needs the same reason (other routes, such as `PYTEST_ADDOPTS` or an outside plugin, are not seen; DESIGN section 10). A test the change adds is covered only if the outcome is sealed. `odd seal <slug>` before the code checks the proof fails and fingerprints the test files in the outcome file; editing them later fails `done` and the gate until a reseal, which changes the outcome file in the diff. Optional; a reviewer still has to look. |
| "What happens when a bug gets through anyway?" | `odd escaped <slug> "<what, where found>"` records it on the outcome it got past, and you write a new outcome whose proof fails on that bug. `odd stats` splits recorded escapes by sealed, take-out skipped and proof strength, so a team sees which kinds of proof leak. Only what someone records is counted, and strength only where it was measured locally. |
| "Can the proof just skip its test or exit 0 early?" | Not for unittest, pytest, jest or go test: a proof that exits 0 having run no test, skipped every test (or had only xfail / expected failures), or stopped before the runner's summary (`sys.exit(0)` at import) is refused. It reads the output and is conservative: a multi-step proof, a script run directly or a quieted runner is not checked, and a go test that calls `t.Skip` in every test is not detected (DESIGN section 4). |
| "Does it check that my test is thorough?" | Partly. It checks that the proof depends on the change, then makes up to eight small breaks in the changed lines, one per line first, and names each one the proof misses: "proof strength k of n" (`"strength": "enforce"` fails on them). For a Python proof it also names each changed line the proof never ran ("not run by the proof: file:line"); other languages say "not measured". A proof that only prints (imports, `print(...)`, plain assignments; nothing that can fail on purpose) is refused; `| grep -q .` after a print is not detected. Under enforce a break whose run did not complete (exit 126, 127, 129-192, a timeout) fails too. No survivor is not proof of thoroughness; a person should still read the outcome sentence and the proof. |

Full limits: [DESIGN.md](DESIGN.md#10-limits).

## Trying and adopting it

**How do I try it?**
```bash
pipx install odd-tool          # or: pip install odd-tool, or download odd.py
cd your-project && odd init     # writes .odd/ and the method into AGENTS.md
bash launch/demo.sh             # from this repository: watch it refuse a test that proves nothing
```
It is one file with no account and no service. To remove it, delete `.odd/` and the block it added to `AGENTS.md`.

**How do I make it count in CI?**
On GitHub Actions, one step at the end of your test job, made a required check:
```yaml
- uses: varunkan/ODD-Outcome-Driven-Development@v0.4.0
```
Other CI systems use the two lines `odd init` prints. The `strength`/`mutants` settings and `sealed:` need 0.4.0 or later; `test-change:` needs a tool newer than 0.4.0 (v0.4.0 refuses it as an unknown field).

**Can a pull request's code get the comment token or forge odd's comment?** Not through the environment: the gate
step, which runs the proofs, gets no token; a later step posts the comment. Only a comment by the bot (input
`author`) starting with the marker is updated, and text from the change is escaped. A proof runs as the same user,
so a process it leaves behind could still alter the summary file before it is posted.

**What does the reviewer see?**
One pull-request comment, updated on every run: the verdict, then per outcome its sentence, its proof, what the proof
said with the change taken out and how many small breaks it caught, then what passed without verification. It needs
`permissions: pull-requests: write` on the job; without that the step summary still has it and the check is
unaffected. We do not yet know how many review minutes it saves; [docs/review-time.md](docs/review-time.md) is how we
intend to find out.

**I do not know what proof command to write.**
`odd new <slug> "<outcome>" --in "<globs>" --proof auto` looks for pytest, unittest, a jest/vitest/mocha test script,
`go.mod`, `Cargo.toml` or a Makefile `test` target, prints what it found and the narrow command it chose (for example
`python3 -m pytest -q tests/test_<slug>.py`), and refuses if it finds nothing. It reads files, not your setup, so
read the command before relying on it. `odd init` prints the same suggestion.

**Can my agent call it as tools instead of through a shell?**
Yes: `odd init --mcp` installs a small MCP server (`.odd/odd_mcp.py`, standard library only) and registers it in
`.mcp.json` next to any servers you already have. Each tool runs odd itself and returns its exit code and output,
so the tools can never disagree with the command line. Only the test suite has driven it so far.

**Can it run several agents at once and keep the best attempt?**
`odd race <slug>` (a tool newer than 0.4.0) runs the outcome as N attempts, each by an agent command you configure
in `"agents"` in `.odd/config.json`, each in its own git worktree under `.git/`, never in your working tree. Every
attempt is checked as `odd done` would check it, and an attempt that edits the proof's test files or the outcome
is discarded. The winner is the verified attempt whose proof caught the most small breaks, then the smallest, then
the first to finish; it is applied to your tree only if you have no changes inside the boundary, otherwise it is
written as a patch. Seal the proof first (`odd seal`; `"race_seal": true` makes the race refuse an unsealed one).
odd calls no model itself. On fake agents the correct attempt won 10 races of 10; real agents are not measured yet.

**Can an attempt leave something behind on my machine?**
Less than in B1 and B2. Each attempt's tree is a `git clone --shared` under `.git/`, so a `git config`, a
hook, an exclude rule or a branch it makes stays in its own clone and is deleted with it (earlier builds used linked
worktrees, which share your `.git/config` and hooks). Before the check odd puts the clone's config, hooks and index
back, so these cannot hide a change from the check either. On Linux, a process the agent detached (`setsid`, a daemon)
is found by its `ODD_ATTEMPT` mark, killed, and the attempt refused. Not covered: an agent that writes outside its
tree on purpose (absolute paths, `git -C` on your repository; it runs as you), a process that clears its environment,
and macOS, which has no `/proc` (only the agent's process group is killed there).

**Can it try a cheap model first and pay for a stronger one only when needed?**
`odd cascade <slug>` (a tool newer than 0.4.0) runs the agent commands in `"agents"` in order, cheapest first, one
level at a time, each attempt in its own git worktree and checked as `odd done` would. The first verified attempt is
applied and the dearer agents never run; a refused attempt's full finding (the failing output, the surviving break and
its line, the line the proof never ran) goes into the next agent's prompt; after the last level the outcome is parked
with every reason. You put the agents in order; odd does not know prices. Costs appear only when your agent command
prints a line `odd-cost: <usd>` at the end. Under `"strength": "report"` an attempt with a surviving break still counts
as verified and stops the cascade; use `"enforce"` to escalate on it. Real agents are not measured yet.

**Can a stronger model write the proof and a cheaper one the code?**
Yes: `odd spec <slug> --proof-by "<command>"` (a tool newer than 0.4.0). The command writes only the proof, in its own
git worktree; odd refuses it if it changed anything but test files or if the proof does not fail before the code, and
passes the reason to the next try (3 tries by default, `"proof_tries"`), then parks the outcome. An accepted proof is
brought back, sealed red and labelled `proof-by: <name>` in the outcome file. `odd race` and `odd cascade` then refuse
any attempt that edits it. The reason to bother: in ExecCritic (arXiv 2609.09133) tests from a weak model lowered a
fixed repairer's resolution from 61.2% to 57.3%, and tests from a stronger model raised it to 65.3%. That is a
published result, not one we have reproduced; the comparison to run is the same cheap implementer with a cheap-written
against a strong-written sealed proof. odd cannot tell whether the proof tests the right thing, only that it is red
first and stays unchanged; read it.

**How do I make sure every requirement of the ticket was done, not just the ones the agent liked?**
List them once in `.odd/requirements/<ticket>.md`, one per line (`R1: ...`, `R2: ...`), and give each outcome a
`covers: R1, R3` line (`odd new ... --covers R1,R3`; a tool newer than 0.4.0). `odd gate`, local and `--recompute`,
and the pull-request summary report each requirement no outcome in the change covers, and fail on a `covers:` id that
is not in the file. With `"coverage": "enforce"` an uncovered requirement fails the gate; the default `"report"` only
prints it, and `"off"` turns the check off. Outcomes without `covers:` behave as before. odd cannot tell whether the
list is the whole ticket or whether a proof tests the requirement it claims to cover; a reviewer reads both. Whether
this lowers missed requirements is not measured yet.

**For a bug fix, how do I know the test reproduces the bug and does not just pass?**
Create the outcome with `odd new ... --kind bug` (a tool newer than 0.4.0). `odd seal` and `odd done` then run the
proof on the unfixed code, the outcome's changed files put back to the base, require it to fail there, and print
`reproduced: <last line>`; a proof that passes on the unfixed code is refused. The line shows how it failed; odd
cannot tell whether that is the reported symptom (an import of a file the fix added also fails), so read it.

**How do I state a refactor, where nothing new should be observable?**
`odd new <slug> "<sentence>" --in "<globs>" --kind refactor` (a tool newer than 0.4.0): the proof defaults to the
whole suite of the runner odd detects (for example `python3 -m unittest discover -q -s tests`), and the outcome
records `counterfactual: skip - behaviour-preserving refactor`, since taking a refactor out should change nothing.
`done` then passes when the suite passes and no existing test was edited unexplained; the take-out and strength
checks are skipped, so odd does not show the suite runs the changed lines. The sentence still needs an observable:
"Every existing test of billing still passes after the split." `--kind feature` and `--kind bug` print their own
hints (the proof covers the new behaviour and the suite stays green; reproduce first). Turning a `kind: bug` outcome
into a refactor to skip the reproduce rule shows: a sealed one fails until resealed, and the local gate prints `kind
changed from bug`.

**What if the ticket is too vague to state a checkable outcome?**
`odd new` refuses a sentence with no observable (no verb such as sees, gets, returns, is refused, and no measurable
term such as a number, every, within, seconds) and suggests "<who> <observes> <what>, measurably". The agent is told
to ask one precise question instead of guessing: `odd ask <slug> "<question>"` writes it into the outcome file, and
the gate shows "waiting for an answer" for that outcome rather than a fail. Delete the `asked:` line once it is
answered; until then the outcome covers no files and no requirement, so it does not satisfy `"coverage": "enforce"`.
The check is a word list, not a model: it stops "Refactor the billing module." and "Improve the code so the tests
pass." (the suite passing is not an observable), passes state sentences such as "The login button is disabled while
the request is pending.", lets through vague sentences that contain a listed word, and refuses ordinary sentences
built only from words it does not list; set `"ambiguity_stop": false` if it gets in your way (for example, outcomes
written in another language). A tool newer than 0.4.0. Whether it lowers rework is not measured.

**When `odd done` fails, how does my agent know what to fix?**
The output ends with a `next:` block: one line per item that is present (the proof's failing line, each small break
the proof did not notice, each changed line it never ran, each test edit refused for lack of a reason) and the
command to rerun. A failure with none of these items (nothing changed inside `in:`, the proof passes with the change
taken out) has no block: rerunning would fail the same way, and the message says what to do. Race, cascade (whose next prompt carries it) and the MCP server (`structuredContent.next`) give the
same block. It states facts and does not say how to pass. A tool newer than 0.4.0. Whether it shortens the loop is
not measured.

**What is a sensible way to adopt it?**
1. Today: run the demo (60 seconds).
2. This week: `odd init` on one repository and use it on your next agent task.
3. This month: add the action as a required check on agent pull requests.
4. Tell us: open an issue when it catches something, and when it gets in your way.

**A challenge to try on your own code:** take the last change your agent called finished, state its outcome and
proof, and run `odd done`. If the proof still passes with the change taken out, that test proves nothing.

## Explaining it in a session

A ten-minute talk built around the live demo.

1. **Hook (1 min).** "Who has had an AI agent tell you a task was done, and it wasn't?" Then: "The tests passed. They
   just didn't test anything the change did."
2. **The problem (1 min).** Agents decide when they are done; their "done" is a claim. More rules do not fix it. Tell
   the source story: 1,856 instructions over three months, and the two costliest mistakes were the process's own rules.
3. **The idea (30 s).** On screen: *An outcome counts as delivered only when its proof fails without the change.*
4. **Live demo (3 min).** `bash launch/demo.sh`. The agent states the outcome, writes a test that asserts nothing and
   says done; `odd done` takes the change out, sees the test still pass, and refuses it. That is the moment people
   remember. Then a real test and fix are verified, and CI recomputes the verdict.
5. **Why it is different (1.5 min).** "Other frameworks help the agent plan. ODD checks whether the work is actually
   done." Done is a command's verdict; the proof must fail without the change; in CI a change cannot loosen its own
   check; `odd park` makes honesty acceptable.
6. **Who it is for (1 min).** Developers with agents, teams letting agents open pull requests, anyone running agents
   unattended. It sits under Spec Kit, BMAD or Superpowers.
7. **Honesty (1 min).** "We are running the same tasks with five approaches and publishing whatever it shows. Early
   sign: strong models already get most work right, so ODD's value is trust and an honest done, not a smarter agent."
8. **Close (30 s).** "`pipx install odd-tool`, then `odd init`. In CI it is one line. Everything is on GitHub,
   including what did not work."

**Tips.** Lead with the refusal in the demo. Use the real numbers from the source project. Make no speed or quality
claim until the comparison is published. Better still, run `odd done` live on a real agent change from someone in the
room: one catch on their own code beats any slide.

**Why people should use it, in a sentence each:**
- It costs five minutes to try and nothing to remove.
- It catches the false "done" on your own code, where you can see it.
- It gets more useful as models improve, because more code goes unread.
- It does not ask you to believe a claim: the evidence and the comparison are public, including what failed.

> Your agent says it's done. ODD checks. Five minutes to try, nothing to lose.
