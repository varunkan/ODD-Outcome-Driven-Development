# bmad

The BMAD Method (BMad Method), started through its unattended build skill in one headless session.

## To state with the results

- The stable 6.12 line is measured (`bmad-method@6.12.4`), not the v7 preview.
- It is run through the unattended skill `bmad-build-auto`, one headless session per task. BMAD's attended build
  (`bmad-build`, with human checkpoints) and its planning path (`bmad-spec`, stories, one session each) are not
  measured.
- The skill halts `blocked` when a request has more than one defensible reading; the common ending tells every arm
  to decide and proceed. On the vague task the two pull against each other.
- The skill writes its status into its own record file and does not know the `RESULT:` line, which only the common
  ending asks for. A run with claim `none` may still have recorded a status under `_bmad-output/`.
- Its records under `_bmad-output/` count in `changed_lines` and `files_changed`, not in `changed_lines_py`.
- It needs Node.js 20.12 or later, npx and uv on the machine, and the subagent tool in the session: without
  subagents the skill halts `blocked`, and the run then shows the harness, not the method.
- No session of this arm had been run when these notes were written (see "Not verified").

## Version pinned

`bmad-method@6.12.4` from npm (published 2026-10-14; tarball integrity
`sha512-DBVws7H1NxpSOhv2DHvLEHTceQGCv9c+gBx/1cnVF38WhlN70854SnHUUCHkTuLIalu6hq/7LRVtAWCNHmnFEw==`), which is git tag
`v6.12.4`, commit `bab9082c3e884e0d72c759bcd1a6d90bcc01be84`, the npm `latest` tag and the head of the `V6.12` branch
on 2026-11-11. The version is the `BMAD_VERSION` line in `setup.sh`. The installer's own npm dependencies are not
pinned; the files it writes into the repository come only from that package.

The project ships on two lines. Its README on `main` calls v6.12 "the stable release ... installed by the npm
installer and frozen aside from bug fixes" and v7 a "preview alpha" whose "skills, install path, and docs change
often", with a release expected in mid-November 2026. This arm pins the stable line. When v7 is released the arm
needs a new pin and a new `setup.sh`: v7 installs with `npx skills add bmad-code-org/BMAD-METHOD` plus an in-session
`bmad setup`, not with the npm installer. The public docs site (docs.bmad-method.org) already describes v7, so the
sources below are the files at the pinned tag.

## What `setup.sh` does

1. Checks the machine prerequisites the project lists: `node` 20.12 or later, `npx`, `uv`. Missing any, it stops
   with a message. Without `uv` every BMAD build session would halt at its first step, and the run would measure a
   missing tool.
