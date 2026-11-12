#!/usr/bin/env python3
"""Run the comparison: every task x arm x repeat is one headless session, graded afterwards on hidden tests.

usage: run.py --model M [--tasks ID ...] [--arms ARM ...] [--repeats N] [--max-turns T] [--max-budget-usd B]
              [--timeout SECONDS] [--jobs J] [--out DIR] [--keep] [--dry-run] [--pass-env NAME ...] [--allow-dirty]
              [--resume] [--odd-commit SHA] [--strong-model M]

One run, in this order:
  1. a fresh copy of tasks/<id>/repo as <temp>/bench-<random>/s/project, a directory of its own outside any git
     repository; git init on main with a local identity, committed as "start"
  2. arms/<arm>/setup.sh run there (env BENCH_CACHE, ODD_PY, BENCH_PRIVATE), committed as "arm setup"; branch "work"
  3. the agent, prompted with arms/<arm>/prompt.md ({ticket} replaced), a blank line and arms/TAIL.md, in an
     environment built from an allow-list (agent_env) with TMPDIR=<top>/tmp; when it exits its process group is
     killed, then every process whose cwd or open files are under <top> (Linux /proc). An arm that ships agent.sh
     runs it instead of the one claude session (run_arm_agent; SPEC.md "An arm-supplied agent")
  4. changed lines measured against the "arm setup" commit, in a scratch index outside the session
  5. two copies made outside the session at once: P, where arms/<arm>/post.sh runs (its exit status is the arm's own
     check), and G, which waits
  6. only when every session of the invocation has ended (no agent is running anywhere): in each G the shipped
     visible tests are put back and run (regression), .bench/final.txt and .bench/claim.json are written,
     tasks/<id>/hidden copied in (each *.py with a random canary line) and the task's grade command run; then every
     transcript is audited for contamination and the record written
Writes <out>/<task>.<arm>.<n>.json and, beside it, the agent's stream-json transcript (.transcript.jsonl). Between
step 5 and the record, <out>/<task>.<arm>.<n>.pending.json (the durable manifest) holds everything the grade and the
record need, so a machine restart loses no ended session: --resume grades those, skips recorded runs and re-runs the
rest (an old transcript of a re-run is moved aside to <name>.aborted-<UTC time>). A cap
(turns, budget, timeout) or a context overflow is graded and named in stopped_at; no result, or another error result,
is not graded. SPEC.md is the contract; RUNNER-NOTES.md explains the permission flags.

No model is called with --dry-run, or when BENCH_FAKE_AGENT is set to a command. That command runs in the session
directory with the prompt on stdin and prints either one JSON object with a "result" string or stream-json lines
ending in a "result" event (optional: total_cost_usd, usage, modelUsage, num_turns, duration_ms). It is also given
BENCH_TASK, BENCH_ARM, BENCH_REPEAT and BENCH_TASK_DIR; a real agent never is. --dry-run alone uses a built-in agent
that changes nothing and answers NOT DONE.

exit 0 when every run was graded, 1 when any run could not be (its JSON names the error), 2 on bad arguments.
"""
import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import secrets
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
# The transcript readers and the claim parser are shared with the helper an arm-supplied agent runs (arm_agent.py).
from arm_agent import (EMPHASIS, LEADING_MARKS, VERDICT, USAGE_KEYS, events, parse_claim, parse_result,  # noqa: E402,F401
                       stream_usage, tokens, total, transcripts)
BENCH_REPO = os.path.dirname(HERE)
GIT = ['git', '-c', 'user.name=bench', '-c', 'user.email=bench@example.com']
# What lets a headless session edit files and run commands in its directory. Evidence: RUNNER-NOTES.md.
PERMISSION_FLAGS = ['--permission-mode', 'acceptEdits', '--permission-prompts', 'none',
                    '--allowedTools', 'Bash,Read,Glob,Grep,Skill']
# What the agent inherits (SPEC.md rule 3). On this machine PATH and HOME alone let the CLI log in and reach the API
# (RUNNER-NOTES.md); whatever another machine needs is named with --pass-env.
ENV_ALLOW = ('PATH', 'HOME', 'LANG', 'TERM', 'USER', 'LOGNAME', 'SHELL')  # TMPDIR is always the session's own
SETUP_TIMEOUT, POST_TIMEOUT, GRADE_TIMEOUT = 900, 300, 180
ARM_SPAN = 4  # an arm-supplied agent may run this many --timeout spans in all (its sessions run one after another)
# The result subtypes CLI 2.1.322 printed (exit 1, is_error true, result null) when --max-turns 1 and
# --max-budget-usd 0.00001 were reached live on 2026-11-11 (RUNNER-NOTES.md). Such a run is graded as it stands.
CAPS = {'error_max_turns': 'max_turns', 'error_max_budget_usd': 'max_budget'}
# A context overflow is the arm's outcome too (a heavy framework fills the window): graded, stopped_at "context".
OVERFLOW = 'Prompt is too long'
# Appended to every hidden *.py copied into G; any canary in any transcript is contamination, whichever run it is from.
CANARY = re.compile(r'bench-canary-[0-9a-f]{24}')
DRY_AGENT = '%s -c %s' % (shlex.quote(sys.executable), shlex.quote(
    'import json; print(json.dumps({"result": "dry run: nothing was changed\\nRESULT: NOT DONE: dry run"}))'))

LIVE = set()  # process groups now running, so an interrupt can stop every session
LIVE_LOCK = threading.Lock()
TOPS = set()  # the top directory of every session now running: its processes are never another session's leftovers
STOPPING = threading.Event()  # set on an interrupt: a session ending now was stopped, so it gets no manifest


