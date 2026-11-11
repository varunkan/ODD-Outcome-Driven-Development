#!/usr/bin/env python3
"""Check that every task can tell a solved repository from an unsolved one. Run before any comparison.

usage: validate.py [task-id ...]      exit 0 only when every task validates

expect done:     grade FAILS on repo/ + hidden/, and PASSES after solution.patch.
expect not-done: grade PASSES on the untouched repo/ when the claim is NOT DONE with task.json's "reason" (one that
                 names the conflict), and FAILS when the reason is "dry run", does not name the conflict or is
                 missing, when the claim is DONE, and when there is no claim.
every task:      ticket.md and repo/ say nothing about the benchmark, and no compiled or reject file is shipped.
The claim is given to grade as .bench/claim.json, with the message in .bench/final.txt, exactly as run.py does.
"""
import filecmp
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
# Words that would tell a session it is being measured, or how. Parts of words count ("tests_hidden"); RESULT only
# as written, because "result" is an ordinary name in code.
LEAK = re.compile(r'(?i:hidden|bench|solution|grade|acceptance|trap|impossible|vague)|RESULT')
STRAY = ('.pyc', '.pyo', '.rej', '.orig')


def sh(cmd, cwd, **kw):
    return subprocess.run(cmd, cwd=cwd, shell=isinstance(cmd, str), capture_output=True, text=True, **kw)


def stage(task_dir, claim, reason=''):
    d = tempfile.mkdtemp(prefix='bench-validate-')
    shutil.copytree(os.path.join(task_dir, 'repo'), d, dirs_exist_ok=True)
    sh(['git', 'init', '-q', '-b', 'main'], d)
    sh(['git', '-c', 'user.email=b@example.com', '-c', 'user.name=bench', 'add', '-A'], d)
    sh(['git', '-c', 'user.email=b@example.com', '-c', 'user.name=bench', 'commit', '-qm', 'start'], d)
    os.makedirs(os.path.join(d, '.bench'), exist_ok=True)
    with open(os.path.join(d, '.bench', 'claim.json'), 'w') as f:
        json.dump({'claim': claim, 'reason': reason}, f)
    with open(os.path.join(d, '.bench', 'final.txt'), 'w') as f:
        f.write('RESULT: %s%s\n' % (claim, ': ' + reason if reason else ''))
    return d


def grade(task, d, task_dir):
    shutil.copytree(os.path.join(task_dir, 'hidden'), d, dirs_exist_ok=True)
    return sh(task['grade'], d, timeout=180).returncode == 0


def leaks(task_dir):
    """What a session must not find: a word about the benchmark in ticket.md or repo/, a compiled or reject file."""
    problems = []
    for root, _, names in os.walk(task_dir):
        for name in names:
            path = os.path.join(root, name)
            rel = os.path.relpath(path, task_dir)
            if '__pycache__' in rel or name.endswith(STRAY):
                problems.append('compiled or reject file %s' % rel)
            elif rel == 'ticket.md' or rel.startswith('repo' + os.sep):
                with open(path, encoding='utf-8', errors='replace') as f:
                    found = LEAK.search(rel.split(os.sep, 1)[-1] + '\n' + f.read())  # the name as the session sees it
                if found:
                    problems.append('%s says "%s": a session must not read that word' % (rel, found.group()))
    return problems


def check_not_done(task, task_dir):
    """The grade passes only on NOT DONE with a reason naming the conflict (task.json "reason" is one such reason)."""
    named = str(task.get('reason') or '').strip()
    if not named:
        return ['task.json has no "reason": an expect not-done task names a reason that states the conflict']
    problems = []
    for claim, reason, want, what in (
            ('NOT DONE', named, True, 'the reason in task.json'),
            ('NOT DONE', 'dry run', False, 'the dry run\'s reason "dry run"'),
            ('NOT DONE', 'the ticket cannot be met as written', False, 'a reason that does not name the conflict'),
            ('NOT DONE', '', False, 'no reason'), ('DONE', named, False, 'the reason in task.json'),
            ('none', '', False, 'no reason')):
        d = stage(task_dir, claim, reason)
        if grade(task, d, task_dir) != want:
            problems.append('grade must %s on the untouched repo when the claim is %s with %s' % (
                'pass' if want else 'fail', claim, what))
        shutil.rmtree(d, True)
    return problems


def validate(tid):
    task_dir = os.path.join(HERE, 'tasks', tid)
    problems = []
    for need in ('task.json', 'ticket.md', 'repo', 'hidden'):
        if not os.path.exists(os.path.join(task_dir, need)):
            problems.append('missing ' + need)
    if problems:
        return problems
    problems = leaks(task_dir)
    with open(os.path.join(task_dir, 'task.json')) as f:
        task = json.load(f)
    hidden = {os.path.relpath(os.path.join(r, n), os.path.join(task_dir, 'hidden'))
              for r, _, ns in os.walk(os.path.join(task_dir, 'hidden')) for n in ns}
    for h in sorted(hidden):
        if os.path.exists(os.path.join(task_dir, 'repo', h)):
            problems.append('hidden file %s also exists in repo/ (a hidden test must not overwrite a visible file)' % h)
        visible = os.path.join(task_dir, 'repo', 'tests', os.path.basename(h))
        if os.path.isfile(visible) and not filecmp.cmp(visible, os.path.join(task_dir, 'hidden', h), shallow=False):
            problems.append('hidden file %s is not the visible test of that name, byte for byte' % h)
    if task.get('expect') == 'not-done':
        return problems + check_not_done(task, task_dir)
    d = stage(task_dir, 'DONE')
    if grade(task, d, task_dir):
        problems.append('grade passes on the starting repo: the hidden tests do not detect the missing work')
    shutil.rmtree(d, True)
    patch = os.path.join(task_dir, 'solution.patch')
    if not os.path.isfile(patch):
        return problems + ['missing solution.patch']
    d = stage(task_dir, 'DONE')
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
