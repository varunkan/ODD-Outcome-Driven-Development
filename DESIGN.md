# ODD design

Version 2, 2026-11-11. This replaces the first design after a four-lens review (tamper resistance, the correctness
of the check, day-to-day friction, portability) returned 23 required changes. The review and its ruling are in
[`docs/evidence/10-design-review.md`](docs/evidence/10-design-review.md).

## 1. What it is

One command-line tool, `odd`, in one file, and a half-page method that a coding agent follows.

**"Done" is recomputed from the code, not claimed by the agent.** An outcome is verified when its proof passes on the
tree as it is, fails on the same tree with the change taken out, and passes again once the change is put back. For
proofs that run from the repository, anyone, including CI, can recompute that.

Install: `pipx install odd-tool` (or download `odd.py`), then run `odd init` in a git repository. It needs a POSIX shell, git 2.23 or newer
and Python 3.8 or newer.

## 2. The unit of work: an outcome file

`.odd/outcomes/<slug>.md`, committed with the work:

```
---
outcome: A cashier who splits a bill three ways sees three totals that add up to the bill.
proof: pytest tests/test_split.py -q
in: src/billing/**
---
Free notes: questions asked and answered, decisions and why.
```

- `outcome`: one sentence, who observes what.
- `proof`: a command that exits 0 only when the outcome holds. It is the narrowest command that shows the outcome,
  never the whole suite. It asserts results or counts, not wall-clock time.
- `in`: globs of the product files this outcome may change (its boundary).
- Paths, globs and the proof are relative to the repository root.
- Optional lines: `counterfactual: skip - <reason>`, `parked: <reason>`, `escaped: ...` (written by `odd escaped`,
  section 9), `sealed: ...` (written by `odd seal`, section 4).

There is no status field. "Done" is never written to a committed file. A requirement becomes one or more outcome
files; their sentences and proofs are the specification, and each file is a task.

## 3. Commands

| command | what it does | exit |
|---|---|---|
| `odd init [--claude-hooks] [--mcp]` | installs or repairs: `.odd/odd.py`, `.odd/config.json`, the method in `AGENTS.md`, the import line in an existing Claude instruction file; prints the CI step, the conditions under which CI is the authority, and a proof suggestion (section 3a); `--mcp` also installs the MCP server (section 7) | 0 |
| `odd new <slug> "<outcome>" --proof CMD --in "GLOB, GLOB"` (comma-separated; `--in` may repeat) | writes the outcome file; `--proof auto [--test PATH]` picks the command (section 3a) | 0, 1 refused (also: `auto` and no runner detected) |
| `odd seal <slug> [--base REF]` | optional: requires the proof to fail now, then fingerprints it in the outcome file (section 4) | 0 sealed, 1 already passes or no test file changed, 2 could not run |
| `odd done <slug> [--base REF]` | verifies the outcome (section 4) and records it locally | 0 verified, 1 not shown, 2 could not run |
| `odd gate [--base REF] [--recompute] [--summary FILE] [--json FILE]` | checks the whole change (section 5); optionally also writes the result as Markdown or JSON | 0 pass, 1 fail, 2 could not run |
| `odd park <slug> "<reason>"` | the honest exit, for blocked work and for work that cannot be done as specified | 0 |
| `odd escaped <slug> "<what, where found>"` | records a defect that got past this outcome (section 9) | 0, 1 vague report or no such outcome |
| `odd stats` | counts, labelled self-reported, with escaped defects split by kind of proof | 0 |

`odd hook stop|session-start` is an internal entry point called only by the opt-in Claude Code hooks.

### 3a. Proof suggestions

`odd new ... --proof auto` picks a narrow proof from the test runner the repository already uses, prints every
runner it detected and the command it chose, and writes that command into the outcome file like any other. Nothing
detected is a refusal (exit 1) that says to give `--proof "<command>"`; it never guesses silently. `odd init` prints
the same suggestion with `<slug>` in place of a name. Detection, most specific first (the first one found is used):

