#!/usr/bin/env python3
"""Build comparison tasks from real open-source issues (SWE-bench Lite), for BACKLOG item 18.

usage: realtasks.py --rows DIR --out ROOT [--strict] [--want N] [--python X.Y] ID [ID ...]

DIR holds the SWE-bench Lite rows as fetched from the Hugging Face datasets server (rows*.json). For each instance ID
this writes ROOT/tasks/<id>/ in the harness's task format: repo/ (the project at the issue's base commit, without its
git history), ticket.md (the issue text, as its reporter wrote it), hidden/tests_hidden/ (the test file as the real
fix's test patch leaves it), solution.patch (the real fix) and task.json (grade: pytest on that whole file, so its
other tests catch a regression the way SWE-bench's same-file PASS_TO_PASS tests do, less any test the real fix itself
fails on this machine, such as one needing an optional package that is not installed: a test the reference fix cannot
pass checks nothing). With --strict such a task is refused instead (the rule for SWE-bench Verified tasks, whose tests
people checked against the issue: a trimmed file is no longer that check). With --want N the IDs are candidates in the
order given and building stops once N tasks are kept, so the selection is fixed before any task is tried.

With --python X.Y (BACKLOG item 42) each task gets its own environment, ROOT/tasks/<id>/env: that Python (fetched by
uv), pytest, and the project's own dependencies at the issue's commit, without the project itself, so the code under
test is always the tree in front of the test and never an installed copy. The grade then runs with env/bin first on
PATH (task_environ), the way SWE-bench gives every instance its own environment. The hidden test then comes with its whole test
directory, so that directory's conftest files and test data apply to it. ROOT/arms/ is copied from this directory, so `run.py --root ROOT` runs the usual arms on these tasks.

Each task is validated here, because validate.py's leak check rejects any real codebase (its code says "result",
"hidden" and "solution"): the grade must FAIL on repo/ and PASS after solution.patch. A task that does not is left out
and named. Nothing is committed: the repositories are large; this script is how to rebuild them.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def sh(cmd, cwd, check=True, **kw):
    r = subprocess.run(cmd, cwd=cwd, shell=isinstance(cmd, str), capture_output=True, text=True, **kw)
    if check and r.returncode:
        raise RuntimeError('%s: %s' % (cmd if isinstance(cmd, str) else ' '.join(cmd), (r.stderr or r.stdout)[-400:]))
    return r


def rows(folder):
    out = {}
    for name in sorted(os.listdir(folder)):
        if name.startswith('rows') and name.endswith('.json'):
            with open(os.path.join(folder, name), encoding='utf-8') as f:
                for r in json.load(f)['rows']:
                    out[r['row']['instance_id']] = r['row']
    return out


def checkout(repo, commit, dest):
    os.makedirs(dest)
    sh(['git', 'init', '-q'], dest)
    sh(['git', 'fetch', '-q', '--depth', '1', 'https://github.com/%s' % repo, commit], dest, timeout=900)
    sh(['git', 'checkout', '-q', 'FETCH_HEAD'], dest)
    shutil.rmtree(os.path.join(dest, '.git'))


def task_environ(task_dir, environ=None):
    """The environment a task's commands run in: `environ` with the task's own env/bin first on PATH when the task was
    built with --python, else unchanged."""
    env = dict(os.environ if environ is None else environ)
    bin_dir = os.path.join(task_dir, 'env', 'bin')
    if os.path.isdir(bin_dir):
        env['PATH'] = bin_dir + os.pathsep + env.get('PATH', '')
        env['VIRTUAL_ENV'] = os.path.dirname(bin_dir)
        if os.path.isdir(os.path.join(task_dir, 'repo', 'src')):  # a src layout: the tree's package, not an installed one
            env['PYTHONPATH'] = os.pathsep.join(['src'] + [x for x in [env.get('PYTHONPATH')] if x])
    return env


def make_env(task_dir, python, before=None):
    """ROOT/tasks/<id>/env: `python`, pytest and the project's dependencies, each in the newest version published by
    `before` (the day the issue was filed), since a project of that day breaks on later releases of what it uses. The
    project is installed to resolve its dependencies and then taken out again, and what that install wrote into
    repo/ is removed."""
    repo, env = os.path.join(task_dir, 'repo'), os.path.join(task_dir, 'env')
    had = set(os.listdir(repo))
    sh(['uv', 'venv', '-q', '--python', python, env], task_dir, timeout=900)
    py = os.path.join(env, 'bin', 'python')
    dated = ['--exclude-newer', before] if before else []
    # setuptools below 81 still ships pkg_resources, which projects of these years import at run time
    sh(['uv', 'pip', 'install', '-q', '--python', py] + dated + ['pytest', 'setuptools<81'], task_dir, timeout=900)
    # not editable: build tools of the issue's day cannot build an editable install
    sh(['uv', 'pip', 'install', '-q', '--python', py] + dated + [repo], task_dir, timeout=1800,
       env=dict(os.environ, SETUPTOOLS_SCM_PRETEND_VERSION='0.0.0'))  # no git history here to read a version from
    names = sh([py, '-c', 'import importlib.metadata as m\nfor d in m.distributions():\n'
                '    if d.read_text("direct_url.json"): print(d.metadata["Name"])'], task_dir).stdout.split()
    if names:
        sh(['uv', 'pip', 'uninstall', '-q', '--python', py] + names, task_dir, timeout=300)
    for name in set(os.listdir(repo)) - had:  # egg-info, build/: not part of the project at that commit
        path = os.path.join(repo, name)
        shutil.rmtree(path, ignore_errors=True) if os.path.isdir(path) else os.remove(path)


def grade_status(task_dir, grade, patch=None, out=None):
    """The grade's exit status on a copy of repo/ with the hidden tests in, and `patch` applied first if given; with a
    list as `out`, the names of the tests that failed or errored are appended to it."""
    work = tempfile.mkdtemp(prefix='realtask-')
    try:
        copy = os.path.join(work, 'p')
        shutil.copytree(os.path.join(task_dir, 'repo'), copy, symlinks=True)
        if patch:
            sh(['git', 'apply', '--whitespace=nowarn', patch], copy)
        shutil.copytree(os.path.join(task_dir, 'hidden', 'tests_hidden'), os.path.join(copy, 'tests_hidden'))
        r = sh(grade + (' -rfE' if out is not None else ''), copy, check=False, timeout=900, env=task_environ(task_dir))
        if out is not None:
            out += re.findall(r'^(?:FAILED|ERROR) \S+::(\w+)', r.stdout, re.M)
        return r.returncode
    finally:
        shutil.rmtree(work, ignore_errors=True)


def build(row, root, strict=False, python=None):
    iid = row['instance_id']
    task_dir = os.path.join(root, 'tasks', iid)
    shutil.rmtree(task_dir, ignore_errors=True)
    files = re.findall(r'^\+\+\+ b/(\S+)', row['test_patch'], re.M)
    if len(files) != 1:
        return 'needs exactly one test file, has %d' % len(files)
    repo = os.path.join(task_dir, 'repo')
    checkout(row['repo'], row['base_commit'], repo)
    if python:
        make_env(task_dir, python, row.get('created_at'))
    # the hidden test: the test file as the real fix's test patch leaves it, applied to a scratch copy only
    scratch = tempfile.mkdtemp(prefix='realtask-test-')
    try:
        target, folder = os.path.join(scratch, files[0]), os.path.dirname(files[0])
        if python and folder:  # the whole test directory, so its conftest files and test data apply to the hidden test
            shutil.copytree(os.path.join(repo, folder), os.path.join(scratch, folder), symlinks=True)
        else:
            os.makedirs(os.path.dirname(target), exist_ok=True)  # a test file at the project root lives in scratch itself
            if os.path.exists(os.path.join(repo, files[0])):
                shutil.copy2(os.path.join(repo, files[0]), target)
        with open(os.path.join(scratch, 'test.patch'), 'w', encoding='utf-8') as f:
            f.write(row['test_patch'])
        sh(['git', 'apply', '--whitespace=nowarn', 'test.patch'], scratch)
        if python and folder:
            shutil.copytree(os.path.join(scratch, folder), os.path.join(task_dir, 'hidden', 'tests_hidden'), symlinks=True)
        else:
            os.makedirs(os.path.join(task_dir, 'hidden', 'tests_hidden'))
            shutil.copy2(target, os.path.join(task_dir, 'hidden', 'tests_hidden', os.path.basename(files[0])))
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    grade = 'python3 -m pytest -q -p no:cacheprovider tests_hidden/%s' % os.path.basename(files[0])
    with open(os.path.join(task_dir, 'solution.patch'), 'w', encoding='utf-8') as f:
        f.write(row['patch'])
    with open(os.path.join(task_dir, 'ticket.md'), 'w', encoding='utf-8') as f:
        f.write(row['problem_statement'].strip() + '\n')
    fix, broken = os.path.join(task_dir, 'solution.patch'), []
    if grade_status(task_dir, grade, fix, broken) != 0:
        target = {t.split('::')[-1].split('[')[0] for t in json.loads(row['FAIL_TO_PASS'])}
        if strict or not broken or target & set(broken):
            return 'the grade fails after the real fix (%s)' % (', '.join(broken[:6]) or 'no test named')
        grade += ' -k "not (%s)"' % ' or '.join(dict.fromkeys(broken))
    with open(os.path.join(task_dir, 'task.json'), 'w', encoding='utf-8') as f:
        json.dump({'id': iid, 'size': 'large', 'kind': 'real', 'grade': grade, 'expect': 'done',
                   'source': 'SWE-bench Lite %s (%s at %s)' % (iid, row['repo'], row['base_commit'][:12])}, f, indent=2)
    if grade_status(task_dir, grade) == 0:
        return 'the grade passes before the fix'
    if grade_status(task_dir, grade, fix) != 0:
        return 'the grade fails after the real fix'
    return ''


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--rows', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--strict', action='store_true', help='refuse a task whose whole test file fails after the real fix')
    ap.add_argument('--want', type=int, help='stop once this many tasks are kept, trying the IDs in order')
    ap.add_argument('--python', help='give each task its own environment with this Python version, e.g. 3.9')
    ap.add_argument('ids', nargs='+')
    a = ap.parse_args(argv)
    found = rows(a.rows)
    os.makedirs(os.path.join(a.out, 'tasks'), exist_ok=True)
    shutil.rmtree(os.path.join(a.out, 'arms'), ignore_errors=True)
    shutil.copytree(os.path.join(HERE, 'arms'), os.path.join(a.out, 'arms'))
    bad = kept = 0
    for iid in a.ids:
        if a.want and kept >= a.want:
            break
        if iid not in found:
            print('%s: not in the rows' % iid)
            bad += 1
            continue
        try:
            why = build(found[iid], a.out, a.strict, a.python)
        except (RuntimeError, subprocess.TimeoutExpired) as e:
            why = str(e)
        if why:
            shutil.rmtree(os.path.join(a.out, 'tasks', iid), ignore_errors=True)
            bad += 1
        else:
            kept += 1
        grade = '' if why else json.load(open(os.path.join(a.out, 'tasks', iid, 'task.json')))['grade']
        print('%s: %s' % (iid, why or 'ok (fails before the real fix, passes after it; grades %s)' % (
            'the whole test file' if ' -k ' not in grade else 'the test file less ' + grade.split('-k ', 1)[1])))
    return (1 if kept < a.want else 0) if a.want else (1 if bad else 0)


if __name__ == '__main__':
    sys.exit(main())
