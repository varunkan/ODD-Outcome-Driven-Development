#!/usr/bin/env python3
"""Does a reader made by `odd reread` behave like the second reading of the replay (evidence 26)?

The design is ruling-6 (docs/evidence/data/real/ruling-6.md). Only the reader is paid for: each host is a fix kept
from an earlier run, with its hidden grade. Per host and per arm (a reader model) `odd reread` runs once; every proof
it accepts is then run, with no model, on every host of the same task.

  rereadtest.py run --root ROOT --kept DIR --out DIR --odd-commit SHA [--cap 14.40] [--arms H,S] [--jobs 2] [--dry-run]
  rereadtest.py reader TRIAL_DIR PROMPT_FILE        (what `odd reread --by` runs, in the reader's clone)

ROOT holds tasks/<id>/ (repo/, env/, ticket.md, task.json, hidden/); --kept holds the kept runs' record folders
(real-out2, real-out3, six-C, six-M, six-S). --dry-run builds and checks every host and prints the list; that output
is committed before the first paid session.
"""
import argparse
import collections
import concurrent.futures
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import odd  # noqa: E402
from arm_agent import parse_result  # noqa: E402
from crosstest import split  # noqa: E402
from realtasks import grade_status  # noqa: E402
from run import PERMISSION_FLAGS, agent_env  # noqa: E402

MODELS = {'H': 'claude-haiku-4-5', 'S': 'claude-sonnet-5-5'}
SESSION_CAP, RESERVE, TURNS, SECONDS = 0.27, 0.30, 40, 900
SENTENCE = 'The behaviour the ticket asks for holds.'
o2, o3 = 'real-out2', 'real-out3'
HOSTS = (  # (task, record folder, arm of the kept run, W wrong or R right, core or extension), in the ruling's order
    ('sympy__sympy-12489', o2, 'odd-lean', 'W', 'core'), ('sympy__sympy-12489', o2, 'plain-tests', 'W', 'core'),
    ('sympy__sympy-12489', 'six-C', 'odd-lean', 'W', 'core'), ('sympy__sympy-12489', 'six-M', 'odd-lean', 'W', 'core'),
    ('sympy__sympy-12489', 'six-S', 'odd-lean', 'R', 'core'),
    ('sphinx-doc__sphinx-8265', o2, 'odd-lean', 'W', 'core'), ('sphinx-doc__sphinx-8265', 'six-C', 'odd-lean', 'W', 'core'),
    ('sphinx-doc__sphinx-8265', 'six-M', 'odd-lean', 'W', 'core'), ('sphinx-doc__sphinx-8265', 'six-S', 'odd-lean', 'R', 'core'),
    ('sympy__sympy-13615', o3, 'odd-lean', 'W', 'core'), ('sympy__sympy-13615', o3, 'plain-tests', 'W', 'core'),
    ('sympy__sympy-13615', 'six-C', 'odd-lean', 'R', 'core'), ('sympy__sympy-13615', 'six-M', 'odd-lean', 'R', 'core'),
    ('sympy__sympy-18698', o3, 'odd-lean', 'W', 'core'), ('sympy__sympy-18698', 'six-M', 'odd-lean', 'W', 'core'),
    ('sympy__sympy-18698', 'six-C', 'odd-lean', 'R', 'core'), ('sympy__sympy-18698', 'six-S', 'odd-lean', 'R', 'core'),
    ('sphinx-doc__sphinx-8638', o2, 'odd-lean', 'W', 'core'), ('sphinx-doc__sphinx-8638', 'six-C', 'odd-lean', 'W', 'core'),
    ('sphinx-doc__sphinx-8035', o2, 'odd-lean', 'R', 'core'), ('sphinx-doc__sphinx-9673', o3, 'plain-tests', 'R', 'core'),
    ('sympy__sympy-12419', o2, 'odd-lean', 'R', 'core'), ('sympy__sympy-13551', o2, 'odd-lean', 'R', 'core'),
    ('sympy__sympy-13647', o3, 'odd-lean', 'R', 'core'),
    ('sympy__sympy-13877', o3, 'odd-lean', 'R', 'extension'), ('sympy__sympy-16792', o3, 'odd-lean', 'R', 'extension'),
    ('sympy__sympy-18211', o3, 'odd-lean', 'R', 'extension'), ('sympy__sympy-19040', 'six-M', 'odd-lean', 'R', 'extension'),
    ('sympy__sympy-20154', o3, 'odd-lean', 'R', 'extension'), ('sympy__sympy-22914', o3, 'odd-lean', 'R', 'extension'),
    ('sympy__sympy-23262', o3, 'plain-tests', 'R', 'extension'), ('sympy__sympy-24066', o3, 'odd-lean', 'R', 'extension'),
)


