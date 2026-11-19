#!/usr/bin/env python3
"""Build comparison tasks from real open-source issues (SWE-bench Lite), for BACKLOG item 18.

usage: realtasks.py --rows DIR --out ROOT [--strict] [--want N] [--python X.Y|spec] [--keep-refused] ID [ID ...]

DIR holds the SWE-bench Lite rows as fetched from the Hugging Face datasets server (rows*.json). For each instance ID
this writes ROOT/tasks/<id>/ in the harness's task format: repo/ (the project at the issue's base commit, without its
git history), ticket.md (the issue text, as its reporter wrote it), hidden/tests_hidden/ (the test file as the real
fix's test patch leaves it), solution.patch (the real fix) and task.json (grade: pytest on that whole file, so its
other tests catch a regression the way SWE-bench's same-file PASS_TO_PASS tests do, less any test the real fix itself
fails on this machine, such as one needing an optional package that is not installed: a test the reference fix cannot
pass checks nothing). With --strict such a task is refused instead (the rule for SWE-bench Verified tasks, whose tests
people checked against the issue: a trimmed file is no longer that check). With --want N the IDs are candidates in the
order given and building stops once N tasks are kept, so the selection is fixed before any task is tried.

With --python (BACKLOG item 42) each task gets its own environment, ROOT/tasks/<id>/env: that Python (fetched by uv;
with "spec", the version and the test dependencies SPECS names for the task's project, which are SWE-bench's own),
pytest, and the project's own dependencies at the issue's commit, without the project itself, so the code under test
is always the tree in front of the test and never an installed copy. The grade then runs with env/bin first on PATH
and that tree as the package (task_environ), the way SWE-bench gives every instance its own environment; run.py
gives each session a copy of the environment and grades in the task's own. The hidden test then comes with its whole
test directory, so that directory's conftest files and test data apply to it. ROOT/arms/ is copied from this
directory, so `run.py --root ROOT` runs the usual arms on these tasks.

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
import time

HERE = os.path.dirname(os.path.abspath(__file__))
# How each project's environment is built for --python: what SWE-bench's own harness does for it (its constants,
# swebench 4.1.0 harness/constants/python.py: Python 3.9 for every version of these five projects, sphinx installed
# with its "test" extra, pylint with its requirements_test.txt), less that harness's version pins, which only hold a
# 2023 install to what the project could use: here every dependency is resolved as of the issue's day instead.
# 'pins' are installed last and whatever their date; 'newer' names a package the project's own install may take as
# of a later day; VERSION_SPECS changes an entry for one (project, version).
SPECS = {
    # atomicwrites (pytest 4 and 5 need it) was taken off the package index and put back on 2022-07-08, so every
    # release of it carries that day; SWE-bench pins its 1.4.1
    'pytest-dev/pytest': {'python': '3.9', 'newer': {'atomicwrites': '2022-07-09T00:00:00Z'}},
    'psf/requests': {'python': '3.9'},
    'pylint-dev/pylint': {'python': '3.9', 'requirements': ['requirements_test.txt']},
    # sphinx's setup.cfg adds the day to its version, and the setuptools of 2020 and 2021 adds it twice when it
    # builds a wheel, which is then no version at all: its wheel is built with a setuptools from after that was fixed
    'sphinx-doc/sphinx': {'python': '3.9', 'extras': 'test', 'newer': {'setuptools': '2023-01-01T00:00:00Z'}},
    'sympy/sympy': {'python': '3.9'},
}
VERSION_SPECS = {}
# The day after each Python came out. Nothing is resolved as of an earlier day: what was published before a Python
# existed was never run on it (pytest of 2018 does not start on 3.9), and SWE-bench builds with 2023's releases.
PYTHON_RELEASED = {'3.7': '2018-06-28T00:00:00Z', '3.8': '2019-10-15T00:00:00Z', '3.9': '2020-10-06T00:00:00Z',
                   '3.10': '2021-10-05T00:00:00Z', '3.11': '2022-10-25T00:00:00Z', '3.12': '2023-10-03T00:00:00Z',
                   '3.13': '2024-10-08T00:00:00Z'}


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
    """The project at `commit` in `dest`, without its history. Returns the day of that commit, in UTC."""
    os.makedirs(dest)
    sh(['git', 'init', '-q'], dest)
    sh(['git', 'fetch', '-q', '--depth', '1', 'https://github.com/%s' % repo, commit], dest, timeout=900)
    sh(['git', 'checkout', '-q', 'FETCH_HEAD'], dest)
    day = sh(['git', 'log', '-1', '--format=%cd', '--date=format-local:%Y-%m-%dT%H:%M:%SZ'], dest,
             env=dict(os.environ, TZ='UTC')).stdout.strip()
    shutil.rmtree(os.path.join(dest, '.git'))
    return day


def spec_for(row, python):
    """How to build the row's environment: its project's SPECS entry when `python` is 'spec' (a project without one
    is refused: its needs are not known), else that entry, or none, with the Python version given."""
    spec = SPECS.get(row['repo'])
    if python == 'spec' and spec is None:
        raise RuntimeError('no environment spec for %s: add one to SPECS, or name a Python version' % row['repo'])
    spec = dict(spec or {}, **VERSION_SPECS.get((row['repo'], row.get('version')), {}))
    return spec if python == 'spec' else dict(spec, python=python)


def requirements(folder, names):
    """The requirement lines of the files `names` in `folder` and of the files they include (-r), without comments,
    options and the lines that install the project itself (-e ., .[extra]): make_env installs it its own way."""
    out = []
    for name in names:
        path = os.path.join(folder, name)
        if not os.path.isfile(path):
            continue
        with open(path, encoding='utf-8') as f:
            for line in f:
                line = re.sub(r'(^|\s)#.*', '', line).strip()
                if line.startswith('-r '):
                    out += requirements(os.path.dirname(path), [line[3:].strip()])
                elif line and not line.startswith(('-', '.')):
                    out.append(line)
    return out


def grade_environ(task_dir, environ=None, tree=None):
    """The environment a task's grade runs in, here and in run.py: task_environ with the task's own env/, and, for a
    task that has one, without the machine's proxy settings, which a project's tests read (requests) and which no
    SWE-bench container has. A session keeps them: its agent may need them to reach its model."""
    out = task_environ(task_dir, environ, tree)
    if 'VIRTUAL_ENV' in out and os.path.isdir(os.path.join(task_dir, 'env', 'bin')):
        out = {k: v for k, v in out.items() if not k.lower().endswith('_proxy')}
    return out


def test_folder(path):
    """The directory that comes with the hidden test file `path` when the task has its own environment: the project's
    test tree if the file is in one (its conftest files and the data other folders of the tree hold apply to it), else
    the file's own folder (a test folder inside the package, as in sympy: the package itself is never hidden; build()
    keeps that folder's path under tests_hidden/ and the conftest.py of each folder above it, which pytest applies
    to it in the project: sympy's tells sympy that pytest runs it, without which an expected failure is a failure)."""
    top = path.split('/')[0]
    return top if '/' in path and top in ('tests', 'testing', 'test') else os.path.dirname(path)


