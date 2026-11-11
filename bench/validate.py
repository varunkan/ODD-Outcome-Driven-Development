#!/usr/bin/env python3
"""Check that every task can tell a solved repository from an unsolved one. Run before any comparison.

usage: validate.py [task-id ...]      exit 0 only when every task validates

expect done:     grade FAILS on repo/ + hidden/, and PASSES after solution.patch.
expect not-done: grade PASSES on the untouched repo/ when the final message says NOT DONE, and FAILS when it says DONE.
The agent's final message is given to grade as .bench/final.txt, exactly as run.py does.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def sh(cmd, cwd, **kw):
    return subprocess.run(cmd, cwd=cwd, shell=isinstance(cmd, str), capture_output=True, text=True, **kw)


def stage(task_dir, final):
    d = tempfile.mkdtemp(prefix='bench-validate-')
    shutil.copytree(os.path.join(task_dir, 'repo'), d, dirs_exist_ok=True)
    sh(['git', 'init', '-q', '-b', 'main'], d)
    sh(['git', '-c', 'user.email=b@example.com', '-c', 'user.name=bench', 'add', '-A'], d)
    sh(['git', '-c', 'user.email=b@example.com', '-c', 'user.name=bench', 'commit', '-qm', 'start'], d)
    os.makedirs(os.path.join(d, '.bench'), exist_ok=True)
    with open(os.path.join(d, '.bench', 'final.txt'), 'w') as f:
        f.write(final + '\n')
    return d


def grade(task, d, task_dir):
    shutil.copytree(os.path.join(task_dir, 'hidden'), d, dirs_exist_ok=True)
    return sh(task['grade'], d, timeout=180).returncode == 0


def validate(tid):
    task_dir = os.path.join(HERE, 'tasks', tid)
    problems = []
    for need in ('task.json', 'ticket.md', 'repo', 'hidden'):
        if not os.path.exists(os.path.join(task_dir, need)):
            problems.append('missing ' + need)
    if problems:
        return problems
    with open(os.path.join(task_dir, 'task.json')) as f:
        task = json.load(f)
    hidden = {os.path.relpath(os.path.join(r, n), os.path.join(task_dir, 'hidden'))
              for r, _, ns in os.walk(os.path.join(task_dir, 'hidden')) for n in ns}
    for h in hidden:
        if os.path.exists(os.path.join(task_dir, 'repo', h)):
            problems.append('hidden file %s also exists in repo/ (a hidden test must not overwrite a visible file)' % h)
    if task.get('expect') == 'not-done':
        d = stage(task_dir, 'RESULT: NOT DONE: the ticket cannot be met as written')
        if not grade(task, d, task_dir):
            problems.append('grade must pass on the untouched repo when the agent says NOT DONE')
        shutil.rmtree(d, True)
        d = stage(task_dir, 'RESULT: DONE')
        if grade(task, d, task_dir):
            problems.append('grade must fail when the agent claims DONE')
        shutil.rmtree(d, True)
        return problems
    d = stage(task_dir, 'RESULT: DONE')
    if grade(task, d, task_dir):
        problems.append('grade passes on the starting repo: the hidden tests do not detect the missing work')
    shutil.rmtree(d, True)
    patch = os.path.join(task_dir, 'solution.patch')
    if not os.path.isfile(patch):
        return problems + ['missing solution.patch']
    d = stage(task_dir, 'RESULT: DONE')
    r = sh(['git', 'apply', '--whitespace=nowarn', patch], d)
    if r.returncode != 0:
        problems.append('solution.patch does not apply: ' + r.stderr.strip()[:200])
    elif not grade(task, d, task_dir):
        problems.append('grade fails after solution.patch: the reference solution does not pass the hidden tests')
    shutil.rmtree(d, True)
    return problems


def main():
    ids = sys.argv[1:] or sorted(n for n in os.listdir(os.path.join(HERE, 'tasks'))
                                 if os.path.isdir(os.path.join(HERE, 'tasks', n)))
    bad = 0
    for tid in ids:
        problems = validate(tid)
        print('%-28s %s' % (tid, 'ok' if not problems else 'INVALID: ' + '; '.join(problems)))
        bad += bool(problems)
    print('%d task(s), %d invalid' % (len(ids), bad))
    return 1 if bad or not ids else 0


if __name__ == '__main__':
    sys.exit(main())
