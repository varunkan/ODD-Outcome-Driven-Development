# Runner notes: the permission setting and what was checked

## The flags `run.py` adds to every session

```
--permission-mode acceptEdits --permission-prompts none --allowedTools Bash,Read,Glob,Grep,Skill
```

They are `PERMISSION_FLAGS` in `run.py`, the same for every arm (fairness rule 1). `agent_command` also adds
`--no-session-persistence` (listed by `claude --help` in 2.1.322), so no transcript of a benchmark session is kept
under `~/.claude/projects` for a later session to find.

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
  them the hosting session's (the session reported its host's entry point). Those two sessions inherited the whole
  environment of the hosting agent session; `run.py` no longer passes it (next section).

## The agent's environment: an allow-list

`agent_env` in `run.py` gives the agent only `PATH`, `HOME`, `LANG`, `LC_*`, `TERM`, `USER`, `LOGNAME`, `SHELL`,
`TMPDIR`, the names given with `--pass-env NAME`, and `GIT_CONFIG_GLOBAL` set to an empty file of the session's own.
Never passed, even with `--pass-env` (refused at start): `BENCH_*`, `PWD`, `OLDPWD`, and every `CLAUDE*` name except
`CLAUDE_CODE_OAUTH_TOKEN`. The names each agent received are the record's `env_passed`. The session repository has
`user.name bench` and `user.email bench@example.com` in its local config, so an arm that commits works on any machine.

What the CLI needs here, found by experiment on 2026-11-11 (CLI 2.1.322, root): one call,
`env -i PATH=... HOME=... claude -p "Say ok" --model haiku --max-turns 1 --no-session-persistence --output-format json
--strict-mcp-config --setting-sources project`, returned a `success` result for $0.0016. So `PATH` and `HOME` are the
whole set on this machine: the login is read from the credentials file under the home directory, and no proxy or CA
variable was needed to reach the API. A machine that logs in with a variable or needs a proxy names it with
`--pass-env` (for example `ANTHROPIC_API_KEY`, `HTTPS_PROXY`, `NODE_EXTRA_CA_CERTS`); the record then shows it.
`setup.sh` and `post.sh` are not the agent: they get the shell's environment (setup downloads frameworks) plus
`BENCH_CACHE`, `ODD_PY` and `BENCH_PRIVATE`.

## What `run.py` does beyond the letter of SPEC.md

- When the session ends nothing writes to its directory again. `run.py` makes two copies outside it, each in a
  temporary directory of its own: P, where `arms/<arm>/post.sh` runs (its exit status is `arm_check`), and G, where
  `.bench/` is written, the hidden tests are copied in and `grade` runs. Both are removed after the grade, with or
  without `--keep`; `--keep` keeps the session directory as the session left it.
- Changed lines are measured in a scratch git index seeded from the "arm setup" commit and kept outside the session.
- Token counts are the sums over the CLI's `modelUsage` when it is present, because `usage` covers the main
  conversation only (session 1, one subagent: 1,071 output tokens in `usage`, 1,410 in `modelUsage`). Cost is the
  CLI's `total_cost_usd` either way.
- The session directory is `<temp>/bench-<random>/s/project`: a top-level temporary directory per session (mode
  700), whose path names neither the task nor the arm. Two levels up there is only that session's own `s/`, its empty
  git config and `private/` (`BENCH_PRIVATE`: the Superpowers arm copies its plugin there, so concurrent sessions
  never share a writable plugin directory). Three levels up is the temporary directory itself, where the other
  sessions and, while one is being graded, its copy G sit: running as root, nothing on the filesystem is out of a
  session's reach, which is why contamination is detected from the transcript.
- The odd arm runs `odd.py` as committed at the bench repository's HEAD (`git show HEAD:odd.py`, written into the
  cache as `odd-<sha256>.py`), never the working-tree file. A run with a model from a repository with uncommitted
  changes is refused unless `--allow-dirty` is given; every record's `provenance` holds `bench_commit`, `bench_dirty`,
  `odd_sha256`, `task_tree` (sha256 over the task directory's file paths and contents) and `arm_version` (the arm's
  `VERSION` file).
- A run whose setup fails is written with `passed: null` and its error; `report.py` counts it apart, in no rate.
- Hidden tests are kept out of the session directory, not off the machine: a session that can run shell commands can
  read any file the user can. Nothing in a session points at them.
