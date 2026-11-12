# odd 0.3.0

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
- uses: varunkan/ODD-Outcome-Driven-Development@v0.3.0
```

## What is in this release

- Six commands: `init`, `new`, `done`, `gate`, `park`, `stats`. One file, standard library only, Python 3.8+.
- The method (about twenty lines) in `AGENTS.md`, read by Codex, Cursor, Copilot in VS Code, Claude Code, Junie and
  Windsurf without configuration.
- Optional Claude Code hooks (`odd init --claude-hooks`): a status line at session start, and a turn cannot end on
  unproven work.
- A GitHub Action that judges each pull request with its own pinned copy of the tool, and a PyPI package.

## How it was hardened

- A design review by four critics: 23 required changes, all applied
  ([docs/evidence/10-design-review.md](../docs/evidence/10-design-review.md)).
- A red team of 0.2.0: six attackers and an independent reproduction of every finding. 48 confirmed (5 blockers,
  27 major, 16 minor), each now a test that failed before its fix
  ([docs/evidence/11-red-team.md](../docs/evidence/11-red-team.md)). The suite has 82 tests.

## What is not claimed

No speed, cost or quality figure. A same-task comparison against plain Claude Code, Spec Kit, BMAD and Superpowers
is in [`bench/`](../bench/SPEC.md); its results will be published with their spread, whatever they show. Only Claude
Code has been run with the method so far, and Windows and macOS are untested. The full list of limits is in
[DESIGN.md](../DESIGN.md#10-limits).