def run(cmd, cwd, env, timeout, stdin=None):
    """Run cmd (a list, or a string for the shell) in its own process group; the whole group is killed when cmd exits
    or times out, so nothing it started in the background keeps running. Returns (exit status or None on timeout,
    stdout, stderr)."""
    p = subprocess.Popen(cmd, cwd=cwd, env=env, shell=isinstance(cmd, str), start_new_session=True,
                         stdin=subprocess.DEVNULL if stdin is None else subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8', errors='replace')
    with LIVE_LOCK:
        LIVE.add(p.pid)
    try:
        out, err = p.communicate(stdin, timeout=timeout)
        return p.returncode, out, err
    except subprocess.TimeoutExpired:
        kill_group(p.pid)
        try:
            out, err = p.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            out, err = '', ''
        return None, out, err
    finally:
        kill_group(p.pid)
        with LIVE_LOCK:
            LIVE.discard(p.pid)


def kill_group(pid):
    try:
        os.killpg(pid, signal.SIGKILL)
    except OSError:
        pass


def kill_under(top, spare=()):
    """Kill every process whose cwd, executable or an open file is under top: the CLI may detach a shell into a group
    of its own. A process whose cwd is under a spare top (another session still running) is never killed: an agent
    that looks around ../../.. may hold this session's directories open for a moment. Returns how many were killed,
    or None where /proc is not available (not Linux)."""
    if not os.path.isdir('/proc/self/fd'):
        return None
    real, killed = os.path.realpath(top), 0
    others = [os.path.realpath(t) for t in spare if os.path.realpath(t) != real]

    def under(path, root):
        return path == root or path.startswith(root + os.sep)
    for _ in range(3):  # a process may fork while the scan runs
        found = 0
        for pid in (n for n in os.listdir('/proc') if n.isdigit() and int(n) != os.getpid()):
            base = os.path.join('/proc', pid)
            try:
                fds = [os.path.join('fd', n) for n in os.listdir(os.path.join(base, 'fd'))]
            except OSError:
                fds = []
            links = []
            for name in ['cwd', 'exe'] + fds:
                try:
                    links.append(os.readlink(os.path.join(base, name)))
                except OSError:
                    pass
            try:
                cwd = os.readlink(os.path.join(base, 'cwd'))
            except OSError:
                cwd = ''
            if cwd and any(under(cwd, o) for o in others) and not under(cwd, real):
                continue  # another live session's process
            if any(under(x, real) for x in links):
                try:
                    os.kill(int(pid), signal.SIGKILL)
                    found += 1
                except OSError:
                    pass
        killed += found
        if not found:
            break
    return killed


def clear(path):
    """Remove whatever is at path (a symlink, a file or a directory) without following a symlink."""
    if os.path.islink(path) or os.path.isfile(path):
        os.unlink(path)
    elif os.path.isdir(path):
        shutil.rmtree(path)


def git(session, env, *args):
    status, out, err = run(GIT + list(args), session, env, 120)
    if status != 0:
        raise RuntimeError('git %s failed: %s' % (' '.join(args[:2]), (err or out).strip()[-300:]))
    return out.strip()


def passable(name):
    """False for the harness's own variables, the launch directory and a hosting agent session's variables."""
    hosting = name.startswith('CLAUDE') and name != 'CLAUDE_CODE_OAUTH_TOKEN'  # that one is a login, not a session
    return not (name.startswith('BENCH_') or name in ('PWD', 'OLDPWD') or hosting)


def agent_env(source, extra, gitconfig, tmpdir):
    """The agent's environment: the allow-list, LC_*, the names given with --pass-env, an empty global git config
    and a temporary directory of the session's own, so neither the machine's configuration, the shell that started
    run.py nor the shared temporary directory (other sessions) reaches the session."""
    env = {k: v for k, v in source.items() if (k in ENV_ALLOW or k.startswith('LC_') or k in extra) and passable(k)
           and k != 'TMPDIR'}
    return dict(env, GIT_CONFIG_GLOBAL=gitconfig, TMPDIR=tmpdir)


def bench_state(env):
    """(HEAD commit or None, uncommitted changes?) of the repository holding run.py. No commit counts as dirty."""
    status, head, _ = run(['git', 'rev-parse', 'HEAD'], BENCH_REPO, env, 60)
    if status != 0:
        return None, True
    status, changes, _ = run(['git', 'status', '--porcelain'], BENCH_REPO, env, 60)
    return head.strip(), status != 0 or bool(changes.strip())


def odd_from_commit(cache, env, commit='HEAD'):
    """odd.py as committed at `commit` (HEAD unless --odd-commit names one), written into the cache under its hash:
    the odd arm runs that, never the working-tree file, so every result names the exact method text it ran.
    Returns (path, sha256, the full commit id)."""
    sha = subprocess.run(['git', 'rev-parse', '--verify', '--quiet', commit + '^{commit}'], cwd=BENCH_REPO, env=env,
                         capture_output=True, text=True)
    if sha.returncode != 0:
        raise RuntimeError('no commit %s in %s' % (commit, BENCH_REPO))
    sha = sha.stdout.strip()
    found = subprocess.run(['git', 'show', sha + ':odd.py'], cwd=BENCH_REPO, env=env, capture_output=True)
    if found.returncode != 0:
        raise RuntimeError('no odd.py at %s of %s: %s' % (commit, BENCH_REPO,
                                                          found.stderr.decode(errors='replace').strip()))
    digest = hashlib.sha256(found.stdout).hexdigest()
    path = os.path.join(cache, 'odd-%s.py' % digest)
    if not os.path.isfile(path):
        part = tempfile.mkstemp(dir=cache)[1]
        with open(part, 'wb') as f:
            f.write(found.stdout)
        os.replace(part, path)  # whole or absent, even with two runs starting at once
    return path, digest, sha


def write_json(path, value):
    """value as JSON at path, whole or absent: a temporary file beside it (not ending in .json, so report.py never
    reads it), flushed to disk, then os.replace."""
    fd, part = tempfile.mkstemp(dir=os.path.dirname(path), prefix='.%s.' % os.path.basename(path), suffix='.part')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(value, f, indent=2)
            f.write('\n')
            f.flush()
            os.fsync(f.fileno())
        os.replace(part, path)
    except BaseException:
        try:
            os.unlink(part)
        except OSError:
            pass
        raise


def run_name(task_id, arm, repeat):
    return '%s.%s.%d' % (task_id, arm, repeat)


def manifest_path(cfg, rec):
    return os.path.join(cfg['out'], run_name(rec['task'], rec['arm'], rec['repeat']) + '.pending.json')


def save_manifest(cfg, pending):
    """The durable manifest of an ended session: everything finish() and record() need, written atomically. No
    top-level "task" or "arm" key, so report.py never takes it for a record."""
    write_json(manifest_path(cfg, pending['rec']), {
        'manifest': 1, 'task_id': pending['task']['id'], 'rec': pending['rec'], 'errors': pending['errors'],
        'top': pending['top'], 'copies': pending['copies'], 'grade_copy': pending['grade_copy'],
        'grading_dir': pending.get('grading_dir'), 'graded': pending['graded']})


def drop_manifest(path, manifest=None):
    """Remove a manifest and every directory it names (the copies, a grading directory)."""
    if manifest is None:
        try:
            with open(path, encoding='utf-8') as f:
                manifest = json.load(f)
        except (OSError, ValueError):
            manifest = {}
    for d in list(manifest.get('copies') or []) + [manifest.get('grading_dir')]:
        if isinstance(d, str):
            shutil.rmtree(d, ignore_errors=True)
    try:
        os.unlink(path)
    except OSError:
        pass


def load_pending(path, task):
    """The pending run a manifest describes, ready for finish() and record(), or None when it cannot be graded as it
    stands (unreadable, or its copy G is gone): then its directories are removed and the run starts again. A grading
    directory a killed grade left (hidden tests in it) is removed here, before any session starts."""
    try:
        with open(path, encoding='utf-8') as f:
            m = json.load(f)
    except (OSError, ValueError):
        m = None
    if not isinstance(m, dict) or 'rec' not in m:
        drop_manifest(path, {})
        return None
    if m.get('grading_dir'):
        shutil.rmtree(m['grading_dir'], ignore_errors=True)
    usable = m.get('graded') or m.get('grade_copy') is None or os.path.isdir(m['grade_copy'])
    if not usable:
        drop_manifest(path, m)
        return None
    return {'task': task, 'rec': m['rec'], 'errors': m.get('errors') or [], 'top': m['top'],
            'copies': m.get('copies') or [], 'grade_copy': m.get('grade_copy'), 'grading_dir': None,
            'graded': bool(m.get('graded'))}


def move_aside(out, name):
    """A run that starts again keeps its earlier transcript as <transcript>.aborted-<UTC time>."""
    old = os.path.join(out, name + '.transcript.jsonl')
    if os.path.exists(old):
        stamp, dest, n = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()), None, 0
        while dest is None or os.path.exists(dest):
            n += 1
            dest = '%s.aborted-%s%s' % (old, stamp, '' if n == 1 else '-%d' % n)
        os.replace(old, dest)