| runner | shown by | proof (default test path) |
|---|---|---|
| pytest | `pytest.ini`, `[tool.pytest` in `pyproject.toml`, `[pytest]` in `tox.ini`, `[tool:pytest]` in `setup.cfg`, a `conftest.py` at any depth, `pytest` in a root `requirements*.txt` | `python3 -m pytest -q tests/test_<name>.py` |
| jest, vitest, node, mocha | the word (`node --test`) in `package.json`'s `scripts.test` | `npx jest` / `npx vitest run` / `node --test` / `npx mocha test/<slug>.test.js` |
| go | `go.mod` | `go test .` (`<name>_test.go`; `go test ./<dir>` for a test path in a directory) |
| cargo | `Cargo.toml` | `cargo test --test <name>` (`tests/<name>.rs`) |
| unittest | any `*.py` file outside `.odd/` | `python3 -m unittest -q tests/test_<name>.py` |
| make | a `test:` target in the Makefile | `make test`, flagged as running the whole target |

`<name>` is the slug with `-` and `.` turned into `_`. `--test PATH` names the test file instead (quoted for the
shell) and goes with `--proof auto` only. Limits: detection reads file names and a few settings, not how the
project really runs its tests (a virtualenv, `npm test` flags, a workspace, a Go package that is not the root); the
command is a starting point for a person or agent to read, and `make test` is not narrow. A proof literally `auto`
can no longer be written with `--proof` (edit the file). A proof that exits 5 or prints that it ran no tests gets the
hint that the runner may be wrong; unittest is still picked for a repository whose only sign is a `.py` file.

## 4. Verification (`odd done`, and `odd gate --recompute`)

**The base** is one revision for everything: where this branch left the target branch (the merge-base of HEAD and
`--base REF`, or of HEAD and the default branch). If it cannot be found, the result is "could not run" with the
command that fetches it.

**The changed set** is `git diff --name-only -z --no-renames <base>` plus untracked, non-ignored files. A rename is a
delete and an add. It is computed from git, so files written through a shell are seen like any other.

**Test files** are the files matching `test_globs` in the settings (`tests/**`, `**/test_*.py`, `**/*_test.*`,
`**/*.test.*` and the like). They are never taken out, need no outcome, and do not count toward the small-change lane.

**The check is green, red, green:**

1. The proof passes on the tree as it is.
2. The product files this outcome changed are taken out: added files are removed, deleted files recreated, modified
   files put back to their base version. The proof must now fail by running to completion and exiting non-zero.
3. The change is put back and the proof passes again.

This shows the proof depends on the change. For new code it shows only that the proof reaches it. It costs three
proof runs per outcome, plus one per mutant of the strength check below.

Rules of the in-place check:

- A journal of byte copies (type and mode kept, links as links) is written under the git directory before the first
  file changes. Nothing of it is visible in the working tree.
- Git writes the base versions to the working tree only; the index is never touched.
- The change is put back in a `finally`, on SIGINT, SIGTERM and SIGHUP, and by any later `odd` command that finds
  the journal of a dead run (that command then stops with exit 2 so the tree can be looked at).
- A path is put back only if it still holds exactly what the check left there. If it was edited meanwhile, the edit
  stays and the earlier version is kept beside the journal; both are named.
- One check at a time per working tree.
- Any error while taking the change out: put it back and exit 2. The proof never runs on a half-reverted tree.
- Every file the check writes gets a newer modification time, so caches keyed on it notice.
- With the change taken out, a timeout, exit 126 or 127, or death by signal is "could not run", not a failure.
- If nothing inside `in` changed, the check stops with exit 1 before a second run.
- If the proof runs a file that would be taken out, the check stops and says to keep it under a test path.

**Proof strength: small breaks in the changed lines.** After green, red, green, the check makes small deliberate
breaks ("mutants") in the changed lines of the outcome's product files, one at a time, and runs the proof against
each. A mutant the proof still passes ("survivor") is a changed line the proof does not depend on: a weak proof, or
a line no test reaches, without any language's coverage tool.

- The breaks are textual and the same in every language: `<` `<=` `>` `>=` `==` `!=` swapped, `and`/`or`,
  `&&`/`||`, `+`/`-`, `true`/`false` in their usual spellings, an integer literal plus one. Strings and comments
  (quotes, triple quotes, `/* */`, `#`, `//`, a leading `--`) are blanked first; the detection is approximate and
  errs towards fewer mutants.
- At most `mutants` (default 8) per outcome, spread evenly over the candidates in a fixed order, so two runs on the
  same tree make the same breaks. Each costs one proof run.
- Each mutant goes in and comes out through the same journal as the take-out: a kill puts it back, an edit made
  meanwhile stays.
