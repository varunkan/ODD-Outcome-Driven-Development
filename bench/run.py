#!/usr/bin/env python3
"""Run the comparison: every task x arm x repeat is one headless session, graded afterwards on hidden tests.

usage: run.py --model M [--tasks ID ...] [--arms ARM ...] [--repeats N] [--max-turns T] [--max-budget-usd B]
              [--timeout SECONDS] [--jobs J] [--out DIR] [--keep] [--dry-run] [--pass-env NAME ...] [--allow-dirty]

One run, in this order:
  1. a fresh copy of tasks/<id>/repo as <temp>/bench-<random>/s/project, a directory of its own outside any git
     repository; git init on main with a local identity, committed as "start"
  2. arms/<arm>/setup.sh run there (env BENCH_CACHE, ODD_PY, BENCH_PRIVATE), committed as "arm setup"; branch "work"
  3. the agent, prompted with arms/<arm>/prompt.md ({ticket} replaced), a blank line and arms/TAIL.md, in an
     environment built from an allow-list (agent_env)
  4. changed lines measured against the "arm setup" commit, in a scratch index outside the session
  5. two copies made outside the session: P, where arms/<arm>/post.sh runs (its exit status is the arm's own check),
     and G, where .bench/final.txt is written, tasks/<id>/hidden copied in and the task's grade command run
Writes <out>/<task>.<arm>.<n>.json. SPEC.md is the contract; RUNNER-NOTES.md explains the permission flags.

No model is called with --dry-run, or when BENCH_FAKE_AGENT is set to a command. That command runs in the session
directory with the prompt on stdin and must print a JSON object with a "result" string (optional: total_cost_usd,
usage, num_turns, duration_ms). It is also given BENCH_TASK, BENCH_ARM, BENCH_REPEAT and BENCH_TASK_DIR; a real
agent never is. --dry-run alone uses a built-in agent that changes nothing and answers NOT DONE.

exit 0 when every run was graded, 1 when any run could not be (its JSON names the error), 2 on bad arguments.
"""
import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH_REPO = os.path.dirname(HERE)
GIT = ['git', '-c', 'user.name=bench', '-c', 'user.email=bench@example.com']
# What lets a headless session edit files and run commands in its directory. Evidence: RUNNER-NOTES.md.
PERMISSION_FLAGS = ['--permission-mode', 'acceptEdits', '--permission-prompts', 'none',
                    '--allowedTools', 'Bash,Read,Glob,Grep,Skill']
# What the agent inherits (SPEC.md rule 3). On this machine PATH and HOME alone let the CLI log in and reach the API
# (RUNNER-NOTES.md); whatever another machine needs is named with --pass-env.
ENV_ALLOW = ('PATH', 'HOME', 'LANG', 'TERM', 'USER', 'LOGNAME', 'SHELL', 'TMPDIR')
SETUP_TIMEOUT, POST_TIMEOUT, GRADE_TIMEOUT = 900, 300, 180
# The result subtypes CLI 2.1.322 printed when a cap was reached (RUNNER-NOTES.md): such a run is graded as it stands.
CAPS = {'error_max_turns': 'max_turns', 'error_max_budget_usd': 'max_budget'}
DRY_AGENT = '%s -c %s' % (shlex.quote(sys.executable), shlex.quote(
    'import json; print(json.dumps({"result": "dry run: nothing was changed\\nRESULT: NOT DONE: dry run"}))'))

LIVE = set()  # process groups now running, so an interrupt can stop every session
LIVE_LOCK = threading.Lock()


def run(cmd, cwd, env, timeout, stdin=None):
    """Run cmd (a list, or a string for the shell) in its own process group; on timeout the whole group is killed.
    Returns (exit status or None on timeout, stdout, stderr)."""
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
        with LIVE_LOCK:
            LIVE.discard(p.pid)


def kill_group(pid):
    try:
        os.killpg(pid, signal.SIGKILL)
    except OSError:
        pass


def git(session, env, *args):
    status, out, err = run(GIT + list(args), session, env, 120)
    if status != 0:
        raise RuntimeError('git %s failed: %s' % (' '.join(args[:2]), (err or out).strip()[-300:]))
    return out.strip()


def passable(name):
    """False for the harness's own variables, the launch directory and a hosting agent session's variables."""
    hosting = name.startswith('CLAUDE') and name != 'CLAUDE_CODE_OAUTH_TOKEN'  # that one is a login, not a session
    return not (name.startswith('BENCH_') or name in ('PWD', 'OLDPWD') or hosting)