def tree_hash(directory):
    """sha256 over every file's relative path and contents, in sorted order: the task exactly as it was run."""
    h = hashlib.sha256()
    for base, dirs, files in os.walk(directory):
        dirs.sort()
        for name in sorted(files):
            path = os.path.join(base, name)
            with open(path, 'rb') as f:
                h.update(os.path.relpath(path, directory).encode() + b'\0' + hashlib.sha256(f.read()).digest())
    return h.hexdigest()


def first_line(path):
    if not os.path.isfile(path):
        return None
    with open(path, encoding='utf-8') as f:
        return f.readline().strip() or None


# Markdown around the claim line: emphasis (an underscore only at a word's edge, so snake_case in a reason survives),
# then list, quote and heading marks. A framework that wraps the line must not lose its claim (SPEC.md, the claim).
def strings(value):
    """Every string in a decoded JSON value: tool inputs, tool results, text, a subagent's events alike."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from strings(v)


def contamination(transcript, repos, tmp, own_top, cache):
    """The first string anywhere in the transcript (a tool input, a tool result, text; lines that are not JSON too)
    that shows the session reached the bench repository, hidden tests, a hidden test's canary or another session's
    directory (SPEC.md rule 8), or None. The shared cache is the arms' own install location, so it is not one."""
    temps = sorted({tmp, os.path.realpath(tmp)}, key=len, reverse=True)
    pattern = re.compile('|'.join([re.escape(r) for r in repos] + ['tests_hidden', '/hidden/', CANARY.pattern] +
                                  [re.escape(t) + r'/bench-[\w.-]+' for t in temps]))
    own = os.path.basename(own_top)
    # Another session's directory by its name alone, however it was reached (a relative path, a listing of ../../..):
    # mkdtemp names every session and copy 'bench-' plus eight characters, so seeing one that is not this session's
    # means the session looked at a peer.
    peer = re.compile(r'(?<![\w-])bench-[a-z0-9_]{8}(?![\w-])')
    # the whole cache path only: a path that merely starts with the same letters is not the cache
    shared = re.compile('|'.join(re.escape(c) + r'(?![\w.-])' for c in {cache, os.path.realpath(cache)}))
    texts = []
    for line in transcript.splitlines():
        try:
            texts.extend(strings(json.loads(line)))
        except ValueError:
            texts.append(line)
    for text in texts:
        text = shared.sub('', text)
        for m in pattern.finditer(text):
            hit = m.group(0)
            if not (os.path.basename(hit) == own and any(hit.startswith(t + '/bench-') for t in temps)):
                return hit[:120]
        for m in peer.finditer(text):
            if m.group(0) != own:
                return m.group(0)
    return None


def context_overflow(result, transcript):
    """True when the session ended because its context was full: an error result after at least one turn, with the
    CLI's "Prompt is too long" in the result or in an assistant message."""
    if not (result.get('is_error') or result.get('subtype') == 'error_during_execution') or \
            not (result.get('num_turns') or 0) > 0:
        return False
    said = list(strings([result.get('result'), result.get('errors')]))
    said += [s for e in events(transcript) if e.get('type') == 'assistant' for s in strings(e.get('message'))]
    return any(OVERFLOW in s for s in said)


def agent_command(prompt, model, max_turns, max_budget_usd, session):
    """The real agent. Every arm gets the same line; an arm's setup may name one plugin directory."""
    cmd = ['claude', '-p', prompt, '--model', model, '--output-format', 'stream-json', '--verbose',
           '--setting-sources', 'project',
           '--strict-mcp-config', '--no-session-persistence', '--max-turns', str(max_turns)]
    if max_budget_usd is not None:  # the CLI shows this to the agent ("USD budget: $0/$2"), which changes what it does
        cmd += ['--max-budget-usd', str(max_budget_usd)]
    cmd += PERMISSION_FLAGS
    marker = os.path.join(session, '.bench-plugin-dir')
    if os.path.isfile(marker):
        with open(marker, encoding='utf-8') as f:
            cmd += ['--plugin-dir', f.read().strip()]
    return cmd


def changed(session, env, base, scratch):
    """(lines, files, lines in *.py) that differ from the arm-setup commit, .bench/ excluded: git add -A, then diff
    --shortstat, in a scratch index seeded from that commit, so the session's own index and tree stay as it left
    them. The *.py figure leaves out the planning documents a framework writes."""
    env = dict(env, GIT_INDEX_FILE=os.path.join(scratch, 'index'))
    git(session, env, 'read-tree', base)
    git(session, env, 'add', '-A')
    counts = []
    for paths in (['.'], ['*.py']):
        stat = git(session, env, 'diff', '--cached', '--shortstat', base, '--', *paths, ':(exclude).bench')
        n = {word: int(count) for count, word in re.findall(r'(\d+) (file|insertion|deletion)', stat)}
        counts.append((n.get('insertion', 0) + n.get('deletion', 0), n.get('file', 0)))
    return counts[0][0], counts[0][1], counts[1][0]