def sh(cmd, cwd, env=None, timeout=900, **more):
    return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout, **more)


def name(host):
    return '%s.%s.%s' % (host[0].split('__')[-1], host[1], host[2])


def trial_env(env_copy, tmpdir, gitconfig, pythonpath=None):
    """run.py's agent environment with a copy of the task's own first on PATH, and no PYTHONPATH unless one is given:
    a path to the tree that holds the fix must never reach the reader."""
    os.makedirs(tmpdir, exist_ok=True)
    open(gitconfig, 'a').close()
    env = agent_env(os.environ, (), gitconfig, tmpdir)
    env.update(PATH=os.path.join(env_copy, 'bin') + os.pathsep + env.get('PATH', ''), VIRTUAL_ENV=env_copy,
               PYTHONDONTWRITEBYTECODE='1')
    env.pop('PYTHONPATH', None)
    return dict(env, PYTHONPATH=pythonpath) if pythonpath else env


def build_tree(task_dir, kept, dest):
    """The trial tree: the task's repo committed as `main`, then the kept run's changed test and product files laid
    over it, uncommitted, so no commit and no arm file (hooks, AGENTS.md) of the kept tree is in it.
    Returns (test files, product files)."""
    tests, product = split(kept, 'main')
    shutil.copytree(os.path.join(task_dir, 'repo'), dest, symlinks=True)
    git = ['git', '-c', 'user.name=bench', '-c', 'user.email=bench@localhost', '-c', 'commit.gpgsign=false']
    sh(git + ['init', '-q', '-b', 'main'], dest, check=True)
    sh(git + ['add', '-A'], dest, check=True)
    sh(git + ['commit', '-q', '--no-verify', '-m', 'the task'], dest, check=True)
    for p in tests + product:
        src, dst = os.path.join(kept, p), os.path.join(dest, p)
        if os.path.isfile(src):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(src, dst)
        elif os.path.lexists(dst):  # the kept run removed it
            os.remove(dst)
    return tests, product


