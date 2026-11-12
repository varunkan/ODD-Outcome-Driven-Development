# odd 0.4.0

The first public release of Outcome-Driven Development (ODD) for coding agents: an outcome counts as delivered only
when its proof fails without the change.

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
- uses: varunkan/ODD-Outcome-Driven-Development@v0.4.0
```

## What is in this release

- Commands: `init`, `new`, `done`, `gate`, `park`, `seal`, `escaped`, `stats`. One file, standard library only,
  Python 3.8+.
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
- The 0.4.0 additions were each built test-first and then reviewed by two independent reviewers (tamper resistance;
  usability and cost). 14 reproduced findings, among them keeping the comment token out of the proof's environment
  and refusing HTML injection into the comment; all addressed except the limits stated in DESIGN.md. The suite has
  120 tests, green on Linux (Python 3.8 and 3.13) and macOS.

## What the evidence says so far

On a strong model (Sonnet), plain Claude Code already got 48 of 48 hidden-test tasks right, as did ODD; ODD cost
about three cents more per task, less than Spec Kit or BMAD ([13](../docs/evidence/13-verdict-and-use.md)). So ODD's
value shown so far is a "done" that can be checked, not more correct code. A weaker model (Haiku) is being measured.
What the research literature supports and does not: [14](../docs/evidence/14-research.md).

## What is not claimed

No speed or quality gain. Only Claude Code has been run with the method; Windows is untested. The full list of limits
is in [DESIGN.md](../DESIGN.md#10-limits).