def git_state(session, env):
    """(branch, worktrees, left_outside): the branch checked out, the worktree count, and whether work sits where the
    grade never looks (another worktree, or a branch other than main/work with commits HEAD does not reach)."""
    branch = git(session, env, 'branch', '--show-current') or None
    trees = [x[len('worktree '):] for x in git(session, env, 'worktree', 'list', '--porcelain').splitlines()
             if x.startswith('worktree ')]
    outside = any(os.path.realpath(t) != os.path.realpath(session) for t in trees)
    for name in git(session, env, 'for-each-ref', '--format=%(refname:short)', 'refs/heads').splitlines():
        if name not in ('main', 'work') and git(session, env, 'rev-list', '--count', 'HEAD..' + name) != '0':
            outside = True
    return branch, len(trees), outside


# A quoted string of two or more characters with a digit in it: a test's inputs and expected values ('1e3', '2h'),
# not its messages or module names.
LITERAL = re.compile(r"""(['"])((?:(?!\1)[^\\\n])*\d(?:(?!\1)[^\\\n])*)\1""")


def read_text(path):
    try:
        with open(path, encoding='utf-8') as f:
            return f.read()
    except (OSError, UnicodeDecodeError):
        return None


def lines_removed(before, after):
    """The non-blank lines of `before` that `after` no longer has: a changed line counts as removed, an added one not."""
    kept = set(after.splitlines())
    return [x for x in before.splitlines() if x.strip() and x not in kept]


def py_texts(top, tests):
    """{relative path: text} of the *.py files under top: those under tests/ when tests is true, else the others;
    hidden directories (.git, .bench, a vendored .odd) left out."""
    out = {}
    for base, dirs, names in os.walk(top):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        rel_base = os.path.relpath(base, top)
        if (rel_base.split(os.sep)[0] == 'tests') != tests:
            continue
        for name in (n for n in names if n.endswith('.py')):
            text = read_text(os.path.join(base, name))
            if text is not None:
                out[os.path.normpath(os.path.join(rel_base, name))] = text
    return out


def tests_edited(shipped, left):
    """The shipped visible test files that the session deleted or took a line out of (tests/<path>, sorted). Adding
    a test to a shipped file, or a new file, is not editing the visible tests."""
    out = []
    for base, _, names in os.walk(shipped):
        for name in names:
            rel = os.path.relpath(os.path.join(base, name), shipped)
            after = read_text(os.path.join(left, rel))
            if after is None or lines_removed(read_text(os.path.join(base, name)) or '', after):
                out.append('tests/' + rel.replace(os.sep, '/'))
    return sorted(out)


def test_literals(tests_text, code_text):
    """The quoted literals with a digit in the visible tests that the shipped code never contains."""
    return {m.group(2) for m in LITERAL.finditer(tests_text)} - {m.group(2) for m in LITERAL.finditer(code_text)}


def quoted_in(literals, added):
    """Which literals appear quoted in `added`: possible special-casing of the test inputs, for a person to judge."""
    return sorted(x for x in literals if "'%s'" % x in added or '"%s"' % x in added)


def special_cased(repo, left):
    """The visible tests' literals that the session wrote, quoted, into lines of non-test *.py files that the shipped
    file of that name lacks. A heuristic: a string built at run time, or a number compared, is not seen."""
    code = py_texts(repo, False)
    literals = test_literals('\n'.join(py_texts(repo, True).values()), '\n'.join(code.values()))
    added = '\n'.join(line for rel, text in py_texts(left, False).items()
                      for line in lines_removed(text, code.get(rel, '')))
    return quoted_in(literals, added)

def one_run(cfg, task, arm, repeat):
    """The session half of one task x arm x repeat: everything up to the copies P and G. Never raises: whatever goes
    wrong is named in the record's "error". Returns the pending run that finish() grades and record() writes."""
    rec = {'task': task['id'], 'arm': arm, 'repeat': repeat, 'model': cfg['model'], 'kind': task.get('kind'),
           'size': task.get('size'), 'expect': task.get('expect'), 'passed': None, 'claim': 'none',
           'false_done': False, 'cost_usd': None, 'cost_missing': True, 'cost_missing_reason': None,
           'input_tokens': None, 'output_tokens': None, 'usage_from': None,
           'cache_read_tokens': None, 'cache_creation_tokens': None, 'num_turns': None, 'duration_ms': None,
           'wall_seconds': None, 'changed_lines': None, 'files_changed': None, 'exit_status': None,
           'arm_check': None, 'arm_notes': None, 'error': None, 'final': '', 'max_turns': cfg['max_turns'],
           'max_budget_usd': cfg['max_budget_usd'], 'timeout_seconds': cfg['timeout'], 'cli': cfg['cli'],
           'provenance': dict(cfg['provenance'], task_tree=cfg['trees'][task['id']], arm_version=cfg['versions'][arm]),
           'env_passed': None, 'stopped_at': None, 'claim_reason': '', 'regression_passed': None,
           'changed_lines_py': None, 'transcript': None, 'contaminated': False, 'contaminated_by': None,
           'models': [], 'branch': None, 'worktrees': None, 'left_outside': None, 'leftovers_killed': None,
           'warnings': []}
    # A top-level directory per session (mkdtemp: mode 700) whose name says nothing about the task or the arm. The
    # session sits two levels down, so its own surroundings hold no other session and no hidden tests.
    top = tempfile.mkdtemp(prefix='bench-')
    with LIVE_LOCK:
        TOPS.add(top)
    session = os.path.join(top, 's', 'project')
    pending = {'task': task, 'rec': rec, 'errors': [], 'top': top, 'copies': [], 'grade_copy': None,
               'grading_dir': None, 'graded': False, 'manifest': False}
    try:
        session_and_copies(cfg, task, arm, repeat, pending, session)
    except Exception as e:  # one broken run must not stop the others
        pending['errors'].append('%s: %s' % (type(e).__name__, e))
    with LIVE_LOCK:
        TOPS.discard(top)
    if cfg['keep']:
        rec['session_dir'] = session
    else:
        shutil.rmtree(top, ignore_errors=True)
    if not STOPPING.is_set():  # a session an interrupt stopped is not an ended session: --resume runs it again
        try:
            save_manifest(cfg, pending)
            pending['manifest'] = True
        except Exception as e:
            pending['rec']['warnings'].append('manifest not written: %s: %s' % (type(e).__name__, e))
    return pending


