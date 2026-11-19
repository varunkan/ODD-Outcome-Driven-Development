#!/usr/bin/env python3
"""After a run: do the tests the agent itself wrote fail without its change?

A session that says "my tests pass" has shown nothing if those tests would pass on the unchanged code. odd's take-out
check refuses exactly that; a plain agent told to write and run tests has no such check. This measures, on what any
arm left behind, how often it happens: for each run record, in a copy of the kept tree,

  1. the files that differ from the base branch are split into test files (odd's own test paths, and pytest's
     testing/ folder) and the rest;
  2. the changed test files are run with pytest, in the task's environment, as the session left the tree;
  3. the rest is put back as it is on the base branch (new files removed), and the same tests are run again.

Verdicts: "no test of its own" (no test file changed), "not passing as left" (step 2 fails: the session's own tests do
not pass), "fails without the change" (a real proof), "passes without the change" (the tests show nothing about it).

usage: ownproof.py --root ROOT [--base main] RECORD.json [RECORD.json ...]
       ROOT holds tasks/<id>/ (for the task's environment); each record names its kept tree in session_dir.
Prints one JSON object per record, then the counts per arm.
"""
import argparse
import collections
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import odd  # noqa: E402
from realtasks import grade_environ  # noqa: E402

OWN = ('.odd/', '.claude/', '.specify/', 'specs/', 'AGENTS.md', 'CLAUDE.md')  # an arm's own files: neither test nor product
TIMEOUT = 900
# pytest keeps its own tests under testing/, in files not all named test_*.py; odd's test paths are not changed for it
TEST_GLOBS = odd.DEFAULTS['test_globs'] + ['testing/**', '**/testing/**']


def git(tree, *args):
    return subprocess.run(['git'] + list(args), cwd=tree, capture_output=True, text=True)


def changed(tree, base):
    """Paths that differ from `base` in the kept tree: committed, uncommitted and untracked."""
    names = set(git(tree, 'diff', '--name-only', '-z', base).stdout.split('\0'))
    names |= set(git(tree, 'ls-files', '-z', '--others', '--exclude-standard').stdout.split('\0'))
    return sorted(n for n in names if n and not n.startswith(OWN) and n not in OWN)


def run_tests(tree, tests, env):
    try:
        p = subprocess.run([sys.executable if 'VIRTUAL_ENV' not in env else 'python3', '-m', 'pytest', '-q', '-x',
                            '-p', 'no:cacheprovider'] + tests, cwd=tree, env=env, capture_output=True, text=True,
                           timeout=TIMEOUT)
        return p.returncode, (p.stdout + p.stderr).strip().splitlines()[-1:]
    except subprocess.TimeoutExpired:
        return None, ['timed out after %d s' % TIMEOUT]


def own_proof(tree, task_dir, base='main'):
    """The verdict for one kept tree, with what it rests on."""
    files = changed(tree, base)
    tests = [f for f in files if odd.matches(f, TEST_GLOBS) and f.endswith('.py')
             and os.path.isfile(os.path.join(tree, f))]
    product = [f for f in files if f not in tests and not odd.matches(f, TEST_GLOBS)]
    out = dict(tests=tests, product=product)
    if not tests:
        return dict(out, verdict='no test of its own')
    work = tempfile.mkdtemp(prefix='ownproof-')
    try:
        copy = os.path.join(work, 'p')
        shutil.copytree(tree, copy, symlinks=True)
        env = grade_environ(task_dir, tree=copy)
        rc, last = run_tests(copy, tests, env)
        out['as_left'] = dict(exit=rc, last=last)
        if rc != 0:
            return dict(out, verdict='not passing as left')
        for f in product:  # the change taken out: each product file as it is on the base, or gone if it is new
            had = git(copy, 'cat-file', '-e', '%s:%s' % (base, f)).returncode == 0
            if had:
                git(copy, 'checkout', base, '--', f)
            elif os.path.lexists(os.path.join(copy, f)):
                os.remove(os.path.join(copy, f))
        rc, last = run_tests(copy, tests, env)
        out['without'] = dict(exit=rc, last=last)
        return dict(out, verdict='passes without the change' if rc == 0 else 'fails without the change')
    finally:
        shutil.rmtree(work, True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--root', required=True)
    ap.add_argument('--base', default='main')
    ap.add_argument('records', nargs='+')
    a = ap.parse_args(argv)
    counts = collections.defaultdict(collections.Counter)
    for path in a.records:
        with open(path, encoding='utf-8') as f:
            rec = json.load(f)
        tree = rec.get('session_dir') or ''
        if not os.path.isdir(tree):
            res = dict(verdict='no kept tree')
        else:
            res = own_proof(tree, os.path.join(a.root, 'tasks', rec['task']), a.base)
        counts[rec['arm']][res['verdict']] += 1
        print(json.dumps(dict(task=rec['task'], arm=rec['arm'], repeat=rec.get('repeat'), claim=rec.get('claim'),
                              passed=rec.get('passed'), **res)))
    for arm in sorted(counts):
        print('%s: %s' % (arm, ', '.join('%s %d' % kv for kv in sorted(counts[arm].items()))))
    return 0


if __name__ == '__main__':
    sys.exit(main())