2. Runs the documented headless install, with the version pinned as the install guide says to do in automation:
   `npx --yes bmad-method@6.12.4 install --directory . --modules bmm --tools claude-code --user-name User --yes`,
   stdin closed, npm's cache at `$BENCH_CACHE/npm`. The only addition to the documented command is
   `--user-name User`: without it the installer writes the machine's login name into the project configuration
   (`User` is the installer's own fallback when it cannot read one).
3. Checks that the manifest records 6.12.4 and that the entry skill and the shared render script exist; fails
   otherwise. A second run finds them and changes nothing. (Re-running the installer itself is not idempotent: with
   `--yes` on an existing install it does a "quick update" that rewrites timestamps in four generated files.)
4. Runs `uv run --no-cache _bmad/scripts/render_skill.py --help`, which writes nothing, to prove uv can find the
   Python 3.11 or later that the entry skill's first step needs.

It adds 235 files and modifies none:

- `.claude/skills/` (214 files): 29 skills, among them `bmad-build`, `bmad-build-auto`, `bmad-spec`,
  `bmad-code-review`, `bmad-help`.
- `_bmad/` (21 files): `config.toml`, `config.user.toml`, `_config/` (manifests), `core/` and `bmm/` (module
  configuration), `scripts/` (five Python files the skills run through uv), `custom/` (empty override files),
  `render/` (where a skill writes its rendered copy at run time; ignored by its own `.gitignore`).
- `_bmad-output/`: empty; the build skills write their spec and result records under it.

One of the 235, `_bmad/custom/config.user.toml`, is git-ignored by the installer's own `.gitignore` and stays out of
the harness's commit; `_bmad-output/` is empty and so is not in the commit either. Both remain on disk. No
`CLAUDE.md`, no `AGENTS.md`, no `.claude/settings.json`, no hooks, no MCP server, no git branch, nothing under the
home directory. `project_name` in the configuration is the name of the directory setup runs in.

The install puts 27 Python files in the repository, eleven of them tests
(`.claude/skills/*/scripts/tests/test_*.py`). A grading command scoped to its own directory does not collect them,
and `python3 -m unittest discover` from the repository root does not either (same test count before and after
setup, checked on one task). pytest's documented default skips directories whose names start with a dot; pytest
was not run here.

## What the prompt is, and where each part is documented

The prompt is `/bmad-build-auto`, then the ticket; the runner adds the common ending (`arms/TAIL.md`). Nothing else
is added.

- A small change. The documented entry point is the build skill, given the request as it is: "Already have a
  repository and a small change you want to make? ... run the installed `bmad-build` skill"; "A typical session is
  one goal: about 500 lines of code added or changed (not counting tests) in a small handful of files. If it fits,
  give it to `bmad-build`." Every task in this benchmark fits that size.
- A larger feature. Planning comes first: `bmad-spec` writes a specification, an epic-sized one is broken into
  stories, and each story is one build session. That path is several sessions by design and is not used here.
- Attended or unattended. The build skill exists twice. `bmad-build` is "with human checkpoints": its workflow says
  "ALWAYS halt at checkpoints and wait for human input", and any change it does not class as small and
  unambiguous stops for plan approval. `bmad-build-auto` is "the unattended worker for one session-sized unit",
  "for a caller or orchestrator", "without human interaction": the same clarify, plan, implement and review steps,
  ending in a terminal status (`done` or `blocked` with a reason). A `claude -p` session has nobody at a checkpoint,
  so the arm uses the skill the project documents for that case. With `bmad-build` a session that stopped for
  approval would end with no code written, and the result would show the missing human, not the method. To run the
  attended skill instead, change the first line of `prompt.md` to `/bmad-build`.
- The form `/<skill> <request>` is how the docs start a build in Claude Code (`/bmad-build Fix the login validation
  bug that allows empty passwords.`), and how the project's own orchestrator (bmad-loop) starts an unattended one:
  it opens a fresh coding-tool session and sends `/bmad-build-auto` followed by the story or spec to work on.
- The ticket is the "short free-form change request" that `bmad-build-auto` takes as its invocation prompt.

## What the harness has to provide

- The prompt must reach `claude -p` unchanged, starting with `/bmad-build-auto`: Claude Code runs a skill directly
  only when the prompt starts with its name. If the name does not match a loaded skill, the text goes to the model
  as an ordinary message. With `--output-format stream-json`, `bmad-build-auto` should appear in the `slash_commands`
  list of the first `system/init` event; that is the cheapest check that the skills loaded.
- The session needs the subagent tool and the shell. `bmad-build-auto` starts one implementation subagent and four
  review subagents and halts `blocked` with `no subagents` when it cannot. It runs `uv` and `git` through the shell.
- `uv` and Python 3.11 or later on the session's PATH, as in setup.
- A git identity that can commit. The skill requires a clean working tree at the start, which the harness's commit
  after setup gives it, and it commits its own work locally at the end.
- Changed lines are counted against the commit made after setup. BMAD's own records under `_bmad-output/` (one spec
  file per run, sometimes a patch file) are part of what the session writes: they count in `changed_lines`, as
  every arm's planning files do, and not in `changed_lines_py`.

## Known interactions with the common prompt ending

- `bmad-build-auto` is told by its own steps not to pick between "multiple defensible readings" of a request: it
  halts `blocked` with `intent gap`. The common ending tells every arm to decide and proceed. On the vague tasks
  these two instructions pull against each other, and which one the model follows is part of what is measured.
- The skill ends by writing its status into its record file. The `RESULT:` line is asked for by the common ending
  only; the skill does not know about it.

## Sources

Pinned tag:

- Repository at the tag: https://github.com/bmad-code-org/BMAD-METHOD/tree/v6.12.4
- Package: https://www.npmjs.com/package/bmad-method/v/6.12.4
- Prerequisites, line 18; install and "invoke `bmad-build` with what you want to change", lines 21-24:
  https://github.com/bmad-code-org/BMAD-METHOD/blob/v6.12.4/README.md
- Prerequisites, lines 16-28; "Headless CI installs" with `--yes --modules bmm --tools claude-code`, lines 100-111;
  what is installed where, lines 113-119:
  https://github.com/bmad-code-org/BMAD-METHOD/blob/v6.12.4/docs/start/install-bmad.md
- Small change in an existing repository, lines 9-12; the install command with `--directory .`, line 37;
  `/bmad-build <request>`, line 53:
  https://github.com/bmad-code-org/BMAD-METHOD/blob/v6.12.4/docs/start/build-your-first-change.md
- Sizing a session, lines 14-25; giving the request, lines 36-64; plan approval, lines 80-91; when to plan first,
  lines 149-170; the two build skills side by side, lines 176-177:
  https://github.com/bmad-code-org/BMAD-METHOD/blob/v6.12.4/docs/build/build-a-change.md
- The unattended worker, lines 8-16; prerequisites (subagents, clean tree), lines 28-35; inputs, lines 39-49;
  statuses and blocking conditions, lines 147-222; artifacts, lines 224-268; what a caller should do, lines 270-285:
  https://github.com/bmad-code-org/BMAD-METHOD/blob/v6.12.4/docs/build/autonomous-development-loops.md