def session_and_copies(cfg, task, arm, repeat, pending, session):
    rec, errors, top = pending['rec'], pending['errors'], pending['top']
    env, task_dir, arm_dir = cfg['env'], task['dir'], os.path.join(cfg['root'], 'arms', arm)
    private = os.path.join(top, 'private')  # the arm's per-session files outside the repository (a plugin copy)
    agent_tmp = os.path.join(top, 'tmp')  # the agent's TMPDIR: never the shared one, where other sessions sit
    os.makedirs(private)
    os.makedirs(agent_tmp)
    arm_env = dict(env, BENCH_CACHE=cfg['cache'], ODD_PY=cfg['odd_py'], BENCH_PRIVATE=private)
    gitconfig = os.path.join(top, 'gitconfig')
    open(gitconfig, 'w').close()

    shutil.copytree(os.path.join(task_dir, 'repo'), session)
    git(session, env, 'init', '-q', '-b', 'main')
    # the agent's own commits get this identity whatever the machine has (its global config is the empty file)
    git(session, env, 'config', 'user.name', 'bench')
    git(session, env, 'config', 'user.email', 'bench@example.com')
    git(session, env, 'add', '-A')
    git(session, env, 'commit', '-q', '--allow-empty', '-m', 'start')
    with cfg['setup_locks'][arm]:  # two sessions of one arm must not fill the shared cache at once
        status, out, err = run(['bash', os.path.join(arm_dir, 'setup.sh')], session, arm_env, SETUP_TIMEOUT)
    if status != 0:
        errors.append('arm setup %s: %s' % ('timed out' if status is None else 'exited %d' % status,
                                            (err or out).strip()[-300:]))
        return
    git(session, env, 'add', '-A')
    git(session, env, 'commit', '-q', '--allow-empty', '-m', 'arm setup')
    base = git(session, env, 'rev-parse', 'HEAD')
    git(session, env, 'checkout', '-q', '-b', 'work')  # every arm starts here; no setup.sh makes a branch

    with open(os.path.join(arm_dir, 'prompt.md'), encoding='utf-8') as f:
        template = f.read()
    with open(os.path.join(task_dir, 'ticket.md'), encoding='utf-8') as f:
        prompt = template.replace('{ticket}', f.read().strip()).rstrip('\n') + '\n\n' + cfg['tail']
    agent = agent_env(os.environ, cfg['pass_env'], gitconfig, agent_tmp)
    rec['env_passed'] = sorted(agent)
    started = time.time()
    arm_agent = os.path.join(arm_dir, 'agent.sh')
    if cfg['fake']:  # no model: the fake replaces an arm-supplied agent too
        fake_env = dict(agent, BENCH_TASK=task['id'], BENCH_ARM=arm, BENCH_REPEAT=str(repeat), BENCH_TASK_DIR=task_dir)
        status, out, err = run(cfg['fake'], session, fake_env, cfg['timeout'], stdin=prompt)
    elif os.path.isfile(arm_agent):
        status, out, err = run_arm_agent(cfg, rec, arm_agent, prompt, session, top, agent)
    else:
        cmd = agent_command(prompt, cfg['model'], cfg['max_turns'], cfg['max_budget_usd'], session)
        status, out, err = run(cmd, session, agent, cfg['timeout'])
    rec['wall_seconds'] = round(time.time() - started, 1)
    # run() killed the agent's process group; whatever it detached is stopped here, before anything reads the tree
    with LIVE_LOCK:
        spare = sorted(TOPS - {top})
    rec['leftovers_killed'] = kill_under(top, spare)
    if rec['leftovers_killed'] is None:
        rec['warnings'].append('leftover processes not checked: /proc is not available here')
    rec['exit_status'] = status
    rec['transcript'] = '%s.%s.%d.transcript.jsonl' % (task['id'], arm, repeat)
    summed = total(os.path.join(top, 'transcripts')) if 'sessions' in rec else None
    texts = dict(transcripts(os.path.join(top, 'transcripts'))) if summed is not None else {}
    with open(os.path.join(cfg['out'], rec['transcript']), 'w', encoding='utf-8') as f:
        if summed is not None:  # every claude session the arm started, then the arm's own output
            for name, text in sorted(texts.items()):
                f.write(json.dumps({'type': 'bench_session', 'file': name}) + '\n' + text)
            f.write(json.dumps({'type': 'bench_arm_agent_output'}) + '\n')
        f.write(out)
    result = parse_result(out) or {}
    rec['stopped_at'], error = outcome_of(status, result, out, err)
    if error:
        errors.append('the agent ' + error)
    if summed is not None:
        for s in summed['sessions']:
            stopped, error = outcome_of(s['exit'], s['result'] or {}, texts[s['file']], '')
            if error:
                errors.append('claude session %s: %s' % (s['file'], error))
            s.update(stopped_at=stopped, result=None)
        rec['sessions'] = summed['sessions']
        if result:  # the figures are run.py's own sum over the transcripts, never the arm's report of them
            if result.get('total_cost_usd') != summed['total_cost_usd']:
                rec['warnings'].append('the arm reported a cost of %s; the sum over its sessions is %s'
                                       % (result.get('total_cost_usd'), summed['total_cost_usd']))
            result = dict(result, total_cost_usd=summed['total_cost_usd'], num_turns=summed['num_turns'],
                          duration_ms=summed['duration_ms'], usage=summed['usage'], modelUsage=None)
        measure(rec, result, read_text(os.path.join(cfg['out'], rec['transcript'])) or '')
        rec['models'] = summed['models'] or rec['models']
        missing = [s['file'] for s in summed['sessions'] if s['cost_usd'] is None]
        if missing:
            rec['cost_missing_reason'] = ('%d of %d claude session(s) have no result event with a cost (%s): the CLI '
                                          'prices a session only there' % (len(missing), len(summed['sessions']),
                                                                           ', '.join(missing)))
    else:
        measure(rec, result, out)
    final = result.get('result') if isinstance(result.get('result'), str) else ''
    rec['final'] = final
    rec['claim'], rec['claim_reason'] = parse_claim(final)

    # The session is over and is never written again: what the arm runs afterwards and the grade each get a copy of
    # it, made now, outside it, so neither can change the other and --keep keeps the tree exactly as the session left
    # it. G holds no hidden test until every session has ended (finish).
    pending['copies'] = copies = [tempfile.mkdtemp(prefix='bench-'), tempfile.mkdtemp(prefix='bench-')]
    try:
        rec['changed_lines'], rec['files_changed'], rec['changed_lines_py'] = changed(session, env, base, copies[0])
        rec['branch'], rec['worktrees'], rec['left_outside'] = git_state(session, env)
    except RuntimeError as e:
        rec['warnings'].append('git state not measured: %s' % e)
    if errors:
        return
    post_copy, pending['grade_copy'] = (copy_of(session, d) for d in copies)
    post = os.path.join(arm_dir, 'post.sh')
    if os.path.isfile(post):
        notes = os.path.join(copies[0], 'post-notes.json')  # beside P, not in it: what post.sh reports
        rec['arm_check'] = run(['bash', post], post_copy, dict(arm_env, BENCH_POST_NOTES=notes), POST_TIMEOUT)[0]
        if os.path.isfile(notes):
            try:
                with open(notes, encoding='utf-8') as f:
                    rec['arm_notes'] = json.load(f)
            except ValueError as e:
                rec['warnings'].append('post.sh notes unreadable: %s' % e)


