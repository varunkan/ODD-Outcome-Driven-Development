# Changelog

Each entry names the backlog item that carries its reason and evidence ([BACKLOG.md](BACKLOG.md)); behaviour is
specified in [DESIGN.md](DESIGN.md).

## 0.5.0

The first public release. See [launch/RELEASE-NOTES-v0.5.0.md](launch/RELEASE-NOTES-v0.5.0.md). 0.4.0 was the number
used during development and was never published.

**The core**
- `init`, `new`, `done`, `gate`, `park`, `seal`, `escaped`, `stats`; the take-out check; proof strength; the GitHub
  Action.

**Agents and attempts**
- `odd race`, `odd cascade`, `odd chain`: several attempts at one outcome, each in its own copy; the proof picks.
- `odd spec`: another agent writes and seals the proof. `odd challenge`: an agent tries to break a verified change.
- `odd plan`, `odd start`, a `reasoner` setting; premises (`assume:`) and a predicted failure (`red-because:`).
- Attempt budgets (`max_attempts`, `max_cost`), a verification cache, `odd stats` with costs.

**Checks**
- `kind: bug` (reproduce first), `kind: refactor`, `same:` (behaviour unchanged), held-out proofs, per-file inertness.
- `probe:` (passing attempts must agree), literals copied from the proof (advisory), `entry:` (the proof must run
  the entry point).
- `"cases": "require"`: requirements written with their edge cases, each named in a test (item 44).
- `reject:` (report only): inputs odd makes from the proof's examples that the entry point does not reject (45).
- Hostile inputs through `entry:`, report only: any that end in a traceback or a signal (50).
- A proof whose command or tests name the repository's own absolute path is refused (49).
- Passing attempts compared on inputs odd makes (46).
- Standing checks, flaky-proof repeats, guards on earlier outcomes, duplication, owed steps on the real system.

**Leaner by default** (the ruling in docs/evidence/data/lean-ruling.md)
- The method text is about 1,200 characters (it was about 2,600); `"coverage"` is `off` by default.
- `odd done` and `odd gate` end with one `VERDICT:` line; with odd's hooks a report must carry it.

**A second reading**
- `odd reread`: another agent writes a proof from the request without seeing the change; odd runs it on the change.
  Advisory (54).

**With no setup**
- `odd check`: the take-out check on any change, with no outcome file; also a Stop hook (`--stop-hook`), an Action
  mode (`mode: check`) and an MCP tool. Report only (53).
- A proof that begins with `cd` into the repository's own absolute path is rewritten, not refused.

**Reports**
- `odd claim`: what is proven, what is not, one verdict line, generated from the gate's facts (43).
- `odd ask`, `odd ask --open`; requirement coverage (`covers:`); the auto-merge lane; `odd ship`; `odd owed`.
