# Ruling 6: does a reader made by `odd reread` behave like the second reading of the replay?

*Ruled 2026-11-20, before any run. Read-only: nothing changed, no model ran, $0 spent. Read: evidence 24 to 26, ruling 5, crosstest.json, DESIGN 3r and 3t, cmd_reread /
_proof_check / _authored / _worktree / _launch, crosstest.py, ownproof.py, run.py, arm_agent.py, and the 65 kept trees. Inferences are marked.*

## 0. Three facts found while reading, which change the proposal
- **The command can take 13 of the 25 wrong fixes, on 5 tasks.** It refuses a change whose own proof fails (8 wrong trees) and a change with no product file (4 wrong trees
  hold tests only). The 13: sympy-12489 x4, sphinx-8265 x3, sympy-13615 x2, sympy-18698 x2, sphinx-8638 x2: all among "the six".
- **The yardstick is not "22 of 24".** That counts a fix flagged by any of up to four other attempts; one reread is one reader. Recomputed from crosstest.json on the fixes
  the command can take: **one other attempt's tests fail on 21 of 41 wrong-fix pairs (51%) and 11 of 39 right-fix pairs (28%)**; tests from an attempt that is itself right:
  10 of 15 and 2 of 22.
- **The reader never sees the fix, so its proof can be run on every kept fix of its task for $0.** One paid session gives up to five comparisons, not one.

## 1. Design: the proposal (reader only, no new fix), with three amendments
- **The harness rebuilds every trial tree:** a copy of `tasks/<task>/repo` committed as `main`, then the attempt's changed test and product files (crosstest's `split`) laid
  over it, uncommitted. Reason: lean trees carry odd's hooks and AGENTS.md in the base (the reader's session would load them; plain trees have none), and 8 trees hold the
  fix as a commit the reader's clone could show.
- **The harness writes every outcome file, also where the session wrote one:** `outcome: The behaviour the ticket asks for holds.`; `proof: PYTHONPATH="$PWD" ` +
  `odd.tests_proof` of the attempt's own changed test files; `in:` its changed product files. The mechanical sentence is acceptable, and better than the session's own,
  which is the first author's reading in words (sympy-13615's states the misreading). Price: this is the best case for independence, and the result must say so.
- **Every accepted reader proof is replayed at $0 on every eligible fix of its task** (crosstest's rule: its test files copied over the fix's tree, run with `tests_proof`).
  The command's own verdict on its host is kept beside.

## 2. Hosts, readers, caps
- **Eligible fix:** sympy or sphinx task, own tests pass in the rebuilt tree, a product file changed, no test file naming a kept tree's path (none does today), hidden grade
  regraded once and equal to its record.
- **Core, 24 hosts, in this order** (W wrong, R right; o2/o3 = real-out2/3): 12489: W o2 lean, W o2 plain, W six-C, W six-M, R six-S. 8265: W o2 lean, W six-C, W six-M, R
  six-S. 13615: W o3 lean, W o3 plain, R six-C, R six-M. 18698: W o3 lean, W six-M, R six-C, R six-S. 8638: W o2 lean, W six-C. Then R on other tasks: sphinx-8035 lean,
  sphinx-9673 plain, sympy-12419 lean, 13551 lean, 13647 lean. 13 W (all there are), 11 R.
- **Extension, 8 more R, only from money left:** 13877 lean, 16792 lean, 18211 lean, 19040 six-M, 20154 lean, 22914 lean, 23262 plain, 24066 lean. No pytest or pylint task
  (their test folders need settings).
- **Two readers per host, one batch:** arm H `claude-haiku-4-5` (the authors' model, the replay's condition) and arm S `claude-sonnet-5-5` (what `"reasoner"` is for). The
  replay says the reader's quality is the whole of it; only two readers on the same fixes test that. A session whose `modelUsage` names another model is void.
- **Per session:** `--max-budget-usd 0.27`, `--max-turns 40`, killed at 900 s, **`--tries 1`**. A refused try is "not compared" and is what (c) measures; the default 3
  tries would triple the worst case.