def agent_env(source, extra, gitconfig):
    """The agent's environment: the allow-list, LC_*, the names given with --pass-env, and an empty global git
    config, so neither the machine's configuration nor the shell that started run.py reaches the session."""
    env = {k: v for k, v in source.items() if (k in ENV_ALLOW or k.startswith('LC_') or k in extra) and passable(k)}
    return dict(env, GIT_CONFIG_GLOBAL=gitconfig)


def bench_state(env):
    """(HEAD commit or None, uncommitted changes?) of the repository holding run.py. No commit counts as dirty."""
    status, head, _ = run(['git', 'rev-parse', 'HEAD'], BENCH_REPO, env, 60)
    if status != 0:
        return None, True
    status, changes, _ = run(['git', 'status', '--porcelain'], BENCH_REPO, env, 60)
    return head.strip(), status != 0 or bool(changes.strip())


def odd_from_head(cache, env):
    """odd.py as committed at HEAD, written into the cache under its hash: the odd arm runs that, never the
    working-tree file, so every result names the exact method text it ran. Returns (path, sha256)."""
    found = subprocess.run(['git', 'show', 'HEAD:odd.py'], cwd=BENCH_REPO, env=env, capture_output=True)
    if found.returncode != 0:
        raise RuntimeError('no odd.py at HEAD of %s: %s' % (BENCH_REPO, found.stderr.decode(errors='replace').strip()))
    digest = hashlib.sha256(found.stdout).hexdigest()
    path = os.path.join(cache, 'odd-%s.py' % digest)
    if not os.path.isfile(path):
        part = tempfile.mkstemp(dir=cache)[1]
        with open(part, 'wb') as f:
            f.write(found.stdout)
        os.replace(part, path)  # whole or absent, even with two runs starting at once
    return path, digest


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
EMPHASIS = re.compile(r'[*`]|(?<![A-Za-z0-9])_+|_+(?![A-Za-z0-9])')
LEADING_MARKS = re.compile(r'^(?:[\s>#+-]+|\d+[.)]\s+)+')
VERDICT = re.compile(r'RESULT:\s*(NOT\s+DONE|DONE)\s*(?:[:\-\u2013\u2014]\s*(.*))?$', re.IGNORECASE)


def parse_claim(final):
    """(claim, reason): the last line of the final message that contains RESULT:, cleaned of Markdown, must read
    RESULT: DONE or RESULT: NOT DONE, optionally with ':' or a dash and a reason; anything else is ('none', '')."""
    line = next((x for x in reversed(final.splitlines()) if 'RESULT:' in x), '')
    line = LEADING_MARKS.sub('', EMPHASIS.sub('', line)).strip()
    found = VERDICT.match(line) if line.startswith('RESULT:') else None
    if not found:
        return 'none', ''
    return ('NOT DONE' if found.group(1).upper() != 'DONE' else 'DONE'), (found.group(2) or '').strip()


def tool_inputs(transcript):
    """Every tool input in a stream-json transcript, as JSON text (subagents' calls included: they are events too)."""
    for line in transcript.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        content = (event.get('message') or {}).get('content') if isinstance(event, dict) else None
        for block in content if isinstance(content, list) else []:
            if isinstance(block, dict) and block.get('type') == 'tool_use':
                yield json.dumps(block.get('input'))


def contamination(transcript, repos, tmp, own_top, cache):
    """The first string a tool input used to reach the bench repository, hidden tests or another session's
    directory (SPEC.md rule 8), or None. The shared cache is the arms' own install location, so it is not one."""
    temps = sorted({tmp, os.path.realpath(tmp)}, key=len, reverse=True)
    pattern = re.compile('|'.join([re.escape(r) for r in repos] + ['tests_hidden', '/hidden/'] +
                                  [re.escape(t) + r'/bench-[\w.-]+' for t in temps]))
    own = os.path.basename(own_top)
    for text in tool_inputs(transcript):
        for c in {cache, os.path.realpath(cache)}:
            text = text.replace(c, '')
        for m in pattern.finditer(text):
            hit = m.group(0)
            if not (os.path.basename(hit) == own and any(hit.startswith(t + '/bench-') for t in temps)):
                return hit[:120]
    return None


