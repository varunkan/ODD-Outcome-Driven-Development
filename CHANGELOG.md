# Changelog

Each entry names the backlog item that carries its reason and evidence ([BACKLOG.md](BACKLOG.md)); behaviour is
specified in [DESIGN.md](DESIGN.md), where everything below is marked "needs a tool newer than 0.4.0".

## Unreleased

Built since 0.4.0 and not yet in a release.

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
- `reject:` and `"reach": "require"`: the entry point must reject inputs odd makes from the proof's examples (45).
- Passing attempts compared on inputs odd makes (46).
- Standing checks, flaky-proof repeats, guards on earlier outcomes, duplication, owed steps on the real system.

**Reports**
- `odd claim`: what is proven, what is not, one verdict line, generated from the gate's facts (43).
- `odd ask`, `odd ask --open`; requirement coverage (`covers:`); the auto-merge lane; `odd ship`; `odd owed`.

## 0.4.0

The first public release: `init`, `new`, `done`, `gate`, `park`, `seal`, `escaped`, `stats`; the take-out check;
proof strength; the GitHub Action. See [launch/RELEASE-NOTES-v0.4.0.md](launch/RELEASE-NOTES-v0.4.0.md).
