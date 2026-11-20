#!/usr/bin/env python3
"""After a run: do the tests the agent itself wrote fail without its change?

A session that says "my tests pass" has shown nothing if those tests would pass on the unchanged code. odd's take-out
check refuses exactly that; a plain agent told to write and run tests has no such check. This measures, on what any
arm left behind, how often it happens: for each run record, `odd check` (odd.py at the root of this checkout) runs in
a copy of the kept tree, in the task's environment. It runs the test files that differ from the base branch, then
takes every other changed file out and runs them again. An arm's own files (OWN) are neither test nor product, and
pytest's testing/ folder counts as tests.

Verdicts, odd check's own: "no test of its own", "not passing as left", "fails without the change" (a real proof),
"passes without the change" (the tests show nothing about it), "not passing again", "nothing to check".

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
from realtasks import grade_environ  # noqa: E402

ODD = os.path.join(os.path.dirname(HERE), 'odd.py')
OWN = '.odd/**,.claude/**,.specify/**,specs/**,AGENTS.md,CLAUDE.md'  # an arm's own files: neither test nor product
TESTS = 'testing/**,**/testing/**'  # pytest keeps its own tests under testing/, in files not all named test_*.py
TIMEOUT = 1800


def own_proof(tree, task_dir, base='main'):
    """odd check's facts for one kept tree (verdict, tests, product, proof, ...), from a copy of it."""
    work = tempfile.mkdtemp(prefix='ownproof-')
    try:
        copy = os.path.join(work, 'p')
        shutil.copytree(tree, copy, symlinks=True)
        env = dict(grade_environ(task_dir, tree=copy), ODD_BASE='')
        try:
            p = subprocess.run([sys.executable, ODD, 'check', '--base', base, '--json', '--tests', TESTS, '--exempt', OWN],
                               cwd=copy, env=env, capture_output=True, text=True, timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            return dict(verdict='could not run', said='timed out after %d s' % TIMEOUT)
        try:
            return json.loads(p.stdout)
        except ValueError:
            return dict(verdict='could not run', said=(p.stderr or p.stdout).strip()[-400:])
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
