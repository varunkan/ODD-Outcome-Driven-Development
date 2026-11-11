# speckit

GitHub Spec Kit, driven through its Spec-Driven Development (SDD) process in one headless session.

## Version pinned

`specify-cli==1.4.0` from PyPI, which is release tag `v1.4.0`, commit `0019fa14d12f45edabc2cc3176c9168a68bd0f97`,
the latest release on 2026-11-11. The version is the `VERSION` line in `setup.sh`. PyPI lists the wheel's sha256 as
`68c691596167171ea047d88e07baf57cd2815129308c9a10792da9f9a02b95f5`; `setup.sh` pins the version, not the hash. The
CLI's own dependencies are not pinned; the files it writes into the repository come only from assets bundled in the
package.

## What `setup.sh` does

1. Installs the CLI once into `$BENCH_CACHE/speckit-1.4.0/` (`uv tool install specify-cli==1.4.0` with uv's tool,
   bin and cache directories pointed there; without uv, a venv and `pip install specify-cli==1.4.0`). A file lock
   keeps simultaneous first runs from installing twice. Later runs need no network.
2. Runs the documented scripted init for an existing repository:
   `specify init --here --force --non-interactive --integration claude --script sh --ignore-agent-tools`.
   `--script sh` is already the default off Windows and is stated so the result does not depend on the machine;
   `--ignore-agent-tools` skips the check that `claude` is on PATH. Standard input is `/dev/null`.
3. Checks that the six skills the prompt names, the scripts and the templates exist, and fails otherwise. A second
   run in the same repository finds them and changes nothing.

It adds 29 files and modifies none: `.claude/skills/speckit-{analyze,checklist,clarify,constitution,converge,
implement,plan,specify,tasks}/SKILL.md` and `.specify/` (bash scripts, templates, an unfilled constitution, manifests,
the bundled workflow definition). No `CLAUDE.md`, no `.claude/settings.json`, no hooks, no MCP server, no git branch,
nothing under the home directory. The skills call only `.specify/scripts/bash/*.sh`, which need bash; `jq` and
`python3` are used when present. The `specify` CLI is not needed during a session.

## What the prompt is, and where each part is documented

- The six steps and their order are the README's "minimal flow" and the quickstart's "shorter path, for smaller
  features": constitution, specify, plan, tasks, implement, converge, "one at a time", and "repeat implement and
  converge until convergence reports Converged".
- Step 1's wording ("principles that are already true for the repository") and step 3's ("reuses the existing
  architecture, dependencies, and test conventions") are from the guide for adopting Spec Kit in an existing project.
- The ticket is the feature description that `/speckit-specify` takes.
- "Invoke these skills yourself": in `claude -p` only a skill named at the very start of the prompt is run directly,
  so one session cannot be given six slash commands. Spec Kit installs its Claude Code skills as model-invocable, and
  the prompt asks the agent to invoke them in the documented order.
- Left out, as the documentation allows: `/speckit-clarify`, `/speckit-checklist`, `/speckit-analyze` ("quality gates
  you add for anything with meaningful ambiguity"; clarify works by asking the user questions).

## Sources

- Repository at the pinned tag: https://github.com/github/spec-kit/tree/v1.4.0
- Release (tag, commit, "Latest"): https://github.com/github/spec-kit/releases/tag/v1.4.0
- Package: https://pypi.org/project/specify-cli/1.4.0/
- Minimal flow, lines 100-121; bug fixing as a separate bundled extension, lines 127-157:
  https://github.com/github/spec-kit/blob/v1.4.0/README.md
- Pinned install from PyPI, line 57; non-interactive default integration, line 71; "CI and AI Agent Harnesses",
  lines 108-127: https://github.com/github/spec-kit/blob/v1.4.0/docs/installation.md
  (published at https://github.github.io/spec-kit/installation.html)
- Existing repository: init, line 16; constitution, line 46; plan, line 85; converge, line 90:
  https://github.com/github/spec-kit/blob/v1.4.0/docs/how-to/existing-projects.md
- Shorter path, lines 32-38: https://github.com/github/spec-kit/blob/v1.4.0/docs/quickstart.md
- Which steps are required and which are optional gates, line 5:
  https://github.com/github/spec-kit/blob/v1.4.0/docs/reference/agentic-sdd.md
- Claude Code: integration key, where skills are installed, model-invocable by default, lines 3-30:
  https://github.com/github/spec-kit/blob/v1.4.0/docs/integrations/claude.md
- Invocation spelling per agent, lines 16-33: https://github.com/github/spec-kit/blob/v1.4.0/docs/integrations/cli.md
- Claude Code: project skills load from `.claude/skills/` with the `project` setting source; how `claude -p` treats
  a skill name: https://code.claude.com/docs/en/skills

## Verified by running (2026-11-11, Linux, uv 0.11.32, Python 3.13)

- `setup.sh` in a fresh git repository made from `tasks/t01-interval-overlap/repo`, empty cache: exit 0 in 4 to
  20 s over two trials, the 29 files above, no starting file changed, the task's visible tests still pass.
- Second run in the same repository after committing: exit 0, `git status` clean, tree hash unchanged.
- A second fresh repository with the warm cache and the network blocked: exit 0, same files; contents differ from
  the first repository only in `installed_at` / `updated_at` timestamps in three `.specify` JSON files.
- Two runs started together on an empty cache: both exit 0. The lock was shown to block a second holder.
- uv hidden from PATH: the venv and pip route gives the same result.
- Failure cases: no `BENCH_CACHE` and a failing `specify init` both exit 1; a deleted skill directory is re-created
  on the next run.
- `specify init` with an empty home directory writes nothing there.
- The PyPI package's command templates, file templates, bash scripts and Python sources are identical to the
  `v1.4.0` tag checkout.
- `prompt.md`: one line is exactly `{ticket}`, no other braces, last four lines identical to the plain arm's.

## Not verified

- No Claude session was started. Unproven until the pilot: that `claude -p --setting-sources project` lists the nine
  skills, that the agent runs all six in order rather than doing the work directly, and that the helper scripts run
  under the benchmark's permission mode (the session must be allowed the Skill and Bash tools).
- macOS, and a machine whose `python3` is older than 3.11, which the CLI requires.

## To state with the results

- Spec Kit documents a separate, lighter process for defects (`specify extension add bug`, then `/speckit-bug-assess`,
  `/speckit-bug-fix`, `/speckit-bug-test`). This arm uses SDD for every task kind, bugfix included. The extension is
  bundled and installs without network; using it would need a prompt that chooses a process per ticket.
- The session writes `specs/<feature>/` (spec, plan, tasks and more) and fills `.specify/memory/constitution.md`.
  These are in the tree the session leaves, so they count in "changed lines" unless the report excludes them.
- `/speckit-specify` and `/speckit-implement` are written to stop and ask the user in some cases; the common closing
  sentence is what tells the agent to decide instead.
- Spec Kit also ships a workflow runner that starts one `claude -p` process per step. It is not used: the benchmark
  measures a single session.
