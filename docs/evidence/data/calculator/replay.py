#!/usr/bin/env python3
"""Stage 0, no model: replay odd's "reject:" check (backlog 45) on the nine kept calculators.

For every pair (tests of run T, calc.py of run P) a fresh folder holds P's calc.py and T's tests; odd.rejects() is
called on it with entry calc.py and reject 2 (the ticket's exit code for an invalid expression). T == P is what the
gate would have seen in that run; T != P shows whether the check raises false alarms on a program with other tests.
Writes replay.json beside this file.

usage: replay.py
"""
import glob
import json
import multiprocessing
import os
import shutil
import subprocess
import sys
import tempfile

S = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = '/home/user/odd-outcome-driven-development'
sys.path.insert(0, REPO)
import odd  # noqa: E402

RUNS = [('odd', n, 'calc-out') for n in (1, 2, 3)] + [('speckit', n, 'calc-out') for n in (1, 2, 3)] + \
       [('odd-cases', n, 'calc-out2') for n in (1, 2, 3)]


class Outcome:
    def __init__(self, fields):
        self.fields, self.rel = fields, '.odd/outcomes/replay.md'

    def get(self, k):
        return self.fields.get(k)


def project(arm, n, out):
    return json.load(open(os.path.join(S, out, 'calculator.%s.%d.json' % (arm, n))))['session_dir']


def one(pair):
    t, p = pair
    d = tempfile.mkdtemp(prefix='replay-')
    try:
        shutil.copy(os.path.join(project(*p), 'calc.py'), os.path.join(d, 'calc.py'))
        shutil.copytree(os.path.join(project(*t), 'tests'), os.path.join(d, 'tests'),
                        ignore=shutil.ignore_patterns('__pycache__', '.pytest_cache'))
        subprocess.run(['git', 'init', '-q'], cwd=d, check=True)
        tests = sorted(os.path.relpath(f, d) for f in glob.glob(os.path.join(d, 'tests', '**', '*.py'), recursive=True))
        o = Outcome({'proof': 'python3 -m pytest ' + ' '.join(tests), 'entry': 'calc.py', 'reject': '2'})
        cfg = dict(odd.DEFAULTS)
        try:
            verdict, text = 'pass', odd.rejects(d, cfg, o)
        except odd.Fail as e:
            verdict, text = 'FAIL', str(e).split('\n')[0]
        except odd.CouldNotRun as e:
            verdict, text = 'could not run', str(e)
        return dict(tests='%s.%d' % t[:2], program='%s.%d' % p[:2], verdict=verdict, text=text)
    finally:
        shutil.rmtree(d, True)


if __name__ == '__main__':
    with multiprocessing.Pool(6) as pool:
        rows = pool.map(one, [(t, p) for t in RUNS for p in RUNS])
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'replay.json'), 'w') as f:
        json.dump(rows, f, indent=1)
    names = ['%s.%d' % r[:2] for r in RUNS]
    print('rows: tests of; columns: program of ' + ' '.join(names))
    for t in names:
        print('%-12s' % t + ' '.join('%-*s' % (len(n), {'pass': 'ok', 'FAIL': 'FAIL'}.get(r['verdict'], '?'))
                                      for n in names for r in rows if r['tests'] == t and r['program'] == n))
    for r in rows:
        if r['tests'] == r['program'] or r['verdict'] != 'pass':
            print('%s on %s: %s' % (r['tests'], r['program'], r['text'][:260]))