## 3. Numbers fixed now (per arm; a comparison = one accepted reader proof run on one eligible fix of its task)
The harness's own run decides: pytest exit 0 = agree, 1 = disagree, anything else = not compared.
- **A** = share of wrong-fix comparisons that disagree (up to 52). **B** = the same on right fixes (30 core, up to 43). **C** = share of sessions with no accepted proof.
  Also printed: the host verdicts alone as a 2x2, the tasks with a catch, cost a session, and how often the command's own words differ from the rerun.
- **BETTER than the replay:** A >= 60% and B <= 15%, with a catch on at least 4 of the 5 tasks.
- **LIKE the replay:** A >= 40%, B <= 40%, A - B >= 15 points, a catch on at least 3 of the 5 tasks.
- **WORSE:** A < 40%, or A - B < 15 points, or B > 40% (a disagreement then says little).
- **NOT TESTED:** C > 1/3; fewer than 26 wrong or 15 right comparisons; 3 or more void trials; the odd commit, list, caps or prompt changed after the first paid session
  (what ran is void, its cost counts).
- **Between arms:** "the stronger reader is better" only if S's A - B exceeds H's by 20 points or more. All of this is counts on 5 tasks, about 20 readers an arm, each used
  on several fixes: not rates.
- **DESIGN 3r: no outcome lets reread fail work.** Rule 2 is broken by the replay and again at any B above 0. Rule 3 cannot be met: every task here is one the command was
  shaped on. Rule 4 is not run (no session fixes what is flagged) and its cost bound fails on sight: a reader near $0.15 beside fixes of $0.17 to $0.50. The run may change
  one sentence of 3t ("no model round has run") and which reader the text suggests. Nothing more.

## 4. Money
- **Recommended: hard cap $14.40** = 24 hosts x 2 arms x $0.30 (cap $0.27 + $0.03). A trial starts only if cap minus spent minus reserves in flight covers $0.30; a session
  with no cost counts $0.30. The core is guaranteed; the extension runs as far as the money goes. No top-up, no rerun, no stopping on results. Likely spend $7 to $10
  (inference). With `--tries 3` the same list could cost $43.20.
- **Fallback: $7.20**, arm H only, same list and rules. Lost: any word on whether a stronger reader is better. **Or $0:** publish section 0 as a correction to evidence 26
  (the per-reader yardstick; 13 of 25).

## 5. Threats, to state with the result
- **Recall.** Public issues with public fixes and tests: a reader that recalls the reference test is the hidden test under another name. Arm S is the more exposed (6 of 6
  in ruling 5). Nothing here rules it out.
- **What of the fix reaches the reader** (read in cmd_reread and _worktree): the outcome file is copied into its clone and quoted in its prompt, so it gets the proof
  command, which **names the first author's test file**, and `in:`, which **names the files the fix changed**. Both say where the first author looked; that pulls towards
  agreement, most where the fix is in the wrong place (sphinx-8265). It is how the command is built: measured, not removed. The clone also reads the tree's objects through
  a path that leads back to the tree with the fix: hence the rebuilt tree (no fix in any commit) and the scan of step 8.
- **Two faults of the command, read not run (inference):** `_proof_check` takes any non-zero exit as "fails before the change", so a proof that does not collect, or whose
  named file is missing, is accepted; and a reader that writes its test at another path than the proof runs gets "two readings agree" from the author's untouched file. The
  harness counts both apart; report them whatever the bands say.
- The neutral sentence (best case). Four of the 11 core right fixes were written by Sonnet and are read by Sonnet in arm S. One kept tree a cell; 13 wrong fixes on 5 hard
  tasks, mostly one model's; grades regraded once.

## 6. `bench/rereadtest.py`: `run --root ROOT --out DIR --cap 14.40 [--arms H,S] [--jobs 2] [--dry-run]`, and `reader`
1. The host list of section 2 is a literal in the file: (task, record path, W or R, core or extension).
2. Per host build `T` = `DIR/<host>/p` (section 1). Regrade it with `realtasks.grade_status` (the fix as a patch) and run its proof once in `T`; a host whose grade differs
   from its record, or whose proof does not exit 0, is dropped, listed with the reason, never replaced.