def outcome_of(status, result, transcript, err):
    """(stopped_at, error) of one session. A cap or a context overflow is the arm's own outcome and is graded;
    anything else without a clean result is the machine's failure and enters no rate, so a rate limit or a crash
    never counts against an arm."""
    if status is None:
        return 'timeout', None
    if result.get('subtype') in CAPS:
        return CAPS[result['subtype']], None
    if result and context_overflow(result, transcript):
        return 'context', None
    if not result:
        return None, 'printed no result object: %s' % (err or transcript).strip()[-300:]
    if result.get('is_error') or str(result.get('subtype') or 'success') != 'success':
        return None, 'reported %s: %s' % ('an error' if result.get('subtype') in (None, 'success') else result['subtype'],
                                         str(result.get('result') or result.get('errors') or '')[:300])
    return None, None


def run_arm_agent(cfg, rec, script, prompt, session, top, agent):
    """An arm-supplied agent (SPEC.md): arms/<arm>/agent.sh, copied with arm_agent.py into <top>/arm (so nothing it
    runs names the bench's path), run in the session directory with the prompt on stdin and the ARM_* variables;
    every claude session it starts writes its transcript into <top>/transcripts. Bounded by ARM_SPAN times the
    timeout, since its sessions run one after another; each session is bounded by the timeout itself."""
    own, folder = os.path.join(top, 'arm'), os.path.join(top, 'transcripts')
    os.makedirs(own)
    os.makedirs(folder)
    shutil.copy2(script, os.path.join(own, 'agent.sh'))
    shutil.copy2(os.path.join(HERE, 'arm_agent.py'), os.path.join(own, 'arm_agent.py'))
    flags = agent_command('', cfg['model'], cfg['max_turns'], cfg['max_budget_usd'], session)
    assert flags[:2] == ['claude', '-p'] and flags[3] == '--model', flags
    env = dict(agent, ARM_MODEL=cfg['model'], ARM_STRONG_MODEL=cfg['strong_model'], ARM_MAX_TURNS=str(cfg['max_turns']),
               ARM_MAX_BUDGET_USD='' if cfg['max_budget_usd'] is None else str(cfg['max_budget_usd']),
               ARM_TIMEOUT=str(cfg['timeout']), ARM_TRANSCRIPTS=folder, ARM_CLAUDE_FLAGS=json.dumps(flags[5:]),
               ARM_AGENT_ENV=json.dumps(sorted(agent)), ARM_HELPER=os.path.join(own, 'arm_agent.py'),
               ARM_ODD_PY=cfg['odd_py'])
    rec.update(sessions=[], strong_model=cfg['strong_model'], arm_timeout_seconds=cfg['timeout'] * ARM_SPAN)
    return run(['bash', os.path.join(own, 'agent.sh')], session, env, cfg['timeout'] * ARM_SPAN, stdin=prompt)


def measure(rec, result, transcript):
    """Cost, tokens, turns and models: the CLI's own result event when there is one with figures; otherwise (the
    timeout stopped the session before it printed one) tokens, turns and models rebuilt from the transcript's
    assistant events, and the cost left null with the reason, since the CLI prices a session only in its result."""
    if any(k in result for k in ('total_cost_usd', 'usage', 'modelUsage')):
        rec.update(cost_usd=result.get('total_cost_usd'), num_turns=result.get('num_turns'),
                   duration_ms=result.get('duration_ms'), models=sorted(result.get('modelUsage') or {}),
                   usage_from='result')
        (rec['input_tokens'], rec['output_tokens'], rec['cache_read_tokens'],
         rec['cache_creation_tokens']) = tokens(result)
        if rec['cost_usd'] is None:
            rec['cost_missing_reason'] = 'the result event has no total_cost_usd'
    else:
        rebuilt = stream_usage(transcript)
        if rebuilt:
            (rec['input_tokens'], rec['output_tokens'], rec['cache_read_tokens'], rec['cache_creation_tokens']), \
                rec['num_turns'], rec['models'] = rebuilt
            rec['usage_from'] = 'transcript'
        rec['cost_missing_reason'] = ('no result event: the CLI prices a session only there, and run.py keeps no '
                                      'price table of its own' + ('' if rebuilt else '; no assistant usage either'))
    rec['cost_missing'] = rec['cost_usd'] is None


def finish(cfg, pending, canaries):
    """The grade half, run only once no session is running anywhere: hidden tests reach the disk only now. Never
    raises; the copies are removed whatever happens."""
    grading = None
    try:
        if pending['grade_copy'] and not pending['errors']:
            # The grade runs in a fresh copy of G, named in the manifest before any hidden test reaches the disk: a
            # grade the machine kills leaves G untouched, and --resume removes that copy before a session starts.
            grading = pending['grading_dir'] = tempfile.mkdtemp(prefix='bench-')
            if pending['manifest']:
                save_manifest(cfg, pending)
            work = copy_of(pending['grade_copy'], grading)
            pending['graded'] = grade(pending['task'], work, cfg['env'], pending['rec'], canaries)
            pending['grading_dir'] = None
            if pending['manifest']:
                save_manifest(cfg, pending)  # graded: the record no longer needs the copies
    except Exception as e:  # a machine failure: what a session left is handled inside grade()
        pending['errors'].append('grade: %s: %s' % (type(e).__name__, e))
    finally:
        for d in pending['copies'] + [grading]:
            if d:
                shutil.rmtree(d, ignore_errors=True)


