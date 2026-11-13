# superpowers

Superpowers (github.com/obra/superpowers), loaded as the Claude Code plugin it is, for one session at a time.

## To state with the results

- Release v7.0.2 is measured, loaded with `--plugin-dir`. The prompt is the ticket alone, as for the plain arm.
- The workflow is written for a person who answers: it waits for approval of a design, consent to a worktree, a
  choice of how to execute and a choice of how to finish. Nobody answers here, and what the session then does is
  part of what is measured.
- Its skills can move the work to another branch or a git worktree. Only the files left in the session directory
  are graded, which the common ending tells every arm; a run that left work elsewhere is marked `left_outside`.
- Design documents and plans under `docs/superpowers/` count in `changed_lines` and `files_changed`, not in
  `changed_lines_py`.
- Its subagents' cost is in the CLI's totals; the models they used are in `models`.
- Each session loads its own copy of the pinned plugin under `BENCH_PRIVATE` (no `.git`); a session cannot change
  the copy another session uses.
- No session of this arm had been run when these notes were written (see "Not verified").

## Version pinned

Release `v7.0.2`, published 2026-11-03, marked "Latest" on 2026-11-11 (the default branch was at the same commit).
The pin is the commit the tag names: `22f0b463e7a5e579904dd6211a520321035526f7` (the annotated tag object is
`c62ffea8267a70de07583e153544d355b6748a56`). `setup.sh` clones the tag and then requires the checkout to be that
commit, so a tag that is later moved fails setup instead of changing the arm. The plugin manifest in that commit
declares version `7.0.2`, which `setup.sh` also checks.

## What the plugin is

- `.claude-plugin/plugin.json`: the manifest, name `superpowers`.
- `skills/`: 15 skills, which Claude Code lists as `superpowers:<skill>` (brainstorming, systematic-debugging,
  test-driven-development, writing-plans, executing-plans, subagent-driven-development, using-git-worktrees,
  requesting-code-review, receiving-code-review, verification-before-completion, finishing-a-development-branch,
  dispatching-parallel-agents, diagnosing-superpowers, writing-skills, using-superpowers).
- `hooks/hooks.json`: one SessionStart hook (matcher `startup|clear|compact`). Its command,
  `"${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd" session-start`, prints one JSON object whose `additionalContext` is
  "You have superpowers." followed by the whole text of `skills/using-superpowers/SKILL.md`. That text is what tells
  the agent to look for a skill before doing anything.
- No agents, no commands, no MCP server, no package lockfile (so Claude Code installs nothing for it).

## What `setup.sh` does

1. Takes a file lock in `$BENCH_CACHE` so that setups started together run one at a time.
2. If `$BENCH_CACHE/superpowers` does not exist: `git clone --depth 1 --branch v7.0.2` into a temporary directory
   beside it, checks the commit, and moves it into place. Later runs need no network.
3. Requires the checkout to be the pinned commit; anything else in that place stops setup with a message.
4. If any file in the checkout was changed, added or removed since (by an earlier session or by hand), restores the
   pinned commit and says so on stderr. Every run therefore starts from the same framework files.
5. Runs the hook's own command once and requires the SessionStart JSON with the bootstrap text. A machine where the
   hook prints nothing would otherwise turn this arm into the plain arm without any error.
6. Writes the checkout's absolute path to `.bench-plugin-dir` at the repository root. The file is the path and
   nothing else: no trailing newline.

It adds that one file to the repository and changes no other. Nothing is written to `.claude/`, to the home
directory, or to any user-level configuration. `ODD_PY` is not used.

## What the runner must do

When `.bench-plugin-dir` exists at the repository root, add `--plugin-dir <its content>` to the `claude -p` command.
That is the whole contract. The flag loads the plugin for that session only and does not depend on
`--setting-sources`; the plugin then appears as `superpowers@inline`. Where a flag cannot be added, Claude Code
v2.1.280 or later reads the same path from the `CLAUDE_CODE_PLUGIN_DIRS` environment variable.

Without the flag this arm is the plain arm (same prompt, nothing loaded), and nothing would report it. The runner
should treat "`.bench-plugin-dir` present but not passed" as an error.

## Why `--plugin-dir`, and not files under `.claude/`

- The installs Superpowers documents for Claude Code are marketplace installs (`/plugin install
  superpowers@claude-plugins-official`, or its own marketplace). They write to the user-level plugin directory and
  user settings, which this benchmark must not touch and which `--setting-sources project` does not read.
- Enabling it in the project's `.claude/settings.json` is not enough: by the Claude Code documentation, a plugin
  enabled only in project settings does not load until it is also installed on the machine, and installed plugins
  are kept under the home directory.
- A copy placed as a plugin under the project's `.claude/skills/` is "not used" in a `claude -p` run in a folder
  that was never trusted, and recording trust means editing a user-level file.
- Copying the 15 skills in as plain project skills and registering the hook in `.claude/settings.json` would load,
  but it is not an install the project documents, and it drops the `superpowers:` prefix that the bootstrap text and
  the skills use to refer to each other.
- `--plugin-dir` loads the release unmodified, and it is how the project's own headless tests start it:
  `claude -p "$PROMPT" --plugin-dir "$PLUGIN_DIR"`, with `PLUGIN_DIR` the repository root.

## The prompt

The ticket alone, byte for byte the plain arm's prompt; the runner adds the common ending (`arms/TAIL.md`). The
README says "because the skills trigger automatically, you don't need to do anything special", and the project's own
tests pass a plain request. No slash command and no skill name is added, so the only difference from the plain arm
is the plugin.

## Reading this arm's results