- Larger work goes through `bmad-spec`, lines 31-41:
  https://github.com/bmad-code-org/BMAD-METHOD/blob/v6.12.4/docs/plan/choose-a-planning-path.md
- The attended skill's checkpoints: `workflow.md` line 80, `step-02-plan.md` lines 34-58:
  https://github.com/bmad-code-org/BMAD-METHOD/tree/v6.12.4/src/bmm-skills/ship/bmad-build
- The unattended skill: `SKILL.md` line 9 (the uv command), `workflow.md` lines 3 and 51-55 (no human, subagents
  mandatory), `step-01-clarify-and-route.md` line 74 (clean tree), `step-02-plan.md` line 14 (intent gap):
  https://github.com/bmad-code-org/BMAD-METHOD/tree/v6.12.4/src/bmm-skills/ship/bmad-build-auto
- Installer flags, lines 12-52: https://github.com/bmad-code-org/BMAD-METHOD/blob/v6.12.4/tools/installer/commands/install.js
- Default user name and the quick update on an existing install, lines 344-354 and 965-973:
  https://github.com/bmad-code-org/BMAD-METHOD/blob/v6.12.4/tools/installer/ui.js
- The render script needs Python 3.11 or later, line 3:
  https://github.com/bmad-code-org/BMAD-METHOD/blob/v6.12.4/src/scripts/render_skill.py

Other:

- The two release lines, README line 18 on `main` (commit `a867e1604b365d48ea03cbd109da1066ba0c84bc`, 2026-11-07):
  https://github.com/bmad-code-org/BMAD-METHOD/blob/main/README.md
- The docs site, which describes v7 on 2026-11-11: https://docs.bmad-method.org/start/build-your-first-change/
- bmad-loop, the project's orchestrator, composing `/bmad-build-auto <request>` (commit
  `795a55aec95f365ca09fba4f3c4f7ff2baa558d8`; `src/bmad_loop/engine.py` line 9834, `src/bmad_loop/stories_engine.py`
  line 343; `skills/README.md` line 21): https://github.com/bmad-code-org/bmad-loop
- Claude Code: skills named at the start of a `-p` prompt are run ("Include `/skill-name` in the prompt string and
  Claude Code expands it before running"): https://code.claude.com/docs/en/headless
- Claude Code: project skills load when the setting sources include `project`; an unmatched `/<name>` is sent to the
  model as ordinary text; `slash_commands` in the init event: https://code.claude.com/docs/en/agent-sdk/skills
- Claude Code: `--setting-sources`, `--strict-mcp-config`: https://code.claude.com/docs/en/cli-reference

## Verified by running (2026-11-11; Linux, Node 22.23.4, npm 10.9.9, uv 0.11.32, Python 3.13, git 2.43)

- `npx bmad-method@6.12.4 install --help` and `--list-tools`: the flags used exist; `claude-code` installs to
  `.claude/skills`.
- `setup.sh` in a scratch git repository holding a task's starting files, with an empty cache: exit 0 in 5 seconds,
  234 files in the commit that follows, clean `git status` after that commit.
- `setup.sh` a second time in the same repository: exit 0 in under a second, every file byte-identical (sha256 of
  all 243 files compared), `git status` still clean, the top level of the home directory unchanged.
- Each check in `setup.sh` can fail: `BENCH_CACHE` unset, `uv` absent from PATH, an installer that exits 1, and an
  installer that exits 0 without installing each end with exit 1 and a message, leaving the repository untouched.
- The entry skill's first step, run by hand in a copy:
  `uv run --no-cache _bmad/scripts/render_skill.py --project-root <repo> --skill <repo>/.claude/skills/bmad-build-auto`
  exits 0, prints the path of a rendered `workflow.md` under `_bmad/render/`, and leaves `git status` clean.
- Six simultaneous first runs of `npx bmad-method@6.12.4` against one empty npm cache all exit 0.
- `prompt.md`: starts with `/bmad-build-auto` and has one line that is exactly `{ticket}`. (It then also held the
  common ending, which is now `arms/TAIL.md`.)

## Not verified

- No Claude Code session was started. Not run: that `claude -p --setting-sources project` lists the 29 skills, that
  `/bmad-build-auto` followed by a newline and the ticket is expanded as a skill with the ticket as its argument,
  and that the workflow runs to a terminal status inside the benchmark's turn and budget caps. The first two rest
  on the Claude Code documentation above and on reading the installed CLI (2.1.322), which splits the skill name
  from its argument at the first whitespace of any kind. An older CLI may split only at a space; if the pilot shows
  the skill not starting, check `slash_commands` first.
- Subagents under the benchmark's permission mode. If the subagent tool is unavailable the skill halts `blocked`,
  and the arm then measures the harness, not the method.
- How the skill judges "a branch that fits the intent" on the `work` branch every session starts on.
- macOS, Windows, and a machine where uv has to download Python because none at 3.11 or later is installed.
- The installer's best-effort update check (`npm view bmad-method@latest version`, five-second limit) on a machine
  with no network; a warm cache was not tested offline.
