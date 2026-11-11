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

## The caps, seen live (one statement; this replaces the earlier "not seen live")

On CLI 2.1.322 on 2026-11-11 both caps were reached live with `haiku` and `run.py`'s flags (preflight transcripts
`q2turns.jsonl` and `q2budget.jsonl`, kept in the preflight scratch directory outside this repository):

- `--max-turns 1` on a task needing two shell calls: exit 1; final `result` event `subtype: error_max_turns`,
  `is_error: true`, `result: null`, `errors: ["Reached maximum number of turns (1)"]`; `num_turns` reads **2** (the
  CLI counts the turn that hit the cap), so a turn figure at a cap is the cap plus one. The first file was written.
- `--max-budget-usd 0.00001`: exit 1; `subtype: error_max_budget_usd`, `is_error: true`, `result: null`,
  `errors: ["Reached maximum budget ($0.00001)"]`, `num_turns` 1; no tool ran.

`run.py` grades both as they stand (`CAPS`: `stopped_at` `max_turns` / `max_budget`); the final message is empty, so
the claim is `none`. The unit test `test_a_reached_cap_is_graded_and_named` replays these shapes.

## The CLI reads a root AGENTS.md by itself

Preflight on CLI 2.1.322, 2026-11-11, with `run.py`'s flags (`--setting-sources project --strict-mcp-config
--no-session-persistence`, the permission flags) and its allow-listed environment: in a scratch repository holding
only an `AGENTS.md` (no `CLAUDE.md`) that names a secret phrase, `haiku` answered with that phrase in one turn and no
tool call; with a `CLAUDE.md` that imports `@AGENTS.md`, the same; without `AGENTS.md`, it answered `NONE`. So the
odd arm's method text (written to `AGENTS.md` by `odd init`) reaches the model with no import and no extra prompt
text (transcripts `q1a.jsonl`, `q1b.jsonl`, `q1c.jsonl` in the same preflight directory). Not yet shown: that each
framework's text reached the model in a real benchmark run of every arm (no per-arm pilot has run).

## Not shown by these sessions

- A real session being stopped by `--timeout`, or a real context overflow (`Prompt is too long`). Both are tested
  with fake agents only.
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
the names given with `--pass-env NAME`, `GIT_CONFIG_GLOBAL` set to an empty file of the session's own, and `TMPDIR`
set to `<top>/tmp`, the session's own (never the shared temporary directory, where the other sessions sit; a
`TMPDIR` passed with `--pass-env` is ignored).
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

- When the agent exits, `run.py` kills its process group, then (Linux `/proc`) every process whose cwd, executable
  or an open file is under the session's top: the CLI may detach a shell into a group of its own. The count is the
  record's `leftovers_killed`; where `/proc` is missing it is null and a warning says nothing was checked. Only then
  is the tree measured and copied, so nothing the agent started writes into it afterwards.
- When the session ends nothing writes to its directory again. `run.py` makes two copies outside it at once, each
  in a temporary directory of its own: P, where `arms/<arm>/post.sh` runs (its exit status is `arm_check`; what it
  writes to `$BENCH_POST_NOTES`, a JSON object, is the record's `arm_notes`), and G, which waits. **No hidden test
  is on disk outside `tasks/` while any session runs**: every grade runs only after the whole session pool has
  drained. Then, in each G, the visible tests as shipped replace whatever the session left at `tests/` (a
  directory, a file or a symlink), `.bench/` is written, each top-level path of `hidden/` is cleared (a symlink the
  session left there is removed, never followed) and copied in, every hidden `*.py` gets a line
  `# bench-canary-<24 random hex>`, and `grade` runs. Both copies are removed after the grade, with or without
  `--keep`; `--keep` keeps the session directory as the session left it. Proven by the peek probe
  (`test_no_hidden_test_is_on_disk_while_any_session_runs`): a fake agent searching `../../..` for five seconds while
  another session's grade sleeps finds nothing; before the change it found that session's `tests_hidden`.
