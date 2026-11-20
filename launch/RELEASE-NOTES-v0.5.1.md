# odd 0.5.1

Outcome-Driven Development (ODD) for coding agents: an outcome counts as delivered only when its proof fails without
the change. 0.5.0 was the first public release; 0.5.1 changes no behaviour and brings the README up to date (the
problem in its measured forms, where to use odd, and setup in Claude Code, Cursor and GitHub Copilot).

**The quickest way in, with no setup:** `pipx install odd-tool`, then `odd check` in any git repository after a
change with tests: it runs the tests the change brings, takes the change out, and runs them again.

**Work is done when a proof says so, not when the agent says so.** Before writing code the agent states one outcome
sentence, a proof command and the files it may touch. `odd done` passes only when the proof passes, fails with the
change taken out, and passes again once the change is put back. `odd gate --recompute` re-runs it in CI and trusts
nothing the agent recorded.

## Install

```bash
pipx install odd-tool          # or: pip install odd-tool, or download odd.py
cd your-project && odd init     # writes .odd/ and the method into AGENTS.md
```

GitHub Actions, one step at the end of your test job, made a required check:

```yaml
- uses: varunkan/ODD-Outcome-Driven-Development@v0.5.1
```

## What is in this release

- One file, standard library only, Python 3.8+. It calls no model; where a command runs an agent, it runs the agent
  command you configure.
- **The core commands:** `init`, `new`, `seal`, `done`, `gate`, `park`, `ask`, `escaped`, `stats`.
- **Several attempts at one outcome:** `race` (N attempts, each in its own copy; the proof picks), `cascade` (agents
  in order, cheapest first, until one is proven), `chain` (a long task as outcomes in order, each proven and
  committed as a checkpoint).
- **Other agents in other roles:** `plan` (a ticket's requirements planned into outcomes), `spec` (another agent
  writes only the proof, sealed before any code), `challenge` (an agent tries to make a verified change wrong while the proof still passes) and
  `second` (a second attempt compared with the verified one); both advisory.
- **Before and after the work:** `start` (checks the outcome's premises and the baseline), `claim` (what is proven
  and what is not, with one verdict line, from the gate's facts), `owed` (closes a step owed on the real system
  against an evidence file), `ship` (binds a built artifact to its commit and that commit's recomputed gate).
- Every command, its exit codes and its limits: the table in [DESIGN.md](../DESIGN.md). Every change by backlog item:
  [CHANGELOG.md](../CHANGELOG.md).
- **The take-out check:** the proof must pass, fail with the change taken out, and pass again.
- **Proof strength:** small deliberate breaks ("mutants") in the changed lines; any the proof does not notice is
  reported, or fails the check with `"strength": "enforce"`. Reported as "proof strength k of n", never as "verified".
- **Sealed proofs:** `odd seal` requires the proof to fail before the code exists and fingerprints it; a later edit
  to the sealed test fails `done` and the gate until it is resealed, which shows in review.
- **The reviewer's comment:** the Action posts one PR comment (updated, never duplicated) with each outcome, its proof,
  what the proof said without the change and the strength score, and writes the same to the job summary.
- **Escaped defects:** `odd escaped` records a defect that got through against the outcome whose proof missed it;
  `odd stats` splits them by kind of proof.
- **Adoption aids:** `--proof auto` picks a narrow proof command from the repository's test runner; an MCP server
  (`odd-mcp`, `odd init --mcp`) lets agents call odd as tools.
- The method (about twenty lines) in `AGENTS.md`, read by Codex, Cursor, Copilot in VS Code, Claude Code, Junie and
  Windsurf without configuration. Optional Claude Code hooks (`odd init --claude-hooks`).

## How it was hardened

- A design review by four critics: 23 required changes, all applied
  ([docs/evidence/10-design-review.md](../docs/evidence/10-design-review.md)).
- A red team of 0.2.0: 48 confirmed defects, each now a test that failed before its fix
  ([docs/evidence/11-red-team.md](../docs/evidence/11-red-team.md)).
- Proof strength, sealed proofs and the reviewer's comment were each built test-first and then reviewed by two
  independent reviewers (tamper resistance; usability and cost). 14 reproduced findings, among them keeping the
  comment token out of the proof's environment and refusing HTML injection into the comment; all addressed except
  the limits stated in DESIGN.md.
- The suite has 400 tests. CI runs it on Linux (Python 3.8 and 3.13) and macOS.

## What the evidence says so far

On a strong model (Sonnet), plain Claude Code already got 48 of 48 hidden-test tasks right, as did ODD; ODD cost
about three cents more per task, less than Spec Kit or BMAD ([13](../docs/evidence/13-verdict-and-use.md)). So ODD's
value shown so far is a "done" that can be checked, not more correct code. On Haiku too, every arm got every doable
task right ([15](../docs/evidence/15-comparison.md)).
What the research literature supports and does not: [14](../docs/evidence/14-research.md).
Everything measured, with what each page does and does not show: [docs/evidence/](../docs/evidence/README.md).

## What is not claimed

No speed or quality gain. Only Claude Code has been run with the method; Windows is untested. The full list of limits
is in [DESIGN.md](../DESIGN.md#10-limits).
