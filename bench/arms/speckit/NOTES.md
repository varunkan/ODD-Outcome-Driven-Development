# speckit

GitHub Spec Kit in one headless session, through the process Spec Kit documents for the request: Spec-Driven
Development (SDD) to build something, its bundled bug extension to repair broken behaviour.

## Version pinned

`specify-cli==1.4.0` from PyPI, which is release tag `v1.4.0`, commit `0019fa14d12f45edabc2cc3176c9168a68bd0f97`,
the latest release on 2026-11-11. The version is the `VERSION` line in `setup.sh`. PyPI lists the wheel's sha256 as
`68c691596167171ea047d88e07baf57cd2815129308c9a10792da9f9a02b95f5`; `setup.sh` pins the version, not the hash. The
CLI's own dependencies are not pinned; the files it writes into the repository come only from assets bundled in the
package, the bug extension (version 1.0.2, `core_pack/extensions/bug/extension.yml:6` in the wheel) included. `VERSION`
states the same in one line.

## What `setup.sh` does

1. Installs the CLI once into `$BENCH_CACHE/speckit-1.4.0/` (`uv tool install specify-cli==1.4.0` with uv's tool,
   bin and cache directories pointed there; without uv, a venv and `pip install specify-cli==1.4.0`). A file lock
   keeps simultaneous first runs from installing twice. Later runs need no network.
2. Runs the documented scripted init for an existing repository:
   `specify init --here --force --non-interactive --integration claude --script sh --ignore-agent-tools`.
   `--script sh` is already the default off Windows and is stated so the result does not depend on the machine;
   `--ignore-agent-tools` skips the check that `claude` is on PATH. Standard input is `/dev/null`.
3. Runs `specify extension add bug --force`, the documented install of the bug extension ("no network required",
   `extensions/bug/README.md:41-42`); `--force` because a plain add exits 1 once the extension is registered, even
   with one of its skills deleted.
4. Checks that the nine skills the prompt names, the scripts and the templates exist, and fails otherwise. A second
   run in the same repository finds them and changes nothing.

The init adds 29 files and modifies none: `.claude/skills/speckit-{analyze,checklist,clarify,constitution,converge,
implement,plan,specify,tasks}/SKILL.md` and `.specify/` (bash scripts, templates, an unfilled constitution, manifests,
the bundled workflow definition). The extension adds `.claude/skills/speckit-bug-{assess,fix,test}/SKILL.md`,
`.specify/extensions.yml` (no hooks) and `.specify/extensions/` (its manifest, README, command sources, registry).
No `CLAUDE.md`, no `.claude/settings.json`, no hooks, no MCP server, no git branch,
nothing under the home directory. The skills call only `.specify/scripts/bash/*.sh`, which need bash; `jq` and
`python3` are used when present. The `specify` CLI is not needed during a session.

## What the prompt is, and where each part is documented

- Two processes, and the agent picks: the README's "Choose your process" table (README.md:25-36) sends "Build a
  feature or application" to SDD and "Diagnose and repair broken behavior" to bug fixing, and calls them "independent
  entry points, not mandatory phases"; the existing-project guide says a repair can follow the bug-fixing quickstart
  instead, and "Neither process requires completing the SDD steps below first" (existing-projects.md:36-40). The
  prompt quotes those two descriptions and never says which kind a ticket is, so the choice is the agent's, as it is
  a user's.
- SDD: the six steps and their order are the README's "minimal flow" (README.md:100-121) and the quickstart's
  "shorter path, for smaller features" (quickstart.md:29-38): constitution, specify, plan, tasks, implement, converge,
  "one at a time", and "Repeat implement and converge until convergence reports `Converged`".
- Bug fixing: assess, fix, test with one slug (README.md:130-154; guides/bugfix.md:31-66). No slug is given: in
  automated mode the assess skill generates one (reference/agentic-bugfix.md:19). "If its verdict is failed, revisit
  the diagnosis or fix using that evidence, then test again" is the guide's row for `failed` (guides/bugfix.md:72).
- Step 1's wording, "principles that are already true for the repository", is what the existing-project guide tells
  a user to give `/speckit-constitution` (existing-projects.md:46-47), so it stays.
- Removed: step 3's "reusing the existing architecture, dependencies, and test conventions". The guide does not tell
  a user to write it; it tells the user to check the plan's output ("verify that the proposed design reuses the
  existing architecture, dependencies, and test conventions", existing-projects.md:85-86). Written into the prompt it
  was a hint no other arm gets. `/speckit-plan` now takes no argument.