def task_environ(task_dir, environ=None, tree=None, env=None):
    """The environment a task's commands run in: `environ`, unchanged unless the task was built with --python. Then
    the task's environment comes first on PATH (`env`, a copy of it, in place of the task's own when given: run.py
    gives every session one) and the project's package is the one in `tree`, the directory the commands run in,
    by its absolute path, since a test's own subprocess starts in some other directory."""
    out = dict(os.environ if environ is None else environ)
    own = os.path.join(task_dir, 'env')
    if os.path.isdir(os.path.join(own, 'bin')):
        own = env or own
        out['PATH'] = os.path.join(own, 'bin') + os.pathsep + out.get('PATH', '')
        out['VIRTUAL_ENV'] = own
        src = os.path.isdir(os.path.join(task_dir, 'repo', 'src'))  # a src layout: the package is under src/
        if tree or src:
            code = os.path.join(tree, 'src') if tree and src else tree or 'src'
            out['PYTHONPATH'] = os.pathsep.join([code] + [x for x in [out.get('PYTHONPATH')] if x])
    return out


def make_env(task_dir, spec, before=None, version=None):
    """ROOT/tasks/<id>/env, built as `spec` says (spec_for): its Python, pytest, pip and the project's dependencies,
    with the extra and the requirement files its tests need, each in the newest version published by `before` (the
    day of the issue or of its commit) or by the day that Python came out if that is later (PYTHON_RELEASED), since a
    project of that day breaks on later releases of what it uses; then the spec's pins, whatever their date. The
    project is installed to resolve its dependencies and then taken out again, and what that install wrote at the
    top of repo/ is removed. The environment is relocatable: it works from a copy."""
    repo, env = os.path.join(task_dir, 'repo'), os.path.join(task_dir, 'env')
    had = set(os.listdir(repo))
    sh(['uv', 'venv', '-q', '--relocatable', '--python', spec['python'], env], task_dir, timeout=900)
    py = os.path.join(env, 'bin', 'python')
    install = ['uv', 'pip', 'install', '-q', '--python', py]
    dated = ['--exclude-newer', max(before, PYTHON_RELEASED.get(spec['python'], ''))] if before else []
    # setuptools below 81 still ships pkg_resources, which projects of these years import at run time; pip, so that a
    # session's "pip install" finds this environment's (its own copy's) and not the machine's
    sh(install + dated + ['pytest', 'setuptools<81', 'pip'], task_dir, timeout=900)
    # not editable: build tools of the issue's day cannot build an editable install
    project = repo + ('[%s]' % spec['extras'] if spec.get('extras') else '')
    newer = [x for name, day in sorted(spec.get('newer', {}).items()) if dated
             for x in ('--exclude-newer-package', '%s=%s' % (name, day))]
    sh(install + dated + newer + [project] + requirements(repo, spec.get('requirements', [])), task_dir, timeout=1800,
       # no git history here to read a version from: the one the row names
       env=dict(os.environ, SETUPTOOLS_SCM_PRETEND_VERSION=version or '0.0.0'))
    names = sh([py, '-c', 'import importlib.metadata as m\nfor d in m.distributions():\n'
                '    if d.read_text("direct_url.json"): print(d.metadata["Name"])'], task_dir).stdout.split()
    if names:
        sh(['uv', 'pip', 'uninstall', '-q', '--python', py] + names, task_dir, timeout=300)
    if spec.get('pins'):
        sh(install + spec['pins'], task_dir, timeout=900)
    for name in set(os.listdir(repo)) - had:  # egg-info, build/: not part of the project at that commit
        path = os.path.join(repo, name)
        shutil.rmtree(path, ignore_errors=True) if os.path.isdir(path) else os.remove(path)


