#!/usr/bin/env python3
"""Run the comparison: every task x arm x repeat is one headless session, graded afterwards on hidden tests.

usage: run.py --model M [--tasks ID ...] [--arms ARM ...] [--repeats N] [--max-turns T] [--max-budget-usd B]
              [--timeout SECONDS] [--jobs J] [--out DIR] [--keep] [--dry-run]

One run, in this order:
  1. a fresh copy of tasks/<id>/repo in a session directory outside any git repository, committed as "start"
  2. arms/<arm>/setup.sh run there (env BENCH_CACHE, ODD_PY), committed as "arm setup"
  3. the agent, with arms/<arm>/prompt.md as the prompt ({ticket} replaced by the task's ticket.md)
  4. changed lines measured against the "arm setup" commit, in a scratch index so the tree is left as the session left it
  5. arms/<arm>/post.sh, when the arm has one: its exit status is recorded as the arm's own check
  6. the final message written to .bench/final.txt, and the claim read from its last line starting with RESULT:
  7. only now tasks/<id>/hidden copied in and the task's grade command run
Writes <out>/<task>.<arm>.<n>.json. SPEC.md is the contract; RUNNER-NOTES.md explains the permission flags.

No model is called with --dry-run, or when BENCH_FAKE_AGENT is set to a command. That command runs in the session
directory with the prompt on stdin and must print a JSON object with a "result" string (optional: total_cost_usd,
usage, num_turns, duration_ms). It is also given BENCH_TASK, BENCH_ARM, BENCH_REPEAT and BENCH_TASK_DIR; a real
agent never is. --dry-run alone uses a built-in agent that changes nothing and answers NOT DONE.

exit 0 when every run was graded, 1 when any run could not be (its JSON names the error), 2 on bad arguments.
"""
import argparse
import concurrent.futures
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
ODD_PY = os.path.abspath(os.path.join(HERE, '..', 'odd.py'))
GIT = ['git', '-c', 'user.name=bench', '-c', 'user.email=bench@example.com']
# What lets a headless session edit files and run commands in its directory. Evidence: RUNNER-NOTES.md.
PERMISSION_FLAGS = ['--permission-mode', 'acceptEdits', '--permission-prompts', 'none',
                    '--allowedTools', 'Bash,Read,Glob,Grep,Skill']
SETUP_TIMEOUT, POST_TIMEOUT, GRADE_TIMEOUT = 900, 300, 180
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


def parse_claim(final):
    """DONE, NOT DONE or none, from the LAST line that starts with RESULT: (spaces and Markdown emphasis ignored)."""
    for line in reversed(final.splitlines()):
        line = line.strip().strip('*`_').strip()
        if line.startswith('RESULT:'):
            said = line[len('RESULT:'):].strip()
            return 'NOT DONE' if re.match(r'NOT DONE\b', said) else 'DONE' if re.match(r'DONE\b', said) else 'none'
    return 'none'


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
    cmd = ['claude', '-p', prompt, '--model', model, '--output-format', 'json', '--setting-sources', 'project',
           '--strict-mcp-config', '--max-turns', str(max_turns), '--max-budget-usd', str(max_budget_usd)]
    cmd += PERMISSION_FLAGS
    marker = os.path.join(session, '.bench-plugin-dir')
    if os.path.isfile(marker):
        with open(marker, encoding='utf-8') as f:
            cmd += ['--plugin-dir', f.read().strip()]
    return cmd


def changed(session, env, base, scratch):
    """(lines, files) that differ from the arm-setup commit, .bench/ excluded: git add -A, then diff --shortstat,
    in a scratch index seeded from that commit, so the session's own index and tree stay as it left them."""
    env = dict(env, GIT_INDEX_FILE=os.path.join(scratch, 'index'))
    git(session, env, 'read-tree', base)
    git(session, env, 'add', '-A')
    stat = git(session, env, 'diff', '--cached', '--shortstat', base, '--', '.', ':(exclude).bench')
    n = {word: int(count) for count, word in re.findall(r'(\d+) (file|insertion|deletion)', stat)}
    return n.get('insertion', 0) + n.get('deletion', 0), n.get('file', 0)


def one_run(cfg, task, arm, repeat):
    """One task x arm x repeat. Never raises: whatever goes wrong is named in the record's "error"."""
    rec = {'task': task['id'], 'arm': arm, 'repeat': repeat, 'model': cfg['model'], 'kind': task.get('kind'),
           'size': task.get('size'), 'expect': task.get('expect'), 'passed': None, 'claim': 'none',
           'false_done': False, 'cost_usd': None, 'input_tokens': None, 'output_tokens': None,
           'cache_read_tokens': None, 'cache_creation_tokens': None, 'num_turns': None, 'duration_ms': None,
           'wall_seconds': None, 'changed_lines': None, 'files_changed': None, 'exit_status': None,
           'arm_check': None, 'error': None, 'final': '', 'max_turns': cfg['max_turns'],
           'max_budget_usd': cfg['max_budget_usd'], 'timeout_seconds': cfg['timeout'], 'cli': cfg['cli']}
    errors = []
    scratch = tempfile.mkdtemp(prefix='r', dir=cfg['tmp'])  # the name says nothing about the task or the arm
    session = os.path.join(scratch, 'project')
    try:
        graded = session_and_grade(cfg, task, arm, repeat, rec, errors, scratch, session)
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
        shutil.rmtree(scratch, ignore_errors=True)
    name = '%s.%s.%d.json' % (task['id'], arm, repeat)
    with open(os.path.join(cfg['out'], name), 'w', encoding='utf-8') as f:
        json.dump(rec, f, indent=2)
        f.write('\n')
    return rec