- The ticket is the feature description `/speckit-specify` takes, or the report `/speckit-bug-assess` takes.
- "Invoke these skills yourself": in `claude -p` only a skill named at the very start of the prompt is run directly,
  so one session cannot be given several slash commands. Spec Kit installs its Claude Code skills as
  model-invocable, and the prompt asks the agent to invoke them in the documented order.
- Left out, as the documentation allows: `/speckit-clarify`, `/speckit-checklist`, `/speckit-analyze` ("quality gates
  you add for anything with meaningful ambiguity"; clarify works by asking the user questions); the bundled
  `bugfix` workflow, which adds a human review gate between assess and fix and runs one CLI process per step.
- The common ending (nobody answers; judged on the files; the `RESULT:` line) is `arms/TAIL.md`, added by `run.py`.

## Sources

- Repository at the pinned tag: https://github.com/github/spec-kit/tree/v1.4.0
- Release (tag, commit, "Latest"): https://github.com/github/spec-kit/releases/tag/v1.4.0
- Package: https://pypi.org/project/specify-cli/1.4.0/
- "Choose your process", lines 25-36; minimal flow, lines 100-121; bug fixing, lines 130-154:
  https://github.com/github/spec-kit/blob/v1.4.0/README.md
- Bug-fixing quickstart, lines 3-5, 17-21, 31-72: https://github.com/github/spec-kit/blob/v1.4.0/docs/guides/bugfix.md
- Bug commands, slug in automated mode, line 19:
  https://github.com/github/spec-kit/blob/v1.4.0/docs/reference/agentic-bugfix.md
- Pinned install from PyPI, line 57; non-interactive default integration, line 71; "CI and AI Agent Harnesses",
  lines 108-127: https://github.com/github/spec-kit/blob/v1.4.0/docs/installation.md
  (published at https://github.github.io/spec-kit/installation.html)
- Existing repository: init, line 16; a repair may skip SDD, lines 36-40; constitution, lines 46-47; plan,
  lines 85-86; converge, line 90:
  https://github.com/github/spec-kit/blob/v1.4.0/docs/how-to/existing-projects.md
- Constitution and shorter path, lines 29-38: https://github.com/github/spec-kit/blob/v1.4.0/docs/quickstart.md
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
- Bug extension (2026-11-11, same machine): `setup.sh` on an empty cache in a fresh repository made from
  `tasks/t09-pagination-off-by-one/repo`: exit 0 in 6 s, 39 files (the 29 above and 10 from the extension), branch
  `main` only, visible tests pass. Second run after committing: exit 0, "nothing to do", tree unchanged. Another fresh
  repository with the warm cache and no network (`unshare -n`): exit 0, the same files, differing only in timestamps
  (the three JSON files above and `.specify/extensions/.registry`). A deleted bug skill is re-created offline.
- After a core skill is deleted, the re-run's `specify init --force` re-renders the bug skills with two extra
  front-matter keys (`user-invocable: true`, `disable-model-invocation: false`) and a heading; a normal first run
  leaves them without those keys, which in Claude Code means model-invocable as well.
- `prompt.md`: one line is exactly `{ticket}`, no other braces; none of `TAIL.md`'s lines
  (`tests/test_arm_speckit.py`).

## Not verified

- No Claude session was started. Unproven until the pilot: that `claude -p --setting-sources project` lists the
  twelve skills, that the agent picks a process and runs its steps in order rather than doing the work directly, and
  that the helper scripts run
  under the benchmark's permission mode (the session must be allowed the Skill and Bash tools).
- macOS, and a machine whose `python3` is older than 3.11, which the CLI requires.

## To state with the results

- Two processes, chosen by the agent from the request: Spec-Driven Development (`/speckit-constitution`,
  `/speckit-specify`, `/speckit-plan`, `/speckit-tasks`, `/speckit-implement`, `/speckit-converge`) to build
  something, the bundled bug extension (`/speckit-bug-assess`, `/speckit-bug-fix`, `/speckit-bug-test`) to repair
  broken behaviour, as the README's "Choose your process" table divides them. The prompt never says which kind a
  ticket is; which process each run used is in its transcript, and a run may pick the other one.
- Planning documents count in `changed_lines` but not in `changed_lines_py`: `specs/<feature>/` and a filled
  `.specify/memory/constitution.md` (SDD), or `.specify/bugs/<slug>/` (bug fixing).
- `/speckit-specify`, `/speckit-implement` and `/speckit-bug-assess` stop to ask the user in some cases; the common
  ending ("nobody is available") is what tells the agent to decide instead.
- Left out: the optional quality gates (`/speckit-clarify`, `/speckit-checklist`, `/speckit-analyze`) and Spec Kit's
  workflow runner (one `claude -p` process per step, with a human review gate in its `bugfix` workflow). The
  benchmark measures one session with nobody to answer.