- A mutant whose run times out, exits 126 or 127, or dies by a signal is neither caught nor survived; it is listed.
  Under `"enforce"` any such mutant is a failure: the proof controls its own exit code, so a run that did not
  complete is never evidence of strength.
- Under `"report"` sampling stops once the breaks have taken about as long as the three core runs (at least 2 s),
  and says so; the estimate is printed before the first break. `"enforce"` always runs all `mutants`. A survivor
  line ends with a `next:` step.
- The setting `strength`: `"report"` (default) prints the score and each survivor (file:line, the swap, the line) in
  `odd done` and the gate; `"enforce"` makes a survivor a failure; `"off"` makes no mutant. `--recompute` measures
  it again with the settings of the target branch.

**Sealed proofs (optional).** `odd seal <slug>` runs the proof on the tree as it is and requires it to fail (run
to completion, non-zero); a proof that passes is refused with exit 1, one that cannot run is exit 2. It then writes
`sealed: proof@<hash>, <test file>@<hash>, ...` into the outcome file: a 12-hex sha256 of the proof command and of
each test file changed since the base (content, mode, a link as a link). It refuses when no test file has changed.
`odd done`, the local gate and `--recompute` then fail while the proof command or a sealed file differs, naming
them: "the sealed proof changed after it was sealed: <files>; reseal it or restore it". Resealing is `odd seal`
again; it needs the proof red again (take the product change out first) and it changes the outcome file, so it is
visible in review. Limits: the seal is written by the party being checked, so it proves nothing about what the test
was before `seal` ran, and a reseal is allowed; it covers only the files named, not helpers or fixtures added after;
a malformed `sealed:` line fails. Outcomes without it behave exactly as before. Seal runs no in-place edit, so it
needs no journal. `odd seal` also records a seal event (fingerprint, base, what the red proof said) in local
evidence; `odd stats` counts an outcome as sealed only when that event matches its `sealed:` line, and shows
`unseen` otherwise (a hand-written line, or a seal made on another machine). CI cannot check that the seal came
first; what it does check, with the sealed test files in place, is the take-out: the proof fails over the base.

**A skip is an exemption with a reason, not a verification.** `counterfactual: skip - <reason>` is for a change
where nothing can fail first: a pure refactor, a dependency bump, a removal, a submodule pointer. The proof must
still pass. Every skip is named in the gate's result with its reason and its changed-line count.

## 5. The gate, and who is trusted

An outcome is **in play** when its file was added or changed since the base. `odd gate` passes when every changed
product file is inside the boundary of exactly one verified in-play outcome, or falls under a printed exemption.

- A changed product file may match the `in` of only one in-play outcome. Otherwise the gate fails and names both:
  such outcomes become one outcome, or two successive changes.
- A parked outcome covers no files. Its changes are removed, moved to another outcome, or fit the small-change lane.
- **Locally**, the gate runs no proof. An outcome counts as verified when `odd done` passed on exactly the current
  content (a hash of the proof, the boundary and the files inside it, kept under the git directory). A commit or an
  edit elsewhere changes nothing. This is fast feedback, and an agent with a shell could forge it.
- **With `--recompute`**, nothing recorded is trusted. Every in-play outcome that is not parked is verified again,
  and the settings are read from the base revision, so a change cannot loosen its own gate.
- "Could not run" is never reported as a pass.

The gate report is written for the person who reviews the change. Per outcome: the files and lines taken out, the
last line the proof printed when it failed, the seconds. Per change: the lines that passed under each exemption (the
small-change lane, exempt paths, each skip with its reason), test files that existed at the base and were modified or
deleted, and control files changed.

**CI is the authority only when** (1) the gate is a required check on the target branch, (2) the tool, its settings
and the CI configuration cannot change without a person's review, and (3) the agent cannot merge or push to the
target branch. Without all three the gate is advisory. On GitHub Actions the step is `uses: varunkan/ODD-Outcome-Driven-Development@<tag>` (`action.yml`): it unshallows the checkout, fetches the target branch and runs the action's own copy of the tool, pinned by the workflow. Elsewhere the CI step runs the copy of the tool from the target branch:

```
git show "refs/remotes/origin/$TARGET:.odd/odd.py" > "$TMP/odd.py" 2>/dev/null || cp .odd/odd.py "$TMP/odd.py"
python3 "$TMP/odd.py" gate --recompute --base "refs/remotes/origin/$TARGET"
```