def session_and_grade(cfg, task, arm, repeat, rec, errors, scratch, session):
    env, task_dir, arm_dir = cfg['env'], task['dir'], os.path.join(cfg['root'], 'arms', arm)
    arm_env = dict(env, BENCH_CACHE=cfg['cache'], ODD_PY=ODD_PY)

    shutil.copytree(os.path.join(task_dir, 'repo'), session)
    git(session, env, 'init', '-q', '-b', 'main')
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

    with open(os.path.join(arm_dir, 'prompt.md'), encoding='utf-8') as f:
        template = f.read()
    with open(os.path.join(task_dir, 'ticket.md'), encoding='utf-8') as f:
        prompt = template.replace('{ticket}', f.read().strip())
    started = time.time()
    if cfg['fake']:
        fake_env = dict(env, BENCH_TASK=task['id'], BENCH_ARM=arm, BENCH_REPEAT=str(repeat), BENCH_TASK_DIR=task_dir)
        status, out, err = run(cfg['fake'], session, fake_env, cfg['timeout'], stdin=prompt)
    else:
        cmd = agent_command(prompt, cfg['model'], cfg['max_turns'], cfg['max_budget_usd'], session)
        status, out, err = run(cmd, session, env, cfg['timeout'])
    rec['wall_seconds'] = round(time.time() - started, 1)
    rec['exit_status'] = status
    if status is None:
        errors.append('the agent was stopped after %d seconds' % cfg['timeout'])
    result = parse_result(out)
    if result is None:
        errors.append('the agent printed no result object: %s' % (err or out).strip()[-300:])
        result = {}
    elif result.get('is_error') or str(result.get('subtype') or 'success') != 'success':
        errors.append('the agent reported %s' % (result.get('subtype') or 'an error'))
    rec.update(cost_usd=result.get('total_cost_usd'), num_turns=result.get('num_turns'),
               duration_ms=result.get('duration_ms'))
    (rec['input_tokens'], rec['output_tokens'], rec['cache_read_tokens'],
     rec['cache_creation_tokens']) = tokens(result)
    final = result.get('result') if isinstance(result.get('result'), str) else ''
    rec['final'], rec['claim'] = final, parse_claim(final)

    try:
        rec['changed_lines'], rec['files_changed'] = changed(session, env, base, scratch)
    except RuntimeError as e:
        errors.append('changed lines not measured: %s' % e)
    post = os.path.join(arm_dir, 'post.sh')
    if os.path.isfile(post):
        rec['arm_check'] = run(['bash', post], session, arm_env, POST_TIMEOUT)[0]
    os.makedirs(os.path.join(session, '.bench'), exist_ok=True)
    with open(os.path.join(session, '.bench', 'final.txt'), 'w', encoding='utf-8') as f:
        f.write(final + '\n')

    # Only now, with the session over and measured, do the hidden tests enter its directory.
    shutil.copytree(os.path.join(task_dir, 'hidden'), session, dirs_exist_ok=True)
    status, out, err = run(task['grade'], session, env, GRADE_TIMEOUT)
    if status is None:
        errors.append('grade was stopped after %d seconds' % GRADE_TIMEOUT)
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
    a = ap.parse_args(argv)

    fake = os.environ.get('BENCH_FAKE_AGENT') or (DRY_AGENT if a.dry_run else None)
    if not fake and not a.model:
        ap.error('--model is required unless --dry-run')
    root = os.path.abspath(a.root)
    all_tasks = names_in(os.path.join(root, 'tasks'), ('task.json', 'ticket.md', 'repo', 'hidden'))
    all_arms = names_in(os.path.join(root, 'arms'), ('setup.sh', 'prompt.md'))
    unknown = [t for t in a.tasks or [] if t not in all_tasks] + [x for x in a.arms or [] if x not in all_arms]
    if unknown or not all_tasks or not all_arms or a.repeats < 1 or a.jobs < 1:
        ap.error('unknown or incomplete task or arm: %s' % ', '.join(unknown) if unknown
                 else 'need at least one task, one arm, one repeat and one job')
    tasks = []
    for tid in a.tasks or all_tasks:
        with open(os.path.join(root, 'tasks', tid, 'task.json'), encoding='utf-8') as f:
            tasks.append(dict(json.load(f), id=tid, dir=os.path.join(root, 'tasks', tid)))
    arms = a.arms or all_arms

    env = {k: v for k, v in os.environ.items() if k not in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE')}
    tmp = tempfile.mkdtemp(prefix='ws-')
    if run(['git', 'rev-parse', '--show-toplevel'], tmp, env, 60)[0] == 0:
        shutil.rmtree(tmp, ignore_errors=True)
        sys.exit('the temporary directory %s is inside a git repository; set TMPDIR to one that is not' % tmp)
    out = os.path.abspath(a.out or os.path.join(HERE, 'results', time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())))
    cache = os.environ.get('BENCH_CACHE') or os.path.join(tempfile.gettempdir(), 'bench-cache')
    os.makedirs(out, exist_ok=True)
    os.makedirs(cache, exist_ok=True)
    try:
        cli = None if fake else (run(['claude', '--version'], tmp, env, 60)[1].strip() or None)
    except OSError:
        shutil.rmtree(tmp, ignore_errors=True)
        sys.exit('the claude command was not found; install it, or use --dry-run')
    cfg = {'root': root, 'out': out, 'tmp': tmp, 'cache': cache, 'env': env, 'fake': fake, 'keep': a.keep, 'cli': cli,
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
        print('session directories kept under %s' % tmp)
    else:
        shutil.rmtree(tmp, ignore_errors=True)
    print('%d run(s) written to %s, %d not graded' % (len(todo), out, not_graded))
    return 1 if not_graded else 0


if __name__ == '__main__':
    sys.exit(main())