def parse_result(stdout):
    """The agent's result object: the whole output, or failing that its last line that is such an object."""
    for text in [stdout] + stdout.strip().splitlines()[::-1]:
        try:
            found = json.loads(text)
        except ValueError:
            continue
        if isinstance(found, list):
            found = next((o for o in reversed(found) if isinstance(o, dict) and o.get('type') == 'result'), None)
        if isinstance(found, dict) and ('result' in found or found.get('type') == 'result'):
            return found
    return None


def tokens(result):
    """(input, output, cache read, cache write) tokens. The CLI's "modelUsage" counts subagents too, so it is used
    when present; "usage" is the main conversation only."""
    per_model = [m for m in (result.get('modelUsage') or {}).values() if isinstance(m, dict)]
    if per_model:
        return [sum(m.get(k) or 0 for m in per_model)
                for k in ('inputTokens', 'outputTokens', 'cacheReadInputTokens', 'cacheCreationInputTokens')]
    usage = result.get('usage') or {}
    return [usage.get(k) for k in ('input_tokens', 'output_tokens', 'cache_read_input_tokens',
                                   'cache_creation_input_tokens')]


def agent_command(prompt, model, max_turns, max_budget_usd, session):
    """The real agent. Every arm gets the same line; an arm's setup may name one plugin directory."""
    cmd = ['claude', '-p', prompt, '--model', model, '--output-format', 'stream-json', '--verbose',
           '--setting-sources', 'project',
           '--strict-mcp-config', '--no-session-persistence', '--max-turns', str(max_turns), '--max-budget-usd', str(max_budget_usd)]
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


def one_run(cfg, task, arm, repeat):
    """One task x arm x repeat. Never raises: whatever goes wrong is named in the record's "error"."""
    rec = {'task': task['id'], 'arm': arm, 'repeat': repeat, 'model': cfg['model'], 'kind': task.get('kind'),
           'size': task.get('size'), 'expect': task.get('expect'), 'passed': None, 'claim': 'none',
           'false_done': False, 'cost_usd': None, 'input_tokens': None, 'output_tokens': None,
           'cache_read_tokens': None, 'cache_creation_tokens': None, 'num_turns': None, 'duration_ms': None,
           'wall_seconds': None, 'changed_lines': None, 'files_changed': None, 'exit_status': None,
           'arm_check': None, 'error': None, 'final': '', 'max_turns': cfg['max_turns'],
           'max_budget_usd': cfg['max_budget_usd'], 'timeout_seconds': cfg['timeout'], 'cli': cfg['cli'],
           'provenance': dict(cfg['provenance'], task_tree=cfg['trees'][task['id']], arm_version=cfg['versions'][arm]),
           'env_passed': None, 'stopped_at': None, 'claim_reason': '', 'regression_passed': None,
           'changed_lines_py': None, 'transcript': None, 'contaminated': False, 'contaminated_by': None,
           'models': [], 'branch': None, 'worktrees': None, 'left_outside': None, 'warnings': []}
    errors = []
    # A top-level directory per session (mkdtemp: mode 700) whose name says nothing about the task or the arm. The
    # session sits two levels down, so its own surroundings hold no other session and no hidden tests.
    top = tempfile.mkdtemp(prefix='bench-')
    session = os.path.join(top, 's', 'project')
    try:
        graded = session_and_grade(cfg, task, arm, repeat, rec, errors, top, session)
    except Exception as e:  # one broken run must not stop the others
        errors.append('%s: %s' % (type(e).__name__, e))
        graded = False
    rec['error'] = '; '.join(errors) or None
    if not graded:
        rec['passed'] = None
    rec['false_done'] = rec['claim'] == 'DONE' and rec['passed'] is False
    if cfg['keep']:
        rec['session_dir'] = session
    else:
        shutil.rmtree(top, ignore_errors=True)
    name = '%s.%s.%d.json' % (task['id'], arm, repeat)
    with open(os.path.join(cfg['out'], name), 'w', encoding='utf-8') as f:
        json.dump(rec, f, indent=2)
        f.write('\n')
    return rec