3. Write `T/.odd/outcomes/reread.md` (section 1), nothing else under `.odd/`. Copy the task's `env/` to `DIR/<host>/env` as run.py does for a session, so no path the reader
   has names `tasks/<task>/`.
4. `--dry-run` stops here and prints the list; that output is committed before the first paid session.
5. Per host, per arm, in list order, two at a time, after reserving $0.30 in a ledger file under a lock, with cwd `T`: `python3 odd.py reread reread --base main --tries 1
   --ticket <a copy of ticket.md outside T> --by "python3 <abs>/rereadtest.py reader <trial dir> {prompt_file}"`; odd.py of commit a018794; the environment of run.py's
   `agent_env` (ENV_ALLOW, an empty GIT_CONFIG_GLOBAL, TMPDIR = the trial's own) plus the copied env first on PATH, VIRTUAL_ENV, PYTHONDONTWRITEBYTECODE=1 and **no
   PYTHONPATH**. Keep its output and exit code.
6. `reader` (its cwd is the reader's clone): the same environment with PYTHONPATH = the clone, then run.py's line: `claude -p <prompt text> --model <M> --output-format
   stream-json --verbose --setting-sources project --strict-mcp-config --no-session-persistence --max-turns 40 --max-budget-usd 0.27 --permission-mode acceptEdits
   --permission-prompts none --allowedTools Bash,Read,Glob,Grep,Skill`, stdin closed, stdout to `<trial dir>/transcript.jsonl`, killed with its group at 900 s. Cost =
   `total_cost_usd` of the result event (`arm_agent.parse_result`), models = the keys of its `modelUsage`: written to `<trial dir>/cost.json`; print `odd-cost: <usd>`; exit
   0. No result event: cost null, and the ledger keeps the $0.30.
7. Read odd's verdict: "two readings agree" / "one of the two readings is wrong" (exit 1) / "not compared" and its reason / could not run. Copy `second-proof.patch` and the
   reader's test files out before the next trial.
8. Void the trial (its cost counts, no replacement) if the transcript holds the path of `T`, of the kept tree or of `tasks/`, the words `tests_hidden` or `solution.patch`,
   or a model other than its arm's.
9. Replay, $0: each accepted proof on each eligible fix of its task (the host too): a fresh copy of that fix's tree, the reader's test files copied in, `PYTHONPATH="$PWD" `
   + `tests_proof` of those files, same environment; record the exit code. A reader file that holds its clone's path or `odd-runs-` is listed, not counted.
10. One JSON line a trial and a comparison; then per arm the tables of section 3, the band, and the ledger.

## 7. Sentences, written now
- **BETTER:** "A proof written by `odd reread` failed on a of n wrong fixes and b of m right ones (one other attempt's tests in the replay: 21 of 41 and 11 of 39). On these
  five tasks it reads better than a second attempt."
- **LIKE:** "It behaves as the replay said: a of n wrong, b of m right. A disagreement is worth a look and proves nothing; a reading cost $x."
- **WORSE:** "It does not do what the replay promised: a of n and b of m. A reader that writes only tests reads worse than one that also wrote a fix. The command stays with
  this number beside it, or goes."
- **NOT TESTED:** counts and the reason only; if C: "k of n readers wrote no proof that fails before the change in one try; the command could not be measured at this
  price."
- **Arms:** "The stronger reader caught a of n against a' of n, with b of m false alarms against b'", or "no difference shown between the two readers".
- **Always:** "Advisory; nothing here lets it fail work (DESIGN 3r). The reader had a neutral sentence, not the author's; public issues, so it may have recalled the fix; 5
  tasks." **Never:** "catches 22 of 24"; a rate; anything about private code or other models; "agreement shows the fix is right" (18 of 57 in the replay did not).