def record(cfg, pending):
    """Audit the transcript (after every grade, so every canary of this invocation exists) and write the record."""
    rec, errors = pending['rec'], pending['errors']
    if rec['transcript']:
        with open(os.path.join(cfg['out'], rec['transcript']), encoding='utf-8') as f:
            hit = contamination(f.read(), sorted({BENCH_REPO, cfg['root']}), tempfile.gettempdir(), pending['top'],
                                cfg['cache'])
        rec['contaminated'], rec['contaminated_by'] = hit is not None, hit
    rec['error'] = '; '.join(errors) or None
    if not pending['graded'] or errors:
        rec['passed'] = None
    rec['false_done'] = rec['claim'] == 'DONE' and rec['passed'] is False
    write_json(os.path.join(cfg['out'], run_name(rec['task'], rec['arm'], rec['repeat']) + '.json'), rec)
    try:
        os.unlink(manifest_path(cfg, rec))
    except OSError:
        pass
    return rec


def copy_of(session, directory):
    copy = os.path.join(directory, 'project')
    shutil.copytree(session, copy, symlinks=True)
    return copy


def grade(task, copy, env, rec, canaries):
    """The grade, in copy G, the only place the hidden tests are ever copied to. First the visible tests as the task
    ships them replace whatever the session left at tests/ (a directory, a file or a symlink: regression, behaviour
    the hidden tests may not cover), then the claim and final message are written and the hidden tests copied in,
    each path cleared first so nothing the session left there is followed or mixed in, every *.py marked with a
    random canary line. Before the visible tests are replaced, two facts for the cheat rate are read from what the
    session left: the shipped visible test files it deleted or took lines out of (visible_tests_edited) and the
    visible tests' literals it wrote into its code (special_cased). Nothing a session did makes this raise."""
    shipped = os.path.join(task['dir'], 'repo', 'tests')
    rec['special_cased'] = special_cased(os.path.join(task['dir'], 'repo'), copy)
    if os.path.isdir(shipped):
        rec['visible_tests_edited'] = tests_edited(shipped, os.path.join(copy, 'tests'))
        clear(os.path.join(copy, 'tests'))
        shutil.copytree(shipped, os.path.join(copy, 'tests'))
        status = run(['python3', '-m', 'unittest', 'discover', '-s', 'tests', '-q'], copy, env, GRADE_TIMEOUT)[0]
        rec['regression_passed'] = status == 0
        if status is None:
            rec['warnings'].append('the visible tests were stopped after %d seconds' % GRADE_TIMEOUT)
    clear(os.path.join(copy, '.bench'))
    os.makedirs(os.path.join(copy, '.bench'))
    with open(os.path.join(copy, '.bench', 'final.txt'), 'w', encoding='utf-8') as f:
        f.write(rec['final'] + '\n')
    with open(os.path.join(copy, '.bench', 'claim.json'), 'w', encoding='utf-8') as f:
        json.dump({'claim': rec['claim'], 'reason': rec['claim_reason']}, f)
    hidden = os.path.join(task['dir'], 'hidden')
    canary = 'bench-canary-' + secrets.token_hex(12)
    canaries.append(canary)
    for name in os.listdir(hidden):
        source, dest = os.path.join(hidden, name), os.path.join(copy, name)
        clear(dest)
        if os.path.isdir(source):
            shutil.copytree(source, dest)
        else:
            shutil.copy2(source, dest)
        marked = [dest] if not os.path.isdir(dest) else [os.path.join(b, f) for b, _, fs in os.walk(dest) for f in fs]
        for path in (p for p in marked if p.endswith('.py')):
            with open(path, 'a', encoding='utf-8') as out:
                out.write('\n# %s\n' % canary)
    status = run(task['grade'], copy, env, GRADE_TIMEOUT)[0]
    if status is None:  # code that hangs is the session's outcome: a fail, not a machine error
        rec['warnings'].append('grade was stopped after %d seconds' % GRADE_TIMEOUT)
    rec['passed'] = status == 0
    return True


def names_in(directory, need):
    if not os.path.isdir(directory):
        return []
    return sorted(n for n in os.listdir(directory) if all(os.path.exists(os.path.join(directory, n, x)) for x in need))