def session_and_grade(cfg, task, arm, repeat, rec, errors, top, session):
    env, task_dir, arm_dir = cfg['env'], task['dir'], os.path.join(cfg['root'], 'arms', arm)
    private = os.path.join(top, 'private')  # the arm's per-session files outside the repository (a plugin copy)
    os.makedirs(private)
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
        return False
    git(session, env, 'add', '-A')
    git(session, env, 'commit', '-q', '--allow-empty', '-m', 'arm setup')
    base = git(session, env, 'rev-parse', 'HEAD')
    git(session, env, 'checkout', '-q', '-b', 'work')  # every arm starts here; no setup.sh makes a branch

    with open(os.path.join(arm_dir, 'prompt.md'), encoding='utf-8') as f:
        template = f.read()
    with open(os.path.join(task_dir, 'ticket.md'), encoding='utf-8') as f:
        prompt = template.replace('{ticket}', f.read().strip()).rstrip('\n') + '\n\n' + cfg['tail']
    agent = agent_env(os.environ, cfg['pass_env'], gitconfig)
    rec['env_passed'] = sorted(agent)
    started = time.time()
    if cfg['fake']:
        fake_env = dict(agent, BENCH_TASK=task['id'], BENCH_ARM=arm, BENCH_REPEAT=str(repeat), BENCH_TASK_DIR=task_dir)
        status, out, err = run(cfg['fake'], session, fake_env, cfg['timeout'], stdin=prompt)
    else:
        cmd = agent_command(prompt, cfg['model'], cfg['max_turns'], cfg['max_budget_usd'], session)
        status, out, err = run(cmd, session, agent, cfg['timeout'])
    rec['wall_seconds'] = round(time.time() - started, 1)
    rec['exit_status'] = status
    rec['transcript'] = '%s.%s.%d.transcript.jsonl' % (task['id'], arm, repeat)
    with open(os.path.join(cfg['out'], rec['transcript']), 'w', encoding='utf-8') as f:
        f.write(out)
    # A cap is the arm's own outcome and is graded; anything else without a clean result is the machine's failure
    # and enters no rate, so a rate limit or a crash never counts against an arm.
    result = parse_result(out) or {}
    if status is None:
        rec['stopped_at'] = 'timeout'
    elif result.get('subtype') in CAPS:
        rec['stopped_at'] = CAPS[result['subtype']]
    elif not result:
        errors.append('the agent printed no result object: %s' % (err or out).strip()[-300:])
    elif result.get('is_error') or str(result.get('subtype') or 'success') != 'success':
        errors.append('the agent reported %s: %s' % (
            'an error' if result.get('subtype') in (None, 'success') else result['subtype'],
            str(result.get('result') or result.get('errors') or '')[:300]))
    rec.update(cost_usd=result.get('total_cost_usd'), num_turns=result.get('num_turns'),
               duration_ms=result.get('duration_ms'), models=sorted(result.get('modelUsage') or {}))
    (rec['input_tokens'], rec['output_tokens'], rec['cache_read_tokens'],
     rec['cache_creation_tokens']) = tokens(result)
    final = result.get('result') if isinstance(result.get('result'), str) else ''
    rec['final'] = final
    rec['claim'], rec['claim_reason'] = parse_claim(final)
    hit = contamination(out, sorted({BENCH_REPO, cfg['root']}), tempfile.gettempdir(), top, cfg['cache'])
    rec['contaminated'], rec['contaminated_by'] = hit is not None, hit

    # The session is over and is never written again: what the arm runs afterwards and the grade each get a copy of
    # it, outside it, so neither can change the other and --keep keeps the tree exactly as the session left it.
    copies = [tempfile.mkdtemp(prefix='bench-'), tempfile.mkdtemp(prefix='bench-')]
    try:
        try:
            rec['changed_lines'], rec['files_changed'], rec['changed_lines_py'] = changed(session, env, base, copies[0])
            rec['branch'], rec['worktrees'], rec['left_outside'] = git_state(session, env)
        except RuntimeError as e:
            rec['warnings'].append('git state not measured: %s' % e)
        if errors:
            return False
        post_copy, grade_copy = (copy_of(session, d) for d in copies)
        post = os.path.join(arm_dir, 'post.sh')
        if os.path.isfile(post):
            rec['arm_check'] = run(['bash', post], post_copy, arm_env, POST_TIMEOUT)[0]
        return grade(task, grade_copy, env, rec)
    finally:
        for d in copies:
            shutil.rmtree(d, ignore_errors=True)


def copy_of(session, directory):
    copy = os.path.join(directory, 'project')
    shutil.copytree(session, copy, symlinks=True)
    return copy


