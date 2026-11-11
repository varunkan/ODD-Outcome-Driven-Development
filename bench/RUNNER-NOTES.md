# Runner notes: the permission setting and what was checked

## The flags `run.py` adds to every session

```
--permission-mode acceptEdits --permission-prompts none --allowedTools Bash,Read,Glob,Grep,Skill
```

They are `PERMISSION_FLAGS` in `run.py`, the same for every arm (fairness rule 1).

- `--permission-mode acceptEdits`: the file tools create and edit files inside the session directory without asking.
- `--allowedTools Bash,Read,Glob,Grep,Skill`: shell commands; reading outside the session directory (a plugin
  directory, a framework's installed files); invoking skills.
- `--permission-prompts none`: whatever would still ask is refused at once, so no session waits for an answer nobody
  will give.

No bypass flag is used. The CLI refuses `--dangerously-skip-permissions` for root unless `IS_SANDBOX=1` is set: that
check and its message ("cannot be used with root/sudo privileges") were read in the CLI's own code, not triggered.
This container does set `IS_SANDBOX=1`, so a bypass would be accepted here, but the runner would then work only where
that variable is set. The flags above do not depend on it.

## Evidence

Two real sessions on 2026-11-11: CLI 2.1.322, user id 0 (root), `--model haiku`, `--max-budget-usd 0.40` each, in
scratch directories under the system temporary directory. A third was allowed and not needed.

| | session 1: the CLI directly | session 2: through `run.py` |
|---|---|---|
| started as | `claude -p <prompt> --model haiku --output-format stream-json --verbose --setting-sources project --strict-mcp-config --max-turns 14 --max-budget-usd 0.40` + the flags above | `run.py --root <scratch> --model haiku --max-turns 15 --max-budget-usd 0.40 --timeout 240 --jobs 1 --keep` on a one-file task, with an arm whose `setup.sh` wrote `.bench-plugin-dir` |
| asked to | write `ok.txt` with the file tool; run `echo shell-ok > sh.txt`; invoke a project skill; have a subagent write `sub.txt` | fix the task, then invoke a skill that exists only in the plugin directory |
| file edit | `ok.txt` = `ok` | `calc.py` fixed with the edit tool |
| shell command | `sh.txt` = `shell-ok` | two ran (one ran Python to check the fix); read from the saved transcript |
| skill | project skill ran: `skill.txt` = `skill-ok` | plugin skill ran: `plugin-marker.txt` = `plugin-ok`, so `--plugin-dir` took effect |
| subagent | ran: `sub.txt` = `sub-ok` (1 spawned, 1 completed) | not asked |
| refused tool calls | `permission_denials: []` | not reported in this output format; all four tool calls in the transcript ran; exit 0 |
| result | `success`, 7 turns, 14.0 s, $0.0083 | passed the hidden test, claim DONE, 6 turns, 7.1 s, $0.0031, 3 changed lines in 2 files |

Session 2 also shows that `--output-format json` prints one object that `run.py` reads (`result`, `total_cost_usd`,
`num_turns`, `duration_ms`, `usage`, `modelUsage`), and that `--max-turns`, which `claude --help` does not list in
this version, is accepted.

## Not shown by these sessions

- A cap being reached (`--max-turns`, `--max-budget-usd`) or a real session being stopped by `--timeout`. The stop
  is tested with a fake agent only; the CLI's `error_max_turns` shape is covered by a unit test, not seen live.
- A refusal. Nothing was asked that should be refused (the web tools, a file-tool write outside the session
  directory), so what a refusal costs an arm is unknown.
- The Spec Kit, BMAD and Superpowers arms under these flags, and any model other than the cheapest alias.

## What a session still inherits on this machine

From the start-up record of session 1, despite `--setting-sources project --strict-mcp-config`:

- MCP servers: none. User-level skills: none (the home directory has two; neither was listed).
- 22 skills were listed: the project's own and 21 that ship with the CLI or its host. 40 tools were listed, some of
  them the hosting session's (the session reported its host's entry point). So when `run.py` is itself started from
  inside an agent session, that session's environment variables reach every benchmark session. This is the same for
  every arm, but it is not what a plain terminal gives. `run.py` does not strip them: which of them carry the login is
  not known, and a third probe could not have settled it.

## What `run.py` does beyond the letter of SPEC.md

- `arms/<arm>/post.sh`, when present, runs after the session and before the hidden tests; its exit status is recorded
  as `arm_check`. SPEC.md's layout does not list `post.sh`; the odd arm has one.
- Changed lines are measured in a scratch git index seeded from the "arm setup" commit, so the session's own index
  and tree are untouched when `post.sh` runs. The measure runs before `post.sh` and before `.bench/` is written.
- Token counts are the sums over the CLI's `modelUsage` when it is present, because `usage` covers the main
  conversation only (session 1, one subagent: 1,071 output tokens in `usage`, 1,410 in `modelUsage`). Cost is the
  CLI's `total_cost_usd` either way.
- The session directory is `<temp>/ws-<random>/r<random>/project`: its path names neither the task nor the arm.
  `ODD_PY` and `BENCH_CACHE` are given to `setup.sh` and `post.sh` only, never to the agent.
- A run whose setup fails is written with `passed: null` and its error; `report.py` counts it apart, in no rate.
- Hidden tests are kept out of the session directory, not off the machine: a session that can run shell commands can
  read any file the user can. Nothing in a session points at them.
