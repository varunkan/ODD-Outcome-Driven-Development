#!/usr/bin/env python3
"""After several runs of one task: do the tests one run wrote pass on the fix another run made?

A fix and the tests written beside it share one reading of the ticket, so a check on those tests cannot see a
misreading. Tests written apart from the fix can. This measures, with no model, what such tests would have caught:
for every two kept runs X and Y of one task, X's changed test files are copied over a copy of Y's tree and run there
with `odd`'s own choice of command (odd.tests_proof), in the task's environment. X's tests are first run on X's own
tree; only tests that pass there count.

An ALARM on Y is: tests of some other run, passing on their own tree, fail on Y's tree. Set beside Y's hidden grade
it is a true alarm (Y fails the hidden tests) or a false one (Y passes them).

usage: crosstest.py --root ROOT [--base main] [--jobs N] RECORD.json [RECORD.json ...]
Prints one JSON object per pair (tests_of, fix_of), then the counts.
"""
import argparse
import collections
import json
import multiprocessing
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import odd  # noqa: E402
from ownproof import OWN, TESTS  # noqa: E402
from realtasks import grade_environ  # noqa: E402

TIMEOUT = 900


def split(tree, base):
    """(test files, product files) of what a kept run changed, by odd check's own rules and ownproof's options."""
    cfg = odd.load_config(tree, at=odd.EMPTY_TREE)
    cfg['test_globs'], cfg['exempt'] = cfg['test_globs'] + TESTS.split(','), cfg['exempt'] + OWN.split(',')
    _, _, tests, product = odd.classify(odd.changed_files(tree, base), cfg)
    return [t for t in tests if os.path.isfile(os.path.join(tree, t))], product


def one(job):
    task_dir, base, x, y = job
    tests, _ = split(x['session_dir'], base)
    out = dict(task=x['task'], tests_of=x['label'], fix_of=y['label'], own=x['label'] == y['label'],
               fix_passes_hidden=y['passed'], tests=tests)
    if not tests:
        return dict(out, result='no tests')
    work = tempfile.mkdtemp(prefix='crosstest-')
    try:
        copy = os.path.join(work, 'p')
        shutil.copytree(y['session_dir'], copy, symlinks=True)
        for t in tests:
            os.makedirs(os.path.dirname(os.path.join(copy, t)), exist_ok=True)
            shutil.copyfile(os.path.join(x['session_dir'], t), os.path.join(copy, t))
        proof = odd.tests_proof(copy, tests)
        if not proof:
            return dict(out, result='no tests')
        rc, tail, _ = odd.run_proof(copy, proof, TIMEOUT, grade_environ(task_dir, tree=copy))
        return dict(out, proof=proof, result='pass' if rc == 0 else 'fail', said=odd.says(tail) if rc else '')
    finally:
        shutil.rmtree(work, True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--root', required=True)
    ap.add_argument('--base', default='main')
    ap.add_argument('--jobs', type=int, default=4)
    ap.add_argument('records', nargs='+')
    a = ap.parse_args(argv)
    by = collections.defaultdict(list)
    for path in a.records:
        with open(path, encoding='utf-8') as f:
            rec = json.load(f)
        if os.path.isdir(rec.get('session_dir') or ''):
            rec['label'] = '%s:%s' % (os.path.basename(os.path.dirname(os.path.abspath(path))), rec['arm'])
            by[rec['task']].append(rec)
    jobs = [(os.path.join(a.root, 'tasks', task), a.base, x, y) for task, recs in sorted(by.items())
            for x in recs for y in recs]
    with multiprocessing.Pool(a.jobs) as pool:
        rows = pool.map(one, jobs, chunksize=1)
    for r in rows:
        print(json.dumps(r))
    sound = {(r['task'], r['tests_of']) for r in rows if r['own'] and r['result'] == 'pass'}
    alarms = collections.defaultdict(list)
    for r in rows:
        if not r['own'] and (r['task'], r['tests_of']) in sound:
            alarms[(r['task'], r['fix_of'], r['fix_passes_hidden'])].append(r['result'] == 'fail')
    for hidden in (False, True):
        fixes = [v for k, v in alarms.items() if k[2] is hidden]
        print('fixes whose hidden tests %s: %d with tests of another run to try; %d of them fail at least one'
              % ('pass' if hidden else 'fail', len(fixes), sum(1 for v in fixes if any(v))))
    return 0


if __name__ == '__main__':
    sys.exit(main())