The workflow is written for a person who answers. In the pinned release: brainstorming has a hard gate ("Nothing
gets built until your human partner approves the design doc"), using-git-worktrees asks for consent before creating
a worktree, writing-plans asks which way to execute, and finishing-a-development-branch presents three options and
waits. `using-superpowers` also says that user instructions take precedence over skills. The common sentence that
nobody will answer is the only thing this arm's prompt says about that; what the session then does is part of what
is measured, and the prompt adds nothing to steer it.

- Design documents (`docs/superpowers/specs/`) and plans (`docs/superpowers/plans/`) are written into the repository
  and count in "changed lines".
- If the session does its work in a git worktree or on another branch and never brings it back, the tree the
  hidden tests run on does not contain the change, and the run is graded as not passed.
- subagent-driven-development starts a subagent per task; their cost is in the CLI's totals.
- The only outside request the plugin itself can cause is a logo on brainstorming's optional browser page, which
  carries the plugin version. The README documents `SUPERPOWERS_DISABLE_TELEMETRY=1` to turn it off; this arm does
  not set it, and the runner may set it in the session's environment.

## Sources

- Repository at the pinned tag: https://github.com/obra/superpowers/tree/v7.0.2
- Release (tag, commit, "Latest"): https://github.com/obra/superpowers/releases/tag/v7.0.2
- README: skills trigger automatically, line 46; Claude Code installs, lines 56-82; the workflow, lines 308-324;
  telemetry switch, lines 398-400: https://github.com/obra/superpowers/blob/v7.0.2/README.md
- Manifest: https://github.com/obra/superpowers/blob/v7.0.2/.claude-plugin/plugin.json
- Hook: https://github.com/obra/superpowers/blob/v7.0.2/hooks/hooks.json,
  https://github.com/obra/superpowers/blob/v7.0.2/hooks/run-hook.cmd,
  https://github.com/obra/superpowers/blob/v7.0.2/hooks/session-start
- The project's own headless runs with `--plugin-dir`: lines 25 and 71-75 of
  https://github.com/obra/superpowers/blob/v7.0.2/tests/explicit-skill-requests/run-test.sh and lines 160 and 167 of
  https://github.com/obra/superpowers/blob/v7.0.2/tests/claude-code/test-subagent-driven-development-integration.sh
- Skills quoted above, under https://github.com/obra/superpowers/blob/v7.0.2/skills/ :
  `using-superpowers/SKILL.md` lines 63-65; `brainstorming/SKILL.md` lines 269-283; `using-git-worktrees/SKILL.md`
  lines 41-45 and 76; `writing-plans/SKILL.md` lines 16 and 189; `finishing-a-development-branch/SKILL.md` lines 55-81.
- `--plugin-dir`, `--setting-sources`: https://code.claude.com/docs/en/cli-reference
- Loading a plugin for one session, `CLAUDE_CODE_PLUGIN_DIRS`: https://code.claude.com/docs/en/plugins/create
- The `@inline` origin, loading in place, project-enabled plugins needing an install, name conflicts:
  https://code.claude.com/docs/en/plugins/loading
- `claude --plugin-dir <dir> plugin list`, `claude plugin validate`, managed `disableSideloadFlags`:
  https://code.claude.com/docs/en/plugins/cli-reference
- What a `claude -p` run uses from an untrusted folder: https://code.claude.com/docs/en/permissions
  ("What runs before you trust a folder")
- Hook output: `additionalContext`, its 10,000-character limit, plugin hooks: https://code.claude.com/docs/en/hooks

## Verified by running (2026-11-11, Linux, bash 5.2, git 2.43, Claude Code 2.1.322; no session started)

- `setup.sh` in a scratch git repository holding a task's starting files, empty cache: exit 0; the only change in
  the repository is the new `.bench-plugin-dir`; the cache holds `superpowers/` at the pinned commit with no changed
  file, and the lock file.
- A second run after committing: exit 0, `git status` empty, same file list, same sha256 for every cache file.
- Four setups started together on one empty cache: all exit 0, exactly one clones.
- A run with `HOME` set to an empty directory: exit 0, the directory stays empty.
- Each check fails when it should: `BENCH_CACHE` unset; a checkout with an edited, an added and a deleted file
  (restored byte for byte, with the warning); a checkout at another commit; a plain directory in its place with the
  cache inside another git repository; hook output in another tool's format; a pin that differs from the tag's
  commit (exit 1, nothing left in the cache).
- The hook command run by hand from the task repository: exit 0, one JSON object for SessionStart, 3,405 characters
  of `additionalContext` holding the whole `using-superpowers` skill (under the documented 10,000-character limit).
- `claude plugin validate <checkout>`: "Validation passed".
- `claude --setting-sources project --strict-mcp-config --plugin-dir <checkout> plugin list --json`, from the task
  repository: one plugin, `superpowers@inline`, version 7.0.2, scope `session`, enabled.

## Not verified

- No `claude` session was run. Not observed: that in `claude -p --setting-sources project --strict-mcp-config
  --plugin-dir <checkout>` the SessionStart hook fires and its text reaches the model, that the skills then trigger
  from a ticket alone, and what the workflow does when nobody answers. The documentation and the project's own tests
  say the first two hold; the pilot should confirm them from a transcript (a `Skill` call naming `superpowers:...`).
- macOS and Windows. The script uses only bash, git and python3, but was run on Linux only.
- A machine whose managed settings turn off `--plugin-dir`: Claude Code then exits 1 without starting.
- The cached checkout is shared and writable, but no session loads it: each one gets its own copy under
  `BENCH_PRIVATE`.