def prepare(root, kept_dir, out, host):
    """Build and check one host (ruling, step 2). Returns its facts, with 'dropped' naming why it cannot be used."""
    task, folder, arm, kind, tier = host
    task_dir = os.path.join(root, 'tasks', task)
    with open(os.path.join(kept_dir, folder, '%s.%s.1.json' % (task, arm)), encoding='utf-8') as f:
        rec = json.load(f)
    h = dict(host=name(host), task=task, kind=kind, tier=tier, kept=rec['session_dir'], recorded_pass=rec['passed'])
    top = os.path.join(out, h['host'])
    shutil.rmtree(top, ignore_errors=True)
    os.makedirs(top)
    h['tree'], h['env'] = os.path.join(top, 'p0'), os.path.join(top, 'env')
    h['tests'], h['product'] = build_tree(task_dir, rec['session_dir'], h['tree'])
    shutil.copytree(os.path.join(task_dir, 'env'), h['env'], symlinks=True)
    if (kind == 'R') != rec['passed']:
        return dict(h, dropped='the list says %s and its record says passed=%s' % (kind, rec['passed']))
    if not h['product']:
        return dict(h, dropped='no product file changed')
    here = (rec['session_dir'].rstrip('/'), os.path.realpath(rec['session_dir']))
    if any(x in odd.read_text(os.path.join(h['tree'], t)) for t in h['tests'] for x in here):
        return dict(h, dropped='a test file names the kept tree')
    tests_cmd = odd.tests_proof(h['tree'], h['tests'])
    if not tests_cmd:
        return dict(h, dropped='no test of its own')
    h['proof'] = 'PYTHONPATH="$PWD" ' + tests_cmd
    env = trial_env(h['env'], os.path.join(top, 'tmp'), os.path.join(top, 'gitconfig'))
    rc, tail, _ = odd.run_proof(h['tree'], h['proof'], 900, env)
    if rc != 0:
        return dict(h, dropped='its own proof does not pass in the rebuilt tree (%s): %s' % (rc, odd.says(tail)))
    sh(['git', 'add', '-A'], h['tree'], check=True)
    patch = os.path.join(top, 'fix.patch')
    with open(patch, 'w', encoding='utf-8', errors='surrogateescape') as f:
        f.write(sh(['git', 'diff', '--cached', '--binary'], h['tree'], check=True).stdout)
    sh(['git', 'reset', '-q'], h['tree'], check=True)
    with open(os.path.join(task_dir, 'task.json'), encoding='utf-8') as f:
        grade = json.load(f)['grade']
    h['regraded_pass'] = grade_status(task_dir, grade, patch) == 0
    if h['regraded_pass'] != rec['passed']:
        return dict(h, dropped='its hidden grade, taken again, differs from its record')
    with open(os.path.join(top, 'ticket.md'), 'w', encoding='utf-8') as f:
        f.write(odd.read_text(os.path.join(task_dir, 'ticket.md')))
    return h


def reader(trial, prompt_file):
    """`odd reread --by`: one headless session in the reader's clone (the current directory), run.py's line. Its
    transcript and its cost go to the trial's folder; the line "odd-cost:" is what odd's own reports read."""
    model = os.environ['REREAD_MODEL']
    env = dict(os.environ, PYTHONPATH=os.getcwd())
    env.pop('REREAD_MODEL')
    with open(prompt_file, encoding='utf-8') as f:
        prompt = f.read()
    cmd = ['claude', '-p', prompt, '--model', model, '--output-format', 'stream-json', '--verbose', '--setting-sources',
           'project', '--strict-mcp-config', '--no-session-persistence', '--max-turns', str(TURNS), '--max-budget-usd',
           str(SESSION_CAP)] + PERMISSION_FLAGS
    path = os.path.join(trial, 'transcript.jsonl')
    with open(path, 'wb') as out:
        p = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT, env=env,
                             start_new_session=True)
        try:
            p.wait(timeout=SECONDS)
            timed_out = False
        except subprocess.TimeoutExpired:
            timed_out = True
        finally:
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except OSError:
                pass
            p.wait()
    with open(path, encoding='utf-8', errors='replace') as f:
        result = parse_result(f.read()) or {}
    cost = result.get('total_cost_usd')
    with open(os.path.join(trial, 'cost.json'), 'w') as f:
        json.dump(dict(cost_usd=cost, models=sorted(result.get('modelUsage') or {}), num_turns=result.get('num_turns'),
                       subtype=result.get('subtype'), timed_out=timed_out, clone=os.getcwd()), f)
    if cost is not None:
        print('odd-cost: %s' % cost)
    return 0


def verdict(rc, said):
    for words, v in (('two readings agree', 'agree'), ('one of the two readings is wrong', 'disagree'),
                     ('not compared', 'not compared')):
        if words in said:
            return v
    return 'could not run (exit %s)' % rc