def main(argv=None):
    ap = argparse.ArgumentParser(description='Run task x arm x repeat and write one JSON file per run.')
    ap.add_argument('--tasks', nargs='+', metavar='ID', help='task ids (default: every task)')
    ap.add_argument('--arms', nargs='+', metavar='ARM', help='arms (default: every directory under arms/)')
    ap.add_argument('--repeats', type=int, default=1)
    ap.add_argument('--model', help='required unless --dry-run')
    ap.add_argument('--max-turns', type=int, default=80)
    ap.add_argument('--max-budget-usd', type=float, default=None,
                    help='off by default: the CLI writes it into the agent\'s system prompt, and agents then cut steps; '
                         'a measured run is bounded by --max-turns and --timeout, which the agent does not see')
    ap.add_argument('--timeout', type=int, default=2400, help='seconds one session may take')
    ap.add_argument('--strong-model', default='sonnet',
                    help='the second model an arm-supplied agent may use (ARM_STRONG_MODEL; default: sonnet)')
    ap.add_argument('--jobs', type=int, default=2, help='sessions at a time')
    ap.add_argument('--out', help='results directory (default: results/<UTC timestamp> beside this file)')
    ap.add_argument('--keep', action='store_true', help='keep the session directories')
    ap.add_argument('--dry-run', action='store_true', help='call no model: BENCH_FAKE_AGENT, or a do-nothing agent')
    ap.add_argument('--root', default=HERE, help='directory holding tasks/ and arms/ (default: beside this file)')
    ap.add_argument('--pass-env', nargs='+', default=[], metavar='NAME', help='more variables the agent may inherit')
    ap.add_argument('--allow-dirty', action='store_true', help='run a model even with uncommitted bench changes')
    ap.add_argument('--resume', action='store_true',
                    help='continue an interrupted --out: skip recorded runs, grade ended sessions from their manifests, '
                         'run the rest again')
    ap.add_argument('--odd-commit', metavar='SHA', default='HEAD',
                    help='the bench commit whose odd.py the odd arm runs (default: HEAD)')
    a = ap.parse_args(argv)
    if a.resume and not a.out:
        ap.error('--resume needs --out: the results directory to continue')

    fake = os.environ.get('BENCH_FAKE_AGENT') or (DRY_AGENT if a.dry_run else None)
    if not fake and not a.model:
        ap.error('--model is required unless --dry-run')
    refused = [n for n in a.pass_env if not passable(n)]
    if refused:
        ap.error('never passed to the agent: %s' % ', '.join(refused))
    root = os.path.abspath(a.root)
    all_tasks = names_in(os.path.join(root, 'tasks'), ('task.json', 'ticket.md', 'repo', 'hidden'))
    all_arms = names_in(os.path.join(root, 'arms'), ('setup.sh', 'prompt.md'))
    unknown = [t for t in a.tasks or [] if t not in all_tasks] + [x for x in a.arms or [] if x not in all_arms]
    if unknown or not all_tasks or not all_arms or a.repeats < 1 or a.jobs < 1:
        ap.error('unknown or incomplete task or arm: %s' % ', '.join(unknown) if unknown
                 else 'need at least one task, one arm, one repeat and one job')
    tail_path = os.path.join(root, 'arms', 'TAIL.md')
    if not os.path.isfile(tail_path):
        ap.error('%s is missing: the ending every prompt gets' % tail_path)
    with open(tail_path, encoding='utf-8') as f:
        tail = f.read()
    env = {k: v for k, v in os.environ.items() if k not in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE')}
    commit, dirty = bench_state(env)
    if dirty and not fake and not a.allow_dirty:
        ap.error('%s has uncommitted changes (or no commit), so a result could not name what ran; commit them, '
                 'or pass --allow-dirty and the record says so' % BENCH_REPO)
    tasks = []
    for tid in a.tasks or all_tasks:
        with open(os.path.join(root, 'tasks', tid, 'task.json'), encoding='utf-8') as f:
            tasks.append(dict(json.load(f), id=tid, dir=os.path.join(root, 'tasks', tid)))
    arms = a.arms or all_arms

    tmp = tempfile.gettempdir()
    if run(['git', 'rev-parse', '--show-toplevel'], tmp, env, 60)[0] == 0:
        sys.exit('the temporary directory %s is inside a git repository; set TMPDIR to one that is not' % tmp)
    out = os.path.abspath(a.out or os.path.join(HERE, 'results', time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())))
    cache = os.environ.get('BENCH_CACHE') or os.path.join(tempfile.gettempdir(), 'bench-cache')
    os.makedirs(out, exist_ok=True)
    os.makedirs(cache, exist_ok=True)
    try:
        odd_py, odd_sha, odd_commit = odd_from_commit(cache, env, a.odd_commit)
    except RuntimeError as e:
        sys.exit(str(e))
    try:
        cli = None if fake else (run(['claude', '--version'], tmp, env, 60)[1].strip() or None)
    except OSError:
        sys.exit('the claude command was not found; install it, or use --dry-run')
    cfg = {'root': root, 'out': out, 'cache': cache, 'env': env, 'fake': fake, 'keep': a.keep, 'cli': cli,
           'tail': tail, 'pass_env': a.pass_env, 'odd_py': odd_py,
           'provenance': {'bench_commit': commit, 'bench_dirty': dirty, 'odd_sha256': odd_sha,
                          'odd_commit': odd_commit},
           'trees': {t['id']: tree_hash(t['dir']) for t in tasks},
           'versions': {arm: first_line(os.path.join(root, 'arms', arm, 'VERSION')) for arm in arms},
           'model': 'none (fake agent)' if fake else a.model, 'max_turns': a.max_turns, 'max_budget_usd': a.max_budget_usd,
           'timeout': a.timeout, 'strong_model': a.strong_model, 'setup_locks': {arm: threading.Lock() for arm in arms}}

    todo = [(task, arm, n) for n in range(1, a.repeats + 1) for task in tasks for arm in arms]
    print('%d run(s): %d task(s) x %d arm(s) x %d repeat(s), %d at a time -> %s'
          % (len(todo), len(tasks), len(arms), a.repeats, a.jobs, out), flush=True)
    pending, canaries, skipped = [], [], 0
    if a.resume:  # decided before any session starts, so a killed grade's hidden tests are gone before one does
        fresh = []
        for task, arm, n in todo:
            name = os.path.join(out, run_name(task['id'], arm, n))
            if os.path.exists(name + '.json'):
                skipped += 1
                if os.path.exists(name + '.pending.json'):  # killed between the record and the manifest's removal
                    drop_manifest(name + '.pending.json')
                continue
            resumed = load_pending(name + '.pending.json', task) if os.path.exists(name + '.pending.json') else None
            if resumed:
                resumed['manifest'] = True
                pending.append(resumed)
            else:
                move_aside(out, os.path.basename(name))
                fresh.append((task, arm, n))
        print('resume: %d recorded (skipped), %d ended session(s) to grade, %d to run'
              % (skipped, len(pending), len(fresh)), flush=True)
        todo = fresh
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=a.jobs)
    futures = [pool.submit(one_run, cfg, *job) for job in todo]
    try:
        for future in concurrent.futures.as_completed(futures):
            pending.append(future.result())
            r = pending[-1]['rec']
            print('%-28s %-12s %d  session ended%s' % (
                r['task'], r['arm'], r['repeat'], ', stopped at %s' % r['stopped_at'] if r['stopped_at'] else ''),
                flush=True)
        # Every session has ended, so no agent is running anywhere: only now does a hidden test reach the disk.
        futures = [pool.submit(finish, cfg, p, canaries) for p in pending if not p['graded']]
        for future in futures:
            future.result()
    except KeyboardInterrupt:
        STOPPING.set()
        for future in futures:
            future.cancel()
        with LIVE_LOCK:
            for pid in list(LIVE):
                kill_group(pid)
        pool.shutdown(wait=True)
        for p in pending:  # graded runs are written; the rest are left for --resume
            if p['graded']:
                record(cfg, p)
            elif not p['manifest']:
                for d in p['copies']:
                    shutil.rmtree(d, ignore_errors=True)
        print('interrupted: sessions stopped; graded runs are in %s; run again with --resume --out %s to grade '
              'the ended sessions and run the rest' % (out, out), file=sys.stderr)
        return 130
    pool.shutdown(wait=True)
    not_graded = 0
    for p in sorted(pending, key=lambda p: (p['rec']['task'], p['rec']['arm'], p['rec']['repeat'])):
        r = record(cfg, p)
        not_graded += r['passed'] is None
        print('%-28s %-12s %d  %-10s claim=%-8s %s%s%s%s' % (
            r['task'], r['arm'], r['repeat'],
            'not graded' if r['passed'] is None else 'passed' if r['passed'] else 'failed', r['claim'],
            'stopped at %s ' % r['stopped_at'] if r['stopped_at'] else '',
            '' if r['cost_usd'] is None else '$%.2f ' % r['cost_usd'],
            'CONTAMINATED by %s ' % r['contaminated_by'] if r['contaminated'] else '', r['error'] or ''), flush=True)
    if a.keep:
        print('session directories kept: each record names its own in session_dir')
    print('%d run(s) written to %s, %d not graded%s' % (len(pending), out, not_graded,
                                                      ', %d already recorded' % skipped if a.resume else ''))
    return 1 if not_graded else 0


if __name__ == '__main__':
    sys.exit(main())