**The review comment.** `odd gate --summary FILE` writes the same result as Markdown for the person who reviews
the change, and `--json FILE` as data: the verdict first, then per outcome its sentence, its proof, what the proof
printed with the change taken out (the last line naming a reason, such as an error or an assertion, then its last line), the strength score and each survivor, then every exemption, the control
files changed and why it did not pass. A result of "could not run" is written too, never left blank. The Action
appends it to the job's step summary always and, on `pull_request` events (input `comment`: `auto`, `true`,
`false`), creates or updates one pull-request comment: the comment by the input `author` (default
`github-actions[bot]`) whose body starts with the hidden line `<!-- odd-gate -->`, searched over every page; a
marker in anyone else's comment is ignored. Text from the change (outcome, proof, output, reasons, paths) is
escaped: entities for `& < >`, a backslash before Markdown punctuation, a code fence longer than any backtick run.
The gate runs in one step with no token; the token is given only to a second step (`if: always()`) that posts the
comment from the summary file. Limit: a proof runs as the same user, so a process it leaves behind could still
rewrite that file before the comment step reads it; it never sees the token in its environment. That needs
`permissions: pull-requests: write`; a refused or failed comment is logged and never changes the exit code. A pull
request from a fork gets a read-only token, so it gets the step summary and no comment. At most 50 pages of
comments are searched; the comment is cut at 60,000 characters. Whether the comment saves review time is not
measured; the protocol is [`docs/review-time.md`](docs/review-time.md).

It needs full history (not a depth-1 checkout) and the toolchain the proofs use, so it belongs at the end of the
project's existing test job. On GitHub, do not move it to `pull_request_target`. Without CI, fetch the target
branch and run `odd gate --recompute --base <target branch>` on the committed work before merging. A ref name that
could mean a tag, a local branch and a remote branch at once is refused rather than guessed.

## 6. Exemptions

- **The small-change lane.** Product lines changed outside any outcome pass while they total at most `trivial_lines`
  (default 25). It is a per-change budget read from the base settings. Small is not the same as low-risk, and a run
  of small changes passes. A binary file or a submodule pointer changed outside an outcome is over the limit.
- **Exempt paths** (default: `.odd/outcomes/**`, `**/*.md`, licence and ignore files, lockfiles).
- **Control files** (`.odd/odd.py`, `.odd/config.json`) need no outcome and are always reported when changed.
- **Test files** and **skips**, as above.

Exemptions are not verification. Each is printed with its line count.

## 7. How it reaches each tool

`odd init` writes the method, about twenty lines, into the root `AGENTS.md` between markers (at the top on first
insertion). That is the only rendered copy. If a Claude instruction file exists (`CLAUDE.md` or `.claude/CLAUDE.md`),
it gets one `@AGENTS.md` import line.

| reads a root `AGENTS.md` without configuration | needs one line of configuration |
|---|---|
| Codex, Cursor, GitHub Copilot in VS Code (and its cloud agent and CLI), Claude Code (directly, or through the import), Junie, Windsurf/Devin | Gemini CLI, Aider, Copilot Chat outside VS Code |

The tool and the gate are the same for every agent and for a person.

Opt-in, per developer, never committed: `odd init --claude-hooks` adds two Claude Code hooks to
`.claude/settings.local.json`. At session start one line of status. At turn end, a block only when this turn changed
files and either a locally verified outcome has gone stale or more than the lane changed with no outcome in play.
The hook commands cannot exit non-zero.