def grade(task, copy, env, rec):
    """The grade, in copy G, the only place the hidden tests are ever copied to. First the visible tests as the task
    ships them replace whatever the session left (regression: behaviour the hidden tests may not cover), then the
    claim and final message are written and the hidden tests copied in."""
    shipped = os.path.join(task['dir'], 'repo', 'tests')
    if os.path.isdir(shipped):
        shutil.copytree(shipped, os.path.join(copy, 'tests'), dirs_exist_ok=True)
        status = run(['python3', '-m', 'unittest', 'discover', '-s', 'tests', '-q'], copy, env, GRADE_TIMEOUT)[0]
        rec['regression_passed'] = status == 0
        if status is None:
            rec['warnings'].append('the visible tests were stopped after %d seconds' % GRADE_TIMEOUT)
    os.makedirs(os.path.join(copy, '.bench'), exist_ok=True)
    with open(os.path.join(copy, '.bench', 'final.txt'), 'w', encoding='utf-8') as f:
        f.write(rec['final'] + '\n')
    with open(os.path.join(copy, '.bench', 'claim.json'), 'w', encoding='utf-8') as f:
        json.dump({'claim': rec['claim'], 'reason': rec['claim_reason']}, f)
    shutil.copytree(os.path.join(task['dir'], 'hidden'), copy, dirs_exist_ok=True)
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
    ap.add_argument('--max-budget-usd', type=float, default=4)
    ap.add_argument('--timeout', type=int, default=2400, help='seconds one session may take')
    ap.add_argument('--jobs', type=int, default=2, help='sessions at a time')
    ap.add_argument('--out', help='results directory (default: results/<UTC timestamp> beside this file)')
    ap.add_argument('--keep', action='store_true', help='keep the session directories')
    ap.add_argument('--dry-run', action='store_true', help='call no model: BENCH_FAKE_AGENT, or a do-nothing agent')
    ap.add_argument('--root', default=HERE, help='directory holding tasks/ and arms/ (default: beside this file)')
    ap.add_argument('--pass-env', nargs='+', default=[], metavar='NAME', help='more variables the agent may inherit')
    ap.add_argument('--allow-dirty', action='store_true', help='run a model even with uncommitted bench changes')
    a = ap.parse_args(argv)

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
        odd_py, odd_sha = odd_from_head(cache, env)
    except RuntimeError as e:
        sys.exit(str(e))
    try:
        cli = None if fake else (run(['claude', '--version'], tmp, env, 60)[1].strip() or None)
    except OSError:
        sys.exit('the claude command was not found; install it, or use --dry-run')
    cfg = {'root': root, 'out': out, 'cache': cache, 'env': env, 'fake': fake, 'keep': a.keep, 'cli': cli,
           'tail': tail, 'pass_env': a.pass_env, 'odd_py': odd_py,
           'provenance': {'bench_commit': commit, 'bench_dirty': dirty, 'odd_sha256': odd_sha},
           'trees': {t['id']: tree_hash(t['dir']) for t in tasks},
           'versions': {arm: first_line(os.path.join(root, 'arms', arm, 'VERSION')) for arm in arms},
           'model': 'none (fake agent)' if fake else a.model, 'max_turns': a.max_turns, 'max_budget_usd': a.max_budget_usd,
           'timeout': a.timeout, 'setup_locks': {arm: threading.Lock() for arm in arms}}

    todo = [(task, arm, n) for n in range(1, a.repeats + 1) for task in tasks for arm in arms]
    print('%d run(s): %d task(s) x %d arm(s) x %d repeat(s), %d at a time -> %s'
          % (len(todo), len(tasks), len(arms), a.repeats, a.jobs, out), flush=True)
    not_graded = 0
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=a.jobs)
    futures = [pool.submit(one_run, cfg, *job) for job in todo]
    try:
        for future in concurrent.futures.as_completed(futures):
            r = future.result()
            not_graded += r['passed'] is None
            print('%-28s %-12s %d  %-10s claim=%-8s %s%s' % (
                r['task'], r['arm'], r['repeat'],
                'not graded' if r['passed'] is None else 'passed' if r['passed'] else 'failed', r['claim'],
                '' if r['cost_usd'] is None else '$%.2f ' % r['cost_usd'], r['error'] or ''), flush=True)
    except KeyboardInterrupt:
        for future in futures:
            future.cancel()
        with LIVE_LOCK:
            for pid in list(LIVE):
                kill_group(pid)
        pool.shutdown(wait=True)
        print('interrupted: sessions stopped; results so far are in %s' % out, file=sys.stderr)
        return 130
    pool.shutdown(wait=True)
    if a.keep:
        print('session directories kept: each record names its own in session_dir')
    print('%d run(s) written to %s, %d not graded' % (len(todo), out, not_graded))
    return 1 if not_graded else 0


if __name__ == '__main__':
    sys.exit(main())