- Contamination (SPEC.md rule 8) is audited after every grade, over every string of every transcript event (tool
  inputs, tool results, text, subagents' events) and lines that are not JSON: the bench repository, `tests_hidden`,
  `/hidden/`, another session's top, or any `bench-canary-` string. The canary catches a hidden test read under
  another name, including one from a concurrent invocation in the same temporary directory.
- A context overflow (an error result after at least one turn with the CLI's `Prompt is too long` in the result or
  an assistant message) is the arm's outcome: the tree is graded, `stopped_at` is `context`. The same text before
  any turn is not graded.
- The odd arm's `post.sh` runs the pinned `"$ODD_PY" gate --recompute --base main` in P, never the session's
  `.odd/odd.py`, and reports `arm_notes.odd_py`: `same`, `differs` (the session changed its copy) or `missing`.
- Changed lines are measured in a scratch git index seeded from the "arm setup" commit and kept outside the session.
- Token counts are the sums over the CLI's `modelUsage` when it is present, because `usage` covers the main
  conversation only (session 1, one subagent: 1,071 output tokens in `usage`, 1,410 in `modelUsage`). Cost is the
  CLI's `total_cost_usd` either way (`usage_from: result`).
- A session stopped by `--timeout` has no result event. Its tokens, turns and models are rebuilt from the saved
  transcript (`usage_from: transcript`): the usage of every assistant message, each message id once (the CLI repeats
  a message's usage on every event it splits it into), subagents included; turns count the main conversation's
  messages, so they may differ from the CLI's own `num_turns` by the one-turn offset seen at a cap. The cost stays
  null with `cost_missing: true` and `cost_missing_reason`: the CLI prices a session only in its result event and
  `run.py` keeps no price table of its own (a table copied here would go stale unseen). `report.py` must count such
  runs rather than drop them silently.
- The session directory is `<temp>/bench-<random>/s/project`: a top-level temporary directory per session (mode
  700), whose path names neither the task nor the arm. Two levels up there is only that session's own `s/`, its empty
  git config and `private/` (`BENCH_PRIVATE`: the Superpowers arm copies its plugin there, so concurrent sessions
  never share a writable plugin directory). Three levels up is the temporary directory itself, where the other
  sessions and the waiting copies sit (no hidden test among them while a session runs): running as root, nothing
  on the filesystem is out of a session's reach, so another arm's work in progress on the same task can still be
  read. Contamination is detected from the transcript: any other session's directory name (`bench-` plus eight
  characters, as mkdtemp makes them) seen anywhere in it, including in a listing of `../../..`, marks the run.
- The odd arm runs `odd.py` as committed at the bench repository's HEAD (`git show HEAD:odd.py`, written into the
  cache as `odd-<sha256>.py`), never the working-tree file. A run with a model from a repository with uncommitted
  changes is refused unless `--allow-dirty` is given; every record's `provenance` holds `bench_commit`, `bench_dirty`,
  `odd_sha256`, `task_tree` (sha256 over the task directory's file paths and contents) and `arm_version` (the arm's
  `VERSION` file).
- A run whose setup fails is written with `passed: null` and its error; `report.py` counts it apart, in no rate.
- Hidden tests are kept out of the session directory and, while any session runs, out of the temporary directory;
  they stay readable under `tasks/` in the bench repository: a session that can run shell commands can read any file
  the user can. Nothing in a session points at them, and a transcript naming the repository is contaminated. No
  sandbox (bwrap, unshare) is used.

## The agent can see a dollar cap, so measured runs do not set one (pilot, 2026-11-11)

`--max-budget-usd` is written into the agent's system prompt: asked to quote any budget, a headless session started
with `--max-budget-usd 2` answered "USD budget: $0/$2; $2 remaining", and one started without it found none. A
`--max-turns` cap is not shown ("I found no turn limit"). In the pilot, the BMAD session on t01 read its workflow and
then reported that it "did not run the BMAD workflow's review and spec steps, to stay within budget". A visible cap
therefore penalises the arms whose process has more steps. `run.py` passes `--max-budget-usd` only when it is given
explicitly (default off) and every measured run is bounded by `--max-turns` and `--timeout` alone. Every session sees
the same token count (`<total_tokens>`), which the CLI shows regardless.
