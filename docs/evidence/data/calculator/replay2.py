#!/usr/bin/env python3
"""Stage 0, no model: replay odd's comparison of passing attempts (backlog 46) on the fifteen kept calculators.

For every test file T (one per kept run) the inputs are odd.variants() of T's strings and numbers, exactly what a race
would compare. Every program P is run on them once. Two programs "differ" under T by odd's own rule: exit codes differ,
or both exit 0 with different output. Each program is labelled from the frozen probes (probes.json): clean (differs
on none of the 142) or defective. Writes replay2.json beside this file.

Read from it: pairs of clean programs that differ (a false alarm, or something the probes miss: each is listed),
and for each defective program how often a second attempt would have exposed it.

usage: replay2.py [VARIANTS]     (the cap on inputs, to see what a different cap would find; default odd's own)
"""
import glob
import itertools
import json
import multiprocessing
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
S = os.path.dirname(HERE)
REPO = '/home/user/odd-outcome-driven-development'
sys.path.insert(0, REPO)
sys.path.insert(0, HERE)
import odd  # noqa: E402
import probes  # noqa: E402

RUNS = [('odd', n, 'calc-out') for n in (1, 2, 3)] + [('speckit', n, 'calc-out') for n in (1, 2, 3)] + \
       [('odd-cases', n, 'calc-out2') for n in (1, 2, 3)] + [('odd-reach', n, 'calc-out3') for n in (1, 2, 3)]
NAME = lambda r: '%s.%d' % r[:2]  # noqa: E731


class Outcome:
    def __init__(self, fields):
        self.fields, self.rel = fields, '.odd/outcomes/replay.md'

    def get(self, k):
        return self.fields.get(k)


def project(arm, n, out):
    return json.load(open(os.path.join(S, out, 'calculator.%s.%d.json' % (arm, n))))['session_dir']


def inputs_of(t):
    d = tempfile.mkdtemp(prefix='replay2-')
    try:
        shutil.copytree(os.path.join(project(*t), 'tests'), os.path.join(d, 'tests'),
                        ignore=shutil.ignore_patterns('__pycache__', '.pytest_cache'))
        subprocess.run(['git', 'init', '-q'], cwd=d, check=True)
        tests = sorted(os.path.relpath(f, d) for f in glob.glob(os.path.join(d, 'tests', '**', '*.py'), recursive=True))
        o = Outcome({'proof': 'python3 -m pytest ' + ' '.join(tests)})
        return odd.variants(odd._entry_inputs(d, dict(odd.DEFAULTS), o))
    finally:
        shutil.rmtree(d, True)


def results(job):
    p, inputs = job
    calc = os.path.join(project(*p), 'calc.py')
    out = {}
    for x in inputs:
        rc, text = probes.run(calc, x)
        out[x] = [rc, text if rc == 0 else '']
    return NAME(p), out


if __name__ == '__main__':
    odd.VARIANTS = int(sys.argv[1]) if len(sys.argv) > 1 else odd.VARIANTS
    frozen = json.load(open(os.path.join(HERE, 'probes.json')))['kept']
    wrong = {}
    for r in RUNS:
        calc = os.path.join(project(*r), 'calc.py')
        wrong[NAME(r)] = [p['input'] for p in frozen if not probes.same((p['exit'], p['stdout']), probes.run(calc, p['input']))]
    clean = [n for n in wrong if not wrong[n]]
    per_test = {NAME(t): inputs_of(t) for t in RUNS}
    every = sorted({x for v in per_test.values() for x in v})
    with multiprocessing.Pool(8) as pool:
        got = dict(pool.map(results, [(p, every) for p in RUNS]))
    rows = []
    for t, inputs in per_test.items():
        for a, b in itertools.combinations([NAME(r) for r in RUNS], 2):
            apart = [x for x in inputs if None not in (got[a][x][0], got[b][x][0]) and got[a][x] != got[b][x]]
            rows.append(dict(tests=t, a=a, b=b, inputs=len(inputs), differ=len(apart),
                             examples=[[x, got[a][x], got[b][x]] for x in apart[:4]]))
    with open(os.path.join(HERE, 'replay2.json'), 'w') as f:
        json.dump(dict(wrong_on_frozen_probes=wrong, rows=rows), f, indent=1)
    print('clean on the frozen probes:', ', '.join(clean))
    print('defective:', ', '.join('%s (%d)' % (n, len(w)) for n, w in wrong.items() if w))
    cc = [r for r in rows if r['a'] in clean and r['b'] in clean]
    print('clean against clean: %d of %d (tests, pair) differ' % (sum(1 for r in cc if r['differ']), len(cc)))
    seen = set()
    for r in cc:
        for x, ga, gb in r['examples']:
            if (x, r['a'], r['b']) not in seen and len(seen) < 25:
                seen.add((x, r['a'], r['b']))
                print('    %r: %s %s, %s %s' % (x, r['a'], ga, r['b'], gb))
    for n in [n for n in wrong if wrong[n]]:
        with_clean = [r for r in rows if n in (r['a'], r['b']) and (r['a'] in clean or r['b'] in clean)]
        own = [r for r in with_clean if r['tests'] == n]
        print('%-12s with a clean second attempt: differs in %d of %d (tests, pair); with its own tests %d of %d'
              % (n, sum(1 for r in with_clean if r['differ']), len(with_clean), sum(1 for r in own if r['differ']), len(own)))
    dd = [r for r in rows if wrong[r['a']] and wrong[r['b']]]
    print('defective against defective: %d of %d differ' % (sum(1 for r in dd if r['differ']), len(dd)))
    for a, b in itertools.combinations([n for n in wrong if wrong[n]], 2):
        rs = [r for r in dd if (r['a'], r['b']) == (a, b)]
        if rs and not all(r['differ'] for r in rs):
            print('    %s and %s: differ under %d of %d test files' % (a, b, sum(1 for r in rs if r['differ']), len(rs)))