def trial(root, out, odd_py, h, arm):
    """One paid session: `odd reread` on a copy of the host's tree (ruling, steps 5 to 8)."""
    top = os.path.join(out, h['host'], arm)
    os.makedirs(top)
    tree = os.path.join(top, 'p')
    shutil.copytree(h['tree'], tree, symlinks=True)
    env_copy = os.path.join(top, 'env')
    shutil.copytree(h['env'], env_copy, symlinks=True)
    os.makedirs(os.path.join(tree, '.odd', 'outcomes'))
    with open(os.path.join(tree, '.odd', 'outcomes', 'reread.md'), 'w', encoding='utf-8') as f:
        f.write('---\noutcome: %s\nproof: %s\nin: %s\n---\n' % (SENTENCE, h['proof'], ', '.join(h['product'])))
    env = dict(trial_env(env_copy, os.path.join(top, 'tmp'), os.path.join(top, 'gitconfig')), REREAD_MODEL=MODELS[arm])
    by = 'python3 %s reader %s {prompt_file}' % (shlex.quote(os.path.abspath(__file__)), shlex.quote(top))
    try:
        p = sh([sys.executable, odd_py, 'reread', 'reread', '--base', 'main', '--tries', '1', '--ticket',
                os.path.join(out, h['host'], 'ticket.md'), '--by', by], tree, env, timeout=SECONDS + 1500)
        rc, said = p.returncode, p.stdout + p.stderr
    except subprocess.TimeoutExpired:
        rc, said = None, 'the command did not end'
    with open(os.path.join(top, 'odd.txt'), 'w', encoding='utf-8') as f:
        f.write(said)
    cost = {}
    if os.path.isfile(os.path.join(top, 'cost.json')):
        with open(os.path.join(top, 'cost.json')) as f:
            cost = json.load(f)
    row = dict(kind='trial', host=h['host'], task=h['task'], fix=h['kind'], arm=arm, model=MODELS[arm], exit=rc,
               said=verdict(rc, said), why=next((l.strip()[:300] for l in said.splitlines() if 'not compared' in l), ''),
               cost_usd=cost.get('cost_usd'), models=cost.get('models'), num_turns=cost.get('num_turns'),
               subtype=cost.get('subtype'), reader_tests=[])
    patch = os.path.join(tree, '.git', 'odd', 'reread', 'reread', 'second-proof.patch')
    if os.path.isfile(patch):  # an accepted proof: its files, as written at the base
        shutil.copyfile(patch, os.path.join(top, 'second-proof.patch'))
        base = os.path.join(top, 'base')
        sh(['git', 'clone', '-q', '--no-hardlinks', tree, base], top, check=True)
        if sh(['git', 'apply', '--binary', os.path.join(top, 'second-proof.patch')], base).returncode == 0:
            files = [l for l in sh(['git', 'status', '--porcelain', '-uall'], base).stdout.splitlines()]
            for line in files:
                rel = line[3:]
                dst = os.path.join(top, 'reader-tests', rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copyfile(os.path.join(base, rel), dst)
                row['reader_tests'].append(rel)
        shutil.rmtree(base, ignore_errors=True)
    void = []
    transcript = odd.read_text(os.path.join(top, 'transcript.jsonl')) if os.path.isfile(os.path.join(top, 'transcript.jsonl')) else ''
    for what, needle in (('the trial tree', tree), ('the host tree', h['tree']), ('the kept tree', h['kept']),
                         ('the tasks folder', os.path.join(root, 'tasks')), ('tests_hidden', 'tests_hidden'),
                         ('solution.patch', 'solution.patch')):
        if needle in transcript:
            void.append('the transcript holds ' + what)
    if cost.get('models') and [m for m in cost['models'] if not m.startswith(MODELS[arm])]:
        void.append('another model ran: %s' % ', '.join(cost['models']))
    row['void'] = void
    clone = cost.get('clone') or '\0'
    row['reader_files_naming_a_run'] = [t for t in row['reader_tests'] if any(
        x in odd.read_text(os.path.join(top, 'reader-tests', t)) for x in (clone, 'odd-runs-'))]
    return row


def replay(out, hosts, row):
    """No model: one accepted reader proof on every host of its task (ruling, step 9)."""
    rows = []
    usable = [t for t in row['reader_tests'] if t not in row['reader_files_naming_a_run']]
    for h in [x for x in hosts if x['task'] == row['task']]:
        top = os.path.join(out, row['host'], row['arm'], 'on-' + h['host'])
        shutil.rmtree(top, ignore_errors=True)
        copy = os.path.join(top, 'p')
        shutil.copytree(h['tree'], copy, symlinks=True)
        for t in usable:
            os.makedirs(os.path.dirname(os.path.join(copy, t)), exist_ok=True)
            shutil.copyfile(os.path.join(out, row['host'], row['arm'], 'reader-tests', t), os.path.join(copy, t))
        cmd = odd.tests_proof(copy, usable)
        base = dict(kind='comparison', arm=row['arm'], reader_of=row['host'], fix_of=h['host'], task=h['task'],
                    fix=h['kind'], own=h['host'] == row['host'])
        if not cmd:
            rows.append(dict(base, result='not compared', said='no test file to run'))
        else:
            env = trial_env(h['env'], os.path.join(top, 'tmp'), os.path.join(top, 'gitconfig'))
            rc, tail, _ = odd.run_proof(copy, 'PYTHONPATH="$PWD" ' + cmd, 900, env)
            rows.append(dict(base, exit=rc, result={0: 'agree', 1: 'disagree'}.get(rc, 'not compared'),
                             said=odd.says(tail) if rc else ''))
        shutil.rmtree(copy, ignore_errors=True)
    return rows


def band(a, b, n_w, n_r, c, voids, tasks_caught):
    """The ruling's bands for one arm, from A and B as fractions."""
    if c > 1 / 3 or n_w < 26 or n_r < 15 or voids >= 3:
        return 'NOT TESTED'
    if a >= 0.60 and b <= 0.15 and tasks_caught >= 4:
        return 'BETTER'
    if a >= 0.40 and b <= 0.40 and a - b >= 0.15 and tasks_caught >= 3:
        return 'LIKE'
    return 'WORSE'


def summary(rows, arms):
    lines = []
    for arm in arms:
        trials = [r for r in rows if r['kind'] == 'trial' and r['arm'] == arm]
        ok = {r['host'] for r in trials if not r['void']}
        comps = [r for r in rows if r['kind'] == 'comparison' and r['arm'] == arm and r['reader_of'] in ok]
        w = [r for r in comps if r['fix'] == 'W' and r['result'] != 'not compared']
        rr = [r for r in comps if r['fix'] == 'R' and r['result'] != 'not compared']
        a, b = [sum(1 for r in x if r['result'] == 'disagree') for x in (w, rr)]
        none = sum(1 for r in trials if not r['reader_tests'])
        caught = len({r['task'] for r in w if r['result'] == 'disagree'})
        host = collections.Counter((r['fix'], r['said']) for r in trials if not r['void'])
        cost = [r['cost_usd'] for r in trials if r['cost_usd'] is not None]
        lines.append('arm %s (%s): %d sessions, %d void, %d with no accepted proof (C); wrong-fix comparisons %d, '
                     'disagree %d (A); right-fix comparisons %d, disagree %d (B); tasks with a catch %d; cost $%.2f '
                     '(%d sessions with a cost); band %s' % (
                         arm, MODELS[arm], len(trials), len(trials) - len(ok), none, len(w), a, len(rr), b, caught,
                         sum(cost), len(cost), band(a / len(w) if w else 0, b / len(rr) if rr else 0, len(w), len(rr),
                                                    none / len(trials) if trials else 1, len(trials) - len(ok), caught)))
        lines.append('   the command\'s own words on its host: %s' % ', '.join(
            '%s fix %s: %d' % (k[0], k[1], v) for k, v in sorted(host.items())))
    return lines


def run(a):
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    sha = sh(['git', 'rev-parse', '--verify', a.odd_commit + '^{commit}'], os.path.dirname(HERE), check=True).stdout.strip()
    odd_py = os.path.join(out, 'odd.py')
    with open(odd_py, 'w', encoding='utf-8') as f:
        f.write(sh(['git', 'show', sha + ':odd.py'], os.path.dirname(HERE), check=True).stdout)
    hosts = []
    for host in HOSTS:
        h = prepare(a.root, a.kept, out, host)
        print(json.dumps(dict(kind='host', **{k: h.get(k) for k in (
            'host', 'task', 'tier', 'recorded_pass', 'regraded_pass', 'tests', 'product', 'proof', 'dropped')})), flush=True)
        if not h.get('dropped'):
            hosts.append(h)
    core = [h for h in hosts if h['tier'] == 'core']
    print('hosts usable: %d core (%d wrong, %d right), %d extension; odd at %s; arms %s; cap $%.2f, $%.2f reserved a '
          'session' % (len(core), sum(h['kind'] == 'W' for h in core), sum(h['kind'] == 'R' for h in core),
                       len(hosts) - len(core), sha[:7], ','.join(a.arms), a.cap, RESERVE), flush=True)
    if a.dry_run:
        return 0
    lock, state, rows = threading.Lock(), dict(spent=0.0, held=0.0), []
    ledger = os.path.join(out, 'ledger.json')

    def paid(h, arm):
        row = trial(a.root, out, odd_py, h, arm)
        with lock:
            state['held'] -= RESERVE
            state['spent'] += row['cost_usd'] if row['cost_usd'] is not None else RESERVE
            with open(ledger, 'w') as f:
                json.dump(state, f)
        more = replay(out, hosts, row) if row['reader_tests'] and not row['void'] else []
        return [row] + more

    with concurrent.futures.ThreadPoolExecutor(a.jobs) as pool:
        waiting = []
        for h in hosts:  # the list's order; both arms of a host are one batch
            for arm in a.arms:
                while True:
                    with lock:
                        fits = a.cap - state['spent'] - state['held'] >= RESERVE - 1e-9
                        if fits:
                            state['held'] += RESERVE
                    if fits or not waiting:
                        break
                    concurrent.futures.wait([waiting.pop(0)])  # money comes back when a session ends under its reserve
                if not fits:
                    print(json.dumps(dict(kind='not started', host=h['host'], arm=arm, why='the cap')), flush=True)
                    continue
                waiting.append(pool.submit(paid, h, arm))
                waiting[-1].add_done_callback(lambda fut: [print(json.dumps(r), flush=True) or rows.append(r)
                                                           for r in fut.result()])
    for fut in waiting:  # a trial that broke is said, never lost
        if fut.exception() is not None:
            print(json.dumps(dict(kind='error', why=repr(fut.exception()))), flush=True)
    for line in summary(rows, a.arms):
        print(line)
    print('ledger: spent $%.2f of $%.2f' % (state['spent'], a.cap))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('run')
    s.add_argument('--root', required=True)
    s.add_argument('--kept', required=True)
    s.add_argument('--out', required=True)
    s.add_argument('--odd-commit', required=True)
    s.add_argument('--cap', type=float, default=14.40)
    s.add_argument('--arms', type=lambda v: v.split(','), default=['H', 'S'])
    s.add_argument('--jobs', type=int, default=2)
    s.add_argument('--dry-run', action='store_true')
    s = sub.add_parser('reader')
    s.add_argument('trial')
    s.add_argument('prompt_file')
    a = ap.parse_args(argv)
    return reader(a.trial, a.prompt_file) if a.cmd == 'reader' else run(a)


if __name__ == '__main__':
    sys.exit(main())