**As MCP tools.** `odd init --mcp` copies `odd_mcp.py` (shipped beside `odd.py`, standard library only) into
`.odd/` and adds `"odd": {"command": "python3", "args": [".odd/odd_mcp.py"]}` under `mcpServers` in the project's
`.mcp.json`, keeping every other server and key; a `.mcp.json` it cannot read, or whose `mcpServers` is not an
object, stops `init` with exit 2 before anything is written. `.odd/odd_mcp.py` is a control file. The server speaks
JSON-RPC 2.0 over stdio and exposes `new`, `seal`, `done`, `gate`, `park` and `escaped`; each call runs `odd.py`
from beside it as a subprocess in the server's working directory and returns its exit code (in
`structuredContent.exit_code`, and `isError` when not 0) and everything it printed, so no logic is repeated.
Arguments of the wrong name or kind are refused (-32602) before odd runs. It is dual-era: it serves the stateless
MCP revision `2026-07-28` (`server/discover`, the version in each request's `_meta`) and the `initialize` handshake
of `2025-11-25` and earlier, echoing a requested legacy version it knows. Limits: the relative path in `.mcp.json`
assumes the client starts the server at the repository root (not checked against Claude Code); only a pipe
round trip in the tests has driven it, not Claude Code or another client; a call runs as long as odd does
(`proof_timeout` bounds each proof); the protocol's newer optional parts (subscriptions, tasks, input requests) are
not implemented. `pip install odd-tool` also installs an `odd-mcp` command.

## 8. Measurement

`odd stats` counts outcome files (total, skipped, parked, escaped) and local verification attempts, and splits
recorded escaped defects by kind of proof (section 9). It is self-reported and is never published as a result.

Published figures come only from the comparison harness in `bench/`: hidden acceptance tests, the harness's clock and
the token counts the agent CLI reports. It reports "gate passed, hidden tests failed" as its own figure: that is the
size of what this design does not catch.

## 9. Learning

A defect that escaped is recorded on the outcome it got past: `odd escaped <slug> "<what went wrong, where it was
found>"` appends `YYYY-MM-DD: <text>` (UTC date, whitespace collapsed) to that outcome's `escaped:` line, entries
joined by `; `, so the field stays one line. Then it becomes a new outcome whose proof fails on the escaped behaviour.
Changing only the `escaped:` line of a merged outcome does not put it back in play; any other edit to the file does.

`odd stats` prints, per outcome, the escape count, whether it is sealed, and the strength (caught/mutants) of the
latest passing verification recorded on this machine; then, in total, escapes against outcomes split three ways:
sealed or not, take-out skipped or checked, and every mutant caught, a mutant survived, or not measured here. Each
split reads `N in K of M`: N escapes in K of the M outcomes of that kind. There is no lessons database.

Limits: only recorded escapes are counted, so the figures are self-reported. Strength comes from local evidence, so
on another machine, or for an outcome verified before strength existed, it is "not measured here". Seal and skip are
read from the outcome file as it is now, not as it was when the defect escaped. An entry is counted by its
`YYYY-MM-DD: ` prefix after `; `; a free-text `escaped:` value written by hand counts as one, and text that itself
contains `; 2026-01-02: ` is counted twice. Before `odd escaped` existed this document suggested `escaped: <slug>` on the *new* outcome; such a
line still loads, and is now counted as one escape against the outcome that carries it.

## 10. Limits

- CI is the authority only under the three conditions in section 5. Nothing inside a repository can protect its own
  CI configuration. The change that adopts the tool is judged by its own copy and default settings; a person reviews it.
- The check shows that the proof depends on the change, not that it checks the outcome. A proof that only imports a
  new symbol fails on the tree without it. The strength check narrows this only for the few textual breaks it makes,
  on at most `mutants` of them: a survivor is a real gap, but no survivor does not prove the proof complete, a
  change with no operator or number in it gets no mutant, and a break that makes the code invalid (a generic
  `List<int>` read as a comparison) is "caught" by any proof. Each run moves the files' modification times a few
  seconds further into the future. A flaky test counts as a failure. The last line of the failing run is
  printed for a person to read.
- The proof is written by the party being checked, so it can tell the reverted tree from the real one (git state,
  file hashes). This is not closed. The proof text is in the diff.
- Coverage is by path. An outcome with `in: **` puts every changed file inside its boundary. The gate shows lines per
  outcome; it does not prevent this.
- State outside tracked files (installed dependencies, build outputs, caches, databases) is not reverted. A
  dependency-only change, a generated file or a runner that selects tests from git state needs a skip.
- The proof's test must live in a file of its own under a test path. Tests in the same file as the product (Rust
  `#[cfg(test)]`, doctests) cannot be verified and need a skip.
- For the length of the failing run the tree holds base content, so a dev server, hot reload or file sync sees it.
- A proof that needs a real device, account or secret cannot be recomputed in CI. The tool has no "proven on the real
  system" label.
- Within one change a file belongs to one outcome.
- Changes are measured against the target branch. Work committed directly on it is not seen. A shallow clone is
  "could not run". Editing a merged outcome file puts it back in play.
- Windows, Git LFS and `autocrlf` are untested. A submodule change needs a skip.
- Only Claude Code has been run with it. The other tools' paths rest on their documentation.
- Every effectiveness figure is unmeasured until the comparison runs.