def grade_status(task_dir, grade, patch=None, out=None, said=None):
    """The grade's exit status on a copy of repo/ with the hidden tests in, and `patch` applied first if given; with a
    list as `out`, the names of the tests that failed or errored are appended to it, and with one as `said` the last
    error and the last line the grade printed (why it failed, when no test did: a missing package)."""
    work = tempfile.mkdtemp(prefix='realtask-')
    try:
        copy = os.path.join(work, 'p')
        shutil.copytree(os.path.join(task_dir, 'repo'), copy, symlinks=True)
        if patch:
            sh(['git', 'apply', '--whitespace=nowarn', patch], copy)
        shutil.copytree(os.path.join(task_dir, 'hidden', 'tests_hidden'), os.path.join(copy, 'tests_hidden'))
        r = sh(grade + (' -rfE' if out is not None else ''), copy, check=False, timeout=900, env=grade_environ(task_dir, None, copy))
        if out is not None:
            out += re.findall(r'^(?:FAILED|ERROR) \S+::(\w+)', r.stdout, re.M)
        if said is not None:
            lines = [x.strip() for x in (r.stdout + r.stderr).splitlines() if x.strip()]
            said += [x for x in lines if x.startswith('E ')][-1:] + lines[-1:]  # pytest's last error, and its ending
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
    spec = spec_for(row, python) if python else None
    repo = os.path.join(task_dir, 'repo')
    committed = checkout(row['repo'], row['base_commit'], repo)
    if spec:  # as of the commit's day when that is the later one: the commit may pin a release made since the issue
        make_env(task_dir, spec, max(row.get('created_at') or '', committed or '') or None, row.get('version'))
    # the hidden test: the test file as the real fix's test patch leaves it, applied to a scratch copy only
    scratch = tempfile.mkdtemp(prefix='realtask-test-')
    try:
        target, folder = os.path.join(scratch, files[0]), test_folder(files[0]) if python else ''
        inner = '' if folder == files[0].split('/')[0] else folder  # a folder inside the package keeps its path
        if folder:  # the whole test directory, so its conftest files and test data apply to the hidden test
            shutil.copytree(os.path.join(repo, folder), os.path.join(scratch, folder), symlinks=True)
        else:
            os.makedirs(os.path.dirname(target), exist_ok=True)  # a test file at the project root lives in scratch itself
            if os.path.exists(os.path.join(repo, files[0])):
                shutil.copy2(os.path.join(repo, files[0]), target)
        with open(os.path.join(scratch, 'test.patch'), 'w', encoding='utf-8') as f:
            f.write(row['test_patch'])
        sh(['git', 'apply', '--whitespace=nowarn', 'test.patch'], scratch)
        if folder:
            hidden = os.path.join(task_dir, 'hidden', 'tests_hidden')
            shutil.copytree(os.path.join(scratch, folder), os.path.join(hidden, inner), symlinks=True)
            above = os.path.dirname(inner)
            while above:
                if os.path.isfile(os.path.join(repo, above, 'conftest.py')):
                    shutil.copy2(os.path.join(repo, above, 'conftest.py'), os.path.join(hidden, above, 'conftest.py'))
                above = os.path.dirname(above)
        else:
            os.makedirs(os.path.join(task_dir, 'hidden', 'tests_hidden'))
            shutil.copy2(target, os.path.join(task_dir, 'hidden', 'tests_hidden', os.path.basename(files[0])))
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    grade = 'python3 -m pytest -q -p no:cacheprovider tests_hidden/%s' % (
        os.path.join(inner, os.path.relpath(files[0], folder)) if folder else os.path.basename(files[0]))
    with open(os.path.join(task_dir, 'solution.patch'), 'w', encoding='utf-8') as f:
        f.write(row['patch'])
    with open(os.path.join(task_dir, 'ticket.md'), 'w', encoding='utf-8') as f:
        f.write(row['problem_statement'].strip() + '\n')
    fix, broken, said, started = os.path.join(task_dir, 'solution.patch'), [], [], time.time()
    passed = grade_status(task_dir, grade, fix, broken, said) == 0
    seconds = int(time.time() - started) + 1  # what the whole file takes here: run.py's limit for it follows this
    if not passed:
        target = {t.split('::')[-1].split('[')[0] for t in json.loads(row['FAIL_TO_PASS'])}
        if strict or not broken or target & set(broken):
            return 'the grade fails after the real fix (%s)' % (
                ', '.join(broken[:6]) or 'no test named; it ended: ' + ' | '.join(said)[-300:])
        grade += ' -k "not (%s)"' % ' or '.join(dict.fromkeys(broken))
    with open(os.path.join(task_dir, 'task.json'), 'w', encoding='utf-8') as f:
        json.dump(dict({'id': iid, 'size': 'large', 'kind': 'real', 'grade': grade, 'expect': 'done',
                        'source': 'SWE-bench Lite %s (%s at %s)' % (iid, row['repo'], row['base_commit'][:12])},
                       **({'python': spec['python'], 'grade_seconds': seconds} if spec else {})), f, indent=2)
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
    ap.add_argument('--python', metavar='X.Y|spec', help='give each task its own environment: with this Python '
                    'version, or with "spec" as SPECS says for its project (the way SWE-bench builds it)')
    ap.add_argument('--keep-refused', action='store_true',
                    help='move a refused task to ROOT/refused/<id>, to see why, in place of removing it')
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
            aside = os.path.join(a.out, 'refused', iid)
            shutil.rmtree(aside, ignore_errors=True)
            if a.keep_refused and os.path.isdir(os.path.join(a.out, 'tasks', iid)):
                os.makedirs(os.path.dirname(aside), exist_ok=True)
                os.replace(os.path.join(a.out, 'tasks', iid), aside)
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
